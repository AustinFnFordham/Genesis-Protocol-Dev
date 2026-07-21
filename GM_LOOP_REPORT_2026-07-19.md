# THE FOUR-CONTROLLER AI GM — Build Report (2026-07-19)

The game is no longer scripted. **GENESIS_GM_ARCHITECTURE.md** (your four-controller spec + the Conversational Action Economy addendum, canonicalized at the repo root) is implemented and running.

## What shipped

### The spec, canonized
`E:\StarWars\GENESIS_GM_ARCHITECTURE.md` v1.1 — your full draft with §17 Conversational Action Economy merged in, including the conviction exception (an NPC may press through a *social* interruption, never a resolved physical one) and the reaction-window quick-time variation.

### The four controllers (`api_bridge/gm_controllers.py` + `/api/v1/gm/*`)
| Controller | Implementation | Notes |
|---|---|---|
| **Game Master** | qwen2.5:32b, temp 0.75, isolated creative prompt | Dialogue **beats** with `interruption_window`, ≤4 suggested actions with `visible_basis`, `custom_action_allowed` hard-true. Never sees a die, an HP value it can change, or a hidden fact — only Steward directives. |
| **Combat Master** | qwen2.5-coder:32b, temp 0.15, **two-phase** | Phase 1 adjudicates from the character sheet's `exact_effect` mechanics and declares `required_rolls`; the dice service rolls; Phase 2 resolves using those exact results by `roll_id`. Cannot narrate, cannot touch hidden state. |
| **Record Keeper** | deterministic code | Applies Steward-approved patches only; appends `chronicle.jsonl` (fact-classed), NPC memory ledgers, runtime versioning, `turn_log.jsonl` provenance. |
| **Genesis Steward** | deterministic code | Routing, §17.3 interrupt classification, GM/CM output validation, hidden-leak screening, dice verification, authority-scoped patch approval, one repair cycle then block. **The law does not hallucinate.** |

### Dice integrity (§9)
Seeded service (`campaign seed ^ turn number`), formula parser with advantage/disadvantage, full roll log. The Steward rejects any resolution referencing a roll_id the service didn't produce or a total that changed. Fabricated dice = blocked commit.

### The runtime, seeded from your files
`api_bridge/gm/aero_character_runtime.yml` (player_and_gm) + `aero_hidden_gm_ledger.yml` (**gm_only — stripped from every player-visible endpoint and every GM prompt**). The shared runtime carries the full §5 contract including the §17.5 spatial dialogue scene (positions, interactables, exits) and `scene_state` with `action_lock: false`. Opening scope: Aero, newly knighted, escorting six engineers to the frontier sensor array, High Republic, two weeks before the Harvest Festival.

### Revelation: THE LIVING TABLE
New engagement tab beside NARRATIVE and TACTICAL. Beats render with speaker + "▸ interruptible" markers; mechanics arrive as an amber Combat Master card showing the actual dice (`1d20+5 → [8] = 13`); suggestions are chips, **never rails** — the free-action line ("attempt anything plausible…") is always live. Component submits declarations only; it mutates nothing.

## Verified live
1. **Narrative turn:** "ask Nona what she isn't telling me" → Nona in-character (warm, assessing), Dax gossips in from the cockpit door, 3 legal suggestions grounded in visible info, zero violations, **no leakage of Cardo Vel / Stillwater / the Council division** — the hidden ledger held.
2. **The Vader test:** "Before Dax finishes his sentence I punch him in the face" → Steward: `isolated_attack` → CM adjudicated from Aero's real sheet (*Martial Arts Training*, *Unarmed Strike*, +5), judged Dax **aware** (no drama-advantage, §17.4) → dice service: nat 8 → 13 → **miss** → GM narrated from the freeze point: Dax ducks, sentence unfinished → **no combat initiated** (`escalation: none` — §17.8: combat only when the situation requires it). Chronicle committed with roll provenance.
3. **In the shell:** full turn through the actual UI, ~10s for narrative turns; audit clean.

## Known refinements (logged, not blocking)
- Classifier misses some power phrasings ("use my Force Connection" → narrative, not power_use) — Steward regex set will grow, or Phase 2 mounts a low-temp classifier model.
- GM sometimes emits `speaker: "npc_id|nona"` literally — client strips it; prompt tightening later.
- NPC combat profiles are thin (role-only); real adversary sheets come from the content pipeline.
- Reaction-window quick-time UI (§17.8) not yet rendered — server contract supports it via `escalation_recommended: brawl`.

## Where this leaves the stack
Two AI runtimes now coexist and neither can lie: the **content pipeline** (creator → repair → zero-violation gate) makes things exist; the **four controllers** (GM → CM → Steward → RK) make things happen. Both propose; deterministic law disposes. Next: mount Phase 2 skills (Lookup against the gold registry, Rules Lawyer), grow adversary sheets, bridge the Living Table's combat escalation onto the Diorama holotable, and the reaction-window UI.
