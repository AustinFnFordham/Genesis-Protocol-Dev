# Source comparison and candidate resolution — 2026-11-05

Structured candidates: `candidates/CANDIDATES_2026-11-05.yml` (noncanonical, nothing promoted, no gate run, no runtime or source file changed). Extends `REGISTRY_DEPENDENCY_REPORT.md`.

## What the sources actually are
- **OmniBrew SW5e data** (`E:\StarWars\sw5e-data`): species Chiss (PHB) and Miraluka (EC), traits, manual rules text. **No Trooper or Bounty Hunter class exists there** (ten classes only; Bounty Hunter is a PHB *background*). So Trooper and Bounty Hunter are Genesis-original classes, not SW5e rules.
- **Genesis game data** (`game_data.zip` and `forge_v3/backend`): the only source of both classes.
- **Sourcebook PDFs and FFG/EDGE books were not found** under `E:\StarWars`. The `StarWarsFFG-2.0.3` folder is Foundry system code with no career or specialization data. Tell me where the books are and I will look at the Style options there.

## Results
| Dependency | Class | Finding |
|---|---|---|
| Chiss | Source-backed candidate | SW5e PHB and Forge agree on INT+2/CHA+1 and 30 ft. Id mapping confirmed; two key-shape defects fixed in memory pass the schema. Varon's Shyriiwook has no recorded origin. |
| Miraluka | Source-backed candidate | SW5e (EC) and Forge agree on WIS+2/CHA+1 and Miralukese. SW5e Force Sight and Force-Sensitive (denounce / curse / bestow curse) are negated by the approved severance, recorded as an override, not an edit. |
| Bounty Hunter | Source-backed candidate | A **schema-valid** copy exists in `game_data.zip` (has `level_progression`). The forge copy differs only in shape. Saves STR+WIS, hit die 1d10. `hunter_quarry` has no definition file anywhere I looked. |
| Trooper | Unresolved dependency | Same structure in both copies. **No Style option is defined in any file.** AP has spenders (Suppressive Fire 2 AP and Heavy Weapons Specialist 1 AP as feats, Heavy Gunner 3 AP at 11) but no starting pool or recovery. |
| Adaptive Countermovement | Explicit campaign adaptation | Cross-checked against SW5e reaction and opportunity-attack rules (`the-order-of-combat.md`, pp. 90–91 per its source tag; `making-an-attack.md`; `actions-in-combat.md`): no conflict. |
| Sensory band, Rassira's weapons | Explicit adaptation / unresolved | No source records. Needs item definitions and balance review. |

## Gameplay fallback applied
Ammunition Points: Varon takes no AP spender, so nothing at Level 1 depends on a pool. Continue normally; I did not invent one.

## Defaults recorded, not applied (per your instruction)
Rassira: source ASI, source saves (STR+WIS), source Strain base 12 pending Jade's confirmation of the DEX choices. Languages with origins: Miraluka(lese) (species), Basic, Dathomiri (Dathomir witch-raised upbringing), Huttese (background or history). `commit_ready: false` stays until the mechanics and equipment validate.

## Decisions I actually need
1. **Adaptive Countermovement registration:** approve registering it as a campaign-local option, as the only Trooper Style, since the other three are not in any file. Does the 10 ft come out of his normal movement? (The text reads as no.)
2. **Bounty Hunter era adaptation:** the class needs an era-compatibility ruling that I'm keeping in the GM lane to avoid spoiling the setting. I'll propose it there; I only need your go-ahead to use the Genesis Bounty Hunter class under an explicit adaptation.
3. **Location of the sourcebooks** if you want the missing Trooper Styles and `hunter_quarry` text sought in them.

Everything else waits on Jade or on the Custodian lane.

## Update: FFG rulebooks and owner approvals (13:22)
Books are in `E:\StarWars\FFG_RULEBOOKS`. Searchable: EotE Core, AoR Beta, Beginner Game, Game Master's Kit/Guide. **Image-only, so unsearched: `fnd_core.pdf` and `FnD_Deciples_of_Harmony.pdf`** (needs OCR; that is where a Miraluka entry would be).

