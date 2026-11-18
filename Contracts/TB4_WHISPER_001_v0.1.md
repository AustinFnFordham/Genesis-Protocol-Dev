# Genesis Protocol — Turn Builder 4 + WHISPER Design Contract

**Contract ID:** `TB4-WHISPER-001`  
**Version:** `0.1.0` — design baseline / implementation candidate  
**Prepared:** 2026-11-17  
**Owner direction:** Approved in conversation at the concept level: Turn Builder 4 as a player-facing composer; WHISPER as the AMD / emotional-state umbrella; intent matters to morality; every action category has suggestions **and** a custom entry; Taunt is proposed as a **bonus-action mechanic**; free-only testing; no changes to live Hask Meadow.  
**Release status:** **NOT CANONICAL / NOT DEPLOYED / NOT A NEW GAMEPLAY RULING**. The owner has requested this contract and implementation handoff, not production activation. Decisions explicitly labeled *proposed* need owner approval before adoption into live play.  
**Target repository:** `AustinFnFordham/Genesis-Protocol-Dev`  
**Baseline inspected:** `staging/mobile-test` (file-by-file read, 2026-11-17); inspect current branch tips again before changing anything.

## 0. Executive contract

> **Turn Builder 4 is the player-facing interface for expressing what the player wishes to attempt, how, why, and in what order. WHISPER is the separate emotional/intentional/appraisal subsystem: it interprets player-authorized inner context and accepted experience, but cannot take over the player's mind, roll dice, rewrite deeds, or directly author canon.**

The builder is *not* a replacement for the existing scene sequencer, action-economy validator, campaign gateway, GM provider, ledger, or Forge. It is a backward-compatible evolution of `turn-contract/3`. Genesis remains one authoritative game system with many interchangeable GM providers, not parallel worlds per AI.

### Non-negotiable invariants

1. **Agency:** Player characters' thoughts, decisions, dialogue, methods, and continuation are authored by the player. A suggestion, hypothetical, selected tone, or model interpretation is not consent to act.
2. **Trinity:** Atomic owns legal mechanics and durable accepted truth; Soul owns identity and grounded narration; Chaos evaluates conditional typed relationships and candidate consequences. WHISPER spans the *psychological/appraisal* aspects of Soul plus evidence-gated evaluators, without acquiring Atomic write authority.
3. **Truth boundaries:** Distinguish `objective_fact`, `utterance/claim`, `observation`, `belief/interpretation`, `intention`, `attempt`, `resolved_outcome`, and `narrative_presentation`. Claims are not facts. Thoughts are not actions. Dice failure is not moral failure.
4. **Durability:** The existing provider-neutral gateway and canonical Git-backed ledger remain sole accepted-truth path. No second dice, receipt, event, scheduler, lease, or character-state store. No narration presented as accepted before commit.
5. **Secrecy:** Inner feelings may be PC-private; NPCs cannot read them without an explicitly supported information channel. No GM-only knowledge enters a player UI suggestion.
6. **Costs:** Suggestions and deterministic eligibility/ranking cost zero model calls. Novel prose is optional/on-demand or batched into an existing authorized GM call. No paid inference in the acceptance suite.
7. **Staging safety:** Hask Meadow and production deployments are protected. Isolated noncanonical fixtures only; no alterations to historical outcomes, no owner decisions made implicitly.
8. **Backward compatibility:** Existing `turn-contract/1`, `/2`, and `/3` declarations, state snapshots, accepted event types, and saved UI drafts continue reading and validating as before. TB4 fields are optional and versioned.

---

## 1. Source-of-truth inventory and status distinctions

**Existing implementation inspected** (repository path relative to root):

