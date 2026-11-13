#!/usr/bin/env python3
"""Adjudication repair (ruling 2026-11-13, creator/ACTION_ECONOMY_RULING.md), run against turn_contract.js.

Fixture: the public turn context of Hask Meadow evt_1385 (round 9, object interaction already spent, left hand
on the blaster in Wick's hand, right hand on the unlit hilt), republished with the repaired object fields.
Covers: release/contact vs possession, actor-specific interactions, ordered declarations, NPC cooperation,
and that a real second interaction still costs the action. Run: python3 -I test_action_economy.py
"""
import json, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
JS = HERE / "turn_contract.js"
CTX = HERE / "fixtures" / "handoff_round9.json"
SPEECH = {"approach": "assertive", "extended": False, "option": "d1", "text": "Lantern to me. Both hands on the grip."}


def validate(steps, ctx=CTX):
    decl = {"actor": "aero", "source": "composer", "freeform": "", "unmapped": [], "steps": steps}
    p = subprocess.run(["node", str(JS), "validate", "-", str(ctx)], input=json.dumps(decl), capture_output=True, text=True)
    assert p.returncode in (0, 3), p.stderr
    return json.loads(p.stdout)["validation"]


def obj(i): return {"type": "object", "option": i}
SAY = {"type": "speech", "option": "d1", "text": SPEECH["text"]}
codes = lambda v, k="errors": [e["code"] for e in v[k]]


def test_release_is_not_an_object_interaction():
    v = validate([obj("release_blaster")])
    assert v["legal"] and v["used"]["action"] == 0 and v["used"]["object_interaction"] == 0, v["used"]
    assert "(no action)" in v["preview"][0]["text"], v["preview"]


def test_handoff_in_order_costs_aero_nothing():
    v = validate([obj("release_blaster"), SAY, obj("wick_gives_lantern"), obj("wick_two_hands")])
    assert v["legal"], v["errors"]
    assert v["used"] == {"action": 0, "bonus_action": 0, "movement_ft": 0, "object_interaction": 0, "reaction": 0}, v["used"]
    assert "NPC_COOPERATION" in codes(v, "info")
    assert sum("theirs to do" in p["text"] for p in v["preview"]) == 2, v["preview"]


def test_order_matters_receiving_needs_the_hand_free_first():
    v = validate([SAY, obj("wick_gives_lantern"), obj("release_blaster")])
    assert not v["legal"] and "HANDS" in codes(v), v["errors"]


def test_no_two_free_hands_requirement_for_a_one_handed_item():
    v = validate([obj("release_blaster"), obj("wick_gives_lantern")])
    assert v["legal"], v["errors"]   # right hand still holds the hilt


def test_taking_it_yourself_is_possession_and_costs():
    v = validate([obj("release_blaster"), obj("take_lantern")])
    assert v["legal"] and v["used"]["action"] == 1, v["used"]   # interaction already spent this turn
    assert "(uses your action)" in v["preview"][1]["text"], v["preview"]


def test_stowing_still_costs_when_the_interaction_is_spent():
    v = validate([obj("clip_hilt")])
    assert v["used"]["action"] == 1 and "(uses your action)" in v["preview"][0]["text"], v


def test_first_real_interaction_is_free_with_budget():
    ctx = json.loads(CTX.read_text()); ctx["budget"]["object_interaction"] = 1
    tmp = HERE / "fixtures" / ".handoff_budget1.json"; tmp.write_text(json.dumps(ctx))
    try:
        v = validate([obj("release_blaster"), obj("take_lantern"), obj("clip_hilt")], tmp)
        assert v["used"]["object_interaction"] == 1 and v["used"]["action"] == 1, v["used"]
        texts = [p["text"] for p in v["preview"]]
        assert "(no action)" in texts[0] and "(free object interaction)" in texts[1] and "(uses your action)" in texts[2], texts
    finally:
        tmp.unlink()


def test_old_contexts_are_unchanged():
    ctx = json.loads(CTX.read_text())
    for o in ctx["objects"]:
        o.pop("cost", None); o.pop("by", None)
    tmp = HERE / "fixtures" / ".handoff_legacy.json"; tmp.write_text(json.dumps(ctx))
    try:
        v = validate([obj("release_blaster")], tmp)
        assert v["used"]["action"] == 1, v["used"]   # unflagged objects keep the old accounting
    finally:
        tmp.unlink()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok action economy tests")
