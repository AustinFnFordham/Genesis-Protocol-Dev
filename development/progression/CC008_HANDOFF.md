# CC-008: unified progression framework — handoff

**Branch:** `dev/cc008-progression-framework`, created from `5ec21bb` (CC-007 is preserved).

**Kind of work:** sandbox only. No candidate curve or milestone benefit was promoted.

**Not touched:** Hask Meadow, shared-1, shared-0002, Oracle, GM credentials, live campaign rules, and Aero's runtime sheet (its SHA-256 is checked by the tests). The Oracle and Crucible branches were not merged. The SA-001 and CMT-001 doc branches were read, not merged.

## Commits

| Milestone | SHA | Content |
|---|---|---|
| A: source reconciliation | `5810c10` | `CC008_SOURCE_RECONCILIATION.md` |
| B: unified schema | `b99c34f` | `schema/genesis_progression_tree.schema.json`, `framework.js`, `PROGRESSION_SCHEMA.md` |
| C: explicit thresholds | `a49343e` | `curves.js`, `validate.js`, the Telekinetic Control tree, candidate class curves and their pacing |
| D: three-choice milestones | `0ad3efa` | `choices.js` |
| E: shared Discipline XP | `d7c296c` | `disciplines.js`, `policies/discipline_allocation.v0.1.json` |
| F: Aero vertical slice | `8bec928` | `fixtures/aero_vertical/` (`evidence.json`) |
| Test fix (combat UI) | `378beec` | Two load-sensitive assumptions in `test_playtest_ui`; the runner now keeps failing output. **Commit F was pushed while that suite was red; this commit restored green.** |
| G: authoring tools | `a939b57` | `tools/validate_tree.cjs`, `authoring.js`, `AUTHORING.md`, `XP_TABLES.md` |

**Tests:** `test_cc008.cjs` runs B to G (17 + 36 + 26 + 26 + 30 + 26 = **161 checks**). The full `run_all_checks.sh` gives **74 suites, 0 failed**: all 73 CC-007 suites plus the CC-008 runner.

## Key results

- **Typed ledger.** `class_xp`, `mastery_xp`, `discipline_xp` and `purchase_currency` are never exchanged, and a class level is never a mastery level (tested both ways).
- **Legacy trees.**
  - 17 of 100 candidate class trees (Sentinel among them) and 23 of 195 hub class and subclass trees are **unsatisfiable when read literally**: they require several picks from one exclusive group.
  - The adapter reads them as `any_of_group` and records each reinterpretation. The validator rejects the literal form at exactly Sentinel L3 and L7.
- **Three-choice contract.**
  - The server computes each option's status (eligible, locked, purchased, unavailable) from actual holdings.
  - It presents up to three candidates in a deterministic order, with **no filler**.
  - It re-validates at the moment of selection and records a sealed, recoverable transaction.
- **Discipline XP.**
  - Each observation gives one primary track and at most 2 pools, at most 2 XP in total.
  - The capability must be owned and the evidence committed.
  - Setup and payoff count as one observation, team credit is per actor, and speech, footsteps and trivial pickups earn nothing.
- **Aero slice.** Class (Force Connection, Sentinel Balance) and species (the three Echani traits) grants match the sheet. Candidate thresholds take him to class 3, where all 8 source archetypes are offered.
  - **Sentry** is selected and its track unlocks.
  - **Mastery:** 50 and then 190 committed strikes take Echani Strike mastery to 3 and 6, with matching Martial Arts discipline XP.
  - Three candidate techniques are offered and one is recorded. An upgrade chain and a cross-tree (class plus species) technique unlock later.
  - Every refusal case holds, and replay is byte-identical.
- **Tool findings on real data.**
  - None of the Sentinel class features after level 1, and none of the Sentry features, are approved Registry identities.
  - The Minor Telekinesis anchor is a campaign ruling, not a Registry entry.

**Corrections to earlier reports**
- **SA-001 exists.** It is a draft "Secondary **Action**" contract on `docs/cinematic-combat-capability-v0.2-20261121`; earlier reports said it was missing. Its rule matches CC-007 option A.
- **Aero's size is source-backed.** Echani `size: Medium` is in the species source, not just a fixture default.

## Owner decisions needed for actual tree content

1. **Character-level thresholds.** No source defines them. Choose a table or curve, or milestone levelling (candidates are in `candidates/`).
2. **The subclass model.** Three branch clusters (DESIGN_DECISIONS) vs a selected archetype at L3 (the class trees and the brief). Choose the cadence: the sources use 3/7/11/15/18 and 3/7/11/13/17/19; the brief says 3/6/9/12/15/18.
3. **Legacy prerequisite reading.** Accept `any_of_group` for the 40 affected trees, or repair the sources.
4. **Sentry authority.** `specialization_features` vs `progression_tree` (they don't overlap), and their effects (contradictory or placeholder text).
5. **What drives species tiers.** Class level, or an independent heritage track? Also: turn Echani's free-text tier benefits into executable effects.
6. **The Echani source copy.** `official_species_playable` (cited by the sheet) vs `backend`.
7. **Purchase currency.** The fate of legacy `xp_cost`, `starting_xp` and `upgrades[].xp_cost`, and the price of CMT-001 Maneuvers.
8. **Discipline policy.** Adopt the pool list and the weights and bounds (experimental), and whether Disciplines have milestone content of their own.
9. **Anti-farming.** The per-scene caps, and what counts as "meaningful" speech, traversal and handling.
10. **Offer presentation.** The rotation rule when more than three options are eligible (deterministic hash rotation vs a fixed authored order).
11. **Candidate content to replace.** All `candidate_*` techniques and specialties in the Aero fixture are placeholders for your tree designs.
12. **Registry promotion.** Approving the Sentinel and Sentry feature identities that progression grants reference.
