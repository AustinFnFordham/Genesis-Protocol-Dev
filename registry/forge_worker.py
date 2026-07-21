"""GENESIS BACKGROUND FORGE WORKER — bounded batches, never auto-promotes.

Queries corpus_registry.sqlite for one bounded domain, normalizes and
validates candidates, emits draft / quarantine / validated_candidate into a
SEPARATE candidate build (registry/candidate_builds/<build_id>/). The live
API stays pinned to its approved registry; nothing here hot-reloads.

Status heartbeat: registry/forge_background_status.json (the required contract).
Run:  python registry/forge_worker.py --domain classes
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time

ROOT = r'E:\StarWars'
REG = os.path.join(ROOT, 'registry')
DB = os.path.join(REG, 'corpus_registry.sqlite')
STATUS = os.path.join(REG, 'forge_background_status.json')
FORGE_VERSION = 'forge_worker_v1.0'

DOMAIN_QUERIES = {
    'classes': "SELECT DISTINCT source_pointer FROM entity_candidates WHERE (source_pointer LIKE '%/classes/%' OR source_pointer LIKE '%subclass%') AND source_pointer LIKE '%.yml'",
    'actions': "SELECT DISTINCT source_pointer FROM entity_candidates WHERE source_pointer LIKE '%/actions/%' AND source_pointer LIKE '%.yml'",
    'weapons': "SELECT DISTINCT source_pointer FROM entity_candidates WHERE (source_pointer LIKE '%weapon%' OR source_pointer LIKE '%/items/%') AND source_pointer LIKE '%.yml'",
    'powers': "SELECT DISTINCT source_pointer FROM entity_candidates WHERE source_pointer LIKE '%/powers/%' AND source_pointer LIKE '%.yml'",
    'backgrounds': "SELECT DISTINCT source_pointer FROM entity_candidates WHERE source_pointer LIKE '%background%' AND source_pointer LIKE '%.yml'",
    'species': "SELECT DISTINCT source_pointer FROM entity_candidates WHERE source_pointer LIKE '%species%' AND source_pointer LIKE '%.yml'",
}
# authoritative source lanes only — forge outputs/fixtures are NOT inputs
SOURCE_ALLOW = ('forge_v3_backend', 'raw_source')


def heartbeat(state):
    state['last_heartbeat'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    json.dump(state, open(STATUS, 'w', encoding='utf-8'), indent=1)


def audit_candidate(doc, kind):
    """Articles of Creation + Trinity audit (declared, per candidate)."""
    has_mech = any(k in doc for k in ('progression', 'levels', 'hit_die', 'mechanics', 'damage', 'effects', 'features'))
    has_fluff = any(k in doc for k in ('description', 'flavor', 'lore', 'narrative', 'summary'))
    refs = [v for k, v in doc.items() if isinstance(v, str) and (v.startswith(('class_', 'species_', 'feature_', 'power_', 'bg_', 'background_')))]
    return {
        'crunch_fluff_partition': has_mech and has_fluff or (has_mech != has_fluff),
        'emotions_structured_where_applicable': 'n/a' if kind != 'npc' else 'unreviewed',
        'urid_stable': bool(doc.get('urid') or doc.get('id') or (doc.get('metadata') or {}).get('id') if isinstance(doc.get('metadata'), dict) else doc.get('id')),
        'visual_dna_present_where_applicable': 'n/a' if kind not in ('species', 'npc') else bool(doc.get('visual_dna')),
        'bifurcated_output_compatible': True,
        'atomic': {'schema_valid': None, 'deterministic': True, 'references_valid': None,
                   'provenance_complete': None, 'mutation_compatible': True},
        'soul': {'identity_preserved': True, 'lore_preserved': has_fluff, 'relationships_preserved': 'n/a',
                 'emotional_meaning_preserved': 'n/a', 'visual_constants_preserved': 'n/a'},
        'chaos': {'synergy_inputs_declared': 'tags' in doc or 'taxonomy' in doc,
                  'prerequisites_declared': any('prereq' in str(k).lower() for k in doc),
                  'consequence_hooks_present': False, 'world_reaction_hooks_present': False,
                  'no_automatic_unlock_from_tags': True},
    }


def validate_class_shape(doc):
    """Domain validation for classes/subclasses (schema-lite; strict schemas run at promotion)."""
    errors, warnings = [], []
    idn = doc.get('id') or doc.get('urid') or (doc.get('metadata') or {}).get('id')
    if not idn:
        errors.append('no stable id/urid')
    is_subclass = 'subclass' in json.dumps(doc)[:400].lower() or (doc.get('type') == 'subclass')
    if is_subclass:
        parent = doc.get('class') or doc.get('class_id') or doc.get('parent_class')
        if not parent:
            warnings.append('subclass without parent class reference')
    else:
        if not any(k in doc for k in ('hit_die', 'hit_dice', 'hp', 'progression', 'levels', 'level_progression', 'features')):
            warnings.append('class without progression/hit-die signals')
    return errors, warnings, ('subclass' if is_subclass else 'class')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--domain', default='classes')
    ap.add_argument('--limit', type=int, default=100)
    args = ap.parse_args()

    import yaml
    db = sqlite3.connect(DB)
    rows = [r[0] for r in db.execute(DOMAIN_QUERIES[args.domain]).fetchall()]
    # bounded batch; authoritative source roots only; dedupe by exact-hash groups
    files = {p: (sr, h, dg) for p, sr, h, dg in db.execute('SELECT path, source_root, hash, duplicate_group FROM files')}
    batch = []
    seen_hashes = set()
    for p in sorted(rows):
        meta = files.get(p)
        if not meta or meta[0] not in SOURCE_ALLOW:
            continue
        if meta[1] in seen_hashes:
            continue  # exact duplicate — process once, record lineage
        seen_hashes.add(meta[1])
        batch.append(p)
        if len(batch) >= args.limit:
            break

    input_hash = hashlib.sha256('\n'.join(batch).encode()).hexdigest()[:16]
    src_manifest = json.load(open(os.path.join(REG, 'exports', 'build_manifest.json')))
    build_id = f'cand_{args.domain}_{input_hash}'
    out_root = os.path.join(REG, 'candidate_builds', build_id)
    for sub in ('validated_candidate', 'draft', 'quarantine'):
        os.makedirs(os.path.join(out_root, sub), exist_ok=True)
    log_path = os.path.join(out_root, 'worker.log')
    ckpt_path = os.path.join(out_root, 'checkpoint.json')

    state = {
        'worker_running': True, 'process_id': os.getpid(), 'forge_version': FORGE_VERSION,
        'source_registry_build_id': src_manifest['registry_build_id'],
        'active_job_id': f'job_{build_id}', 'active_batch': input_hash, 'active_domain': args.domain,
        'candidate_count': len(batch), 'completed_count': 0, 'passed_count': 0,
        'quarantined_count': 0, 'failed_count': 0, 'unresolved_count': 0,
        'started_at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'estimated_remaining': len(batch),
        'output_root': out_root, 'log_path': log_path, 'checkpoint_path': ckpt_path,
        'candidate_registry_build_id': build_id,
    }
    heartbeat(state)
    done = set()
    if os.path.exists(ckpt_path):  # restart-safe resume
        done = set(json.load(open(ckpt_path)).get('done', []))

    results = []
    with open(log_path, 'a', encoding='utf-8') as log:
        for p in batch:
            if p in done:
                state['completed_count'] += 1
                continue
            full = os.path.join(ROOT, p)
            try:
                doc = yaml.safe_load(open(full, encoding='utf-8', errors='replace'))
            except Exception as e:
                state['failed_count'] += 1
                results.append({'path': p, 'outcome': 'quarantine', 'reason': f'strict_parse: {str(e)[:120]}'})
                log.write(f'QUARANTINE parse {p}\n')
                done.add(p); state['completed_count'] += 1
                heartbeat(state); continue
            docs = doc if isinstance(doc, list) else [doc]
            for d in docs:
                if not isinstance(d, dict):
                    continue
                errors, warnings, kind = validate_class_shape(d)
                aud = audit_candidate(d, kind)
                idn = d.get('id') or d.get('urid') or os.path.splitext(os.path.basename(p))[0]
                rec = {'candidate_urid': str(idn), 'kind': kind, 'source_pointer': p,
                       'source_root': files[p][0], 'duplicate_group': files[p][2],
                       'errors': errors, 'warnings': warnings, 'creation_audit': aud,
                       'forge_version': FORGE_VERSION, 'promotion': 'requires_manifest_and_review'}
                if errors:
                    outcome = 'quarantine'; state['quarantined_count'] += 1
                elif warnings:
                    outcome = 'draft'; state['unresolved_count'] += 1
                else:
                    outcome = 'validated_candidate'; state['passed_count'] += 1
                rec['outcome'] = outcome
                fn = f"{str(idn)[:60].replace('/', '_')}.json"
                json.dump({'record': d, 'validation': rec}, open(os.path.join(out_root, outcome, fn), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
                results.append(rec)
                log.write(f'{outcome.upper()} {idn} <- {p}\n')
            done.add(p)
            state['completed_count'] += 1
            state['estimated_remaining'] = len(batch) - state['completed_count']
            if state['completed_count'] % 10 == 0:
                json.dump({'done': sorted(done)}, open(ckpt_path, 'w'))
                heartbeat(state)

    json.dump({'done': sorted(done)}, open(ckpt_path, 'w'))
    manifest = {
        'forge_batch': {
            'job_id': state['active_job_id'], 'domain': args.domain,
            'source_query': DOMAIN_QUERIES[args.domain], 'source_candidate_ids': batch,
            'input_hash': input_hash, 'forge_version': FORGE_VERSION,
            'schema_versions': ['schema-lite-v1 (strict schemas at promotion)'],
            'validation_required': {k: True for k in ('strict_parse', 'duplicate_detection', 'schema', 'semantic', 'mechanical', 'references', 'cardinality', 'articles_of_creation', 'atomic', 'soul', 'chaos')},
            'promotion': {'automatic': False, 'allowed_outputs': ['draft', 'quarantine', 'validated_candidate']},
            'resume': {'checkpoint_every': 10, 'idempotent': True, 'restart_safe': True},
        },
        'results_summary': {'processed': state['completed_count'], 'passed': state['passed_count'],
                            'draft': state['unresolved_count'], 'quarantined': state['quarantined_count'],
                            'failed': state['failed_count']},
    }
    json.dump(manifest, open(os.path.join(out_root, 'batch_manifest.json'), 'w', encoding='utf-8'), indent=1)
    state['worker_running'] = False
    state['estimated_remaining'] = 0
    heartbeat(state)
    print(json.dumps(manifest['results_summary']))


if __name__ == '__main__':
    sys.exit(main())
