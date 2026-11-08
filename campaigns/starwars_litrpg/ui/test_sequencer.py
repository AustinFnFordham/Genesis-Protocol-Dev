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


def progress(decl, outcome, ctx=CTX):  # noqa
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
    assert stop["ok"] and stop["plan_progress"]["paused"] == ["b1"] and stop["plan_progress"]["unattempted"] == ["a3", "a4"], stop
    assert stop["pending_steps"][0]["type"] == "branch" and [x["status"] for x in stop["pending_steps"]] == ["paused", "unattempted", "unattempted"]
    # a settled case: "credible information" was committed, so the cut and the rest run
    go = progress(S2, {"completed": ["a1", "a2", "b1s", "a3", "a4"], "branches": {"b1": 1}, "stop_kind": "complete", "reason": ""})
    assert go["ok"] and go["plan_progress"]["skipped"] == [] and not go["pending_steps"], go
    # "trapped" was confirmed: no cut, then stop and ask (the player's own instruction)
    trapped = progress(S2, {"completed": ["a1", "a2"], "branches": {"b1": 0}, "stop_kind": "condition", "reason": "Wick says someone is shut inside."})
    assert trapped["ok"] and trapped["plan_progress"]["paused"] == ["a3"] and trapped["plan_progress"]["unattempted"] == ["a4"] and trapped["plan_progress"]["skipped"] == ["b1s"], trapped


# ---------- S3: unexpected interruption, partial prefix, entry into combat ----------
def test_S3_hidden_mastiff_interrupts_and_combat_invalidates_the_rest():
    done = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s10b", "s11"]
    r = progress(S1_FIXED, {"action_id": "a_s3", "completed": done, "interrupted": "s12", "stop_kind": "combat",
                            "reason": "Something burst out of the dark behind you and lunged; it went past you through the open door."})
    assert r["ok"], r
    pp = r["plan_progress"]
    assert pp["completed"] == done and pp["cancelled"] == ["s12", "s13", "s14", "s15"] and pp["unattempted"] == [] and pp["interrupted"] == []
    assert all(x["status"] == "cancelled" for x in r["pending_steps"]) and r["pending_steps"][0]["interrupted"]
    assert r["plan_result"]["completed"] == 12 and r["plan_result"]["cancelled"] == 4 and r["plan_result"]["unattempted"] == 0
    # cancelled steps can never be run again, even if a client marks them authorized
    again = [dict(x, authorized=True) for x in r["pending_steps"]]
    v = validate(plan(*again))
    assert "NOT_CONTINUABLE" in codes(v) and not v["legal"]


def test_consequential_stop_leaves_pending_steps_that_need_reauthorization():
    r = progress(S1_FIXED, {"completed": ["s1", "s2", "s3"], "interrupted": "s4", "stop_kind": "consequential",
                            "reason": "Wick grabs your sleeve: someone is coming up the lane with a lamp."})
    assert r["ok"] and r["plan_progress"]["interrupted"] == ["s4"] and r["pending_steps"][0]["status"] == "interrupted"
    assert r["plan_progress"]["cancelled"] == [] and len(r["plan_progress"]["unattempted"]) == 12, "a consequential stop does not cancel the rest"
    v = validate(plan(*r["pending_steps"]))
    assert "PENDING_UNAUTHORIZED" in codes(v)
    ok = validate(plan(*[dict(x, authorized=True) for x in r["pending_steps"]]))
    assert "PENDING_UNAUTHORIZED" not in codes(ok)


def test_status_vocabulary_is_distinct_and_combat_can_suspend():
    done = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s10b", "s11"]
    r = progress(S1_FIXED, {"completed": done, "interrupted": "s12", "stop_kind": "combat", "reason": "Initiative.", "suspended": ["s13"]})
    st = {x["id"]: x["status"] for x in r["pending_steps"]}
    assert st == {"s12": "cancelled", "s13": "suspended", "s14": "cancelled", "s15": "cancelled"}, st
    combat = json.loads(CTX.read_text()); combat["mode"] = "combat"; combat["context_id"] = "c1"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(combat, f)
    sus = [dict(x, authorized=True, authorized_ctx="c1") for x in r["pending_steps"] if x["status"] == "suspended"]
    assert "SUSPENDED" in codes(validate(plan(*sus), ctx=f.name)), "suspended intentions wait until the fight is over"
    scene_ok = validate(plan(*[dict(x, authorized_ctx="fixture_sequencer") for x in sus]))
    assert "SUSPENDED" not in codes(scene_ok) and "NOT_CONTINUABLE" not in codes(scene_ok)


