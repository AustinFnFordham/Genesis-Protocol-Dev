# Oracle GM release checklist for `01e77407`

The release revalidation on Linux x86_64 passed 89 provider and 15 conformance tests with MCP 1.29.0, PyJWT 2.13.0 and httpx 0.28.1. The provider suite includes a signed full turn through an isolated Git authority and verifies that ordinary startup and public reads leave the authority unchanged even when upstream has advanced. Eight startup/deployment tests also passed separately at rollback SHA `8bd0aee`. Host preflight remains required because these fixtures do not establish the running Oracle build, installed dependencies, effective service configuration or current OAuth grants.

## Before approval

- Work from the existing authorized Oracle SSH session. Record `systemctl is-active genesis-gateway.service`, the deployed application HEAD and branch, service unit fragment and drop-in paths, Python, Node and Git versions, and installed MCP dependency versions. Compare the deployed checkout and dependencies to the reviewed fixture. Inspect the effective environment only in a privileged process and record booleans for write enablement, provider mapping, GM credential presence and distinctness, issuer/resource match and pinned-generation match. Keep tokens, client IDs and environment bytes out of terminal and chat output.
- Use only the existing deployment checkout and service. Confirm the application checkout is clean, and compare the running SHA with the candidate. The reviewed six-file comparison is against `8bd0aee1025694b59fe303d6c1e1e2ca6a4932fc`. A different running SHA requires a fresh diff and rollback review before proceeding.
- Confirm the mount, clean authority branch, recorded upstream and external remote SHA. Use `git ls-remote` from a separate checkout for the external comparison. Never fetch or reconcile from the live authority checkout during this release. Verify the five committed authority inputs using the candidate and record the full input manifest digest. For the observed authority SHA `350c9da29ed2d7d667f147421d9d15b5471cd4d2`, the independently verified manifest digest is `sha256:02005efa82f7c351cda4a5a442aed4c19620d110a2274689cfe54fb29ab91f21`.
- Before and after each preflight, service change and rollback, capture the snapshot below and require exact equality. Also record an authenticated `genesis_refresh` with the public digest, revision, head, generation, recovery flags, action ID, provider, lease and accepted work. The expected baseline is `shared-1` at revision `40` / `evt_0043`, `shared-0002` submitted to `gpt-session`, no lease, tables, rolls or batch, recovery clear. Stop if the baseline has moved and confirm the new state with the owner.

Run the following on Oracle in a root shell. The snapshot prints aggregates and protected file metadata only. Open the existing lock without creating it.

```bash
set -euo pipefail
export GIT_OPTIONAL_LOCKS=0
app=/opt/genesis-code
authority=/var/data/authority
envfile=/etc/genesis/gateway.env
service=genesis-gateway.service
candidate=01e7740719090607bd29190ba07049cde620cd83
rollback=8bd0aee1025694b59fe303d6c1e1e2ca6a4932fc
systemctl is-active "$service"
systemctl show "$service" -p FragmentPath -p DropInPaths -p WorkingDirectory
git -C "$app" status --short --branch
git -C "$app" rev-parse HEAD
mountpoint -q /var/data
test -f "$authority/.git/genesis-operation.lock"
test -f "$authority/.git/genesis-operation.generation.json"

snapshot() (
  flock -s 9
  cd "$authority"
  git symbolic-ref --short HEAD
  git rev-parse HEAD refs/remotes/origin/staging/provider-shared
  test -z "$(git status --porcelain --untracked-files=all)"
  git for-each-ref | sha256sum
  find staging/shared-1 .git -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
  sha256sum "$envfile"
  stat -c '%a %u %g %n' "$envfile"
) 9<"$authority/.git/genesis-operation.lock"

records=$(mktemp -d /root/genesis-01e77407.XXXXXXXX)
chmod 0700 "$records"
snapshot > "$records/before"
test "$(git -C "$app" rev-parse HEAD)" = "$rollback"
test -z "$(git -C "$app" status --porcelain --untracked-files=all)"
```

## After explicit approval for the application release and restart

Fetch only into the application checkout. Run the two `--check` preflights from temporary application worktrees. Use the same service account, venv, environment file and systemd protections. The process needs to open the existing operation lock read/write to lock it. `--check` neither serves requests nor reconciles, and the snapshots verify that the authority is preserved. Compare immediately before switching.