| Path | Currently established | Boundary for TB4 |
|---|---|---|
| `campaigns/starwars_litrpg/creator/TURN_CONTRACT.md` | `turn-contract/3`: context, ordered steps, branches, sequencer, reactions, pending steps, free text | Extend, don't replace; preserve `steps` order and legacy shapes |
| `campaigns/starwars_litrpg/ui/turn_contract.js` | One shared parse/preflight implementation used in browser and GM process | Preserve same semantics and shared validation; add tests before changes |
| `campaigns/starwars_litrpg/ui/src/composer.js` | Mobile/Datapad turn composer and sequence UI | Add player-facing surfaces without creating a second validator |
| `campaigns/starwars_litrpg/ui/build_datapad.py` | Assembles `head.html`, `turn_contract.js`, `core.js`, `composer.js` into one page | Any new browser module must be included in build in deterministic order; no CDN dependency |
| `campaigns/starwars_litrpg/creator/ACTION_ECONOMY_RULING.md` | Provisional scoped object-hand/speech ruling with actual regressions | Don't rewrite Hask history or bill simple narration as an action |
| `campaigns/starwars_litrpg/creator/ENCOUNTER_RULING.md` | Proposed encounter rules; explicitly **not in force** overall; owner decisions remain | Do not silently activate it; use isolated fixtures where appropriate |
| `development/gm_provider/gateway.py` | One provider-neutral deterministic gateway and accepted operation journal | Reuse; do not bypass or reimplement transaction/recovery |
| `development/gm_provider/npc_review.py` | Guards event citations and repeated NPC outcomes, but does not prove judgment | Extend evidence checks without claiming this is full AMD |
| `development/PROVIDER_INTERCHANGE.md` | Release candidate HOLD, provider interchange, recovery, canonical ownership | Preserve accepted receipts and provider handoff semantics |
| `Contracts/CAUSAL_INTERACTION_SYSTEM_CONTRACT_v0.1.md` (`CIS-001`) | Typed causal proposal; **not owner-ratified or runtime-enforced** | Candidate semantics only until ratified; no silent universal rewrite |
| `Contracts/AGENT_ADJUDICATION_STATE_MACHINE_CONTRACT_v0.1.md` (`AAS-001`) | Proposed adjudication lifecycle | Respect legality vs failed check vs malformed orchestration output |
| `Contracts/CHAOS_ORIGIN_AND_DESIGN_DOCTRINE.md` | Chaos is conditional transformation, not random punishment | No tag-only forced nemeses or automatic faction-wide consequences |

**Scope caveat:** Files above may differ across `main`, `staging/mobile-test`, `integration/mobile-test-build`, `dev/encounter-controller`, and other development branches. Claude must compare branch heads and reconcile completed work before selecting the implementation baseline. This contract does not authorize an assumption that a design or fixture is deployed.

---

## 2. Player-facing Turn Builder 4 contract

### 2.1 Proposed layout and flow

1. **Current scene and budget** — visible setting, actor, turn/round state, available action/bonus/reaction, remaining movement, hands, known gear, allies, pending steps, uncertainty, and options derived only from the player-visible context.
2. **WHISPER: beginning-of-turn context (optional)** — player's declared felt emotional state, outward presentation, explicit intention/motive, and optional private reflection. An empty field means *unspecified*, not calm, cold, emotionless, or indifferent.
3. **Compose activity** — Primary Action, Bonus Action, Secondary Activity, Movement, Free Speech, Object Interaction, Reaction, and conditional steps. Each category has (a) up to four situation-grounded suggestions when available, (b) **an always-visible editable custom box**, and (c) a clear cost/uncertainty preview. The player can enter multiple lawful actions within the existing cost model; UI categories are not new economy slots.
4. **Order and branch** — move sequence steps, set `if/unless` conditions, choose targets/methods, use previously accepted plans, show potential stop points. Unresolved conditions never auto-execute. Free text remains first class and unmatched text is retained for adjudication.
5. **Preflight and player confirmation** — show allowed vs uncertain vs illegal, clear reason codes, availability and resource checks, no spoilers, no rolls or predicted successes. Only the player submits the final ordered declaration.
6. **Resolve via gateway** — Atomic preflight and authoritative mechanics, accepted event ledger, publication; do not invent extra player actions or reorder steps.
7. **Outcome and WHISPER review** — resolved consequences are shown separately from optional proposed emotional transitions. Player controls the PC's subjectively felt emotion; rules-defined stress/exhaustion/fear effects can remain mechanical when legally justified.

### 2.2 All categories must support a custom box

| User category | Suggested item example | What custom entry does | Mechanical policy |
|---|---|---|---|
| Primary Action | Dodge / defend / inspect | Explicit method, target, goal | Spends action only when adjudicated as action |
| Bonus Action | **Taunt** | Player chooses exact words, gestures, delivery | Bonus slot only when an authorized Taunt mechanic/feature applies |
| Secondary Activity | Distract, coordinate, perform supporting gesture | Describe supporting conduct | **Grouping/semantic annotation, not a free extra action**; classify actual cost per rules |
| Movement | Position behind cover | Exact path/destination | Movement and obstruction checks |
| Free Speech | Warn Wick | Player's verbatim words | Short speech costless; extended social attempt may be an action |
| Object Interaction | Operate latch, retrieve item | Which hand/object/how | Existing free interaction, second may cost action; ordinary reposition/release costless |
| Reaction | Use available defensive reaction | Player-defined trigger/response | Trigger and eligibility checked; never execute automatic new choice |
| Emotional Context | Afraid but controlled | Player describes felt state and expression | Never automatically becomes action cost or moral score |
| Intent / Motive | Protect ally | Player-authored reason; may be unspecified | Admissible evidence, not guaranteed truth about unseen actors |
| Conditional Sequence | If predator lunges... | Planned steps, stop conditions | Existing `turn-contract/3` sequencer semantics |

