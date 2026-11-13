# Canonical dice recovery reconciliation — HOLD

New isolated branch: `rc/canonical-dice-recovery-f241ea6`.
The canonical commit has exactly one parent, the unchanged base
`f241ea6ef6e470b83d412ac3cbc25907b144ace5`.

Compared immutable inputs:

| Candidate | Branch | Commit |
| --- | --- | --- |
| A | `dev/legacy-dice-recovery-f241ea6` | `97620de2e903c0c076a5ccf06720303c82366adb` |
| B | `dev/legacy-dice-crash-recovery-f241ea6` | `883308ea5c891f9540740c3bc84c263a9af2eb64` |

Both candidate branches remain intact. No merge between them was performed.
The live campaign branch was observed at `6a956071` during read-only inspection;
its later code and records were neither incorporated nor overwritten here.

## Selection

Use **B's single `dice_transaction.py` implementation as the foundation**, with
A's audit/batch barriers, directory durability, and unique regression coverage.
B provides the clearer unkeyed recovery contract, a versioned journal containing
the original request, receipts for every accepted operation, and validation of
both public and hidden logs even when an operation appends to neither/only one.

This branch contains one legacy transaction implementation. A's `transactions.py`
is not installed alongside it. The pre-existing sandbox experimental adapter
remains separate and shares the same lock and pending barriers; it was not
rewritten or duplicated. Pure RNG/formula/face-selection functions are unchanged.

## Code-level comparison

References in this table refer to the paths **at the pinned input commits**.
The canonical paths use B's file and journal names.

| Concern | Candidate A | Candidate B | Canonical decision |
| --- | --- | --- | --- |
| Transaction machinery | `transactions.execute`; unversioned pending plan with fingerprint, streams, before/after cursor and result | `dice_transaction.execute`; v1 plan also retains original request and receipt ID | B's module and v1 schema; validate version, exact destination set, request fingerprint and receipt identity before recovery |
| Acceptance and durability | Shared writer lock; durable private plan before log append; flushed log, temporary-state replacement, directory sync; explicitly syncs campaign directory for new `hidden/` | Same ordering; creates/syncs receipt directory before acceptance; log/state writes split and flushed twice; omits explicit campaign-directory sync after creating `hidden/` | B ordering plus A's campaign-directory sync; retain file flushes and directory syncs |
| Partial writes | Complete an exact matching suffix; reject changed prefix/suffix or cursor; tests intercept real writes including journal/receipt temporaries | Same matching-prefix recovery; explicit partial-log and partial-state hooks; tests accumulate nonempty prefixes | Retain both styles of fault injection and both fixture strategies; never truncate or regenerate accepted dice |
| Cursor/history checks | Public sequence/count/current-turn draws; hidden log completeness checked only when appending a DC | `validate_cursor` checks both logs on every new roll/advance, plus duplicate/orphan hidden roll IDs | Retain B's checks, including untouched streams in every pending plan |
| Receipts | Keyed operations only; private result/fingerprint; exact completed keyed retry returns original result | Every operation has receipt; unkeyed uses a private generated ID; completed keyed retries also survive later operations | Retain B's receipt behavior; additionally reject a pending operation's existing receipt if it differs from the accepted plan |
| Stable request IDs | Up to 200 characters, validated inside transaction module | Same CLI restriction; transaction function itself lacked this validation | Validate in CLI and transaction API; IDs are immutable, case-sensitive operation identities, not roll authorization |
| Unkeyed interruption | Repeating identical arguments implicitly resumes pending; a following call is a fresh operation | Repeated unkeyed invocation refuses; `--recover-pending` explicitly finishes only the pending operation | Select B's explicit recovery semantics; A's one differing test expectation is updated accordingly |
| No pending operation | Ordinary unkeyed invocation starts a fresh operation; no explicit recovery command | `--recover-pending` refuses and cannot infer a lost completed unkeyed response | Retain B; internal unkeyed receipts do not make repeated ordinary commands idempotent |
| Ledger/public readers | `ledger.read_jsonl` barrier plus locked RNG audit barrier | Ledger barrier, but RNG audit reads files directly | A's locked audit barrier plus both candidate pending filenames in ledger/audit guards |
| Ledger batch receipt replay | A's added check runs before returning an existing batch receipt | Existing batch receipt can return before ledger validation encounters the dice barrier | Retain A's early guard for legacy and experimental pending dice, including receipt replay |
| Experimental adapter | Stops on A pending journal before new rolls or receipt replay | Stops on B pending journal | Stop on either filename; no format migration or reroll |
| Response-loss window | Keyed receipt precedes pending unlink; exact keyed retry is safe after completion before stdout | Same; unkeyed receipt also persisted | Retain keyed replay. An unkeyed lost response after pending removal still requires manual log inspection |
| Successful legacy calls | Same roller output and normal CLI arguments; formerly ignored combinations for turn advance remain accepted | Same normal output; rejects formula/DC/purpose/by/mode combined with advance and rejects mixed recovery/new-operation arguments | Select B's stricter validation; normal successful roll and advance invocations remain compatible |
| Persisted compatibility | A pending/receipt filenames and Unicode fingerprint serialization differ from B | v1 B journals and receipts use the selected format | Recover existing B v1 fixture exactly. Refuse A pending artifacts or a nonempty A receipt directory; require original compatible resolver or a reviewed migration |

