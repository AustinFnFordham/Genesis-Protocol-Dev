import collections
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import policy
import engine
from fixtures import campaign_copy, action_for, request_for

QA = engine.ROOT / "development/.qa"
QA.mkdir(exist_ok=True)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, engine.ROOT / path)
    out = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(out)
    return out


audit = module("resolution_rng_audit", ".claude/skills/litrpg-dice/audit_rng.py")
brief = module("resolution_brief", ".claude/skills/litrpg-process-turn/brief.py")
review = module("resolution_review", ".claude/skills/litrpg-process-turn/plan_review.py")
client = module("resolution_client", "development/interop/public_client.py")


def record(face, alt=None, mode="normal", kind="check"):
    faces = iter([(face-1)/20, ((alt or face)-1)/20])
    dice, alternate, raw, mods, single = engine.roller.do_roll("1d20+3", mode, lambda: next(faces))
    return {"dice": dice, "alt_dice": alternate, "raw_total": raw, "modifiers": mods,
            "final_total": raw+mods, "formula": "1d20+3", "mode": mode}


class PolicyTests(unittest.TestCase):
    def test_every_face_and_uniform_distribution(self):
        for temperature, low, copies in (("regular", 1, 1), ("heroic", 11, 2), ("legendary", 16, 4)):
            values = [policy.effective(n, temperature) for n in range(1, 21)]
            self.assertEqual(sorted(set(values)), list(range(low, 21)))
            self.assertEqual(set(collections.Counter(values).values()), {copies})
            for raw in range(1, 21):
                expected = raw if temperature == "regular" else 11+(raw-1)//2 if temperature == "heroic" else 16+(raw-1)//4
                self.assertEqual(values[raw-1], expected)

    def test_all_advantage_pairs(self):
        for first in range(1, 21):
            for second in range(1, 21):
                for mode, select in (("advantage", max), ("disadvantage", min)):
                    raw = record(first, second, mode)
                    for temperature in policy.TEMPERATURES:
                        result = policy.resolve(raw, {"temperature": temperature, "narrative_consequences": False}, "check", True, 17)
                        self.assertEqual(result["roll"]["raw_original"], [first])
                        self.assertEqual(result["roll"]["raw_alternate"], [second])
                        self.assertEqual(result["roll"]["selected_raw_d20"], select(first, second))
                        self.assertEqual(result["roll"]["effective_d20"], policy.effective(select(first, second), temperature))
                        self.assertEqual(result["roll"]["modifier"], 3)
                        self.assertEqual(result["task"]["target"], 17)

    def test_natural_critical_policy(self):
        for temperature in policy.TEMPERATURES:
            selected = {"temperature": temperature, "narrative_consequences": False}
            one = policy.resolve(record(1), selected, "attack", True, 1)
            self.assertEqual(one["roll"]["automatic_attack_miss"], temperature == "regular")
            self.assertEqual(one["task"]["result"], "failure" if temperature == "regular" else "success")
            for raw in range(1, 21):
                result = policy.resolve(record(raw), selected, "attack", True, 100)
                self.assertEqual(result["roll"]["attack_critical"], raw == 20)
            self.assertEqual(policy.resolve(record(20), selected, "save", True, 100)["task"]["result"], "failure")
            self.assertEqual(policy.resolve(record(1), selected, "check", True, 1)["task"]["result"], "success")

    def test_degree_boundaries_and_independent_axes(self):
        self.assertEqual([(policy.narrative(n)["advantage"], policy.narrative(n)["threat"]) for n in range(1,7)],
                         [(0,2),(0,1),(0,0),(0,0),(1,0),(2,0)])
        for margin, expected in [(-11,"severe_failure"),(-10,"severe_failure"),(-9,"hard_failure"),(-5,"hard_failure"),
                                 (-4,"narrow_failure"),(-1,"narrow_failure"),(0,"narrow_success"),(4,"narrow_success"),
                                 (5,"strong_success"),(9,"strong_success"),(10,"exceptional_success")]:
            self.assertEqual(policy.degree(margin), expected)
        for success in (False, True):
            for positive in (False, True):
                out = policy.resolve(record(10), {"temperature":"regular","narrative_consequences":True}, "check", True,
                                     10 if success else 20, 6 if positive else 1)
                self.assertEqual(out["task"]["result"], "success" if success else "failure")
                self.assertEqual(out["narrative"]["advantage" if positive else "threat"], 2)
                self.assertEqual(policy.assess_causal(out, [], lambda _: True)["causal"], {"eligible_effects":[],"committed_effects":[]})
        out = policy.resolve(record(10), {"temperature":"regular","narrative_consequences":False}, "check", True, 20, 6)
        self.assertIsNone(out["narrative"])

    def test_no_automatic_causal_commit(self):
        out = policy.resolve(record(10), {"temperature":"regular","narrative_consequences":True}, "check", True, 10, 6)
        candidate = {"effect_id":"known_effect", "rule_source":"test_domain_rule", "event_ids":["evt_0001"], "axis":"advantage", "cost":1}
        self.assertFalse(policy.assess_causal(out, [candidate], lambda _: False)["causal"]["eligible_effects"])
        assessed = policy.assess_causal(out, [candidate], lambda _: True)
        self.assertEqual(assessed["causal"]["eligible_effects"], [candidate])
        self.assertFalse(assessed["causal"]["committed_effects"])

    def test_mixed_check_transforms_only_the_d20(self):
        draws = iter([0.1, 0.5])
        dice, alt, total, mods, _ = engine.roller.do_roll("1d20+1d4+3", "normal", lambda: next(draws))
        raw = {"dice":dice,"alt_dice":alt,"raw_total":total,"modifiers":mods,"final_total":total+mods,"formula":"1d20+1d4+3"}
        result = policy.resolve(raw, {"temperature":"heroic","narrative_consequences":False}, "check", True, 17)
        self.assertEqual(result["roll"]["effective_d20"], 12)
        self.assertEqual(result["roll"]["other_dice_total"], 3)
        self.assertEqual(result["roll"]["total"], 18)
        self.assertEqual(raw["dice"][1]["rolled"], [3])

    def test_private_nested_metadata_is_not_exported(self):
        out = policy.resolve(record(10), {"temperature":"heroic","narrative_consequences":True}, "check", True, 99173, 6)
        out["roll"]["hidden_dc"] = "PRIVATE_CANARY"
        out["narrative"]["secret_intent"] = "PRIVATE_CANARY"
        out["causal"]["eligible_effects"] = ["PRIVATE_CANARY"]
        safe = json.dumps(policy.public_resolution(out))
        for secret in ("PRIVATE_CANARY", "99173", '"target"', '"margin"'):
            self.assertNotIn(secret, safe)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=QA)
        self.addCleanup(self.directory.cleanup)
        self.campaign = campaign_copy(self.directory.name)

    def test_sequence_isolation_and_replay(self):
        originals = []
        narrative_values = []
        for temperature in policy.TEMPERATURES:
            for enabled in (False, True):
                with tempfile.TemporaryDirectory(dir=QA) as root:
                    camp = campaign_copy(root)
                    action = action_for(camp, temperature, enabled)
                    request = request_for()
                    result = engine.execute(camp, "same-action", action, request)
                    originals.append((result["roll"]["dice"], (camp/"hidden/dice_state.json").read_bytes()))
                    saved = {str(p.relative_to(camp)): p.read_bytes() for p in camp.rglob("*") if p.is_file()}
                    self.assertEqual(result, engine.execute(camp, "same-action", action, request))
                    self.assertEqual(saved, {str(p.relative_to(camp)): p.read_bytes() for p in camp.rglob("*") if p.is_file()})
                    changed = copy.deepcopy(action)
                    changed["resolution_settings"]["temperature"] = "legendary" if temperature != "legendary" else "heroic"
                    with self.assertRaises(ValueError):
                        engine.execute(camp, "same-action", changed, request)
                    if enabled:
                        narrative_values.append(result["resolution"]["narrative"])
                    self.assertTrue(audit.audit(camp, samples=1000)["ok"])
                    self.assertTrue(engine.replay(camp)["ok"])
        self.assertTrue(all(value == originals[0] for value in originals))
        self.assertTrue(all(value == narrative_values[0] for value in narrative_values))

    def test_npc_and_damage_isolation(self):
        action = action_for(self.campaign, "legendary", True)
        for i, (actor, kind, formula) in enumerate((("npc","attack","1d20+3"),("gm_hidden_table","check","1d20"),("aero","damage","2d6+3"),("aero","damage","1d20"))):
            request = dict(request_for(str(i)), requested_by=actor, kind=kind, formula=formula)
            result = engine.execute(self.campaign, "isolation", action, request)
            self.assertFalse(result["resolution"]["eligible"])
            self.assertEqual(result["resolution"]["roll"]["total"], result["roll"]["final_total"])
            self.assertIsNone(result["resolution"]["narrative"])

    def test_invalid_preflight_cannot_be_fixed_by_temperature(self):
        for temperature in policy.TEMPERATURES:
            action = action_for(self.campaign, temperature, True)
            action["declaration"]["actions"][0]["option"] = "unavailable_action"
            action["declaration"]["steps"][0]["option"] = "unavailable_action"
            before = (self.campaign/"hidden/dice_state.json").read_bytes()
            with self.assertRaises(ValueError):
                engine.execute(self.campaign, "invalid", action, request_for())
            self.assertEqual((self.campaign/"hidden/dice_state.json").read_bytes(), before)

    def test_pending_step_requires_player_authorization(self):
        action = action_for(self.campaign)
        action["declaration"]["steps"][0]["pending"] = True
        with self.assertRaises(ValueError):
            engine.execute(self.campaign, "pending", action, request_for())

    def test_legacy_settings_and_plan_approval(self):
        action = action_for(self.campaign)
        action.pop("resolution_settings")
        result = engine.execute(self.campaign, "legacy", action, request_for())
        self.assertEqual(result["resolution"]["settings"], policy.DEFAULT)
        action["request_plan_review"] = True
        action.update(review.create(action, {"legal":True}, "legacy"))
        approval = {"decision":"approved","action_id":"legacy","campaign_id":action["campaign_id"],
                    "review_id":action["review_plan"]["review_id"], "based_on_revision":action["based_on_revision"],"ledger_head":action["ledger_head"]}
        self.assertTrue(review.approved(action, approval, "legacy"))
        action["resolution_settings"] = {"temperature":"heroic","narrative_consequences":False}
        self.assertFalse(review.approved(action, approval, "legacy"))

    def test_brief_binds_current_action_settings(self):
        action = action_for(self.campaign, "heroic", True)
        entry = {"path":self.campaign, "id":action["campaign_id"], "dir":str(self.campaign.relative_to(engine.ROOT))}
        _, bundle = brief.build(entry, action=action)
        self.assertEqual(brief.compact(bundle)["submitted_resolution_settings"], action["resolution_settings"])

    def test_scene_mode_changes_preserve_history_and_private_boundaries(self):
        from compare_scenes import complete_turn
        previous = []
        entry = {"path":self.campaign,"id":"resolution-staging-copy","dir":str(self.campaign.relative_to(engine.ROOT))}
        pending = copy.deepcopy(engine.export_state.build(campaign_dir=self.campaign)["turn_context"]["pending_steps"])
        for index, (temperature, enabled) in enumerate((t, n) for t in policy.TEMPERATURES for n in (False, True)):
            action = action_for(self.campaign, temperature, enabled)
            result = engine.execute(self.campaign, f"switch-{index}", action, request_for())
            state = complete_turn(self.campaign, f"switch-{index}", action, result, "You finish looking. What do you do next?")
            self.assertEqual(state["dice_history"][:len(previous)], previous)
            previous = copy.deepcopy(state["dice_history"])
            self.assertEqual(state["dice_history"][-1]["resolution"]["settings"], action["resolution_settings"])
            self.assertEqual(state["turn_context"]["pending_steps"], pending)
            self.assertEqual(brief.build(entry)[1]["resolution_settings"], action["resolution_settings"])
            for out in (client.refresh(self.campaign, action["campaign_id"]), brief.build(entry, audience="player")[1]):
                self.assertNotIn("PRIVATE_RESOLUTION_CANARY", json.dumps(out))
            self.assertTrue(engine.ledger.validate_all(self.campaign)[1] == [])

    def test_actual_process_interruptions_resume_without_rng(self):
        points = ["accepted", "append:records/roll_log.jsonl", "append:hidden/experimental_resolution_log.jsonl",
                  "append:hidden/roll_dcs.jsonl", "state:temporary", "state:replaced", "receipt"]
        for point in points:
            with self.subTest(point=point), tempfile.TemporaryDirectory(dir=QA) as root:
                camp = campaign_copy(root)
                action = action_for(camp, "heroic", True)
                request = request_for()
                a, r = Path(root)/"action.json", Path(root)/"request.json"
                a.write_text(json.dumps(action)); r.write_text(json.dumps(request))
                code = "import sys,os,json;sys.path.insert(0,sys.argv[1]);import engine;engine.execute(sys.argv[2],'crash',json.load(open(sys.argv[3])),json.load(open(sys.argv[4])),lambda p:os._exit(77) if p==sys.argv[5] else None)"
                child = subprocess.run([sys.executable,"-B","-c",code,str(Path(__file__).parent),str(camp),str(a),str(r),point])
                self.assertEqual(child.returncode, 77)
                plan = json.loads((camp/"hidden/experimental_dice_pending.json").read_text())
                with self.assertRaises(ValueError):
                    engine.export_state.build(campaign_dir=camp)
                # Recovery is prohibited from generating or drawing again.
                original = engine.generate
                engine.generate = lambda *a, **k: (_ for _ in ()).throw(AssertionError("recovery rerolled"))
                try:
                    result = engine.execute(camp, "crash", action, request)
                finally:
                    engine.generate = original
                self.assertEqual(result, plan["result"])
                self.assertTrue(audit.audit(camp, samples=1000)["ok"])

    def test_torn_append_and_partial_state_temporary(self):
        action = action_for(self.campaign, "legendary", True)
        request = request_for()
        with self.assertRaises(RuntimeError):
            engine.execute(self.campaign, "torn", action, request,
                           lambda p: (_ for _ in ()).throw(RuntimeError()) if p == "accepted" else None)
        plan = json.loads((self.campaign/"hidden/experimental_dice_pending.json").read_text())
        path = self.campaign/"records/roll_log.jsonl"
        stream = plan["streams"]["records/roll_log.jsonl"]
        with path.open("ab") as handle:
            handle.write(stream["tail"].encode()[:17])
        (self.campaign/"hidden/dice_state.experimental.tmp").write_bytes(b'{"seed":')
        with self.assertRaises(ValueError):
            engine.execute(self.campaign, "other", action, request)
        self.assertEqual(engine.execute(self.campaign, "torn", action, request), plan["result"])
        self.assertTrue(audit.audit(self.campaign, samples=1000)["ok"])
        self.assertFalse((self.campaign/"hidden/dice_state.experimental.tmp").exists())

    def test_legacy_cli_interruption_is_detected_not_silently_repaired(self):
        # Characterize the unmodified legacy CLI. Its public append precedes
        # cursor replacement; this is an intentionally failing RELEASE gate.
        before = json.loads((self.campaign/"hidden/dice_state.json").read_text())
        code = "import sys,os;sys.path.insert(0,sys.argv[1]);import roll;original=roll.append\ndef interrupted(path,rec):\n original(path,rec)\n os._exit(78)\nroll.append=interrupted;roll.main(['1d20','--campaign',sys.argv[2]])"
        result = subprocess.run([sys.executable,"-B","-c",code,str(engine.ROOT/".claude/skills/litrpg-dice"),str(self.campaign)])
        self.assertEqual(result.returncode, 78)
        self.assertEqual(json.loads((self.campaign/"hidden/dice_state.json").read_text()), before)
        with self.assertRaises(ValueError):
            engine.execute(self.campaign, "refuse-legacy-cursor", action_for(self.campaign), request_for())
        self.assertFalse(audit.audit(self.campaign, samples=1000)["ok"])
        (QA/"legacy_dice_crash_gate.json").write_text(json.dumps({"legacy_cli_crash_atomicity":"FAIL",
            "failure":"public roll append can precede cursor replacement", "experimental_adapter_rejects_divergence":True,
            "legacy_cli_modified":False,"live_campaign_exercised":False},indent=2)+"\n")


if __name__ == "__main__":
    unittest.main()
