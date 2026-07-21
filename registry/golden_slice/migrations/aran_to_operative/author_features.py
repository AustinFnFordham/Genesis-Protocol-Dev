"""Author the 7 canonical Operative feature lane records (from class_operative.yml/PHB)."""
import os

D = r'E:\StarWars\registry\golden_slice\global_definitions'
FEATS = {
    'feature_operative_expertise': ('Expertise', 'class_operative L1/L6',
        'Choose two proficiencies (skills or tools); double proficiency bonus with them. Two more selections at 6th level.'),
    'feature_operative_sneak_attack': ('Sneak Attack', 'class_operative L1',
        'Once per turn, deal extra damage (1d6 scaling to 10d6 per the class table) on a hit with a finesse or ranged weapon when you have advantage, or when another enemy of the target is within 5 ft, that enemy is not incapacitated, and you lack disadvantage.'),
    'feature_operative_cunning_action': ('Cunning Action', 'class_operative L2',
        'Take the Dash, Disengage, or Hide action as a bonus action on each of your turns.'),
    'feature_operative_exploits': ('Operative Exploits', 'class_operative L2',
        'Adopt two exploits; additional exploits at 7th, 13th, and 17th level.'),
    'feature_operative_bad_feeling': ('Bad Feeling', 'class_operative L3',
        'When you roll for initiative, you can move up to your speed before the initiative order begins.'),
    'feature_operative_practice': ('Operative Practice', 'class_operative L3',
        'Choose an Operative Practice granting features at 3rd, 9th, 13th, and 17th level.'),
    'feature_operative_uncanny_dodge': ('Uncanny Dodge', 'class_operative L5',
        "When an attacker you can see deals damage to you with an attack, use your reaction to halve the attack's damage against you."),
}
TPL = """urid: {urid}
entity_type: ClassFeature
name: {name}
status: validated
authority_lane: golden_slice
class_id: class_operative
provenance:
  primary_source: SW5e_Data_Hub/forge_v3/backend/clean_source/SW5e_PHB.txt (p.108-109)
  granted_by: '{granted}'
mechanics:
  exact_effect: >-
    {effect}
"""
for urid, (name, granted, effect) in FEATS.items():
    open(os.path.join(D, f'{urid}.yml'), 'w', encoding='utf-8').write(
        TPL.format(urid=urid, name=name, granted=granted, effect=effect))
print(f'authored {len(FEATS)} feature lane records')