**No silent interpretation loss:** Custom input must survive UI → declaration → preflight → accepted operation/projection (as appropriate). Maintain original literal text alongside any normalized interpretation. Unmapped text is never discarded or recast as free mechanical capability.

### 2.3 Suggestion engine (not WHISPER itself)

A small, deterministic suggestion selector is a **Turn Builder** subcomponent, not a model agent and not the WHISPER identity. Candidate sources: approved action/ability/gear records, known threats and distances, current scene affordances, established styles explicitly selected by the player, and validated pending steps.

- Gate candidates by actor, ruleset/campaign grants, resources, hand/position availability, visibility, and current step order; do **not** use hidden DCs, unrevealed enemies, GM plans, or NPC secrets.
- Rank legal/uncertain candidates using documented stable weights and ties by stable id. Inputs: scene relevance, legal feasibility, explicit player style, diversification, and optionally last-used repetition penalty. **No statistical/player-psychological profiling from private thoughts** without opt-in.
- Show up to four; never fake a legal option when zero candidates exist; **always show Custom**.
- Mark candidates `known_legal`, `needs_adjudication`, or `blocked` with meaningful reasons. A suggestion cannot grant a skill, spell, power, extra movement, or bonus slot.
- Generation budget: deterministic ranking **0 paid API calls**; on-demand imaginative flavor only if requested and cost permitted; cached templates preferred.

### 2.4 Intrusive Thoughts / “What if...?”

An optional, collapsed **creative thought experiment** controls. It may expose contrasting approaches, including dark, fearful, impulsive, ruthless, self-protective, or surprisingly compassionate possibilities.

- **No thought is a confession or established emotion.** Viewing, expanding, dismissing, or hovering over a thought creates no canonical record, motive, alignment delta, or player profile.
- No one is forced to have such a thought; never frame it as a fact about the PC.
- If the player explicitly **writes or adopts** private internal thought, persist only through authorized PC-private fields, with provenance `player_explicit` and appropriate visibility. If the player later chooses an actual deed, that is a *new action declaration* subject to legality and consequences.
- No auto-generation of four novel ideas per card. Use optional zero-cost authored/cached alternatives; one requested novel variant may be batched into a model call already made for the turn, if the provider supports it and the player requests it.
- Hide from observers unless an observed outward expression, confession, mind-reading mechanic, or valid evidence channel actually establishes it.

---

## 3. WHISPER: emotional / intentional / appraisal umbrella

**Name:** `WHISPER` (owner-selected). **Boundary:** separate reusable module, not a fourth Trinity authority lane or an LLM always running. WHISPER can propose appraisals and projections; accepted mutation still passes domain owner + gateway transaction.

### 3.1 Three independently modeled axes

1. **Moral appraisal:** what was intentionally chosen, attempted, omitted, and done; what the actor reasonably knew or could foresee; ability, feasible alternatives, coercion, necessity, proportionality, threat, and outcome. An unsuccessful attempted cruel act may still be morally relevant; a failed rescue is not automatically immoral. Choice not to help requires evidence of awareness, feasible capacity, stakes, and volition. No all-seeing morality metric.
2. **Psychological appraisal:** what the event means to this actor given their declared emotional context, memories, identity, relationship, goals, stress load, and coping style. Distinguish internal feeling from visible expression and from actual behavior. No diagnosis from a flat response or single emotion.
3. **Social appraisal:** what others witnessed, heard, believed, inferred, or learned through legal channels. Reputation and relationship consequences require actor-specific exposure/knowledge, not omniscient broadcast.

All three may disagree. Intent may influence moral assessment without guaranteeing success. The same outward action can correspond to different motives. Inner emotion alone never defines light/dark alignment.

### 3.2 Start-of-turn player context

Optional fields: `felt_emotion` (enum/custom text, may be multiple), `expression` (visible or masked), `motive` (player-authored goal/meaning), `reflection` (private notes), `visibility` per field, and `provenance` of explicit player authorship. A blank state is `unspecified`, **not** `none_felt` or `calm`. When player chooses `none_felt`, it only describes the subjective claim; it is not a psychiatric conclusion.

Examples:
- Felt: `fear`; expression: `controlled`; motive: `protect Wick`.
- Felt: `anger`; expression: `warm`; motive: `defend my integrity`.
- Unspecified: no emotional inference and no morale penalty.

### 3.3 During and after the turn

