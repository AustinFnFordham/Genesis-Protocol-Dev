# Rhowarr — Atomic starter sheet (stage 2)
Revision 1 | commit_ready: false | runtime_authorized: false | campaign: unassigned
Companion to [Soul dossier](soul-dossier.md), preserved unchanged. Audit basis: repository tree at 89b824a1cfa61c143f15db33266fe3913abdbece (1,473 entries, not truncated). This is a development worksheet, not a Character or Character Runtime instance. Locked means player-authored selection, not promoted mechanical authority.

## 1. Locked selections
Rhowarr; Trandoshan; intended Berserker level 1; Bounty Hunter **background** (not Bounty Hunter class); Force-insensitive; STR/DEX/CON priorities; stun cuffs and musical instrument (electro guitar); additional language Huttese; narrative ownership of armor, gauntlets, Warfang and Doom Talon; dormant tattoo enhancement concept. Subclass not selected. No campaign, era, faction membership or current location assigned. Corrected point-buy allocation below remains pending explicit confirmation because the original approved array was subsequently corrected.

## 2. Attributes
Repository rule: campaigns/starwars_litrpg/creator/DESIGN_DECISIONS.md, Decided 2026-10-27: 27 points, base 8–15, costs 0/1/2/3/4/5/7/9 for 8–15, species increases after purchase. This confirms the method, not promotion of species effects.

| Ability | Base | Cost | Draft species increase | Projected score | Conventional d20 modifier (conditional) |
|---|---:|---:|---:|---:|---:|
| STR | 15 | 9 | 2 | 17 | +3 |
| DEX | 14 | 7 | 0 | 14 | +2 |
| CON | 14 | 7 | 0 | 14 | +2 |
| INT | 10 | 2 | 0 | 10 | 0 |
| WIS | 10 | 2 | 1 | 11 | 0 |
| CHA | 8 | 0 | 0 | 8 | -1 |
| Total cost | | 27 | | | |

Arithmetic checked: 9+7+7+2+2+0=27. Modifier preview uses floor((score-10)/2), not a finalized runtime derivation. No dice rolled. Original array with INT12 and base WIS10 actually cost 29, not 30 as previously stated; corrected array above is valid point-buy. No silent change to Soul dossier.

## 3. Species and background: source-supported candidates, NOT activated
S1: registry/candidate_builds/cand_species_f0919a09ca17ebcf/draft/trandoshan.json (blob cff1b8a7baa09b37d069e9e4edbd142ee68486b9)
- STR +2, WIS +1; speed 30 (feet interpretation pending runtime mapping); Medium; Basic, Dosh; starting_xp 105; base_hp 12; base_strain 9. Base quantities are not final HP, strain or XP balances.
- Crushing Claws: modify_unarmed_strike, 1d6 slashing. No attack bonus, ability damage addition, stacking with gauntlets or action grant inferred.
- Trophy Sense: advantage on Survival to track wounded creatures only.
- Regenerative Scales: modify_hp_per_level value 1 conditioned on event=rest_end and rest_cooldown=short. Effect naming and trigger conflict need adjudication; do not implement a permanent HP increase or healing rate from this.
- Optional cultural, environmental, corruption and higher-level features not selected or granted. Crimson is not listed among scale colors; red eyes are listed. Preserve approved cosmetic exception, no benefit. Height approx 2.1844m within 1.8–2.2m listed range.

B1: registry/candidate_builds/cand_backgrounds_516841038a6595a7/draft/background_bounty_hunter.json (blob 46fae9f988a51dbe492be2d614c0a40556edc8dc)
- Skills: intimidation, investigation. Tool choices count 2: stun_cuffs and musical_instrument explicitly listed; chosen instrument Warfang/electro guitar, not weapon proficiency. Language choice count 1, any; Huttese selection fits.
- Hunter's Quarry level 1: advantage on Perception and Survival when tracking designated quarry; criminal underworld information access. Mechanics label bonus_type expertise conflicts with grant_advantage description; do not infer doubled proficiency, blanket advantage or automatic contact cooperation. Quarry designation not yet set; escaped bounty is a narrative lead only. No stacking rule assumed for overlap with Trophy Sense.
- No starting gear or credit package inferred from this record.
Both envelopes report outcome draft, promotion requires_manifest_and_review, schema_valid/references_valid null; both mislabeled kind class. No golden-slice definition for these picks found in enumerated tree. A source match is not a schema or runtime pass.

## 4. Class and progression blocker
No standalone Berserker base definition located in enumerated tree. This does not prove absence in uninspected archives or other branches. Two draft specializations exist:
- registry/candidate_builds/cand_classes_861acd817b14421e/draft/berserker_battle_master.json: parent berserker, first node battle_mastery_3 at level 3, includes initiative and tactical effects using Rage Points.
- registry/candidate_builds/cand_classes_861acd817b14421e/draft/berserker_rage_specialist.json (blob 981fb88d7f19883573e9bc6cecc74abb14678f4a): parent berserker, first node enhanced_rage_3 at level 3.
Both are draft, mislabeled class, with unvalidated references and missing progression/hit-die warnings. Later nodes include extreme effects and prerequisites requiring mutually exclusive choices; visual prompts also include unrelated Force imagery. Do not import as approved mechanics. No Rage pool, activation, duration, damage bonus, resistance, hit die, saving throw proficiencies, class skill choices, weapon/armor proficiencies, maneuvers, subclass or level-one feature grants assumed.
DESIGN_DECISIONS.md establishes three named subclass attractors and fluid progression using prerequisites plus affinity from committed events, followed by player choice; the equipment-restoration arc may inform a future branch but is not itself an unlock. Do not substitute the existing Bounty Hunter class. Resolve Berserker after Aero in Design Progression Trees.

