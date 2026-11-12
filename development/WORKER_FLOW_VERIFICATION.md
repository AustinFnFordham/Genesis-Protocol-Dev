# Worker flow verification follow-up

Development only. No merge, deployment, database connection, trigger firing or
Claude Artifact publication was performed.

## Source reconciliation

The supplied live HEAD is `a31251790597e9ca1c3140b4ebdd2d937571a9f3`.
At inspection, `litrpg/campaign-scaffold` was
`7b926724e69664926680620992e167834ab0e0bd`. The three intervening commits
(`64e6b17`, `bea84b3`, `7b92672`) contain only Hask Meadow public events,
hidden events, rolls and dice state. Those campaign changes were inspected as
file statistics and were not ported or edited.

Prior development at `056b7ba69dedc7379ab95a62673d1052ffcf5811` descends from
the supplied live HEAD and already contains player dice history, independent RNG
replay verification, the selectively ported compact GM brief, and subsequent
isolated increments. This follow-up branches from that tested work as
`dev/worker-flow-verification-056b7ba`; it does not restart or rebase the old
brief prototype. The prototype's `test_brief.py` is retained, with the hardened
brief implementation and checkpoint tests passing against the current code.

## Changes and commits

| Local commit | Actual files changed | Result |
| --- | --- | --- |
| `4d0ebba` | `.claude/skills/litrpg-process-turn/progress.py`, `development/test_worker_progress.py` | Reject a progress timestamp earlier than the current run's latest heartbeat; preserve repeated-stage start time and fresh retry clocks. |
| `42a002e` | `.claude/skills/litrpg-process-turn/turn.py`, `development/test_action_fences.py` | Check supplied public ledger head and context ID before adjudication. Legacy envelopes without these fields remain valid. Node context files use unique, cleaned temporary directories and honor TMPDIR. |
| `c9cd5ec` | `development/test_worker_roundtrip.py` | Disposable sandbox round trip through actual Node parser/validator, GM brief, roller, ledger batch recovery, public projections and snapshot-last publication, using a local SQLite CAS test double. |

`verification/worker_flow_commits.json` maps local commits to their equivalent
published development commit trees. No changes were made to `turn_contract.js`.

Both correctness bugs were reproduced by failing regression tests before the
fixes: a delayed heartbeat was accepted; incorrect head/context values passed
when the public revision matched. All eight new targeted unit cases now pass.

## Integration evidence

The test copies only the noncanonical sandbox into an automatically removed
directory under `development/.qa/`. It submits the existing holster-blaster
choice and preserves the original declaration. Holstering requires no dice;
one explicitly synthetic diagnostic advantage roll exercises real roll/log
retention and independent replay, without deciding the action's outcome.
GM narration and the next context are scripted fixtures, not model output.

The test records actual worker timestamps through Claimed, Context, Rules,
Dice, Ledger, Narration, Publishing and Complete. It verifies:

- An old queue row version cannot overwrite a claimed row.
- A crash between public and hidden batch appends leaves readers closed and
  progress at Ledger. Exact accepted bytes resume without duplicate events.
- Replaying the accepted batch changes neither the dice state nor roll log.
- An interrupted page publication leaves the old snapshot authoritative and
  the action publication-pending. Complete is rejected before publication.
- Every referenced history page has the expected hash before replacing the
  snapshot. The refreshed narration, inventory, scene, holstered hand and
  existing conditional pending decision match the committed fixture.
- Hidden canary text is absent from public documents and the player brief;
  the exported document set contains no campaign RNG seed.
- Original source run files and the validator remain byte-identical.

This does not exercise an interruption inside the dice CLI's own multi-file
writes. It proves no reroll on accepted ledger-batch retry, not crash atomicity
of the legacy dice CLI. Remote queue leases/CAS and provider authentication
still need a separately authorized integration environment.

## Verification and measurements

All 19 Python regression scripts passed. Their exact paths and timings are in
`verification/worker_flow_tests.json`. The unchanged coverage includes dice,
RNG audit, ledger validation/recovery, compact brief/checkpoints, action
validator, sequencer, scene sequencing, campaign features, snapshot margin,
increment contracts and independent public clients. This follow-up changes no
HTML/JS. Browser suites from the preceding increment were not rerun, and no
new real-device or live-worker verification is claimed.

| Measurement | Before / comparator | Current isolated result |
| --- | --- | --- |
| Compact brief at shared head evt_0874 | Full bundle 147,604 bytes | Compact 41,598 bytes; 71.82% smaller; identical field projection |
| Full replay, median of five | No historical timing comparison claimed | 199.80 ms |
| Verified checkpoint | Prefix verification still replays | 220.47 ms; no speedup claimed |
| Equivalent 20-event CLI workloads, five repeats | Individual writes 951.14 ms median, 20 invocations | Batch 58.11 ms median, one invocation |
| Sandbox public snapshot after round trip | Public revision 35 | Revision 39, 16,613 bytes, five history pages |

Timing reflects this machine and concurrent local test load. CLI batch workloads
are checked for equivalent resulting events. None of these numbers represents
model token savings, remote tool latency or live player turn latency. The existing
12 KB snapshot-margin regression still passes on the frozen Hask Meadow copy.

## Status and remaining work

| Area | Status | Remaining gate |
| --- | --- | --- |
| Dice history, legacy face fidelity, unchanged RNG sequence | Implemented; prior and current regression tests pass | Live publication and real-device inspection untested |
| Compact GM brief | Integrated in development; compatibility/security regressions and benchmark pass | Not activated in the live processor |
| Batch/progress/publication integration | Isolated module-level round trip tested, including interruptions | Real remote worker/CAS/lease lifecycle and artifact transport remain untested |
| Scene/Journal and contest/repair | Existing isolated implementation retained | Prior report's live workflow and legacy dependency-mapping limits still apply |
| Relationships and SID | Existing public evidence projection retained | No new psychological claims; Q15/Q16 remain provisional |
| Campaign Genesis | Existing candidate-only CLI retained | Attached design specification's data-readiness gates, conversational UI, playable chronology and missing card deck remain incomplete |
| Providers | Existing independent public-client refresh test passes again | Claude/ChatGPT/Gemini adjudication interchangeability has not been demonstrated |
| Deployment | Not performed | Requires explicit approval before Claude Artifact republication |

No work in this increment is blocked by a missing original consolidated prompt.
The supplied acceptance criteria remain the development requirements. The attached
Campaign Genesis design specification was inspected and does not license promoting
the existing candidate draft into canonical or runtime-certified campaign truth.

## Reproduce

From the repository root:

```sh
mkdir -p development/.qa/tmp
export TMPDIR="$PWD/development/.qa/tmp"
export PYTHONDONTWRITEBYTECODE=1
python -B development/test_worker_progress.py
python -B development/test_action_fences.py
python -B development/test_worker_roundtrip.py
python -B development/benchmark_brief.py
python -B development/benchmark_batch.py
```

The round-trip report is generated in `development/.qa/worker_roundtrip.json`.
Only aggregate results are checked in. Caches, local test databases, temporary
campaign copies and diagnostic files stay in the ignored experimental location.
