# Genesis Protocol — Four-Controller AI Game Architecture
**Status:** Canonical design spec, v1.1 (v1.0 + §17 Conversational Action Economy addendum)
**Controllers:** Game Master · Combat Master · Record Keeper · Genesis Steward

> **The GM performs the world. The Combat Master resolves conflict.
> The Record Keeper preserves truth. The Steward keeps the system honest.**
>
> **Genesis owns the truth. The controllers interpret the truth.
> The player determines what happens next.**

## 1. Purpose
Run a persistent, rules-bound campaign without forcing one model to simultaneously manage narrative, combat math, continuity, state mutation, dice integrity, and schema compliance. Four controllers, each with a distinct job, limited authority, defined inputs, structured outputs, and explicit restrictions. Primary goal: **prevent role contamination**.

## 2. Design Principles
- **2.1 Genesis owns truth.** Authoritative truth = runtime state, character sheets, campaign state, registry, rules data, chronicle, NPC memory ledgers, hidden GM state, validated patch history. Models interpret, narrate, propose, resolve — never silently overwrite.
- **2.2 Bounded authority.** Each controller writes only its owned slices; all persistent mutation passes validation. (Implemented atop RUNTIME_AUTHORITY.md — the Phase One authority matrix is the enforcement layer.)
- **2.3 Skills specialize behavior.** Controllers are stable roles; skills are mounted procedures beneath them.
- **2.4 Player agency is never optional.** Up to four suggested actions, `custom_action_allowed: true` always. The system never predetermines decisions, feelings, loyalties, moral choices, relationships, or outcomes.
- **2.5 When the player takes a turn, the universe takes its turn.** Every meaningful action is checked for witnesses, information spread, faction response, relationship change, environmental consequence, unresolved threads, delayed effects. **No reaction without a causal path.** (The Chaos matcher is this check.)

## 3. Turn Flow
```
PLAYER declaration
  → GENESIS STEWARD  route / validate input
  → GAME MASTER      interpret intent, frame scene
  → COMBAT MASTER    (only if mechanical resolution required)
  → GENESIS STEWARD  audit rules / dice / schema / agency / visibility
  → RECORD KEEPER    commit approved operations
  → GAME MASTER      narrate the new, validated truth
  → PLAYER
```
Record Keeper may no-op when nothing persistent changed.

## 4. Controllers (authority summaries)
### 4.1 Game Master — player-facing narrative
Owns: scene framing, description, dialogue, NPC portrayal, tone, pacing, transitions, action suggestions, intent interpretation, specialist handoff.
May NOT: roll dice, change HP, consume resources, modify inventory/relationships, create registry truth, resolve combat, commit chronicle, approve its own mutations.
Output: cinematic feed (narration, dialogue beats, visible changes, action window), scene analysis (mode, specialist_required), ≤4 suggested actions, `custom_action_allowed: true`.

### 4.2 Combat Master — mechanical conflict resolution
Owns: initiative, turn order, action economy, movement/position/range/LOS/cover, attacks, saves, damage, healing, reactions, conditions, concentration, resources, legality, enemy tactics, hazards, combat termination.
May NOT: rewrite history, invent loot, change relationships without evidence, commit state, narrate beyond the resolved outcome, approve its own result.
Output: adjudication (legality, rules used, costs, required rolls) → dice results (from the dice SERVICE) → resolution → proposed runtime patch.

### 4.3 Record Keeper — persistence
Owns: runtime commits, sheet updates, chronicle entries (fact vs belief vs rumor), registry updates, NPC memories, relationships, factions, quests, inventory, threads, hidden GM records, replay logs, provenance, snapshots.
May NOT: adjudicate, decide what happened, alter approved outcomes, invent values, expose hidden data, generate new consequences.

### 4.4 Genesis Steward — independent orchestrator + auditor
Owns: routing, controller selection, lookup enforcement, rule/dice/schema validation, agency + continuity + pacing + visibility audit, authority enforcement, commit approval.
May NOT: choose player actions, write prose, invent outcomes, override CM rulings without rules evidence, write chronicle, silently repair state.
**Implementation note:** in Genesis the Steward's validation half is deterministic code (the law does not hallucinate); its judgment half (pacing/agency review) may later mount a low-temp model.

