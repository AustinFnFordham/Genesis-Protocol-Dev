#!/usr/bin/env python3
"""Regression cases for the cinematic scene sequencer (turn-contract/3).

Owner request 2026-11-08: sequences as visual groups resolved in one GM pass, a visible palette whose
availability follows the planned order, multi-select and multiline dialogue, custom steps kept verbatim,
conditional branches that never treat missing information as a yes, interruptible plans with
partial-prefix commits, and a strict hidden-information boundary.
Scenarios: S1 = the owner's four-sequence plan, S2 = IF / ELSE IF / OTHERWISE at the chain,
S3 = the hidden Mastiff interruption. Fixtures are NON-canonical (fixtures/hask_r2_sequencer*.json).
Run: python3 -I test_sequencer.py
"""
import copy, json, re, subprocess, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
JS = HERE / "turn_contract.js"
CTX = HERE / "fixtures" / "hask_r2_sequencer.json"
GM = json.loads((HERE / "fixtures" / "hask_r2_sequencer_gm_only.json").read_text())
S1 = json.loads((HERE / "fixtures" / "s1_four_sequences.json").read_text())
S1_FIXED = json.loads((HERE / "fixtures" / "s1_four_sequences_fixed.json").read_text())
COMBAT = HERE / "fixtures" / "hask_r2_barn_combat.json"
OUTPUTS = []  # every validator output, screened for leaks and odds at the end


def node(*args, stdin=None, ok=(0, 3)):
    p = subprocess.run(["node", str(JS), *args], input=stdin, capture_output=True, text=True)
    if p.returncode not in ok:
        raise RuntimeError(p.stderr or p.stdout)
    OUTPUTS.append(p.stdout)
    return json.loads(p.stdout)


def validate(decl, ctx=CTX):
    return node("validate", "-", str(ctx), stdin=json.dumps(decl))["validation"]


def status(decl, ctx=CTX):
    r = node("status", "-", str(ctx), stdin=json.dumps(decl))
    return r["validation"], {k: v["status"] for k, v in r["status"].items()}, r["status"]


def avail(decl, where=None, ctx=CTX):
    args = ["availability", "-", str(ctx)] + ([json.dumps(where)] if where is not None else [])
    return {a["option"]: a for a in node(*args, stdin=json.dumps(decl))}


def progress(decl, outcome, ctx=CTX):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(outcome, f)
    return node("progress", "-", str(ctx), f.name, stdin=json.dumps(decl))


def plan(*steps):
    return {"actor": "aero", "source": "composer", "steps": [dict(s) for s in steps]}


def st(i, seq, t, **k):
    return dict(id=i, seq=seq, type=t, **k)


def codes(v, key="errors"):
    return [x["code"] for x in v[key]]


def err_at(v, sid, code=None):
    return [e for e in v["errors"] if e.get("step_id") == sid and (code is None or e["code"] == code)]


# ---------- S1: the owner's four-sequence plan ----------
def test_S1_four_sequences_planned_state_and_conflicts():
    v, s, full = status(S1)
    assert not v["legal"], v
    # the only blockers: open the door and draw the blaster with the saber in one hand and the cart in the other
    assert sorted((e["step_id"], e["code"]) for e in v["errors"]) == [("s11", "HANDS"), ("s12", "HANDS")], v["errors"]
    e = err_at(v, "s11", "HANDS")[0]
    assert e["resolution"] == "add_step" and e["suggest"] == ["release_cart"] and "left hand holds the handcart" in e["message"], e
    assert s["s5"] == "gm" and s["s10"] == "risky" and s["s11"] == "fix" and s["s1"] == "ok", s
    tr = {t["step_id"]: t for t in v["trace"]}
    assert tr["s1"]["hands"]["left"] is None and tr["s1"]["position"] == "at the shed door"          # planned: left hand free
    assert tr["s3"]["position"] == "at the welding cart"                                               # planned: at the cart
    assert tr["s6"]["hands"]["left"]["item"] == "handcart" and tr["s7"]["position"] == "at the shed door"
    assert "chain_cut" in tr["s10"]["flags"] and "chain_cut" not in tr["s9"]["flags"]                   # enabled by the cut, in order
    # the explicit fix (the player adds "Let go of the handcart") makes the whole plan legal; risks need no tick in a scene
    v2 = validate(S1_FIXED)
    assert v2["legal"] and not v2["needs_confirmation"], v2["errors"]
    assert [p["text"][:20] for p in v2["preview"]][:3] == ["Holster the blaster ", "Say: “Wick, what do ", "Over to the welding "]


