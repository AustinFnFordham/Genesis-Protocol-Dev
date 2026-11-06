#!/usr/bin/env python3
"""Acceptance tests A, B, C, D, J for the composite-turn contract (turn_contract.js), run under node.

The same JS file is inlined into the Datapad, so these tests cover the client preview and the GM
processor's preflight at once. Run: python3 -I test_turn_contract.py
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JS = HERE / "turn_contract.js"
COMBAT = HERE / "fixtures" / "hask_round1.json"
SCENE = HERE / "fixtures" / "hask_wick_scene.json"
HIDDEN_WORDS = ("hit points", " hp", "armor class", " ac ", " dc ", "dc 1", "biscuit", "shard", "silo three")


def run(*args, stdin=None):
    p = subprocess.run(["node", str(JS), *args], input=stdin, capture_output=True, text=True)
    if p.returncode not in (0, 3):
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


def validate(decl, ctx=COMBAT):
    return run("validate", "-", str(ctx), stdin=json.dumps(decl))


def decl(**kw):
    d = {"actor": "aero", "source": "composer", "freeform": "", "speech": None, "actions": [], "bonus_actions": [],
         "movement": None, "objects": [], "reactions": [], "unmapped": []}
    d.update(kw)
    return d


def no_hidden(text):
    t = " " + text.lower() + " "
    leaked = [w for w in HIDDEN_WORDS if w in t]
    assert not leaked, f"hidden info leaked: {leaked}: {text}"


def test_A_legal_composite_turn():
    r = validate(decl(speech={"option": "d1", "text": "Wick! Get back to the shuttle!", "approach": "assertive", "extended": False},
                      objects=["ignite_saber"], actions=[{"option": "burst", "target": None, "trigger": None}],
                      movement={"option": "shift"}))
    v = r["validation"]
    assert v["legal"] and not v["warnings"], v
    assert [p["step"] for p in v["preview"]] == ["speech", "object", "action", "movement"], v["preview"]
    assert any("would reach: Dog A (left) and Dog B (right)" in i["message"] for i in v["info"]), v["info"]


def test_B_illegal_composite_turn_flagged_before_rolling():
    text = "I ignite my lightsaber, use Burst, ready a strike against the first dog that lunges, and retreat toward the ramp."
    r = run("parse", text, str(COMBAT))
    v = r["validation"]
    assert not v["legal"]
    assert v["errors"][0]["code"] == "ACTION_CONFLICT"
    assert "both require your primary action" in r["summary"]
    assert "prone does not automatically prevent an opportunity attack" in r["summary"]
    labels = [a["label"] for a in v["alternatives"]]
    assert any("Burst" in l and "ramp" in l for l in labels) and any("Ready" in l and "ramp" in l for l in labels), labels
    for a in v["alternatives"]:  # every offered alternative is itself legal
        assert validate(a["declaration"])["validation"]["legal"]
    no_hidden(r["summary"])


def test_C_opportunity_attack_warning_without_hidden_info():
    v = validate(decl(objects=["ignite_saber"], actions=[{"option": "burst", "target": None, "trigger": None}],
                      movement={"option": "to_ramp"}))["validation"]
    assert v["legal"] and v["needs_confirmation"], v
    oa = [w for w in v["warnings"] if w["code"] == "OPPORTUNITY_ATTACK"]
    assert oa and "Dog A" in oa[0]["message"] and "Dog B" in oa[0]["message"]
    no_hidden(json.dumps(v))
    # Disengage suppresses the warning
    v2 = validate(decl(actions=[{"option": "disengage", "target": None, "trigger": None}], movement={"option": "to_ramp"}))["validation"]
    assert not [w for w in v2["warnings"] if w["code"] == "OPPORTUNITY_ATTACK"]


def test_D_contextual_dialogue_records_speech_only():
    v = validate(decl(speech={"option": "d2", "text": "When did the dogs start copying human voices?", "approach": "investigative", "extended": False}), SCENE)["validation"]
    assert v["legal"] and v["preview"][0]["step"] == "speech"
    assert v["used"]["action"] == 0, "ordinary speech must not consume the action"
    blob = json.dumps(v).lower()
    assert "moral" not in blob and "alignment" not in blob and "personality" not in blob


def test_J_viewing_another_member_grants_no_control():
    v = validate(decl(actor="varon", actions=[{"option": "dodge", "target": None, "trigger": None}]))["validation"]
    assert not v["legal"] and v["errors"][0]["code"] == "ACTOR"


def test_requirements_range_and_reaction_sharing():
    v = validate(decl(actions=[{"option": "saber_attack", "target": "dog_b", "trigger": None}]))["validation"]
    assert any(e["code"] == "REQUIRES" for e in v["errors"])  # saber not ignited
    v = validate(decl(objects=["ignite_saber"], actions=[{"option": "saber_attack", "target": "dog_c", "trigger": None}]))["validation"]
    assert any(e["code"] == "RANGE" for e in v["errors"])
    v = validate(decl(objects=["ignite_saber"], actions=[{"option": "ready_saber", "target": None, "trigger": "when a dog lunges"}], reactions=["sentinel_balance"]))["validation"]
    assert v["legal"] and any(w["code"] == "REACTION_SHARED" for w in v["warnings"])


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("ok", name)
            except Exception as e:  # noqa: BLE001
                fails += 1; print("FAIL", name, e)
    sys.exit(1 if fails else 0)
