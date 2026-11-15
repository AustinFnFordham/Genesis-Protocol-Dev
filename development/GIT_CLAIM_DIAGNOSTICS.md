# Shared Git claim diagnostics repair

## Observed failure

The shell Git transport cannot obtain usable HTTPS authentication. A non-mutating
push dry-run of the existing shared HEAD back to the same ref and a subsequent
ordinary push of **only the isolated development branch** both returned:

```text
exit code: 128
classification: authentication_or_permission
fatal: could not read Username for '[redacted-url]': terminal prompts disabled
```

The old adapter discarded the original failed push's stderr. This is a fresh,
same-transport reproduction, not recovery of that historical buffer. It provides
no evidence of a competing worker. Server-side write permissions and branch
protection cannot be determined until authentication works.

Read access works. The connected GitHub API can write this separate development
branch; that permission does not configure credentials for the shell Git used by
the gameplay harness. Campaign processing remains blocked on an approved,
CLI-compatible credential helper or authenticated Git transport. No credentials
were printed, created, or changed during this repair.

## Cause and correction

Previously `GitStore._push` returned false for every push failure, `put` converted
false into a generic document `Conflict`, and `Gateway.claim` converted that into
`PROVIDER_BUSY: lost the race for the campaign lease`.

The adapter now preserves the subprocess exit code and a privacy-filtered
diagnostic. CLI startup, runner, and HTTP boundaries retain the typed error.

| Evidence | Error code | Meaning |
| --- | --- | --- |
| Explicit authentication/access denial | `GIT_AUTH_OR_PERMISSION` | Credentials or repository permissions |
| Explicit protected branch/repository rules rejection | `GIT_PROTECTED_BRANCH` | Server policy rejection |
| DNS, connection, TLS, RPC failure or timeout | `GIT_TRANSPORT` | Transport failed; acceptance can be uncertain |
| Non-fast-forward, stale ref or Git ref CAS rejection | `GIT_STALE_REF` | Ref conflict, not evidence of a lease holder |
| Unidentified server hook rejection | `GIT_HOOK_REJECTED` | Hook rejected; policy reason not established |
| Unrecognized Git failure | `GIT_FAILED` | No speculative classification |
| Local history unconfirmed on shared ref | `GIT_SYNC_REQUIRED` | Reconcile read-only before further writes |
| Document CAS rejected without verified holder | `CLAIM_CAS_CONFLICT` | No competing live holder verified |
| Observed unexpired lease held by a different run | `PROVIDER_BUSY` | Competing holder verified |

Timeouts have a null exit code rather than an invented one. Diagnostics remove
URLs, credentials, authorization headers and unrecognized hook output. Known
reason fragments survive; arbitrary server prose is intentionally omitted to
avoid leaking private content. Raw subprocess arguments/output are never exposed
through the error response.

Normal non-force push remains the shared-ref CAS. Definitive rejection restores
only the newly created, unaccepted local document/commit. An indeterminate push
keeps local work because the server may have accepted it. A local-ahead fence
blocks subsequent reads/writes until remote history confirms the commit or the
operator reconciles it. Failed synchronization never populates the success cache.
A lost-acknowledgement test verifies that an accepted lease is preserved and the
adapter does not issue a second push. No persisted lease is deleted by recovery.

## Files and validation

Runtime changes are limited to `development/gm_provider/`: `store.py`,
`gateway.py`, `git_errors.py`, `gmctl.py`, `runner.py`, `service.py`, and
`SESSION_GM.md`. `test_git_diagnostics.py` adds the focused regressions.

Final run: **47 unittest cases passed**, plus the NPC-review script. Suites ran
in parallel with isolated temporary fixtures; times below include contention and
are validation durations, not gameplay performance benchmarks.

| Suite | Result | Process duration |
| --- | --- | --- |
| `test_git_diagnostics.py` | 15 passed | 2.36 s |
| `test_shared_store.py` | 4 passed | 16.13 s |
| `test_gateway.py` | 23 passed | 34.03 s |
| `test_service.py` | 5 passed | 10.24 s |
| `test_npc_review.py` | Passed | 0.04 s |

Focused coverage includes all failure classes, secret/private canary filtering,
CLI initialization and HTTP errors, claim propagation, no model calls after claim
failure, CAS with/without a verified holder, a real local-bare-repository
non-fast-forward race, rejection cleanup, push timeouts, remote acceptance with a
lost acknowledgement, and repeated-read/restarted-process fences. Tests use
local bare remotes or copied noncanonical campaign fixtures. No live remote claim
or GM turn was executed. This is not a full repository regression run.

Reproduce from the repository root:

```sh
mkdir -p development/.qa/tmp
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$PWD/development/.qa/tmp"
python development/gm_provider/test_git_diagnostics.py
python development/gm_provider/test_shared_store.py
python development/gm_provider/test_gateway.py
python development/gm_provider/test_service.py
python development/gm_provider/test_npc_review.py
```

## Isolation and release boundary

Base: `350c9da29ed2d7d667f147421d9d15b5471cd4d2` on
`staging/provider-shared`. Repair branch: `dev/git-claim-diagnostics-350c9da`.

`shared-0002` remains version 1, submitted to `gpt-session`. The lease remains
version 5 with no holder. There are no experimental claim/roll/commit/publication
writes to the real staging scope. The 146 explicitly protected files under
`staging/shared-1`, `campaigns`, and `api_bridge/gm` remain byte-identical. A broader
hash check verifies every tracked file outside `development/` against the base,
and the original checkout remains clean and byte-identical. The remote shared
branch is still at the base commit. See the verification JSON for exact counts
and digests.

Local implementation commits: `fe1bf598642e29b14ca8ee1b93efa5c240c817c2`
and `c7390c165fb02ffd81c32bc6ae82a526bfbbd10b`. Equivalent GitHub API commits
are `4e9bfdf27015b6021154e623d2d60ad3ce4b823a` and
`e76b15effbad90925ce5e649fefd109b18214d51`; corresponding tree hashes were
checked for exact equality before publication. API commit metadata differs from
local commit metadata.

Evidence: `verification/git-claim-diagnostics/` contains sanitized transport and
development-push results, final test output and isolation checks.

Implemented and tested locally; saved on the isolated development branch. **Not
merged, deployed, or applied to the staging gameplay worker.** Real authenticated
remote claim/CAS and server-policy integration remain untested. No live Hask
Meadow data, registry, shared character definitions or Datapad were changed.

Rollback: no campaign rollback is needed because no campaign state changed.
Discard the isolated development worktree/branch, or revert these development
commits on that branch. Do not reset shared history, force-push, delete leases,
retry the queued turn, or reroll as part of this repair.
