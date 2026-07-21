"""GENESIS — SOURCE-CORPUS REGISTRY BUILDER (indexing & discovery layer).

Inventories EVERY discoverable file across all data generations WITHOUT
moving, flattening, or deleting anything. Three layers: file registry,
entity-candidate registry, canonical registry (approved lanes only —
nothing is auto-promoted). Deterministic and reproducible: same corpus
in, same build out (build id = hash of the sorted file-hash list).

Outputs: registry/corpus_registry.sqlite + registry/exports/*.ndjson|json
Run: $env:PYTHONUTF8='1'; python registry/build_corpus_registry.py
"""
import hashlib
import json
import os
import sqlite3
import sys

ROOT = r'E:\StarWars'
OUT = os.path.join(ROOT, 'registry')
EXP = os.path.join(OUT, 'exports')
os.makedirs(EXP, exist_ok=True)

SOURCE_ROOTS = [  # every known data generation; originals stay in place
    ('SW5e_Data_Hub/source_data', 'raw_source'),
    ('SW5e_Data_Hub/forge_v3/backend', 'forge_v3_backend'),
    ('SW5e_Data_Hub/forge_v3/data', 'forge_v3_data'),
    ('SW5e_Data_Hub/forge_v3/schemas', 'schemas'),
    ('SW5e_Data_Hub/docs', 'docs_systems'),
    ('SW5e_Data_Hub/data', 'hub_data'),
    ('schema', 'legacy_schema'),
    ('registry/golden_slice', 'golden_slice'),
    ('api_bridge/gm', 'campaign_local_runtime'),
    ('_QUARANTINE', 'quarantine'),
    ('_ARCHIVE', 'archive'),
]
STAGE_BY_HINT = {'quarantine': 'quarantine', 'archive': 'deprecated', 'golden_slice': 'validated',
                 'forge_v3_data': 'forge_output', 'campaign_local_runtime': 'campaign_local'}
DATA_EXT = {'.yml', '.yaml', '.json', '.txt', '.md', '.ndjson', '.jsonl', '.csv'}
SKIP_DIRS = {'node_modules', '.venv', '__pycache__', '.git', 'Lib', 'site-packages'}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def try_parse(path, ext):
    try:
        if ext in ('.yml', '.yaml'):
            import yaml
            with open(path, encoding='utf-8', errors='replace') as f:
                return yaml.safe_load(f), 'ok'
        if ext == '.json':
            return json.load(open(path, encoding='utf-8', errors='replace')), 'ok'
    except Exception as e:
        return None, f'parse_failed: {str(e)[:120]}'
    return None, 'not_structured'


def entity_candidates(doc, pointer):
    """Extract entity candidates from a parsed document (authority-neutral)."""
    out = []
    def walk(d, depth=0):
        if depth > 4 or not isinstance(d, dict):
            return
        urid = d.get('urid') or (d.get('metadata') or {}).get('id') if isinstance(d.get('metadata'), dict) else d.get('urid')
        eid = urid or d.get('id') or d.get('class_id') or d.get('species_id')
        name = d.get('name') or (d.get('metadata') or {}).get('name') if isinstance(d.get('metadata'), dict) else d.get('name')
        etype = d.get('entity_type') or d.get('type')
        if (eid or name) and isinstance(eid or name, str):
            sig = sorted(k for k in d.keys() if k in ('hit_die', 'progression', 'mechanics', 'ability_scores', 'features', 'powers', 'equipment', 'damage', 'armor_class'))
            out.append({'entity_name': name if isinstance(name, str) else None,
                        'proposed_urid': eid if isinstance(eid, str) else None,
                        'entity_type': etype if isinstance(etype, str) else None,
                        'aliases': [], 'tags': (d.get('tags') if isinstance(d.get('tags'), list) else [])[:10],
                        'source_pointer': pointer,
                        'mechanical_signature': sig,
                        'validation_status': 'candidate', 'authority_confidence': 'neutral'})
        for v in list(d.values())[:40]:
            if isinstance(v, dict):
                walk(v, depth + 1)
            elif isinstance(v, list):
                for it in v[:60]:
                    walk(it, depth + 1) if isinstance(it, dict) else None
    walk(doc)
    return out[:50]