Hybrid rule applied: SW5e gives mechanics; FFG gives lore and comparative design; nothing transferred without an adaptation. Page numbers are PDF page indexes.

- **Adaptive Countermovement (approved):** registration approved as campaign-local, not performed. Mechanics are checked against SW5e only; no FFG Trooper analog found. Classified explicit campaign adaptation.
- **Ammunition Points:** no origin in SW5e or FFG. AoR (p117) says ammo isn't tracked; EotE has Limited Ammo and Spare Clip (p144). AP is a Genesis invention, so there is nothing to transfer; stays unresolved, not needed at Level 1.
- **Trooper Style options:** not in SW5e or any searchable FFG text.
- **Bounty Hunter (era adaptation approved):** it is an FFG-lineage class (EotE career, Assassin/Gadgeteer/Survivalist, matching the Genesis subclasses). Both sources agree the class mechanics are era-neutral. The FFG career's legal-status text ties to its own setting, so the adaptation is to keep the mechanics and omit that licensing; specifics stay GM-side. Classified explicit campaign adaptation.
- **Genesis skill list vs FFG career skills:** Genesis expresses the class in SW5e skills, not FFG's (Athletics, Brawl, Perception, Piloting, Ranged (Heavy), Streetwise, Vigilance). No change proposed.

Still nothing promoted; no gate run.

## Update: gates run and Registry state checked (13:30–13:45)
**Correction to my earlier reports.** The canonical Registry (Rust Registry Custodian, `E:\StarWars\registry\canonical_store`) already holds **`species_chiss`, `feature_chiss_tactical_genius`, `feature_chiss_resilience`, `feature_chiss_enhanced_vision` at v1**, promoted 2026-08-30 (package `chiss_species_features_b75e83383cfaa29d`; the current `chiss.yml` SHA-256 still matches). Verified by exact lookup through the Custodian adapter, not by reading files. The Forge's own projector (`forge_core/custody/species_feature_admission.py`) already maps `chiss_*` to `feature_chiss_*` and only projects fields that pass the Species/Feature schemas, so the `mechanical_benefit` and `type` defects I reported never reach the canonical record. **Varon's Chiss dependencies are satisfied.** Earlier "ID mismatch" and "schema incompatibility" for Chiss are retracted for the canonical store; they described the Python-lane files, which the repo's golden slice does not carry.

