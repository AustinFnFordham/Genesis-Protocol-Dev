# Registry Dependency Reconciliation — 2026-11-05 (rev 2)

**Nothing is promoted.** No Registry record, source pack, schema or runtime was modified. Atomic, Soul, Chaos and Registry Custodian gates were not run (no candidate is ready for them). Evidence below comes from read-only inspection of `E:\StarWars` and in-memory schema checks only.

Character facts preserved (rulings): Aero's runtime is the starting authority (Level 1 Battle Insight and Burst are documented replacements; confirmed vs adopted kept distinct). Varon's design incl. Adaptive Countermovement is approved as a *design*, not as validated mechanics. Rassira Sythrael Nox: Miraluka, Dathomirian witch-raised (culture, not species), Force severed, Bounty Hunter, Scoundrel; her runtime keeps `status: provisional_candidate_draft` / `commit_ready: false` until the values below are validated or separately approved. Togruta: none until played.

**New finding:** Rassira's runtime says the Miraluka and Bounty Hunter packs "were not available". They now are: `SW5e_Data_Hub/forge_v3/backend/species/miraluka.yml` and `.../classes/bounty_hunter.yml`. Several of her "adopted" values contradict them (item 2, 5).

Schemas: `E:\StarWars\schema\Species.schema.json`, `Class.schema.json`. Source root `B` = `E:\StarWars\SW5e_Data_Hub\forge_v3\backend`.

---
## 1. Chiss species (Varon)
- **Expected ids:** `species_chiss@1`; `feature_chiss_tactical_genius`, `feature_chiss_resilience`, `feature_chiss_enhanced_vision` (all @1). Prefix convention inferred from golden-slice `species_echani`/`class_sentinel`; `feature_` prefix comes from Varon's own refs. Custodian to confirm.
- **Source:** `B/species/chiss.yml` (id `chiss`; traits `chiss_tactical_genius`, `chiss_resilience`, `chiss_enhanced_vision`). Also a duplicate under `SW5e_Data_Hub/official_species_playable`.
- **Exact failure:** (a) ID mismatch: runtime urids carry the type prefix, source ids don't. (b) Schema, 2 errors: `environmental_adaptations` items use `mechanical_benefit` where the schema requires `advantage`; `cultural_features` items lack required `type`.
- **Responsible:** mapping (a), source data shape (b). Not the schema, not the character.
- **Smallest correction:** resolve `species_chiss` → source id `chiss` and `feature_chiss_*` → `chiss_*` in the Registry mapping; in the Forge candidate copy rename `mechanical_benefit`→`advantage` and add `type` to each cultural feature. **In-memory test: both fixes together make chiss.yml pass the unmodified schema (0 errors).** Which `type` enum value applies is a classification the Custodian should confirm (I used `cultural`).
- **Numbers check:** source INT+2/CHA+1, base HP 10, Strain 11 reproduce Varon's INT 17, CHA 9, HP 12, Strain 13. Confirmed.
- **Player decisions:** none.
- **Tests before promotion:** schema gate; urid resolution with `fallback_policy: disabled`; recompute Varon's ability/HP/Strain from the resolved record; Atomic gate on the three traits; Custodian review; golden-slice rebuild; Varon runtime load test; isolation check that no other campaign resolves differently.

## 2. Miraluka species (Rassira)
- **Expected id:** `species_miraluka@1` (not yet referenced by a urid in her runtime; add on promotion).
- **Source:** `B/species/miraluka.yml` (+ `official_species_playable/miraluka.yml`).
- **Exact failure:** schema, 1 error: same `mechanical_benefit`→`advantage` defect. In-memory rename gives 0 errors.
- **Divergence from her adopted values (source vs runtime):**

| | Source | Rassira runtime |
|---|---|---|
| Ability increases | WIS +2, CHA +1 | DEX +1, WIS +1 |
| Base Strain | 12 | 11 |
| Languages | Basic, Miraluka | Basic, Dathomiri, Huttese |
| Traits | Force Sight, Force Sensitivity, Spiritual Insight | Force Severance negates them; cybernetic band instead |

- **Responsible:** customization (her adopted spread/strain/language) plus the severance ruling. The source is fine apart from the key rename.
- **Effect if source values applied** to her 27-point buy (8/15/14/10/13/12): DEX 15 (+2), WIS 15 (+2), CHA 13 (+1), Strain 14. Her DEX 16 (+3) would drop, so AC 13→12, initiative +3→+2, DEX attacks +5→+4, Stealth/Sleight +5→+4, DEX save +5→+4.
- **Player decisions (see Q1, Q2, Q3).**
- **Tests:** schema gate; Atomic gate on traits; confirm the severance negation is expressed as an explicit override and does not delete source traits; Soul check that "Dathomirian" stays a culture tag; rebuild and load her runtime in a draft lane only.

