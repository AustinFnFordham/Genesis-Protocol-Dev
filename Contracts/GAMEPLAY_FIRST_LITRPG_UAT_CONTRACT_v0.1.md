# GENESIS — Gameplay-First LitRPG UAT and Causal Stress-Test Contract (UAT-001)
**Version:** 0.1.0 | **Status:** proposed, gameplay sessions not yet executed under this contract | **Date:** 2026-11-03
**Parents:** CIS-001, AAS-001, HRM-001, ALG-001; GENESIS_GM_ARCHITECTURE.md

## North Star / prior design direction
Genesis should **feel like a cinematic single-player RPG with real tabletop freedom**, not a chatbot or developer console. Test an original-world litRPG with sharp, character-driven, irreverent, occasionally absurd comedy (user's Dungeon Crawler Carl-style tonal reference), without copying the copyrighted book's prose, distinctive characters, or plot. **Entertaining and zany is authored tone; contradictory state, nonsensical rules, and broken AI are bugs.**

Prior campaign/test discussions favor 15–20 minutes of minimal typing, 4–6 contextual and *executable* suggestions where suitable, click-to-draft without auto-submit, always-available freeform declarations, active character/scene UI, autonomous world reactions, and an event-ledger-first gameplay-to-novel pipeline. A litRPG **fictional System** is an in-world personality and presentation device; it never overrides the **real authoritative runtime**.

The UAT harness must not be a static scripted story. Player agency can cause victory, chaos, betrayal, death or a different protagonist. Once gameplay is committed, a future Chronicle/novelization pass may embellish prose but **cannot invent causally consequential events**.

## Two complementary test lanes
1. **Deterministic contract tests:** fixtures with expected state transitions, rejected actions, stable seeds, exhaustive edge cases, replay.
2. **Exploratory human gameplay:** unpredictable natural language, social interactions, system abuse, comedic choices, odd environmental usage, tactical improvisation; compare observable traces and flag cases needing better abstractions.

Use metamorphic testing: change one input (witness present/absent, barrel sealed/open, senator funding enough/not enough) and assert that only causally related outcomes change. Use property-based generation of status/entity combinations and model-driven adversarial prompts, with bounded case count. Minimal reproduction for each discovered defect becomes a permanent regression fixture.

## Core reusable test scenario template
```yaml
case_id: uat_causes_001
title: "Cruel choice with possible companion defection"
intent_family: social_moral
fixture:
  ruleset_version: pinned
  campaign_id: isolated_test_run
  seed: 101
  state_snapshot_sha256: pinned
  entities: [char_aero, companion_test] # resolved fixtures only
  relationship_edges: []
  statuses: []
  actor_beliefs: []
  knowledge_visibility: []
  world_clock: {mode: turn_driven, time: "day_0"}
entry:
  location: defined
  initial_event_ids: []
  prompt_to_player: "..."
  player_options: []            # suggested, not exhaustive
actions:
  - natural_language: "..."
    interpreted_intent: ""
expected:
  required_invariants:
    - "no unauthorized canonical mutation"
    - "every changed field cites accepted event"
  allowed_outcomes: []          # lawful branching
  forbidden_outcomes: []        # ghost knowledge, unearned abilities, etc.
  required_traces: [retrieval, adjudication, authority, ledger, chaos, scheduler, narration]
  temporal_expectations: []
  visibility_expectations: []
variation_axes:
  - witness_present
  - reputation_source_reliable
  - actor_has_resources
  - actor_has_relevant_conviction
observations:
  trace_refs: []
  actual_events: []
  diffs: []
  failure_class: null
  severity: null
  owner: null
  reproduction_steps: []
  status: not_run
```

## Three interacting launch scenarios
**A. Companion's betrayal:** Aero acts cruelly -> witness or hears report -> evaluate **individual convictions** -> trust down, respect/fear possibly up -> private goals reweighted -> remain/reconcile/leave/covert opposition/defect/nemesis **only if independently justified**. Tests false rumors, memory, missed witness, contradictory beliefs, private planning, and delayed departure.

**B. Environmental chain:** source of heat + properties + actual target material/context -> eligible ignition -> status burning; explosion **not implied**. Observe smoke, damage, witnesses, later response only with valid causal chains. Tests statuses, stacking, map/line of sight, multi-step effects, physics abstractions.

**C. Political plot:** senator/faction sees verified information -> choose goal/plan with resources, influence and knowledge -> schedule intelligence gathering, propaganda or retaliation -> NPCs act offscreen -> outcomes persist and may surface via media/publicity. Tests world clock, GOAP/HTN, budgets, economy, leadership/governance mini-game projection.

**Integration twist:** The barrel incident can be misrepresented by political propaganda; companion may believe the allegation; player investigation may reveal contrary evidence; a nemesis may use the incident to recruit allies. All edges must have provenance and legal transition owners.

## Coverage matrix
Action categories: speech, persuasion, freeform deception, investigation, Force/tech powers, improvised items, navigation, combat, environmental manipulation, companion commands, sabotage, faction policy, commerce, prolonged idle, reload/new run, cross-campaign switches. Each must exercise clean success, legitimate failure, illegal intent, ambiguous intent, adversarial prompting, stale revision, denied mutation, replay and delayed consequences as applicable.

**Regression attacks:** AI tries to grant HP, XP or powers from narrative adjectives; narrator voices player; party member knows unwitnessed information; too many repeated dialogue suggestions; unauthorized environmental explosion; immediate omniscient nemesis; doubled effects on duplicate dispatch; missed ledger write; hidden-source leakage; failed actor agenda impossible resource spend; stale campaign projections; UI click silently executes instead of drafting; comic narration changes committed world state.

## Acceptance metrics
- **Safety/canon invariants (hard zero target):** unauthorized writes, fabricated rules/powers, ghost relationships, invisible knowledge leaks, uncommitted outcomes narrated as true, duplicate commits, replay divergence.
- **Correctness:** legal-intent handling, rules citation accuracy, cause/effect attribution, domain-state consistency, schema validity.
- **Playability:** 15–20 minute session continuity; meaningful choice diversity, freeform declaration success, scene progression, agency preservation, progression feels earned; no debugging console in normal play.
- **Performance:** time-to-first response, p50/p95 adjudication and UI latency, model cost, scheduler work per world-phase and catch-up.
- **Entertainment:** human-rated coherence, novelty, stakes, wit, character consistency, surprise and emotional payoff. **Do not optimize humor by making the simulation illogical.**
Do not claim test PASS from authored fixture or developer report. Attach run IDs, logs, screenshots, event diff, replay evidence, human observer rating.

## UAT loop
```text
Select fixture + pin rules/schema + seed
 -> play naturally and try weird, genuinely interesting actions
 -> capture per-turn adjudication trace, retrieval refs, ledger and UI state
 -> assert mechanical and causal invariants
 -> classify failure: retrieval / rules / state machine / authority / scheduler / Chaos / memory / visibility / presentation
 -> minimal reproduction, decide owning layer, propose correction
 -> rerun unit + integration + previous regression corpus
 -> human evaluates fun and story quality
 -> version scenario and report; never silently promote to Gold
```

## Gameplay-to-literature checkpoint
Capture a committed gameplay segment as an immutable causal record; identify emergent arcs; choose a chapter boundary; generate prose from that record; verify every new consequential claim against event refs. The in-world litRPG System voice may be sardonic but never claim a mechanical reward the runtime did not award.

## Exit criteria
Prove the three integrated scenarios can run with real player deviations, multiple world turns, one reload and replay, recoverable failure handling and consistently grounded entertaining narration. **Approval requires both machine evidence and a human playtest sign-off.**