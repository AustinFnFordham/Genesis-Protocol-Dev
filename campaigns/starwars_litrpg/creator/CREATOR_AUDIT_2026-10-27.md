# Character creator audit (2026-10-27)

Goal: a full creator (species, background, class, subclass) built from valid, schema-checked data. Files we work out together become the canon examples for the Forge.

## What exists
- `schema/CharacterCreator.schema.json`: a 7-line skeleton of ordered steps (`data_source`, `player_choice`). Needs to be filled out.
- `schema/{Species,Class,Subclass,Background,Character}.schema.json`: real schemas with required fields.
- `registry/candidate_builds/`: Forge drafts, each file wrapped as `{record, validation}`.
- `registry/golden_slice/global_definitions/`: the only hand-validated set (Echani, Human, Sentinel, Operative, Jedi/Smuggler backgrounds, Sentry subclass, powers, features, items).
- Reference build: Aero (`api_bridge/gm/aero_character_runtime.yml`), SW5e-style: six ability scores, proficiency bonus, HP, Strain, Force Points.

## Schema validation of candidate records (record only, envelope stripped)
| Set | Files | Pass | Main failures |
|---|---|---|---|
| Species drafts | 42 | 13 | missing `starting_xp`, `description`, `ability_score_increases`, `contextual_modifiers` |
| Class drafts | 63 | 0 | missing `era`, `rarity`, `narrative`; 53 lack `hit_die` |
| Class/subclass validated_candidate | 37 | 0 | same; 15 are subclasses being checked against the Class schema |
| Backgrounds | 33 | not checked | validator crashed on the Background schema itself (bad `$id` handling) |

## Other findings
- Species drafts carry `validation.kind: "class"`. Mislabeled.
- Duplicates to reconcile before promotion: `human`, `species_human`, `human_*`; `wookiee`, `species_wookiee`; `droid` variants.
- No subclass files exist for most classes; the 15 subclass records sit under classes.

## Proposed promotion rule
A file becomes a canon example only if it (1) validates against its schema with the envelope stripped, (2) has no unresolved duplicate, (3) sets `validation.promotion` and keeps provenance. Promote by copy, never move or delete. Keep a manifest of promoted files.