## 5–6. Shared Runtime + Character Sheet Standard
The shared runtime carries: metadata, campaign, player_characters, active_npcs, combat block, environment (visible/hidden objects, exits, hazards, interactables, world damage), relationships, quests, factions, inventory, open_threads, player_knowledge, **hidden_gm_state**, chronicle ref, validation state.
Character Sheets are resolved runtime objects: every feature/power/weapon carries `exact_effect`, costs, ranges, triggers, restrictions. **The GM never needs to remember what a weapon does — the sheet exposes it.** Reference implementation: `api_bridge/gm/aero_character_runtime.yml`. Hidden-state reference: `api_bridge/gm/aero_hidden_gm_ledger.yml` (gm_only; fact/belief/unresolved boundaries + reveal guardrails).

## 7. Turn Routing
Standard narrative, combat, and dialogue routes per the full draft. Dialogue continues while: unresolved player goal, meaningful new information, active emotional exchange, pending NPC decision, engaged player. Advances when: repetition, no new information, goal resolved, environmental event due, meaningful pause.

## 8. Four-Option UI Contract
≤4 contextual suggestions, each {label, intent, category, legal, visible_basis}. Steward verifies: meaningfully different, legal, based on visible info, spoiler-safe, never framed as the only possibilities. UI may hide buttons when open conversation fits better. `custom_action_allowed: true` always.

## 9. Dice Integrity
Dice come from the deterministic dice service (seeded from campaign seed + turn ledger). A model may request a roll; it may never fabricate one. Steward verifies: roll occurred, correct formula, modifiers match sheet, adv/dis applied, result unchanged, narration matches. Discrepancy ⇒ `commit_allowed: false`.

## 10. State Mutation Contract
RFC6902 patches with provenance {source_event, source_rule, source_controller, validation_id, previous/new value}. No write without Steward approval. (Rides the Phase One envelope + ledger.)

## 11. Lookup Policy
Precedence: 1 Runtime → 2 Character Sheet → 3 campaign registry → 4 Genesis data files → 5 validated provisional ruling → 6 model general knowledge. Model knowledge never overrides a higher source. Unresolvable ⇒ `lookup_status: unresolved`, no confident invention, commit blocked if material.

## 12. Failure Handling
Invalid GM output (leaks, chooses for player, invents facts) ⇒ `repair_required: game_master`. Invalid CM output (fabricated roll, wrong economy) ⇒ `repair_required: combat_master`. Record Keeper unapproved write ⇒ `blocked`. Missing reference ⇒ `blocked: lookup`.

## 13. Model Deployment
| Controller | Model | Temp |
|---|---|---:|
| Game Master | qwen2.5:32b (creative/contextual) | 0.75 |
| Combat Master | qwen2.5-coder:32b (deterministic reasoning) | 0.15 |
| Record Keeper | deterministic code (schema-focused model optional later) | — |
| Genesis Steward | deterministic code (validation model optional later) | — |
Isolated contexts: the Steward never sees the GM's creative prompt; the CM receives only the narrative context needed; the RK has no permission to improvise.

## 14. Phasing
- **P1 (MVI):** shared runtime, four controllers, dice service, validated patch bus, routing. ✅ this build
- **P2:** mount skills (Lookup, Rules Lawyer, Runtime Steward, Record Keeper, World Turn Director, Character Keeper, Encounter Director).
- **P3:** four-option validation, pacing state, NPC memory boundaries, hidden GM state, snapshots, replay, continuity audits.
- **P4 (prove need first):** Quartermaster, Progression Steward, Faction Director, Nemesis Director, Relationship Director, Crafting Director, Lorekeeper.

