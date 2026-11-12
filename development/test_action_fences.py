"""Optional envelope fields fence stale clients without changing legacy validators."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TURN = ROOT / ".claude/skills/litrpg-process-turn/turn.py"
QA = ROOT / "development/.qa"


class ActionFenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QA.mkdir(exist_ok=True)
        cls.info = json.loads(subprocess.check_output([sys.executable, "-B", str(TURN), "info", "sandbox"], text=True))

    def check(self, **fields):
        action = {"text": "Holster the blaster pistol", "actor": "aero", "campaign_id": "sandbox",
                  "based_on_revision": self.info["revision"], **fields}
        with tempfile.TemporaryDirectory(dir=QA) as temporary:
            path = Path(temporary) / "action.json"
            path.write_text(json.dumps(action))
            result = subprocess.run([sys.executable, "-B", str(TURN), "check", "sandbox", str(path)], text=True, capture_output=True)
        return result.returncode, json.loads(result.stdout)

    def test_wrong_head_with_correct_revision_is_rejected(self):
        code, result = self.check(ledger_head="evt_0001")
        self.assertEqual(code, 3, result)
        self.assertEqual(result["verdict"], "needs_revision")

    def test_wrong_context_with_correct_revision_is_rejected(self):
        code, result = self.check(context_id="evt_0001")
        self.assertEqual(code, 3, result)
        self.assertEqual(result["verdict"], "needs_revision")

    def test_current_envelope_passes(self):
        code, result = self.check(ledger_head=self.info["ledger_head"], context_id=self.info["turn_context"]["context_id"])
        self.assertEqual(code, 0, result)

    def test_legacy_envelope_still_passes(self):
        code, result = self.check()
        self.assertEqual(code, 0, result)


if __name__ == "__main__":
    unittest.main()
