# Genesis / Codex / Auth0 setup — beginner checklist
**Date:** 2026-11-22 | **Status:** READ-ONLY PROCEDURE, not authorized deployment. Based on installed CommandCenter Codex CLI --help and current gateway source. **No Oracle changes, no Auth0 changes, no campaign actions were performed.** No secrets belong in this guide or in chats.

## Why there are separate steps
- **GitHub** permission allows source commits, not Genesis GM actions.
- **ChatGPT Plus's custom Genesis MCP** is read-only under current full-MCP workspace availability, no matter that it has "Allow all actions".
- **Codex CLI** can be a separate OAuth client, but current `development/gm_provider/mcp_adapter.py` hardcodes exactly TWO client identities in `JWTVerifier.__init__` and `GatewayTools.authorize`: `gpt-session` and `gemini-session`. It rejects a third client until reviewed source and server-held provider authorization are added.
- **Auth0** issues user-consented access tokens; a token's `scope` must actually contain `genesis:read` and optionally `genesis:gm`. Public metadata advertising a scope does not grant it.
- **Oracle** verifies JWTs and enforces all campaign mutations; it must not be circumvented, and every additional client needs its own `provider` binding and server-held GM authority after approval.
- **Codex on CommandCenter** is a home-machine acceptance route. A hosted GM web console with ChatGPT Work cloud browser is a separate mobile/no-home-PC route to implement and verify later.

## Phase A — prepare code safely (developer / GPT Work lane, owner reviews)
A1. Open the GitHub repository `AustinFnFordham/Genesis-Protocol-Dev`. Review `dev/gm-contract-conformance`, PR #5 (scope probe) and conformance reports. Do not modify `staging/provider-shared` data checkout.
A2. Create isolated branch `dev/codex-provider-auth` (example name, do not assume exists) FROM current verified GM provider code; cherry-pick reviewed probe fixes if needed. No gameplay writes.
A3. Modify `mcp_adapter.py` to add `codex-session` as a THIRD trusted provider while continuing to REQUIRE distinct, pinned Auth0 `azp` client IDs. Do not change issuer, audience, subject, signature, expiry or required-scope comparisons. Update provider-specific binding checks and server-held GM token mapping. Check any downstream gateway/route/provider allowlists, don't stop at JWTVerifier.
A4. Add negative tests: Codex cannot impersonate GPT/Gemini; GPT/Gemini cannot claim Codex; wrong `azp`/issuer/audience/scope denied; `genesis:read` does not permit GM write; repeated requests have idempotent receipts; `shared-0002` cannot be claimed through a different provider. Verify independent read-only refresh on each provider.
A5. Run COMPLETE applicable GM provider regressions + conformance suite + adapter tests in a Linux test environment. Record SHA and outputs. Keep it as PR until the owner approves Oracle deployment.
A6. Establish deployment/rollback plan with the Oracle code checkout separate from the authoritative campaign/Git ledger, and verify expected storage generation, branch and public cursor. Stop on drift.

## Phase B — Auth0 dashboard (owner action, after reviewed code is ready)
B1. From the browser sign into https://manage.auth0.com/ (your existing Genesis/Auth0 tenant). If asked which tenant, choose the same tenant advertised by the current Genesis protected-resource metadata. Do not create a new Auth0 tenant.
B2. In left menu, open **Applications → Applications → Create Application**.
B3. Name it **Genesis Codex CLI**. Select **Native** as the application type (public client using authorization-code + PKCE). Create it. Do not use a Machine-to-Machine app for interactive human login.
B4. Open its **Settings** and COPY ONLY the **Client ID** for later. Never post client secret, access token, authorization code or private login callback URL in a chat. Do not add a client secret to `.codex/config.toml`.
B5. Find **Applications → APIs** and open the EXISTING Genesis staging API (identify it by matching the exact API Identifier / audience expected by `GENESIS_MCP_RESOURCE`; do not create another API). Under **Permissions**, verify `genesis:read` and `genesis:gm` are already defined. Add nothing unless a permission really is absent and the owner has approved the policy.
B6. If that API enforces RBAC, review the current API policy/roles and **least-privilege permission grant** for THIS native client/user. A user-level GM role and client access policy are different. Initially allow only `genesis:read`; do not grant `genesis:gm` simply because it is advertised. Current Auth0 dashboard labels may differ; check actual token scope after login.
B7. The Native application's **Allowed Callback URLs** must match Codex's ACTUAL `redirect_uri` byte-for-byte. **Do not guess this URL.** Select the client registration mode supported by the tenant (pre-registered client, DCR or CIMD), and obtain the callback from the supported Codex OAuth login flow/documentation. When appropriate, use `codex mcp login genesis_staging_codex --scopes genesis:read --no-browser` to display the generated authorization URL and inspect ONLY its `redirect_uri` on your own device; if login is blocked by an unregistered callback, add that EXACT redirect URI in Auth0 and retry. Never share the full URL or `state`/`code` values.
B8. Under **Settings → Advanced Settings → Grant Types**, ensure **Authorization Code** is enabled and PKCE S256 is supported for the Native app (labels vary). Refresh Token is optional and should require an explicit security decision. Save. Leave all other existing GPT and Gemini Auth0 apps unchanged.
B9. Record the approved Client ID and the exact matched redirect URI in a private owner-accessible deployment note, without tokens/secrets in Git.

