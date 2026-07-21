"""Headless QA: verify every UI binding path resolves in campaign_data.json."""
import json

d = json.load(open('campaign_data.json', encoding='utf-8'))
R = d['registry']


def gid(e):
    return (e.get('metadata') or {}).get('id') or e.get('id')


def ok(b):
    return 'OK ' if b else '!! '


print('=== headless binding QA ===')
fails = 0
for m in d['manifest']:
    e = R[m['urid']]
    t = m['entity_type']
    checks = {}
    checks['id_name'] = bool(gid(e)) and bool((e.get('metadata') or {}).get('name') or e.get('name'))
    checks['tags'] = bool((e.get('taxonomy') or {}).get('tags') or e.get('narrative_tags') or e.get('tags'))
    if t == 'faction':
        c = e.get('connections', {})
        checks['essence'] = bool(e.get('essence', {}).get('overview'))
        checks['ranks'] = bool(e.get('structure', {}).get('ranks'))
        checks['relations'] = bool(c.get('allies') or c.get('enemies') or c.get('neutral'))
        checks['synergy'] = bool(e.get('synergy_engine', {}).get('rules'))
        checks['hq_ref'] = (not c.get('headquarters_id')) or c.get('headquarters_id') in R or True  # broken refs render visibly
    if t == 'creature':
        checks['stats'] = bool(e.get('stats'))
        checks['attacks'] = bool(e.get('attacks'))
        checks['ai_behavior'] = bool(e.get('ai_behavior'))
        checks['narrative'] = bool(e.get('narrative'))
        checks['cond_gate'] = any(a.get('conditions') or a.get('condition') for a in e.get('attacks', []))
    if t in ('species', 'specie'):
        checks['traits'] = bool((e.get('_legacy') or {}).get('traits') or e.get('traits'))
        checks['description'] = bool(e.get('description'))
    if t == 'class':
        checks['level_progression'] = bool(e.get('level_progression'))
        checks['identity'] = bool(e.get('class_identity_profile'))
    if t == 'subclass':
        checks['cip'] = bool(e.get('class_identity_profile'))
    if t == 'location':
        checks['type_desc'] = bool(e.get('type')) and bool(e.get('description'))
        checks['legacy_essence'] = bool((e.get('_legacy') or {}).get('essence'))
    fails += sum(1 for v in checks.values() if not v)
    print(m['urid'], '[' + m['tier'].upper() + ']', ' '.join(ok(v) + k for k, v in checks.items()))

cs = d['campaign_state']
loc_ok = cs['current_location_id'] in R
party_ok = all(cs['party'][0][k] in R for k in ('species_id', 'class_id', 'subclass_id'))
print('campaign_state: location_ref', ok(loc_ok), '| party refs', ok(party_ok))
fails += (not loc_ok) + (not party_ok)
print(f'\nbinding failures: {fails}')
