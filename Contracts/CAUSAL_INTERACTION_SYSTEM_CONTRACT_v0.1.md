# Genesis Protocol — Causal Interaction System Contract (CIS-001)

**Version:** 0.1.0 — Proposed canonical architecture, **NOT owner-ratified or runtime-enforced**  
**Date:** 2026-11-03  
**Scope:** All domains, not exclusively combat or factions  
**Status:** Design candidate / review required under Articles of Creation Article 7  
**Change type:** New documentation only; no schema, runtime, or Gold promotion changes

> **Foundational statement:** Genesis simulates a world in which characters, objects, organizations, and environments possess consistent properties, independent motivations, and consequential interactions. AI makes those interactions feel alive; it does not invent authoritative truth.
>
> **Chaos is the Causal Interaction System.** Synergy is *one relationship type*, not a synonym for all of Chaos. **Chaos is possibility, not randomness** (Articles of Creation, Article 4). Tags and taxonomy identify candidates; typed relationships describe connections; causal rules establish conditional eligibility; domain resolvers establish legal outcomes; the authority/commit layer records truth.

## 1. Terminology and ownership

| Term | Exact meaning | Does NOT mean |
| --- | --- | --- |
| **Entity** | Canonical Registry definition, or identified runtime instance that references one | A free-floating narrative concept |
| **Taxonomy** | Typed classification and inheritance of properties/capabilities | An automatic effect |
| **Tag** | Indexed, validated semantic descriptor; discovery/filtering hint | Sufficient proof that an event occurred |
| **Property / capability** | Reusable claim about an entity, with units/levels/context where applicable | A guaranteed outcome |
| **Status** | A time-bounded or conditional state attached to an instance, with application, stacking, expiry and removal rules | A permanent immutable definition |
| **Typed relationship** | Semantic/casual edge between resolved entities or types, e.g. containment, dependency, resistance, antagonism | An authorized mutation |
| **Synergy** | Cooperative or reinforcing relationship between elements | The entire Chaos system |
| **Causal rule** | Declarative trigger + predicates + exclusion + proposed consequence + evidence | Permission to directly edit state |
| **Event** | Accepted fact about something that happened, with actor, visibility, time, provenance and causal parents | Narrative speculation |
| **Interpretation** | A particular actor's meaning/belief about an observed event; may be false | Objective world truth |
| **Goal / plan** | Actor's intention, resources, prerequisites, steps, and scheduled reconsideration | Guaranteed future event |
| **Domain transition** | Evaluated legal transition under relevant game rules and current state | Arbitrary JSON patch |
| **Authority** | Ownership of allowed mutations, enforced at commit | Proof that a transition is mechanically valid |
| **World scheduler** | Deterministically selects due time-driven jobs and event-driven reactions | Every NPC running an LLM every second |
| **Revelation** | Knowledge-filtered player/UI projection of accepted events | An alternate mutable source of truth |

**Relationship vocabulary (canonical proposal subject to Registry validation):**
synergy, antagonism, inhibition, catalysis, dependency, consumption, production, conversion, resistance, vulnerability, amplification, suppression, containment, contamination, compatibility, incompatibility, trigger, counter.

All relationship targets and sources **MUST resolve** to canonical Registry entities/type definitions or a validated campaign-local instance. No ghost edges. Analogical Discovery may **suggest** typed edges for review; similarity alone never promotes a relationship into Canon.

## 2. Architectural separation: do not collapse these roles

1. **Atomic:** mechanics, definitions, constraints, deterministic resolvers and transition invariants.
2. **Soul:** individual identity, psychology, convictions, motivations, interpretation, expressive guidance and visual DNA; never authority to invent mechanics.
3. **Chaos:** discovers eligible interactions from entities, properties, tags, graph edges, accepted events and context; emits **candidate consequences**, not state.
4. **Domain state machines:** combat, social, relationship, progression, inventory, material/environment, faction/politics, projects, nemesis, exploration, Forge lifecycle; validate legal transitions.
5. **World scheduler:** handles actor agendas, clocks, deadlines, re-evaluations and time-domain activation.
6. **Authority/transaction kernel:** checks owners, path+operation permissions, schemas, invariants, expected revisions, idempotency and cross-domain consistency; commits atomically to durable event ledger + state.
7. **Revelation/AI GM:** projects facts appropriate to player knowledge and narrates established effects; no hidden-state leakage or unilateral mutations.