## Phase C — Oracle deployment (explicitly gated OWNER APPROVAL REQUIRED)
C1. Owner reads the specific code PR and Linux test evidence. Approval must explicitly identify the code SHA, scope and Oracle host. Approval of docs is NOT approval to deploy.
C2. Authorized operator checks existing code branch, `staging/provider-shared` ledger head/revision, storage generation, leases, provider tokens and backup/snapshot using existing runbooks. Stop if revision unexpectedly changes or an in-flight action/lease becomes active.
C3. Deploy reviewed gateway code to the existing Oracle **code** checkout only. Update server-secret configuration to map ONLY the new Auth0 Client ID to `codex-session`, with separate server-held GM provider credential if and when separately authorized. Do NOT put provider GM token in `.codex/config.toml` or in browser JS.
C4. Restart only the authorized service via the existing deployment procedure, recheck health and all THREE provider read-only identities, expected cursor and recovery state. Roll back on any access regression.
C5. This does NOT give Codex permission to claim `shared-0002`. That action belongs to `gpt-session` unless the owner separately authorizes a validated reroute.

## Phase D — configure Codex on your Windows computer (after B and C)
D1. Open **PowerShell** on CommandCenter. The actual installed Codex executable has been verified to expose `mcp add --url --oauth-client-id --oauth-resource` and `mcp login --scopes`.
D2. Use a registered Client ID and the ACTUAL resource advertised by the MCP server (these command snippets use the existing documented resource URL; verify live resource value at deployment):
```powershell
codex mcp add genesis_staging_codex `
  --url https://genesis-austin-staging.duckdns.org/mcp `
  --oauth-client-id YOUR_ACTUAL_AUTH0_CLIENT_ID `
  --oauth-resource https://genesis-austin-staging.duckdns.org/mcp
```
D3. Confirm `codex mcp list` shows `genesis_staging_codex`. This only configures a server; it does NOT grant authorization.
D4. First login READ-ONLY with the registered client:
```powershell
codex mcp login genesis_staging_codex --scopes genesis:read
```
D5. Your browser should open Auth0. Confirm tenant and intended Genesis app, approve only permissions you understand. If it reports callback mismatch, stop and reconcile the exact generated redirect URI with B7. Don't use a raw bearer token fallback.
D6. In Codex's connected MCP tool context, call `genesis_refresh {}` read-only. Require `connection_provider=codex-session`, `read_only=true`, matched campaign revision/ledger/public digest and `storage_recovery_required=false`. If it says `gpt-session`, `gemini-session` or returns no tool, STOP: binding or tool discovery is wrong.

## Phase E — optional GM authorization (new explicit owner approval)
E1. Do NOT request GM just because read-only works. First confirm Codex identity and read-only access. Get the owner to approve THIS client's GM scope and provider-route policy.
E2. Update Auth0 grant/RBAC policy for that SAME native client to permit `genesis:gm` when appropriate (not the GPT/Gemini client). Ensure Oracle's server-held GM credential is scoped to `codex-session` and write mode approved.
E3. Re-login with both scopes:
```powershell
codex mcp login genesis_staging_codex --scopes genesis:read,genesis:gm
```
E4. Run the deployed nonmutating `genesis_gm_scope_probe`; verify `gm_scope_granted=true`, `connection_provider=codex-session`. Then `genesis_refresh {}` must show zero GM blockers and unchanged authoritative cursor. If not, inspect redacted booleans only: requested scope / issued scope / actual token scope. Don't weaken server checks.
E5. First write acceptance must be on a NEW, synthetic, owner-approved action routed to `codex-session`, not `shared-0002`. Validate plan, dice, receipt, Git head and recovery; no Hask Meadow writes.

## Phase F — mobile use, home machine not required (separate future milestone)
F1. Codex CLI running on CommandCenter DOES depend on CommandCenter for its execution; installing this on Windows does NOT magically enable write-capable custom MCP actions inside the iPhone ChatGPT Plus conversation.
F2. For the **ChatGPT Work cloud-browser** route, build and deploy a separate authenticated Genesis GM operator web UI on an always-on host (Oracle is a candidate) using the same gateway and authorization. Confirm login and tool navigation work from Work's cloud browser before claiming travel-readiness. Keep server GM credentials server-only.
F3. If a cloud Codex client is preferred instead, it too must have an authorized execution environment and its own legitimate OAuth binding, not share a user's local cached bearer token.
F4. A production mobile-ready release requires the player-app UI and GM operations to share the authoritative ledger, secrecy projections, idempotent dice and player permissions. None exists from this docs guide alone.

## Current blockers and earliest safe user action
- `codex-session` has NOT been added to the gateway, and no new Auth0 native client is confirmed.
- The next practical owner-only step, if they choose, is **B1–B4** to create an Auth0 Native app and note its *Client ID locally*. No elevated GM permission, deployment, or live change is required by creating the app.
- Ask the developer to complete A1–A6 in a separate isolated branch while the owner prepares B1–B4.
- NEVER run CLI GM login against the current two-provider gateway expecting it to work. STOP on any unexpected owner, wrong JWT subject, cursor drift or scope mismatch.

Official references:
- https://learn.chatgpt.com/docs/extend/mcp
- https://learn.chatgpt.com/docs/cli/reference
- https://developers.openai.com/plugins/build/auth
- https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow-with-pkce
- https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
