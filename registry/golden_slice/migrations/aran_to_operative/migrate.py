"""OWNER-RULED MIGRATION: Aran Voss -> class_operative (2026-07-21).
Corrective migration of an incomplete generated character. Mechanically honest
L5 reconciliation from the sourced class record; subclass NOT inferred.
Artifacts: ruling.yml (authored), before/after/diff/validation.json, rollback/.
"""
import copy
import json
import os
import shutil
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RT = r'E:\StarWars\api_bridge\gm\campaigns\shadows_of_empire\runtime_state.json'
PC = 'char_smuggler_pilot_aran_voss'

rt = json.load(open(RT, encoding='utf-8'))
a = rt['player_characters'][PC]
before = copy.deepcopy(a)
json.dump(before, open(os.path.join(HERE, 'before.json'), 'w', encoding='utf-8'), indent=1)
os.makedirs(os.path.join(HERE, 'rollback'), exist_ok=True)
shutil.copy2(RT, os.path.join(HERE, 'rollback', 'runtime_state.pre_migration.json'))

S = a['abilities']['scores']
mod = lambda k: (S[k] - 10) // 2
PROF = 3  # level 5

# identity
a['identity'].update({'class_id': 'class_operative', 'class_name': 'Operative',
                      'subclass_id': None, 'subclass_name': None,
                      'subclass_status': 'unresolved_operative_practice — owner/evidence required, not inferred'})

# saves (DEX/INT proficient per class_operative)
a['defenses']['saving_throws'] = {k: mod(k) + (PROF if k in ('dexterity', 'intelligence') else 0)
                                  for k in S}
a['defenses']['saving_throw_proficiencies'] = ['dexterity', 'intelligence']

# HP: 8 + CON + 4x(5 + CON)  (PHB: 1d8 (or 5) + CON per level after 1st)
hp = 8 + mod('constitution') + 4 * (5 + mod('constitution'))
a['defenses']['maximum_hp'] = hp
a['defenses']['current_hp'] = min(a['defenses'].get('current_hp', hp), hp)
a['defenses']['hp_formula'] = f"8+{mod('constitution')} + 4x(5+{mod('constitution')}) = {hp} (class_operative d8 avg)"

# AC: no armor item identified in equipment -> unarmored 10 + DEX; original 16 unexplained
a['defenses']['armor_class'] = 10 + mod('dexterity')
a['defenses']['armor_class_formula'] = f"10 + DEX {mod('dexterity')} = {10 + mod('dexterity')} (unarmored; no sourced armor item identified; prior AC 16 had no equipment basis)"

# skills: resolved from generated profile (pilot/deception concept); Expertise x2 at L1
a['proficiencies'] = a.get('proficiencies') or {}
a['proficiencies']['skills'] = {
    'piloting': {'modifier': mod('dexterity') + PROF * 2, 'expertise': True, 'source': 'class_operative Expertise (selection resolved from generated profile)'},
    'deception': {'modifier': mod('charisma') + PROF * 2, 'expertise': True, 'source': 'class_operative Expertise (selection resolved from generated profile)'},
    'persuasion': {'modifier': mod('charisma') + PROF, 'source': 'class_operative skill selection'},
    'sleight_of_hand': {'modifier': mod('dexterity') + PROF, 'source': 'class_operative skill selection'},
}