def test_S1_draw_blaster_if_physically_possible_is_structural():
    v = validate(S1_FIXED)
    assert not err_at(v, "s12"), "after letting go of the cart the draw is possible"
    v2 = validate(S1)
    assert err_at(v2, "s12", "HANDS"), "with both hands full it is not"


# ---------- dialogue ----------
def test_multiple_selected_dialogue_lines_are_separate_ordered_steps():
    d = plan(st("x1", 0, "speech", option="d2"), st("x2", 0, "object", option="holster_blaster"), st("x3", 0, "speech", option="d1"))
    v = validate(d)
    assert v["legal"]
    assert [p["step"] for p in v["preview"]] == ["speech", "object", "speech"], v["preview"]
    assert "Warden" in v["preview"][0]["text"] and "Silo Three" in v["preview"][2]["text"]
    assert [s["id"] for s in v["steps"]] == ["x1", "x2", "x3"] and v["steps"][0]["approach"] == "assertive"


def test_multiline_custom_dialogue_is_kept_verbatim():
    text = "Wick, get the lantern ready.\nWhen the door opens, shine it inside, low and steady.\n\n  (quietly) Don't run."
    v = validate(plan(st("x1", 0, "speech", text=text)))
    assert v["legal"] and v["steps"][0]["text"] == text and text in v["preview"][0]["text"]


# ---------- custom actions ----------
def test_custom_action_kept_verbatim_and_marked_for_gm():
    text = "Load the torch and both gas bottles onto the handcart and strap them down"
    v, s, _ = status(plan(st("x1", 0, "move", option="to_cart"), st("x2", 0, "free", text=text, kind="custom")))
    assert v["legal"] and s["x2"] == "gm" and v["steps"][1]["text"] == text and ("Try: " + text) in v["preview"][1]["text"]


def test_custom_item_step_reports_hands_and_distance_without_refusing():
    full = plan(st("x1", 0, "free", text="Grab the gas bottles off the welding cart", kind="custom"))
    v, s, d = status(full)
    assert v["legal"], "the GM adjudicates custom steps; the builder never refuses them"
    w = {x["code"]: x for x in v["warnings"]}
    assert "GM_HANDS" in w and "GM_POSITION" in w and w["GM_POSITION"]["advisory"], v["warnings"]
    assert "35 ft" in w["GM_POSITION"]["message"] and s["x1"] == "gm"


# ---------- sequences: add and reorder ----------
def test_sequence_addition_and_reordering_across_sequences():
    d = copy.deepcopy(S1_FIXED)
    # moving "Over to the welding cart" (seq 0) after "Inspect" breaks the inspection: a missing move, with the fix
    steps = d["steps"]; mv = steps.pop(2); steps.insert(3, mv)
    v = validate(d)
    e = err_at(v, "s4", "POSITION")
    assert e and e[0]["resolution"] == "add_step" and "to_cart" in e[0]["suggest"], v["errors"]
    # moving the walk back (seq 1) into seq 3 makes the cut happen at the cart: a POSITION error at the cut
    d2 = copy.deepcopy(S1_FIXED); s2 = d2["steps"]; walk = next(x for x in s2 if x["id"] == "s7"); s2.remove(walk); walk["seq"] = 3; s2.append(walk)
    v2 = validate(d2)
    assert err_at(v2, "s10", "POSITION") and {x["seq"] for x in v2["steps"]} == {0, 1, 2, 3}
    # a new sequence: palette insertion lands at the end of the chosen sequence and keeps every id
    a = node("availability", "-", str(CTX), json.dumps({"seq": 4}), stdin=json.dumps(S1_FIXED))
    assert {x["option"]: x["status"] for x in a}["signal_wick"] == "ok"
    v3 = validate(plan(*S1_FIXED["steps"], st("n1", 4, "action", option="search_dark")))
    assert v3["legal"] and v3["steps"][-1]["seq"] == 4 and [x["id"] for x in v3["steps"]][:3] == ["s1", "s2", "s3"]