def test_continue_requires_authorization_against_the_latest_context():
    r = progress(S1_FIXED, {"completed": ["s1", "s2", "s3"], "interrupted": "s4", "stop_kind": "consequential", "reason": "Wick stops you."})
    stale = [dict(x, authorized=True, authorized_ctx="an_older_context") for x in r["pending_steps"]]
    assert "PENDING_STALE" in codes(validate(plan(*stale)))
    fresh = [dict(x, authorized=True, authorized_ctx="fixture_sequencer") for x in r["pending_steps"]]
    v = validate(plan(*fresh))
    assert "PENDING_STALE" not in codes(v) and "PENDING_UNAUTHORIZED" not in codes(v)


def test_context_lint_warns_and_defers_instead_of_guessing():
    ctx = json.loads(CTX.read_text())
    ok = node("lintctx", "-", str(CTX))
    assert ok["ok"] and not [f for f in ok["findings"] if f["level"] != "info"], ok
    thin = copy.deepcopy(ctx); thin.pop("hands"); [o.pop("at", None) for o in thin["options"]]
    thin["visible"][2]["hp"] = 12
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(thin, f)
    r = node("lintctx", "-", f.name)
    c = {x["code"] for x in r["findings"]}
    assert {"NO_HANDS", "NO_AT", "LEAK_SUSPECT"} <= c and not r["ok"], r
    # with hands missing, hand checks are deferred (no false refusal), never guessed
    v = validate(plan(st("x", 0, "action", option="open_door")), ctx=f.name)
    assert "HANDS" not in codes(v)


def test_partial_prefix_rules():
    assert not progress(S1_FIXED, {"completed": ["s1", "s3"], "stop_kind": "mechanical", "reason": ""})["ok"]   # not a prefix
    assert not progress(S1_FIXED, {"completed": ["s1"], "stop_kind": "incidental", "reason": "a dog barks far off"})["ok"]  # not a stop
    assert not progress(S1_FIXED, {"completed": ["s1"], "stop_kind": "complete", "reason": ""})["ok"]
    assert not progress(S1_FIXED, {"completed": ["s1"], "interrupted": "s3", "stop_kind": "mechanical", "reason": ""})["ok"]
    pre = progress(S1_FIXED, {"completed": ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"],
                              "stop_kind": "prerequisite", "reason": "The chain held.", "blocked": ["s11", "s15"]})
    assert pre["ok"] and pre["plan_progress"]["blocked"] == ["s11", "s15"] and pre["plan_progress"]["unattempted"] == ["s10b", "s12", "s13", "s14"], pre
    assert not progress(S1_FIXED, {"completed": ["s1"], "stop_kind": "consequential", "reason": "", "suspended": ["s2"]})["ok"], "only combat suspends"
    assert not progress(S1_FIXED, {"completed": ["s1"], "stop_kind": "consequential", "reason": "", "cancelled": ["s1"]})["ok"], "a completed step cannot be cancelled"


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


# ---------- improvised equipment handling (owner 2026-11-08): S4 syntherope harness, S5 quick lightsaber weld ----------
WELD = HERE / "fixtures" / "hask_r2_weld.json"
HARNESS = dict(id="h4", seq=0, type="free", kind="custom",
               text="Tie the syntherope into a harness and lash the torch and both gas bottles to my back",
               method="bottles back to back, rope crossed over both shoulders and knotted at the waist",
               uses=["syntherope"], targets=["welding_cart"], hands=2,
               equipment_changes=[{"item": "syntherope", "to": "attached", "where": "the harness"}],
               creates={"label": "rope harness carrying the torch and two gas bottles", "state": "worn"})


def test_gear_is_derived_from_the_record_and_never_granted():
    ctx = json.loads(CTX.read_text()); eq = {e["id"]: e for e in ctx["equipment"]}
    assert eq["syntherope"]["state"] == "stored" and eq["lightsaber"]["state"] == "held" and eq["compact_jedi_glowrod"]["state"] == "attached"
    v = validate(plan(st("g1", 0, "free", kind="custom", text="Throw my grappling hook over the silo", uses=["grappling_hook"], method="overhand")))
    assert err_at(v, "g1", "UNKNOWN_ITEM") and not v["legal"], "an item Aero does not have is never granted"
    v2 = node("parse", "Throw my grappling hook up onto the roof", str(CTX))["validation"]
    assert v2["legal"] and "UNLISTED_ITEM" in codes(v2, "info"), "unlisted gear in free text is flagged for the GM, not invented"


