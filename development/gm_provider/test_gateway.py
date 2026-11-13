"""Provider interchange tests on isolated copies of the sandbox campaign.

Every GM here is a ScriptedProvider: a deterministic MOCK named "claude", "gpt" or "gemini".
These tests prove the shared boundary (routing, lease, operation identity, recovery, privacy),
not any model's behaviour. No network, no Artifact database, no source campaign writes.
Run: python3 -B development/gm_provider/test_gateway.py
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
QA = ROOT / "development/.qa"
sys.path.insert(0, str(HERE))
import gateway as gateway_module   # noqa: E402
import staging                     # noqa: E402
from gateway import Refused        # noqa: E402
from providers import ScriptedProvider, BadMove  # noqa: E402
from runner import run_turn        # noqa: E402

audit_rng = gateway_module._module("test_rng", ".claude/skills/litrpg-dice/audit_rng.py")
ledger = gateway_module.ledger


class Clock:
    """Real time plus an offset: leases expire for the gateway when the test jumps forward."""
    def __init__(self):
        self.offset = 0

    def __call__(self):
        return time.time_ns() // 1_000_000 + self.offset

    def expire(self, gateway):
        self.offset += gateway.lease_ms + 1000


def marker(name, context):
    return f"GM marker: {name} after {context['ledger_head']}"


def previous_marker(context):
    notes = context["public_context"].get("notes", [])
    found = [n for n in notes if n.startswith("GM marker: ")]
    return found[-1] if found else "GM marker: none"


def script(name, tamper=None):
    """A complete scripted GM. `tamper(move, context)` lets a test corrupt a move."""
    def step(context):
        operation = context["operation"]
        steps = context["declaration"].get("steps", [])
        if operation["tables"] is None:
            move = {"type": "tables", "tables": {"interpretation": f"{name} reads the declaration as {len(steps)} ordered step(s) in the scripted staging scene.",
                                                 "tables": f"{name} private table: on 12 or more the remote's damage reads as real.", "npc_evaluations": []}}
        else:
            wanted = [{"roll_key": f"{s['id']}.check", "step_id": s["id"], "formula": "1d20+3", "mode": "normal", "kind": "check",
                       "requested_by": "aero", "purpose": "Aero studies the remote", "dc": 12, "rule_sources": ["staging script"]}
                      for s in steps if s["type"] == "action"]
            missing = [r for r in wanted if r["roll_key"] not in operation["rolls"]]
            if missing:
                move = {"type": "rolls", "rolls": missing}
            else:
                events, hands = [], copy.deepcopy(context["public_context"].get("hands"))
                for s in steps:
                    if s["type"] == "object":
                        if s["option"] == "holster_blaster" and hands:
                            hands["left"] = None
                        events.append({"kind": "object_interaction", "actor": "aero", "summary": f"Aero: {s['option']}",
                                       "details": {"step_id": s["id"], "option": s["option"], "hands": hands}})
                    elif s["type"] == "action":
                        total = operation["rolls"][f"{s['id']}.check"]["final_total"]
                        events.append({"kind": "observation", "actor": "aero", "summary": f"Aero studies the remote (total {total})",
                                       "details": {"step_id": s["id"]}, "roll_keys": [f"{s['id']}.check"]})
                events.append({"kind": "world_fact", "visibility": "gm_only", "summary": f"PRIVATE_{name.upper()}_CANARY hidden position note for the staging scene",
                               "details": {"canary": True}})
                nxt = copy.deepcopy(context["public_context"])
                nxt.pop("context_id", None)
                nxt.pop("equipment", None)
                if hands is not None:
                    nxt["hands"] = hands
                nxt["notes"] = [n for n in nxt.get("notes", []) if not n.startswith("GM marker: ")] + [marker(name, context)]
                move = {"type": "commit", "proposal": {
                    "world_time": "Staging", "events": events,
                    "narration": f"[{name}] You act. Before this: {previous_marker(context)}. Head was {context['ledger_head']}.",
                    "scene_state": {"summary": f"Staging scene after {name}", "title": "Sim deck", "location": "Staging", "atmosphere": ["staging"]},
                    "turn_context": nxt}}
        if tamper:
            move = tamper(move, context) or move
        return move
    return ScriptedProvider(name, step)


def fingerprints():
    base = ROOT / "campaigns/starwars_litrpg/runs"
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in base.rglob("*") if p.is_file()}


HOLSTER = "Holster the blaster pistol"
INSPECT = "Inspect the disabled remote again"


class Base(unittest.TestCase):
    experimental = False

    def setUp(self):
        self.protected = fingerprints()
        QA.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="provider-", dir=QA)
        self.addCleanup(self.tmp.cleanup)
        self.clock = Clock()
        self.gw, self.first = staging.make(self.tmp.name, experimental=self.experimental, clock=self.clock)
        self.addCleanup(self.gw.store.close)
        self.n = 0

    def tearDown(self):
        self.assertEqual(fingerprints(), self.protected, "a source campaign file changed")

    def act(self, text, provider=None, settings=None):
        self.n += 1
        action = staging.declare(self.gw, f"stage-{self.n:04d}", text=text, provider=provider, settings=settings)
        return action, self.gw.submit(action)

    def narration(self):
        return self.gw.public_state()["state"]["feed"][-1]["text"]

    def rolls_for(self, action_id):
        return [r for r in ledger.read_jsonl(self.gw.campaign / "records/roll_log.jsonl") if f"[{action_id}]" in r["purpose"]]

    def healthy(self):
        self.assertFalse(ledger.validate_all(self.gw.campaign)[1])
        self.assertTrue(audit_rng.audit(self.gw.campaign, samples=500)["ok"])


class Interchange(Base):
    def test_extended_single_provider_play(self):
        claude = script("claude")
        self.gw.select_provider("claude")
        heads = [self.first["cursor"]["ledger_head"]]
        for text in (HOLSTER, INSPECT, INSPECT, INSPECT, INSPECT):
            action, _ = self.act(text)
            out = run_turn(self.gw, claude)
            self.assertEqual(out["outcome"], "committed", out)
            self.assertIn(f"Head was {heads[-1]}", self.narration())
            heads.append(self.gw.public_state()["cursor"]["ledger_head"])
        self.assertEqual(len(set(heads)), 6)
        self.assertEqual(run_turn(self.gw, claude)["outcome"], "nothing")
        self.healthy()

    def test_switch_three_providers_and_return(self):
        providers = {n: script(n) for n in ("claude", "gpt", "gemini")}
        previous = "GM marker: none"
        order = ["claude", "gpt", "gemini", "claude", "gemini", "gpt"]
        for name in order:
            before = self.gw.public_state()["cursor"]
            action, status = self.act(INSPECT if name != "claude" else HOLSTER if self.n == 0 else INSPECT, provider=name)
            self.assertEqual(status["provider"], name)
            for other in providers:
                if other != name:
                    self.assertEqual(run_turn(self.gw, providers[other])["outcome"], "not_routed")
            out = run_turn(self.gw, providers[name])
            self.assertEqual(out["outcome"], "committed", out)
            text = self.narration()
            self.assertTrue(text.startswith(f"[{name}]"))
            self.assertIn(f"Before this: {previous}.", text, "the provider did not continue from its predecessor's committed result")
            self.assertIn(f"Head was {before['ledger_head']}", text)
            previous = f"GM marker: {name} after {before['ledger_head']}"
            after = self.gw.public_state()
            self.assertGreater(after["cursor"]["revision"], before["revision"])
            self.assertEqual(self.gw.store.read("view/state")[1]["revision"], after["cursor"]["revision"])
        committed = [json.loads(line) for line in (self.gw.campaign / "hidden/events.jsonl").read_text().splitlines()]
        by = [e["details"]["gm_provider"]["committed_by"] for e in committed if e["kind"] == "gm_ruling" and "gm_provider" in e.get("details", {})]
        self.assertEqual(by, order)
        self.healthy()

    def test_routing_selection_is_explicit_and_reversible(self):
        with self.assertRaises(Refused) as caught:
            self.act(HOLSTER)
        self.assertEqual(caught.exception.code, "PROVIDER_NOT_SELECTED")
        self.gw.select_provider("gpt")
        _, status = self.act(HOLSTER)
        self.assertEqual(status["provider"], "gpt")
        self.assertEqual(run_turn(self.gw, script("gpt"))["outcome"], "committed")
        self.gw.select_provider("claude")
        self.gw.select_provider("gpt")
        self.assertEqual([h["provider"] for h in self.gw.routing()["history"]], ["gpt", "claude", "gpt"])

    def test_stale_and_duplicate_submissions(self):
        self.gw.select_provider("claude")
        stale = staging.declare(self.gw, "stale-0001", text=INSPECT)
        action, first = self.act(HOLSTER)
        again = self.gw.submit(copy.deepcopy(action))
        self.assertTrue(again["duplicate"])
        changed = copy.deepcopy(action)
        changed["text"] = "Something else"
        with self.assertRaises(Refused) as caught:
            self.gw.submit(changed)
        self.assertEqual(caught.exception.code, "ACTION_ID_REUSED")
        with self.assertRaises(Refused) as caught:
            self.gw.submit(stale)
        self.assertEqual(caught.exception.code, "TURN_IN_FLIGHT")
        self.assertEqual(run_turn(self.gw, script("claude"))["outcome"], "committed")
        with self.assertRaises(Refused) as caught:
            self.gw.submit(stale)
        self.assertEqual(caught.exception.code, "STALE")
        self.assertTrue(self.gw.submit(copy.deepcopy(action))["duplicate"])      # a late retry of a committed action
        self.assertEqual(self.gw.action_status(action["action_id"])["status"], "committed")
        self.assertEqual(run_turn(self.gw, script("claude"))["outcome"], "nothing")
        self.assertEqual(len([e for e in ledger.load_all(self.gw.campaign) if e["kind"] == "player_declaration"
                              and e["details"].get("action_id") == action["action_id"]]), 1)

    def test_racing_declarations_leave_exactly_one_in_flight(self):
        self.gw.select_provider("claude")
        first, _ = self.act(HOLSTER)
        second = staging.declare(self.gw, "racer-0002", text=INSPECT)
        real, calls = self.gw._in_flight, {"n": 0}
        def blind_once():
            calls["n"] += 1
            return None if calls["n"] == 1 else real()      # the window between the check and the write
        self.gw._in_flight = blind_once
        try:
            with self.assertRaises(Refused) as caught:
                self.gw.submit(second)
        finally:
            self.gw._in_flight = real
        self.assertEqual((caught.exception.code, caught.exception.extra["action_id"]), ("TURN_IN_FLIGHT", first["action_id"]))
        self.assertEqual(self.gw.action_status("racer-0002")["status"], "failed")
        self.assertEqual(self.gw._in_flight()[2]["action_id"], first["action_id"])
        self.assertEqual(run_turn(self.gw, script("claude"))["outcome"], "committed")
        self.assertEqual(len([e for e in ledger.load_all(self.gw.campaign) if e["kind"] == "player_declaration"
                              and e["details"].get("action_id") == "racer-0002"]), 0)

    def test_second_provider_cannot_resolve_a_claimed_declaration(self):
        action, _ = self.act(INSPECT, provider="claude")
        self.gw.claim("claude", "run-a")
        for provider, run, code in (("gpt", "run-b", "PROVIDER_BUSY"), ("claude", "run-c", "PROVIDER_BUSY")):
            with self.assertRaises(Refused) as caught:
                self.gw.claim(provider, run)
            self.assertEqual(caught.exception.code, code)
        with self.assertRaises(Refused) as caught:
            self.gw.reroute(action["action_id"], "gpt")
        self.assertEqual(caught.exception.code, "PROVIDER_BUSY")
        with self.assertRaises(Refused) as caught:
            self.gw.context("gpt", "run-a")          # right run id, wrong provider
        self.assertEqual(caught.exception.code, "LEASE_LOST")
        self.clock.expire(self.gw)
        with self.assertRaises(Refused) as caught:
            self.gw.claim("gpt", "run-b")            # expired lease, but still routed to claude
        self.assertEqual(caught.exception.code, "NOT_ROUTED_HERE")
        with self.assertRaises(Refused) as caught:
            self.gw.fix_tables("claude", "run-a", {"interpretation": "late"})
        self.assertEqual(caught.exception.code, "LEASE_LOST")

    def test_interrupted_mid_turn_handoff_keeps_tables_and_dice(self):
        action, _ = self.act(INSPECT, provider="claude")
        def crash(kind, move):
            if kind == "commit":
                raise KeyboardInterrupt("worker killed before commit")
        with self.assertRaises(KeyboardInterrupt):
            run_turn(self.gw, script("claude"), run="run-a", interrupt=crash)
        rolls = self.rolls_for(action["action_id"])
        self.assertEqual(len(rolls), 1)
        dice = (self.gw.campaign / "hidden/dice_state.json").read_bytes()
        self.assertEqual(self.gw.action_status(action["action_id"])["status"], "processing")
        self.clock.expire(self.gw)
        self.gw.reroute(action["action_id"], "gemini")
        seen = {}
        def different_tables(move, context):
            seen.setdefault("phases", []).append(context["operation"]["phase"])
            seen["tables"] = context["operation"]["tables"]
            seen["rolls"] = context["operation"]["rolls"]
            return None
        out = run_turn(self.gw, script("gemini", different_tables), run="run-b")
        self.assertEqual(out["outcome"], "committed", out)
        self.assertEqual(out["moves"], ["commit"], "the successor replanned instead of continuing")
        self.assertEqual(seen["phases"], ["resolve"])
        self.assertIn("claude private table", seen["tables"]["tables"])
        self.assertEqual(list(seen["rolls"]), [f"{action['declaration']['steps'][0]['id']}.check"])
        self.assertEqual(self.rolls_for(action["action_id"]), rolls)
        self.assertEqual((self.gw.campaign / "hidden/dice_state.json").read_bytes(), dice)
        with self.assertRaises(Refused):
            self.gw.fix_tables("gemini", "run-b", {"interpretation": "x"})          # lease released after commit
        ruling = [e for e in ledger.load_all(self.gw.campaign) if e["kind"] == "gm_ruling" and "gm_provider" in e.get("details", {})][-1]
        self.assertEqual(ruling["details"]["gm_provider"], {"committed_by": "gemini", "runs": ["claude", "gemini"]})
        self.assertIn("claude private table", ruling["details"]["tables"])
        self.healthy()

    def test_successor_cannot_replace_tables_or_reroll(self):
        action, _ = self.act(INSPECT, provider="claude")
        self.gw.claim("claude", "run-a")
        self.gw.fix_tables("claude", "run-a", {"interpretation": "first reading", "tables": "t"})
        step = action["declaration"]["steps"][0]["id"]
        request = {"roll_key": "a", "step_id": step, "formula": "1d20+3", "kind": "check", "requested_by": "aero", "purpose": "Aero studies the remote", "dc": 12}
        first = self.gw.roll("claude", "run-a", request)
        self.assertEqual(self.gw.roll("claude", "run-a", request)["result"], first["result"])
        self.clock.expire(self.gw)
        self.gw.reroute(action["action_id"], "gpt")
        self.gw.claim("gpt", "run-b")
        with self.assertRaises(Refused) as caught:
            self.gw.fix_tables("gpt", "run-b", {"interpretation": "a kinder reading", "tables": "t2"})
        self.assertEqual(caught.exception.code, "TABLES_FIXED")
        renamed = self.gw.roll("gpt", "run-b", dict(request, roll_key="b", formula="1d20+9"))
        self.assertTrue(renamed["replayed"])
        self.assertEqual(renamed["result"], first["result"])
        with self.assertRaises(Refused) as caught:
            self.gw.roll("gpt", "run-b", dict(request, formula="1d20+9"))
        self.assertEqual(caught.exception.code, "ROLL_KEY_REUSED")
        with self.assertRaises(Refused) as caught:
            self.gw.review("gpt", "run-b", {"summary": "undo", "errors": [{"code": "HANDS", "message": "x"}]})
        self.assertEqual(caught.exception.code, "TOO_LATE_FOR_REVIEW")
        self.assertEqual(len(self.rolls_for(action["action_id"])), 1)

    def test_interrupted_ledger_batch_is_finished_byte_for_byte(self):
        action, _ = self.act(INSPECT, provider="gpt")
        real = gateway_module.batch.apply
        def torn(campaign, request, lock, run, led, after_stream=None):
            return real(campaign, request, lock, run, led, after_stream=lambda _: (_ for _ in ()).throw(RuntimeError("power lost")))
        gateway_module.batch.apply = torn
        try:
            with self.assertRaises(RuntimeError):
                run_turn(self.gw, script("gpt"), run="run-a")
        finally:
            gateway_module.batch.apply = real
        with self.assertRaises(ValueError):
            self.gw.public_state()                       # readers fail closed while a batch is pending
        dice = (self.gw.campaign / "hidden/dice_state.json").read_bytes()
        op = self.gw._op(action["action_id"])
        self.clock.expire(self.gw)
        out = run_turn(self.gw, script("gpt", lambda m, c: self.fail("a recovered batch must not be re-authored")), run="run-b")
        self.assertEqual((out["outcome"], out["authored"]), ("committed", False), out)
        self.assertEqual(self.gw._op(action["action_id"])["commit"]["fingerprint"], op["commit"]["fingerprint"])
        self.assertEqual((self.gw.campaign / "hidden/dice_state.json").read_bytes(), dice)
        self.assertEqual(len(self.rolls_for(action["action_id"])), 1)
        self.assertTrue(self.narration().startswith("[gpt]"))
        self.healthy()

    def test_publication_recovery_by_any_provider_without_authoring(self):
        action, _ = self.act(HOLSTER, provider="claude")
        before = self.gw.store.read("view/state")[1]
        real = self.gw.store.put
        def flaky(key, data, expected):
            if key == "view/state":
                raise ValueError("snapshot write refused")
            return real(key, data, expected)
        self.gw.store.put = flaky
        try:
            out = run_turn(self.gw, script("claude"))
        finally:
            self.gw.store.put = real
        self.assertEqual(out["outcome"], "resolved_unpublished", out)
        status = self.gw.action_status(action["action_id"])
        self.assertEqual((status["status"], status["publication"]["status"]), ("resolved", "pending"))
        self.assertEqual(self.gw.store.read("view/state")[1], before, "the player must keep seeing the last complete revision")
        with self.assertRaises(Refused) as caught:
            self.gw.submit(staging.declare(self.gw, "next-0001", text=INSPECT, provider="gpt"))
        self.assertEqual(caught.exception.code, "TURN_IN_FLIGHT")
        head = ledger.load_all(self.gw.campaign)[-1]["event_id"]
        out = run_turn(self.gw, script("gemini", lambda m, c: self.fail("publication must not author anything")))
        self.assertEqual((out["outcome"], out["authored"], out["moves"]), ("committed", False, ["publish"]))
        self.assertEqual(ledger.load_all(self.gw.campaign)[-1]["event_id"], head)
        self.assertEqual(self.gw.store.read("view/state")[1]["revision"], self.gw.public_state()["cursor"]["revision"])
        self.assertEqual(self.gw.action_status(action["action_id"])["status"], "committed")

    def test_unavailable_provider_blocks_and_is_never_substituted(self):
        action, _ = self.act(HOLSTER, provider="gemini")
        down = ScriptedProvider("gemini", lambda c: None, available=False, reason="missing GEMINI_API_KEY")
        out = run_turn(self.gw, down)
        self.assertEqual(out["outcome"], "blocked")
        status = self.gw.action_status(action["action_id"])
        self.assertEqual((status["status"], status["blocked"]["code"], status["provider"]), ("submitted", "PROVIDER_UNAVAILABLE", "gemini"))
        for other in ("claude", "gpt"):
            self.assertEqual(run_turn(self.gw, script(other))["outcome"], "not_routed")
        self.assertEqual(self.gw.action_status(action["action_id"])["status"], "submitted")
        self.gw.reroute(action["action_id"], "gpt")                     # the player's explicit choice
        self.assertEqual(run_turn(self.gw, script("gpt"))["outcome"], "committed")
        row = self.gw.store.read("actions/" + action["action_id"])[1]
        self.assertEqual([r["provider"] for r in row["gm"]["route"]], ["gemini", "gpt"])
        self.assertTrue(self.narration().startswith("[gpt]"))

    def test_provider_failing_mid_turn_keeps_accepted_dice(self):
        action, _ = self.act(INSPECT, provider="gpt")
        from providers import Unavailable
        calls = {"n": 0}
        def dies(move, context):
            calls["n"] += 1
            if move["type"] == "commit":
                raise Unavailable("gpt: HTTP 503")
        out = run_turn(self.gw, script("gpt", dies))
        self.assertEqual(out["outcome"], "blocked", out)
        self.assertEqual(out["moves"], ["tables", "rolls"])
        rolls = self.rolls_for(action["action_id"])
        out = run_turn(self.gw, script("gpt"))                           # same provider, later, lease was released
        self.assertEqual((out["outcome"], out["moves"]), ("committed", ["commit"]))
        self.assertEqual(self.rolls_for(action["action_id"]), rolls)

    def test_review_returns_the_declaration_without_dice(self):
        action, _ = self.act(HOLSTER, provider="claude")
        dice = (self.gw.campaign / "hidden/dice_state.json").read_bytes()
        head = ledger.load_all(self.gw.campaign)[-1]["event_id"]
        review = {"type": "review", "review": {"summary": "Which hand?", "errors": [{"code": "HANDS", "message": "Both hands are full."}],
                                               "alternatives": [{"label": "Holster the blaster", "declaration": action["declaration"]}]}}
        out = run_turn(self.gw, ScriptedProvider("claude", lambda c: review))
        self.assertEqual(out["outcome"], "needs_revision")
        self.assertEqual(self.gw.action_status(action["action_id"])["review"]["errors"][0]["code"], "HANDS")
        self.assertEqual((self.gw.campaign / "hidden/dice_state.json").read_bytes(), dice)
        self.assertEqual(ledger.load_all(self.gw.campaign)[-1]["event_id"], head)
        _, status = self.act(HOLSTER, provider="gpt")                    # the player revises; another provider may take it
        self.assertEqual(run_turn(self.gw, script("gpt"))["outcome"], "committed")

    def test_shared_validators_reject_unsafe_proposals(self):
        cases = {
            "ACTS_FOR_PLAYER": lambda p, c: p["events"].append({"kind": "object_interaction", "actor": "aero", "summary": "Aero also picks up the remote", "details": {}}),
            "RESERVED_KIND": lambda p, c: p["events"].append({"kind": "owner_ruling", "summary": "the GM grants a power", "details": {}}),
            "UNKNOWN_ROLL": lambda p, c: p["events"].append({"kind": "observation", "summary": "an invented roll", "roll_keys": ["made-up"], "details": {}}),
            "ROLL_UNACCOUNTED": lambda p, c: [e.pop("roll_keys", None) for e in p["events"]],
            "PRIVATE_LEAK": lambda p, c: p.__setitem__("narration", p["narration"] + " " + c["operation"]["tables"]["tables"]),
            "BAD_CONTEXT": lambda p, c: p["turn_context"].__setitem__("context_id", "evt_9999"),
            "NARRATION_LINT": lambda p, c: p.__setitem__("narration", p["narration"] + " The bolt severed your hand."),
        }
        action, _ = self.act(INSPECT, provider="claude")
        self.gw.claim("claude", "run-a")
        good = script("claude")
        while True:
            context = self.gw.context("claude", "run-a")
            move = good.step(context)
            if move["type"] == "commit":
                break
            if move["type"] == "tables":
                self.gw.fix_tables("claude", "run-a", move["tables"])
            else:
                for request in move["rolls"]:
                    self.gw.roll("claude", "run-a", request)
        head = ledger.load_all(self.gw.campaign)[-1]["event_id"]
        for code, corrupt in cases.items():
            proposal = copy.deepcopy(move["proposal"])
            corrupt(proposal, context)
            with self.assertRaises(Refused) as caught:
                self.gw.commit("claude", "run-a", proposal)
            self.assertEqual(caught.exception.code, "PROPOSAL_REJECTED")
            self.assertIn(code, [p["code"] for p in caught.exception.extra["problems"]], code)
            self.assertEqual(ledger.load_all(self.gw.campaign)[-1]["event_id"], head)
        for bad in ({"roll_key": "x", "step_id": "nope", "formula": "1d20", "kind": "check", "requested_by": "aero", "purpose": "undeclared"},
                    {"roll_key": "y", "formula": "1d20", "kind": "check", "requested_by": "gm", "purpose": "the dog resists DC 15"}):
            with self.assertRaises(Refused) as caught:
                self.gw.roll("claude", "run-a", bad)
            self.assertIn(caught.exception.code, ("NOT_DECLARED", "PURPOSE_LEAK"))
        self.assertEqual(self.gw.commit("claude", "run-a", move["proposal"])["status"], "committed")

    def test_runner_feeds_rejections_back_then_releases(self):
        action, _ = self.act(INSPECT, provider="gemini")
        attempts = {"n": 0}
        def flaky(move, context):
            if move["type"] == "commit":
                attempts["n"] += 1
                if attempts["n"] == 1:
                    self.assertNotIn("feedback", context)
                    move["proposal"]["events"].append({"kind": "object_interaction", "actor": "aero", "summary": "extra", "details": {}})
                else:
                    self.assertEqual(context["feedback"]["rejected"]["code"], "PROPOSAL_REJECTED")
            return move
        out = run_turn(self.gw, script("gemini", flaky))
        self.assertEqual((out["outcome"], attempts["n"]), ("committed", 2))
        action, _ = self.act(INSPECT, provider="gemini")
        hopeless = ScriptedProvider("gemini", lambda c: (_ for _ in ()).throw(BadMove("not JSON")))
        out = run_turn(self.gw, hopeless)
        self.assertEqual(out["outcome"], "released")
        self.assertEqual(self.gw.action_status(action["action_id"])["status"], "processing")
        self.assertEqual(run_turn(self.gw, script("gemini"))["outcome"], "committed")   # same provider recovers; nothing was lost

    def test_npc_evaluations_must_account_for_changes(self):
        action, _ = self.act(HOLSTER, provider="claude")
        self.gw.claim("claude", "run-a")
        with self.assertRaises(Refused) as caught:
            self.gw.fix_tables("claude", "run-a", {"interpretation": "i", "npc_evaluations": [
                {"npc": "remote", "since": "evt_0001", "changes": [], "outcome_key": "hold", "basis": "it is disabled"}]})
        self.assertEqual(caught.exception.code, "NPC_EVALUATION")
        self.assertEqual({p["code"] for p in caught.exception.extra["problems"]}, {"NPC_SINCE"})
        self.gw.fix_tables("claude", "run-a", {"interpretation": "i", "npc_evaluations": [
            {"npc": "remote", "since": None, "changes": [], "no_change_reason": "first evaluation; it is disabled", "outcome_key": "hold", "basis": "disabled"}]})

    def test_private_information_never_reaches_player_surfaces(self):
        providers = {n: script(n) for n in ("claude", "gpt", "gemini")}
        ids = []
        for name in providers:
            action, _ = self.act(INSPECT, provider=name)
            ids.append(action["action_id"])
            self.assertEqual(run_turn(self.gw, providers[name])["outcome"], "committed")
        public = self.gw.public_state()
        surfaces = [public, [self.gw.page(name) for name in public["pages"]], [self.gw.action_status(i) for i in ids],
                    [self.gw.store.read(k)[1] for k in self.gw.store.keys("")]]
        text = json.dumps(surfaces)
        for secret in ("CANARY", "private table", "seed", "roll_dcs", "interpretation", '"dc"'):
            self.assertNotIn(secret, text, secret)
        hidden = (self.gw.campaign / "hidden/events.jsonl").read_text()
        for name in providers:
            self.assertIn(f"PRIVATE_{name.upper()}_CANARY", hidden)
        self.assertIn("CANARY", json.dumps(self.gw._op(ids[0])) + hidden)      # it exists privately, so the check above is meaningful


class Settings(Base):
    def test_legacy_campaign_refuses_dice_modes(self):
        with self.assertRaises(Refused) as caught:
            self.act(INSPECT, provider="claude", settings={"temperature": "heroic", "narrative_consequences": True})
        self.assertEqual(caught.exception.code, "UNSUPPORTED_SETTINGS")
        with self.assertRaises(Refused) as caught:
            self.act(INSPECT, provider="claude", settings={"temperature": "godlike"})
        self.assertEqual(caught.exception.code, "BAD_SETTINGS")


class ExperimentalSettings(Base):
    experimental = True

    def test_dice_modes_follow_the_inspected_policy_across_providers(self):
        seen = {}
        def capture(move, context):
            seen[context["provider"]] = copy.deepcopy(context["operation"]["rolls"])
        for name, settings in (("claude", {"temperature": "regular", "narrative_consequences": False}),
                               ("gpt", {"temperature": "heroic", "narrative_consequences": True}),
                               ("gemini", {"temperature": "legendary", "narrative_consequences": True})):
            action, _ = self.act(INSPECT, provider=name, settings=settings)
            out = run_turn(self.gw, script(name, capture))
            self.assertEqual(out["outcome"], "committed", out)
            roll = next(iter(seen[name].values()))["resolution"]["roll"]
            raw = roll["selected_raw_d20"]
            expect = {"regular": raw, "heroic": 11 + (raw-1)//2, "legendary": 16 + (raw-1)//4}[settings["temperature"]]
            self.assertEqual((roll["temperature"], roll["effective_d20"]), (settings["temperature"], expect))
            narrative = next(iter(seen[name].values()))["resolution"]["narrative"]
            self.assertEqual(narrative is not None, settings["narrative_consequences"])
            declared = [e for e in ledger.load_all(self.gw.campaign) if e["kind"] == "player_declaration"][-1]["details"]
            self.assertEqual(declared.get("resolution_settings", gateway_module.policy.DEFAULT), {**gateway_module.policy.DEFAULT, **settings})
        self.healthy()
        self.assertTrue(gateway_module.engine.replay(self.gw.campaign)["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
