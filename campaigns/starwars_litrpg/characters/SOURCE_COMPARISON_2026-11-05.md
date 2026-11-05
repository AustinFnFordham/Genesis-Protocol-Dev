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
