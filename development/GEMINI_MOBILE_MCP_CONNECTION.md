# Gemini Mobile Connected App & Remote MCP Provider Connection

## 1. Architecture & Role Separation

The native Gemini mobile conversation (`gemini-session`) acts as the Game Master while the owner's
desktop is powered off by connecting Gemini's **Custom Connected Apps** (Model Context Protocol over
Streamable HTTP) to a lightweight, remotely hosted instance of the existing Genesis gateway
(`development/gm_provider/service.py` + `development/gm_provider/mcp_adapter.py`).

| Layer | Where it runs | Responsibility |
| --- | --- | --- |
| Player UI & GM Reasoning | Native Gemini mobile app (iOS / Android) | The player speaks with Gemini in chat; **Gemini in the conversation performs all GM reasoning** (`gemini-session`, `kind: "agent-session"`). No backend model API (`generateContent`) is called by the server |
| Authenticated MCP Adapter | `development/gm_provider/mcp_adapter.py` mounted at `/mcp` (and `/v1/mcp`) on `service.py` | Translates MCP Streamable HTTP JSON-RPC 2.0 (`initialize`, `tools/list`, `tools/call`, `prompts/*`, `resources/*`) and OAuth 2.1 PKCE (`S256`) directly onto `Gateway` calls |
| Mechanical & Validation Authority | `development/gm_provider/gateway.py` | Preflight validation (`turn_contract.js`), bounded GM context (`brief.py`), deterministic dice (`roll.py` / `engine.py`), NPC evaluation guard (`npc_review.py`), atomic ledger commits (`batch.py`), and ordered publication (`export_state.py`) |
| Durable Storage & CAS | `store.GitStore` against `origin/staging/provider-shared` (`staging/shared-1`) | Queue rows, campaign lease, accepted operation receipts (`hidden/provider_ops/`), and published pages live in the same Git history as the staging ledger; non-force `git push` is the compare-and-set |

Nothing is duplicated: no second dice roller, no second lease table, no second validator, no
second commit path, and no second recovery store exist.

---

## 2. Google Custom Connected Apps & Remote MCP Requirements

Inspected against Google's official documentation:
- **Gemini Help — Connect custom apps in Gemini Apps (`17209137`):**
  `https://support.google.com/gemini/answer/17209137`
- **Google Developers — Gemini Apps Developer Mode (`dev-mode/usage`) & Connected Apps MCP:**
  `https://developers.google.com/connected-apps/mcp/dev-mode/usage`

### Summary of Google's Requirements & Adapter Implementation

1. **Account & App Surface:**
   - Custom MCP apps are linked once in a desktop browser at `https://gemini.google.com` (**Settings → Connected Apps → Custom apps → Add a custom app**) or via **Gemini Apps Developer Mode** (`https://gemini.google.com/devmode` → **+ Create new**).
   - Once linked on a personal Google Account (18+, English, **Keep Activity** enabled), the connected app is synced to the user's account and available inside the **native Gemini mobile app** in conversation (via `@AppName` or direct tool invocation).
2. **Transport (`Streamable HTTP`):**
   - Must be a public `https://` endpoint accepting JSON-RPC 2.0 `POST` requests (`initialize`, `notifications/initialized`, `tools/list`, `tools/call`, `ping`).
   - `mcp_adapter.py` serves `/mcp` and `/v1/mcp`, negotiates MCP protocol versions (`2025-06-18`, `2025-03-26`, `2024-11-05`), issues `Mcp-Session-Id` headers on `initialize`, supports stateless `POST` execution (so serverless scale-to-zero instances do not break active conversations), returns `405 Method Not Allowed` (`Allow: POST, DELETE, OPTIONS`) on unsolicited `GET /mcp`, and returns `204 No Content` on `DELETE /mcp`.
3. **Authentication (`OAuth 2.1 with PKCE S256` + `Bearer`):**
   - Unauthenticated calls to `/mcp` return `401 Unauthorized` with `WWW-Authenticate: Bearer realm="genesis-mcp", resource_metadata="https://<host>/.well-known/oauth-protected-resource"`.
   - Implements RFC 9728 Protected Resource Metadata (`GET /.well-known/oauth-protected-resource`), RFC 8414 Authorization Server Metadata (`GET /.well-known/oauth-authorization-server` and `/.well-known/openid-configuration`), RFC 7591 Dynamic Client Registration (`POST /oauth/register`), OAuth 2.1 Authorization Code + PKCE `S256` (`GET|POST /oauth/authorize`), and token exchange + persistent refresh tokens (`POST /oauth/token`).
   - Signs authorization codes, access tokens, and 30-day refresh tokens with `HMAC-SHA256` (`GENESIS_OAUTH_SECRET`), so linked mobile sessions survive serverless container restarts without a separate auth database.
   - Also accepts direct `Authorization: Bearer <token>` headers (`GENESIS_READ_TOKEN`, `GENESIS_PLAYER_TOKEN`, `GENESIS_GM_TOKENS["gemini-session"]`).