def main():
    files, candidates = [], []
    for rel_root, root_tag in SOURCE_ROOTS:
        base = os.path.join(ROOT, rel_root)
        if not os.path.isdir(base):
            continue
        for dirpath, dirs, fnames in os.walk(base):
            dirs[:] = [d for d in sorted(dirs) if d not in SKIP_DIRS]
            for fn in sorted(fnames):
                p = os.path.join(dirpath, fn)
                ext = os.path.splitext(fn)[1].lower()
                if ext not in DATA_EXT:
                    continue
                try:
                    h = sha256(p)
                except Exception:
                    continue
                rel = os.path.relpath(p, ROOT).replace('\\', '/')
                stage = STAGE_BY_HINT.get(root_tag, 'source')
                if 'fixture' in rel.lower() or 'sandbox' in rel.lower():
                    stage = 'fixture'
                doc, parse_status = try_parse(p, ext)
                rec = {'path': rel, 'source_root': root_tag, 'hash': h, 'stage': stage,
                       'format': ext.lstrip('.'), 'parse_status': parse_status,
                       'size': os.path.getsize(p)}
                files.append(rec)
                if doc is not None:
                    candidates.extend(entity_candidates(doc, rel))
    # duplicate grouping (exact by hash; entity by urid)
    byhash, byurid = {}, {}
    for f in files:
        byhash.setdefault(f['hash'], []).append(f['path'])
    for c in candidates:
        if c['proposed_urid']:
            byurid.setdefault(c['proposed_urid'], []).append(c['source_pointer'])
    dup_groups = [{'type': 'exact_duplicate', 'hash': h, 'paths': ps} for h, ps in byhash.items() if len(ps) > 1]
    urid_dups = [{'type': 'entity_duplicate', 'urid': u, 'sources': sorted(set(ps))} for u, ps in byurid.items() if len(set(ps)) > 1]
    for f in files:
        f['duplicate_group'] = f['hash'] if len(byhash[f['hash']]) > 1 else None
    conflicts = [d for d in urid_dups if len(d['sources']) > 3]
    parse_fails = [f for f in files if f['parse_status'].startswith('parse_failed')]

    # canonical layer = approved lanes only (golden_slice validated records)
    canonical = [c for c in candidates if c['source_pointer'].startswith('registry/golden_slice') and c['proposed_urid']]
    for c in canonical:
        c['validation_status'] = 'lane_validated'
        c['authority_lane'] = 'golden_slice'

    build_id = hashlib.sha256('\n'.join(sorted(f['hash'] for f in files)).encode()).hexdigest()[:16]

    # SQLite
    db = sqlite3.connect(os.path.join(OUT, 'corpus_registry.sqlite'))
    db.executescript('''
      DROP TABLE IF EXISTS files; DROP TABLE IF EXISTS entity_candidates; DROP TABLE IF EXISTS canonical;
      CREATE TABLE files(path TEXT PRIMARY KEY, source_root TEXT, hash TEXT, stage TEXT, format TEXT, parse_status TEXT, size INT, duplicate_group TEXT);
      CREATE TABLE entity_candidates(entity_name TEXT, proposed_urid TEXT, entity_type TEXT, source_pointer TEXT, mechanical_signature TEXT, validation_status TEXT);
      CREATE TABLE canonical(proposed_urid TEXT PRIMARY KEY, entity_name TEXT, entity_type TEXT, source_pointer TEXT, authority_lane TEXT);
      CREATE INDEX ix_cand_name ON entity_candidates(entity_name); CREATE INDEX ix_cand_urid ON entity_candidates(proposed_urid);
    ''')
    db.executemany('INSERT INTO files VALUES(?,?,?,?,?,?,?,?)',
                   [(f['path'], f['source_root'], f['hash'], f['stage'], f['format'], f['parse_status'], f['size'], f['duplicate_group']) for f in files])
    db.executemany('INSERT INTO entity_candidates VALUES(?,?,?,?,?,?)',
                   [(c['entity_name'], c['proposed_urid'], c['entity_type'], c['source_pointer'], json.dumps(c['mechanical_signature']), c['validation_status']) for c in candidates])
    seen = set()
    for c in canonical:
        if c['proposed_urid'] not in seen:
            seen.add(c['proposed_urid'])
            db.execute('INSERT OR IGNORE INTO canonical VALUES(?,?,?,?,?)',
                       (c['proposed_urid'], c['entity_name'], c['entity_type'], c['source_pointer'], 'golden_slice'))
    db.commit(); db.close()

    def nd(name, rows):
        with open(os.path.join(EXP, name), 'w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    nd('files.ndjson', files)
    nd('entity_candidates.ndjson', candidates)
    nd('duplicates.ndjson', dup_groups + urid_dups)
    nd('conflicts.ndjson', conflicts)
    nd('unresolved_references.ndjson', [{'urid': 'class_id:null', 'holder': 'char_smuggler_pilot_aran_voss', 'note': 'awaiting owner ruling (aran_class_review.yml)'}])
    json.dump({}, open(os.path.join(EXP, 'aliases.json'), 'w'))  # populated by review passes
    json.dump({'registry_build_id': build_id, 'files': len(files), 'entity_candidates': len(candidates),
               'canonical': len(seen), 'exact_duplicate_groups': len(dup_groups), 'entity_duplicate_urids': len(urid_dups),
               'parse_failures': len(parse_fails), 'deterministic': True,
               'auto_promotion': 'none — canonical layer mirrors approved golden_slice lane only'},
              open(os.path.join(EXP, 'build_manifest.json'), 'w'), indent=1)
    print(f'build {build_id}: files={len(files)} candidates={len(candidates)} canonical={len(seen)} '
          f'dup_groups={len(dup_groups)} urid_dups={len(urid_dups)} parse_fails={len(parse_fails)}')
    # acceptance: Operative discovery
    db = sqlite3.connect(os.path.join(OUT, 'corpus_registry.sqlite'))
    n = db.execute("SELECT COUNT(*) FROM entity_candidates WHERE entity_name LIKE '%perative%' OR proposed_urid LIKE '%operative%'").fetchone()[0]
    fp = db.execute("SELECT COUNT(*) FROM files WHERE path LIKE '%operative%'").fetchone()[0]
    print(f'operative discovery: {n} candidates, {fp} files')


if __name__ == '__main__':
    sys.exit(main())