def test_insertion_respects_sequence_boundaries():
    a = avail(S1, {"seq": 1})  # end of sequence 2 (index 1): Aero is back at the shed door with the cart in hand
    assert a["inspect_cart"]["status"] == "needs_step" and a["inspect_cart"]["suggest"][0]["option"] == "to_cart"
    assert a["draw_blaster"]["status"] == "needs_step" and a["draw_blaster"]["suggest"][0]["option"] == "release_cart"
    assert a["release_cart"]["status"] == "ok" and a["push_cart"]["status"] == "not_here"   # already pushing it


# ---------- prerequisites (order-aware) ----------
def test_prerequisites_enable_later_steps_only_in_order():
    empty = plan()
    a = avail(empty)
    assert a["push_cart"]["status"] == "needs_step" and [x["option"] for x in a["push_cart"]["suggest"]] == ["to_cart", "holster_blaster"]
    assert a["open_door"]["status"] == "needs_step" and a["prepare_enter"]["status"] == "needs_step"
    assert a["draw_blaster"]["status"] == "not_here" and "already has" in a["draw_blaster"]["reasons"][0]
    assert a["release_cart"]["status"] == "not_here" and "does not have the handcart" in a["release_cart"]["reasons"][0]  # nothing to let go of
    assert a["cut_chain"]["status"] == "risky" and a["signal_wick"]["status"] == "ok"
    a2 = avail(plan(st("p1", 0, "object", option="holster_blaster"), st("p2", 0, "move", option="to_cart")))
    assert a2["push_cart"]["status"] == "ok" and a2["inspect_cart"]["status"] == "ok"
    # requirement before / after its provider
    before = validate(plan(st("q1", 0, "object", option="holster_blaster"), st("q2", 0, "action", option="open_door"), st("q3", 0, "action", option="cut_chain")))
    assert err_at(before, "q2", "REQUIRES") and err_at(before, "q2", "REQUIRES")[0]["suggest"] == ["cut_chain"]
    after = validate(plan(st("q1", 0, "object", option="holster_blaster"), st("q3", 0, "action", option="cut_chain"), st("q2", 0, "action", option="open_door")))
    assert after["legal"], after["errors"]
    # removes apply at their step: deactivating the blade before the cut
    off = validate(plan(st("r1", 0, "object", option="deactivate_saber"), st("r2", 0, "action", option="cut_chain")))
    assert err_at(off, "r2", "REQUIRES")


def test_nothing_is_ever_added_removed_or_reordered():
    for d in (S1, S1_FIXED):
        v = validate(d)
        assert [s["id"] for s in v["steps"]] == [s["id"] for s in d["steps"]]
        assert [s["type"] for s in v["steps"]] == [s["type"] for s in d["steps"]]


# ---------- S2: conditional branches ----------
S2 = plan(st("a1", 0, "object", option="holster_blaster"),
          st("a2", 0, "speech", text="Wick. Is something shut in there? Tell me what you know."),
          {"id": "b1", "seq": 0, "type": "branch", "otherwise": "stop", "cases": [
              {"when": "Wick confirms something is trapped inside", "steps": [], "after": "stop"},
              {"when": "Wick gives credible information supporting opening the shed", "steps": [{"id": "b1s", "type": "action", "option": "cut_chain"}]}]},
          st("a3", 1, "action", option="open_door"), st("a4", 1, "action", option="prepare_enter"))