## 15. Acceptance Criteria
**Narrative:** dialogue sustains without forced combat; scenes stop at meaningful decisions; player can act outside the four options; NPCs consistent with state.
**Combat:** dice external + preserved; initiative/economy correct; damage matches mechanics; outcomes returned without narrative contamination.
**Persistence:** every change has a validated patch; sheets auto-update; chronicle separates fact/belief/rumor; NPC knowledge bounded; saves replayable.
**Oversight:** invalid outputs rejected pre-commit; missing lookups block rulings; hidden info doesn't leak; no authority violations; every fact's origin explainable.
**Player experience:** *I can attempt anything plausible. The game answers honestly. The world reacts. The world remembers.*

---

# 17. Conversational Action Economy (Addendum, v1.1)
**Core rule: dialogue is not a separate mode that suspends gameplay.** Conversation happens inside the same actionable scene as movement, combat, powers, items, reactions, and environmental interaction. While an NPC is speaking the player can punch them, draw a weapon, use a Force power, move, interrupt, signal an ally, inspect something, leave, lie, grab an object, or attempt any plausible action. **The system never traps the player in a dialogue cutscene.**

## 17.1 Scene state, not locked mode
```yaml
scene_state:
  mode: dialogue
  action_lock: false
  player_interrupts_allowed: true
  physical_actions_allowed: true
  powers_allowed: true
  movement_allowed: true
  custom_action_allowed: true
```

## 17.2 Interrupt flow
```
Player interrupts dialogue
  → Steward identifies a mechanical action
  → GM freezes the scene at the EXACT interruption point
  → Combat Master resolves surprise, initiative, attack, reaction, damage
  → Steward validates
  → Record Keeper commits
  → GM resumes narration from the validated outcome
```
**Freeze correctly.** Bad: "The officer finishes his speech, storms away, and you decide to punch him." Good: "The officer reaches the words 'You will obey—' Aero's fist moves." Then mechanics. The NPC does not finish the sentence because the GM had already drafted it.

## 17.3 Interrupt classification (Steward)
`social_interruption | contested_action | isolated_attack | full_combat_transition | immediate_incapacitation | environmental_action`
Cutting someone off verbally stays in dialogue; a table slam is narrative unless intimidation is contested; grabbing a wrist is a contested check; a punch is attack resolution; a Force choke is power resolution and possibly combat; a ceiling shot is attack/environmental without necessarily rolling initiative; attacking a guarded commander likely transitions to combat. **The CM determines mechanics; the Steward determines whether combat mode is warranted after the action resolves.**

## 17.4 Surprise and readiness
Conversation does not make targets helpless. Resolution weighs: hostility expectation, drawn weapons, distance, LOS, awareness, body language, tension, reactions, abilities. No automatic hit because it was dramatic; no automatic denial because "you're in dialogue."

## 17.5 Dialogue scenes keep a spatial runtime
Positions, interactables, exits, weapons, gestures, hazards, allies, guards, active powers, tension — tracked while people talk, or a sudden action cannot be fairly resolved.

## 17.6 Options never block actions
Four suggestions render; the player can still type "I punch him." Suggestions, not rails.

## 17.7 Pacing — beats with interruption windows
```yaml
dialogue_beat:
  speaker:
  spoken_text:
  physical_behavior:
  environmental_change:
  interruption_window: open
```
Long speeches divide into beats wherever interruption would matter; pause after meaningful statements.

## 17.8 Acceptance criteria (addendum)
- player_can_interrupt_before_npc_finishes (beats + open interruption windows make this real)
- player_can_move_during_dialogue
- player_can_use_items_or_powers_during_dialogue
- hostile_actions_route_to_mechanical_resolution
- dialogue_options_do_not_limit_free_action
- scene_positions_remain_valid_during_conversation
- gm_never_completes_a_preplanned_speech_after_a_valid_interruption — *situational conviction exception:* an NPC with strong conviction may press on through a SOCIAL interruption (Steward-metered), never through a resolved physical one
- combat_begins_only_when_the_situation_requires_it — a cantina punch can be a brawl, not a massacre; when stakes turn lethal the GM may present a **reaction window** (quick-time prompt): *"You sense the attacker in the back has drawn his weapon. What do you do?"* `[Keep brawling] [Draw weapon]` + free text, optional timer. A UI variation, not the norm.
