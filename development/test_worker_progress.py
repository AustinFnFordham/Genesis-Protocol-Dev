"""Worker progress must remain truthful across heartbeats and retries."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("progress", ROOT / ".claude/skills/litrpg-process-turn/progress.py")
progress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(progress)


class ProgressClockTests(unittest.TestCase):
    def setUp(self):
        self.lock = {"holder": "worker", "expires_ms": 10000}
        self.row = {"status": "processing"}
        self.row.update(progress.patch(self.row, self.lock, "worker", "claimed", now=1000))
        self.row.update(progress.patch(self.row, self.lock, "worker", "context", now=1100))
        self.row.update(progress.patch(self.row, self.lock, "worker", "context", now=1500))

    def test_backwards_clock_cannot_replace_newer_heartbeat(self):
        with self.assertRaises(ValueError):
            progress.patch(self.row, self.lock, "worker", "rules", now=1400)

    def test_boolean_is_not_a_worker_timestamp(self):
        with self.assertRaises(ValueError):
            progress.patch({"status": "processing"}, self.lock, "worker", "claimed", now=True)

    def test_heartbeat_preserves_phase_start(self):
        value = progress.patch(self.row, self.lock, "worker", "context", now=1700)["processing"]
        self.assertEqual(value["started_ms"], 1000)
        self.assertEqual(value["stage_started_ms"], 1100)
        self.assertEqual(value["heartbeat_ms"], 1700)

    def test_new_run_starts_a_new_clock(self):
        value = progress.patch(self.row, {"holder": "retry", "expires_ms": 10000}, "retry", "claimed", now=2000)["processing"]
        self.assertEqual(value["started_ms"], 2000)
        self.assertEqual(value["stages"], {"claimed": 2000})


if __name__ == "__main__":
    unittest.main()
