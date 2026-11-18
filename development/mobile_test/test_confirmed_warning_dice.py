"""Regression (2026-11-18, found by a real test-worker round trip): with the dice-settings resolver on, a legal turn whose
risk the player confirmed (moving out of a hound's reach) must still be able to roll — for the provoked opportunity
attack and for the creatures' own turns. Before the fix every roll was DICE_REFUSED."""
import sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "gm_provider"))
import test_mobile_env as M  # noqa: E402
import staging  # noqa: E402

M.subprocess.run([sys.executable, "-B", str(HERE / "build_fixture.py")], check=True, capture_output=True)
with tempfile.TemporaryDirectory(prefix="warn-", dir=M.QA) as d:
    gw, first = staging.make(d, campaign_id="mobile-test-1", experimental=True, source=M.FIXTURE)
    try:
        # Aero closes on the near hound (no roll needed for this check), so moving back out of reach provokes.
        action, run, ctx = M.submit(gw, text="I ignite my lightsaber and close on the near hound.")
        steps = {s["type"]: s["id"] for s in ctx["declaration"]["steps"]}
        gw.fix_tables(M.ME, run, {"interpretation": "Two steps.", "tables": "none", "npc_evaluations": []})
        events = [M.e("object_interaction", _actor="aero", step_id=steps["object"], option="ignite_saber"),
                  M.e("resource_spent", actor_id="aero", resource="object_interaction", **{"for": steps["object"]}),
                  M.e("movement", _actor="aero", step_id=steps["move"], option="to_near_hound"),
                  M.e("resource_spent", actor_id="aero", resource="movement_ft", amount=10, **{"for": steps["move"]})]
        ctx2 = M.next_context(gw, state_flags=["saber_ignited"], budget={"action": 1, "bonus_action": 1, "reaction": 1, "movement_ft": 20, "object_interaction": 0})
        ctx2["movement"] = [{"id": "hold", "label": "Hold position", "feet": 0}, {"id": "back_to_wick", "label": "Fall back to Wick", "feet": 20, "leaves_reach_of": ["hound_1"]}]
        assert gw.commit(M.ME, run, {"world_time": "Sim drill, round 1", "narration": "The blade hums. You are nose to nose with the near hound.",
                                     "scene_state": {"summary": "close", "title": "Sim", "location": "Sim", "atmosphere": ["test"]},
                                     "turn_context": ctx2, "events": events})["status"] == "committed"
        action, run, ctx = M.submit(gw, steps=[{"type": "move", "option": "back_to_wick", "id": "k0", "seq": 0}], extra={"confirmed_warnings": True})
        assert ctx["validation"]["needs_confirmation"], ctx["validation"]
        step = ctx["declaration"]["steps"][0]["id"]
        gw.fix_tables(M.ME, run, {"interpretation": "Leaving reach provokes.", "tables": "OA 1d20+3", "npc_evaluations": []})
        oa = gw.roll(M.ME, run, {"roll_key": "oa", "step_id": step, "subject": "hound_1", "formula": "1d20+3", "kind": "attack",
                                  "requested_by": "gm", "purpose": "The near hound snaps as Aero pulls away", "dc": 13, "rule_sources": ["SRD"]})
        assert oa["result"]["roll_id"], oa
        print("ok confirmed-warning turn can roll under the resolver")
    finally:
        gw.store.close()