---

## 3. Deliverable 1: Authenticated, Read-Only Staging Refresh

When `service.py` runs with `--read-only` (or `GENESIS_MCP_READ_ONLY=1`, the default in
`deploy/Dockerfile`, `deploy/cloudrun.service.yaml`, and `deploy/fly.toml`) or when authenticated
with `genesis:read` scope:

- **`tools/list` exposes only the 4 read-only tools:**
  1. `genesis_staging_refresh`: Calls `gateway.public_state()` and `gateway.recovery()`, returning `campaign_id`, `read_only: true`, `changed`, `cursor {campaign_id, revision, ledger_head, context_id, public_sha256}`, `routing`, `recovery {revision, ledger_head, record_mid_write, in_flight, lease}`, `pages`, and a bounded mobile-friendly `summary` of `scene`, `character`, `turn_context`, and `recent_feed`.
  2. `genesis_get_page`: Calls `gateway.page(page)`.
  3. `genesis_get_action`: Calls `gateway.action_status(action_id)`.
  4. `genesis_gm_guide`: Reads `GM_GUIDE.md` and `SESSION_GM.md`.
- **Write and GM-private tools are hard-fenced:** Any call to `genesis_submit_action`, `genesis_select_provider`, `genesis_reroute_action`, `genesis_gm_claim`, `genesis_gm_context`, `genesis_gm_review`, `genesis_gm_tables`, `genesis_gm_roll`, `genesis_gm_commit`, `genesis_gm_publish`, or `genesis_gm_release` is rejected with `READ_ONLY_MODE` / `FORBIDDEN_SCOPE` before touching the gateway.
- **`shared-0002` preservation:** On `staging/shared-1`, `genesis_staging_refresh` reports `revision: 40`, `ledger_head: "evt_0043"`, and `recovery.in_flight.action_id: "shared-0002"` (`status: "submitted"`, `provider: "gpt-session"`, `phase: "interpret"`, `lease.held: false`) without modifying any file or Git ref.

---

## 4. Evidence Classification (Local vs. Mocks vs. Remote vs. Mobile)

| Category | What was executed | Status |
| --- | --- | --- |
| **Local deterministic tests** | `test_mcp_adapter.py` (OAuth 2.1 discovery, DCR, PKCE `S256`, replay/verifier rejection, refresh token, `Mcp-Session-Id` wire framing, read-only staging refresh against `staging/shared-1`, scope & `--read-only` fences, `NOT_ROUTED_HERE` guard when `gemini-session` tries to claim a `gpt-session` action, public/private leak scan, and byte-identity verification of all 146 protected files + `staging/shared-1`), plus `test_gateway.py` (23 cases), `test_service.py` (5 cases), `test_shared_store.py` (4 cases), `test_git_diagnostics.py` (15 cases), `test_npc_review.py` | **Executed & Passed locally** |
| **Mocks / test doubles** | `test_conversational_gm_turn_on_isolated_sandbox_and_routing_guard` uses the deterministic `script("gemini-session")` test double on an isolated temporary copy to drive `genesis_gm_claim` → `genesis_gm_context` → `genesis_gm_tables` → `genesis_gm_roll` → `genesis_gm_commit`. Proves the MCP tool boundary, not live Gemini reasoning | **Executed locally (mock GM on isolated copy)** |
| **Local loopback HTTP socket tests** | `test_live_http_server_mcp_roundtrip` (`ThreadingHTTPServer` on `127.0.0.1`), `test_service.py` | **Executed & Passed on local loopback HTTP** |
| **Remote connection tests** | Calling a public cloud-hosted `https://<host>/mcp` endpoint over the internet | **Not executed** (no cloud service was provisioned or deployed, per instructions) |
| **Actual Gemini mobile evidence** | Linking the remote URL in `gemini.google.com` and running `@Genesis` in the native Gemini mobile app | **Not executed** (requires owner hosting deployment and personal Google account login) |

