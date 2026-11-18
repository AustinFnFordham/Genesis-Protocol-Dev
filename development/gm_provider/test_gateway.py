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
    def test_whisper_context_never_enters_the_public_ledger(self):
        claude = script("claude")
        self.gw.select_provider("claude")
        self.n += 1
        action = staging.declare(self.gw, f"stage-{self.n:04d}", text=INSPECT)
        ctx = {"schema": "genesis-whisper-context/1", "source": "player_explicit", "visibility": "pc_private",
               "felt_emotion": ["fear"], "expression": {"style": "controlled", "text": "steady"}, "motive": "protect Wick",
               "reflection": "If it gets past me it gets him."}
        action["declaration"]["whisper"] = ctx
        action["text"] = action["text"] + "\nWHISPER (private): feels fear; why: protect Wick"
        self.gw.submit(action)
        self.assertEqual(run_turn(self.gw, claude)["outcome"], "committed")
        public = ledger.read_jsonl(self.gw.campaign / "records/events.jsonl")
        hidden = ledger.read_jsonl(self.gw.campaign / "hidden/events.jsonl")
        decl = [e for e in public if e["kind"] == "player_declaration" and e["details"]["action_id"] == action["action_id"]][0]
        self.assertNotIn("whisper", decl["details"]["declaration"])
        self.assertNotIn("WHISPER", decl["details"]["text"])
        self.assertNotIn("protect Wick", json.dumps(public))
        self.assertNotIn("protect Wick", json.dumps(self.gw.public_state()))
        kept = [e for e in hidden if e["kind"] == "whisper_context"]
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["details"]["context"], ctx)
        self.assertEqual(kept[0]["visibility"], "gm_only")
        self.healthy()

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
        provenance = ruling["details"]["gm_provider"]
        self.assertEqual((provenance["committed_by"], provenance["runs"]), ("gemini", ["claude", "gemini"]))
        self.assertEqual([(i["provider"], i["kind"], i["mock"]) for i in provenance["identities"]],
                         [("claude", "scripted", True), ("gemini", "scripted", True)], "a scripted stand-in must be recorded as one")
        self.assertIn("claude private table", ruling["details"]["tables"])
        self.healthy()

    def test_tb4_recovery_001_turn_builder_and_whisper_survive_a_crash_and_handoff(self):
        """TB4-22 / TB4-RECOVERY-001: TB4 custom words, Taunt fields and WHISPER context ride through a crash and a
        provider handoff unchanged; dice are not rerolled; exactly one result; WHISPER stays out of the public ledger."""
        self.n += 1
        action = staging.declare(self.gw, f"stage-{self.n:04d}", text=INSPECT, provider="claude")
        tb4 = {"schema": "genesis-turn-builder/4", "custom": [{"category": "secondary", "text": "Keep one eye on the door, verbatim."}],
               "taunt": {"target": None, "skill": "deception", "words": "You call that a drill?"}}
        whisper = {"schema": "genesis-whisper-context/1", "source": "player_explicit", "visibility": "pc_private",
                   "felt_emotion": ["doubt"], "expression": "unspecified", "motive": "learn what the remote hides", "reflection": None}
        action["declaration"]["tb4"] = tb4
        action["declaration"]["whisper"] = whisper
        action["declaration"]["unmapped"] = list(action["declaration"].get("unmapped", [])) + ["Keep one eye on the door, verbatim."]
        self.gw.submit(action)
        def crash(kind, move):
            if kind == "commit":
                raise KeyboardInterrupt("worker killed before commit")
        with self.assertRaises(KeyboardInterrupt):
            run_turn(self.gw, script("claude"), run="run-a", interrupt=crash)
        rolls = self.rolls_for(action["action_id"])
        dice = (self.gw.campaign / "hidden/dice_state.json").read_bytes()
        self.clock.expire(self.gw)
        self.gw.reroute(action["action_id"], "gpt")
        seen = {}
        def watch(move, context):
            seen["declaration"] = context["declaration"]
            return None
        out = run_turn(self.gw, script("gpt", watch), run="run-b")
        self.assertEqual(out["outcome"], "committed", out)
        self.assertEqual(seen["declaration"]["tb4"], tb4, "the successor sees the player's TB4 words unchanged")
        self.assertEqual(seen["declaration"]["whisper"], whisper, "and the private context, GM-side")
        self.assertEqual(self.rolls_for(action["action_id"]), rolls)
        self.assertEqual((self.gw.campaign / "hidden/dice_state.json").read_bytes(), dice)
        public = ledger.read_jsonl(self.gw.campaign / "records/events.jsonl")
        decls = [e for e in public if e["kind"] == "player_declaration" and e["details"]["action_id"] == action["action_id"]]
        self.assertEqual(len(decls), 1, "exactly one accepted declaration")
        self.assertEqual(decls[0]["details"]["declaration"]["tb4"], tb4)
        self.assertNotIn("whisper", decls[0]["details"]["declaration"])
        hidden = [e for e in ledger.read_jsonl(self.gw.campaign / "hidden/events.jsonl") if e["kind"] == "whisper_context"]
        self.assertEqual(len(hidden), 1)
        self.assertEqual(run_turn(self.gw, script("gpt"))["outcome"], "nothing", "nothing left to resolve twice")
        self.healthy()

    def test_whisper_post_turn_review_end_to_end(self):
        """Owner decisions 1-2: after a consequential committed turn the gateway proposes WHISPER candidates; the player's
        answer is recorded; only confirmed answers enter the private history; nothing reaches NPC knowledge."""
        (self.gw.campaign / "features.json").write_text(json.dumps({"switches": {"whisper_review": True, "whisper_context": True}}))
        def failed_rescue(move, context):
            if move["type"] == "commit":
                step = context["declaration"]["steps"][0]["id"]
                move["proposal"]["events"].append({"kind": "check_resolved", "actor": "aero", "summary": "Aero's reach falls short.",
                                                   "details": {"step_id": step, "actor": "aero", "act": "rescue", "target": "wick", "success": False}})
            return move
        self.gw.select_provider("claude")
        self.n += 1
        action = staging.declare(self.gw, f"stage-{self.n:04d}", text=INSPECT)
        action["declaration"]["whisper"] = {"schema": "genesis-whisper-context/1", "source": "player_explicit", "visibility": "pc_private",
                                             "felt_emotion": ["fear"], "expression": "unspecified", "motive": "save Wick", "reflection": None}
        self.gw.submit(action)
        self.assertEqual(run_turn(self.gw, script("claude", failed_rescue))["outcome"], "committed")
        out = self.gw.whisper("review", action_id=action["action_id"])
        self.assertEqual(out["recorded"], "whisper_review")
        self.assertEqual(self.gw.whisper("review", action_id=action["action_id"])["recorded"], None, "reviewed once only")
        state = self.gw.public_state()["state"]
        pend = state["whisper"]["pending"]
        cand = pend["candidates"][0]
        self.assertIn("save Wick", cand["explanation"], "the motive came from the GM-side context, not the public ledger")
        self.assertNotIn("save Wick", json.dumps([e for e in ledger.read_jsonl(self.gw.campaign / "records/events.jsonl") if e["kind"] == "player_declaration"]))
        with self.assertRaises(Refused):
            self.gw.whisper("respond", review_id=pend["review_id"], candidate_id=cand["candidate_id"], choice="edit", text="")
        self.gw.whisper("respond", review_id=pend["review_id"], candidate_id=cand["candidate_id"], choice="defer")
        self.assertIsNotNone(self.gw.public_state()["state"]["whisper"]["pending"], "defer keeps it open")
        self.gw.whisper("respond", review_id=pend["review_id"], candidate_id=cand["candidate_id"], choice="edit",
                        text="He replays the moment his fingers closed on nothing.")
        st = self.gw.public_state()["state"]["whisper"]
        self.assertIsNone(st["pending"])
        self.assertEqual([h["text"] for h in st["history"]], ["He replays the moment his fingers closed on nothing."])
        sys.path.insert(0, str(ROOT / "development/whisper"))
        import evidence
        envs = evidence.envelopes(ledger.read_jsonl(self.gw.campaign / "records/events.jsonl"))
        self.assertFalse([x for x in evidence.knows(envs, "wick") if x["type"] == "intention"], "NPCs never get WHISPER")
        (self.gw.campaign / "features.json").write_text(json.dumps({"switches": {}}))
        with self.assertRaises(Refused):
            self.gw.whisper("review", action_id=action["action_id"])
        self.healthy()

    def test_npc_knowledge_view_is_actor_scoped(self):
        """Owner decision 3: the GM's NPC context holds only what each NPC witnessed, heard or was part of;
        claims stay claims; no player WHISPER context; no GM-only fact the NPC was not part of. Switch off: absent."""
        def seeded(move, context):
            if move["type"] == "commit":
                move["proposal"]["events"] += [
                    {"kind": "speech", "actor": "orren", "summary": "Orren: 'Wick took the crates.'", "knowledge_type": "report",
                     "known_to": ["wick", "aero"], "details": {"speaker": "orren", "subject": "wick", "predicate": "took", "object": "crates", "channel": "heard"}},
                    {"kind": "world_fact", "visibility": "gm_only", "actor": "gm", "summary": "Kesh actually took the crates.",
                     "known_to": ["kesh"], "details": {"subject": "kesh", "predicate": "took", "object": "crates"}}]
            return move
        self.gw.select_provider("claude")
        self.n += 1
        action = staging.declare(self.gw, f"stage-{self.n:04d}", text=INSPECT)
        action["declaration"]["whisper"] = {"schema": "genesis-whisper-context/1", "source": "player_explicit", "visibility": "pc_private",
                                             "felt_emotion": ["anger"], "expression": {"style": "masked", "text": "polite"}, "motive": "PRIVATE_MOTIVE_CANARY", "reflection": None}
        self.gw.submit(action)
        self.assertEqual(run_turn(self.gw, script("claude", seeded))["outcome"], "committed")
        self.act(INSPECT)
        self.gw.claim("claude", "run-k")
        self.assertNotIn("npc_knowledge", self.gw.context("claude", "run-k"), "switch off: no NPC view")
        self.gw.release("claude", "run-k", "test")
        (self.gw.campaign / "features.json").write_text(json.dumps({"switches": {"npc_knowledge": True}}))
        self.gw.claim("claude", "run-k2")
        view = self.gw.context("claude", "run-k2")["npc_knowledge"]["by_npc"]
        wick = view.get("wick", [])
        claims = [x for x in wick if x["type"] == "claim"]
        self.assertTrue(claims and "Wick took the crates" in claims[0]["summary"] and claims[0]["provenance"] == "speaker:orren", wick)
        self.assertFalse([x for x in wick if x["type"] == "fact" and "Kesh" in x["summary"]], "no GM-only fact Wick was not part of")
        self.assertIn("Kesh actually took the crates.", [x["summary"] for x in view.get("kesh", [])], "Kesh knows what he did")
        self.assertNotIn("PRIVATE_MOTIVE_CANARY", json.dumps(view), "the player's WHISPER context never reaches an NPC")
        self.assertNotIn("anger", json.dumps(view))
        self.gw.release("claude", "run-k2", "test")
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


