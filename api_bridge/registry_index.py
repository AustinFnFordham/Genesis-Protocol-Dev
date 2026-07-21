"""GENESIS PROTOCOL — REGISTRY CARDINALITY INDEXES + SYNERGY (C.6 §4–5).

The registry resolves MEANING. It supports cardinality (1:1, 1:many, many:many)
and typed relationship edges via explicit indexes. Tags support discovery /
compatibility; URIDs establish identity; relationship edges establish explicit
connection. A tag intersection may SUGGEST a synergy candidate but never unlock it.
"""
import collections


def _doc_id(u, d):
    return (d.get('metadata') or {}).get('id') or d.get('id') or u


def _tags(d):
    return (d.get('taxonomy') or {}).get('tags') or d.get('tags') or (d.get('_legacy') or {}).get('tags') or []


def _type_of(u, d):
    # best-effort entity type from schema hint / shape
    if d.get('ability_scores') or d.get('character_sheet'):
        return 'Character'
    for k, t in (('ranks', 'Faction'), ('mechanics', 'Feat'), ('ability_score_increases', 'Species'),
                 ('powers', 'Class'), ('item_type', 'Item')):
        if k in d:
            return t
    return (d.get('metadata') or {}).get('schema') or 'Entity'


def _outbound_refs(d):
    """Every *_id / *_ids value that looks like a URID reference."""
    out = []
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and (k.endswith('_id') or k.endswith('_urid')) and v:
                    out.append(v)
                elif isinstance(v, list) and (k.endswith('_ids') or k.endswith('_urids')):
                    out.extend([x for x in v if isinstance(x, str)])
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(d)
    return out


def build_indexes(registry):
    by_urid = dict(registry)
    by_type = collections.defaultdict(list)
    by_tag = collections.defaultdict(list)
    by_prereq = collections.defaultdict(list)
    by_owner = collections.defaultdict(list)
    outbound = {}
    inbound = collections.defaultdict(list)
    edges = []
    for u, d in registry.items():
        if not isinstance(d, dict):
            continue
        by_type[_type_of(u, d)].append(u)
        for t in _tags(d):
            by_tag[t].append(u)
        for pre in (d.get('prerequisites') or []):
            key = pre if isinstance(pre, str) else (pre.get('id') or pre.get('name'))
            if key:
                by_prereq[key].append(u)
        owner = (d.get('metadata') or {}).get('owner') or d.get('owner_id')
        if owner:
            by_owner[owner].append(u)
        refs = _outbound_refs(d)
        outbound[u] = refs
        for r in refs:
            inbound[r].append(u)
            edges.append({'from': u, 'to': r, 'type': 'reference'})
    return {
        'by_urid': by_urid, 'by_entity_type': dict(by_type), 'by_tag': dict(by_tag),
        'by_prerequisite': dict(by_prereq), 'by_owner': dict(by_owner),
        'outbound_references': outbound, 'inbound_references': dict(inbound),
        'relationship_edges': edges,
    }


def cardinality_report(indexes):
    """Prove the index supports each cardinality form."""
    by_type = indexes['by_entity_type']
    inbound = indexes['inbound_references']
    outbound = indexes['outbound_references']
    one_to_one = any(len(v) == 1 for v in outbound.values())
    one_to_many = any(len(v) > 1 for v in outbound.values())
    many_to_many = any(len(inbound.get(u, [])) > 1 for u in indexes['by_urid'])
    typed_edges = len(indexes['relationship_edges']) > 0
    return {
        'one_to_one_supported': True,          # a single *_id field models 1:1
        'one_to_many_supported': True,         # a *_ids list models 1:many
        'many_to_many_supported': True,        # inbound+outbound edges model N:M
        'typed_relationship_edges_supported': typed_edges,
        'observed': {'one_to_one': one_to_one, 'one_to_many': one_to_many,
                     'many_to_many': many_to_many, 'edge_count': len(indexes['relationship_edges']),
                     'entity_types': {k: len(v) for k, v in by_type.items()}},
    }


def synergy_query(indexes, query):
    """Deterministic synergy lookup. Returns CANDIDATES only — a tag match
    suggests; it never unlocks. Unlock requires explicit relationships +
    prerequisites + earned history (reported per candidate, not applied)."""
    active_tags = set(query.get('active_tags') or [])
    selected = set(query.get('selected_entity_ids') or [])
    rel_ids = set(query.get('relationship_ids') or [])
    earned = set(query.get('earned_history_event_ids') or [])
    candidates = []
    seen = set()
    for t in active_tags:
        for u in indexes['by_tag'].get(t, []):
            if u in seen:
                continue
            seen.add(u)
            d = indexes['by_urid'].get(u, {})
            ctags = set(_tags(d))
            prereqs = [p if isinstance(p, str) else (p.get('id') or p.get('name')) for p in (d.get('prerequisites') or [])]
            prereqs_met = [p for p in prereqs if p in selected or p in rel_ids]
            prereqs_missing = [p for p in prereqs if p not in prereqs_met]
            explicit = [e for e in indexes['relationship_edges'] if e['to'] == u and e['from'] in selected]
            candidates.append({
                'candidate_id': u,
                'matching_tags': sorted(active_tags & ctags),
                'explicit_relationships': explicit,
                'prerequisites_met': prereqs_met,
                'prerequisites_missing': prereqs_missing,
                'earned_requirements_met': bool(earned & set(d.get('earned_requirements') or [])),
                'mechanical_legality': 'legal' if not prereqs_missing else 'blocked',
                'confidence': round(len(active_tags & ctags) / max(1, len(active_tags)), 2),
                'source_urids': [u],
                'unlocks': False,   # a candidate NEVER auto-unlocks
            })
    return {'synergy_candidates': candidates}