def test_S2_branch_validates_every_path_and_waits_for_the_player():
    v, s, _ = status(S2)
    assert v["legal"] and v["paths"] == 3 and v["halts"] == [2], v
    assert s["b1"] == "branch" and s["a3"] == "waits" and s["a4"] == "waits" and s["b1s"] in ("risky", "case"), s
    texts = [p["text"] for p in v["preview"]]
    assert texts[2].startswith("If Wick confirms something is trapped inside: do none of this, then stop and ask me")
    assert texts[3].startswith("Else if Wick gives credible information") and texts[4] == "Otherwise: stop and ask me"
    assert "BRANCH" in codes(v, "info")


def test_S2_otherwise_continue_flags_the_path_where_a_later_step_cannot_happen():
    d = copy.deepcopy(S2); d["steps"][2]["otherwise"] = "continue"
    v = validate(d)
    assert v["legal"], "a step that fails on only some paths is advisory"
    w = [x for x in v["warnings"] if x["code"] == "BRANCH_DEPENDENT" and x["step_id"] == "a3"]
    assert w and "otherwise" in w[0]["message"] and w[0]["advisory"], v["warnings"]


def test_S2_missing_information_is_never_confirmation():
    # the GM may not call the plan complete or pick a case without a settled answer
    bad = progress(S2, {"completed": ["a1", "a2"], "stop_kind": "complete", "reason": ""})
    assert not bad["ok"]
    stop = progress(S2, {"completed": ["a1", "a2"], "stop_kind": "condition", "reason": "Wick does not know what is inside."})
    assert stop["ok"] and stop["plan_progress"]["pending"] == ["b1", "a3", "a4"], stop
    assert stop["pending_steps"][0]["type"] == "branch" and all(x["status"] == "pending" for x in stop["pending_steps"])
    # a settled case: "credible information" was committed, so the cut and the rest run
    go = progress(S2, {"completed": ["a1", "a2", "b1s", "a3", "a4"], "branches": {"b1": 1}, "stop_kind": "complete", "reason": ""})
    assert go["ok"] and go["plan_progress"]["skipped"] == [] and not go["pending_steps"], go
    # "trapped" was confirmed: no cut, then stop and ask (the player's own instruction)
    trapped = progress(S2, {"completed": ["a1", "a2"], "branches": {"b1": 0}, "stop_kind": "condition", "reason": "Wick says someone is shut inside."})
    assert trapped["ok"] and trapped["plan_progress"]["pending"] == ["a3", "a4"] and trapped["plan_progress"]["skipped"] == ["b1s"], trapped


# ---------- S3: unexpected interruption, partial prefix, entry into combat ----------
def test_S3_hidden_mastiff_interrupts_and_combat_invalidates_the_rest():
    done = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s10b", "s11"]
    r = progress(S1_FIXED, {"action_id": "a_s3", "completed": done, "interrupted": "s12", "stop_kind": "combat",
                            "reason": "Something burst out of the dark behind you and lunged; it went past you through the open door."})
    assert r["ok"], r
    pp = r["plan_progress"]
    assert pp["completed"] == done and pp["interrupted"] == "s12" and pp["invalidated"] == ["s12", "s13", "s14", "s15"] and pp["pending"] == []
    assert all(x["status"] == "invalidated" for x in r["pending_steps"]) and r["pending_steps"][0]["interrupted"]
    assert r["plan_result"] == {"stop_kind": "combat", "reason": pp["reason"], "completed": 12, "pending": 0, "invalidated": 4}
    # invalidated steps can never be run again, even if a client marks them authorized
    again = [dict(x, authorized=True) for x in r["pending_steps"]]
    v = validate(plan(*again))
    assert "INVALIDATED" in codes(v) and not v["legal"]


def test_consequential_stop_leaves_pending_steps_that_need_reauthorization():
    r = progress(S1_FIXED, {"completed": ["s1", "s2", "s3"], "interrupted": "s4", "stop_kind": "consequential",
                            "reason": "Wick grabs your sleeve: someone is coming up the lane with a lamp."})
    assert r["ok"] and r["plan_progress"]["pending"][0] == "s4" and r["pending_steps"][0]["status"] == "interrupted"
    v = validate(plan(*r["pending_steps"]))
    assert "PENDING_UNAUTHORIZED" in codes(v)
    ok = validate(plan(*[dict(x, authorized=True) for x in r["pending_steps"]]))
    assert "PENDING_UNAUTHORIZED" not in codes(ok)


