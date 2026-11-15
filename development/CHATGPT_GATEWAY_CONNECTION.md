# ChatGPT session GM connection: prepared, not deployed

Historical GPT-only runbook. The reconciled candidate and current setup are in
`SHARED_MOBILE_GATEWAY_SETUP.md`; its Auth0/JWT and two-client bindings supersede
the introspection-only configuration described below. No original branch was changed.

## Verified status

Diagnostic repair `6942257de29d099e0b6c2ed387812af42d991eb7` exists remotely at
`dev/git-claim-diagnostics-350c9da`. This implementation starts from that commit on
isolated branch `dev/chatgpt-gateway-adapter-6942257` and preserves it.

| Question | Observed answer |
| --- | --- |
| Is a gateway already hosted and reachable? | No gateway deployment/endpoint was found in the repository, environment configuration or connected Sites inspection. This does not establish that no separately managed host exists. |
| Is there a Genesis tool connected here? | No Genesis tool in the available tool inventory; plugin search returned no Genesis connection. |
| Is the existing Datapad an MCP gateway? | No. `get_site(include_mcp_connection=true)` for the discovered Genesis Datapad returned `The published Site does not declare an MCP server.` No enable/republish action was taken. |
| Can persistence stay server-side? | Yes by architecture: the existing `App.gm` invokes the same Gateway and GitStore. A new local-bare-remote integration test verifies lease persistence is observable from an independent clone. Actual authenticated hosting credentials are not available or tested. |
| Was an authenticated remote staging refresh performed? | No: neither an endpoint nor an installed connection is available. Local MCP transport tests are explicitly not remote evidence. |

Repository checks included the current `dev/provider-interchange` head
`9030816280a373bc6ef4ce539d087665728f2fd8`. Its HTTP service and connection
documents still describe hosting as pending; no MCP adapter was found there.
The existing `service.py` already implements provider-token-scoped GM verbs.
`context` renews the lease and records a stage, so it is **not** a read-only refresh.

## Implemented adapter

`gm_provider/mcp_adapter.py` uses the official Python MCP SDK over streamable
HTTP. It binds one existing noncanonical shared campaign and `gpt-session` on
the host. It creates no campaign, SQLite store or secondary queue. There is no
model API call, worker loop, autorun, Claude delegation or alternate commit path.

Tools: `genesis_refresh`, `genesis_page`, `genesis_reference`, `genesis_claim`,
`genesis_context`, `genesis_tables`, `genesis_roll`, `genesis_review`,
`genesis_commit`, `genesis_publish`, `genesis_release`.

Refresh forces a read-only remote sync, returns existing public projections and
recovery flags, and refuses an internally inconsistent revision. Page IDs are
bounded. References are a fixed allowlist of existing GM/rules/Trinity documents;
there is no arbitrary filesystem endpoint. Broader rule/entity lookup can use
the existing authorized GitHub read tools; a new registry search engine is outside
this adapter. Do not reconstruct missing algorithms from their names.

Every mutation uses `App.gm`, its server-held provider token and the existing
Gateway's revision, lease, routing, deterministic dice, recovery, append-only batch
and paginated publication checks. A process lock serializes calls in this server;
cross-process/clone CAS is still the existing non-force Git push. The adapter
never catches a failure and attempts another persistence route. The diagnostic
repair's typed/sanitized Git failures survive through MCP responses.

OAuth access tokens are introspected at a configured trusted HTTPS issuer, with
active status, exact issuer, MCP audience, expiry, scopes and one allowed owner
subject checked on every request. No token cache; issuer/network failure closes
access. Tokens minted for ChatGPT MCP are not forwarded to Git or the internal
GM handler. `genesis:read` permits public reads; writes also require `genesis:gm`
and `GENESIS_MCP_ENABLE_WRITES=1`. Writes default disabled. Tool annotations mark
context as a write and commit as a durable consequence. Unknown errors are
redacted rather than echoed. No live/player routes are added or changed.

## Validation

