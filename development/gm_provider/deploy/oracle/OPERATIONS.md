# Oracle gateway operations

The systemd unit opens the existing mounted authority checkout. Startup
requires the configured generation, existing operation lock, clean worktree,
expected authority branch and origin, and a HEAD equal to the locally recorded
upstream. It checks for a ledger mid-write without contacting the Git remote.
Oracle public MCP reads also use the local checkout under the operation lock.
Check for remote advances through an explicitly authorized reconciliation.
The guarded GM transaction path retains its existing Git synchronization.

Run the Oracle entry point with `--check` to validate and exit without serving.
The separate `--reconcile` operation can fetch and fast-forward authority. In
explicit bootstrap mode it can also create missing storage. Run it only under
operator authorization, with the service stopped and after verifying the
mount, scope and intended remote state. Reconciliation is outside a routine
application deployment.

## Rollback constraint

A rollback that restarts a revision containing the legacy startup sync can
update authority before the service is healthy. Before deploying under a
strict authority-preservation requirement, have the owner approve a rollback
target that already contains the startup safety fix. Test that target against
a writable fixture that has a newer upstream commit. Preserve the original
environment backup and verify its contents and mode before deployment.

## Authentication acceptance

Use independent OAuth exchanges for GPT, Gemini and Codex. For the first read-only
checkpoint, verify authenticated `genesis_refresh` reports the expected
provider and matching campaign cursor, and confirm Codex reports read-only.
Keep existing grant and token settings intact.

For GM acceptance, first verify the Codex CLI requests the intended scopes and
that the configured issuer grants them to the independent Native client.
Use the scope probe to test the authorization challenge and then report the
granted scopes and write blockers without recording tokens. The Oracle gateway
maps the verified client identity to a provider, requires `genesis:gm`, and
requires that provider's distinct server-held GM credential.

A controlled write acceptance requires separate authorization, a disposable
campaign and an action routed to Codex. Observe claim, context, table
acceptance, roll receipt, commit, publication and lease release. Repeat an
accepted roll request and verify the same receipt and a single ledger entry.
Use a second provider's independent read to check the final cursor. Keep
shared-1 and its pending request outside this exercise.

Codex CLI authorization establishes what the CLI can request. The Oracle
gateway enforces scopes, credential binding, routing and transactions.
ChatGPT custom MCP writes also depend on the particular account, workspace
and client. Confirm that capability with an actual permitted invocation in an
eligible ChatGPT client before claiming native ChatGPT write support.
