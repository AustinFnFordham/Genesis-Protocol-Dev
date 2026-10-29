# Creator shortlist (2026-10-27, status refreshed by shortlist_status.py)

Era: hidden (GM-chosen). Picks are era-neutral. Status = schema validation with envelope stripped and cross-file refs resolved.

## Species

| Pick | Status | Missing required | Other errors |
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

| Pick | Status | Missing required | Other errors |
|---|---|---|---|
| guardian | gaps | - | 4 |
| sentinel | gaps | class_identity_profile, era, narrative, rarity | 1 |
| consular | PASS | - | 0 |
| soldier | PASS | - | 0 |
| scout | gaps | class_identity_profile, era, narrative, rarity | 1 |
| scoundrel | gaps | class_identity_profile, era, narrative, rarity | 1 |
| smuggler | gaps | era, narrative, proficiencies, rarity | 1 |
| bounty_hunter | PASS | - | 0 |
| engineer | gaps | proficiencies | 1 |
| spy | gaps | era, narrative, primary_ability, rarity | 1 |

## Subclass

| Pick | Status | Missing required | Other errors |
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

| Pick | Status | Missing required | Other errors |
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

Variants kept with parent species: `zabrak_dathomirian`, `togruta_nightsister`.

## Structural findings
1. ~~Class schema required `level_progression`~~ Fixed 2026-10-29: `progression_tree` added, one of the two is required.
2. Golden-slice records use `urid` + an envelope instead of `id`. Rule proposed: `urid = <entity_type>_<id>`, derived, never hand-written.
3. The 63 class drafts are specializations (`class_id` parent) mislabeled `kind: class`. Target schema is Subclass.
4. Backgrounds embed a `feature` that must satisfy CharacterClassFeature; all drafts are lighter than required.
5. Era is almost never set on species.