**Critical:** No single giant game state machine is required. Domain machines share one transition-envelope and commit discipline. A coordinated action affecting multiple owners is committed in an all-or-nothing transaction only after each owner validates its part.

## 3. Universal Causal Rule Template (design target; NOT valid against the current SynergyRules schema yet)

```yaml
contract: CIS-001
version: "0.1.0"
rule_id: rule_unique_stable_id
status: candidate                 # candidate | approved | deprecated
source:
  origin_ref: "source/document/commit"
  schema_version: "TBD"
  ruleset_scope: "campaign_ruleset"
  canon_scope: "original_or_licensed_scope"
participants:
  actor_ref: "<resolved_urid_or_variable>"
  target_ref: "<resolved_urid_or_variable>"
  observer_refs: []              # bound by visibility/knowledge rules
classification:
  relation_types: [trigger, vulnerability]
  capability_refs: []            # properties/statuses registered by URID
  tags: []                       # discovery only; not proof
trigger:
  event_type: event_canonical
  event_schema_ref: "TBD"
predicates:
  all: []                        # conjunction / typed facts
  any: []                        # optional alternatives
  none: []                       # exclusion
  thresholds: []                 # typed, unit-aware when needed
  required_knowledge: []         # observer knew/perceived/learned what, when
  required_resources: []
eligibility:
  uncertainty: deterministic     # deterministic | ruleset_roll | bounded_probability
  resolver_ref: resolver_registered
  rule_precedence: 50
  stacking_policy: "TBD"
candidate:
  consequence_type: consequence_registered
  owning_domain: "registered_domain"
  target_ref: "<resolved_urid>"
  requested_transition: "transition_registered"
  parameters: {}
temporal:
  activation: immediate          # immediate | due_time | conditional_recheck
  earliest_world_time: null
  expiration_world_time: null
  review_policy: on_new_evidence
  simulation_cost_class: event_only
visibility:
  fact_scope: gm_only
  disclosure: on_discovery
causality:
  caused_by_event_ids: []
  idempotency_key: "rule_id:event_id:target_id:phase_or_window"
  max_fanout: 6
  max_depth: "TBD"
evidence:
  match_trace: []                # matched rules, source facts, failed predicates
  expected_state_revision: 0
  validation_result: pending
  owner_decision: pending
```

**Migration note:** Current `schema/SynergyRules.schema.json` is a draft-07 **array schema** of rule objects with `trigger`, `mechanical_effect`, `exclusions`, etc. Current `app/genesis-os/src/state/chaos.js` also uses a distinct baseline `mechanical_effect: {consequence, owner, payload}` shape. This template is a proposed *new normalized contract*, not a drop-in schema or working runtime input. Evolve schemas through a versioned task; never silently reinterpret existing Gold rules.

## 4. Worked rule: Companion witnesses a cruel choice (emotional causal chain)

**Desired chain:** Aero makes a cruel decision → companion witnesses/learns it → evaluates against *their own convictions* → trust may fall, respect/fear may rise → reassessment → goals and behavior change → companion may reconcile, leave, spy, sabotage, defect, or become a nemesis.

**Do not implement this as** `cruel_action => approval -10 => nemesis`.

```yaml
rule_id: rule_companion_moral_reassessment
trigger:
  event_type: morally_salient_action_committed
participants:
  actor_ref: char_aero
  observer_refs: ["<companion_urid>"]
predicates:
  all:
    - observation_proven_or_credible_information_acquired
    - observer_has_personal_conviction_relevant_to_action
    - actor_action_meets_ruleset_defined_moral_context
  none:
    - observer_incapacitated_without_later_information
candidate:
  consequence_type: interpretation_and_relationship_review
  owning_domain: relationship_engine
  requested_transition: evaluate_observer_reaction
  parameters:
    axes: [trust, respect, fear, affection]
    conviction_weights: "from Soul profile, NOT universal values"
temporal:
  activation: immediate
  review_policy: on_new_evidence
causality:
  idempotency_key: "rule_companion_moral_reassessment:event_id:observer_id"
```

