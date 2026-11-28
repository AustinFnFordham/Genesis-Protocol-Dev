# CC-009 — Hask Meadow Gameplay Recovery & Combat Turn Builder v2

Branch `dev/cc009-turn-builder-v2`, from `7375107`. **Noncanonical design + prototype.** Nothing here is live. Hask Meadow, Oracle, shared-1/shared-0002, canonical rules, SA-001 and progression content were not modified. All Hask evidence was read from the committed record (`runs/hask_meadow_r2`, ends `evt_1417`, round 11).

| File | Role |
|---|---|
| `turn_plan_v2.js` | v2 plan layer **over** `turn_contract.js` (no second validator) |
| `schema/turn_plan_v2.schema.json` | Structured turn-plan contract |
| `schema/encounter_state_v1.schema.json` | Minimum encounter state (existing vs gap fields) |
| `evidence/issues.json` | Bug-to-contract traceability matrix (machine-readable) |
| `evidence/hask_replay.json` | Every committed combat declaration replayed through today's contract |
| `replay_hask.cjs` | Read-only generator for the replay |
| `fixtures/hask_r2_round9_10.json` | Read-only copies of the round 9–10 contexts and declarations (source sha256 pinned) |
| `test_cc009.cjs` | 12-scenario acceptance matrix + fix F1 (in `run_all_checks.sh`) |

## 1. Verified implementation inventory

| Component | Where | What it already does |
|---|---|---|
| Live turn contract `turn-contract/3` | `ui/turn_contract.js` (inlined in the Datapad, run by the processor) | Ordered steps with ids/sequences, branches, conditions, halts, pending steps with statuses, hands per item, `cost:"none"` / `by:<npc>` objects, reaction prompts (`REACTION_ONLY/NOT_OFFERED/…`), `end_turn` + `TURN_CONTINUES`, availability per palette candidate |
| M11 intent-first builder | `ui/src/tb4.js`, `ui/src/composer.js` | ≤4 contextual editable plans from published options; picking edits the builder, never executes; collapsed full catalog; per-category Custom; null-aware budget badges |
| M12 cross-platform | `ui/src/head.html`, preview | Touch/focus/scroll/keyboard CSS, immediate drafts, browser-mode manifest, 18 responsive workflows (Chromium/WebKit/Windows) |
| Sequencer | composer + contract | Plan/scene sequencing, Continue with `authorized_ctx`, stale `PENDING_STALE` |
| Processor stale guard | `.claude/skills/litrpg-process-turn/turn.py check` | Refuses an action whose revision, ledger head or turn context moved on |
| Encounter controller | `ENCOUNTER_RULING.md` (2026-11-15, adopted live) | Initiative tracker derived from the ledger, per-actor budgets, core actions |
| Atomic combat slice CC-002–CC-007 | `development/combat_slice/` | Card builder, Main/Bonus/**Secondary (SA-001 switch)**/Reaction/move/OI, reaction windows, NPC policies through the same validator, receipted server dice, Roll Theater, viewer projections |
| Dice | dice skill + `roll_log` / Atomic receipts | Deterministic, receipted, redacted per viewer |

## 2. Hask Meadow issues and evidence

The full matrix is `evidence/issues.json`.

| # | Area | Status | Root cause | Key evidence | Now |
|---|---|---|---|---|---|
| H1 | Object interactions | verified | state sync + rule ambiguity | r7 `evt_1345`, r9 `evt_1386` (release billed) | Ruling 11-13 fixes it when the GM publishes `cost:"none"` (D4) |
| H2 | Wick / blaster / lantern | working | UI friction | `evt_1382` hands stop, pending s4/s5 | Correct; builder should offer the freeing edit |
| H3 | Hands and equipment | verified | state sync | Wick's hands, blaster and charge are prose only | Encounter-state gap |
| H4 | Budget contradictions | verified | UI + GM adjudication | No structured contradiction in 13 contexts; r10 custom step silently billed as the action, GM ruled it the OI (`evt_1402`) | **F1 fixed** (disclosure); default cost is D2 |
| H5 | Compound declarations | verified | client parsing | `evt_1375` ordered OK; r10 freeform appended after a plan left unmapped | v2 makes every activity explicit |
| H6 | Conditional / interrupted | working | — | pending statuses preserved | — |
| H7 | Submission = end of turn | verified | GM adjudication + state sync | **All 10 combat turns r1–r10 ended with resources unspent; today's contract continues every one** (`hask_replay.json`) | Fixed by the 11-15 ruling; not yet exercised live |
| H8 | NPC action / state | verified | rule ambiguity + state sync | Wick fires on Aero's turn with no initiative entry; charge untracked (`evt_1412`) | D1, D5 |
| H9 | Dice controls / low rolls | enhancement | UI | Live has no player roll control; 114 d20 mean 10.20, χ²(19)=12.0 — no RNG anomaly; Wick's miss was disadvantage at long range vs DC 15 | D3 |
| H10 | Pending / resolved visibility | suspected | UI | GM's re-costing of custom steps is GM-only | Surface adjudicated cost in `plan_progress` |