def test_S4_occupied_hands_are_not_exhausted_capacity():
    base = [st("h1", 0, "object", option="holster_blaster"), st("h2", 0, "move", option="to_cart"), st("h3", 0, "object", option="eq_take:syntherope")]
    a = avail(plan(*base[:2]), {"seq": 0})
    assert a["eq_take:syntherope"]["status"] == "ok", a["eq_take:syntherope"]
    a0 = avail(plan(), {"seq": 0})
    assert a0["eq_take:syntherope"]["status"] == "needs_step" and a0["eq_take:syntherope"]["suggest"][0]["option"] == "holster_blaster", a0["eq_take:syntherope"]
    # with a method the harness is the GM's call, not refused (the saber still fills the right hand)
    v, s, full = status(plan(*base, dict(HARNESS)))
    assert v["legal"], v["errors"]
    w = {x["code"] for x in v["warnings"] if x.get("step_id") == "h4"}
    assert "GM_HANDS" in w and s["h4"] == "gm", (w, s)
    assert "IMPROVISED" in codes(v, "info")
    tr = {t["step_id"]: t for t in v["trace"]}
    assert tr["h3"]["equipment"]["syntherope"] == "held" and tr["h4"]["equipment"]["syntherope"] == "attached" and tr["h4"]["equipment"]["made_h4"] == "worn*"
    # without a method and without free hands the builder asks instead of guessing
    bare = dict(HARNESS); bare.pop("method")
    v2 = validate(plan(*base, bare))
    e = err_at(v2, "h4", "HANDS")
    assert e and e[0]["resolution"] == "needs_choice", v2["errors"]
    # switching the blade off and clipping it to the hip frees the hand: then nothing is left to ask
    off = [st("h1b", 0, "object", option="deactivate_saber"), st("h1c", 0, "object", option="eq_stow:lightsaber")]
    v3 = validate(plan(base[0], *off, *base[1:], bare))
    assert v3["legal"] and not [x for x in v3["warnings"] if x.get("step_id") == "h4" and x["code"] == "GM_HANDS"], (v3["errors"], v3["warnings"])
    # a lit blade cannot be clipped to the belt: switch it off first
    v4 = validate(plan(st("x", 0, "object", option="eq_stow:lightsaber")))
    assert err_at(v4, "x", "REQUIRES") and err_at(v4, "x", "REQUIRES")[0]["suggest"] == ["deactivate_saber"]


def test_S4_stored_tools_and_far_targets_are_asked_about():
    t = dict(id="k", seq=0, type="free", kind="custom", text="Lash the bottles with the syntherope", uses=["syntherope"], targets=["welding_cart"])
    v = validate(plan(st("h1", 0, "object", option="holster_blaster"), t))
    codes_k = {e["code"] for e in v["errors"] if e.get("step_id") == "k"}
    assert {"ACCESS", "POSITION"} <= codes_k, v["errors"]
    acc = err_at(v, "k", "ACCESS")[0]
    assert acc["suggest"] == ["eq_take:syntherope"] and acc["resolution"] == "add_step"
    # free text naming the rope links it, but the GM reads the method: advisory, never a refusal
    r = node("parse", "Holster the blaster. Tie the syntherope around the bottles", str(CTX))["validation"]
    assert r["legal"] and any(x["code"] == "GM_ACCESS" for x in r["warnings"]), r["warnings"]


def test_S4_created_item_is_planned_until_committed_and_later_use_depends_on_it():
    later = dict(id="h6", seq=1, type="free", kind="custom", text="Shrug the harness off by the shed door", uses=["made_h4"], hands=0,
                 equipment_changes=[{"item": "made_h4", "to": "placed"}])
    v = validate(plan(st("h1", 0, "object", option="holster_blaster"), st("h2", 0, "move", option="to_cart"), st("h3", 0, "object", option="eq_take:syntherope"),
                      dict(HARNESS), st("h5", 1, "move", option="to_shed_door"), later))
    assert v["legal"] and any(x["code"] == "GM_DEPENDS" and x["step_id"] == "h6" for x in v["warnings"]), v["warnings"]
    # encumbrance only when the record states capacity and bulk; never invented
    ctx = json.loads(CTX.read_text()); ctx["carry"] = {"capacity": 2, "unit": "bulk"}
    for e in ctx["equipment"]:
        if e["id"] in ("backpack", "syntherope"): e["bulk"] = 1
        if e["id"] == "lightsaber": e["bulk"] = 1
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(ctx, f)
    v2 = validate(plan(st("h1", 0, "object", option="holster_blaster")), ctx=f.name)
    assert any(x["code"] == "ENCUMBERED" and x["advisory"] for x in v2["warnings"]), v2["warnings"]
    assert not any(x["code"] == "ENCUMBERED" for x in validate(plan(st("h1", 0, "object", option="holster_blaster")))["warnings"])


