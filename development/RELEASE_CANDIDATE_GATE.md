# Release candidate gate — HOLD

Branch: `rc/experimental-resolution-acd961c`.
Final frozen live base: `7845e4c4d03a45946930c497ba5274a57a3de17c`.
Development incorporated: `8f6a641b4a062031da52838b20e6a2d7b3f47119`.

The inspected live HEAD was newer than the supplied `2d7f186`. Its three newer
commits (`31900b7`, `8ddbbed`, `dc1eb4d`) changed campaign records only. The release
candidate is based on that live HEAD and incorporates the tested development
branch through a merge in the isolated checkout. Newer Hask Meadow bytes were
preserved. Nothing was merged into production, deployed, republished, or sent to
a live worker. The earlier local audit checkout was restored after an aborted,
uncommitted merge command before assembling the candidate in its own worktree.

The initial assembly used `dc1eb4d`. Live play then appended two more turns
(`8709afa`, `acd961c`). They were incorporated unchanged into this candidate.
Data-dependent readiness, RNG, full brief verification and pagination checks
were repeated against this final inspected base. The history test now loads all
Journal pages rather than assuming a single page.

One final live turn (`7845e4c`) arrived during the remote tree check and was
incorporated unchanged. The 1,168 verified prefix heads remain byte-identical;
18 appended heads were independently compared against full replay and checked
for player leaks. Together they cover all 1,186 heads. RNG audit, snapshot budgets
and complete paginated history were checked again. This is the frozen candidate
base; any later live advancement must be reconciled at the staging approval gate.

## Increment references

Local refs below are mapped to equivalent published trees in
`verification/release_candidate_commits.json`.

| Commit | Scope |
| --- | --- |
| `601333d` | Combine the current live base with the prior tested development changes. |
| `1039f1f` | Sandbox deterministic temperature/narrative policy, transactional dice adapter, public filters, immutable review and brief contracts, tests/comparisons. |
| `b945fd4` | Gated mobile composer controls, submitted-mode display and pagination expansion fix. |
| `cf3628b` | Reject renamed retry keys for an already accepted step/actor/roll kind. |
| `51cd32b` | Incorporate the two newer live turns unchanged. |
| `e21839d` | Exercise all Journal pages against the larger live record. |
| `01c7293` | Preserve the final observed live turn without modifying its records. |
| `c5b48d1` | Preserve ordinary NPC natural-face outcomes and validate public resolution provenance against immutable roll/declaration records. |

The exact changed-file list and aggregate results are under
`development/verification/release_candidate/`. Original source data, seeds, private
GM prose and credentials are not included in those evidence files.

## Gates

| Gate | Status | Evidence / limitation |
| --- | --- | --- |
| Preserve current Hask Meadow, registry and shared character definitions | PASS locally | Empty Git diff against the live base for all `campaigns/starwars_litrpg/runs/`, all `api_bridge/gm/`, and `ui/turn_contract.js`. |
| Experimental mapping, eligibility, criticals, degree bands and independent d6 | PASS locally | 19 experimental test cases, including all 20 faces, all 400 advantage pairs in both directions, mixed-dice isolation and every degree boundary. |
| Retry/replay and dice partial-write recovery | PASS for new adapter | Real subprocess termination at seven transaction boundaries, torn append and partial state-temporary recovery, independent ordinary replay and separate-axis replay. |
| Unmodified legacy dice CLI crash atomicity | FAIL | Process termination after public append leaves its cursor behind. Adapter refuses divergence. Legacy CLI itself remains unchanged and is not certified safe for interrupted retry. |
| Existing Python regressions | PASS | 20 scripts including the experimental suite; earlier dice, validator, security, ledger, brief, sequencer and public-client coverage retained. |
| Compact brief replay/privacy | PASS locally | All 1,186 heads covered by verified prefix plus appended-head replay; zero detected player leaks; hidden history retrieval refused. |
| Browser regression suites | PASS in Chromium | Seven suites: base composer, sequencer, scene, emulated iPhone, paginated history, player experience and experimental controls. |
| Real mobile Safari | NOT RUN | No real Safari/device connection available. Chromium mobile emulation is not Safari certification. |
| Remote queue, CAS, lease and publication | BLOCKED / NOT RUN | Dedicated staging endpoint/project and access method have not been supplied. The connected mobile Site reports no MCP worker server; no remote mutations were attempted. Local SQLite/CAS tests are not substituted for this gate. |
| Complete GM-generated remote staging turn | BLOCKED / NOT RUN | Scripted local diagnostic turns are covered. No real remote provider adjudication or full staging publication was exercised. |
| Actual provider end-to-end latency, tokens and model calls vs baseline | NOT MEASURED | No remote staging call was made; no comparable historical provider usage baseline is available. Token counts remain null rather than inferred from bytes. |
| Hidden data in public chapters, relationships and refresh | PASS locally; remote unverified | Canaries, strict nested resolution allowlists, six-turn chapter/refresh tests and full brief verification. No provider interchangeability claim. |

## Measurements