## 3. Proposed player workflow

The existing builder stays. v2 is its data model: every card, palette pick or custom box becomes one **activity** row.

```mermaid
flowchart TD
  A[Turn context published] --> B[Suggestions ≤4 (M11) or Build]
  B --> C[Activity rows: slot · capability or custom · target · speech · flair · if · after]
  C --> D{Validate live: turn_contract.validate via v2}
  D -- blocked --> E[Row shows why + one-tap fix: add the freeing step / move it / pick a hand]
  E --> C
  D -- legal --> F[Review: intention · authorization · cost shown per row]
  F --> G[Submit partial plan]
  G --> H[GM / Atomic resolve in order, roll, commit events]
  H --> I{Halt?}
  I -- condition, hands, NPC choice, combat --> J[Pending rows with status; turn continues]
  J --> C
  I -- no --> K{Budget left and no 'end my turn'?}
  K -- yes --> C
  K -- no --> L[Turn ends → next actor]
```

**Three layers per row** (never merged in the UI):
1. **Intention**: the player's words, kept literally (custom text, speech, flair).
2. **Authorization**: the validator's verdict (`known_legal`, `needs_adjudication`, `waits_on_condition`, `declared_intent`, `blocked`) with its reason and the cost it will bill.
3. **Outcome**: only from committed events and receipts; empty until then.

**Always available:** the Say / Describe row, whatever the budget (scenario 7). Its mechanical effect is never assumed: brief speech is free; an extended exchange takes the action; any effect on another character is adjudicated.

## 4. Structured action-plan contract

See `schema/turn_plan_v2.schema.json`. Each slot maps one-to-one onto the live step types, so no live rule changes:

| v2 slot | live step | Notes |
|---|---|---|
| `main` | `action` | |
| `bonus` | `bonus_action` | |
| `movement` | `move` | |
| `object` | `object` | costs from the context (`cost`, `by`) |
| `free` | `free` (custom) | the GM adjudicates; preview now states the billed cost (F1) |
| `speech` | `speech` | |
| `reaction` | `declaration.reactions` | an intent with a trigger, never a step |
| `secondary` | none | `SECONDARY_NOT_ENABLED` unless `ruleset.secondary_action === true` |

Plan-level gates added by v2: `STALE_PLAN` (context id), `PLAN_ACTOR`, `DEPENDENCY_ORDER` / `DEPENDENCY_UNKNOWN`, `EMPTY_ACTIVITY`, `TARGET_KIND`, `REACTION_NEEDS_TRIGGER`. A partial plan is always submittable when legal (`partial_ok`); only `end_turn` or an exhausted budget ends the turn. Editing (`add`/`remove`/`move`/`update`) is pure and revalidates.

### 4.3 Builder behaviour on a block

Show the contract's own `resolution` / `suggest_steps` as one-tap edits (e.g. H2: "Let go of the blaster first"). Never apply them automatically: the GM never adds a release or picks a hand (ruling §6).

## 5. Encounter state

See `schema/encounter_state_v1.schema.json`. It is a projection from committed events, per viewer. Existing fields come from turn-contract contexts and the Atomic state. The gaps evidenced at Hask Meadow are:
- allied NPCs missing from the initiative order;
- NPC hands, equipment and weapon charge;
- object durability and cover (hatch planks);
- hazards (embers);
- standing instructions.

## 6. UI / Atomic / GM responsibility boundaries

| Concern | UI (Datapad) | Client validation (`turn_contract.js`) | Atomic / processor | GM |
|---|---|---|---|---|
| Authoring, order, editing | ✔ | | | |
| Legality, costs, hands, budgets | shows | ✔ (same code runs server-side) | revalidates at execution | adjudicates custom/unmapped |
| Staleness | warns | `STALE_PLAN` | `turn.py check` (authoritative) | |
| Dice | displays receipts | never predicts | ✔ rolls, receipts | requests rolls, fixes tables first |
| NPC decisions | never | | NPC policy via same validator (sandbox) | ✔ (tables fixed before rolling) |
| Outcomes / ledger | never writes | | commits events | narrates committed events |
| WHISPER / post-combat | unchanged | | | its own contract |