- The system observes **accepted** events, attempted acts, explicit motives, established situational facts, meaningful omissions when observable, and mechanically recorded effects. It never treats an unaccepted draft as history.
- WHISPER may calculate *appraisal candidates* (e.g., plausible relief, lingering fear, pride, guilt, vigilance, reinforced resolve, or no supported change) and cite evidence/uncertainty. **These are not automatic PC feelings.**
- Player PC: private emotional-transition proposals are optional `accept | edit | reject | defer`; without acceptance they remain noncanonical. A player's explicit feeling should not be contradicted by an LLM. Mechanical stress or strain can change only through a validated ruleset mechanic, with proper consent/authority.
- NPC: valid GM/domain evaluations may accept contextually grounded transitions through existing ownership and `npc_review` evidence checks, but no mechanical compulsion absent rules.
- Repeated trauma, injuries, long-standing stress, resilience, or coping patterns are longitudinal hypotheses fed by multiple events and time—not predetermined permanent mental effects from one loss.
- Emotional state is not morality; moral appraisal never equals raw success/failure. A character may feel anger and act mercifully; peace and intentional cruelty are possible.

### 3.4 Provisional math — interfaces, not invented coefficients

Define candidate appraisal **signatures** while leaving numerical weights noncanonical:

```text
MoralAppraisal = MoralRule(accepted_attempt_or_action, declared_intent,
                         known_facts, feasible_choices, coercion, risk,
                         proportionality, accepted_outcome, rule_profile)

PsychologicalCandidate = IndividualAppraisal(accepted_event,
                          actor_knowledge, event_grounded_memories,
                          identity_and_goals, player_emotion_context,
                          situational_constraints, elapsed_time)

SocialCandidate = ObserverAppraisal(accepted_event_or_claim,
                  observer_exposure, observer_knowledge_and_beliefs,
                  relationship_context, communication_channel, world_time)
```

No numerical dark-side meter, emotional modifiers, trust delta, stress value, or AMD coefficients are authorized by this contract. A future calibration must specify domain, dimensions, valid ranges, transition timescales, baselines, tests, and consent semantics. Existing AMD experimental formulas remain historical candidates, not deployed rules.

---

## 4. Algorithms A / B / C — minimum vertical slice

### A. Evidence-grounded knowledge (small bounded kernel)

Implement reusable **typed evidence envelopes**—not a new canonical database. Separate `fact`, `claim`, `speech`, `observation`, `belief`, `inference`, `intention`, `attempt`, `outcome`, with IDs/actor, campaign, source accepted event, world time, scope, provenance, confidence/evidence *when appropriate*, and retraction/correction references. No arbitrary float certainty required for a first slice.

- `claim('dockworkers stole crates')` does not become `fact('dockworkers stole crates')`.
- `player_private(fear)` does not become `npc_known(fear)`.
- A private GM record cannot be returned in a player suggestion or render payload.
- Retrieve visibility-filtered evidence **before** any semantic ranking; rejected candidates never enter a model context.
- Reuse canonical ledger/event IDs and Registry entity IDs where available; never invent ghost relations.

### B. Event-grounded episodic memory + appraisal

A memory record references at least a validated accepted event (or an established in-world observation), perceiving actor, time, channel, subject, salience candidate, and visibility. Use deterministic memory retrieval first (actor/participants/time/relevance); optional semantic similarity only ranks **pre-authorized** candidates and never makes truth.

Minimum examples: Neri remembers Sera's speech if she witnessed it; doesn't if absent; a PC's privately selected emotion is not added to Neri's memory. Consequence of repeated events is accumulated only via justified evidence, not predetermined numerical diagnosis. Existing `npc_review.py` structural checks are retained.

### C. Typed causal dependency resolution

Start with a small registered set: `observes`, `communicates`, `believes`, `protects`, `threatens`, `depends_on`, `trusts`, plus mapped CIS-001 canonical relations where already valid. Do **not** silently alter the global ontology; names not in the canonical Registry remain fixture-local candidates pending review.

`accepted event -> eligible rules by event type + properties -> predicate filtering -> owning-domain proposal -> dependency ordering -> authority/invariant validation -> single durable commit`. Require causal parent event references, valid entities, supported knowledge/time preconditions, bounded work, stable IDs, idempotence, and explicit *no effect* where insufficient evidence. Two independent chains may remain separate until a supported linking event.

**No global SID propagation this milestone.** Collect properly typed exposure/observation records; aggregate cultural transition equations and population mechanics come later. No forced riots, nemeses, reputation penalties, or Dark Side transitions on text-tag match alone.

### 4.1 Pure deterministic pipeline (candidate)