def test_partial_prefix_rules():
    assert not progress(S1_FIXED, {"completed": ["s1", "s3"], "stop_kind": "mechanical", "reason": ""})["ok"]   # not a prefix
    assert not progress(S1_FIXED, {"completed": ["s1"], "stop_kind": "incidental", "reason": "a dog barks far off"})["ok"]  # not a stop
    assert not progress(S1_FIXED, {"completed": ["s1"], "stop_kind": "complete", "reason": ""})["ok"]
    assert not progress(S1_FIXED, {"completed": ["s1"], "interrupted": "s3", "stop_kind": "mechanical", "reason": ""})["ok"]
    pre = progress(S1_FIXED, {"completed": ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9"], "interrupted": "s10",
                              "stop_kind": "prerequisite", "reason": "The chain held.", "invalidated": ["s11", "s12", "s15"]})
    assert pre["ok"] and pre["plan_progress"]["invalidated"] == ["s11", "s12", "s15"] and pre["plan_progress"]["pending"] == ["s10", "s10b", "s13", "s14"], pre


def test_uneventful_plan_is_one_pass_with_nothing_pending():
    ids = [s["id"] for s in S1_FIXED["steps"]]
    r = progress(S1_FIXED, {"completed": ids, "stop_kind": "complete", "reason": ""})
    assert r["ok"] and r["pending_steps"] == [] and r["plan_result"]["completed"] == len(ids)


def test_entry_into_combat_keeps_strict_action_economy():
    combat = json.loads(COMBAT.read_text())
    acts = [o["id"] for o in combat["options"] if o["slot"] == "action"][:2]
    v = validate(plan(st("c1", 0, "action", option=acts[0], target=None), st("c2", 1, "action", option=acts[1], target=None)), ctx=COMBAT)
    assert "ACTION_CONFLICT" in codes(v), "sequences never multiply the combat action economy"


# ---------- free text has the same checks ----------
def test_freeform_parity():
    r = node("parse", "Holster the blaster. Then go to the cart. Then push the cart. Then open the door.", str(CTX))
    v = r["validation"]
    assert [s.get("option") for s in v["steps"]] == ["holster_blaster", "to_cart", "push_cart", "open_door"], v["steps"]
    found = {e["code"] for e in v["errors"]}
    assert {"REQUIRES", "POSITION"} <= found, v["errors"]      # no cut first; the door is 35 ft back from the cart


# ---------- hidden-information boundary and no predictions ----------
def test_no_hidden_information_or_odds_anywhere():
    ctx_text = CTX.read_text()
    for m in GM["leak_markers"]:
        assert m not in ctx_text, m
    validate(S1); avail(S1, {"seq": 2}); status(S2)
    blob = "\n".join(OUTPUTS)
    for m in GM["leak_markers"]:
        assert m not in blob, "leak: " + m
    reasons = " ".join(re.findall(r'"(?:message|reasons|text)":\s*"([^"]*)"', blob))
    assert not re.search(r"\b(chance|likely|probabl\w*|odds|\d+\s*%|DC\s*\d+|succeed|will hit|will miss)\b", reasons, re.I), "no predictions"


def test_contract2_and_1_declarations_still_validate():
    old = {"actor": "aero", "source": "composer", "speech": None, "actions": [{"option": "signal_wick", "target": None, "trigger": None}],
           "bonus_actions": [], "movement": {"option": "hold"}, "objects": [], "reactions": [], "unmapped": []}
    v = validate(old)
    assert v["legal"] and v["steps"][0]["id"] == "k0" and v["contract"] == "turn-contract/3"


if __name__ == "__main__":
    import sys
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("ok", name)
            except Exception as e:  # noqa
                fails += 1; print("FAIL", name, repr(e)[:600])
    print("all passed" if not fails else f"{fails} failed")
    sys.exit(1 if fails else 0)