WELD_STEP = dict(id="w2", seq=0, type="free", kind="custom", text="Run the tip of the lit blade along the door seam to tack-weld it shut",
                 method="short tacks along the latch side, then across the top hinge strap", uses=["lightsaber"], targets=["shed_door"],
                 creates={"label": "tack-welded seam on the shed door", "state": "placed"})


def test_S5_quick_lightsaber_weld_is_allowed_and_left_to_the_gm():
    v, s, _ = status(plan(st("w1", 0, "action", option="shut_door"), dict(WELD_STEP)), ctx=WELD)
    assert v["legal"] and s["w2"] == "gm" and "IMPROVISED" in codes(v, "info"), (v["errors"], s)
    # the blade must be lit for it: switched off first, the builder asks (no method) or defers (method)
    bare = dict(WELD_STEP); bare.pop("method")
    v2 = validate(plan(st("w0", 0, "object", option="deactivate_saber"), st("w1", 0, "action", option="shut_door"), bare), ctx=WELD)
    assert err_at(v2, "w2", "REQUIRES"), v2["errors"]
    v3 = validate(plan(st("w0", 0, "object", option="deactivate_saber"), st("w1", 0, "action", option="shut_door"), dict(WELD_STEP)), ctx=WELD)
    assert v3["legal"] and any(x["code"] == "GM_REQUIRES" for x in v3["warnings"])
    # from 15 ft back the seam is out of reach: a move is offered
    v4 = validate(plan(st("w1", 0, "move", option="back_off"), bare), ctx=WELD)
    p = err_at(v4, "w2", "POSITION")
    assert p and p[0]["suggest"] == ["hold"] or p and p[0]["resolution"] in ("add_step", "needs_choice"), v4["errors"]


def test_S5_weld_in_combat_uses_the_action_and_can_be_interrupted():
    weld = json.loads(WELD.read_text()); weld["mode"] = "combat"; weld["round"] = 1
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(weld, f)
    v = validate(plan(st("w1", 0, "action", option="shut_door"), dict(WELD_STEP)), ctx=f.name)
    assert "ACTION_CONFLICT" in codes(v), "a custom action costs the action in combat"
    assert validate(plan(dict(WELD_STEP)), ctx=f.name)["legal"]
    r = progress(plan(st("w1", 0, "action", option="shut_door"), dict(WELD_STEP), st("w3", 1, "action", option="brace_door")),
                 {"completed": ["w1"], "interrupted": "w2", "stop_kind": "mechanical", "reason": "Something slams into the door from inside before the seam is done."}, ctx=WELD)
    assert r["ok"] and r["pending_steps"][0]["status"] == "interrupted" and r["pending_steps"][0]["creates"]["label"].startswith("tack-welded"), r
    assert "made_w2" not in json.dumps(r["plan_progress"]), "an interrupted construction creates nothing"


def test_ledger_tracks_created_items_and_moves():
    import importlib.util
    spec = importlib.util.spec_from_file_location("eqm", HERE / "equipment.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    ev = [{"event_id": "e1", "kind": "object_interaction", "details": {"hands": {"right": {"item": "lightsaber"}, "left": None}}},
          {"event_id": "e2", "kind": "equipment_change", "details": {"item": "syntherope", "to": "attached", "where": "rope harness"}},
          {"event_id": "e3", "kind": "item_created", "details": {"id": "rope_harness", "label": "rope harness with the torch and two bottles", "state": "worn",
                                                                  "made_from": ["syntherope", "welding torch", "gas bottles"], "limits": "rides high; slips if Aero runs"}}]
    eq = {e["id"]: e for e in m.derive(ev)}
    assert eq["lightsaber"]["state"] == "held" and eq["syntherope"]["state"] == "attached" and eq["rope_harness"]["state"] == "worn" and eq["rope_harness"]["improvised"]
    assert "grappling_hook" not in eq
    eq2 = {e["id"]: e for e in m.derive(ev + [{"event_id": "e4", "kind": "item_destroyed", "details": {"item": "rope_harness"}}])}
    assert "rope_harness" not in eq2


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