```python
# Interfaces only; never bypass the existing gateway.

def preview_suggestions(public_ctx, authorized_style, draft):
    candidates = derive_candidates(public_ctx, draft)            # NO secrets
    return stable_rank(filter_by_rules(candidates, public_ctx), authorized_style)[:4]


def propose_appraisals(accepted_events, actor_view, explicit_context):
    evidence = retrieve_actor_scoped_evidence(accepted_events, actor_view)
    memories = retrieve_event_linked_memories(evidence, actor_view)
    return evaluate_candidate_meanings(evidence, memories, explicit_context)


def propose_consequences(accepted_event, current_snapshot):
    eligible = discover_registered_typed_rules(accepted_event, current_snapshot)
    return bounded_dependency_resolve(
        [r.propose(accepted_event) for r in eligible if r.predicates_hold(current_snapshot)]
    )  # returned proposals only — gateway validates & commits
```

---

## 5. Taunt and action-economy ruling boundary

**Owner direction:** Taunt should be a **bonus-action mechanic**, not merely a decorative insult card and not charged as a primary action. Player chooses exact delivery. Distinguish brief costless speech from a rule-invoking mechanical Taunt.

**Important conflict:** The inspected `ENCOUNTER_RULING.md` says a bonus action exists only when a ruleset feature grants it and the ruling is marked provisional/not broadly in force. Therefore:

- **Proposed change:** an opt-in **Genesis campaign ruleset grant** for `bonus_action:taunt`, available in an **isolated noncanonical test fixture**, subject to owner approval and balance review before any live campaign adoption.
- **Cost:** 1 bonus action. It never consumes the primary action merely because it's speech. The player can provide text, gesture, target, motive, and method.
- **Effect:** an attempted attention/provocation influence that requires evidence of eligible target, perception/communication channel, target motivations, and any chosen ruleset resolution. It **does not mind-control or force an attack** and doesn't override NPC autonomy.
- **Resolution:** don't invent DC, resistance stat, modifier, cooldown, or compelled-target behavior. Mark unresolved test profile details for owner review; a minimal fixture may test cost, legal parsing, and proposal shapes without resolving a social effect.
- **Compatibility:** if not explicitly granted/configured, present `Taunt` as a proposed custom/needs-adjudication action, not as a secretly legal combat bonus action. Ordinary taunting speech remains costless within campaign rules for brief speech.
- **Secondary Activity:** not an additional free action slot. It groups supporting speech/gestures/other activity; actual cost is adjudicated by established action rules. No implicit extra turns for Wick or any NPC.

---

## 6. Data interface proposal (noncanonical, additive)

This is a *suggested* shape to be reconciled against actual schema/ledger contracts. Do **not** introduce it as a new required ledger event merely because it appears here.

```json
{
  "schema": "genesis-turn-declaration/4-proposal",
  "actor": "aero",
  "context_id": "<current-public-context-id>",
  "steps": [
    {"id":"s1", "seq":0, "type":"speech", "text":"Wick, behind me!"},
    {"id":"s2", "seq":0, "type":"bonus_action", "option":"taunt", "target":"visible_threat", "text":"Come at me!", "method":"challenge"},
    {"id":"s3", "seq":0, "type":"action", "option":"dodge"}
  ],
  "secondary_activity": [{"step_id":"s1", "role":"supporting", "player_text":"Keep Wick informed"}],
  "whisper": {
    "felt_emotion": ["fear"],
    "expression": "controlled",
    "intention": "protect Wick, not provoke unnecessary cruelty",
    "reflection": null,
    "source": "player_explicit",
    "visibility": "pc_private"
  },
  "unmapped": [],
  "end_turn": false
}
```

**Test-fixture warning:** `taunt` and `dodge` option IDs above are illustrative and must resolve to actual campaign grants/options before being accepted. Existing code may need a different compatible encoding. A WHISPER state might require separate authorized event/projection APIs instead of embedding it in the action envelope; prefer whichever supports accepted-source provenance and private scope without changing canonical operation semantics.

Suggested accepted-projection semantics:

- `draft_suggestion`: ephemeral only, no ledger entry.
- `player_declared_intent` / `player_declared_emotion`: only explicitly submitted by the player, with private scope and revision fence as appropriate.
- `accepted_attempt` / `resolved_outcome`: existing Atomic accepted event(s), with actor, target, outcome, provenance and timestamps.
- `appraisal_candidate`: derived/noncanonical; keep separate from subjective PC state.
- `player_accepted_emotional_transition`: only after explicit player authorization and gateway validation.
- `npc_appraisal_candidate`: GM proposal, accepted only after the domain/evidence/authority gates.

---

## 7. Acceptance test matrix (all free; scripted first)