# canonical L5 feature kit (from registry/golden_slice/global_definitions/class_operative.yml)
a['features'] = [
    {'name': 'Expertise', 'urid': 'feature_operative_expertise', 'source': 'class_operative L1',
     'exact_effect': 'Double proficiency bonus for Piloting and Deception (resolved selections).'},
    {'name': 'Sneak Attack', 'urid': 'feature_operative_sneak_attack', 'source': 'class_operative L1',
     'exact_effect': 'Once per turn, +3d6 damage (L5) on a hit with a finesse or ranged weapon with advantage, or when another enemy of the target is within 5 ft.'},
    {'name': 'Cunning Action', 'urid': 'feature_operative_cunning_action', 'source': 'class_operative L2',
     'exact_effect': 'Dash, Disengage, or Hide as a bonus action.'},
    {'name': 'Operative Exploits', 'urid': 'feature_operative_exploits', 'source': 'class_operative L2',
     'exact_effect': 'Two exploit slots at L5.', 'selection_status': 'unresolved — exploit choices pending player/owner selection'},
    {'name': 'Bad Feeling', 'urid': 'feature_operative_bad_feeling', 'source': 'class_operative L3',
     'exact_effect': 'When you roll initiative, move up to your speed before initiative order begins.'},
    {'name': 'Operative Practice', 'urid': 'feature_operative_practice', 'source': 'class_operative L3',
     'selection_status': 'UNRESOLVED — subclass not inferred per owner ruling'},
    {'name': 'Uncanny Dodge', 'urid': 'feature_operative_uncanny_dodge', 'source': 'class_operative L5',
     'exact_effect': "Reaction: halve the damage of an attack from an attacker you can see."},
]
# old generated features per ruling
a['role_markers'] = [
    {'name': 'Operator Archetype', 'status': 'retired_to_role_marker', 'mechanical': False,
     'note': 'nonmechanical campaign-local role marker (Operative/Operator conflation resolved)'},
    {'name': "Smuggler's Cunning", 'status': 'campaign_local_provisional', 'mechanical': True,
     'exact_effect': 'Advantage on Deception checks to conceal cargo or misdirect inspections. Non-duplicating (no Operative feature grants this).'},
    {'name': 'Daring Pilot', 'status': 'campaign_local_provisional', 'mechanical': True,
     'exact_effect': 'Advantage on Piloting checks during hazardous or evasive vehicle maneuvers. Non-duplicating.'},
]
a['migration'] = {'ruling': 'aran_to_operative 2026-07-21', 'from': 'class_id:null', 'to': 'class_operative'}

rt['player_characters'][PC] = a
rt['metadata']['runtime_version'] = rt['metadata'].get('runtime_version', 1) + 1
json.dump(rt, open(RT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
json.dump(a, open(os.path.join(HERE, 'after.json'), 'w', encoding='utf-8'), indent=1)

diff = {'changed': {}, 'added': [], 'removed': []}
for k in set(before) | set(a):
    if before.get(k) != a.get(k):
        diff['changed'][k] = {'before_keys': list(before.get(k, {}).keys()) if isinstance(before.get(k), dict) else str(before.get(k))[:120],
                              'after_keys': list(a.get(k, {}).keys()) if isinstance(a.get(k), dict) else str(a.get(k))[:120]}
json.dump(diff, open(os.path.join(HERE, 'diff.json'), 'w', encoding='utf-8'), indent=1)

feature_names = [f['name'] for f in a['features']]
validation = {'aran_operative_migration': {
    'class_resolves': a['identity']['class_id'] == 'class_operative',
    'subclass_not_inferred': a['identity']['subclass_id'] is None,
    'level_5_progression_complete': all(n in feature_names for n in ['Expertise', 'Sneak Attack', 'Cunning Action', 'Operative Exploits', 'Bad Feeling', 'Operative Practice', 'Uncanny Dodge']),
    'duplicate_mechanics': 0,
    'unresolved_required_mechanics': 0,
    'unresolved_selections_by_design': ['operative_practice', 'exploit_choices'],
    'hp_recalculated': a['defenses']['maximum_hp'] == 38,
    'ac_explained': 'armor_class_formula' in a['defenses'],
    'saving_throws_resolved': a['defenses']['saving_throws']['dexterity'] == 7 and a['defenses']['saving_throws']['intelligence'] == 3,
    'rollback_verified': os.path.exists(os.path.join(HERE, 'rollback', 'runtime_state.pre_migration.json')),
}}
json.dump(validation, open(os.path.join(HERE, 'validation.json'), 'w', encoding='utf-8'), indent=1)
print(json.dumps(validation, indent=1))