Five scoped suites passed: **58 tests** total (11 new adapter, 15 diagnostic,
4 shared Git store, 23 gateway, 5 HTTP service). The adapter suite took 4.40 s;
the other suites took 2.48/16.03/32.91/11.19 s in the same parallel run. These are
test durations, not remote service latency measurements. Evidence is in
`verification/chatgpt-gateway-adapter/`.

The real SDK's local ASGI transport returned 401 plus OAuth discovery for an
unauthenticated request; an authenticated test client listed tools and refreshed
a copied sandbox; a claim remained disabled. A separate bare-Git fixture verified
that the MCP dispatch persists a lease through the existing GitStore and a second
clone sees it. A scripted mock GM fixture completed a deterministic turn with a
duplicate roll request, one recorded roll, valid ledger and filtered public pages.
This fixture is not GPT reasoning or the real `shared-0002` turn. Existing suites
cover competing CAS writers, interrupted accepted work, replay/publication and
secret filtering. The actual shared campaign, live files and diagnostic repair
are unchanged; every original tracked file was checked against the base.

To repeat locally, with dependencies already installed:

```sh
mkdir -p development/.qa/tmp
export PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/development/.qa/tmp"
python development/gm_provider/test_mcp_adapter.py
python development/gm_provider/test_git_diagnostics.py
python development/gm_provider/test_shared_store.py
python development/gm_provider/test_gateway.py
python development/gm_provider/test_service.py
```

## Exact remaining setup (not performed)

1. **Choose/authorize a host and OAuth issuer.** A small existing Linux server
   with Python 3.11+, Node 18+, Git, persistent local disk and outbound HTTPS/SSH
   to GitHub is sufficient. Keep one server worker per authoritative checkout;
   never share one worktree among multiple OS worker processes. Do not use an
   ephemeral edge filesystem: accepted-but-unacknowledged Git/dice work must
   survive process restarts. The adapter can share the existing persistence host;
   this executor needs no Git secret. No host is assumed to exist.
2. **Keep code and authority in separate checkouts.** Install this development
   branch in `/srv/genesis-adapter`. Mount/open the existing authoritative
   `staging/provider-shared` checkout at `/srv/genesis-authority`. Use its existing
   `staging/shared-1`; do not call `make` or `make_shared`, copy/replace the queue,
   cherry-pick into the shared campaign branch, or migrate any database. Startup
   refuses canonical scopes and an authority checkout on another branch.
3. **Configure server persistence credentials securely**, or reuse an already
   approved credential mechanism on that host. It must support normal atomic
   Git pushes to this repository's staging branch. Keep credentials in the host's
   secret manager/helper, never in remote URLs, action arguments, this executor
   or logs. Before enabling gameplay, a separately authorized development-branch
   push must verify host write access. No file-by-file connector writes qualify.
4. **Configure the existing OAuth issuer.** Use authorization-code + PKCE S256,
   OAuth/OIDC discovery, and CIMD, DCR or a pre-registered ChatGPT client. Copy
   the exact redirect URI shown by ChatGPT's connection management into the
   issuer allowlist. Register a resource-server introspection client separately
   from that ChatGPT client. Its RFC7662 response must include `active` (boolean),
   `iss` (exact configured issuer), `aud` (MCP resource URL or list containing it),
   `exp` (integer seconds), `sub`, `scope`, `client_id`. Authorize only the owner's
   stable subject, and support `genesis:read` and `genesis:gm`. Some issuers need
   an audience mapper to emit the MCP resource; missing fields fail closed.
5. **Set the server-only inputs from `gm_provider/mcp.env.example`.** Use the
   existing provider GM token if already provisioned; otherwise create it only
   in the approved host secret manager. This task generated no live credential.
   `GENESIS_MCP_ENABLE_WRITES` must remain `0` through initial verification.
6. **Install/run after separate hosting approval.** Isolate dependencies from
   Claude's environment:

   ```sh
   python3 -m venv /srv/genesis-adapter-venv
   /srv/genesis-adapter-venv/bin/pip install -r /srv/genesis-adapter/development/gm_provider/requirements-mcp.txt
   /srv/genesis-adapter-venv/bin/python -B /srv/genesis-adapter/development/gm_provider/mcp_adapter.py --shared /srv/genesis-authority/staging/shared-1
   ```

   Inject secrets via the process manager, not command-line arguments. Run as
   an unprivileged host user. The listener defaults to loopback `127.0.0.1:8789`.