## 7. Datapad on desktop, iPhone and iPad

These keep M12's CSS and the journal/history pagination. No past entry is re-rendered into a new model; v2 applies to new drafts only.
- **iPhone Safari:**
  - one column: Turn summary bar (budget chips: Action · Bonus · Move ft · Object · Reaction), then the activity list, then the sticky Submit;
  - target picking in a bottom sheet listing visible ids only;
  - the keyboard opens only for the custom/speech fields;
  - safe-area insets keep Submit clear of the home indicator;
  - rows reorder with up/down buttons (≥44 px), not drag.
- **iPad Safari + Magic Keyboard:**
  - two panes: the activity list beside the scene/journal;
  - `↑/↓` move focus between rows, `⌥↑/⌥↓` reorder, `Enter` edits, `⌘↩` submits, `Esc` closes a sheet;
  - focus never lands behind the keyboard (`scrollIntoView` on focus within the visual viewport).
- **Windows desktop:**
  - the same two panes;
  - the same shortcuts with `Ctrl`;
  - visible focus rings.

Pending, resolved and adjudicated items keep their existing status tags (completed, interrupted, unattempted…). An adjudicated cost shows on the resolved row.

## 8. Regression matrix (`test_cc009.cjs`)

| # | Scenario | Evidence | Result |
|---|---|---|---|
| 1 | OI spent; action and bonus remain | `evt_1385` | pass |
| 2 | Two-handed rake vs lantern + hilt | `evt_1400` | pass |
| 3 | Conditional pickup waits; reordering before its dependency is refused | r9 | pass |
| 4 | Compound declaration in order | `evt_1375` | pass |
| 5 | Interrupted work preserved and continuable | `evt_1385` | pass |
| 6 | Turn continues after a submission | `evt_1386` | pass |
| 7 | Free speech at zero budget; extended speech still costs | `evt_1400` (budgets zeroed) | pass |
| 8 | Reaction only on a legal trigger (contract + Atomic) | `hask_round1` | pass |
| 9 | NPC turn spends only the NPC's budget; receipts to the NPC | Atomic duelist | pass |
| 10 | Stale / invalid plan refused, ledgers unchanged (v2 + `turn.py check` on sandbox) | | pass |
| 11 | No Secondary in live Hask contexts; refused by v2; sandbox-only switch | | pass |
| 12 | WHISPER passed through; v2 has no outcome, ledger or dice paths | | pass |
| F1 | Custom-step cost disclosed in combat only | `evt_1401` | pass |

The suite also asserts that the Hask Meadow and sandbox ledgers, roll logs and dice state hash identically before and after the run.

## 9. Decision records (missing mechanics; no rule invented)

| # | Question | Evidence | Options |
|---|---|---|---|
| D1 | How does an allied NPC act in combat? | Wick fired on Aero's word during Aero's turn; no initiative entry | (a) allies get their own initiative and economy; (b) they act on the PC's turn via a PC action (Help/command); (c) current GM practice, recorded as a ruling |
| D2 | Default cost of a combat custom step | the validator bills the action; the GM ruled the OI (`evt_1402`) | keep "action until ruled" (now disclosed) / "no budget held, GM rules" / per-category default |
| D3 | Player-triggered dice in live | the Atomic Roll Theater exists; live is GM-rolled | keep GM-rolled / Roll Theater for the PC's own rolls only (receipts unchanged) |
| D4 | Release / receive without GM fields | ruling 11-13 needs `cost:"none"` published | keep GM-published / contract default for verbs "let go / drop / release" |
| D5 | Weapon charges and ammo in live | "remaining charge is not tracked" | track per item / ignore below N shots |
| D6 | Object durability and cover | hatch planks cut and burned; Wick's shot "total cover", DC 15 | needs SW5e object/cover source text (not in repo) |
| D7 | Auto end-of-turn when nothing is left to spend | current contract ends it | keep / always require "end my turn" so free speech can follow |
| D8 | Secondary Action (SA-001) | sandbox only | confirm it stays off in live |

## 10. Implemented isolated fix

**F1:** `turn_contract.js previewSteps`. A combat custom step now reads "Try: … (the GM rules its cost; it counts as your action until then)". That is the cost `validateLinear` already bills. No cost, legality or rule changed. `genesis_datapad.html` was rebuilt for build equality. It is **not published**.
