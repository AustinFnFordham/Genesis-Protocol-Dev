# Genesis progression (CC-007 mastery substrate + CC-008 unified framework) — SANDBOX, NONCANONICAL

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

## CC-008 unified framework

| File | Purpose |
|---|---|
| `CC008_SOURCE_RECONCILIATION.md` | Milestone A: what the sources say and where they conflict |
| `PROGRESSION_SCHEMA.md`, `schema/genesis_progression_tree.schema.json` | Milestone B: the schema and authoring specification |
| `framework.js` | Tracks, requirements, typed ledger, two-phase transactions, legacy adapter |
| `curves.js` | Curve evaluator and table generator |
| `validate.js`, `authoring.js`, `tools/validate_tree.cjs`, `AUTHORING.md` | Validator, authoring checks, the command-line entry point and its guide |
| `choices.js` | Milestone D: the three-choice selection contract |
| `disciplines.js`, `policies/discipline_allocation.v0.1.json` | Milestone E: shared Discipline XP |
| `fixtures/aero_vertical/` | Milestone F: the Aero Echani + Sentinel vertical slice (`evidence.json`) |
| `candidates/` | Candidate class-level curves and their pacing comparison (not adopted) |
| `XP_TABLES.md` | Level-by-level sample tables |
| `test_cc008.cjs` | Runs `test_cc008_{b..g}.cjs`; part of `run_all_checks.sh` |