Exact lookups (v1, no fallback): found: `species_chiss`, three Chiss features. **Not found:** `species_miraluka`, `class_trooper`, `class_bounty_hunter`, `feature_trooper_style_adaptive_countermovement`. (`species_echani` is also not in the Rust store; Aero's Echani/Sentinel resolve in the Python golden slice, a separate lane. Not touched.)

**Established promotion path:** Forge preparation code → `rust_promotion_adapter.request_promotion` → Rust custodian is the only writer; the Python custodian is retired. Domain projectors exist only for **Species+Features (Chiss-specific table)** and **Items**. **There is no Class projector**, so Trooper and Bounty Hunter have no implemented route into the canonical store. That is the real blocker for those two, beyond the data gaps.

**Adaptive Countermovement gate results** (candidate: `candidates/feature_trooper_style_adaptive_countermovement.json`, text verbatim from Varon's runtime):
- Feature schema: **pass, 0 findings** (meaningful).
- Atomic and Soul validators: reported pass in wip and gold, **but also passed deliberately broken control records** (id `bad id!`, narrative `TODO`). They check a different block layout, so for a Feature record their pass is **not evidence**. Not counted.
- Chaos: no per-record gate exists for a Feature (only intake/proposal tests), so not applicable.
- Rules cross-check against SW5e reaction/opportunity-attack text: no conflict (earlier section).
- **Registration:** `forge_v3/data/campaign_local` contains only `Character__*` files; there is no convention for a campaign-local Feature. I did **not** write one. Registering it would need a Feature route in the campaign-local lane (or a campaign-scoped Rust promotion), and it also references `class_trooper`, which does not exist yet. Status: schema-valid candidate, not registered, not promoted.
Side effect on your machine: a scratch copy of the candidate in `%TEMP%\acm_candidate.json` and OCR scratch in `%TEMP%\ffg_ocr*`. Nothing under `E:\StarWars` was written.

## Owner tiebreaker (13:45)
SW5e wins where sources conflict or balance is in doubt and that makes sense; FFG is lore/comparison only. Does not alter promoted records or approved customizations. Effect: Miraluka stays SW5e-sourced (FFG has no entry in the searchable or OCR'd pages); Bounty Hunter stays expressed in SW5e terms; Rassira's recommended defaults (source ASI, Strain, saves) already sit on the SW5e/Genesis side.

## Correction (14:08): combine and enhance where both sources have it
My earlier "keep Bounty Hunter SW5e-only, don't import FFG skills or licensing" over-applied the tiebreaker. The rule is: SW5e supplies mechanics and wins on conflict; where FFG also has the content, combine and enhance, translated into SW5e terms.

Bounty Hunter, FFG (EotE PDF p58-60) vs Genesis class (SW5e-expressed):
| Element | FFG | Genesis/SW5e | Proposed combination (not applied) |
|---|---|---|---|
| Specializations | Assassin, Gadgeteer, Survivalist | same three plus Operator, Skip Tracer, Martial Artist | Already combined. No change. |
| Career skills | Athletics, Brawl, Perception, Piloting (Planetary/Space), Ranged (Heavy), Streetwise, Vigilance | choose 3 from Athletics, Deception, Intimidation, Investigation, Perception, Stealth, Survival, Technology | Athletics, Perception (covers Vigilance) already present. **Add SW5e Piloting** to the list (FFG lists it twice; SW5e has the skill). Brawl and Ranged (Heavy) are weapon training, already covered by Martial and blaster rifle proficiency. Streetwise has no SW5e skill; nearest existing choices are Investigation and Insight, so nothing to add. |
| Hunter's Creed | "People don't have bounties; only acquisitions"; guild/independent code (p59) | no equivalent | Add as the class's narrative/Soul text. It fits Rassira's contract ethic. Flavor only, no mechanics. |
| Legal status (license) | Imperial-era licensing assumed | none | Keep as an era-appropriate equivalent (guild standing or local license) as a narrative hook, specifics GM-side. Not mechanical. |

Smallest change to the class source: add Piloting to the skill choice list and the Creed to its narrative. That edits a Genesis source file, so it goes through the Forge candidate lane for approval; I have not changed any source. Rassira's runtime (Investigation, Perception, Stealth, Survival) is unaffected.

## Rule restated (14:10) and applied to the conflicts found
Rule: SW5e is the fallback only where FFG has no data. On a real conflict, find the cause and the resolution that best marries both.

Conflicts found so far (most items had no FFG data, so SW5e/Genesis stands):
1. **Ammunition.** FFG abstracts it: AoR (PDF p117) says characters always have enough power packs; scarcity enters only through Despair or the Limited Ammo quality (EotE p15, p144). SW5e tracks it per weapon (capacity, reload, ammunition property; Varon's pistol is 12 shots). *Cause:* FFG is narrative-first and uses ammunition as a story lever; SW5e is resource-first. *Resolution that marries them:* keep per-weapon capacity as the SW5e baseline, and treat Ammunition Points as a separate, abstract pool for deliberate ammunition-expenditure maneuvers (Suppressive Fire etc.), which is FFG's "spend supply for effect" idea in SW5e form. Jams and shortages as complications go to the Chaos layer, matching FFG's Despair use, not to AP. This also explains why AP does not touch weapon capacity. *Still undefined:* pool size and recovery. Candidate options for later approval (nothing applied, Varon needs none at Level 1): size = proficiency bonus or 2x; recovery = short or long rest (SW5e's normal rest structure). I need the owner's call only when a Trooper actually takes an AP spender.
2. **Bounty Hunter legal status.** FFG assumes its own era's licensing; SW5e background has none. *Cause:* an era-specific setting layer in FFG. *Resolution:* keep the class mechanics and add an era-appropriate standing hook (done in the Bounty Hunter proposal).
3. **Skill model.** FFG career skills (Streetwise, Brawl, Ranged (Heavy), Vigilance) have no one-to-one SW5e skill. *Cause:* different skill taxonomies. *Resolution:* map to the nearest SW5e skill or proficiency; add Piloting, which exists in both (proposal above).

## Update (14:15): skills as separate, adjacent skills
No skill schema or skill registry exists in Genesis (skills are names in class/background lists and sheets), and SW5e data has no renown mechanic. So adding FFG-derived skills is a content decision, not a schema change. Brawl and Ranged (Heavy) are attack proficiencies in the 5e frame, not skills; they stay as proficiencies. Piloting exists in both and is already a SW5e skill.
Proposed definitions (nothing applied): **Streetwise** (Wisdom): urban/underworld navigation, contacts, black markets, reading the street's social terrain. The urban counterpart of Survival, distinct from Investigation (deduction), Insight (reading intent), Persuasion (convincing). **Vigilance** (Wisdom): sustained alertness, being awake and ready, resisting ambush and surprise; Perception stays active noticing. Vigilance touches initiative/surprise math, so its exact effect needs an owner call.
Licensing: Bounty Hunter standing starts at 0 at Level 1. Genesis has faction ranks (`rank_` ids, `factions/`), so the natural home is the lowest rung of the relevant guild's rank; not yet checked which faction record fits.

## Vigilance ruling (16:22), drafted as a candidate rule (not applied)
- **Trigger:** only when surprise is possible (ambush, hidden threat). Not a general initiative skill. Initiative stays a Dexterity check.
- **Check:** Vigilance (Wisdom) vs a DC set by the GM or the ambusher's Stealth result.
- **Success:** not surprised. No initiative change.
- **Failure:** still surprised, but adds to initiative (reacting quickly once the shock passes).
- **Critical failure (natural 1):** surprised and subtracts from initiative.
- **Defaults I will use unless corrected:** add = proficiency bonus on failure; subtract = proficiency bonus on a natural 1. Success-vs-failure as written means a failed check can leave a higher initiative than a success; that follows your wording and is intended as "the shock sharpens you", but say if you want success to carry a small bonus too.
- Streetwise definition remains proposed, not yet confirmed.

## Vigilance numbers, worked out (16:24) — recommended, pending owner OK, not applied
Analysis (d20 math, run offline; not game dice):
- **DC = 10 + the ambushers' best Stealth modifier**, taken from their stat block. Deterministic, so the GM sets nothing. Only the player's d20 is rolled. Success chance vs. modifier gap (Vigilance minus Stealth): -2 → 45%, 0 → 55%, +2 → 65%, +4 → 75% (a natural 1 always fails; included).
- **Failure: +2 initiative, flat. Natural 1: -4 initiative, flat.** Flat, not proficiency-scaled: +2 moves initiative win chance vs an equal opponent from 47.5% to 57.3%; proficiency scaling would reach +6 (74%) at high levels and dominate Dexterity. -4 drops it to 30%, deliberately larger than the bonus because it happens only 5% of the time.
- At equal modifiers: success 55%, ordinary failure 40%, natural 1 5%, so the expected initiative change per check is +0.6. A failed check never leaves a character worse off than the average, which keeps proficiency from feeling punished.
- Surprise is the large effect (no first-round action); these initiative changes are the small, secondary one.

GM-bias safeguards (the GM is Claude, so these are structural, not promises):
1. The ambush and its Stealth modifier are written to the hidden ledger **before** the player declares anything. The ledger is append-only, so it can't be changed after the roll.
2. The Stealth modifier comes from the adversary data, not from my judgment of the scene.
3. The check is rolled with the dice skill and logged. Only the player's roll and the outcome are shown; the DC stays hidden.
4. Outcomes are applied mechanically from the table. I can't upgrade or downgrade one afterward.
Remaining GM discretion, stated openly: whether an ambush exists in a scene. Mitigation: ambush likelihood for a scene comes from a logged Chaos roll when the situation is open-ended; a story-driven ambush is recorded before the declaration like any other hidden setup.
