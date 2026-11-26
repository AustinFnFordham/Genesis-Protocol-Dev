# Genesis skill-mastery substrate (CC-007 §4–§6) — SANDBOX, NONCANONICAL

This is a reusable, deterministic progression ledger. Nothing here writes to any character sheet or campaign file, and nothing is live.

| File | What it is |
|---|---|
| `mastery.js` | The substrate (`genesis-mastery/0.1`): curves, capability, XP gate, two-phase awards, recovery, replay, milestones |
| `adapters.js` | Authority-side adapters: verified combat turns → events; exploration uses validated against scene data; session limit overlay |
| `skills/telekinetic_control.v0.1.json` | The Telekinetic Control prototype (owner numbers, for simulation) |
| `skills/grappling.scaffold.v0.1.json` | The Grapple scaffold: families and dependencies only, no grants |
| `fixtures/scene_objects.json` | A synthetic exploration scene |
| `test_progression.cjs` | 50 checks; part of `run_all_checks.sh` |
| `sim_telekinesis.cjs` → `sim_telekinesis_results.json` | Pacing, farming and environment study |
| `TELEKINETIC_CONTROL_PROGRESSION.md` | The level 0–20 proposal, plus findings and decisions |
| `GRAPPLE_PROGRESSION_SCAFFOLD.md` | The Grapple design scaffold |

## Guarantees (each one tested)

- **XP comes only from validated, committed events.**
  - Allowed authorities: `atomic` (server-verified combat turn) and `atomic_exploration` (a use validated against scene object data).
  - Refused: narration, client assertions, and uncommitted, unvalidated or refused steps.
  - Combat events are refused until the server has verified the turn (`TURN_NOT_VERIFIED`).
- **No double awards.** Each (character, skill, event) pair gets **one receipt**. The receipt id is a deterministic SHA-256 hash, and every receipt is hash-sealed. Replaying a log that contains duplicates awards nothing extra.
- **Two-phase transactions.** `begin` writes `pending`, and `commit` applies it. `recover()` completes an interrupted award exactly once, and a stale pending copy is discarded.
- **Versioned curves** (`quadratic/1` with parameters in the skill definition) and **per-level improvements**, with **provenance on every number**.
- **Milestones grant nothing by themselves.**
  - They are **eligibility** checks: level, required skills and required features.
  - A grant needs a recorded approval (who approved it, which event, and the source) and is stored as `sandbox_proposal`.
  - Each milestone lists what it `never_grants`: Force Pull, Force Push, creature manipulation, damage.
- **Independent of class level.** Mastery state is per character and per skill.
- **Combat limits are a session overlay.** A session can use mastery limits only through `newState({tk_limits})` (`s.tk_limits`, labelled). Without it, the Jedi Fundamentals limits apply unchanged.
