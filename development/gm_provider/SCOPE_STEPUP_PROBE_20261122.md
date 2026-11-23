# Genesis GM OAuth scope-step-up diagnostic — 2026-11-22

**Status:** Reviewed implementation candidate; NOT deployed. **Branch:** `fix/gm-safe-scope-stepup-20261122` from `dev/gm-contract-conformance` at `370b2bd2e7f00dbf6cf524e598420fbb6bd26db6`. **Code commit:** `abfc1d49d971d85852fc9718912c72cca8a804cb`. **Tests:** `d5e20786e2f543835fdf54f69c521f1365b01e99`.

## Current verified problem

Authenticated `genesis_refresh` in ChatGPT returned provider `gpt-session`, `read_only=true`, exactly `gm_write_blockers=[INSUFFICIENT_SCOPE]`, `storage_recovery_required=false`. Shared staging remains `shared-1` revision 40 / `evt_0043`, public SHA256 `195d4cc4ebf6aa2de46d1a76af8f3b45cd5dd2bae0ef1603f67ed443c3650d1e`; queued action `shared-0002` remains submitted with no lease or accepted rolls. OAuth protected resource discovery advertises both `genesis:read` and `genesis:gm`; advertising does not grant either scope to an existing OAuth token.

Original `mcp_adapter.py` returned a `mcp/www_authenticate` challenge including error and scopes, but NOT `error_description`. The current OpenAI plugin auth guidance explicitly requires both error and error_description for tool-level OAuth linking/reauthorization. The only GM-scoped exposed tools were stateful claim/context/tables/roll/commit/publish/release, none of which is suitable as an authorization-only test. This code change adds a safe probe; it does not prove the ChatGPT client requested `genesis:gm` or Auth0 issued it.

## Proposed patch (no campaign writes)

- Add `genesis_gm_scope_probe`, marked **readOnlyHint=true** but with required OAuth `securitySchemes` scopes `[genesis:read, genesis:gm]`. It is available independently of whether gateway writes are enabled.
- The probe checks the existing verified token and returns only `connection_provider`, `gm_scope_granted`, `gm_write_ready` and `gm_write_blockers`. It cannot claim, lease, roll, read private GM context, or mutate the ledger.
- If token lacks GM permission, it responds with `INSUFFICIENT_SCOPE` plus a tool result `_meta["mcp/www_authenticate"]` including `error="insufficient_scope"`, `error_description` and the requested scopes, so ChatGPT can offer OAuth step-up if the client supports it.
- Maintain global required scope `[genesis:read]`, existing provider binding, token validation, storage-generation checks, and all existing GM tool gates; this change is intentionally additive and does not relax authorization.
- No OAuth credentials, JWTs, Auth0 grants, or Git service tokens were accessed or changed.

## Test evidence

On the authorized CommandCenter workstation, used a disposable shallow clone at `C:\Users\Austi\AppData\Local\Temp\genesis-scope-probe-20261122` and an isolated Python environment in WSL2. The Windows Python attempt was not valid because the server requires Linux `fcntl`; the first Linux attempt lacked `node` on PATH. After using the user's existing WSL Node.js at `~/.local/bin/node`, the full `python -m unittest test_mcp_adapter -q` completed: **14 tests, 0 failures**, exit code 0. Tests included both new scope-probe cases and prior authenticated MCP adapter, Git continuity, recovery and read-only behavior. The suite did not connect to Oracle or mutate a real campaign.

Independent verification at PR head `5f261a81c057d77a0ef58c9283dfaa159ace7052` passed all **81 GM provider tests** (including all **14 adapter tests**) and **15 conformance tests** on Linux x86_64, Python 3.12.14, with the Oracle runner's pinned MCP dependencies. The adapter suite also passed a standalone run. Oracle VM execution and the live client OAuth flow remain unverified.

From the repository root, using the installed `requirements-mcp.txt` and conformance dependencies:

```sh
mkdir -p development/.qa/tmp
export PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/development/.qa/tmp"
python -m unittest discover -s development/gm_provider -p 'test_*.py'
python -m unittest discover -s development/gm_provider/conformance -p 'test_*.py'
python -m unittest discover -s development/gm_provider -p test_mcp_adapter.py
```

## Safe launch sequence (requires explicit owner approval)

