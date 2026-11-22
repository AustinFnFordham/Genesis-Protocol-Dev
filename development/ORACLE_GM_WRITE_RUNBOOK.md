# Oracle shared staging GM writes

Deployment candidate for the existing Oracle pilot, based on `aa6fb5c`. Read-only remains the default. The runner requires a mounted persistent volume, an existing authority checkout, the approved generation, a server-held repository credential, and distinct server-held GM tokens for the enabled providers. It checks Git's push transport under the service identity with a dry-run to an isolated diagnostic ref. The same adapter still verifies Auth0 signature, audience, issuer, owner, client binding, expiration and `genesis:gm` before dispatching to the existing Gateway and GitStore.

## Before write opt-in

- Keep the existing Caddy endpoint, Auth0 audience and client bindings. On the existing Auth0 API authorize `genesis:gm` only for approved owner sessions, then reconnect the intended GPT and/or Gemini client to obtain an access token with both `genesis:read` and `genesis:gm`. The server will not infer scope from login or from the presence of a tool.
- Preserve the authoritative volume. Compare its clean checkout, ancestry, accepted receipts, in-flight action and public cursor to GitHub and MCP refresh using the existing [recovery procedure](SHARED_GATEWAY_RECOVERY_READINESS.md). For this incident the operator reported `staging/provider-shared` at `350c9da`, clean and identical to GitHub. Recheck before approving the existing generation. A missing or replaced marker under a write configuration blocks startup. Do not regenerate or pin a new value just to clear an error.
- Use a server credential scoped to this repository with GitHub Contents write access, subject to the staging branch's rules. GitHub API access from Work and a Codespace user login are separate identities. Store the GitHub credential and provider tokens on Oracle in the existing root-owned mode-0600 environment file. Never paste them into the chat, shell arguments, or a Git remote.

Read-only inspection on Oracle:

```sh
findmnt --mountpoint /var/data
sudo -u genesis git -C /var/data/authority status --short --branch
sudo -u genesis git -C /var/data/authority rev-parse HEAD
sudo -u genesis git -C /var/data/authority ls-remote --exit-code origin refs/heads/staging/provider-shared
sudo -u genesis /opt/genesis-venv/bin/python -c 'import json; from pathlib import Path; print(json.loads(Path("/var/data/authority/.git/genesis-operation.generation.json").read_text())["generation"])'
```

Do not use unauthenticated Git output as evidence of equivalence if fetch or remote lookup fails. Use the approved service credential mechanism to confirm it. The printed value is a storage identifier, not a credential.

## Deployment commands after owner approval

The commands change the application checkout and service configuration only. They use the existing venv and systemd service. Run on Oracle. Check the fetch result against the reviewed commit SHA before checkout.

```sh
sudo git -C /opt/genesis-code status --short
sudo git -C /opt/genesis-code fetch --no-tags origin refs/heads/dev/oracle-opt-in-gm-writes
sudo git -C /opt/genesis-code log -1 --format='%H %s' FETCH_HEAD
```

Continue only with a clean code checkout and the reviewed commit. Stop the service before changing its code. Edit the existing file in place and keep all existing OAuth values.

```sh
sudo systemctl stop genesis-gateway.service
sudo git -C /opt/genesis-code checkout --detach FETCH_HEAD
sudoedit /etc/genesis/gateway.env
sudo chmod 0600 /etc/genesis/gateway.env
```

Set `GENESIS_MCP_ENABLE_WRITES=1`, `GENESIS_STORAGE_GENERATION` to the reviewed UUID, `GENESIS_GITHUB_TOKEN` to the scoped server credential, and `GENESIS_GM_TOKENS` to a JSON object keyed by enabled provider IDs (`gpt-session` and/or `gemini-session`). Use distinct values for each provider. Setting writes to `0` omits the mutation tools, even with otherwise valid configuration.

Run the preflight using the service user and environment file without sourcing secrets in an interactive shell:

```sh
sudo systemd-run --wait --pipe --collect \
  -p User=genesis -p Group=genesis -p WorkingDirectory=/opt/genesis-code \
  -p EnvironmentFile=/etc/genesis/gateway.env \
  -p Environment=HOME=/var/lib/genesis \
  /opt/genesis-venv/bin/python -B /opt/genesis-code/development/gm_provider/deploy/oracle/run.py --check
```

A successful dry-run establishes contact with GitHub's push transport using the configured service credential. It creates no remote ref and cannot prove that GitHub will accept a real update to the protected staging ref. Verify the credential's write scope and staging branch rules separately. An actual gateway-owned write and independent remote observation require an authorized turn, outside this deployment check. On failure use the sanitized diagnostic and stop. The check syncs only a clean authority checkout, fast-forward only.

```sh
sudo install -m 0644 /opt/genesis-code/development/gm_provider/deploy/oracle/genesis-gateway.service /etc/systemd/system/genesis-gateway.service
sudo systemctl daemon-reload
sudo systemctl start genesis-gateway.service
sudo systemctl status genesis-gateway.service --no-pager
```

Use authenticated MCP refresh from each intended client. Expect the correct `connection_provider`, the same pre-deploy campaign cursor, `storage_recovery_required: false`, `read_only: false`, and an empty `gm_write_blockers` list. Verify the eight existing GM tools are discoverable. Confirm a read-scope session remains read-only. Do not claim `shared-0002` as a deployment probe.

## Rollback

Stop the service, set `GENESIS_MCP_ENABLE_WRITES=0` in the environment file, and restart on the previous code. Keep the authority volume, receipts, leases, and storage marker intact. Keep any accepted remote commits if gameplay later occurs.

```sh
sudo systemctl stop genesis-gateway.service
sudoedit /etc/genesis/gateway.env
sudo chmod 0600 /etc/genesis/gateway.env
sudo git -C /opt/genesis-code checkout --detach aa6fb5c667d38f459b730b95bd29edf144cda006
sudo install -m 0644 /opt/genesis-code/development/gm_provider/deploy/oracle/genesis-gateway.service /etc/systemd/system/genesis-gateway.service
sudo systemctl daemon-reload
sudo systemctl start genesis-gateway.service
sudo systemctl status genesis-gateway.service --no-pager
```

Verify authenticated refresh still returns the expected public cursor and read-only status, with GM mutation tools omitted.
