import copy
import json
import unittest

from acceptance import check_recovered_rolls, check_refresh_pair, diagnose_scope
from harness import score
from test_harness import CASES, VALIDATOR, proposal


def refresh(provider):
    return {"audience": "player", "connection_provider": provider,
            "storage_recovery_required": False, "recovery": {"record_mid_write": False},
            "public": {"cursor": {"campaign_id": "fixture", "revision": 7,
                                  "ledger_head": "fixture_evt_7", "public_sha256": "a" * 64}}}


class Acceptance(unittest.TestCase):
    def test_distinct_clients_must_present_the_same_authoritative_cursor(self):
        gpt, gemini = refresh("gpt-session"), refresh("gemini-session")
        self.assertEqual(check_refresh_pair(gpt, gemini)[1], 7)
        for key, value in (("revision", 8), ("ledger_head", "other"), ("public_sha256", "b" * 64)):
            altered = copy.deepcopy(gemini)
            altered["public"]["cursor"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                check_refresh_pair(gpt, altered)
        with self.assertRaises(ValueError):
            check_refresh_pair(gpt, gpt)
        gemini["storage_recovery_required"] = True
        with self.assertRaises(ValueError):
            check_refresh_pair(gpt, gemini)

    def test_recovery_checks_binding_receipts_not_just_roll_keys(self):
        prior = {"s1.check": {"request_hash": "fixture_request", "result": {"roll_id": "r1", "total": 8}}}
        restored = json.loads(json.dumps(prior))
        self.assertEqual(check_recovered_rolls(prior, restored), 1)
        restored["s1.check"]["result"]["total"] = 17
        with self.assertRaises(ValueError):
            check_recovered_rolls(prior, restored)
        with self.assertRaises(ValueError):
            check_recovered_rolls(prior, {})
        with self.assertRaises(ValueError):
            check_recovered_rolls(prior, {**prior, "another": prior["s1.check"]})

    def test_public_event_and_context_leaks_are_rejected(self):
        case = CASES["receipt-and-secret"]
        for target in ("event", "context"):
            move = proposal(copy.deepcopy(case))
            content = move["proposal"]
            if target == "event":
                content["events"][0]["summary"] = "BLUE QUARANTINE"
            else:
                content["turn_context"]["notes"].append("AC 17")
            with self.subTest(target=target):
                self.assertIn("SECRECY", {e.split(":")[0] for e in score(json.dumps(move), case, VALIDATOR)})

    def test_player_step_substitution_and_false_rule_reference_are_rejected(self):
        case = CASES["choice-stop"]
        move = proposal(copy.deepcopy(case))
        move["proposal"]["events"][0]["details"]["step_id"] = "s2"
        self.assertTrue(any(e.startswith("AGENCY") for e in score(json.dumps(move), case, VALIDATOR)))
        case = CASES["request-roll"]
        roll = case["expect"]["roll"] | {"purpose": "Inspect.", "rule_sources": ["invented:rule"]}
        self.assertTrue(any(e.startswith("MECHANICS") for e in score(
            json.dumps({"type": "rolls", "rolls": [roll]}), case, VALIDATOR)))

    def test_redacted_oauth_diagnostics_do_not_guess(self):
        self.assertEqual(diagnose_scope(), "REQUEST_OR_GRANT_EVIDENCE_MISSING")
        self.assertEqual(diagnose_scope(request_includes_gm=False), "CLIENT_OMITTED_GM")
        self.assertEqual(diagnose_scope(request_includes_gm=True, issued_includes_gm=False),
                         "ISSUER_DID_NOT_GRANT_GM")
        self.assertEqual(diagnose_scope(issued_includes_gm=True), "SESSION_DOES_NOT_REFLECT_ISSUED_GRANT")
        with self.assertRaises(ValueError):
            diagnose_scope(request_includes_gm="not a boolean")


if __name__ == "__main__":
    unittest.main()