## Reproduced gaps and fixes

Synthetic subprocess probes against the pinned input code confirmed:

| Probe (true indicates a gap) | A | B | Canonical |
| --- | --- | --- | --- |
| RNG audit certifies a pending transaction at the receipt boundary | false | true | false |
| Completed batch receipt bypasses a pending dice barrier | false | true | false |
| Pending recovery overwrites an already divergent receipt | true | true | false |
| Turn advance accepts a torn hidden DC log without a journal | true | false | false |

The probes use fresh synthetic campaigns with seed 99, not source campaign
records. Results are in `verification/dice_reconciliation/comparison_probes.json`.
Canonical regression cases cover each refusal. Journal version/destination/request
binding checks and clean rejection of malformed completed receipts add further
fail-closed behavior. No authentication or adversarial local-filesystem guarantee
is claimed; private plans/receipts remain trusted local runtime records.

## One recovery contract

1. Assign a stable request ID **before** every worker roll and every turn advance.
   Use distinct operation/step IDs and preserve the original arguments. Renaming
   an ID is a new request, not permission to reroll. The worker must still retain
   its immutable validated action/step plan; this CLI does not authorize rolls.
2. Before durable journal acceptance, no authoritative log or cursor is changed.
   A torn journal temporary may be replaced by a fresh valid invocation. If a
   new campaign's random seed had not yet been accepted, no result was binding.
3. After acceptance, only the exact keyed request or explicit recovery may
   continue. Recovery validates every log and the cursor, then finishes accepted
   bytes without calling result generation. Conflicting requests stop.
4. Interrupted unkeyed requests **always require** `--recover-pending`. An
   ordinary unkeyed call cannot be used to implicitly resume them. Successful
   unkeyed calls remain distinct operations for backward compatibility.
5. `--recover-pending` takes only campaign selection; it finishes the single
   accepted pending operation, whether keyed or unkeyed. It cannot begin a roll
   or turn advance. With no pending journal it fails. A keyed operation recovered
   explicitly keeps its original request ID and receipt.
6. Logs are flushed before atomic cursor replacement. The matching receipt is
   durable before pending removal. A keyed retry returns that receipt even after
   later rolls/turns, without resetting their cursor. A divergent existing receipt
   alongside pending stops recovery rather than being overwritten.
7. Preserve pending files, private receipts and exact log bytes during recovery
   or rollback. Never truncate, reseed, rename keys, delete barriers or guess a
   plan for an old interrupted write. Unsupported/foreign journals stop.

Examples for a **future authorized non-live staging directory**:

```sh
python -B .claude/skills/litrpg-dice/roll.py --campaign "$STAGING_CAMPAIGN" --advance-turn --request-id 'ACTION_ID:advance'
python -B .claude/skills/litrpg-dice/roll.py '1d20+3' --campaign "$STAGING_CAMPAIGN" --by aero --purpose 'Public inspection' --dc 10 --request-id 'ACTION_ID:STEP_ID:check'
python -B .claude/skills/litrpg-dice/roll.py --campaign "$STAGING_CAMPAIGN" --recover-pending
```

