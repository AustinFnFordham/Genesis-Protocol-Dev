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

## Campaign-owned brief inputs

For Git-backed campaigns, the brief uses the campaign authority checkout's
charter, turn contract, narrative spec, continuity rule, and Aero runtime
sheet. Startup and GM context check that all five files exist and match
their blobs in one committed authority revision. Untracked, missing,
symlinked, or modified inputs fail validation. The application checkout is
not a fallback for Git-backed authority. The standalone brief CLI retains
its existing local rules and sheet.

The GM brief's `meta.brief_inputs` records the authority commit, a SHA-256
version of the input manifest, and full SHA-256 hashes for the five inputs.
The existing short rules hashes remain available under `meta.ruleset`.
The authority commit can advance through ordinary transactions without
changing the input version. An intentional rules or sheet update requires
an approved authority commit and a corresponding input-version change.

## Deploying the brief provenance release

- Inventory the diff from the running application SHA. Verify the approved
  candidate and rollback revisions in the application repository while
  its worktree is clean. Keep the original gateway environment and service
  binding for the application deployment.
- Under the existing authority operation lock, record the read-only public
  digest, cursor, storage generation, clean authority HEAD, refs, and file
  hashes. Confirm the routed request, lease, roll counts, and recovery
  flags. Verify the five brief inputs against the existing authority commit.
- Switch the existing application to the approved SHA and restart the
  existing systemd service. Verify discovery, the unauthenticated challenge,
  provider bindings, authenticated refresh, and the unchanged authority
  snapshot. Restore the previously running startup-safe SHA and restart
  if a required check fails. Recheck the same snapshot on rollback.
- Treat disposable write acceptance as a separately approved maintenance
  window. Prepare a newly initialized local authority repository and
  local bare remote on a separate mount with a distinct generation.
  Seed the five files from verified committed sources and submit exactly one
  synthetic action routed to `codex-session`. Keep live authority inaccessible
  in the temporary systemd binding. Arm an independent timed restore before
  switching and verify the authenticated disposable binding with writes off.
- Only after that check, generate a fresh Codex GM credential into a root-only
  temporary environment file. Use only the Codex credential there. Preserve
  the original environment file byte for byte and never place credentials in
  command arguments, logs, Git, or transcripts. Recheck readiness using the
  signed scope probe and use one stable run ID.
- Verify claim, context and brief provenance, fixed tables, one accepted roll
  and identical replay, commit, publication, and lease clearance. On an
  ambiguous result, use read-only recovery evidence before any retry.
  On every exit remove the temporary drop-in and credential file, restore
  and restart the original binding, then compare the protected snapshots
  and authenticated cursor. Stop the timed restore only after restoration
  verifies. Never use the live pending request for this test.
