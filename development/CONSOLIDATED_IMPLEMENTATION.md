# Consolidated development handoff

Base commit 7ac860a4dce5e75777ab808f1b2c97ff8cbe3f66.
Branch dev/dice-history-gm-brief-cc9cfc5.
All implementation and verification described here is development work. The
production branch, live campaign, registry, database and Claude Artifact are
unchanged. No live workflow or deployment certification is claimed.

## Measured results

| Measure | Before | After |
| --- | --- | --- |
| Snapshot bytes at public revision 705 | 95,920 | 82,173 |
| Headroom under 96,000 bytes | 80 | 13,827 |
| Snapshot trimming target | Ceiling only | 84,000 bytes with a 96,000-byte ceiling |
| Equivalent 20-event workload, median of five runs | 804.45 ms, 20 CLI invocations | 41.55 ms, one CLI invocation |
| Public full-history availability | Feed, Journal and dice pages | Also Chapters, Events and shared-experience pages |
| RNG replay audit | Existing audit retained | 225/225 historical records still verify; original future advantage faces retained |

Benchmark figures are local CLI wall time. No remote round-trip latency or live
model turn speed is inferred. All history remains in page documents within
150,000 bytes. Snapshot previews may shrink while authoritative data remains
in the ledger and complete page set.

## Commits and files

These are local development commit references. REMOTE_COMMITS.json, when present,
maps them to the equivalent published GitHub commits with identical trees.

| Increment | Commit | Principal files |
| --- | --- | --- |
| Readiness | dca6f7a | dice/roll.py, dice/audit_rng.py, ui/export_state.py, development/test_readiness.py |
| Ordered batches | 060b64e | ledger/batch.py, ledger/ledger.py, ledger/test_batch.py |
| Reader fencing | bba872c | ledger/batch.py and ledger/ledger.py |
| Processing indicator | 457a32b | process-turn/progress.py, ui/src/composer.js |
| Scene and Journal | d4ee5d4 | ui/projections.py, ui/export_state.py, ui/src/core.js, composer.js, turn.py |
| Contest and repair | e0303b2 | ledger/repair.py, process-turn/SKILL.md, composer.js |
| Relationships and SID | eed5433 | ui/projections.py, export_state.py, core.js, development/SID_AND_AUTHORITY.md |
| Campaign and client prototypes | de43673 | development/campaign_genesis/genesis.py, development/interop/public_client.py and INTERFACES.md |
| Lease boundary checks | d2e7570 | ledger/batch.py |
| Portable lock handling | 8b55229 | ledger/batch.py |
| Original rules provenance | 4ef4fdf | campaign_genesis/before_fall_source.json |
| Legacy contest support and dice preservation | 31fe84f | ledger/repair.py, composer.js, ledger/test_batch.py |
| Optional pre-roll review | eab27c6 | process-turn/plan_review.py, SKILL.md, composer.js |
| Enforce original-rules hash | f4bb1e1 | campaign_genesis/genesis.py and foundation acceptance tests |
| Actual source/endpoint test | 122551d | campaign_genesis/example_request.json and foundation_source_test.json |

Skill paths above are under .claude/skills/litrpg-*, and UI paths are under
campaigns/starwars_litrpg/ui/. Generated genesis_datapad.html is rebuilt from
the tracked sources. The exact changed-file list is in verification/changed_files.json.

## Tests and acceptance evidence

Sixteen Python regression scripts pass, retaining the earlier roller, public
projection, compact-brief, validator, sequencer and publication tests. Added
acceptance tests verify:

- Actual first/alternate/selected faces without adding RNG draws, and complete
  paginated history under a reserved snapshot margin.
- Batch crash after a stream write, torn-byte append recovery, duplicate retries,
  separate-process writer rejection, stale revision/lease rejection, causal order,
  visibility split and unchanged dice state/log bytes.
- Monotonic worker stages and real timestamps, completion only after publication,
  and fresh stage timings on a new worker run.