**Possible follow-up state machine (each edge gated):**
`unaware -> informed -> evaluating -> concerned -> distrustful -> (reconcile | remain | withdraw | leave_party | covert_opposition | defect | nemesis_candidate)`.

These are **possible states**, not an obligatory sequence. Each branch needs motivations, awareness, resources, opportunities, relationship/party rules, and owner approval. A character may respect power while condemning cruelty; fear, trust, respect, and affection are independent axes. An actor may believe a lie; provenance distinguishes **world fact**, **observed report**, and **actor belief**. Player-facing narration is filtered accordingly.

**Test cases:** eyewitness vs rumor; loyal pacifist vs ruthless soldier; no witness; false accusation; later exoneration; insufficient resources to defect; duplicate delivery of the same event; delayed reconsideration while player is offline.

## 5. Worked rule: Barrel ignition does not imply explosion

**Inheritance:** `physical_object -> container -> barrel`; actual contents are separately referenced; `combustible` is a property, `burning` is a *status*, `contains` is a typed relationship.

1. Accepted event supplies an ignition source/context.
2. Taxonomy retrieves material properties and environment; relationships resolve barrel -> contents, proximity, containment, shielding.
3. A fire rule evaluates eligible ignition conditions through a **material/environment resolver** (the game need not implement chemical CFD).
4. Only after an accepted ignition transition does `burning` become true.
5. A **separate rule** evaluates pressure, confinement, material strength, contents, venting and relevant thresholds; **explosion is not inferred solely from `burning`**.
6. Optional subsequent events (smoke, witness noticing, damage, investigation, grievance) have their own constraints and provenance.

**Test cases:** flammable but no source; burning but open container; noncombustible contents; fire suppression; sealed volatile container without enough pressure; duplicate ignition event; impossible cross-map witness; delayed political investigation.

**Scope:** A practical **material-capability ontology**, not an exhaustive chemical periodic table. Real scientific data may be linked as authored references later; fantasy/Force-reactive materials use ruleset-scoped properties rather than physical claims.

## 6. Living World: actor schedules, emotions, nemesis turns, and faction/city management

**Core contract:** world time progresses only according to a declared campaign time policy. Gameplay commands have an elapsed-time cost; idle simulation is a **configurable mode**, never an implicit guarantee that wall-clock seconds equal world time. On resume, deterministic catch-up must be bounded and avoid unaudited surprise consequences.

**Modes:** `paused`, `turn_driven`, `real_time_scaled` (opt-in), `catch_up_bounded`. The authoritative world clock is persisted. One world tick does **not** mean every NPC gets an LLM call.

**Scheduler sketch:**
```text
on accepted event or world-time advancement:
  collect due jobs (min-heap by due_time, stable actor_id, job_id)
  add event subscribers whose predicates may now change
  coalesce duplicate actor/goal/reason jobs
  for each due job within deterministic budget:
    read authoritative snapshot + actor-visible knowledge
    select eligible goal/plan action (rules-first; model can propose)
    resolve through relevant domain state machine(s)
    validate owner, constraints, resources and expected revisions
    atomically commit accepted envelopes, or record rejection
    schedule next job based on new facts and time
  defer remaining jobs with stable order; never silently delete them
  publish only knowledge-filtered updates to player UI
```

**Actor agenda minimum:** stable URID; motivations/convictions; private knowledge and confidence/source; goals; plans/steps; resources; opportunity and location; risk/budget policy; deadlines; next review time; active/suspended/blocked status. Character, nemesis, polity, faction, city and project may use different goal schemas but share scheduling metadata.

