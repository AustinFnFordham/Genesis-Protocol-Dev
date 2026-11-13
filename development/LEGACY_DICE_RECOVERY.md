# Legacy dice recovery milestone

Development branch: `dev/legacy-dice-recovery-f241ea6`.
Starting candidate: `f241ea6ef6e470b83d412ac3cbc25907b144ace5`.

## Inspected state and selected milestone

The most recent development candidate incorporates the worker verification
branch at `8f6a641` and the preceding dice-history/compact-brief implementation
at `056b7ba`. Its release gate remains HOLD. The recorded legacy CLI crash gate
failed because public append could precede cursor replacement. That failed local
milestone is the only milestone continued here. Existing development and the
candidate's campaign records are retained, with no rebase or live refresh merge.

The live `litrpg/campaign-scaffold` branch advanced from `79adeae` to `cba7266`
during read-only inspection. This follow-up starts on the frozen candidate;
it does not replace, merge, modify or publish the advancing live branch. Future
release assembly still needs explicit reconciliation of newer live work.

## Result

`roll.py` now prepares exact public/hidden log suffixes, the before/after cursor
and the original CLI result in a durable private pending journal. The existing
campaign writer lock serializes it with ledger batches and the experimental
adapter. All stream prefixes/suffixes and the cursor must match before recovery
writes anything. Torn suffixes resume; changed bytes stop for manual review.
The cursor is flushed to a temporary file and atomically replaced only after log
flushes. A keyed receipt is durable before the pending barrier is removed.

Readers, RNG audits, ledger batches (including receipt retries), and experimental
rolls refuse incomplete legacy transactions. The legacy CLI likewise refuses
pending experimental or ledger transactions. Original RNG, formula parsing,
advantage selection, raw roll fields, DC privacy and successful CLI output retain
their meanings. No seed, DC, receipt or private journal is added to public output.

## Retry contract

For a future authorized staging worker, assign one stable ID per operation:

```sh
python -B .claude/skills/litrpg-dice/roll.py --campaign "$STAGING_CAMPAIGN" --advance-turn --request-id 'ACTION_ID:advance'
python -B .claude/skills/litrpg-dice/roll.py '1d20+3' --campaign "$STAGING_CAMPAIGN" --by aero --purpose 'Public check' --dc 10 --request-id 'ACTION_ID:STEP_ID:check'
```

Retry with the exact original arguments and ID. An accepted pending request
resumes saved bytes before any roller call. A completed ID returns its original
result without altering subsequent rolls or resetting the draw cursor. Reusing
that ID with changed arguments fails. This CLI does not authenticate operation
IDs or authorize additional rolls: a new ID is a new request, and the worker
must preserve its immutable action/step binding. The experimental adapter's
existing stronger step-binding rules remain intact.

Unkeyed commands remain compatible. They can recover a matching pending journal,
but after it clears a repeated command is a new roll/turn advance. Thus exactly
once behavior after a lost completed response requires `--request-id`; it is not
claimed for unkeyed commands. Turn advances and rolls are separate transactions;
a worker must retry the same advance ID before continuing its saved roll plan.
No automatic worker integration or live activation is included in this milestone.

Do not delete private pending files, receipts or temporary journals to bypass a
barrier. Do not truncate logs, reseed, rename retry IDs, or infer a recovery plan
for an older interruption. Old divergent log/cursor pairs without a journal
still require explicit owner reconciliation. An existing completed receipt is
returned as recorded; it is not a certification that unrelated historical bytes
have remained unchanged. Independent replay remains the integrity check.

## Verification

All 21 Python regression scripts passed. The 20 retained scripts cover dice,
independent JavaScript RNG replay, ledger validation/batches, compact briefs,
checkpoints, action contracts, sequencing, public projections, snapshot budgets,
provider refresh fixtures, progress and the local worker round trip. The retained
experimental suite has 19 cases; its former legacy failure characterization now
checks the pending barrier, exact recovery and a subsequent experimental roll.

The new suite has 11 cases and performs 22 real subprocess terminations across
transaction boundaries and partial writes. It covers public and hidden append,
state temporary/replacement, journal temporary, receipt temporary/completion,
no-RNG recovery, exact repeat output, changed arguments, divergent streams and
cursor, once-only turn advance even after subsequent rolls, shared locks,
reader/batch barriers, unkeyed compatibility and new-campaign initialization.
Independent RNG replay and public-field privacy are checked after recovery.

```sh
mkdir -p development/.qa/tmp
export TMPDIR="$PWD/development/.qa/tmp"
export PYTHONDONTWRITEBYTECODE=1
python -I .claude/skills/litrpg-dice/test_roll.py
python -B development/test_legacy_dice_recovery.py
python -B development/experimental_resolution/test_resolution.py
```

Aggregate results and protected-tree checks are in
`verification/legacy_dice_recovery/`. Earlier candidate evidence remains
unchanged. This is local Linux process-death testing, not power-loss, filesystem
fault, native Windows, remote worker, provider or Safari certification. No
frontend files changed; browser suites were not rerun for this increment.

## Remaining release gates

The release remains **HOLD**. Next is an authorized dedicated staging target
with a non-live campaign identity and access method, to exercise actual queue
CAS/leases and publication, then a full GM-generated remote staging turn. Actual
provider latency/tokens/model calls need a comparable baseline. Real mobile
Safari and remote hidden-data/refresh checks remain open. None were simulated
and reported as remote success. No deployment, live worker invocation, campaign
record modification or Datapad republication occurred.
