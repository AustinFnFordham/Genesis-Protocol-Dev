# GM interoperability handoff · Phase-restricted fixtures

Continuation of eb2dc90. Scope is the existing conformance directory. No production
gateway, combat branch, campaign or storage changes.

## Authenticated checks

GPT refresh identified gpt-session at shared-1 revision 40, evt_0043, public digest
195d4cc4ebf6aa2de46d1a76af8f3b45cd5dd2bae0ef1603f67ed443c3650d1e.
It reported read_only=true, storage_recovery_required=false and exactly
[INSUFFICIENT_SCOPE]. The pending action shared-0002 has no lease, tables,
accepted rolls or batch. A missing effective genesis:gm claim is verified.
The session does not expose the matched authorize request or issuer grant.
An operator should observe only three booleans for the same exchange: client
requested GM, issuer granted GM, fresh session includes GM. The helper
diagnose_scope classifies those facts without inspecting JWTs.
Reauthorize the existing ChatGPT connection through its usual Auth0 flow and
run a fresh refresh. If the new connection still reports scope missing, inspect
the request and issuance booleans before changing config. Do not share raw logs,
tokens, codes or client secrets.

In Gemini web Developer Mode, the existing Genesis Shared Mobile Staging app
was visible. The connector mention was disabled in Neon. In Auto mode a
read-only prompt produced an actual telemetry entry for genesis_refresh with
request {}, marked Consent requested. Proceeding from the request reached a
separate Google consent dialog for the existing Oracle MCP server. The owner
must review and accept that connection authorization if desired. No authenticated
tool result, gemini-session attestation or Gemini cursor was observed. Once
connected, invoke only genesis_refresh and compare the actual result to GPT
with check_refresh_pair. An app label or model answer is insufficient evidence.

## Tests and measurements

15 conformance/acceptance tests passed. The separate existing GM provider
regression suite passed 79 tests, including interrupted push, accepted roll
replay, lost acknowledgement, disk loss and partial batch on synthetic fixtures.
check_recovered_rolls independently compares request hashes, receipt IDs and
accepted result payloads. The source, secrecy and player agency tests exercise
bad rule IDs, public event/context leaks and a substituted player step.

| Model | First pass | After one repair | Repaired | Wall median / p95 |
|---|---:|---:|---:|---|
| qwen2.5:14b | 8/14 | 12/14 | 4/6 | 0.661 / 3.849 s |
| qwen2.5-coder:32b | 8/14 | 14/14 | 6/6 | 1.349 / 9.764 s |

Real CommandCenter Ollama 0.40.16 measurements, temperature 0 and fixed seed 22.
Seven fixtures repeated twice per model. Exact errors, attempts, digests and input
hashes are in results-commandcenter-phase-20261122.json. Schema branch selection
comes from synthetic preflight and accepted operation state and stays fixed across
repair. The 14B model still failed the agency and pending-step continuity fixture
twice. The 32B result is a bounded fixture pass with assistance, not proof of
production readiness or general model superiority. Timings include inference
attempts and may mix load with warm calls.

## First authorized turn

Before GPT claims, require a fresh gpt-session refresh with no scope blocker,
storage healthy, the verified staging cursor and exactly the expected queued
action. Receive specific player approval for shared-0002. Verify actual
gateway-owned write and public/Git ancestry afterwards. Gemini needs a matching
independent read receipt, its own GM grant and a newly approved routed action
before its write. Local integration needs an explicitly approved separate binding
and broker that validates decisions against the existing gateway. Keep inference
loopback-only. Advance each provider from the last published cursor; compare the
accepted receipt IDs and immutable contents after recovery. Do not repeat accepted
roll requests. None of the current evidence is a live turn attestation.
