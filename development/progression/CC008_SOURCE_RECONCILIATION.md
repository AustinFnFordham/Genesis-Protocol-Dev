# CC-008 Milestone A: progression source reconciliation (read-only)

**Branch:** `dev/cc008-progression-framework`, created from `5ec21bb` (CC-007).
**Nothing was changed** by this milestone: no sources, no sheets, no campaign data. Legacy example data is **not** treated as canonical.

## 1. Sources read

| Family | File(s) | What they are |
|---|---|---|
| CC-007 mastery | `development/progression/mastery.js`, `adapters.js`, `skills/*.json` | `genesis-mastery/0.1`: earned mastery XP, receipts, two-phase awards, eligibility milestones |
| Class schema | `schema/Class.schema.json` | `progression_tree` (fluid node graph, preferred) or `level_progression` (legacy; still read by `ui/v0.1` and `app/genesis-os`) |
| Subclass schema | `schema/Subclass.schema.json` | `talent_tree`: "progression is handled by spending XP to purchase nodes" |
| Feature and Power schemas | `schema/Feature.schema.json` (`xp_cost`), `schema/Power.schema.json` (`upgrades[]` bought with XP) | Legacy **purchase XP** |
| Character schema | `schema/Character.schema.json` | `level` (1–20) and `xp` (an integer); no thresholds defined |
| Species progression | `schema/SpeciesProgression.schema.json`, `Contracts/wookiee_progression_example.yml` | `progression_tiers.level_5/10/15/20`, with a structured `mechanical_effect` |
| Design decisions | `campaigns/starwars_litrpg/creator/DESIGN_DECISIONS.md` (2026-10-29) | `id` vs `urid` (`urid = <entity_type>_<id>`, derived); fluid tree (prerequisites + tag affinity); cross-tree nodes are legal; **subclasses are three named branch clusters per class** |
| UI plans | `Contracts/02_Progression_Tree_System.md`, `14_Sub_Tree_Choice_System.md`, `skill_tree_system.yml` | Presentation: node types, choice sub-screens, cross-class links. **No authority over mechanics.** |
| Capability and mastery (proposal) | `Contracts/CHARACTER_CAPABILITY_AND_MASTERY_CONTRACT_v0.1.md`, on unmerged `docs/cinematic-combat-capability-v0.2-20261121` | Capability Graph and Mastery Graph; typed edges (`grants_access`, `grants_profile`, `requires`, `improves`); evidence and idempotency rules; **"keep character XP, node purchase costs, mastery evidence credit and tag affinity distinct"** |
| **SA-001** | `Contracts/SECONDARY_ACTION_AND_CAPABILITY_ACTIVATION_CONTRACT_v0.1.md`, same unmerged branch (draft, 2026-11-18) | "**Secondary Action**" (it supersedes "Secondary Activity"). Every character has 1 per turn; only eligible capabilities can use it. |
| Combo, Maneuver, Tactic lifecycle | `Contracts/COMBO_MANEUVER_TACTIC_MASTERY_LIFECYCLE_v0.1.md` (CMT-001) and `examples/combo_maneuver_mastery_example_v0.1.json`, on unmerged `docs/maneuver-mastery-lifecycle-v01-20261122` | Owner-approved direction. **Combo** = free, no new effect. **Maneuver** = purchased composition with a measurable extra effect. **Tactic** = emerges from evidence. Team variants. **Purchase cost ≠ activation cost.** Per-component mastery drives Maneuver upgrades. No arbitrary ceiling on growth. |
| Registry identity | `registry/golden_slice/global_definitions/*.yml` | URID, lane, status and source pointer **only (no mechanics)**: `class_sentinel`, `subclass_sentry` (tag `planned`, campaign scope `meridian_reach`), `species_echani`, `feature_sentinel_balance` (`authored_residual`), `feature_echani_grappling_training` (`authored_residual`), … |
| Candidate builds | `registry/candidate_builds/cand_classes_*/validated_candidate/sentinel.json`, `cand_species_*/draft/echani.json` | Candidate copies of the hub YAML plus validation metadata. **Not promoted.** |
| Hub sources | `_QUARANTINE/hub_root_debris/SW5e_Data_Hub.zip` → `backend/classes/sentinel.yml`, `backend/subclasses/sentinel_subclasses/*.yml` (8 Sentinel subclasses), `backend/features/sentinel/sentry/*.yml`, `backend/species/echani.yml`, `official_species_playable/echani.yml` | Legacy source YAML. The repo's `SW5e_Data_Hub` is a gitlink with no `.gitmodules` URL; this archive is the only readable copy. |
| Aero's sheet | `api_bridge/gm/aero_character_runtime.yml` | Level 1 Sentinel, `subclass_plan: Sentry`, Echani. Cites `06-lore-species.zip/official_species_playable/echani.yml` and `04-game_data.zip/classes/sentinel.yml`. **No XP field.** |

