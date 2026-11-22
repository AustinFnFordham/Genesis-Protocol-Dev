# Genesis Protocol — Cross-Provider GM Acceptance Plan
**ID:** GM-ACCEPT-001 · **Date:** 2026-11-22 · **Status:** Read-only verified baseline, proposed acceptance gates. This is documentation, NOT authorization to mutate staging or run campaign dice.

## Ownership and boundaries
- Claude owns Combat CC-005 and subsequent combat development in development/combat_slice. Work/GPT owns the existing Oracle/Auth0/MCP/Git provider integration, independent acceptance, local-model harness and cross-provider interoperability. No duplicate gateway, combat resolver, ledger or dice engine.
- Preserve live Hask Meadow, the staging provider-shared Git branch, and pending action shared-0002. Do not claim, roll, table, commit, reroute, publish or release shared-0002 as an OAuth test. Its actual execution requires a separate owner-approved gameplay gate.
- Never replace the persisted storage generation, disable recovery protection, reveal tokens/keys, infer a scope from mere tool visibility, or migrate live rules without explicit approval.
- Every implementation change gets one scoped commit, tests, branch + SHA, and a durable handoff. Different provider agents must not overwrite Claude's active combat files.

## 1. Verified baseline from this ChatGPT session
On 2026-11-22 a connected Genesis Staging genesis_refresh returned:
- Provider: gpt-session. Campaign shared-1, revision 40, ledger head evt_0043, public digest 195d4cc4ebf6aa2de46d1a76af8f3b45cd5dd2bae0ef1603f67ed443c3650d1e.
- In flight: action shared-0002; provider gpt-session; status submitted; tables not fixed; zero accepted rolls; no accepted/committed batch.
- Lease: not held. Storage recovery: not required. Existing storage-generation identifier recorded as 8b59b486-b9d7-4ff9-bb74-c8ca35cbdfcd. Treat as an existing identity marker, never generate a replacement.
- ChatGPT tool connection: read_only=true, gm_write_blockers=[INSUFFICIENT_SCOPE].
- Read-only gateway references worked: gm_guide, turn_contract, consequence_authority, soul_contract, chaos_doctrine.
- Public OAuth resource discovery on the connected Windows device at https://genesis-austin-staging.duckdns.org/.well-known/oauth-protected-resource/mcp advertised scopes_supported=[genesis:read, genesis:gm] with Auth0 issuer https://genesis-austin-staging.us.auth0.com/ and resource https://genesis-austin-staging.duckdns.org/mcp.
- OAuth discovery fix branch observed at fix/oracle-mcp-gm-scope-discovery-20261122 commit 412bb7062b86e6dde2bdddbfb34a5dc794cb6422. Scope advertisement is NOT proof the currently connected ChatGPT token holds the GM scope.

## 2. Gate A — Scope and provider identity, no gameplay writes
1. Reconfirm protected resource metadata advertises read and gm, without requiring gm globally for read operations.
2. Owner reauthorizes/reconnects the Genesis Staging ChatGPT connection to obtain a fresh token that requests and receives genesis:gm. Use only the normal ChatGPT/Auth0 connection flow, never paste a JWT, OAuth authorization code or secret into a prompt.
3. On reconnection, independently verify via genesis_refresh that connection_provider=gpt-session, read_only=false, empty gm_write_blockers, no storage recovery, unchanged cursor, expected pending request and no surprise lease. If still insufficient, stop and check authorized Auth0 API permissions, token claim, audience, owner and client bindings using only redacted yes/no diagnostics.
4. Prove a separate read-scoped client still reads successfully but cannot call GM writes, and that unauthorized owner/client/provider combinations fail. Verify the service's Git and authority ancestry using the existing Oracle GM Write Runbook and Recovery Readiness procedure, without disclosing secrets or modifying storage.

**Pass** only if all scope, identity, cursor and recovery predicates hold. **Current state: BLOCKED at effective GM token; read-only works.**

## 3. Gate B — GM contract conformance (fixture tests, no writes)
All model providers use the gateway's exact GM_GUIDE and turn-contract/3 references; source of truth is the accepted state, not model memory.
- Request grammar: review OR tables, then only needed rolls, then commit. Models do not generate die faces or modify Git/ledger directly.
- Player declaration and ordered steps are immutable; stop for material player choices. NPC plans must be consistent with observed state/motives. Reject ungranted powers, impossible hands/range, double action spending, fabricated results and model-only state.
- Never expose private enemy HP, AC, hidden facts, secret table results, or unrevealed GM state in player-visible text.
- Use identical **isolated test fixtures** and validation for GPT, Gemini, and local inference. Score JSON validity, unauthorized player-choice attempts, hallucinated mechanics, roll-key/receipt alignment, NPC evaluations, narrative fidelity and scene continuity.
- Provider handoff tests must carry the same source revision, accepted operation, cursor, idempotency keys and authoritative receipts. Treat a model's natural-language claim of success as non-evidence.