```bash
git -C "$app" fetch --no-tags origin refs/heads/dev/oracle-brief-provenance-rc
test "$(git -C "$app" rev-parse FETCH_HEAD)" = "$candidate"
git -C "$app" merge-base --is-ancestor "$rollback" "$candidate"
git -C "$app" diff --name-status "$rollback" "$candidate"

check_dir=$(mktemp -d /opt/genesis-rc-check.XXXXXXXX)
chmod 0755 "$check_dir"
for sha in "$candidate" "$rollback"; do
  git -C "$app" worktree add --detach "$check_dir/$sha" "$sha"
  systemd-run --wait --pipe --collect -p User=genesis -p Group=genesis \
    -p "WorkingDirectory=$check_dir/$sha" -p "EnvironmentFile=$envfile" \
    -p 'Environment=PYTHONDONTWRITEBYTECODE=1 HOME=/var/lib/genesis' \
    -p ProtectSystem=strict -p ProtectHome=true -p PrivateTmp=true \
    -p NoNewPrivileges=true -p ReadWritePaths=/var/data -p UMask=0077 \
    /opt/genesis-venv/bin/python -B "$check_dir/$sha/development/gm_provider/deploy/oracle/run.py" --check
  git -C "$app" worktree remove "$check_dir/$sha"
done
rmdir "$check_dir"
snapshot > "$records/preflight"
cmp "$records/before" "$records/preflight"
systemctl stop "$service"
git -C "$app" switch --detach "$candidate"
test "$(git -C "$app" rev-parse HEAD)" = "$candidate"
systemctl start "$service"
systemctl is-active "$service"
```

Verify the existing HTTPS discovery route returns 200 and advertises `genesis:read` and `genesis:gm`. Verify unauthenticated `/mcp` returns 401 and an OAuth challenge. Check authenticated refresh, the unchanged cursor and generation, and the provider bindings. No write invocation is part of this release. Compare `snapshot > "$records/after"` followed by `cmp "$records/before" "$records/after"`. If any required check fails, stop and roll back.

```bash
systemctl stop "$service"
git -C "$app" switch --detach "$rollback"
test "$(git -C "$app" rev-parse HEAD)" = "$rollback"
systemctl start "$service"
systemctl is-active "$service"
snapshot > "$records/rollback"
cmp "$records/before" "$records/rollback"
```

Repeat the discovery, challenge and authenticated cursor checks on rollback. This procedure leaves the service unit and environment file in place. It does not replace or restore an older environment backup. A byte or metadata mismatch is an incident, not permission to overwrite an environment file.

## Separate disposable write approval

The exact candidate includes an executable signed external Git authority fixture. Rehearse it before requesting a live write test:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=development/gm_provider python -B -m unittest \
  test_mobile_reconciliation.DiskRecovery.test_signed_codex_context_uses_external_git_authority
```

After separate approval, use the prior Oracle disposable harness with the reviewed SHA. The standard runner binds `/var/data/authority` and `shared-1`, so simply adding a Codex credential to the existing service is unsafe. Validate the harness's temporary authority mount, local bare remote, separate generation, one synthetic action routed to `codex-session`, and denied access from the test process to the live checkout. Pre-arm and rehearse an independent timed restore that removes only the test binding and temp credential, restores the original service and runs integrity checks. If the harness requires a service interruption, the write-test approval must name that interruption. Verify the disposable binding and cursor with writes off before enabling the ephemeral credential. Create the credential only inside a root-owned mode-0600 temporary environment file.

Use signed OAuth and record requested and granted GM scope booleans and the expected read-only scope probe results before enabling writes. After enabling, require `gm_write_ready=true` and the disposable action only. Run claim, context with committed brief provenance, tables, one roll, identical replay, commit and confirmed publication. Release a held lease on failure. On success verify the gateway cleared the lease after publication. Obtain an independent authenticated read of the resulting disposable cursor. Always restore the original binding and verify the full protected snapshot, public cursor, original credential configuration and removal of temporary access before disarming restoration. Never retry a roll with a different request or key.