## 2. Conflicts between the legacy and current schemas

### 2.1 Four different kinds of "XP" (must never be conflated)

| Quantity | Where it appears | Meaning |
|---|---|---|
| **Character/class XP** | `Character.xp` (integer) | Level-up qualification. **No threshold table exists anywhere in the repo.** |
| **Purchase XP** | `Feature.xp_cost` (Sentry Watch: 35), `Power.upgrades[].xp_cost`, the `Subclass.talent_tree` "spend XP", `Species.starting_xp` (Echani: 110) | An FFG-style currency spent to buy nodes |
| **Mastery XP** | CC-007 `genesis-mastery/0.1` | Earned from validated, committed use; levels a skill track |
| **Tag affinity** | DESIGN_DECISIONS fluid tree | Behaviour counters written by the Record Keeper; gates node availability |

The capability contract already requires keeping these distinct.

**CC-008 decision:** each becomes a separate, typed ledger quantity: `class_xp`, `purchase_currency`, `mastery_xp`, `affinity`. There is no implicit exchange between them.

### 2.2 The prerequisite semantics are unsatisfiable as written

- `Class.schema.json` says `prerequisites` are "node_ids that must already be held" (**all**), and `choice_group` nodes are "mutually exclusive picks".
- The Sentinel tree then requires **both** members of an exclusive group:
  - `sentinel_specialization_3` needs `investigation_focus_2` **and** `diplomacy_focus_2` (the group `sentinel_focus_level_2`);
  - `subclass_feature_7` needs `enhanced_investigation_6` **and** `enhanced_diplomacy_6`.

  Read literally, **no character can ever pass level 2.**
- `skill_tree_system.yml` (Bounty Hunter level 3) has the same pattern.

**Scan results**

| Source | Requires several options from one exclusive group | References a node that doesn't exist |
|---|---|---|
| Candidate class trees (100) | **17** (scout, colonist, tracker, sith, trooper, sentinel, hired_gun, inquisitor, …) | 1 (scoundrel) |
| Hub class and subclass trees (195) | **23** | 1 |

**The intent is clearly "any one from the converging group".** The new schema makes the mode explicit:

```
requires: { all: [...] } | { any: [...] } | { any_of_group: "<choice_group>" }
```

A **legacy adapter** reads a list that names several members of one exclusive group as `any_of_group`, and records that it did so. The validator rejects any *new* tree that is ambiguous (§G).

### 2.3 Sentinel / Sentry source formats

| Issue | Evidence |
|---|---|
| **Duplicate top-level keys** | `sentinel_sentry.yml` defines `id: sentinel_sentinel_sentry` and `id: sentry`, plus `name` twice. YAML keeps the last value. **37 of 173** hub subclass files have duplicate ids. |
| **Two disjoint feature lists in one file** | `specialization_features`: `sentry_watch`, `area_protection`, `guardian_mastery`, `sentry_mastery`, `legendary_sentry` (each a feature file with `xp_cost`) **vs** `progression_tree` feature ids: "Sentry's Focus", "Guardianship", "Sentinel's Posture", "Vigilant Watcher", "Defender's Shield". **They share nothing.** 82 of 173 subclass files have the same disjointness. |
| **Display names used as ids** | The tree's `feature_id` values are display names ("Sentry's Focus"). Across the hub subclasses, 272 of 992 node references are display names rather than slugs. |
| **Effect contradicts its description** | Sentry's Focus: "advantage on Perception", but the effect is `ability_modification 1d4 + proficiency bonus`. Guardianship: "reaction to grant an ally temporary HP", but the trigger is "when you take damage". |
| **Placeholder mechanics** | `features/sentinel/sentry/sentry_watch.yml`: `effect: grant_ability`, "Grants a special ability", `action_type: passive`. **Not executable.** |
| **Cadence mismatch** | The Sentinel class tree puts `subclass_feature` at **7, 11, 13, 15, 17, 19**. The Sentry tree has nodes at **3, 7, 11, 15, 18**. Hub subclass cadences vary: 3/7/11/15/18 (103 files), 3/7/11/13/17/19 (30), 3/5/7/…/20 (14), 3/7/11/15 (16). **None matches the brief's 3/6/9/12/15/18.** |
| **Subclass model conflict** | DESIGN_DECISIONS: "three named branch clusters per class; taking most of a cluster earns the title". The hub: **8** separate Sentinel subclass files. The class tree: a single `subclass_entry` choice at level 3. The CC-008 brief: archetype *selected* at 3, with choices at 3/6/9/12/15/18. |
| **Registry lane** | `subclass_sentry` is `global_validated`, `candidate_promoted`, tag `planned`, scoped to `meridian_reach`, a different campaign from Aero's `starwars_litrpg`. **Sentry is prospective for Aero** (`subclass_plan`). |
| **Sentinel Balance provenance** | There is no feature file in the hub. The golden slice marks it `authored_residual` / `genuine_missing_authored`, so it came from the runtime sheet. The sheet's `2 uses / long rest` is its only mechanical source. |
| **Echani Grappling Training** | Not among the Echani `innate_traits` (Martial Arts Training, Combat Discipline, Combat Communication). The sheet sources it from `actions/combat_actions.yml` ("adopted Dexterity implementation"). Registry: `authored_residual`. **It's an action/training grant, not a species trait.** |

