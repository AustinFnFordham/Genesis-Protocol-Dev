# Mobile test build (noncanonical) — 2026-11-15

| | |
|---|---|
| Test Datapad | https://claude.ai/artifact/CnRh7iAy75JNZePbPhUeqb ("Genesis Datapad Test Deck", private) |
| Deployed code | `integration/mobile-test-build` @ `b2d59bb` (page built from it, worker runbook in it) |
| Test campaign | `mobile-test-1` "Sim Deck: Drill Seven", branch `staging/mobile-test`, dir `staging/mobile-test-1/`, `canonical: false` |
| Worker | scheduled task `trig_01J5tRZ3t2WehBNzx3Z3Z2Wj` (poke-only, cloud, no schedule), runbook `development/mobile_test/WORKER.md` |
| Live, untouched | main Datapad `6QTsY4UwYyQFMQMgzydCre` view/state v87, `litrpg/campaign-scaffold` @ `ebda584`, live task `trig_011svPGdUcPjEghbaSmrNFKF` last run 2026-11-15 04:08 |

## Settings in this build (test only, not adopted into live)
Wick is an allied NPC, GM-run, own initiative and budget; Aero may ask, Wick decides; no extra actions.
Each sim hound has its own turn and budget; enemies share one count; the third hound is hidden (gm_only).
Regular/Heroic/Legendary and Narrative Consequences per submission, applied to the player party's own d20s only.
End-turn checkbox and GM end-turn options; partial turns stay open (`TURN_CONTINUES`).

## What ran
**Synthetic (no model, no network, no Artifact database):** `test_mobile_env.py` — partial turn, continuation ended by
word, Wick's own turn, per-creature hound turns and roll subjects (X1), NPC-turn provenance refusal (X2), hidden hound
stays hidden, Heroic only for Aero, GM end-turn option, no rerolls, replay ok. Full suite `run_all_checks.sh`: 44 suites, 0 failed
(includes history with many pages per kind).

**Real transport (2026-11-16 00:45–00:49 UTC):** an action row written to the test artifact's database (by the operator
session, standing in for the phone tap: the browser Submit itself was not exercised), `fire_trigger` on the test task,
a fresh cloud worker session followed WORKER.md: queued via bridge, claimed, fixed tables, 2 rolls through the gateway
(`roll_t1_1` Heroic raw 18 → 19 +5 = 24, 1 Advantage; `roll_t1_2` damage 5), committed `evt_0007`–`evt_0018`, published
revision 14, mirrored view pages then state to the artifact, row `committed`, usage records written (committed, then a
noop recheck). Tracker after: round 1, Aero still acting (movement 20 ft left), Wick next. Replay ok, ledger valid,
hidden hound absent from every public document.

## Not covered / limitations
- The phone's own Submit tap → `fire_trigger` path was not exercised in this session (needs the viewer's consent prompt on first use).
- Wick/hound turns have only run in the synthetic drill; the first real one happens when the player ends Aero's turn.
- The worker takes ~3 minutes per turn (cold cloud session + git pushes per step).

## Round 1 vs round 11
Live Hask Meadow is combat **round 11** at `evt_1417` (GM-published `turn_context.round` and 20 `combat_round` events,
last one round 11) — the earlier audit is right. A "round 1" reading comes from test data, not the live record: the
browser fixture `.qa/state_round1.json`, the sandbox, and this drill all start at round 1, and the new encounter
controller derives rounds only from its own events, which Hask Meadow does not have (it folds the live ledger as
"scene, round 0"). Neither record was changed.
