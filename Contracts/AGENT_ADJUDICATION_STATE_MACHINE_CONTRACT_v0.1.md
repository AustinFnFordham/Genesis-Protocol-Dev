# GENESIS — Agent and Adjudication State Machine Contract (AAS-001)
**Version:** 0.1.0 | **Status:** proposed; owner review, not runtime-certified | **Date:** 2026-11-03
**Parent contracts:** GENESIS_GM_ARCHITECTURE.md, RUNTIME_AUTHORITY.md, Contracts/ARTICLES_OF_CREATION.md, Contracts/CAUSAL_INTERACTION_SYSTEM_CONTRACT_v0.1.md (CIS-001).

## Purpose and non-negotiable boundary
Every player or system-generated declaration has an inspectable adjudication lifecycle. Models may interpret and narrate but never create mechanically authoritative truth by assertion. **A failed in-game roll is a valid, committed game outcome; an illegal declaration is a rules rejection; malformed model output is an orchestration failure.** Do not conflate them.

**Historical implementation:** `api_bridge/gm_controllers.py` already names four controllers (GM, Combat Master, Record Keeper, Genesis Steward) and a seeded dice service; `app/genesis-os/src/state/intents.js` dispatches typed intents; `store.js` applies patches and checks authority. This is a unification target, **not** a statement that the complete orchestration state machine already exists.

## State machine: normative target
```text
RECEIVED -> INTERPRETING -> EVIDENCE_GATHERING -> ADJUDICATING
 -> VALIDATING -> PREPARING_COMMIT -> COMMITTED -> PRESENTING -> COMPLETE
                    |            |
                    +--> CLARIFICATION_REQUIRED --> INTERPRETING (new input)
                    +--> RULES_REJECTED --> PRESENTING (no illegal mutation)
                    +--> ORCHESTRATION_FAILED --> BOUNDED_REPAIR --> VALIDATING
                              |                           |
                              +----> FAILED_TERMINAL <----+
  PREPARING_COMMIT -> STALE_REVISION -> REEVALUATE_FROM_CURRENT_STATE
```
- Every transition has a machine-readable reason, trace ID, time, domain, input/output hashes, budget, and expected revision.
- `COMMITTED` requires durable acknowledgement; a fire-and-forget HTTP call does not constitute a successful durable commit. Future implementation must reconcile existing client behavior with this rule.
- `PRESENTING` uses accepted truth or an explicit pending/rejected outcome, never an invented success.
- Multiple domain effects require atomic or compensating coordinator semantics defined explicitly; prefer true transactional commit where durable store supports it.
- Never repeat stochastic adjudication simply because narrative generation failed; retried presentation reuses accepted results.
- Clarification should be reserved for genuinely underspecified actions. Creative attempts should be translated into known primitives where possible, not summarily refused.

## Controllers and ownership
| Capability | Primary owner | Nature | Can authoritatively write? |
|---|---|---|---|
| Player-intent understanding | Steward router + GM interpretation | LLM-assisted, typed proposal | No |
| Exact canon/rules retrieval | Evidence service | Deterministic lookup; lexical/semantic suggestions | No |
| Rules Lawyer | Deterministic preconditions + ruleset adapter, optional explanatory model | Rules adjudication and citation | No direct writes |
| Combat Master | Domain mechanics resolver + optional specialist narration/model | Mechanical proposed outcomes, validated seeded rolls | Only via domain authority |
| Progress Keeper | Progression domain resolver | XP, features, prerequisites, training, costs | Only via progression authority |
| World/Nemesis/Companion planners | Domain-specific planning (BT/GOAP/utility/HTN as evaluated) | Proposed goals and actions | No direct writes |
| Genesis Steward | Orchestrator + deterministic verification | Validates evidence, agency, visibility, ownership, status | Authorizes route, not raw world edits |
| Record Keeper | Commit service | Atomically persists event + state + causal provenance | Sole commit entrypoint, not rules inventor |
| Game Master / Narrator | Player-facing presentation | Knowledge-filtered narrative, choices | No |
| Forge | Authoring/validation/promotion pipeline | Candidate entity proposals and versioned Gold promotion | Only through separate Forge gates |

Multiple names may represent capabilities, not necessarily separate LLM calls or processes. Rule checks, dice, ownership, and replay must be deterministic; LLM involvement is for semantic interpretation, proposal and prose.

## Strict inputs and outputs
```yaml
adjudication_request:
  request_id: unique_id
  campaign_id: campaign_id
  ruleset_version: version
  actor_urid: validated_actor
  declaration: "I pull the blaster with the Force"
  expected_state_revision: 42
  time_mode: turn_driven
  player_visibility: current_projection
adjudication_trace:
  trace_id: trace_id
  states: []                # every lifecycle transition
  interpreted_intent: {}    # declaration -> known action primitives
  evidence_refs: []        # typed ref, source hash, scope and version
  missing_evidence: []
  rules_invoked: []
  domain_owners: []
  required_rolls: []       # service roll IDs/seeds; never model-declared values
  candidate_effects: []
  validation: {legal: null, schema: null, authority: null, invariants: null}
  decision: pending        # committed | legal_failure | rules_rejected | clarification | failed
  transaction_id: null
  committed_event_ids: []
  state_revision_after: null
  knowledge_scope: player
  model_calls: 0
  elapsed_ms: null
  repair_attempts: 0
```
"legal_failure" means legal action, unsuccessful in-fiction outcome (e.g. a miss), NOT a rejection. All references must resolve; untrusted search evidence never outranks authenticated canonical definitions.

## Guardrails and test cases
- Abilities absent from actor sheet => `RULES_REJECTED` without resource consumption; existing Rules Lawyer tests should be preserved.
- Legal attack miss => valid roll and committed event, then truthful narration.
- Player creative speech => may consume no combat action; never grant HP/XP through narrative adjective inference.
- Stale campaign/mount epoch => no cross-campaign commit.
- Offline or failed ledger write => no success acknowledgement; follow explicit recovery semantics.
- Two simultaneous actions against one revision => conflict/serial ordering, no lost updates.
- Model narrates uncommitted outcome => intercepted before presentation.
- Hidden facts => retrieval gated by agent/actor visibility; GM may use private facts only for lawful decisions without leaking them.
- Consequences after commit => CIS-001 produces candidates; new adjudications go through the same kernel.
- Red-team prompt and sabotage intents => preserve player agency when fictional and mechanically legal; classify rather than silently censor fictional consequences.
- Replay original seed, ruleset, action stream => same authoritative results.

## Integration milestones
1. Instrument existing `gm_controllers.py` routes and `intents.js` with trace IDs/statuses (read-only trace first).
2. Build fixture-driven transition table covering all exit conditions.
3. Repair durable commit and authority granularity before trusting replay.
4. Add independent Rules Lawyer checks, sourced to exact rules and state.
5. Run a real 15–20 minute mostly-clickable session with freeform declarations and compare against the trace.

**Ratification gates:** owner approves state names, controller ownership, transaction semantics, and permitted recovery operations. This file does not mutate code or reinterpret the current four-controller implementation.