---

## 5. Remote Hosting, Durable Storage, Costs & Missing Setup

### What Must Run Remotely (Desktop Powered Off)
1. **Container service (`development/gm_provider/deploy/Dockerfile`):**
   - Runs `service.py serve --shared staging/shared-1` (with Python 3.11 + `PyYAML`, Node.js for `turn_contract.js`, and `git` for `GitStore`).
   - Must have a single active instance (`maxScale: 1`) so `GitStore` working-tree operations and in-memory single-use authorization code tracking are serialized.
2. **Durable storage (`GitStore` on GitHub):**
   - For `staging/shared-1`, the remote GitHub branch `staging/provider-shared` on `AustinFnFordham/Genesis-Protocol-Dev` is already the durable store and CAS boundary.
   - `deploy/entrypoint.sh` configures a non-interactive Git credential helper from `GITHUB_PAT` in memory and fetches `origin/staging/provider-shared` on container startup (`GENESIS_SYNC_ON_START=1`).
   - No paid SQL/NoSQL cloud database or persistent disk is needed for `staging/shared-1`.
3. **Authentication secrets:**
   - `GENESIS_OAUTH_SECRET` (entered by the owner on `/oauth/authorize` when linking the app in Gemini web and used to HMAC-sign stateless OAuth 2.1 tokens).
   - Optional `GENESIS_OAUTH_CLIENT_ID` and `GENESIS_OAUTH_CLIENT_SECRET` (if using static client credentials in Gemini Developer Mode).
   - `GENESIS_READ_TOKEN`, `GENESIS_PLAYER_TOKEN`, `GENESIS_GM_TOKENS={"gemini-session":"..."}`.
   - `GITHUB_PAT`: Fine-grained GitHub Personal Access Token scoped to `AustinFnFordham/Genesis-Protocol-Dev` (`Contents: Read-only` for Deliverable 1 read-only staging refresh; `Contents: Read and write` when enabling full GM commits on `staging/provider-shared`).

### Estimated Monthly Cost (Desktop Off)
- **Google Cloud Run (`deploy/cloudrun.service.yaml`):**
  - `minScale: 0`, `maxScale: 1`, `cpu-throttling: true` (request-based billing), 1 vCPU, 512 MiB RAM.
  - Always-free tier includes 2 million requests/month, 180,000 vCPU-seconds/month, and 360,000 GiB-seconds/month.
  - For solo campaign play and staging refreshes, usage stays well inside the free tier (**\$0.00/month** compute; Secret Manager is \$0.06 per secret version/month after the 6 free secret versions, so **\$0.00/month** for ≤6 secrets).
- **Fly.io alternative (`deploy/fly.toml`):**
  - `shared-cpu-1x`, 512 MB RAM with `auto_stop_machines = "stop"` and `min_machines_running = 0`: ~**\$0.00–\$2.00/month** depending on active minutes.
- **GitHub (`GitStore` on existing repository):** **\$0.00/month**.
- **Gemini reasoning:** Performed inside the user's native Gemini mobile conversation (included in the user's personal Google/Gemini account; **\$0.00** API usage because no backend `GEMINI_API_KEY` is used).

### Concrete Blockers (Why Live Gemini Mobile Could Not Be Run From This Session)
1. **No remote HTTPS host provisioned:** By instruction ("do not provision, enable billing or deploy"), no Cloud Run / Fly.io service was created. Google Connected Apps requires a publicly reachable `https://` URL.
2. **No GitHub write/read PAT configured in a remote host:** And locally, shell `git push` has no configured HTTPS credentials (`exit code 128: terminal prompts disabled`), as documented in `development/GIT_CLAIM_DIAGNOSTICS.md`.
3. **Owner Google Account interactive linking required:** Adding a Custom Connected App in `gemini.google.com` requires interactive sign-in to the owner's personal Google Account (18+, English, Keep Activity on).
4. **`shared-0002` is assigned to `gpt-session`:** Per instruction, `shared-0002` remains untouched and assigned to `gpt-session` (`v1`, `submitted`, lease `v5` with `holder: null`).

---

## 6. Exact Gemini Connection Instructions

