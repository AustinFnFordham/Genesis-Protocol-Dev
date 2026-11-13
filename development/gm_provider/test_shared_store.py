"""Shared staging through git: separate clones stand for separate GM sessions and clients.

Real git (a local bare repository as the remote), real gateway, real dice and ledger. The GMs are
scripted MOCKS; this proves that sessions which share nothing but a git branch keep one queue, one
lease and one set of accepted results. No network.  Run: python3 -B development/gm_provider/test_shared_store.py
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import staging                                   # noqa: E402
from gateway import Refused                      # noqa: E402
from runner import run_turn                      # noqa: E402
from store import Conflict                       # noqa: E402
from test_gateway import script, QA, INSPECT, HOLSTER, Clock, fingerprints, ledger   # noqa: E402


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True).stdout


class Shared(unittest.TestCase):
    def setUp(self):
        self.protected = fingerprints()
        QA.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="shared-", dir=QA)
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        git(root, "init", "--quiet", "--bare", "-b", "staging", "origin.git")
        seed = root / "seed"
        git(root, "clone", "--quiet", str(root / "origin.git"), str(seed))
        (seed / "README").write_text("shared staging test\n")
        git(seed, "add", "-A")
        git(seed, "-c", "user.name=t", "-c", "user.email=t@t.invalid", "commit", "--quiet", "-m", "seed")
        git(seed, "push", "--quiet", "origin", "HEAD:staging")
        self.root = root
        self.player = staging.make_shared(self.clone("player") / "staging/env", "shared-test")

    def tearDown(self):
        self.assertEqual(fingerprints(), self.protected)

    def clone(self, name):
        git(self.root, "clone", "--quiet", "--branch", "staging", str(self.root / "origin.git"), name)
        return self.root / name

    def session(self, name, clock=None):
        return staging.open_shared(self.clone(name) / "staging/env", clock=clock, min_sync_s=0)

    def test_sessions_sharing_only_a_branch_play_and_hand_over(self):
        order = ["gpt", "gemini", "claude", "gpt"]
        sessions = {n: self.session(n + "-session") for n in set(order)}
        head = self.player.public_state()["cursor"]["ledger_head"]
        for n, name in enumerate(order, 1):
            action = staging.declare(self.player, f"shared-{n:04d}", text=HOLSTER if n == 1 else INSPECT, provider=name)
            self.player.submit(action)
            for other in sessions:
                if other != name:
                    self.assertEqual(run_turn(sessions[other], script(other))["outcome"], "not_routed")
            out = run_turn(sessions[name], script(name))
            self.assertEqual(out["outcome"], "committed", out)
            state = self.player.public_state()                                  # the player's own clone, after a pull
            self.assertTrue(state["state"]["feed"][-1]["text"].startswith(f"[{name}]"))
            self.assertIn(f"Head was {head}", state["state"]["feed"][-1]["text"])
            self.assertEqual(self.player.store.read("view/state")[1]["revision"], state["cursor"]["revision"])
            head = state["cursor"]["ledger_head"]
        log = git(self.player.store.repo, "log", "--format=%s", "origin/staging")
        self.assertIn("env: accepted operation shared-0002", log)
        public = "".join(p.read_text() for p in (self.player.store.scope / "store").rglob("*.json"))
        for secret in ("CANARY", "private table", "interpretation"):
            self.assertNotIn(secret, public)

    def test_git_push_is_the_compare_and_set(self):
        a, b = self.session("a"), self.session("b")
        a.select_provider("claude")
        version, _ = a.store.read("routing/shared-test")
        self.assertEqual(b.store.read("routing/shared-test")[0], version)
        a.store.put("routing/shared-test", {"provider": "gpt", "history": []}, version)
        with self.assertRaises(Conflict):
            b.store.put("routing/shared-test", {"provider": "gemini", "history": []}, version)
        self.assertEqual(b.store.read("routing/shared-test")[1]["provider"], "gpt")
        self.assertEqual(git(b.store.repo, "status", "--porcelain").strip(), "")

    def test_another_session_takes_over_mid_turn_without_a_reroll(self):
        clock = Clock()
        first, second = self.session("gpt-session"), self.session("gemini-session", clock=clock)
        action = staging.declare(self.player, "shared-0001", text=INSPECT, provider="gpt")
        self.player.submit(action)
        def killed(kind, move):
            if kind == "commit":
                raise KeyboardInterrupt("session ended")
        with self.assertRaises(KeyboardInterrupt):
            run_turn(first, script("gpt"), run="run-a", interrupt=killed)
        rolls = [r for r in ledger.read_jsonl(first.campaign / "records/roll_log.jsonl") if "shared-0001" in r["purpose"]]
        self.assertEqual(len(rolls), 1)
        status = self.player.action_status("shared-0001")                        # a third clone sees the accepted work
        self.assertEqual((status["mechanical"]["tables_fixed"], status["mechanical"]["rolls_accepted"]), (True, 1))
        with self.assertRaises(Refused) as caught:
            self.player.reroute("shared-0001", "gemini")
        self.assertEqual(caught.exception.code, "PROVIDER_BUSY")
        clock.expire(second)
        second.reroute("shared-0001", "gemini", by="operator")
        out = run_turn(second, script("gemini"), run="run-b")
        self.assertEqual((out["outcome"], out["moves"]), ("committed", ["commit"]), out)
        after = [r for r in ledger.read_jsonl(second.campaign / "records/roll_log.jsonl") if "shared-0001" in r["purpose"]]
        self.assertEqual(after, rolls)
        with self.assertRaises(Refused) as caught:                               # the dead session wakes up
            first.commit("gpt", "run-a", {})
        self.assertEqual(caught.exception.code, "LEASE_LOST")
        self.assertTrue(self.player.public_state()["state"]["feed"][-1]["text"].startswith("[gemini]"))
        self.assertFalse(ledger.validate_all(self.player.campaign)[1])

    def test_environment_refuses_canonical_and_reuse(self):
        scope = self.player.store.scope
        with self.assertRaises(ValueError):
            staging.make_shared(scope, "again")
        (scope / "environment.json").write_text(json.dumps({"campaign_id": "x", "canonical": True}))
        with self.assertRaises(ValueError):
            staging.open_shared(scope)


if __name__ == "__main__":
    unittest.main(verbosity=1)