class RecoveryAfterRelease(Base):
    """Giving the lease back at any point keeps what was accepted and never authorizes a reroll."""

    def drive(self, provider, run, stop_before):
        """Play the scripted GM by hand until just before `stop_before` (tables | rolls | commit)."""
        self.gw.claim(provider, run, {"kind": "scripted", "mock": True})
        gm = script(provider)
        while True:
            context = self.gw.context(provider, run)
            move = gm.step(context)
            if move["type"] == stop_before:
                return move, context
            if move["type"] == "tables":
                self.gw.fix_tables(provider, run, move["tables"])
            elif move["type"] == "rolls":
                for request in move["rolls"]:
                    self.gw.roll(provider, run, request)

    def test_release_after_tables_fixed(self):
        action, _ = self.act(INSPECT, provider="claude")
        cursor = self.gw.public_state()["cursor"]
        nothing = self.gw.mechanical(action["action_id"])
        self.drive("claude", "run-a", "rolls")
        self.gw.release("claude", "run-a", "handing over")
        recovery = self.gw.recovery()
        self.assertEqual(self.gw.public_state()["cursor"], cursor, "the revision does not move when tables are fixed")
        mechanical = recovery["in_flight"]["mechanical"]
        self.assertEqual((mechanical["tables_fixed"], mechanical["rolls_accepted"], mechanical["batch_accepted"]), (True, 0, False))
        self.assertNotEqual(mechanical["fingerprint"], nothing["fingerprint"], "mechanical work must be visible although the revision is unchanged")
        self.assertEqual((recovery["in_flight"]["phase"], recovery["lease"]["held"], recovery["in_flight"]["reroute_allowed"]), ("resolve", False, True))
        self.gw.reroute(action["action_id"], "gpt")
        self.gw.claim("gpt", "run-b")
        context = self.gw.context("gpt", "run-b")
        self.assertIn("claude private table", context["operation"]["tables"]["tables"])
        for attempt, code in ((lambda: self.gw.fix_tables("gpt", "run-b", {"interpretation": "fresh start"}), "TABLES_FIXED"),
                              (lambda: self.gw.review("gpt", "run-b", {"summary": "s", "errors": [{"code": "HANDS", "message": "m"}]}), "TOO_LATE_FOR_REVIEW")):
            with self.assertRaises(Refused) as caught:
                attempt()
            self.assertEqual(caught.exception.code, code)
        self.gw.release("gpt", "run-b")
        self.assertEqual(self.gw.mechanical(action["action_id"])["fingerprint"], mechanical["fingerprint"], "a release changes nothing that was accepted")
        self.gw.reroute(action["action_id"], "claude")
        out = run_turn(self.gw, script("claude"))
        self.assertEqual((out["outcome"], out["moves"]), ("committed", ["rolls", "commit"]))

    def test_release_after_dice_accepted(self):
        action, _ = self.act(INSPECT, provider="gemini")
        cursor = self.gw.public_state()["cursor"]
        self.drive("gemini", "run-a", "commit")
        rolls = self.rolls_for(action["action_id"])
        dice = (self.gw.campaign / "hidden/dice_state.json").read_bytes()
        self.gw.release("gemini", "run-a")
        self.assertEqual(self.gw.public_state()["cursor"], cursor, "the revision does not move when dice are accepted")
        mechanical = self.gw.mechanical(action["action_id"])
        self.assertEqual((mechanical["tables_fixed"], mechanical["rolls_accepted"]), (True, 1))
        self.assertEqual(self.gw.action_status(action["action_id"])["mechanical"], mechanical)
        for provider, run in (("claude", "run-b"), ("gpt", "run-c"), ("gemini", "run-d")):      # every later run, own or foreign
            self.gw.reroute(action["action_id"], provider)
            self.gw.claim(provider, run)
            step = action["declaration"]["steps"][0]["id"]
            again = self.gw.roll(provider, run, {"roll_key": "second-try", "step_id": step, "formula": "1d20+3", "kind": "check",
                                                 "requested_by": "aero", "purpose": "Aero studies the remote again", "dc": 12})
            self.assertTrue(again["replayed"])
            self.assertEqual(again["result"]["roll_id"], rolls[0]["roll_id"])
            self.gw.release(provider, run)
        self.assertEqual(self.rolls_for(action["action_id"]), rolls)
        self.assertEqual((self.gw.campaign / "hidden/dice_state.json").read_bytes(), dice)
        self.assertEqual(self.gw.mechanical(action["action_id"]), mechanical)
        out = run_turn(self.gw, script("gemini"))
        self.assertEqual((out["outcome"], out["moves"]), ("committed", ["commit"]))
        self.assertEqual(self.rolls_for(action["action_id"]), rolls)
        self.healthy()

    def test_release_after_ledger_batch_accepted(self):
        action, _ = self.act(INSPECT, provider="gpt")
        cursor = self.gw.public_state()["cursor"]
        move, _ = self.drive("gpt", "run-a", "commit")
        real = gateway_module.batch.apply
        gateway_module.batch.apply = lambda c, r, l, run, led, after_stream=None: real(
            c, r, l, run, led, after_stream=lambda _: (_ for _ in ()).throw(RuntimeError("power lost")))
        try:
            with self.assertRaises(RuntimeError):
                self.gw.commit("gpt", "run-a", move["proposal"])
        finally:
            gateway_module.batch.apply = real
        self.gw.release("gpt", "run-a", "stopping after a crash")
        recovery = self.gw.recovery()
        self.assertTrue(recovery["record_mid_write"])
        mechanical = recovery["in_flight"]["mechanical"]
        self.assertEqual((mechanical["batch_accepted"], mechanical["batch_committed"], recovery["in_flight"]["phase"]), (True, False, "publish"))
        accepted = self.gw._op(action["action_id"])["commit"]["fingerprint"]
        self.gw.reroute(action["action_id"], "gemini")
        with self.assertRaises(Refused) as caught:
            self.gw.claim("gemini", "run-b") and self.gw.fix_tables("gemini", "run-b", {"interpretation": "again"})
        self.assertEqual(caught.exception.code, "ALREADY_COMMITTED")
        with self.assertRaises(Refused) as caught:
            self.gw.roll("gemini", "run-b", {"roll_key": "z", "formula": "1d20", "kind": "other", "requested_by": "gm", "purpose": "another die"})
        self.assertEqual(caught.exception.code, "ALREADY_COMMITTED")
        self.gw.release("gemini", "run-b")
        out = run_turn(self.gw, script("gemini", lambda m, c: self.fail("an accepted batch is finished, not re-authored")))
        self.assertEqual((out["outcome"], out["authored"]), ("committed", False))
        self.assertEqual(self.gw._op(action["action_id"])["commit"]["fingerprint"], accepted)
        self.assertTrue(self.narration().startswith("[gpt]"), "the committed text is the one the batch accepted")
        self.assertGreater(self.gw.public_state()["cursor"]["revision"], cursor["revision"])
        self.assertEqual(len(self.rolls_for(action["action_id"])), 1)
        self.healthy()

    def test_publication_pending_needs_no_gm_and_survives_release(self):
        action, _ = self.act(INSPECT, provider="claude")
        real = self.gw.store.put
        self.gw.store.put = lambda key, data, expected: (_ for _ in ()).throw(ValueError("snapshot refused")) if key == "view/state" else real(key, data, expected)
        try:
            self.assertEqual(run_turn(self.gw, script("claude"))["outcome"], "resolved_unpublished")
        finally:
            self.gw.store.put = real
        recovery = self.gw.recovery()
        self.assertEqual((recovery["in_flight"]["status"], recovery["in_flight"]["phase"], recovery["lease"]["held"]), ("resolved", "publish", False))
        self.assertTrue(recovery["in_flight"]["mechanical"]["batch_committed"])
        self.assertFalse(recovery["in_flight"]["reroute_allowed"])
        with self.assertRaises(Refused) as caught:
            self.gw.reroute(action["action_id"], "gpt")
        self.assertEqual(caught.exception.code, "NOT_REROUTABLE")
        head = ledger.load_all(self.gw.campaign)[-1]["event_id"]
        self.gw.claim("gpt", "run-b")
        for attempt in (lambda: self.gw.fix_tables("gpt", "run-b", {"interpretation": "again"}),
                        lambda: self.gw.fail("gpt", "run-b", "give up")):
            with self.assertRaises(Refused) as caught:
                attempt()
            self.assertEqual(caught.exception.code, "ALREADY_COMMITTED")
        self.gw.release("gpt", "run-b")                                    # a release while publication is pending
        self.assertEqual(self.gw.action_status(action["action_id"])["status"], "resolved")
        self.assertEqual(run_turn(self.gw, script("gemini"))["outcome"], "committed")
        self.assertEqual(ledger.load_all(self.gw.campaign)[-1]["event_id"], head)
        self.assertEqual(len(self.rolls_for(action["action_id"])), 1)
        self.assertIsNone(self.gw.recovery()["in_flight"])


