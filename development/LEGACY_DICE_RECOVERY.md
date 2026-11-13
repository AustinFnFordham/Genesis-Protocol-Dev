# Legacy dice CLI recovery milestone

Development branch: `dev/legacy-dice-crash-recovery-f241ea6`.
Starting candidate: `f241ea6ef6e470b83d412ac3cbc25907b144ace5` on
`rc/experimental-resolution-acd961c`. Earlier development heads `056b7ba` and
`8f6a641` are already incorporated; none of their implementation was restarted.

Inspection on November 12, 2026 found the live campaign branch at
`cba7266` and main at `1c92850`. The candidate's preserved live base remains
`7845e4c`. This increment builds on the candidate without incorporating,
rewriting or publishing subsequent live turns. The newer live code and records
must be reconciled in an isolated candidate before any future staging release.

## Problem and result

The old failure was reproduced in a disposable campaign: terminate immediately
after the public roll append, leaving one recorded roll with `roll_count=0` and
`draws_used=0`. An ordinary retry could reuse that draw and roll ID.

The CLI now accepts a private durable plan before writing public or hidden logs.
The plan retains exact append suffixes, original prefix hashes, both cursor
versions and the original result. Recovery checks every destination before
finishing any write, completes matching partial suffixes, atomically replaces
the cursor, persists a receipt, then clears the pending barrier. It never
truncates, regenerates accepted dice or infers a repair for old divergence.

The CLI, ledger and experimental adapter share the existing local writer lock.
Ledger readers/public projections and experimental rolling refuse an incomplete
CLI transaction. The CLI also refuses pending ledger/experimental transactions.
Seeds, DCs, requests, receipts and recovery plans stay under `hidden/`; public
roll fields and deterministic RNG/formula/advantage behavior are unchanged.

## Required retry contract

Use a stable ID assigned before invoking each operation. For a future authorized
staging worker, an action ID plus a stable roll-plan slot is suitable. Reuse the
same ID and exact arguments after any timeout, crash or lost response:

```sh
python .claude/skills/litrpg-dice/roll.py --campaign <staging-dir> \
  --advance-turn --request-id '<action-id>:advance'
python .claude/skills/litrpg-dice/roll.py '1d20+3' --campaign <staging-dir> \
  --by aero --purpose '[<action-id>] Inspection' --dc 10 \
  --request-id '<action-id>:inspect:check'
```

A completed retry returns its receipt even after later operations; it does not
advance the turn or draw stream. Reusing an ID with different arguments fails.
IDs do not themselves authorize a new roll: callers must retain the existing
validated action/step plan and must never invent a new ID to retry a roll.

Successful unkeyed legacy calls still represent separate operations. If one
leaves a pending journal, new calls fail until the accepted operation is
explicitly recovered:

```sh
python .claude/skills/litrpg-dice/roll.py --campaign <staging-dir> --recover-pending
```

This command finishes only a pending operation and returns its accepted result;
it never begins another. If an unkeyed response was lost after completion and
journal removal, no command can infer whether an identical invocation is a retry
or a new operation. Consult the authoritative logs; do not blindly repeat it.
Exactly-once completion/response-loss certification therefore requires stable
request IDs for both rolls and `--advance-turn`. Existing workers are not activated
or migrated by this change. No automatic repair of older unjournaled damage is
provided. Keep journals and receipts during rollback; recover using compatible
code before switching writers.

## Verification

All 21 Python regression scripts pass. The new nine-case suite includes real
subprocess termination at ten roll boundaries and six turn-advance boundaries:
acceptance, partial/public/hidden appends, partial/completed state temporary,
state replacement, receipt persistence and completion before stdout. Recovery
runs with result generation replaced by an assertion failure, proving it does
not reroll. Independent JavaScript RNG replay checks the resulting stream.

Additional cases cover changed IDs/arguments, byte divergence, unkeyed recovery,
missing initial state, old cursor/log divergence, writer locking and read barriers.
The experimental suite now verifies that its writer and public projection refuse
a pending CLI roll, then resume after recovery. Its other 18 cases remain intact.
The existing roller parity suite was also run with its required `python -I`.
Three existing scripts require their script directory on Python's import path;
they were rerun successfully with their documented `python -B` invocation after
an initial `-I` import failure. No test behavior was changed for those imports.

Reproduce from the repository root:

```sh
mkdir -p development/.qa/tmp
export TMPDIR="$PWD/development/.qa/tmp"
export PYTHONDONTWRITEBYTECODE=1
python -I -B .claude/skills/litrpg-dice/test_roll.py
python -B development/test_legacy_dice_recovery.py
python -B development/experimental_resolution/test_resolution.py
```

Aggregate timings and gate scope are in
`verification/legacy_dice_recovery/`. Tests write disposable synthetic or sandbox
copies only. Protected campaign/shared-character paths have an empty diff against
the starting candidate. No HTML/JS changed, so the seven prior browser-suite
results are retained historical evidence, not new runs. Native Windows/power-loss
behavior and real mobile Safari remain unverified; these are process-crash tests
on Linux, not hardware failure certification.

## Remaining release gates

The local legacy CLI recovery milestone passes under the explicit retry contract.
Release remains **HOLD**. The next incomplete milestone is remote staging
integration: a dedicated non-live staging target and access method are needed to
exercise queue/CAS/lease/publication and a complete GM-generated turn. Actual
provider latency, tokens and model calls need measurement and a comparable prior
baseline. Real mobile Safari and remote hidden-information checks remain open.
No deployment, production merge, live worker call or campaign write occurred.
