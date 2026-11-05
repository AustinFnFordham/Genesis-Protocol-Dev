# Registry Dependency Report — 2026-11-05

Scope: Chiss, Miraluka, Trooper, Bounty Hunter (referenced by Varon and Rassira runtimes).
Method: read-only inspection of `E:\StarWars` (api_bridge/gm/characters, SW5e_Data_Hub/source_data, forge_v3/backend) via Austin's machine, plus the repo's `_golden_migrate.py` / `_golden_resolve.py` to learn the promotion process.

## Established promotion process (from `_golden_migrate.py`)
A reference slot is promoted only when its name resolves by exact normalized match into a `global_validated` lane (`forge_v3/backend` or `SW5e_Data_Hub/source_data`); the record then gets `validation_status=candidate_promoted`, `resolution_status=exact_validated`. Campaign-local matches get only `reviewed_alias`. Promotion writes into the golden_slice and registry sqlite on Austin's machine. The repo contains none of these source files, and I was using the machine read-only, so **nothing was promoted and no Registry or runtime was modified.**

## Findings
| Entity | Class of problem | Evidence | Status |
|---|---|---|---|
| Bounty Hunter | incomplete validation (not missing) | `source_data/classes/bounty_hunter.yml` exists and passes the local Class schema (the only one of the four that does). No golden_slice record exists for it. Rassira's runtime numbers differ from this source. | Promotable on Austin's machine through `_golden_migrate`; needs a reconciliation ruling on her deviations first. Not done. |
| Trooper | schema incompatibility + undefined content | Sources (`source_data/classes/trooper.yml`, `forge_v3/backend/classes/trooper.yml`) fail local Class schema shape checks. Style options and Ammunition Points are not defined in any source. Varon's Adaptive Countermovement is custom and has no source definition. | Blocked. Authored definition preserved, not replaced. Validation issue stays open. |
| Chiss | ID mismatch + schema incompatibility | Varon cites `species_chiss` and `feature_chiss_*`; draft ids are `chiss` and `chiss_*`. Draft fails shape checks on environmental_adaptations / cultural_features. | Blocked. Needs an id mapping decision plus schema-conformant rewrite from sources. |
| Miraluka | schema incompatibility + deviation | Draft fails the same shape checks. Rassira's adopted numbers differ from the draft. Her runtime is ruled correct. | Blocked. Runtime stays authoritative. |

Atomic/Soul/Chaos gates were not run: they are implemented in the pipeline on Austin's machine, and no record reached a state where running them was meaningful.

## Blockers (exact)
1. The source YAMLs and registry sqlite are not in this repo, so promotion/rebuild cannot run in this session without writing to the owner's machine.
2. Trooper Style options, Ammunition Points, Chiss feature ids and schema shape need owner/pipeline decisions; I did not invent them.
3. Varon and Rassira runtimes exist only locally (UAT-0011).

## Safe continuation
Only Aero is playable this campaign. His Echani and Sentinel records are in the golden slice. Varon and Rassira can appear as named, noncanonical, read-only presentation (no mechanics shown) until the above is resolved. Nothing in campaign state depends on them.

## Suggested next step
On Austin's machine, run `_golden_migrate` for Bounty Hunter only, after he confirms how Rassira's deviations should be recorded.
