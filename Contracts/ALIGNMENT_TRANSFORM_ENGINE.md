# Alignment Transform Engine

## Purpose
Allow features, powers, and status effects to transform between mirrored light/dark (or neutral) variants based on a character's `alignment_score`. This enables redemption/fall arcs without changing subclass or respecing talent investments.

## Core Data Contract
- Each transformable node includes a `corruption_transform` block:
  - `can_corrupt`/`can_purify`: booleans
  - `corrupts_to_feature_id`/`purifies_to_feature_id`: target IDs
  - `retains_mastery`: whether XP/mastery persists after transform

Example (light → dark):
```yaml
corruption_transform:
  can_corrupt: true
  corrupts_to_feature_id: "feature_beast_control_rig"
  retains_mastery: true
```

## Engine Flow
1. Monitor `alignment_score` and threshold crossings (default bands: Dark ≤ 30, Neutral 31–69, Light ≥ 70; project-specific).
2. On crossing into a new band, scan owned features for `corruption_transform`.
3. If a transform applies, swap the feature ID to its counterpart.
4. If `retains_mastery: true`, preserve spent XP/mastery flags.
5. Emit UI transition event to animate the card change.

## UI Transition Hints (optional)
Features may include a `ui_transition` block to guide visuals:
```yaml
ui_transition:
  animation: "card_flicker_to_glow"
  sfx: "dark_to_light_chime"
```

## LLM-GM Guidance
- Narrate the change as internal evolution (empathy → control, or vice versa).
- Offer scenes that foreshadow the shift near thresholds.
- Ensure mechanical swap respects action economy and intended role.

## Validation Rules
- Transforms must be reciprocal pairs where narratively appropriate.
- Do not create power spikes on swap; keep roles parallel.
- Document thresholds and any subclass-specific exceptions.

## Registry & Discoverability
- Maintain mirrored pairs in feature directories with consistent IDs.
- Use subclass talent trees to reference the light/dark IDs; the engine handles runtime swapping.

## Examples
- `feature_beast_bond_empathy` ↔ `feature_beast_control_rig`
- `feature_beast_guardian_aura` ↔ `feature_beast_alpha_intimidation`
- `feature_beast_shared_senses` ↔ `feature_beast_blood_scent`


