# Creator shortlist (2026-10-27)

Era: Old Republic, Cold War period after the Treaty of Coruscant (roughly 3,650-3,640 BBY).
10 per file type, picked for likelihood of play and era fit. Status from `validate_candidates.py` (envelope stripped, cross-file refs resolved).
PASS = schema-valid. Gaps list the missing required fields; 'other' counts type/shape errors.

## Species

| Pick | Status | Missing required fields | Other errors |
|---|---|---|---|
| human | PASS | - | 0 |
| twilek | PASS | - | 0 |
| zabrak | PASS | - | 0 |
| wookiee | PASS | - | 0 |
| echani | gaps | - | 2 |
| chiss | gaps | - | 2 |
| togruta | gaps | - | 1 |
| miraluka | gaps | - | 1 |
| cathar | gaps | - | 1 |
| bothan | PASS | - | 0 |

## Class

| Pick | Status | Missing required fields | Other errors |
|---|---|---|---|
| guardian | gaps | level_progression | 4 |
| sentinel | gaps | class_identity_profile, era, level_progression, narrative, rarity | 1 |
| consular | gaps | level_progression | 0 |
| soldier | gaps | level_progression | 0 |
| scout | gaps | class_identity_profile, era, level_progression, narrative, rarity | 1 |
| scoundrel | gaps | class_identity_profile, era, level_progression, narrative, rarity | 1 |
| smuggler | gaps | era, level_progression, narrative, proficiencies, rarity | 1 |
| bounty_hunter | gaps | level_progression | 0 |
| engineer | gaps | level_progression, proficiencies | 1 |
| spy | gaps | era, level_progression, narrative, primary_ability, rarity | 1 |

## Subclass

| Pick | Status | Missing required fields | Other errors |
|---|---|---|---|
| sentry | gaps | alignment_theme, class_id, class_identity_profile, id, llm_guidance, narrative, talent_tree, talent_tree_theme | 0 |
| guardian_force_warrior | gaps | alignment_theme, class_identity_profile, llm_guidance, narrative, talent_tree, talent_tree_theme | 0 |
| soresu_defender | gaps | alignment_theme, class_identity_profile, llm_guidance, narrative, talent_tree, talent_tree_theme | 0 |
| niman_disciple | gaps | alignment_theme, class_identity_profile, llm_guidance, narrative, talent_tree, talent_tree_theme | 0 |
| sage | gaps | alignment_theme, class_identity_profile, llm_guidance, narrative, talent_tree, talent_tree_theme | 0 |
| assassin | gaps | alignment_theme, class_identity_profile, llm_guidance, narrative, talent_tree_theme | 0 |
| survivalist | gaps | alignment_theme, class_identity_profile, llm_guidance, narrative, talent_tree, talent_tree_theme | 0 |
| mercenary_soldier | gaps | alignment_theme, class_identity_profile, llm_guidance, narrative, talent_tree, talent_tree_theme | 0 |
| slicer | gaps | alignment_theme, class_identity_profile, llm_guidance, narrative, talent_tree, talent_tree_theme | 0 |
| fringer | gaps | alignment_theme, class_identity_profile, llm_guidance, narrative, talent_tree, talent_tree_theme | 0 |

## Background

| Pick | Status | Missing required fields | Other errors |
|---|---|---|---|
| jedi | gaps | - | 6 |
| soldier | gaps | background_type, image_generation, narrative, ui | 6 |
| smuggler | gaps | background_type, image_generation, narrative, ui | 6 |
| scoundrel | gaps | background_type, image_generation, narrative, ui | 6 |
| outlaw | gaps | background_type, image_generation, narrative, ui | 6 |
| bounty_hunter | gaps | background_type, image_generation, narrative, ui | 6 |
| scholar | gaps | background_type, image_generation, narrative, ui | 5 |
| explorer | gaps | background_type, image_generation, narrative, ui | 5 |
| mechanic | gaps | background_type, image_generation, narrative, ui | 5 |
| diplomat | gaps | background_type, image_generation, narrative, ui | 6 |

Variants kept with their parent species: `zabrak_dathomirian`, `togruta_nightsister`.

## Structural findings (need a decision before workshopping)
1. **Schema and data disagree on shape.** `schema/Class.schema.json` requires `level_progression`, `class_identity_profile`, `primary_ability`; the data uses `progression_tree` and `primary_resource`. Either the schema is stale or the data is.
2. **Identity key differs.** Schemas require `id`; `golden_slice` records use `urid` plus an envelope (`entity_type`, `authority_lane`, `validation_status`).
3. **Subclasses are mislabeled.** The 63 drafts tagged `kind: class` are all specializations with a `class_id` parent. The Subclass schema is the right target.
4. **Backgrounds** embed a `feature` that must satisfy `CharacterClassFeature` (needs `id`, `era`, `rarity`, `narrative`, `connections`); every draft's feature is lighter than that.
5. **Era is almost never set** on species, so nothing can be filtered by era yet.