1. Owner can first try user-controlled **Settings > Plugins > Genesis Shared Mobile Staging > Reconnect** and approve permissions if the existing app supports reauthorization. If the actual OAuth prompt lacks `genesis:gm`, this UI step alone cannot manufacture that grant. Do not share raw authorization URLs, JWTs, access tokens or Auth0 secrets.
2. Inspect the code diff and repeat the 14 adapter tests in the Linux deployment-compatible environment. Compare deployed Oracle executable SHA and current Auth0 metadata, confirm stored authority generation / Git head using the existing runbook. Do not alter the storage marker.
3. **Only after owner approves a separate deployment:** deploy the reviewed build to the existing Oracle code checkout without changing gateway runtime authority, token secrets or campaign storage; refresh the connected ChatGPT plugin's tool list (requires relevant app management permissions). Do not recreate a parallel MCP service.
4. In ChatGPT, call the new **read-only** `genesis_gm_scope_probe`. If scope is absent, it should return an OAuth step-up challenge. Complete any user-visible authorization in the provider's own UI. A successful probe alone proves token scope, not actual write ability.
5. Call `genesis_refresh` again and require `connection_provider=gpt-session`, no blockers, `read_only=false`, expected cursor and no recovery flag. Independently check a read-scoped client remains read-only.
6. If scope remains missing, check only redacted booleans for the same Auth0 exchange: `client_requested_genesis_gm`, `auth0_issued_genesis_gm`, `fresh_chatgpt_token_has_genesis_gm`; distinguish client scope omission, Auth0 consent/policy, cached grants, and any account/plan/plugin-action restrictions. Do NOT weaken server checks to work around absent scope.
7. **No GM action yet.** The owner must separately authorize execution of the exact `shared-0002` turn after stage-A auth passes. Gemini requires its own `gemini-session` consent and attested read-only refresh; never spoof it with GPT's client.

**Stop on:** unexpected revision, lease, token identity, missing provider, storage recovery, incorrect branch/generation, tool-list refresh failure, or failure of scope escalation. This diagnostic is deliberately nonmutating.

## ChatGPT eligibility and OAuth evidence

The current account reports Plus. [OpenAI's custom MCP documentation](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt) limits full MCP to Business, Enterprise and Edu. Pro can connect custom MCP servers with read/fetch permissions. The Genesis Staging app-specific setting in Work reports **Allow all actions**. That preference, tool discovery and Auth0 authorization are separate from workspace eligibility. No separately eligible workspace was verified for this session.

| Signal | Observed |
| --- | --- |
| Auth0 resource discovery advertises `genesis:gm` | Yes |
| The ChatGPT authorization request included `genesis:gm` | Unknown |
| Auth0 issued `genesis:gm` in that exchange | Unknown |
| Gateway found `genesis:gm` on the current ChatGPT token | No, inferred from the authenticated `INSUFFICIENT_SCOPE` blocker |
| Gateway found `genesis:gm` on a newly authorized ChatGPT token | Unknown, new exchange pending |

For an eligible workspace, its owner or admin should first confirm that the app's actions are enabled in ChatGPT on the web. After separate Oracle deployment approval, the operator should record the running application SHA, verify the pinned storage generation and clean authority against GitHub, and review the deployed-SHA-to-candidate diff. PR #5 contains a broader history than its three-commit diff. If the deployed base differs, review the full delta or backport only the probe and its tests onto that base, then rerun the suite. Keep the service unit, environment file, authority and credentials in place. Roll back a probe-only deployment by restoring the recorded application SHA and restarting the existing service if the post-deploy checks fail. After tool refresh and probe invocation, an authorized operator can correlate the authorization request and issued grant internally and report only the three scope booleans. The live gateway supplies the third boolean through the probe. Require an independent `genesis_refresh` with `gpt-session`, empty blockers, a healthy generation and the same revision, head and digest. This verifies authorization readiness. Client execution of an actual write remains a separately authorized acceptance step.

## OAuth path outside native ChatGPT

If an eligible ChatGPT workspace is unavailable, use the existing Oracle endpoint from a local [Codex CLI OAuth client](https://learn.chatgpt.com/docs/extend/mcp), subject to registration and staging validation. Codex supports Streamable HTTP, a pre-registered OAuth client ID and explicit scope requests. Keep this client's Auth0 grant and callback distinct from ChatGPT and Gemini. Use authorization code with PKCE in the owner's browser and keep tokens in the client's secure storage. Never paste tokens into Work or configure a direct Git or admin write path.

The adapter currently pins exactly two OAuth clients to `gpt-session` and `gemini-session`. A third client therefore requires a reviewed staging-only provider binding, a distinct provider ID such as `codex-session`, and its own server-held GM token. Preserve validation of issuer, audience, owner, client, expiry and scopes. Include a negative test for unpinned clients and a cross-provider denial test. Start the new client with `genesis:read`, verify the distinct identity and unchanged staging cursor, then request `genesis:read,genesis:gm` with `codex mcp login genesis-staging --scopes genesis:read,genesis:gm` only after its grant is approved. Run the read-only probe and refresh first. A later authorized action must be routed to the new provider explicitly. Leave `shared-0002` assigned to `gpt-session`. This is a design for a separate approval, not a deployed connection or a native ChatGPT GM attestation.