**Event vs time triggers:** witnessing betrayal may trigger immediate consideration; resentment, investigations, propaganda, troop movements, construction, recovery and diplomatic negotiations can be scheduled. Emotional consequences may mature over hours/weeks; not every social change is instant. Party member departure or nemesis conversion requires an explicit permitted transition with evidence.

**Faction-leadership / city-management layer:** when a player gains authority in-world, expose the corresponding management projection (policies, treasury, production, personnel, influence, tradeoffs). The same campaign events and resources apply to individual adventures, faction conflict, and governance: no disconnected mini-game economy.

**Media/reputation layer:** publicity requires transmission, audience reach, credibility, delay and social interpretation. An entertainer with drones and followers may gain/lose ratings only if their actions are recorded, disseminated, recognized and evaluated. Ratings never change solely because the global narrator knows what happened.

**Idle safety:** explicit player preference; pause while in decision windows; bounded catch-up; protect from repeated irreversible developments when absent; report what occurred and why on return; provide deterministic replay and configurable limits. Real-time mode cannot bypass rule validity.

## 7. Canonical relationship graph vs statuses vs tags

**Registry** stores validated entity definitions and typed relationships, with source/target URIDs, directionality, relation category, conditions, scope, evidence, version, and optional strength. Runtime stores instance-specific relation state, beliefs and statuses. Tags accelerate discovery but cannot establish factual relationships.

The graph must support: `contains`, `belongs_to`, `witnessed`, `believes`, `resists`, `vulnerable_to`, `depends_on`, `counteracts`, `amplifies`, `triggers`, etc. Whether those are actual canonical enum IDs requires schema review.

**Universal minimum contract for every entity** (not every entity must have every status/property): stable identity/URID; taxonomy memberships; optional property/status references; typed edges; scope and provenance; ruleset/version; state ownership; visibility policy; event subscription declaration if reactive. Defaults are empty, not invented. Specialist domain extensions own their parameters and units.

## 8. Lessons to adopt selectively

- **KOTOR II / BioWare:** actions alter companions through individual convictions, independent relationship axes, conversations, departures, and transformations; preserve actor agency, not just global approval.
- **Osiris:** declarative facts/events/queries and rule activation; inspectable why/why-not diagnostics; distinct goal lifecycles.
- **Anubis:** per-actor behavioral states/trees separate from world-truth rules. **Lua** is an embeddable scripting language, not mandatory for Genesis. Keep Python/TypeScript and adopt behavior-tree concepts first.
- **Civilization:** deterministic, phased world processing; faction resources, plans and production; bounded actor scheduling and spatial/social consequences.
- **Tabletop D&D:** flexible natural-language actions mapped into reusable mechanical primitives; progression extends action *possibilities* rather than imposing one universal action-point ceiling.
- **Living-world reputation:** news and reactions depend on actual information flow and audience knowledge, not omniscient global flags.

## 9. Existing source lineage — preserve rather than overwrite

- `Contracts/ARTICLES_OF_CREATION.md` Article 2 Atomic, Article 3 Soul, **Article 4 Chaos** ("conditional, emergent behavior"; any profile-enabled entity may host rules; triggered by tags+events; conditional not guaranteed); Article 6 No Silent Loss; Article 7 No Schema Drift; Article 8 Determinism First.
- `Contracts/CHAOS_ENGINE_FOUNDATIONAL_FIVE_COMPLETE.md`: ion vulnerability, fire additive bonus, acid bypass, kinetic reduction, energy resistance — five historical mechanic patterns; **report claim of completion is not independent runtime proof**.
- `Contracts/CHAOS_ENGINE_ENVIRONMENTAL_TRIAD_COMPLETE.md`: underwater aquatic benefit, nonaquatic penalty, fire nullification; some simplified claims should remain ruleset-specific, not universal physics.
- `Contracts/CHAOS_ENGINE_CONSEQUENCE_TRIAD_COMPLETE.md`: kill innocent -> nemesis, heroic quest -> hero tag, faction betrayal -> reputation change; illustrates long-horizon consequences but **not guaranteed or omniscient propagation**.
- `Contracts/chaos_system_walkthrough.md`: tag/event/condition/effect, profile governance and no-bleed.
- `Contracts/tag_system_discovery.md`: versioned lexicon and validator discovery.
- `schema/{SynergyRules,Status,Property,Effect}.schema.json`: existing overlapping structures to reconcile through migration.
- `app/genesis-os/src/state/{chaos,worldPhase,intents,authority,events,store}.js`: runtime contracts; active baseline rule executor has a different shape from SynergyRules draft-07 schema.
- `RUNTIME_AUTHORITY.md`, `CHAOS_AUDIT_OWNER_REVIEW.md`: Chaos cannot directly commit state; legacy baseline rule review gates remain open.