- Five-turn chapter grouping, public citations, rebuilding after an append-only
  void, objective lifecycle and exclusion of hidden events.
- Relationship observations with sourced explicit dimensions and no inferred
  private intent or recruitment outcome.
- Contest dependency closure, preservation of unaffected events, an unfavorable
  outcome refusing correction, missing/incorrect adjudication rejection, and
  rejection of new dice in repair replacements.
- Canonical endpoint/relationship validation, disconnected/ghost endpoint
  rejection, original-rules pass-through and no canonical promotion.
- Independent client processes observing the same public revision before and
  after an append in a temporary campaign copy.

The full compact-brief verifier passes all 874 ledger heads with zero player leaks.
Browser tests pass for the base composer, cinematic sequencer, scene composer,
emulated iPhone, publication/history navigation and the new player-experience flow including optional plan approval/revision requests.
They exercise actual HTML/JS through a mocked database at desktop and phone sizes.
They do not connect to or republish the Claude Artifact, nor simulate Safari itself.

## Operation and recovery

Ledger batches require an immutable request file, batch_id, expected shared ledger
head/revision, complete ordered event drafts and a fresh worker lease. Earlier
batch events may be referenced as '$1', '$2', etc. The accepted journal is durable
before any stream append. Both streams must match the exact accepted prefixes.
While pending, ledger readers fail closed. Retry the same accepted request under a
valid lease before resolving or publishing another turn. No batch operation rolls
dice. Local writer locks supplement the existing external worker lease and CAS
protocol. Directory fsync is available on POSIX; native Windows behavior is
implemented with msvcrt but remains untested.

Progress is an opt-in worker integration through the updated runbook. Generate
phase patches from the current row and lease and apply with the row's if_version
inside existing heartbeat/batch operations. Never advance a stage before work
actually starts. Preserve resolved/publication-pending state if publishing fails.

Contest requests are stored separately from authoritative events. An optional pre-roll review binds the exact declaration, revision and review ID to an explicit player approval. A qualified GM
maps the declaration and step, reviews unlinked later events, supplies rule sources
and a reasoned approval bound to the current head and request hash. The correction
is then an append-only batch, preserving original declarations and rolls. Legacy
declarations without stable step IDs stop for explicit provenance mapping. Repairs
are applied only to marked experimental copies in this increment.

## Prototype limits

The campaign draft CLI composes candidate causal edges from supplied templates and
existing canonical registry records. The inspected index contains 57 entries and
limited actor/faction/era coverage. A valid registry endpoint is not proof of era
or lore compatibility. Generated foundations remain proposed pending authority
review. Prepared possibilities never force a future plot outcome.

BeforeTheFall(1).docx was recovered from Library and its original 30,045 bytes
fingerprinted. The source manifest preserves card suit order, ending card,
resource tiers, projects, telescope effects and renown/scorn constraints. The actual registry endpoints and original source hash were exercised together
in a candidate draft test. A different rules file is rejected by the default
Before the Fall interface. This increment does not alter the original source or
invent the missing card-outcome deck. The chronology game itself is not implemented here.

The public client interoperability test demonstrates read/refresh compatibility.
Actual provider adjudication, remote authentication and cross-provider commit
workflows require future end-to-end tests. Current relationship dimensions remain
empty unless explicit public evidence supplies them. SID Q15/Q16 remain provisional.

## Reproduce

From the repository root:

```sh
python -B development/test_readiness.py
python -B .claude/skills/litrpg-ledger/test_batch.py
python -B development/test_increment_contracts.py
python -B development/test_interop.py
python -B development/benchmark_batch.py
python -B campaigns/starwars_litrpg/ui/build_datapad.py
```

Browser acceptance tests use Playwright with an installed Chromium. Set
GENESIS_TEST_CHROMIUM when supplying an explicit binary and use
development/run_browser_test.cjs with the existing browser regression files.
The new player-experience test uses the public publish-set fixtures in
development/.qa/ui/view/. Those generated fixtures are intentionally ignored.
