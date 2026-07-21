"""Genesis UI v0.1 — data compiler.
Compiles the vertical-slice entities from Gold (fallback: WIP) into campaign_data.json.
The UI consumes ONLY this file — same contract a live API would serve.

Run: python build_data.py   (from ui/v0.1/)
"""
import json
import os
import sys

import yaml

FORGE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'SW5e_Data_Hub', 'forge_v3'))
GOLD = os.path.join(FORGE, 'data', 'gold')
WIP = os.path.join(FORGE, 'data', 'wip')

# The vertical slice: (relative path under gold/wip root)
SLICE = [
    'factions/core/fac_black_sun.yml',
    'species/species_wookiee.yml',
    'classes/guardian.yml',
    'subclasses/subclass_guardian_protector.yml',
    'locations/loc_xizors_palace.yml',
    'creatures/creature_shadowstalker_nexu.yml',
]


def load_entity(rel):
    for root, tier in ((GOLD, 'gold'), (WIP, 'wip')):
        p = os.path.join(root, rel)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data, tier, p
    return None, None, None


def get_id(e):
    return (e.get('metadata') or {}).get('id') or e.get('id') or 'unknown'


def main():
    registry = {}
    manifest = []
    for rel in SLICE:
        data, tier, path = load_entity(rel)
        if data is None:
            print(f'  !! MISSING: {rel}')
            continue
        urid = get_id(data)
        etype = rel.split('/')[0].rstrip('s')  # factions -> faction
        registry[urid] = data
        manifest.append({'urid': urid, 'entity_type': etype, 'tier': tier, 'source': os.path.relpath(path, FORGE)})
        print(f'  {tier.upper():4s} {urid} <- {rel}')

    campaign_state = {
        'campaign_id': 'campaign_vertical_slice_qa',
        'name': 'Vertical Slice QA — Shadows over Coruscant',
        'current_location_id': 'loc_xizors_palace',
        'party': [
            {
                'name': 'Rrawrkhal',
                'species_id': next((u for u in registry if 'wookiee' in u), 'species_wookiee'),
                'class_id': next((u for u in registry if 'guardian' in u and 'protector' not in u), 'class_guardian'),
                'subclass_id': next((u for u in registry if 'protector' in u), 'subclass_guardian_protector'),
                'level': 5,
                'hp': {'current': 42, 'max': 47},
                'ffg_pools': {'duty': 20, 'obligation': 35, 'morality': 55},
            }
        ],
        'active_threats': [get_id(registry[u]) if False else u for u in registry if 'nexu' in u],
        'faction_watch': [u for u in registry if u.startswith('fac_')],
    }

    out = {
        'generated': True,
        'pipeline': 'Genesis Protocol / Forge V3',
        'manifest': manifest,
        'registry': registry,
        'campaign_state': campaign_state,
    }
    dst = os.path.join(os.path.dirname(__file__), 'campaign_data.json')
    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    gold_n = sum(1 for m in manifest if m['tier'] == 'gold')
    print(f'\ncampaign_data.json written: {len(manifest)} entities ({gold_n} gold, {len(manifest)-gold_n} wip)')


if __name__ == '__main__':
    sys.exit(main())
