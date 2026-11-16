#!/usr/bin/env python3
"""SYNTHETIC check of the mobile test drill: scripted GM moves through the real gateway, validator, encounter
controller, experimental resolver and ledger, on a throwaway copy of the deterministic fixture. No model, no network,
no Artifact database, no real transport. The real worker round trip is recorded separately (MOBILE_TEST_BUILD.md).

Covers, in one fight: a partial turn that stays open; the same turn continued and ended by the player's word; Wick's
own GM-run turn; each sim hound's own turn with its own roll subject (shared count, separate budgets, one hidden);
Heroic and Narrative Consequences applied to Aero's d20 only; a GM option that ends the turn; no reroll anywhere.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
QA = ROOT / "development/.qa"
for extra in (ROOT / "development/gm_provider", ROOT / ".claude/skills/litrpg-ledger", ROOT / "development/encounter", ROOT / "development/experimental_resolution"):
    sys.path.insert(0, str(extra))
import staging                      # noqa: E402
import ledger                       # noqa: E402
import encounter                    # noqa: E402
import engine                       # noqa: E402
from gateway import Refused         # noqa: E402

FIXTURE = HERE / "fixture_campaign"
ME, MODEL = "claude-session", {"kind": "scripted", "mock": True}
N = [0]


def e(kind, _private=False, _actor=None, _rolls=None, **details):
    out = {"kind": kind, "summary": kind.replace("_", " "), "visibility": "gm_only" if _private else "player", "details": details}
    if _actor:
        out["actor"] = _actor
    if _rolls:
        out["roll_keys"] = _rolls
    return out


def submit(gw, text=None, steps=None, settings=None, end_turn=False, extra=None):
    N[0] += 1
    action = staging.declare(gw, f"mtest-{N[0]:04d}", text=text, steps=steps, provider=ME, settings=settings)
    if end_turn:
        action["declaration"]["end_turn"] = True
    action.update(extra or {})
    gw.submit(action)
    run = f"run-{N[0]}"
    gw.claim(ME, run, MODEL)
    return action, run, gw.context(ME, run)


def next_context(gw, **changes):
    context = {k: v for k, v in gw.public_state()["state"]["turn_context"].items() if k not in ("context_id", "encounter", "equipment")}
    context.update(changes)
    return context


def codes(context):
    return [i["code"] for i in context["validation"]["info"]]


def main():
    subprocess.run([sys.executable, "-B", str(HERE / "build_fixture.py")], check=True, capture_output=True)
    before = {p.relative_to(FIXTURE).as_posix(): p.read_bytes() for p in FIXTURE.rglob("*") if p.is_file()}
    QA.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mobile-", dir=QA) as directory:
        gw, first = staging.make(directory, campaign_id="mobile-test-1", experimental=True, source=FIXTURE)
        try:
            state = first["state"]
            assert state["experimental_resolution"] == {"enabled": True, "schema": "genesis-experimental-resolution/1"}, "dice controls are exposed only by the noncanonical marker"
            tracker = state["turn_context"]["encounter"]
            assert [(s["label"], s.get("role"), s.get("control")) for s in tracker["order"]] == [
                ("Aero", "player_character", "player"), ("Wick", "allied_npc", "gm"), ("Sim hound (near)", "npc", "gm"), ("Sim hound (far)", "npc", "gm"),
                ("Others you cannot see", None, None)], tracker["order"]
            assert (tracker["round"], tracker["current"], tracker["next"]) == (1, "Aero", "Wick")
            public_dump = lambda: json.dumps(gw.public_state()) + json.dumps([gw.store.read(k)[1] for k in gw.store.keys("view/")]) + (gw.campaign / "records/roll_log.jsonl").read_text()
            assert "hound_3" not in public_dump() and "third hound" not in public_dump()

            # 1. PARTIAL TURN, Heroic + Narrative Consequences: ignite, close, strike. Movement is left, so the turn stays open.
            action, run, context = submit(gw, text="I ignite my lightsaber, close on the near hound and strike the near hound.",
                                          settings={"temperature": "heroic", "narrative_consequences": True})
            assert context["validation"]["legal"] and "TURN_CONTINUES" in codes(context), context["validation"]
            steps = {s["type"]: s["id"] for s in context["declaration"]["steps"]}
            gw.fix_tables(ME, run, {"interpretation": "Three declared steps in order; the strike is an attack against the near hound.", "tables": "none", "npc_evaluations": []})
            attack = gw.roll(ME, run, {"roll_key": "s.attack", "step_id": steps["action"], "formula": "1d20+5", "kind": "attack", "requested_by": "aero",
                                      "purpose": "Aero strikes the near hound", "dc": 12, "rule_sources": ["fixture"]})["result"]
            assert attack["resolution"]["eligible"] and attack["resolution"]["roll"]["temperature"] == "heroic" and attack["resolution"]["narrative"] is not None
            raw = attack["resolution"]["roll"]["selected_raw_d20"]
            assert attack["resolution"]["roll"]["effective_d20"] == 11 + (raw - 1) // 2
            events = [e("object_interaction", _actor="aero", step_id=steps["object"], option="ignite_saber"), e("resource_spent", actor_id="aero", resource="object_interaction", **{"for": steps["object"]}),
                      e("movement", _actor="aero", step_id=steps["move"], option="to_near_hound"), e("resource_spent", actor_id="aero", resource="movement_ft", amount=10, **{"for": steps["move"]}),
                      e("attack_resolved", _actor="aero", _rolls=["s.attack"], step_id=steps["action"], target="hound_1"), e("resource_spent", actor_id="aero", resource="action", **{"for": steps["action"]})]
            proposal = {"world_time": "Sim drill, round 1", "narration": "The blade snaps alight. You close and cut at the near hound. Your turn is still open.",
                        "scene_state": {"summary": "Aero engages the near hound", "title": "Sim Deck: Drill Seven (TEST, not canon)", "location": "Holo-sim deck", "atmosphere": ["test"]},
                        "turn_context": next_context(gw, state_flags=["saber_ignited"], budget={"action": 0, "bonus_action": 1, "reaction": 1, "movement_ft": 20, "object_interaction": 0})}
            for forbidden, code in (([e("turn_end", actor_id="aero"), e("turn_start", actor_id="hound_1")], "ENCOUNTER_OUT_OF_ORDER"),
                                    ([e("resource_spent", actor_id="wick", resource="action")], "ENCOUNTER_OFF_TURN"),
                                    ([e("resource_spent", actor_id="aero", resource="action")], "ENCOUNTER_NO_BUDGET")):
                try:
                    gw.commit(ME, run, dict(proposal, events=events + forbidden))
                    raise AssertionError(code + " was accepted")
                except Refused as refusal:
                    assert code in [p["code"] for p in refusal.extra["problems"]], refusal.extra
            assert gw.commit(ME, run, dict(proposal, events=events))["status"] == "committed"
            tracker = gw.public_state()["state"]["turn_context"]["encounter"]
            assert (tracker["round"], tracker["current"]) == (1, "Aero") and tracker["order"][0]["budget"]["movement_ft"] == 20 and tracker["order"][0]["budget"]["action"] == 0, "the submission did not end the turn"
            assert tracker["order"][1]["status"] == "waiting", "nobody else acted"

            # 2. CONTINUATION: the same turn, ended by the player's word, default (Regular / Off) dice.
            action2, run, context = submit(gw, steps=[{"type": "speech", "option": "d2", "id": "k0", "seq": 0}], end_turn=True)
            assert "TURN_ENDS" in codes(context), context["validation"]["info"]
            assert context["resolution"]["settings"] == {"temperature": "regular", "narrative_consequences": False}, "settings are per submission and default to Regular / Off"
            gw.fix_tables(ME, run, {"interpretation": "Aero asks Wick to shoot the near one if it comes at them, then ends his turn. Wick decides his own turn; then each hound.",
                                    "tables": "Wick: fires at a hound within 20 ft with a clear line; the request matches what he would do anyway.",
                                    "npc_evaluations": [{"npc": "wick", "since": None, "changes": [], "no_change_reason": "first evaluation", "outcome_key": "fires_at_near", "basis": "frightened, stays put, fires when a hound is within 20 ft"},
                                                        {"npc": "hound_1", "since": None, "changes": [], "no_change_reason": "first evaluation", "outcome_key": "bites_nearest", "basis": "drill program"},
                                                        {"npc": "hound_2", "since": None, "changes": [], "no_change_reason": "first evaluation", "outcome_key": "circles_to_wick", "basis": "drill program"}]})
            npc = lambda key, subject, by="gm", formula="1d20+3", kind="attack", dc=13, purpose="A creature attacks": gw.roll(ME, run, {
                "roll_key": key, "formula": formula, "kind": kind, "requested_by": by, "purpose": purpose, "dc": dc, "subject": subject,
                "provenance": {"kind": "gm_turn", "actor_id": subject}, "rule_sources": ["fixture"]})
            wick = npc("n1.attack", "wick", formula="1d20+2", dc=12, purpose="Wick fires at the near hound")
            h1 = npc("n2.attack", "hound_1", purpose="The near hound bites")
            h2 = npc("n3.attack", "hound_2", purpose="The far hound bites")
            assert len({wick["result"]["roll_id"], h1["result"]["roll_id"], h2["result"]["roll_id"]}) == 3, "each creature has its own roll (X1)"
            assert npc("n2b.attack", "hound_1", purpose="again under a new key")["result"]["roll_id"] == h1["result"]["roll_id"], "no reroll under a renamed key"
            for theirs in (wick, h1, h2):
                r = theirs["result"]["resolution"]
                assert (r["eligible"], r["roll"]["temperature"], r["narrative"]) == (False, "regular", None), "only the player party's own d20s can be transformed; Wick and the hounds are Regular"
            speech = context["declaration"]["steps"][0]["id"]
            turns = [e("speech", _actor="aero", step_id=speech), e("turn_end", actor_id="aero"),
                     e("turn_start", actor_id="wick"), e("resource_spent", actor_id="wick", resource="action", **{"for": "fires the blaster pistol"}),
                     e("attack_resolved", _actor="wick", _rolls=["n1.attack"], actor_id="wick", target="hound_1"), e("turn_end", actor_id="wick"),
                     e("turn_start", actor_id="hound_1"), e("resource_spent", actor_id="hound_1", resource="action"), e("attack_resolved", _actor="hound_1", _rolls=["n2.attack"], actor_id="hound_1", target="aero"), e("turn_end", actor_id="hound_1"),
                     e("turn_start", actor_id="hound_2"), e("resource_spent", actor_id="hound_2", resource="movement_ft", amount=40), e("resource_spent", actor_id="hound_2", resource="action"),
                     e("attack_resolved", _actor="hound_2", _rolls=["n3.attack"], actor_id="hound_2", target="wick"), e("turn_end", actor_id="hound_2"),
                     e("turn_start", _private=True, actor_id="hound_3"), e("turn_end", _private=True, actor_id="hound_3"),
                     e("turn_start", actor_id="aero")]
            proposal = dict(proposal, world_time="Sim drill, round 2", narration="Wick fires. The near hound snaps at you; the far one crosses the floor at Wick. It is your turn again.",
                            turn_context=next_context(gw, round=2, budget={"action": 1, "bonus_action": 1, "reaction": 1, "movement_ft": 30, "object_interaction": 1}))
            try:
                gw.commit(ME, run, dict(proposal, events=[x for x in turns if (x["details"].get("actor_id") != "hound_2" or x.get("roll_keys"))]))
                raise AssertionError("a creature's roll without its own turn was accepted")
            except Refused as refusal:
                assert "NPC_ROLL_PROVENANCE" in [p["code"] for p in refusal.extra["problems"]], refusal.extra
            assert gw.commit(ME, run, dict(proposal, events=turns))["status"] == "committed"
            tracker = gw.public_state()["state"]["turn_context"]["encounter"]
            assert (tracker["round"], tracker["current"], tracker["next"]) == (2, "Aero", "Wick"), tracker
            assert [s["label"] for s in tracker["order"]] == ["Aero", "Wick", "Sim hound (near)", "Sim hound (far)", "Others you cannot see"]
            fold = encounter.fold(ledger.load_all(gw.campaign))
            assert {a: fold["actors"][a]["turns_taken"] for a in fold["actors"]} == {"aero": 2, "wick": 1, "hound_1": 1, "hound_2": 1, "hound_3": 1}, "every creature acted exactly once on its own turn"
            assert "hound_3" not in public_dump()

            # 3. A GM OPTION THAT ENDS THE TURN: the review's alternative is legal, loads, and resolves as "end my turn".
            action3, run, context = submit(gw, text="I use Burst and then strike the near hound.")
            assert not context["validation"]["legal"] and context["validation"]["errors"][0]["code"] == "ACTION_CONFLICT"
            end = {"actor": "aero", "source": "composer", "freeform": "", "unmapped": [], "steps": [], "movement": {"option": "hold"}, "end_turn": True}
            reviewed = gw.review(ME, run, {"summary": "Burst and a lightsaber attack both need your action.", "errors": [{"code": "ACTION_CONFLICT", "message": "one action per turn"}],
                                           "alternatives": [{"label": "End your turn here: hold, no actions", "declaration": end}]})
            assert reviewed["status"] == "needs_revision" and reviewed["review"]["alternatives"][0]["declaration"]["end_turn"] is True
            rolls_before = (gw.campaign / "records/roll_log.jsonl").read_bytes()
            N[0] += 1
            chosen = staging.declare(gw, f"mtest-{N[0]:04d}", steps=[], provider=ME)
            chosen["declaration"] = dict(chosen["declaration"], movement={"option": "hold"}, end_turn=True)
            chosen["text"] = "GM option chosen: End your turn here: hold, no actions"
            chosen["gm_alternative"] = {"of_action": action3["action_id"], "index": 0, "label": "End your turn here: hold, no actions"}
            gw.submit(chosen)
            gw.claim(ME, "run-alt", MODEL)
            context = gw.context(ME, "run-alt")
            assert context["validation"]["legal"] and "TURN_ENDS" in codes(context), "an empty GM option is a complete declaration that ends the turn"
            assert (gw.campaign / "records/roll_log.jsonl").read_bytes() == rolls_before, "a review rolls nothing"
            gw.release(ME, "run-alt", "synthetic check ends here")

            assert engine.replay(gw.campaign)["ok"]
            assert not ledger.validate_all(gw.campaign)[1]
            log = ledger.read_jsonl(gw.campaign / "records/roll_log.jsonl")
            assert len(log) == 4 and len({r["roll_id"] for r in log}) == 4, [r["roll_id"] for r in log]
        finally:
            gw.store.close()
    after = {p.relative_to(FIXTURE).as_posix(): p.read_bytes() for p in FIXTURE.rglob("*") if p.is_file()}
    assert after == before, "the fixture source changed"
    print("ok mobile test drill (synthetic): partial turn, continuation, end by word, Wick's GM turn, per-creature hound turns and roll subjects, "
          "hidden hound stays hidden, Heroic only for Aero, GM end-turn option, no rerolls, replay ok")


if __name__ == "__main__":
    main()