### Step 1: Deploy the Prepared Container (Read-Only Deliverable 1 First)
Once you choose to deploy (e.g., to Google Cloud Run):
```bash
# 1. Build and push the container image from theisolated branch
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT_ID/genesis/genesis-mcp-gateway:latest \
  -f development/gm_provider/deploy/Dockerfile .

# 2. Deploy in read-only mode first (GENESIS_MCP_READ_ONLY=1)
gcloud run deploy genesis-mcp-gateway \
  --image REGION-docker.pkg.dev/PROJECT_ID/genesis/genesis-mcp-gateway:latest \
  --region REGION \
  --allow-unauthenticated \
  --min-instances=0 --max-instances=1 \
  --memory=512Mi --cpu=1 \
  --set-env-vars="GENESIS_SHARED_SCOPE=staging/shared-1,GENESIS_GIT_BRANCH=staging/provider-shared,GENESIS_SYNC_ON_START=1,GENESIS_MCP_READ_ONLY=1,GENESIS_ALLOWED_ORIGIN=https://gemini.google.com,GENESIS_OAUTH_CLIENT_ID=genesis-gemini-mobile" \
  --set-secrets="GENESIS_OAUTH_SECRET=genesis-oauth-secret:latest,GENESIS_OAUTH_CLIENT_SECRET=genesis-oauth-client-secret:latest,GENESIS_READ_TOKEN=genesis-read-token:latest,GITHUB_PAT=genesis-github-pat:latest"
```
*(Note: `--allow-unauthenticated` at the Cloud Run ingress layer allows Google's MCP fetcher to reach `/.well-known/oauth-protected-resource` and `/oauth/*`; `/mcp` itself enforces `OAuthServer` Bearer token authentication on every request.)*

After deployment, set `GENESIS_PUBLIC_BASE_URL` to the assigned `https://genesis-mcp-gateway-...run.app` URL.

### Step 2: Verify Remote Read-Only Health & MCP Discovery
```bash
BASE="https://genesis-mcp-gateway-YOUR_HASH.a.run.app"
curl -i "$BASE/v1/health"
curl -i "$BASE/.well-known/oauth-protected-resource"
curl -i "$BASE/.well-known/oauth-authorization-server"
curl -i -X POST "$BASE/mcp" \
  -H "Authorization: Bearer $GENESIS_READ_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"genesis_staging_refresh","arguments":{"campaign_id":"shared-1"}}}'
```

### Step 3: Link in Gemini Web / Developer Mode (Once, on Desktop or Mobile Browser)
1. Ensure your personal Google Account has **Keep Activity** enabled and language set to **English**.
2. Open `https://gemini.google.com/devmode` (or `https://gemini.google.com` → **Settings** → **Connected Apps** → **Custom apps** → **Add a custom app**).
3. Click **+ Create new** / **Add a custom app**:
   - **App name:** `Genesis`
   - **MCP Server URL:** `https://genesis-mcp-gateway-YOUR_HASH.a.run.app/mcp`
   - *(Optional, in Developer Mode → Additional settings → Show more):* Enter Client ID `genesis-gemini-mobile` and your `GENESIS_OAUTH_CLIENT_SECRET` (or leave blank to use automatic Dynamic Client Registration via `/oauth/register`).
4. Click **Next**. When redirected to `/oauth/authorize`, enter your `GENESIS_OAUTH_SECRET` (or `GENESIS_READ_TOKEN` for strictly read-only linking) and click **Approve & Connect**.

### Step 4: Use From the Native Gemini Mobile App (Desktop Powered Off)
1. Open the **Gemini mobile app** on your phone (signed into the same personal Google Account).
2. For the **authenticated, read-only staging refresh**, send:
   > `@Genesis Refresh the shared-1 staging campaign state and recovery status. Report the current revision, ledger head, scene summary, and any in-flight action without modifying anything.`
   Gemini mobile will invoke `genesis_staging_refresh` and report revision `40`, ledger head `evt_0043`, and `shared-0002` queued for `gpt-session`.
3. When ready to enable **full conversational GM play** (`gemini-session`) after `shared-0002` is completed by GPT:
   - Update `GENESIS_MCP_READ_ONLY=0` on the Cloud Run service and provide a `GITHUB_PAT` with `Contents: Read and write` on `AustinFnFordham/Genesis-Protocol-Dev`.
   - In the Gemini mobile chat, instruct `@Genesis` to read `genesis_gm_guide`, submit or claim the `gemini-session` turn (`genesis_gm_claim`), read bounded context (`genesis_gm_context`), fix tables (`genesis_gm_tables`), request authoritative rolls (`genesis_gm_roll`), and commit (`genesis_gm_commit`).