class EncounterThroughTheGateway(Base):
    """The gateway holds every provider to initiative order and per-actor budgets, and publishes the tracker."""

    PARTICIPANTS = [
        {"actor_id": "aero", "label": "Aero", "side": "party", "initiative": 21, "control": {"decides": "player"}},
        {"actor_id": "ally", "label": "The ally", "side": "party", "initiative": 12, "control": {"decides": "gm"}},
        {"actor_id": "lurker_1", "label": "HIDDEN_LURKER_ONE", "side": "foe", "initiative": 7, "group": "lurkers", "hidden": True, "control": {"decides": "gm"}},
        {"actor_id": "lurker_2", "label": "HIDDEN_LURKER_TWO", "side": "foe", "initiative": 7, "group": "lurkers", "hidden": True, "control": {"decides": "gm"}}]

    def gm(self, name, extra):
        def add(move, context):
            if move["type"] == "commit":
                step = context["declaration"]["steps"][0]["id"]
                move["proposal"]["events"] = [e for e in move["proposal"]["events"]] + extra(step)
            return move
        return script(name, add)

    @staticmethod
    def e(kind, **details):
        return {"kind": kind, "summary": kind, "visibility": "gm_only" if details.pop("_private", False) else "player", "details": details}

    def test_order_budgets_and_public_tracker(self):
        e = self.e
        opening = lambda step: [e("encounter_start", encounter_id="staging-fight", mode="combat", participants=self.PARTICIPANTS),
                                e("turn_start", actor_id="aero"), e("resource_spent", actor_id="aero", resource="object_interaction", **{"for": step})]
        self.act(HOLSTER, provider="claude")
        self.assertEqual(run_turn(self.gw, self.gm("claude", opening))["outcome"], "committed")
        state = self.gw.public_state()["state"]
        tracker = state["turn_context"]["encounter"]
        self.assertEqual((tracker["mode"], tracker["round"], tracker["current"], tracker["next"]), ("combat", 1, "Aero", "The ally"))
        self.assertEqual([s["label"] for s in tracker["order"]], ["Aero", "The ally", "Others you cannot see"])
        self.assertEqual(tracker["order"][0]["budget"]["object_interaction"], 0)
        self.assertNotIn("HIDDEN_LURKER", json.dumps(self.gw.public_state()) + json.dumps([self.gw.store.read(k)[1] for k in self.gw.store.keys("view/")]))
        # A second provider continues the same turn. It may not let the ally act on Aero's turn, nor skip anyone.
        cases = {"ENCOUNTER_OFF_TURN": lambda step: [e("resource_spent", actor_id="ally", resource="action", **{"for": "acts on Aero's word"})],
                 "ENCOUNTER_OUT_OF_ORDER": lambda step: [e("turn_end", actor_id="aero"), e("turn_start", actor_id="lurker_1", _private=True)],
                 "ENCOUNTER_NO_BUDGET": lambda step: [e("resource_spent", actor_id="aero", resource="object_interaction")]}
        action, _ = self.act(INSPECT, provider="gpt")
        self.gw.claim("gpt", "run-x", {"kind": "scripted", "mock": True})
        good = script("gpt")
        while True:
            context = self.gw.context("gpt", "run-x")
            move = good.step(context)
            if move["type"] == "commit":
                break
            if move["type"] == "tables":
                self.gw.fix_tables("gpt", "run-x", move["tables"])
            else:
                for request in move["rolls"]:
                    self.gw.roll("gpt", "run-x", request)
        step = action["declaration"]["steps"][0]["id"]
        for code, extra in cases.items():
            proposal = copy.deepcopy(move["proposal"])
            proposal["events"] += extra(step)
            with self.assertRaises(Refused) as caught:
                self.gw.commit("gpt", "run-x", proposal)
            self.assertIn(code, [p["code"] for p in caught.exception.extra["problems"]], code)
        # The legal continuation: Aero spends his action and ends; the ally and both lurkers each take one turn.
        proposal = copy.deepcopy(move["proposal"])
        proposal["turn_context"]["encounter"] = {"mode": "scene", "order": []}          # a forged tracker is discarded, not trusted
        proposal["events"] += [e("resource_spent", actor_id="aero", resource="action", **{"for": step}), e("turn_end", actor_id="aero"),
                               e("turn_start", actor_id="ally"), e("ready_set", actor_id="ally", trigger="Aero says the word", does="one shot"), e("turn_end", actor_id="ally"),
                               e("turn_start", actor_id="lurker_1", _private=True), e("resource_spent", actor_id="lurker_1", resource="movement_ft", amount=30, _private=True), e("turn_end", actor_id="lurker_1", _private=True),
                               e("turn_start", actor_id="lurker_2", _private=True), e("turn_end", actor_id="lurker_2", _private=True),
                               e("turn_start", actor_id="aero")]
        try:
            status = self.gw.commit("gpt", "run-x", proposal)
        except Refused as refusal:
            self.fail(refusal.extra)
        self.assertEqual(status["status"], "committed")
        tracker = self.gw.public_state()["state"]["turn_context"]["encounter"]
        self.assertEqual((tracker["round"], tracker["current"], tracker["next"]), (2, "Aero", "The ally"))
        self.assertEqual(tracker["order"][1]["ready"], {"trigger": "Aero says the word", "does": "one shot"})
        self.assertEqual(tracker["order"][0]["budget"]["action"], 1)
        public = json.dumps(self.gw.public_state()) + json.dumps([self.gw.page(p) for p in self.gw.public_state()["pages"]])
        for secret in ("HIDDEN_LURKER", "lurker_1", "lurker_2"):
            self.assertNotIn(secret, public)
        # Mode change by a third provider, with a reason; initiative is suspended, nobody is removed.
        calm = lambda step: [e("resource_spent", actor_id="aero", resource="action", **{"for": step}), e("turn_end", actor_id="aero"),
                             e("encounter_mode", mode="standoff", reason="neither side can reach the other", cites=[])]
        self.act(INSPECT, provider="gemini")
        self.assertEqual(run_turn(self.gw, self.gm("gemini", calm))["outcome"], "committed")
        tracker = self.gw.public_state()["state"]["turn_context"]["encounter"]
        self.assertEqual((tracker["mode"], tracker["round"], tracker["decision"]["kind"]), ("standoff", None, "player"))
        self.healthy()


    def test_recruitment_and_control_are_owner_records_never_a_gm_proposal(self):
        """Wick-like ally: GM-run until the owner records a recruitment. A provider cannot recruit, hand over or take
        control inside a turn; the owner record is checked by the controller, republishes the tracker and rolls nothing."""
        e = self.e
        people = [{"actor_id": "aero", "label": "Aero", "side": "party", "role": "player_character", "initiative": 21, "control": {"decides": "player"}},
                  {"actor_id": "ally", "label": "The ally", "side": "party", "role": "allied_npc", "initiative": 12, "control": {"decides": "gm", "basis": "temporary ally"}},
                  {"actor_id": "foe", "label": "A foe", "side": "foe", "role": "npc", "initiative": 7}]
        opening = lambda step: [e("encounter_start", encounter_id="control-fight", mode="combat", participants=people),
                                e("turn_start", actor_id="aero"), e("resource_spent", actor_id="aero", resource="object_interaction", **{"for": step})]
        self.act(HOLSTER, provider="claude")
        self.assertEqual(run_turn(self.gw, self.gm("claude", opening))["outcome"], "committed")
        row = lambda: self.gw.public_state()["state"]["turn_context"]["encounter"]["order"][1]
        self.assertEqual((row()["role"], row()["control"]), ("allied_npc", "gm"))
        rolls_before = (self.gw.campaign / "records/roll_log.jsonl").read_bytes()
        # A GM provider tries to recruit him, or to make him player-directed, as part of resolving a turn: refused.
        action, _ = self.act(INSPECT, provider="gpt")
        self.gw.claim("gpt", "run-x", {"kind": "scripted", "mock": True})
        good = script("gpt")
        while True:
            move = good.step(self.gw.context("gpt", "run-x"))
            if move["type"] == "commit":
                break
            if move["type"] == "tables":
                self.gw.fix_tables("gpt", "run-x", move["tables"])
            else:
                for request in move["rolls"]:
                    self.gw.roll("gpt", "run-x", request)
        for sneaked in (e("party_joined", member_id="ally", name="The ally", basis="he helped Aero"),
                        e("control_changed", actor_id="ally", decides="player_directed", basis="Aero ordered him"),
                        e("party_left", member_id="ally", reason="the GM says so")):
            proposal = copy.deepcopy(move["proposal"])
            proposal["events"].append(sneaked)
            with self.assertRaises(Refused) as caught:
                self.gw.commit("gpt", "run-x", proposal)
            self.assertIn("RESERVED_KIND", [p["code"] for p in caught.exception.extra["problems"]])
        # Nor while a declaration is in flight, by anyone.
        with self.assertRaises(Refused) as caught:
            self.gw.owner_record("party_joined", {"member_id": "ally", "name": "The ally", "basis": "owner"})
        self.assertEqual(caught.exception.code, "TURN_IN_FLIGHT")
        step = action["declaration"]["steps"][0]["id"]
        proposal = copy.deepcopy(move["proposal"])
        proposal["events"] += [e("resource_spent", actor_id="aero", resource="action", **{"for": step}), e("turn_end", actor_id="aero")]
        self.assertEqual(self.gw.commit("gpt", "run-x", proposal)["status"], "committed")
        self.assertEqual(self.gw.public_state()["state"]["turn_context"]["encounter"]["decision"], {"kind": "gm", "actor_id": "ally", "control": "gm"})
        # Without recruitment he cannot be handed to the player; with it, he is player-directed by default.
        for kind, details, code in (("control_changed", {"actor_id": "ally", "decides": "player_directed", "basis": "owner"}, "RECORD_REFUSED"),
                                    ("party_joined", {"member_id": "ally", "name": "The ally"}, "BAD_RECORD"),
                                    ("encounter_mode", {"mode": "scene", "reason": "x", "basis": "x"}, "BAD_RECORD")):
            with self.assertRaises(Refused) as caught:
                self.gw.owner_record(kind, details)
            self.assertEqual(caught.exception.code, code)
        before = self.gw.public_state()["cursor"]["revision"]
        done = self.gw.owner_record("party_joined", {"member_id": "ally", "name": "The ally", "basis": "the player asked him to join and he agreed (owner record)"})
        self.assertEqual((row()["role"], row()["control"]), ("party_member", "player_directed"))
        state = self.gw.public_state()
        self.assertGreater(state["cursor"]["revision"], before)
        self.assertEqual(state["state"]["turn_context"]["encounter"]["decision"], {"kind": "player", "actor_id": "ally", "control": "player_directed"})
        self.assertEqual(done["recorded"], "party_joined")
        self.gw.owner_record("control_changed", {"actor_id": "ally", "decides": "gm", "basis": "the player asks the GM to run him for now"})
        self.assertEqual((row()["role"], row()["control"]), ("party_member", "gm"))
        self.gw.owner_record("party_left", {"member_id": "ally", "reason": "he goes home"})
        self.assertEqual((row()["role"], row()["control"]), ("allied_npc", "gm"))
        self.assertEqual(len(ledger.read_jsonl(self.gw.campaign / "records/roll_log.jsonl")), len(rolls_before.splitlines()) + 1, "only the one declared check was rolled")
        self.assertEqual(len([r for r in ledger.read_jsonl(self.gw.campaign / "records/roll_log.jsonl") if "owner" in r.get("purpose", "")]), 0)
        self.assertIsNone(self.gw.recovery()["in_flight"])
        self.healthy()


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

    FIGHT = [{"actor_id": "aero", "label": "Aero", "side": "party", "role": "player_character", "initiative": 21, "control": {"decides": "player"}},
             {"actor_id": "wick", "label": "Wick", "side": "party", "role": "allied_npc", "initiative": 12, "control": {"decides": "gm", "basis": "temporary ally, not recruited"}},
             {"actor_id": "foe_1", "label": "First foe", "side": "foe", "role": "npc", "initiative": 7, "group": "foes", "control": {"decides": "gm"}},
             {"actor_id": "foe_2", "label": "HIDDEN_FOE_TWO", "side": "foe", "role": "npc", "initiative": 7, "group": "foes", "hidden": True, "control": {"decides": "gm"}}]

    def open_fight(self):
        e = EncounterThroughTheGateway.e
        opening = lambda step: [e("encounter_start", encounter_id="dice-fight", mode="combat", participants=self.FIGHT),
                                e("turn_start", actor_id="aero"), e("resource_spent", actor_id="aero", resource="object_interaction", **{"for": step})]
        self.act(HOLSTER, provider="claude")
        self.assertEqual(run_turn(self.gw, EncounterThroughTheGateway.gm(self, "claude", opening))["outcome"], "committed")

    def test_each_creature_has_its_own_roll_subject_and_npc_turn_provenance(self):
        """X1 and X2 (COMPATIBILITY_AND_ADOPTION.md §6), corrected in the existing engine. Two creatures rolled by the GM
        each make the same kind of roll in one action, each on its own turn, citing no player step. Accepted-roll identity
        and no-reroll hold per creature. Only the player character's own d20 is transformed by Heroic."""
        e = EncounterThroughTheGateway.e
        self.open_fight()
        action, _ = self.act(INSPECT, provider="claude", settings={"temperature": "heroic", "narrative_consequences": True})
        self.gw.claim("claude", "run-a", {"kind": "scripted", "mock": True})
        self.gw.fix_tables("claude", "run-a", {"interpretation": "Aero studies the remote; then each foe takes its own turn.", "tables": "none"})
        step = action["declaration"]["steps"][0]["id"]
        own = self.gw.roll("claude", "run-a", {"roll_key": f"{step}.check", "step_id": step, "formula": "1d20+3", "kind": "check", "requested_by": "aero",
                                              "purpose": "Aero studies the remote", "dc": 12})["result"]
        npc = lambda key, subject, by="gm", **more: self.gw.roll("claude", "run-a", dict({"roll_key": key, "formula": "1d20+4", "kind": "attack", "requested_by": by,
                                                              "purpose": "A foe attacks", "dc": 13, "subject": subject, "provenance": {"kind": "gm_turn", "actor_id": subject}}, **more))
        one = npc("npc_a.attack", "foe_1")
        two = npc("npc_b.attack", "foe_2", by="gm_hidden")
        self.assertFalse(one["replayed"] or two["replayed"])
        self.assertNotEqual(one["result"]["roll_id"], two["result"]["roll_id"])
        # No reroll: the same request again, and the same creature under a new key, both return the accepted roll.
        self.assertEqual(npc("npc_a.attack", "foe_1")["result"]["roll_id"], one["result"]["roll_id"])
        again = npc("npc_a.attack_retry", "foe_1")
        self.assertTrue(again["replayed"])
        self.assertEqual(again["result"]["roll_id"], one["result"]["roll_id"])
        self.assertEqual(len(self.rolls_for(action["action_id"])), 3)
        # Refused: a subject on the player character's own roll; a creature that is not in the encounter; mismatched or mixed provenance.
        for bad in ({"roll_key": "x1", "step_id": step, "formula": "1d20+3", "kind": "check", "requested_by": "aero", "purpose": "again", "subject": "aero"},
                    {"roll_key": "x2", "formula": "1d20", "kind": "attack", "requested_by": "gm", "purpose": "a stranger", "subject": "nobody", "provenance": {"kind": "gm_turn", "actor_id": "nobody"}},
                    {"roll_key": "x3", "formula": "1d20", "kind": "attack", "requested_by": "gm", "purpose": "mismatch", "subject": "foe_1", "provenance": {"kind": "gm_turn", "actor_id": "foe_2"}},
                    {"roll_key": "x4", "step_id": step, "formula": "1d20", "kind": "save", "requested_by": "gm", "purpose": "both", "subject": "foe_1", "provenance": {"kind": "gm_turn", "actor_id": "foe_1"}},
                    {"roll_key": "x5", "formula": "1d20", "kind": "attack", "requested_by": "gm", "purpose": "for the player", "subject": "aero", "provenance": {"kind": "gm_turn", "actor_id": "aero"}}):
            with self.assertRaises(Refused) as caught:
                self.gw.roll("claude", "run-a", bad)
            self.assertEqual(caught.exception.code, "BAD_ROLL", bad["roll_key"])
        self.assertEqual(len(self.rolls_for(action["action_id"])), 3)
        # Dice treatment: only Aero's own d20 is Heroic with a narrative axis; both creatures are Regular with none.
        self.assertEqual((own["resolution"]["eligible"], own["resolution"]["roll"]["temperature"], own["resolution"]["narrative"] is not None), (True, "heroic", True))
        for theirs in (one, two):
            r = theirs["result"]["resolution"]
            self.assertEqual((r["eligible"], r["roll"]["temperature"], r["narrative"], r["roll"]["effective_d20"]), (False, "regular", None, None))
        # Provenance: the public roll log names the step for Aero and only "gm_turn" for the creatures; which creature is private.
        log = {r["roll_id"]: r for r in self.rolls_for(action["action_id"])}
        self.assertEqual(log[own["roll_id"]]["resolution_provenance"], {"action_id": action["action_id"], "step_id": step, "roll_key": f"{step}.check"})
        for theirs, key in ((one, "npc_a.attack"), (two, "npc_b.attack")):
            self.assertEqual(log[theirs["result"]["roll_id"]]["resolution_provenance"], {"action_id": action["action_id"], "step_id": None, "roll_key": key, "source": "gm_turn"})
        private = {r["roll_id"]: r["request"] for r in ledger.read_jsonl(self.gw.campaign / "hidden/experimental_resolution_log.jsonl")}
        self.assertEqual([private[t["result"]["roll_id"]]["subject"] for t in (one, two)], ["foe_1", "foe_2"])
        self.assertNotIn("foe_2", (self.gw.campaign / "records/roll_log.jsonl").read_text())
        # Commit: the creatures' rolls must sit in their own turns, cited by their own events.
        base = {"world_time": "Staging", "narration": "You study the remote. Something strikes at you from the dark.", "scene_state": {"summary": "s", "title": "t", "location": "l", "atmosphere": []},
                "turn_context": {k: v for k, v in self.gw.public_state()["state"]["turn_context"].items() if k not in ("context_id", "encounter", "equipment")}}
        mine = [{"kind": "observation", "actor": "aero", "summary": "Aero studies the remote", "details": {"step_id": step}, "roll_keys": [f"{step}.check"]},
                e("resource_spent", actor_id="aero", resource="action", **{"for": step}), e("turn_end", actor_id="aero"),
                e("turn_start", actor_id="wick"), e("turn_end", actor_id="wick")]
        hit = lambda actor, key, private=False: dict(e("attack_resolved", actor_id=actor, _private=private), actor=actor, roll_keys=[key])
        turns = [e("turn_start", actor_id="foe_1"), e("resource_spent", actor_id="foe_1", resource="action"), hit("foe_1", "npc_a.attack"), e("turn_end", actor_id="foe_1"),
                 e("turn_start", actor_id="foe_2", _private=True), e("resource_spent", actor_id="foe_2", resource="action", _private=True), hit("foe_2", "npc_b.attack", True), e("turn_end", actor_id="foe_2", _private=True),
                 e("turn_start", actor_id="aero")]
        wrong_actor = [dict(x, actor="foe_1") if x.get("roll_keys") == ["npc_b.attack"] else x for x in turns]
        no_turn = [hit("foe_1", "npc_a.attack"), hit("foe_2", "npc_b.attack", True)]
        for events in (mine + no_turn, mine + wrong_actor):
            with self.assertRaises(Refused) as caught:
                self.gw.commit("claude", "run-a", dict(base, events=events))
            self.assertIn("NPC_ROLL_PROVENANCE", [p["code"] for p in caught.exception.extra["problems"]])
        try:
            status = self.gw.commit("claude", "run-a", dict(base, events=mine + turns))
        except Refused as refusal:
            self.fail(refusal.extra)
        self.assertEqual(status["status"], "committed")
        tracker = self.gw.public_state()["state"]["turn_context"]["encounter"]
        self.assertEqual((tracker["round"], tracker["current"]), (2, "Aero"))
        self.assertNotIn("HIDDEN_FOE_TWO", json.dumps(self.gw.public_state()))
        self.assertTrue(gateway_module.engine.replay(self.gw.campaign)["ok"])
        self.healthy()

    def test_rolls_without_a_subject_keep_their_accepted_identity(self):
        """The slot of a request that names no subject is byte-identical to the inspected engine's, so nothing accepted
        before the correction can be rerolled after it, and a legacy second GM roll for the same step and kind is still refused."""
        engine = gateway_module.engine
        legacy = lambda action_id, request, actor: [action_id, request.get("step_id"), request.get("kind"), request.get("requested_by", actor)]
        for request in ({"step_id": "k0", "kind": "check", "requested_by": "aero"}, {"step_id": "k0", "kind": "attack", "requested_by": "gm"}, {"step_id": "k1", "kind": "save"}):
            self.assertEqual(engine.slot_identity("act-1", {"actor": "aero"}, request), legacy("act-1", request, "aero"))
        action, _ = self.act(INSPECT, provider="claude")
        self.gw.claim("claude", "run-a", {"kind": "scripted", "mock": True})
        self.gw.fix_tables("claude", "run-a", {"interpretation": "two unnamed rolls", "tables": "none"})
        step = action["declaration"]["steps"][0]["id"]
        ask = lambda key: self.gw.roll("claude", "run-a", {"roll_key": key, "step_id": step, "formula": "1d20+4", "kind": "attack", "requested_by": "gm", "purpose": key})
        ask("unnamed_one.attack")
        with self.assertRaises(Refused) as caught:
            ask("unnamed_two.attack")
        self.assertEqual(caught.exception.code, "DICE_REFUSED")
        self.assertEqual(len(self.rolls_for(action["action_id"])), 1)

    def test_a_companion_roll_is_never_treated_as_the_players(self):
        """Heroic and Narrative Consequences are the player's choice for the player character's own d20s. An ally
        acting on the player's word, in an encounter where the ally is even marked player-directed, still rolls
        through the GM and stays Regular with no narrative axis. Beginning an encounter changes no dice setting."""
        e = EncounterThroughTheGateway.e
        self.open_fight()
        # Even a formally recruited, player-directed companion: tactical control is not dice eligibility (decision D3).
        self.gw.owner_record("party_joined", {"member_id": "wick", "name": "Wick", "basis": "test: recruited on the record"})
        self.assertEqual(self.gw.public_state()["state"]["turn_context"]["encounter"]["order"][1]["control"], "player_directed")
        action, _ = self.act(INSPECT, provider="claude", settings={"temperature": "heroic", "narrative_consequences": True})
        self.gw.claim("claude", "run-a", {"kind": "scripted", "mock": True})
        self.gw.fix_tables("claude", "run-a", {"interpretation": "Aero studies the remote; on his word the ally takes a shot at it.", "tables": "none"})
        step = action["declaration"]["steps"][0]["id"]
        own = self.gw.roll("claude", "run-a", {"roll_key": f"{step}.check", "step_id": step, "formula": "1d20+3", "kind": "check", "requested_by": "aero",
                                              "purpose": "Aero studies the remote", "dc": 12})["result"]["resolution"]
        theirs = self.gw.roll("claude", "run-a", {"roll_key": "ally", "step_id": step, "formula": "1d20+2", "kind": "attack", "requested_by": "gm",
                                                 "purpose": "The ally fires on Aero's word", "dc": 12, "subject": "wick"})["result"]["resolution"]
        self.assertEqual((own["eligible"], own["roll"]["temperature"], own["narrative"] is not None), (True, "heroic", True))
        self.assertEqual((theirs["eligible"], theirs["roll"]["temperature"], theirs["narrative"]), (False, "regular", None))
        self.assertIsNone(theirs["roll"]["effective_d20"])
        with self.assertRaises(Refused) as caught:                    # nobody can ask for a roll "as" the ally to borrow the player's mode
            self.gw.roll("claude", "run-a", {"roll_key": "x", "step_id": step, "formula": "1d20+2", "kind": "attack", "requested_by": "wick", "purpose": "as the ally"})
        self.assertEqual(caught.exception.code, "BAD_ROLL")
        context = self.gw.context("claude", "run-a")
        move = script("claude").step(context)
        move["proposal"]["events"] += [{"kind": "attack_resolved", "actor": "gm", "summary": "The ally fires and misses.", "details": {"npc": "wick"}, "roll_keys": ["ally"]}]
        self.assertEqual(self.gw.commit("claude", "run-a", move["proposal"])["status"], "committed")
        declared = [x for x in ledger.load_all(self.gw.campaign) if x["kind"] == "player_declaration"][-1]["details"]
        self.assertEqual(declared["resolution_settings"], {"temperature": "heroic", "narrative_consequences": True}, "the submitted settings are immutable")
        # The next action, now inside an encounter, defaults to Regular / Off: initiative selects nothing.
        nxt, _ = self.act(INSPECT, provider="claude")
        self.assertEqual(self.gw.store.read("actions/" + nxt["action_id"])[1]["resolution_settings"], gateway_module.policy.DEFAULT)
        tracker = self.gw.public_state()["state"]["turn_context"]["encounter"]
        self.assertEqual((tracker["mode"], tracker["order"][1]["control"]), ("combat", "player_directed"))
        self.assertNotIn("temperature", json.dumps(tracker))
        self.assertTrue(gateway_module.engine.replay(self.gw.campaign)["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