| ID | Test | Required outcome |
|---|---|---|
| TB4-01 | All 9 visible categories populated | Each has explicit Custom box; examples optional, no silent missing text |
| TB4-02 | Free text with ordered/conditional steps | Parser retains original text; same rules in UI and Node preflight |
| TB4-03 | Custom bonus Taunt in approved sandbox fixture | Charges exactly one bonus action, not primary; preserves exact speech |
| TB4-04 | Taunt without campaign grant | Proper `needs_adjudication`/blocked feedback; never silently enables feature |
| TB4-05 | Brief insult without Taunt mechanic | Ordinary speech costless; no guaranteed provoke effect |
| TB4-06 | Secondary activity carries mechanical action | Correct actual cost; never free extra action |
| TB4-07 | Movement/hand/object action order | Existing checks unchanged; valid plans pass, invalid stop with reasons |
| TB4-08 | NPC ally cooperation | Cannot compel Wick, cannot borrow his action, no invented refusal |
| TB4-09 | Scene interrupted by combat or reaction | Pending steps and player choice preserved, no unauthorized continuation |
| TB4-10 | Optional emotional context unspecified | No inferred coldness, absence of emotion, sociopathy, or morality change |
| TB4-11 | Felt fear + calm expression | Internally private fear not disclosed to NPC; visible calm may be perceived |
| TB4-12 | Open/dismiss dark hypothetical | ZERO canonical change, zero model calls, zero moral consequence |
| TB4-13 | Explicitly attempt unjustified harm and miss | Attempt accepted; moral proposal can consider known intent and attempted act, not treat miss as mercy |
| TB4-14 | Failed rescue despite sincere intent | No automatic evil/moral penalty; possible psychological appraisal only if evidenced |
| TB4-15 | Decline to help | Require awareness, feasible capacity, alternatives, coercion/risk context; otherwise unresolved |
| TB4-16 | False accusation heard by 12 | `claim` persists; never upgrades to `fact`; observer knowledge remains scoped |
| TB4-17 | Observer not present | No invented memory/anger, no retroactive exposure |
| TB4-18 | Actor-private emotion plus independent observer | Observer cannot query private emotion by generic context retrieval |
| TB4-19 | Typed relationship targets | Valid Registry/instance IDs; reject unknown ghost edges |
| TB4-20 | Consequence eligibility lacks predicates | No effect; diagnostic reason returned; no arbitrary nemesis/riot |
| TB4-21 | Two independent events / conditional time | No premature merge; time and prerequisites enforced |
| TB4-22 | Repeated action id, crash/restart, provider interchange | Same accepted dice/operation/ledger outcome; no duplicate state |
| TB4-23 | Legacy `turn-contract/1` through `/3` fixtures | Byte-relevant behavior unchanged; old drafts load without requiring WHISPER |
| TB4-24 | Mobile iPad-size composition and custom text | Keyboard, scroll, save, error recovery usable; no hidden controls |
| TB4-25 | Cost profiler for fixture suite | Zero paid model calls; deterministic latency and memory recorded |
| TB4-26 | Player-owned PC after result | Only approved transition is canonical; AI cannot force internal feeling |
| TB4-27 | Two different intents, same final dice outcome | Moral and narrative candidates differ only where supported by evidence |
| TB4-28 | Same character emotion, opposed acts | No alignment change from emotion alone; conduct drives candidate appraisal |

For each: fixture ID, branch/commit, pre-state digest, input declaration, expected accepted events, protected invariants, source references, result, diff, memory/latency, and evidence of no protected path changes.

### 7.1 Private UAT

**One informed tester is sufficient for this stage: the project owner.** Separate reproducible technical gates from subjective fun/agency/clarity ratings (1–5). Don't claim statistical generality or create a public beta. Keep a private issue log with exact seed/fixture/turn/commit. Tests on iPad/Codespaces may preview a static page, but a browser is not authoritative gameplay infrastructure.

### 7.2 Noncanonical fixtures

At minimum:
1. `CMP-001 Ten Missing Crates` (freeze a consistent narrative; private knowledge/false accusation/witness variation).
2. `TB4-WICK-001` (Aero, Wick, fear vs outward composure, legal/illegal Taunt, interruption).
3. `TB4-MORAL-001` (harm attempted/missed, rescue failed, feasible omission, compelled action, witness/no witness).
4. `TB4-RECOVERY-001` (fixed accepted dice and provider transition with a restarted action).

Tests must not alter `campaigns/starwars_litrpg/runs/hask_meadow_r2/`, its public/hidden ledger or live Datapad. Do not reuse live action IDs or leak hidden GM data into public outputs.

---

## 8. Modular implementation plan — not a rewrite

**Suggested layout (reconcile with current code, avoid needless new folders):**