CLI results remain GM-private when they contain a hidden DC's success/failure.
Public roll logs contain no DC, outcome, seed, request ID, receipt or journal.
No new player-facing field or frontend behavior is introduced.

## Test preservation and confirmed verification

The combined test file retains A's 11 cases and B's nine cases as separately
named groups. This deliberately retains two valuable strategies: A resets each
boundary fixture and intercepts low-level writes; B builds successive operations
over nonempty log prefixes. A's implicit-unkeyed recovery expectation is the only
intentional semantic change. Its test now asserts refusal followed by explicit
recovery. Hook and filename adaptations target the single selected resolver.

Ten additional canonical cases cover divergent receipts, unused streams,
interrupted explicit recovery, keyed explicit recovery, an exact B-produced v1
journal, A-artifact refusal, changed journal contracts, duplicate/orphan DC rows,
invalid flag combinations, and rename/unlink-before-directory-sync deaths.
The B fixture is synthetic and was captured from the pinned B commit.

The full **21-script Python regression suite passes**, including the 19-case
experimental suite and the **30-case combined recovery suite**. The latter
observes **55 real subprocess terminations**: 22 in retained A coverage, 23 in
retained B coverage, and 10 in added canonical coverage. B's original headline
16 describes its main ten-roll/six-advance boundary matrix; seven other test
terminations also execute. Counts here come from observed child exit codes,
not an addition of the two agents' headline figures.

No-generation assertions cover accepted keyed/unkeyed recovery and lost-response
retry. Independent JavaScript RNG replay runs after recovery and against the
unchanged frozen campaign copy: **355/355 records verified**. `mulberry`, `parse`
and `do_roll` ASTs match the base exactly. **251 protected tracked files** are
hashed before/after all regressions,
and protected paths have an empty diff from `f241ea6`. Aggregate results, the
termination matrix, RNG replay and isolation checks are in
`verification/dice_reconciliation/`.

Reproduce from the repository root:

```sh
mkdir -p development/.qa/tmp
export TMPDIR="$PWD/development/.qa/tmp"
export PYTHONDONTWRITEBYTECODE=1
python -I -B .claude/skills/litrpg-dice/test_roll.py
python -B development/test_legacy_dice_recovery.py
python -B development/experimental_resolution/test_resolution.py
```

The exact complete suite list and invocation flags are recorded in
`verification/dice_reconciliation/python_tests.json`. No frontend files changed;
the prior seven browser-suite results remain historical evidence and were not
rerun for this backend reconciliation.

## Limits and release blockers

Release remains **HOLD**. This commit selects a canonical local candidate; it
neither merges into production nor approves staging or deployment.

- A dedicated authorized non-live staging target, campaign identity and access
  method are still required for actual remote queue/CAS/lease/publication tests.
- A complete GM-generated remote staging turn, provider refresh privacy checks,
  and actual provider latency/tokens/model-call measurements remain unverified.
  Comparable historical usage data is needed for an honest baseline comparison.
- Real mobile Safari, native Windows, network filesystems, hardware/power-loss
  and disk-failure behavior remain untested. Process death between rename/unlink
  and directory sync is tested, but does not simulate power loss. Windows has no
  portable directory-fsync guarantee in the existing shared helper.
- Local writer locks are not distributed worker leases. A worker must adopt
  stable IDs and retain validated roll plans; this commit does not activate or
  migrate the live worker. Split flushes add local I/O; no provider-latency gain
  is claimed.
- Older unjournaled cursor/log divergence still needs owner reconciliation.
  A-format journals/receipts are not auto-migrated. Completed receipts return
  recorded output and do not independently certify unrelated historical bytes;
  independent replay remains the integrity check.
- The frozen base predates newer live Hask Meadow records and code. Reconcile
  those in an isolated future candidate before release, without overwriting them.

No live campaign record, shared character definition, Datapad publication or
worker invocation was modified. Nothing was deployed. Existing candidate
branches and historical release evidence remain available for review.
