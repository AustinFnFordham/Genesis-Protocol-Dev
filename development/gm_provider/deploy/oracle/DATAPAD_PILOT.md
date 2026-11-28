# Datapad pilot on Oracle

Run the pilot as a separate instance of the existing MCP adapter. Both its
player routes and its GM tools use one GitStore and one operation lock. The
existing `genesis-gateway.service` and its authority stay in place.

## Preflight

1. Prepare a dedicated authority checkout and independent origin containing
   only synthetic pilot authority and the tracked rules inputs. The adapter
   expects branch `staging/provider-shared` and scope
   `staging/datapad-pilot`, with campaign ID `datapad-pilot` and
   `canonical: false`. Use the existing `staging.make_shared` initializer
   against that origin. Confirm the sandbox ledger and empty queue before use.
2. Provision a separate service account, loopback listener port, HTTPS
   resource, and authority mount. Deny the pilot process access to
   `/var/data/authority`, production credentials and canonical campaign
   directories. Initialize the worktree lock and generation once during
   provisioning, then pin the resulting generation in the pilot environment.
   Never generate a replacement marker to make an existing checkpoint pass.
3. Configure `GENESIS_MCP_HOST=127.0.0.1`, an unused `GENESIS_MCP_PORT`,
   the pilot's `GENESIS_STORAGE_GENERATION`, and the exact Auth0 issuer,
   resource, subject and distinct OAuth client mapping using the existing
   `GENESIS_MCP_*` settings. Give only approved pilot providers distinct
   server-held `GENESIS_GM_TOKENS`. Register the pilot audience and verify
   the intended client can obtain `genesis:gm` for that resource.
4. Set a distinct random `GENESIS_DATAPAD_PILOT_PLAYER_TOKEN` in the pilot
   environment and the private Datapad's server runtime. It accepts 32–128
   URL-safe characters. Keep it out of the browser, URLs and logs. Terminate
   public HTTPS at the existing proxy, with routes restricted to this separate
   pilot listener. The browser talks only to the signed-in Datapad.

```sh
cd /opt/genesis-pilot-code
/opt/genesis-venv/bin/python -B development/gm_provider/mcp_adapter.py \
  --shared /var/lib/genesis-datapad-pilot/authority/staging/datapad-pilot --check
```

Use the same invocation without `--check` in the separate pilot unit.
Start with `GENESIS_MCP_ENABLE_WRITES=0` and verify TLS, signed refresh,
storage generation and the cursor. Confirm unauthenticated player requests
receive 401, other campaigns receive 404, and the GM token cannot be used as
a player token. Validate push permission against the dedicated pilot origin.
Enable writes only on the pilot and confirm the signed GM scope probe has no
write blockers.

## Player contract

The Datapad server sends `X-Genesis-Player-Token` on these requests:

- `GET /v1/campaigns/datapad-pilot/state`
- `GET /v1/campaigns/datapad-pilot/pages/{page_id}`
- `POST /v1/campaigns/datapad-pilot/actions`
- `GET /v1/campaigns/datapad-pilot/actions/{action_id}`

Submit the existing turn-contract envelope with an explicit configured
`gm_provider`. The server preserves the declaration, action ID and source
cursor. A queued response means the request awaits the routed GM. Poll its
status, and load public state once publication completes. Retrying the same
action ID requires the same declaration. This surface exposes neither GM
credentials nor rerouting, GM context or internal HTTP GM endpoints.

## Acceptance and rollback

Submit one fresh synthetic custom plan from the pilot Datapad. Verify the
authenticated GM receives its exact declaration. Publish once, replay any
accepted roll with the identical request, and compare the Datapad cursor with
the GM refresh. Record completed and pending steps from the authoritative
result. Have Gemini read the same public cursor with its own signed client
before authorizing a separate Gemini turn.

If verification fails, disable the pilot Datapad binding and remove the
pilot proxy route, then stop only the pilot unit. Preserve its Git ledger
and receipts for diagnosis. Verify the existing gateway and protected cursor.