**Known reconciliation gap:** Old reports describe multiple "completed" pillars, while 2026 client Chaos code contains six baseline rules and separate Registry SynergyRules discovery. Historical documentation alone does not establish that the older 14 rules are presently executable. Keep these historical strata distinct; do not silently merge them.

## 10. Acceptance tests required before ratification

1. **Truth vs belief:** a false allegation changes a believer's plan without changing objective event truth.
2. **Observation:** no direct social consequence absent witnessing, transmission or credible later discovery.
3. **Material conditionality:** ignition may occur without explosion; severity and context honored.
4. **No ghost edges:** every typed edge resolves to a Registry definition or validated instance.
5. **No unauthorized writes:** Chaos only proposes; domain owners validate; illegal path/operation rejected.
6. **Atomicity:** multi-owner consequence commits all-or-nothing; failure leaves no partial state.
7. **Replay:** same seed + same prior state + same accepted events + same ruleset version produce identical outcome and schedules.
8. **Idempotency:** replay/duplicate event doesn't recreate a nemesis, double-charge resources or double-count fear.
9. **Bounded propagation:** deterministic fan-out, cycle detection, recursion and budget policies; deferred work is traceable.
10. **World tick:** nemesis, political, companion, production and reputation jobs are evaluated according to due times/knowledge.
11. **Idle/catch-up:** pausing and bounded resumption respect player-set mode and no hidden unbounded elapsed-time simulation.
12. **Progression:** earned powers legally expand the character's action options without bypassing authority or ruleset action economy.
13. **IP/ruleset scope:** original Genesis mechanics remain separable from licensed/third-party Star Wars-specific rules.
14. **Observability:** structured trace includes objectives, triggering events, source facts, failed predicates, candidate effects, owning engine, accepted/rejected decision, causality, next scheduled job and source provenance.

## 11. Decision register: open owner gates (do not silently decide)

- [ ] Ratify **Causal Interaction System** as the formal expanded definition of Chaos (superseding *synonym* "synergy engine" while retaining `SynergyRules` as a legacy schema name pending versioned migration).
- [ ] Set canonical graph relationship IDs, directionality and type inheritance rules.
- [ ] Select minimal universal entity fields vs domain-specific extensions.
- [ ] Define state-machine phase/revision and multi-owner transaction protocol.
- [ ] Define allowed idle simulation modes, default paused behavior, and bounded catch-up budget.
- [ ] Approve status/material interaction predicate vocabulary and units.
- [ ] Approve relationship/belief/conviction model and companion departure/defection/nemesis transition criteria.
- [ ] Approve Chaos baseline rule dispositions in `CHAOS_AUDIT_OWNER_REVIEW.md`.
- [ ] Assign schema version bumps, compatibility/migration plan and deterministic fixtures per Article 7.

**Implementation sequence (proposed):** (A) reconcile schemas and old Chaos records; (B) define normalized CausalRule/TypedRelationship/ActorAgenda/TransitionEnvelope schemas; (C) build deterministic fact-query + rule matcher; (D) build domain-transition/transaction gate and idempotent ledger; (E) add world scheduler; (F) integrate one barrel + one companion + one senator chain end-to-end; (G) test replay, failure, visibility, reload, performance before expanding ontology.

---
*This document preserves user design intent as an explicit reviewable contract. No architectural change becomes ratified canon, and no existing schema or engine is modified, solely because this document exists.*