## 4. Gate C — Actual ChatGPT GM acceptance (separate owner approval)
Only after Gate A passes and a fresh consistency check confirms the exact authorized pending action:
- One authenticated gpt-session session may claim the action actually routed to it.
- Follow gateway tool contracts: refresh → claim → context → review OR tables → any actually requested gateway roll(s) → commit → publish; release only when appropriate to preserve accepted work.
- On retry/timeout consult accepted operation first; never replace the turn or roll again. Check independently from a new refresh and Git-backed authoritative events that exactly one action completed, with expected revision ancestry, receipts, publication and provider identity.
- Do not claim shared-0002 for deployment validation or without specific owner authorization to run that exact pending gameplay turn.
**Current state: NOT RUN.**

## 5. Gate D — Gemini acceptance
Gemini must be authenticated as its own gemini-session provider, with distinct server-held credential and Auth0 authorization; Google account or AI Studio login by itself is not Genesis GM authorization.
- Establish the supported MCP or approved adapter transport first. In Work Cloud Browser, inspect Gemini/AI Studio setup and perform safe read-only refresh; do not assume that Gemini supports direct MCP authorization just because ChatGPT does.
- Verify Gemini provider identity and cursor/digest from an independently authorized session.
- Run Gate B on identical fixtures; validate structured JSON proposal, source citations, player agency, NPC consistency and secrecy.
- After GPT's pending work is resolved, obtain a distinct player-authorized next staging action routed to gemini-session. Only then run an actual gateway-owned GM turn; compare persisted receipt/ancestry and fresh public state. Never reroute shared-0002 as a convenience.
**Current state: NOT TESTED; not claimed to be connected.**

## 6. Gate E — Local model acceptance
Home workstation can serve a local model through an inference-only endpoint (Ollama/LM Studio or comparable existing runtime). Do not put a long-lived genesis:gm token into a model prompt or connect an unauthenticated local HTTP listener directly to Oracle write authority.
- First test contract fixtures offline with a small faster local model for protocol smoke and a larger reasoning/coding-capable model for comparison. Record exact model version, parser errors, JSON/schema adherence, latency, memory usage and ability to preserve GM facts/knowledge boundaries.
- A provider-neutral local orchestration harness gives the model immutable context; the existing gateway still validates actions, rolls, receipts, accepted results and Git writes. Any live local write requires approved authenticated broker identity and explicit owner gate.
- After offline tests, evaluate a separate authorized staging local-provider identity (name/credentials not invented here); never impersonate gpt-session or gemini-session.
**Current state: planned, not yet run.**

## 7. Test/decision matrix
| Gate | ChatGPT | Gemini | Local | Evidence |
|---|---|---|---|---|
| Read-only refresh | PASS gpt-session | NOT RUN | NOT RUN | gateway cursor |
| OAuth advertises gm | PASS public metadata | same endpoint, not independent authorization | N/A | public resource metadata |
| Effective GM write scope | BLOCKED INSUFFICIENT_SCOPE | NOT VERIFIED | NOT AUTHORIZED | authenticated refresh |
| Contract fixtures | NOT RUN | NOT RUN | NOT RUN | independent harness reports |
| Authorized claim/roll/commit/publish | NOT RUN | NOT RUN | NOT RUN | accepted receipts, published cursor, Git |
| Cross-provider handoff | NOT RUN | NOT RUN | NOT RUN | identical parent cursor and state |

**Never confuse the sandbox Combat CC-005 dice/verification server with Oracle's live authoritative GM gateway.** Adapter integration and replay comparability require separate testing and explicit promotion approval.

## 8. Next actions and stopping criteria
- **Owner action:** reconnect Genesis Staging with the approved scope request, then ask ChatGPT to refresh again. No token sharing.
- **GPT Work independent task:** inspect Oracle deployed auth build and permissions using redacted diagnostics; build fixture-based cross-provider conformance harness on an isolated development/gm_provider branch, with one semantic change per commit; check a supported Gemini connection; produce specific local-model adapter/setup for the workstation; run safe read-only tests. Do not modify Claude's combat files.
- **Owner later:** expressly approve the particular staging action/provider to exercise for a real authoritative turn; determine staging order GPT → Gemini → local model after gate passes.
- **Stop:** scope mismatch, unknown provider identity, changed cursor, lease held by another owner, storage recovery required, mismatched protected Git ancestry, invalid/expired JWT, unsourced power, replay mismatch, or pending unapproved writes.

## 9. Handoff invariant
When any agent/session/provider runs out of usage, record exact branch, commit SHA, latest accepted staging cursor, pending run/phase, accepted receipt IDs, active lease status, outstanding rule decisions and test results. Resume from authoritative storage, never from a copied model conversation or a new random session.
