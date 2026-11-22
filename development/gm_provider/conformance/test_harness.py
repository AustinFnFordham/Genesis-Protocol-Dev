"""Deterministic tests of the benchmark itself. No network or campaign dependencies."""
import copy
import json
import unittest

from jsonschema import Draft202012Validator
from harness import FIXTURES, SCHEMA, fixture_phase, load, phase_schema, run_case, score, summarize

CASES = {c["id"]: c for c in load(FIXTURES)}
SCHEMA_VALUE = load(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA_VALUE)
TABLES = {"type": "tables", "tables": {"interpretation": "Holster the pistol and free the left hand.",
                                      "tables": "No roll required.", "npc_evaluations": []}}


def proposal(case):
    rule = case["expect"]
    event = {"kind": rule["event_kinds"][0], "summary": "Observed result.", "actor": "zara",
             "visibility": "public", "details": {"step_id": "s1"},
             "roll_keys": list(case["context"]["operation"]["rolls"])}
    ctx = dict(case["context"]["public_context"])
    ctx.update(equipment_from_ledger=True, objects=[], movement=[], reactions=[], visible=[],
               dialogue=[{"id": a, "approach": a, "text": "What next?"} for a in ("wry", "curious", "plain")])
    if rule.get("pending"):
        ctx.update(pending_steps=rule["pending"], pending_reason="The wax seal has not been checked.")
    text = "You holster the pistol, freeing your left hand." if rule.get("pending") else "The seal remains unreadable."
    return {"type": "commit", "proposal": {"world_time": "Later", "events": [event], "narration": text,
                                           "scene_state": {"summary": "Quiet", "title": "Dock",
                                                           "location": "Pier", "atmosphere": []},
                                           "turn_context": ctx}}


class Conformance(unittest.TestCase):
    def check(self, move, case):
        return score(json.dumps(move), CASES[case], VALIDATOR)

    def test_schema_and_routine_noop_npc_rejection(self):
        Draft202012Validator.check_schema(SCHEMA_VALUE)
        self.assertEqual(self.check(TABLES, "routine-holster"), [])
        move = copy.deepcopy(TABLES)
        move["tables"]["npc_evaluations"] = [{"action": "none"}]
        self.assertTrue(self.check(move, "routine-holster")[0].startswith("SCHEMA"))

    def test_duplicate_and_non_string_type(self):
        self.assertTrue(score('{"type":"review","type":"tables"}', CASES["routine-holster"], VALIDATOR)[0].startswith("JSON"))
        self.assertTrue(self.check({"type": []}, "routine-holster"))

    def test_adversarial_review_rejects_wrong_code_alternatives_and_leaks(self):
        move = {"type": "review", "review": {"summary": "No.", "errors": [{"code": "HANDS", "message": "No."}],
                                           "warnings": [], "alternatives": [{"label": "Invented", "declaration": {}}]}}
        self.assertEqual({e.split(":")[0] for e in self.check(move, "unlearned-power")}, {"MECHANICS", "AGENCY"})

    def test_npc_causal_evaluation(self):
        move = {"type": "tables", "tables": {"interpretation": "Admit the courier with the valid permit.",
                                             "tables": "No roll required.", "npc_evaluations": [{
            "npc": "g1", "since": None, "changes": ["fixture_evt_7"], "no_change_reason": None,
            "outcome_key": "admit", "repeat_reason": None, "basis": "Valid permit per orders."}]}}
        self.assertEqual(self.check(move, "npc-motive"), [])
        move["tables"]["npc_evaluations"][0]["changes"] = []
        self.assertTrue(self.check(move, "npc-motive")[0].startswith("NPC"))

    def test_roll_fabrication_and_repeat(self):
        roll = CASES["request-roll"]["expect"]["roll"] | {"purpose": "Inspect the seal."}
        move = {"type": "rolls", "rolls": [roll]}
        self.assertEqual(self.check(move, "request-roll"), [])
        roll["result"] = 20
        self.assertTrue(self.check(move, "request-roll")[0].startswith("SCHEMA"))
        del roll["result"]
        self.assertTrue(self.check(move, "receipt-and-secret")[0].startswith("PHASE"))

    def test_commit_receipt_binding_and_hidden_canary(self):
        move = proposal(CASES["receipt-and-secret"])
        self.assertEqual(self.check(move, "receipt-and-secret"), [])
        payload = move["proposal"]
        payload["events"][0]["roll_keys"] += ["s1.check", "invented"]
        payload["narration"] += " BLUE QUARANTINE."
        self.assertEqual({e.split(":")[0] for e in self.check(move, "receipt-and-secret")}, {"SECRECY", "RECEIPT"})

    def test_commit_preserves_pending_declaration(self):
        move = proposal(CASES["choice-stop"])
        self.assertEqual(self.check(move, "choice-stop"), [])
        move["proposal"]["turn_context"]["pending_steps"] = []
        self.assertTrue(self.check(move, "choice-stop")[0].startswith("CONTINUITY"))

    def test_phase_schema_is_derived_from_state_and_reused_on_repair(self):
        for case in CASES.values():
            phase = fixture_phase(case["context"])
            self.assertEqual(phase, case["expect"]["type"])
            branch = phase_schema(SCHEMA_VALUE, phase)
            for other in ("review", "tables", "rolls", "commit"):
                if other != phase:
                    self.assertFalse(Draft202012Validator(branch).is_valid({"type": other}))
        calls = []
        def generate(messages, fmt):
            calls.append(fmt)
            return {"message": {"content": "invalid"}}
        row = run_case(CASES["routine-holster"], generate, "guide", SCHEMA_VALUE, VALIDATOR, "phase", 2)
        self.assertEqual(len(row["attempts"]), 3)
        self.assertEqual(calls, [phase_schema(SCHEMA_VALUE, "tables")] * 3)

    def test_phase_recovery_advances_only_on_accepted_receipt(self):
        context = copy.deepcopy(CASES["request-roll"]["context"])
        self.assertEqual(fixture_phase(context), "rolls")
        context["operation"]["rolls"] = copy.deepcopy(CASES["receipt-and-secret"]["context"]["operation"]["rolls"])
        serialized = json.dumps(context)
        self.assertEqual(fixture_phase(json.loads(serialized)), "commit")
        self.assertEqual(fixture_phase(json.loads(serialized)), "commit")
        context["validation"]["legal"] = False
        with self.assertRaises(ValueError):
            fixture_phase(context)

    def test_repair_is_bounded_and_feedback_preserves_input(self):
        calls = []
        def generate(messages, fmt):
            calls.append(copy.deepcopy(messages))
            return {"message": {"content": "not JSON" if len(calls) == 1 else json.dumps(TABLES)}}
        row = run_case(CASES["routine-holster"], generate, "guide", SCHEMA_VALUE, VALIDATOR, "json", 1)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][:2], calls[1][:2])
        self.assertIn("feedback", calls[1][-1]["content"])
        self.assertEqual(summarize([row])["repaired"], 1)


if __name__ == "__main__":
    unittest.main()