At the frozen live base, the snapshot is 82,780 bytes under the unchanged 96,000
ceiling: **13,220 bytes headroom**. Full feed, Journal and dice history remain in
bounded pages; no authoritative rows were removed. Testing the larger current
history exposed a UI bug: the Previous Turns disclosure collapsed after loading
a page. Section expansion now survives re-rendering; the multi-page browser test
passes without bypassing visibility checks.

For the same 1,186-event workload, full GM bundle: **193,882 bytes**; compact:
**49,666 bytes**, **74.38% smaller**, with identical field projection. Local full
replay median: **233.51 ms**; verified checkpoint: **260.20 ms**. Checkpoint
verification still replays its prefix; no speedup is claimed. These figures are
not token counts, provider latency or a comparison with an equivalent live turn.

Six equivalent-seed scripted workloads, six scenes each:

| Temperature | Narrative Off successes | Narrative On successes | On narrative outcomes | Eligible / committed effects | Decision points |
| --- | --- | --- | --- | --- | --- |
| Regular | 1/6 | 1/6 | 2 Advantage, 4 Threat, 0 Neutral | 0 / 0 | 6 per workload |
| Heroic | 3/6 | 3/6 | 2 Advantage, 4 Threat, 0 Neutral | 0 / 0 | 6 per workload |
| Legendary | 6/6 | 6/6 | 2 Advantage, 4 Threat, 0 Neutral | 0 / 0 | 6 per workload |

Ordinary raw sequences matched across all six workloads. Narrative results were
unchanged by temperature. Each workload appended six public inspection outcomes
and retained the conditional pickup as a pending player choice. Higher success
counts do not establish better gameplay. Actual current local timings, context
retrieval, snapshot sizes and zero scripted-model-call counts are in
`resolution_comparison.json`; no remote publication is implied.

## Known boundaries

- The experiment is versioned and opt-in per submitted turn. Legacy action
  envelopes and historical roll records are not transformed retroactively.
- The source roller is reused, not replaced. Raw fields remain raw; effective
  totals live in additive metadata and appear correctly in public history.
- Private target/margin/task calculations and causal candidates are excluded
  from public resolution serialization. Public points never guarantee effects.
- The broader opportunity/consequence budget is provisional. The candidate
  exposes a validated-candidate assessment hook, not a new canonical Chaos
  relationship generator or automatic effect-spending engine.
- The experimental dice adapter supports one roll per action/step/actor/kind.
  More complex repeated-roll steps need explicit decomposition or a reviewed
  roll-plan contract. A new key is not permission to reroll.
- Legacy interrupted rolls and once-only `--advance-turn` recovery need a
  reviewed integration path. No automatic legacy-state repair is performed.
- Public resolution records are checked against the authoritative roll, original
  declaration, settings and step. Private numeric fields and NPC/GM resolution
  metadata cannot be committed through this public metadata lane. New experimental
  mechanic corrections need a reviewed append-only correction-record contract;
  the original roll record itself cannot be edited. Existing legacy repair tests pass.
- Native Windows, live remote failure injection, provider authentication,
  actual model-usage telemetry and mobile Safari remain untested.

## Rollback procedure

Production needs no rollback: this candidate has not been deployed.

For a future authorized staging run, first pause claims in that staging
environment. Preserve action rows, CAS versions, leases, all public/hidden logs,
the private dice pending journal, receipts, action/roll bindings and execution
records. Drain or hold processing actions before changing worker code.

Recover accepted dice and ledger transactions with the **exact same** immutable
request under the original compatible resolver. Do not delete pending journals,
truncate logs, reseed dice, rename roll keys or replay an action as a new turn.
Any divergent bytes require explicit GM/owner reconciliation. Keep the previous
public snapshot until its page set is fully published; retry publication without
re-adjudicating or rolling again.

Disable experimental resolution only for future submissions, and restore the
previous staging worker/UI version after pending work is safely held or drained.
Keep the v1 reader/replay code for already recorded results. Do not reinterpret
Heroic/Legendary history as Regular. If an authoritative committed outcome needs
correction, use the existing adjudicated append-only void/replacement procedure,
preserving declarations, dice and unaffected dependencies. No Git reset or
campaign database rollback is part of this procedure.

## GitHub assembly boundary

Automatic review rejected restaging references to existing Hask Meadow private
files while reproducing the local refresh merge. That operation was not bypassed
or retried further. The remote candidate instead starts with the existing live
tree and applies only code, tests and reports; campaign and shared character paths
are absent from all write entries. Its resulting full tree is checked against
the tested local candidate before the isolated branch reference moves. Prepared
small development commits are retained as review history; later local refresh
commits are represented by this code-only final assembly.

## Approval boundary

Release status is **HOLD**. This is a reviewable candidate, not an approval-ready
production rollout. The dedicated staging URL/project, non-live campaign identity,
access method and prior model-usage baseline are needed to complete the remote
gates. Do not merge, deploy, activate these modes, republish the Claude Artifact
or invoke the Hask Meadow worker until those gates pass and the owner approves.