- `ui/turn_contract.js` — authoritative *preflight parse and cost* for both browser and Node, optional TB4 fields; no separate parser with divergent rules.
- `ui/src/composer.js` — TB4 component surfaces, per-category custom input, WHISPER selector, event/step order, preview; preserve current UI state and schema migration.
- `ui/src/<suggestions-module>.js` — small pure deterministic source-scoped suggestion selector; inline via `build_datapad.py` in correct order.
- `development/<whisper>/` or equivalent — pure, testable `WHISPER` proposal logic for player-explicit context, evidence-backed appraisal, memory retrieval; can be language-neutral fixture initially.
- `development/<causal-fixtures>/` or equivalent — minimal typed evidence/relations evaluators; use existing canonical registry and gateway when an actual consequence is accepted.
- `tests` near existing relevant test paths — source-precise regression and fixtures.
- `Contracts/TB4_WHISPER_001.md` in a **new isolated development branch** once tests and document alignment are verified.

Only implement layers whose dependency contracts are actually available. Where schema/authority seams aren't ready, deliver a **read-only pure evaluator with fixtures**, explicit limitations and an integration contract; do not inject unvalidated events into the gateway to create the appearance of completeness.

### Cost & deployment

- Tests: offline, free, scripted/mock provider only; no live OpenAI, Gemini, Claude API calls.
- Development: local machine or included Codespaces resources; avoid enabling overage billing. No external production service, no new paid hosting.
- Provider access: reuse **existing** Oracle/OAuth/Git gateway. Do not create new MCP adapters or unrelated authentication middleware.
- Remote release: **HOLD**. A current read-only staging check returned `shared-1` at revision `40`, ledger `evt_0043`, pending `shared-0002`, and `storage_recovery_required=true`; treat this as a blocker to live turn tests until separately resolved. The available MCP tools in this ChatGPT session are read-only.
- No modifications to live Hask Meadow, no deployment, no `main` merge without owner approval.

---

## 9. Approval and conflict register

**Concepts approved in conversation:**

- Turn Builder is the player-facing interface; WHISPER is AMD/emotional context umbrella, not the suggestions module.
- Emotion != intent != action != outcome; all are separate.
- Every Turn Builder category has a custom text entry; suggestions are helpful options, never a closed command set.
- Taunt belongs under the **Bonus Action** category and is intended as a mechanical option, not merely a dialogue suggestion.
- Custom player words are preserved. No prescribed good/evil button required.
- Moral evaluation considers deliberate acts, attempted harm, feasible omissions, and contextual intention; psychological response is distinct from morality.
- Use free testing and keep working toward cross-provider continuity without rebuilding gateway.

**New mechanical/details still require owner ratification or verified canonical ruleset source:**

1. Whether **baseline Taunt** is available to all PCs/creatures, only to certain classes/features, or only in selected campaign rulesets. This proposal uses **isolated opt-in grant** rather than silently granting it globally.
2. Taunt resolution mechanics: resisting attribute/check, targets, range, duration, repeated-use balance, stacking, counterplay, and failure effects. **DO NOT INVENT THESE.**
3. Which WHISPER fields are formally canonical events versus private player projections, and when user confirmation is requested.
4. Whether the player consents to private long-term preference learning from play, beyond explicit per-turn style choices. Default **off**.
5. Whether rules-defined alignment/light-dark mechanics are active in a selected campaign; no universal automatic morality meter.
6. AMD numeric weights and long-term psychological mechanics; SID remains later.
7. Activation of the November 15 encounter-controller ruling in live Hask Meadow remains **not authorized** by this contract.

**Conflict treatment:** When this contract suggests behavior differing from an in-force campaign ruling, maintain the existing ruling in live code; implement the new behavior only behind a noncanonical opt-in fixture and report the conflict for owner decision.

---

## 10. Definition of done

This milestone is *ready for private UAT* only when:

- The updated builder demonstrably supports every category's custom declarations, preserves plan ordering/branches/pending steps and established action-economy protections.
- WHISPER accepts explicit emotional context, distinguishes it from intent/action/result, and never auto-authors a PC's private feeling or moral penalty.
- A/B/C components provide working, offline, evidence-linked minimal tests with no fabricated knowledge or causality.
- Isolated bonus-action Taunt fixture is legal only under an explicit test grant; no forced attack, unapproved DC, or extra action.
- Old contract fixtures and all relevant repository regressions pass with results recorded. Failing existing tests are not silenced.
- Public/GM/private data separation, replay, recovery, operation identities and existing provider interchange are unchanged.
- iPad-size UI is visually and functionally checked; owner can privately rate fun/agency/clarity.
- New branch, committed documented increments, protected-path diff, blocker report, honest incomplete items, and no release to Hask Meadow.

---

## 11. Source references (inspected)

Links below reference the inspected branch, not necessarily the current release.