### 2.4 Species progression

- **Format conflict.**
  - The schema and the Wookiee example use a structured `mechanical_effect {type, value, conditions}`.
  - The Echani source (both copies) uses free-text `mechanical_benefit` strings, such as "+2 to unarmed attack and damage at 15", which can't execute.
- **The two Echani copies differ.** `backend/species/echani.yml` and `official_species_playable/echani.yml` differ in `species_progression`, `innate_traits`, `cultural_features`, `environmental_adaptations` and `tags`. **Aero's sheet cites the `official_species_playable` copy.**
- **Which level drives it is undefined.** "Traits scale with character level" (Wookiee example). The brief asks for species milestones at 5/10/15/20, which matches the source tiers, but nothing says whether the driver is class level or a separate heritage track. **This is an owner decision (§4).**
- **Correction to CC-007:** Echani `size: Medium` *is* in the species source, so Aero's size is source-backed. Only the NPC fixture sizes remain fixture defaults.

### 2.5 Further corrections to earlier reports

- **SA-001 does exist.** Audit D-9 and CC-007's `SA001_PROPOSED_CONTRACT.md` said it wasn't in the repository; that is true only of the integration branch. The draft is on `docs/cinematic-combat-capability-v0.2-20261121` (2026-11-18).
- **Its name is Secondary *Action*.** "Secondary Activity" is superseded naming.
- Its rule ("every character has one; only eligible capabilities use it") matches CC-007 rule **A**. My CC-007 recommendation of rule **C** is a balance observation for the owner, not a reading of the SA-001 text.
- **CMT-001 redefines "Maneuver".** In the CC-002 to CC-007 sandbox, Feint, Parry and the rest are *ability profiles*, not Maneuvers. Under CMT-001, a Maneuver is a *purchased composition*.

## 3. How CC-008 maps the layers onto sources

| Layer (brief) | Sources | XP quantity | Milestone cadence |
|---|---|---|---|
| 1. Character/class level | `Character.level/xp`; `Class.progression_tree` (core / asi nodes) | `class_xp`. **No thresholds exist:** candidate curves only, labelled. | Per authored node level |
| 2. Archetype/subclass | `Class` `subclass_entry` at L3; `Subclass` files; DESIGN_DECISIONS clusters | Driven by class level | Brief: 3/6/9/12/15/18. Sources vary (§2.3), so each tree declares its own `cadence`. |
| 3. Species/heritage | `SpeciesProgression` tiers | **Undecided:** class level or its own track | 5/10/15/20 (matches the sources) |
| 4. General proficiency | Skills (Character.skills), ordinary proficiencies | `mastery_xp` | 5/10/15/20, straightforward improvements |
| 5. Specialized mastery | CC-007 mastery tracks (Telekinetic Control) | `mastery_xp` | 3/6/9/12/15/18 full-tree choices. **Telekinetic Control's CC-007 cadence is 5/10/15** (owner direction), which shows cadences are per-track. |
| 6. Parent-linked capabilities | e.g. `escape_grapple` / `release_grapple` under `grappling` | The parent's `mastery_xp` | Their own choice groups |
| 7. Shared Discipline pools | New, proposed | `discipline_xp`, an allocation from the same evidence and never a duplicate track | Per pool |

## 4. Owner decisions surfaced by this reconciliation (needed before canonical content)

1. **Prerequisite semantics for legacy trees.** Adopt the `any_of_group` reading for the 17 + 23 affected trees, or repair the sources?
2. **The subclass model.** Three branch clusters (DESIGN_DECISIONS) vs a selected archetype at level 3 (the brief and the class trees) vs N subclass files; and which cadence (§2.3).
3. **Which Sentry source is authoritative:** `specialization_features` or `progression_tree`? Both are partly placeholder text.
4. **What drives species milestones:** class level, or a separate heritage track?
5. **Character-level thresholds:** none exist. Adopt a table (for example SW5e/5e-shaped), or keep candidate curves?
6. **What happens to purchase XP:** whether legacy `xp_cost` and `starting_xp` survive as `purchase_currency`, and how they relate to the CMT-001 Maneuver purchase cost (CMT-001 says the currency is still open).
7. **Which Echani copy is authoritative:** `backend` or `official_species_playable`? The sheet cites `official`.