## 5. Derived statistics and skills
| Field | Preview or pending |
|---|---|
| Level | 1 intended |
| HP/current/max, hit dice, recovery | pending class/species rule |
| Strain/current/max | pending; source base 9 only |
| XP/current | pending; source starting_xp 105 only |
| AC/defenses, initiative | pending armor/class/derivation |
| Speed, size | candidate 30, Medium |
| Proficiency bonus | pending applicable derivation |
| Saving throws | pending class and proficiency |
| Intimidation | candidate proficiency; CHA modifier -1 before proficiency |
| Investigation | candidate proficiency; INT modifier 0 before proficiency |
| Other skills (Athletics, Technology, Survival etc.) | not selected/granted; class choices and skill mapping pending |
| Languages | Basic/Dosh candidate; Huttese chosen |
| Tools | stun cuffs, musical instrument candidate; crafting/piloting not implied |
| Force | insensitive locked; no Force powers requested or granted; numerical pool not assigned |
| Tech powers, maneuvers, reactions, Rage | no granted entries; unknown class rules are not zero-valued rules |
| Credits, consumables, encumbrance | pending starting package and item definitions |

## 6. Possession versus availability
All signature items below have approved narrative ownership, but current location, condition, accessibility, equipped state, operational modes and charges are unresolved. None is available for runtime action until a validated item and explicit initial state exist. This is an authoring hold, not a fictional confiscation or damage event. Choose narrative restrictions with owner at campaign insertion.

| Possession | Intended functions | Required before activation |
|---|---|---|
| Iron Warrior armor | heavy mechanical protection, retractable helmet, full remote deployment | item stats, armor category/proficiency, rage compatibility, don/doff and deployment action costs, energy and limits |
| Self-built gauntlets | power fists, blasters, retractable blades, grappling cables, energy shields, flying deployment | item/modification definitions, mode switching, hands, attack/damage/range, ammo, shield limits, grapple/traversal constraints, costs |
| Warfang | metallic electro guitar and blaster | instrument vs weapon routing, validated modes, hands, attack/ammo, proficiency |
| Doom Talon | personal bounty ship | starship definition, ownership/access state, silhouette, speed, handling, defenses, health, crew, costs and systems |
| Jadasshh gifts | grenade bag, gear pouch, meal container, lucky holster | item definitions and starting quantities, no implied grenades/blaster/food supply |
| Glowing tattoos | empty cybernetic enhancement concept | slot count/type, installation requirements, compatible mods, capacity and effects; no installed enhancements or benefits |

No bespoke stats invented, no free actions derived from visual effects, no rare alloy or ammunition granted. Future restoration can be a personal quest, not a prescribed outcome.

## 7. Schema and runtime audit
- schema/Character.schema.json requires id/name/era/rarity/narrative/description/species_id/background_id/game_mode/tags; defines six ability scores and equipment/proficiency arrays. This worksheet deliberately does not claim conformance.
- app/genesis-os/docs/architecture/CHARACTER_RUNTIME.schema.json requires character_id, campaign_id, identity, mechanics, equipment; weapons/armor/gear/vehicles arrays and item-type routing. No campaign id or fake runtime references assigned. Class/subclass, resources, defenses, actions, features and progression must later project from one validated instance.
- schema/Class.schema.json requires hit_die, proficiencies, primary_ability, class_identity_profile and other identity fields; progression design supports tree/legacy progression. Missing base record blocks class audit.
- schema/Item.schema.json requires item_type plus identity/narrative/rarity/image_generation/ui; schema/Modification.schema.json requires mod_type, slot_cost, mechanics and other metadata; schema/Starship.schema.json requires class, type, silhouette, speed, handling, defenses, health and presentation fields. Ownership alone satisfies none of these.
- schema/CharacterCreator.schema.json is a minimal ordered-step skeleton, not an implemented full validator.
- Contracts/atomic_mechanics_refactor.md requires structured dice/ranges/durations/bonuses for its power refactor; use as design guidance, not proof of item rules.
- campaigns/starwars_litrpg/creator/TURN_CONTRACT.md section 4: action, bonus, reaction, movement, free object interaction; capability, range, costs, hands, position checked. ACTION_ECONOMY_RULING.md is scoped provisional campaign guidance, not universal armor deployment permission. No actual turn budget assigned.
- registry/golden_slice/global_definitions/action_unarmed_strike.yml is an approved residual action identity but does not specify damage math in the inspected file. It cannot validate claws/gauntlets by itself.
- registry/exports/build_manifest.json explicitly says no auto-promotion; canonical layer mirrors approved golden_slice only. CREATOR_AUDIT_2026-10-27.md and CREATOR_SHORTLIST_2026-10-27.md describe candidate misclassification, schema gaps and promotion review; these are historical audit results, not a fresh validator run.

## 8. Release gate and verification
Manual repository evidence audit only, not a schema validation run or gameplay regression. Required next steps: confirm corrected allocation; resolve and validate species/background refs and effects; author/reconcile Berserker root and approved progression; select remaining proficiencies/features; validate equipment and initial state, derive stats from approved rules; choose campaign scope and validate runtime instance; only then authorize insertion. No registry promotion, live campaign edits, runtime mutation, or dice. Stage 3 artwork may proceed independently from mechanics using the Soul dossier.