## 3. Trooper class and Style choice (Varon)
- **Expected id:** `class_trooper@1`.
- **Source:** `B/classes/trooper.yml` (also `source_data`; runtime cites `04-game_data.zip/classes/trooper.yml`, which I did not open).
- **Exact failures:** schema, 6 errors: `hit_die` is integer 12 (schema: string like `d12`); missing required `era`, `rarity`, `narrative`, `class_identity_profile`, `level_progression` (the file has `progression_tree` instead). Content defects: node `trooper_style_1` (choice_group `trooper_style_level_1`) has **no option nodes**; `primary_resource: ammunition_points` has no starting pool.
- **Responsible:** source (data gaps) and schema/source shape mismatch (`progression_tree` vs `level_progression`). Not Varon.
- **Smallest justified correction:** `hit_die` → `"d12"` (mechanical no-op). `era`/`rarity`/`narrative`/`class_identity_profile` are authored content; I did not invent them. `progression_tree`→`level_progression` is a structural conversion the Forge pipeline should perform, not a hand edit.
- **Adaptive Countermovement:** see Q4. The three "legal" Styles Varon's runtime refers to do not exist in any pack I could read. `trooper_style` appears only in trooper.yml.
- **Ammunition Points:** named in `feats/trooper_feats.yml` (4 mentions) and `subclasses/trooper_subclasses/trooper.heavy_gunner.yml` (2). I did not read their spend rules in this pass. No Level 1 feature in Varon's runtime spends AP. See Q5.
- **Tests:** schema gate after the structural conversion; Style group must resolve ≥1 option and include Adaptive Countermovement as a custom option without altering its text; AP definition resolved or explicitly marked unused at L1; Varon level-1 recompute (hit die, proficiencies, Heavy Weapons Training); Custodian review.

## 4. Adaptive Countermovement (Varon)
- **Expected id:** `feature_trooper_style_adaptive_countermovement@1` in the `campaign_local` lane (never `global_validated` without a separate decision).
- **Authored text (preserved verbatim, not edited):** reaction; trigger: a hostile Varon can see within his equipped weapon's normal range moves at least 10 ft; effect: move up to 10 ft to an unoccupied space he can see, no opportunity attack from the triggering creature; uses = proficiency bonus (2), long rest; does not stop/reduce the trigger movement, ignore terrain, occupied spaces or barriers; others may still take opportunity attacks.
- **Located source:** none (`source: adopted Trooper Style; proposed addition`). **Responsible:** customization; the source choice group is empty.
- **Prerequisites:** `heavy_weapons_training_1` (the group's own prerequisite), choice group `trooper_style_level_1`, class `class_trooper`.
- **Tests:** option attaches to the group without modifying other options; Atomic decomposition (trigger/condition/movement/resource); uses formula equals proficiency bonus at L1; Chaos/Soul not applicable to a combat feature unless Custodian says otherwise.

## 5. Bounty Hunter class and Rassira's custom Level 1 (Rassira)
- **Expected id:** `class_bounty_hunter@1`.
- **Source:** `B/classes/bounty_hunter.yml`. **Exact failure:** 1 schema error: no `level_progression` (has `progression_tree`). Everything else validates. Same structural conversion as Trooper.
- **Source vs runtime:** saves **Strength + Wisdom** (runtime adopted Dexterity + Wisdom, written when the pack was "unavailable"); armor Light+Medium (runtime Light only: a legal subset); weapons Simple, Martial, Blaster pistols/rifles (runtime lists energy bow and electro-whips, no source item records located); hit die 1d10; Level 1 nodes `hunter_quarry`, `proficiency_bonus` (described as one extra skill proficiency, which looks like a source defect).
- **Her custom features:** *Controlled Pursuit* and *Underworld Adjudication*: customization. The source L1 node `hunter_quarry` only says "track and hunt down their quarry"; I found no mechanics to validate Controlled Pursuit against. Preserved, not replaced.
- **Equipment profiles:** energy bow, paired electro-whips, thigh blaster, sensory band: no authoritative item definitions found. They need definition records (separate from her instances).
- **Tests:** schema after conversion; recompute her saves/skills from the resolved class; item-definition vs item-instance separation; sensory-band feature passes Atomic gate; her runtime stays `commit_ready: false` until Q1–Q3, Q6 are answered.

---
## Questions that need your ruling
**Q1. Miraluka ability increases** (source WIS+2/CHA+1 vs her DEX+1/WIS+1). Options: (a) *Adopt source* — cleanest, costs her AC 13→12 and DEX bonuses. (b) *Keep her spread as an approved campaign variant* — preserves the character, recorded as a custom override, never written into the global species. (c) *Re-spend her 27-point buy under the source spread* so DEX stays high; exact scores to be recomputed and checked for legality. Recommend **(c)** if you care about her hunter's DEX; otherwise (a).
**Q2. Base Strain 11 vs source 12.** Recommend adopt source 12 (Strain 14); no identity cost.
**Q3. Languages.** Source gives Miraluka; hers lists Dathomiri and Huttese instead. Recommend: Basic + Miraluka from species, Dathomiri from her culture, Huttese from Scoundrel or dropped if the background grants none.
**Q4. Adaptive Countermovement scope.** Confirm: (i) registered campaign-local, not global; (ii) does the 10 ft come out of his normal movement (recommend no, per authored text); (iii) is "any hostile within normal range 80 ft" intended, versus a shorter trigger range (recommend keep as authored; it is limited by 2 uses).
**Q5. Ammunition Points at Level 1.** Options: (a) none at L1, since no L1 feature spends them (recommended; no invention); (b) define a pool, e.g. proficiency bonus or 2× proficiency; I need the spend rules first.
**Q6. Bounty Hunter saves.** Source Strength+Wisdom vs adopted Dexterity+Wisdom. Recommend source, unless you want her saves as a deliberate customization.
**Q7. Sensory band.** 15-ft technological blindsight with advantage on movement-detection Perception. Recommend approving it as a custom item/feature (not a species trait) subject to balance review.

## Safe next steps
1. Answer Q1–Q7. 2. Registry Custodian lane: apply mapping + key renames to Chiss/Miraluka candidates, run gates. 3. Forge structural conversion for Trooper/Bounty Hunter. 4. Rebuild golden slice, load-test Varon and Rassira in draft lane. Until then the Datapad shows both as identity only, mechanics pending.
