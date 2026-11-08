#!/usr/bin/env python3
"""Regression cases for scene-mode sequencing, conditions and physical feasibility (turn-contract/2).

Owner request 2026-11-08: tell physical impossibility apart from legitimate sequential narrative
actions, never let the GM decide a conditional for the player, keep combat economy intact.
Fixtures are NON-canonical copies of a player-visible turn context (fixtures/hask_r2_barn_*.json).
Run: python3 -I test_scene_sequencing.py
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JS = HERE / "turn_contract.js"
SCENE = HERE / "fixtures" / "hask_r2_barn_scene.json"
COMBAT = HERE / "fixtures" / "hask_r2_barn_combat.json"
OLD_SCENE = HERE / "fixtures" / "hask_wick_scene.json"


def run(*args, stdin=None):
    p = subprocess.run(["node", str(JS), *args], input=stdin, capture_output=True, text=True)
    if p.returncode not in (0, 3):
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


def validate(decl, ctx=SCENE):
    return run("validate", "-", str(ctx), stdin=json.dumps(decl))["validation"]


def parse(text, ctx=SCENE):
    return run("parse", text, str(ctx))


def decl(steps=None, **kw):
    d = {"actor": "aero", "source": "composer", "freeform": "", "speech": None, "actions": [], "bonus_actions": [],
         "movement": None, "objects": [], "reactions": [], "unmapped": []}
    if steps is not None:
        d["steps"] = steps
    d.update(kw)
    return d


def codes(v, kind="errors"):
    return [x["code"] for x in v[kind]]


def S(t, option=None, **kw):
    s = {"type": t}
    if option:
        s["option"] = option
    s.update(kw)
    return s


# 1. Asking Wick a question and inspecting the barn afterwards: two steps, in order, legal in a scene.
def test_01_question_then_inspect():
    v = validate(decl([S("speech", text="Who chained this barn?"), S("action", "ask_wick"), S("action", "search_dark")]))
    assert v["legal"], v["errors"]
    assert [p["step"] for p in v["preview"]] == ["speech", "action", "action"], v["preview"]
    assert "SEQUENCE" in codes(v, "info") and not v["halts"]
    r = parse('"Who chained this barn?" Ask Wick, then search around by eye again.')
    assert [s["type"] for s in r["declaration"]["steps"]] == ["speech", "action", "action"], r["declaration"]["steps"]
    assert r["validation"]["legal"]


# 2. A question whose answer decides whether Aero cuts the chain: the cut is conditional and is a halt point.
def test_02_conditional_cut_is_not_dropped():
    r = parse('"Why did they weld it shut?" If it was to keep something out, cut the chain with the lightsaber.')
    steps = r["declaration"]["steps"]
    cut = [s for s in steps if s.get("option") == "cut_chain"]
    assert cut and cut[0].get("condition"), steps
    v = r["validation"]
    assert v["legal"] and v["halts"] == [steps.index(cut[0])], v
    assert "CONDITIONAL" in codes(v, "info")
    assert v["preview"][1]["text"].startswith("Only if"), v["preview"]
    # a condition the parser cannot attach to a listed step is kept and flagged, never dropped
    r2 = parse("If the reason was to keep something in, I don't want to cut it.")
    assert r2["declaration"]["unmapped"] and "CONDITIONAL" in codes(r2["validation"], "info"), r2


# 3. Carrying three objects while both hands are occupied: refused, and told why.
def test_03_three_objects_hands_full():
    steps = [S("move", "to_silo_door"), S("object", "take_torch"), S("object", "take_bottle_a"), S("object", "take_bottle_b")]
    v = validate(decl(steps))
    assert not v["legal"] and "HANDS" in codes(v)
    e = [x for x in v["errors"] if x["code"] == "HANDS"][0]
    assert e["step"] == 1 and "right hand holds the lit lightsaber" in e["message"], e
    # freeing the left hand lets the torch be taken; the bottles still do not fit: a carry choice, not a free pass
    v2 = validate(decl([S("object", "holster_blaster")] + steps))
    h = [x for x in v2["errors"] if x["code"] == "HANDS"]
    assert not v2["legal"] and h and h[0]["step"] == 3 and h[0]["resolution"] == "needs_choice", v2["errors"]
    # turning the blade off is not a free hand: the hilt is still held
    v3 = validate(decl([S("object", "deactivate_saber"), S("object", "holster_blaster")] + steps))
    assert [x["step"] for x in v3["errors"] if x["code"] == "HANDS"] == [4, 5], v3["errors"]
    assert "left hand holds the welding torch" in [x for x in v3["errors"] if x["code"] == "HANDS"][0]["message"]


# 4. Holstering the blaster before manipulating an object: legal, and in the player's order.
def test_04_holster_then_take():
    v = validate(decl([S("object", "holster_blaster"), S("move", "to_silo_door"), S("object", "take_torch")]))
    assert v["legal"], v["errors"]
    assert [p["step"] for p in v["preview"]] == ["object", "movement", "object"]
    assert "(uses your action)" not in json.dumps(v["preview"]) and "free object interaction" not in json.dumps(v["preview"])
    # without the holster step it is a missing step, with the fix offered
    v2 = validate(decl([S("move", "to_silo_door"), S("object", "take_torch")]))
    e = [x for x in v2["errors"] if x["code"] == "HANDS"][0]
    assert e["resolution"] == "add_step" and e["suggest"] == ["holster_blaster"], e
    # legacy (contract-1) slots: the move toward the cart now comes before looking it over
    v3 = validate(decl(objects=["holster_blaster"], actions=[{"option": "search_cart", "target": None, "trigger": None}], movement={"option": "to_silo_door"}))
    assert [p["step"] for p in v3["preview"]] == ["object", "movement", "action"], v3["preview"]
    # and acting at the cart from the barn door is a missing move, not an impossibility
    v4 = validate(decl([S("object", "holster_blaster"), S("object", "take_torch")]))
    p = [x for x in v4["errors"] if x["code"] == "POSITION"][0]
    assert p["resolution"] == "add_step" and "to_silo_door" in p["suggest"], p


# 5. An unavailable Force power: refused structurally, flagged for the GM in free text.
def test_05_unavailable_power():
    v = validate(decl([S("action", "force_push")]))
    assert not v["legal"] and "UNKNOWN_OPTION" in codes(v)
    r = parse("I Force push the padlock off the chain.")
    assert "UNLISTED_POWER" in codes(r["validation"], "info") and r["declaration"]["unmapped"], r


# 6. Taking an item that is not established: never invented by the validator, flagged for the GM.
def test_06_unestablished_item():
    v = validate(decl([S("object", "take_crowbar")]))
    assert not v["legal"] and "UNKNOWN_OBJECT" in codes(v)
    r = parse("I grab the crowbar from the shed wall.")
    assert "UNLISTED_ITEM" in codes(r["validation"], "info") and r["declaration"]["unmapped"], r


# 7. Moving farther than combat movement in an uninterrupted scene: legal; two moves are both kept.
def test_07_long_scene_move():
    v = validate(decl([S("move", "toward_trees")]))
    assert v["legal"] and v["used"]["movement_ft"] == 1700
    r = parse("Go to the other barn, then back to silo three.")
    assert [s.get("option") for s in r["declaration"]["steps"]] == ["to_other_barn", "to_silo_door"], r["declaration"]["steps"]
    assert "MOVE_SEQUENCE" in codes(r["validation"], "info")


# 8. An unexpected threat interrupts a declared sequence: steps after the halt come back pending.
def test_08_interrupt_returns_pending():
    d = decl([S("speech", text="Stay close."), S("move", "to_silo_door"), S("object", "holster_blaster"), S("object", "take_torch")])
    h = run("halt", "-", str(SCENE), "2", "something moves at the edge of the light", stdin=json.dumps(d))
    assert [s["type"] for s in h["resolved"]] == ["speech", "move"]
    assert [s["option"] for s in h["pending"]] == ["holster_blaster", "take_torch"] and all(s["pending"] for s in h["pending"])


# 9. Crossing into initiative: the remainder is re-checked under combat economy.
def test_09_into_combat():
    d = decl([S("action", "ask_wick"), S("action", "search_dark"), S("move", "toward_trees")])
    assert validate(d)["legal"]
    v = validate(d, COMBAT)
    assert not v["legal"] and {"ACTION_CONFLICT", "DISTANCE"} <= set(codes(v)), v["errors"]
    # combat still counts a second object interaction against the action
    v2 = validate(decl([S("object", "holster_blaster"), S("object", "deactivate_saber"), S("action", "search_dark")]), COMBAT)
    assert "ACTION_CONFLICT" in codes(v2)


# 10. Remaining steps run only after the player authorizes them again.
def test_10_pending_needs_authorization():
    d = decl([S("speech", text="Stay close."), S("move", "to_silo_door"), S("object", "holster_blaster"), S("object", "take_torch")])
    pend = run("halt", "-", str(SCENE), "2", "condition unresolved", stdin=json.dumps(d))["pending"]
    v = validate(decl(pend))
    assert not v["legal"] and "PENDING_UNAUTHORIZED" in codes(v)
    for s in pend:
        s["authorized"] = True
    # authorized, but Aero is back at the barn door in this fixture: the cart is a missing move, still checked
    v2 = validate(decl(pend))
    assert codes(v2) == ["POSITION"], v2["errors"]
    v3 = validate(decl([S("move", "to_silo_door")] + pend))
    assert v3["legal"], v3["errors"]


def test_contract1_declarations_and_contexts_unchanged():
    # no hands published -> no hand checks (the GM judges), and old scene fixture still validates
    v = validate(decl(speech={"option": "d2", "text": "When did the dogs start copying human voices?", "approach": "investigative", "extended": False}), OLD_SCENE)
    assert v["legal"] and v["used"]["action"] == 0
    r = parse("Look at the tracks.", OLD_SCENE)
    assert r["validation"]["legal"]


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("ok", name)
            except Exception as e:  # noqa: BLE001
                fails += 1; print("FAIL", name, repr(e)[:600])
    sys.exit(1 if fails else 0)
