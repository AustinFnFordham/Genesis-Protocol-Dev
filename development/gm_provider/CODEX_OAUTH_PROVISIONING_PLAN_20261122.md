# Genesis — Codex OAuth Client Provisioning (read-only-first)
**Date:** 2026-11-22 | **Status:** verified local CLI capability + implementation plan, NOT configured or deployed.
**Protection:** Do not affect Oracle staging authority, Hask Meadow, shared-0002, accepted rolls, gateway Git head or storage generation.

## What is verified
CommandCenter's installed Codex executable at OpenAI.Codex_26.1111.2228.0 exposes:
- **codex mcp add <NAME> --url <URL> --oauth-client-id <CLIENT_ID> --oauth-resource <RESOURCE>**
- **codex mcp login <NAME> --scopes <SCOPE,SCOPE>** and optional --oauth-client-registration AUTO|CIMD|DCR, --no-browser
- codex mcp list shows existing MCP_DOCKER/node_repl/cua servers, but **no genesis_staging_codex entry**, as of read-only verification in this session.
The commands have been verified with local --help on CommandCenter, **not actually invoked to register or log into Genesis**.

Existing remote service: https://genesis-austin-staging.duckdns.org/mcp and Auth0 issuer https://genesis-austin-staging.us.auth0.com/. The deployed resource advertises scopes genesis:read and genesis:gm. ChatGPT Plus native custom MCP writes remain ineligible under current OpenAI full custom MCP workspace rules; changing the OAuth client does not confer native write access in this ChatGPT chat.

## Blocking server contract
The existing GitHub file development/gm_provider/mcp_adapter.py, on fix/gm-safe-scope-stepup-20261122, pins the verified JWT azp/client_id to exactly two configured providers: gpt-session and gemini-session. Its constructor REJECTS any other provider and insists on exactly two distinct clients. In addition, the gateway's server-held GM token bindings are provider-scoped. A new Codex client cannot just self-declare gpt-session or gemini-session.

A separately reviewed change must add a distinct approved codex-session provider identity and its Auth0 client mapping (or an approved alternate broker identity with the same hard checks). It must implement no weakening of audience, issuer, expiry, subject, scope, provider routing or recovery, and must update independent tests for wrong-client/wrong-provider/cross-provider claims. Read-only connection must be proven before issuing any GM grant.

## Safe setup sequence
1. **Git branch/code:** Add explicit codex-session support to the provider allowlist and service/session model, preserving gpt-session/gemini-session. Test JWT client binding and deny wrong-provider claims; do not reroute shared-0002.
2. **Auth0:** Register the correct supported OAuth client method (DCR/CIMD/pre-registered client as supported by the actual Auth0 tenant). Configure authorization-code + PKCE S256, exact API audience/resource/scopes, user consent and legitimate redirect URIs discovered from the chosen Codex client strategy. Never invent a callback URI or put client secrets in source files.
3. **Deploy gate:** With owner approval only, test/ship the reviewed gateway change on Oracle after storage/Git ancestry checks. Re-read-only check shared-1 revision, ledger and storage_generation; refuse on drift.
4. **Codex configuration (AFTER provision):** From a terminal on the approved device (replace example CLIENT_ID with verified Auth0 client id):
   codex mcp add genesis_staging_codex --url https://genesis-austin-staging.duckdns.org/mcp --oauth-client-id <REGISTERED_CODEX_CLIENT_ID> --oauth-resource https://genesis-austin-staging.duckdns.org/mcp
5. **Login read-only, via user's browser:**
   codex mcp login genesis_staging_codex --scopes genesis:read
   Explicitly approve the authorization. Do not paste an authorization code, JWT or browser callback into a chat.
6. **Verify:** codex mcp list; then from the authenticated Codex client invoke actual genesis_refresh and require provider codex-session, matching shared-1 cursor/digest, read-only true, expected no recovery or lease, and shared-0002 untouched.
7. **Request GM scope ONLY after the owner authorizes a separate client GM grant and provider side is configured:**
   codex mcp login genesis_staging_codex --scopes genesis:read,genesis:gm
   Verify via nonmutating scope probe and refresh that gm scope is actually effective, with no cross-provider leakage. Scope authentication does not by itself authorize a pending action.
8. **Actual GM turn** requires a distinct submitted owner-approved request routed to codex-session and a separately granted gameplay action. Do not claim or reroute shared-0002.

## Alternative cloud/mobile experience
For always-on mobile without CommandCenter, use a hosted Oracle-authenticated GM web console operated via ChatGPT Work cloud browser (when supported by its navigation and auth controls), or a separately provisioned OpenAI API agent with a secure OAuth broker. This cannot be assumed to work until the GM console exists and independent browser read/write acceptance is proven. Authenticated browser operation must still call the same gateway receipts and replay guard; no service tokens in the web page.

## Stop/go
**READY NOW:** update the GitHub adapter contract, unit tests and Auth0 provisioning plan in isolated development, no production mutation.
**NOT READY:** running codex mcp login against a nonexistent codex provider mapping, shipping an untested policy change, using an existing gpt-session token to impersonate Codex, or executing shared-0002.
Official docs: https://developers.openai.com/plugins/build/auth and https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