- [Composite Turn Contract /3](https://github.com/AustinFnFordham/Genesis-Protocol-Dev/blob/staging/mobile-test/campaigns/starwars_litrpg/creator/TURN_CONTRACT.md)
- [Shared JS preflight](https://github.com/AustinFnFordham/Genesis-Protocol-Dev/blob/staging/mobile-test/campaigns/starwars_litrpg/ui/turn_contract.js)
- [Datapad composer](https://github.com/AustinFnFordham/Genesis-Protocol-Dev/blob/staging/mobile-test/campaigns/starwars_litrpg/ui/src/composer.js)
- [Datapad builder](https://github.com/AustinFnFordham/Genesis-Protocol-Dev/blob/staging/mobile-test/campaigns/starwars_litrpg/ui/build_datapad.py)
- [Object/action economy ruling](https://github.com/AustinFnFordham/Genesis-Protocol-Dev/blob/staging/mobile-test/campaigns/starwars_litrpg/creator/ACTION_ECONOMY_RULING.md)
- [Encounter ruling (provisional)](https://github.com/AustinFnFordham/Genesis-Protocol-Dev/blob/staging/mobile-test/campaigns/starwars_litrpg/creator/ENCOUNTER_RULING.md)
- [Provider gateway](https://github.com/AustinFnFordham/Genesis-Protocol-Dev/blob/staging/mobile-test/development/gm_provider/gateway.py)
- [NPC evaluation guard](https://github.com/AustinFnFordham/Genesis-Protocol-Dev/blob/staging/mobile-test/development/gm_provider/npc_review.py)
- [Provider interchange HOLD](https://github.com/AustinFnFordham/Genesis-Protocol-Dev/blob/staging/mobile-test/development/PROVIDER_INTERCHANGE.md)
- [CIS-001 proposal](https://github.com/AustinFnFordham/Genesis-Protocol-Dev/blob/staging/mobile-test/Contracts/CAUSAL_INTERACTION_SYSTEM_CONTRACT_v0.1.md)
- [AAS-001 proposal](https://github.com/AustinFnFordham/Genesis-Protocol-Dev/blob/staging/mobile-test/Contracts/AGENT_ADJUDICATION_STATE_MACHINE_CONTRACT_v0.1.md)
- [Chaos Doctrine](https://github.com/AustinFnFordham/Genesis-Protocol-Dev/blob/staging/mobile-test/Contracts/CHAOS_ORIGIN_AND_DESIGN_DOCTRINE.md)

**End of TB4-WHISPER-001 v0.1.0.**

---

## Addendum A — Owner decisions 2026-11-17 (evening), recorded verbatim in intent

Supersedes the matching open items in §9 (items 3, 4 and the AMD/causal gates as stated below). Everything else in v0.1.0 stands.

1. **Permanent emotional records — approved with conditions.** WHISPER separates temporary states from meaningful long-term
   experiences. Player-declared feelings may be kept in the PC's *private episodic history* with event sources, timestamps,
   circumstances and visibility. Meaningful or repeated experiences may produce *candidates* for long-term development.
   Permanent subjective states, personality changes, convictions and psychological interpretations for the PC require
   explicit player confirmation. No automatic diagnosis, moralizing or personality rewrite. Mechanical stress, fatigue,
   fear and other conditions remain under the gameplay rules and Atomic authority.
2. **Post-turn emotional suggestions — approved.** After a consequential turn WHISPER evaluates accepted events, the PC's
   established history, the start-of-turn context, declared intentions and actual outcomes, and may propose plausible
   transitions with their supporting evidence. The player answers Accept / Edit / Reject / Defer, or writes a completely
   custom response. Nothing is committed for the PC automatically. No numerical AMD coefficients, no automatic alignment.
3. **Actor-specific NPC knowledge — approved.** Algorithm A feeds the GM's NPC context with strict actor-specific
   visibility: an NPC knows only what observation, communication, memory, inference or another authorized source supports;
   facts, claims, beliefs, observations and interpretations stay distinct; NPCs never receive the player's private WHISPER
   feelings, intentions, reflections or GM-only knowledge. NPC appraisals use the NPC's own identity, knowledge, memories
   and circumstances. Behind a testable switch, verified against the knowledge-boundary fixtures before live use.
4. **Initial typed causal families — approved for bounded testing:** (1) information exposure and communication;
   (2) event-grounded individual memory and appraisal; (3) evidence-grounded relationship consequence candidates;
   (4) explicitly approved mechanical status effects. Every relationship resolves to a valid entity or campaign-local
   instance. Every proposal names its triggering event, supporting evidence, prerequisites, affected entities and owning
   domain. A possible consequence is not an inevitable one. No automatic commits to morality, personality, relationships,
   factions, cultures or world state; no arbitrary weights, unrestricted recursion, invented NPC knowledge or automatic
   nemesis generation. Legal effects go through the existing gateway and domain authority only.

Live gating: Hask Meadow is not advanced and the new causal/psychological runtime behaviour is not enabled live until
its end-to-end tests are verified.
