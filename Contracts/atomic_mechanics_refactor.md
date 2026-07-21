## Atomic Mechanics Refactor - Specification and Playbook

Purpose: Convert all mechanics and mechanical_benefit entries to a fully structured, parseable schema (no compound strings). Narratives remain untouched.

Scope:
- Update these blocks in every power file:
  - base_effect.mechanics: [ ... ]
  - class_synergies[*].mechanical_benefit: [ ... ]
  - species_synergies[*].mechanical_benefit: [ ... ]
  - faction_synergies[*].mechanical_benefit: [ ... ]

General Rules:
- Replace compound strings with explicit objects.
- Preserve existing semantics; this is structural-only.
- Keep existing indentation and ordering where possible.

Common Conversions

1) Damage / Healing / Temp HP
```yaml
# before
- type: apply_damage
  value: 3d6_fire

# after
- type: apply_damage
  value:
    dice_count: 3
    dice_size: 6
    damage_type: fire
    bonus: 0        # optional flat, non-die modifier (e.g., 2d8 + 4)

# healing / temp hp use same structure
- type: apply_healing | grant_temporary_hp
  value:
    dice_count: X
    dice_size: Y
    bonus: 0        # prefer 'bonus' for flat additions
    # 'modifier' may still appear in legacy entries; new work should use 'bonus'

# example with flat bonus (e.g., 2d8 + 4 kinetic)
- type: apply_damage
  value:
    dice_count: 2
    dice_size: 8
    damage_type: kinetic
    bonus: 4
```

2) Flat bonuses and DC/attack adjustments
```yaml
# before
- type: enhance_attack
  value: +2_attack_rolls

# after
- type: enhance_attack
  value:
    bonus: 2
    stat: attack_rolls

- type: enhance_dc
  value:
    bonus: 2
    stat: saving_throw_dc
```

3) Advantage/Disadvantage and Statuses
```yaml
# before
- type: grant_advantage
  value: next_attack

# after
- type: grant_advantage
  value:
    target_stat: next_attack

# statuses
- type: apply_status
  value:
    status_type: frightened  # any named status
```

4) Distances, Areas, Ranges
```yaml
# distance
value:
  distance: 10
  unit: feet

# radius/area
value:
  radius:
    distance: 15
    unit: feet

# line/cone kept via target_scopes but distances still explicit in notes/rules if needed

# range blocks
range:
  distance: 30
  unit: feet
```

5) Durations
```yaml
# before
duration: 2_rounds

# after
duration:
  amount: 2
  unit: rounds

# named timings
duration:
  timing: start_of_turn | end_of_turn
```

6) Multipliers and Percentages
```yaml
# speed, jump, ability boosts
value:
  multiplier: 2
  target: speed | jump_distance | single_ability | two_abilities

# percent modifications
value:
  percent_bonus: 50
  target_property: shield_strength
```

7) Misc Enumerations / Effects
```yaml
# called shots, flags
value:
  target: subsystem

# reroll rules
value:
  rule: reroll_1s

# resource names
value:
  resource: shield_points | hull_points
```

Validation Checklist (per file)
- No compound strings remain in mechanics/mechanical_benefit values.
- All dice strings decomposed into dice_count/dice_size/(damage_type).
- All distances and ranges use distance + unit.
- All durations use amount + unit OR timing when appropriate.
- Statuses expressed as value.status_type.
- Bonuses expressed as bonus + stat (or flat_bonus for damage modifiers).

Examples (from this repo)
- Energy Shield (temp HP and area shield): structured dice and range.
- Flame Sweep (cone damage, lingering flames): structured dice and timing.
- Electromesh (area create, expand radius, status): effect_type, area.radius, status_type.
- Commander's Strike (grant_attack, bonuses): attack_type/bonus/stat.

Notes
- Do not change narrative, flavor_text, manifestation, guidance, or image prompts.
- Keep notes fields intact to preserve human-readable intent.
- If an effect name is ambiguous, wrap as value.effect or value.status_type without renaming semantics.

Migration Strategy
1. Batch by 10 files for review cadence.
2. Convert base_effect.mechanics first, then all synergy mechanical_benefit arrays.
3. Re-run quick grep for patterns like `:\s*[+\-]?\d+d\d+` and `_feet`/`_round` to catch leftovers.
4. Commit with concise messages per batch.