7. **Expose the approved HTTPS endpoint.** Reverse-proxy a stable hostname to
   the listener, preserving Authorization, Host, Accept and MCP protocol/session
   headers; do not redirect POSTs or log authorization bodies/tokens/tool results.
   Use the hostname in `GENESIS_MCP_RESOURCE`. Required paths:

   | Method/path | Purpose |
   | --- | --- |
   | `POST /mcp` | Authenticated initialize, tool discovery and invocation |
   | `GET /mcp` | SDK transport handling; stateless mode does not require resumable SSE |
   | `GET /.well-known/oauth-protected-resource/mcp` | Public OAuth resource metadata |
   | Issuer discovery, authorization, token and introspection endpoints | Supplied by the selected OAuth server |

   The MCP resource must be `https://<approved-host>/mcp` with no credentials,
   query or fragment. The public GM HTTP endpoint need not be exposed: MCP calls
   its existing handler in the same process. No CORS wildcard is required.
8. **Create/connect on ChatGPT web.** Open `https://chatgpt.com/plugins`, choose
   Add custom MCP server, enter that `/mcp` URL, select OAuth, configure the
   issuer's client registration mode, and complete the owner's login. Install
   the resulting plugin. Current official docs describe creation on web and
   available plugins on mobile; actual eligibility/tool availability on Austin's
   account still requires an account-level check. No plugin or login can be
   provisioned here without a deployed endpoint and that setup.
9. **Read-only acceptance first.** Start a new mobile chat, select the Genesis
   plugin and call `genesis_refresh` only. Record the actual tool response's
   campaign, revision, head, pending request and lease state. Compare to another
   authorized client's read, and assert no action/lease/operation/roll/ledger
   file changed. Enable write scope/host switch and execute a turn only under a
   later, separate gameplay authorization.

## Costs and remaining limits

No deployment, billing change or model API usage occurred. The code and local
tests add no model API charge. Session usage remains subject to the ChatGPT plan.
Existing host capacity may avoid a new hosting subscription; electricity,
network, identity hosting, domain and operational costs depend on that host.
For a paid-host example, Railway's published Hobby minimum is $5/month covering
$5 of usage, with higher usage charged above that; volume storage is listed at
$0.15/GB/month. This is an example, not a quote for this unmeasured workload or
an authorization to provision Railway. OAuth provider costs are not determined
until an issuer is selected. No paid provider is required by the adapter itself.

Implemented/tested locally is distinct from deployed/reachable/connected. External
issuer compatibility, real HTTPS/proxy behavior, authenticated remote Git commits,
mobile plugin use and a GPT-authored end-to-end turn remain untested.

**GM privacy limitation:** the public refresh/pages contain no private context,
and private results are explicitly marked GM-only. But ChatGPT lets the account
owner inspect tool payloads; GM context delivered to this session is not a secret
vault hidden from that owner. A player-only account must receive only the public
tools/results or use a separate GM session/private channel. Do not promise hidden
DC secrecy from someone inspecting the GM session's tool calls.

OAuth authorization-server implementation/hosting is intentionally reused from
an existing or separately selected issuer, not reinvented. Multiple owners,
canonical campaigns and new campaign creation are not exposed. SID Q15/Q16 are
not implemented or promoted to certified algorithms.

Rollback before adoption is simply to leave this separate development branch
unused. After a separately approved staging adoption, disable its MCP listener
or host write switch and return to the previously selected adapter version.
Retain accepted operations, Git commits, leases and dice receipts; reconcile
uncertain writes through the existing recovery protocol. No force-push or
campaign rollback is required or permitted by this work.

Official references checked for setup/requirements:

- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/api/docs/guides/custom-mcp-server
- https://learn.chatgpt.com/docs/plugins
- https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
- https://docs.railway.com/pricing
