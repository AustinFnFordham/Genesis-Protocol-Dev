"""Real Genesis modules with a disposable local queue/publication CAS test double.

This is a deterministic integration test, not an AI GM or a production worker.
No network, Artifact operations, live registry edits, or campaign source writes.
"""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "development/.qa"
sys.path.insert(0, str(ROOT / ".claude/skills/litrpg-ledger"))
sys.path.insert(0, str(ROOT / "campaigns/starwars_litrpg/ui"))
import batch
import export_state
import ledger


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


progress = module("flow_progress", ".claude/skills/litrpg-process-turn/progress.py")
brief = module("flow_brief", ".claude/skills/litrpg-process-turn/brief.py")
roller = module("flow_roll", ".claude/skills/litrpg-dice/roll.py")
audit_rng = module("flow_rng", ".claude/skills/litrpg-dice/audit_rng.py")


class Conflict(ValueError):
    pass


class LocalDocuments:
    """Test transport with durable row versions; not an ArtifactData adapter."""
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE documents (key TEXT PRIMARY KEY, version INTEGER, data TEXT)")
        self.db.commit()

    def read(self, key):
        row = self.db.execute("SELECT version,data FROM documents WHERE key=?", (key,)).fetchone()
        return (row[0], json.loads(row[1])) if row else (0, {})

    def put(self, key, data, expected):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            if self.read(key)[0] != expected:
                raise Conflict("document version changed")
            self.db.execute("INSERT INTO documents VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET version=excluded.version,data=excluded.data",
                            (key, expected+1, json.dumps(data)))
        return expected+1


def protected_fingerprints():
    base = ROOT / "campaigns/starwars_litrpg/runs"
    paths = [p for p in base.rglob("*") if p.is_file()]
    paths.append(ROOT / "campaigns/starwars_litrpg/ui/turn_contract.js")
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


class Roundtrip(unittest.TestCase):
    def test_interrupted_turn_and_publication(self):
        protected = protected_fingerprints()
        QA.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="roundtrip-", dir=QA) as temporary:
            root = Path(temporary)
            campaign = root / "campaign"
            shutil.copytree(ROOT / "campaigns/starwars_litrpg/runs/sandbox", campaign)
            store = LocalDocuments(root / "transport.sqlite")
            self.addCleanup(store.db.close)
            source = {name: (campaign/name).read_bytes() for name in ("records/events.jsonl", "hidden/events.jsonl")}
            before = export_state.build(campaign_dir=campaign, campaign_id="isolated-worker-test")
            old = export_state.publish_set(before)
            for name, page in old["pages"].items():
                store.put("view/"+name, page, 0)
            store.put("view/state", old["state"], 0)

            # Use the actual Node parser/validator against the copied published context.
            context = root / "context.json"
            context.write_text(json.dumps(before["turn_context"]))
            text = "Holster the blaster pistol"
            parsed = json.loads(subprocess.check_output(["node", str(ROOT / "campaigns/starwars_litrpg/ui/turn_contract.js"),
                                                        "parse", text, str(context)], text=True))
            self.assertTrue(parsed["validation"]["legal"], parsed)
            declaration = parsed["declaration"]
            action = {"status": "submitted", "campaign_id": "isolated-worker-test", "action_id": "worker-test-action",
                      "based_on_revision": before["revision"], "ledger_head": before["ledger_head"],
                      "context_id": before["turn_context"]["context_id"], "text": text, "declaration": declaration}
            store.put("actions/test", action, 0)
            version, row = store.read("actions/test")
            duplicate = copy.deepcopy(row)
            run = "local-integration-worker"
            lock = {"holder": run, "expires_ms": time.time_ns()//1_000_000+60000}
            lease = root / "lease.json"
            lease.write_text(json.dumps(lock))
            stages = []

            def stage(name):
                nonlocal version, row
                row.update(progress.patch(row, lock, run, name))
                version = store.put("actions/test", row, version)
                stages.append(name)

            row["status"] = "processing"
            stage("claimed")
            with self.assertRaises(Conflict):
                store.put("actions/test", duplicate, 1)
            stage("context")
            entry = {"id": "isolated-worker-test", "path": campaign, "dir": str(campaign.relative_to(ROOT))}
            _, gm_brief = brief.build(entry)
            _, player_brief = brief.build(entry, audience="player")
            self.assertEqual(brief.compact(gm_brief)["fields"], gm_brief["fields"])
            stage("rules")
            checked = json.loads(subprocess.check_output(["node", str(ROOT / "campaigns/starwars_litrpg/ui/turn_contract.js"),
                                                         "validate", "-", str(context)], input=json.dumps(declaration), text=True))
            self.assertTrue(checked["validation"]["legal"])
            self.assertEqual(action["based_on_revision"], export_state.build(campaign_dir=campaign)["revision"])

            stage("dice")
            # No roll is required for holstering. A synthetic diagnostic roll exercises
            # real RNG/log recovery in this test only; it does not adjudicate the action.
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(roller.main(["1d20+2", "--mode", "advantage", "--by", "aero", "--purpose",
                                             "[worker-test-action] synthetic diagnostic only", "--campaign", str(campaign)]), 0)
            roll = json.loads(out.getvalue())
            dice_bytes = (campaign / "hidden/dice_state.json").read_bytes()
            roll_bytes = (campaign / "records/roll_log.jsonl").read_bytes()
            pending_before = copy.deepcopy(before["turn_context"]["pending_steps"])
            next_context = copy.deepcopy(before["turn_context"])
            next_context.pop("context_id", None)
            next_context["hands"]["left"] = None
            all_events = ledger.load_all(campaign)

            def event(kind, summary, details, visibility="player", causes=None):
                return {"session": 1, "turn_no": all_events[-1]["turn_no"]+1, "world_time": "Isolated test",
                        "kind": kind, "summary": summary, "actor": "aero", "visibility": visibility,
                        "knowledge_type": "fact", "known_to": [], "caused_by": causes or [], "roll_ids": [], "details": details}

            narrative = "Sandbox fixture: Aero holsters the blaster. The remote remains untouched."
            request = {"batch_id": "worker-test-action", "expected_revision": len(all_events),
                       "expected_head": all_events[-1]["event_id"], "events": [
                event("player_declaration", text, {"action_id": action["action_id"], "text": text, "declaration": declaration}),
                event("object_interaction", "Blaster holstered", {"option": "holster_blaster", "hands": next_context["hands"]}, causes=["$1"]),
                event("gm_ruling", "PRIVATE_WORKER_CANARY", {"test_only": True}, "gm_only", ["$1"]),
                event("gm_narration", "Sandbox fixture narration", {"text": narrative}, causes=["$2"]),
                event("turn_context", "Sandbox fixture next decision", next_context, causes=["$4"])]}
            stage("ledger")
            with self.assertRaisesRegex(RuntimeError, "injected"):
                batch.apply(campaign, request, lease, run, ledger,
                            after_stream=lambda _: (_ for _ in ()).throw(RuntimeError("injected interruption")))
            with self.assertRaises(ValueError):
                export_state.build(campaign_dir=campaign)
            self.assertEqual(store.read("actions/test")[1]["processing"]["stage"], "ledger")
            self.assertEqual(store.read("view/state")[1], old["state"])
            result = batch.apply(campaign, request, lease, run, ledger)
            self.assertEqual(batch.apply(campaign, request, lease, run, ledger), result)
            self.assertEqual((campaign / "hidden/dice_state.json").read_bytes(), dice_bytes)
            self.assertEqual((campaign / "records/roll_log.jsonl").read_bytes(), roll_bytes)
            self.assertFalse(ledger.validate_all(campaign)[1])
            for name, original in source.items():
                self.assertTrue((campaign/name).read_bytes().startswith(original))
            stage("narration")
            refreshed = export_state.build(campaign_dir=campaign, campaign_id=action["campaign_id"])
            self.assertEqual(refreshed["feed"][-1]["text"], narrative)
            self.assertEqual(refreshed["turn_context"]["pending_steps"], pending_before)
            self.assertIsNone(refreshed["turn_context"]["hands"]["left"])
            self.assertEqual(refreshed["character"]["inventory"], before["character"]["inventory"])
            self.assertEqual(refreshed["scene"], {**before["scene"], "time": "Isolated test"})
            row.update(status="resolved", publication={"status": "pending"})
            stage("publishing")
            documents = export_state.publish_set(refreshed)
            names = list(documents["pages"])
            self.assertTrue(names)
            # Crash after one page. The old snapshot remains the publication authority.
            key = "view/"+names[0]
            store.put(key, documents["pages"][names[0]], store.read(key)[0])
            row["publication"] = {"status": "pending", "error": "injected page publication failure"}
            version = store.put("actions/test", row, version)
            with self.assertRaises(ValueError):
                progress.patch(row, lock, run, "complete")
            self.assertEqual(store.read("view/state")[1], old["state"])
            for name, page in documents["pages"].items():
                store.put("view/"+name, page, store.read("view/"+name)[0])
            for kind, manifest in documents["state"]["history"].items():
                if isinstance(manifest, dict):
                    for page in manifest.get("pages", []):
                        self.assertEqual(store.read("view/"+page["id"])[1]["hash"], page["hash"])
            store.put("view/state", documents["state"], store.read("view/state")[0])
            row["publication"] = {"status": "published"}
            row["status"] = "committed"
            stage("complete")
            self.assertEqual(stages, list(progress.STAGES))
            self.assertTrue(audit_rng.audit(campaign, samples=1000)["ok"])
            for view in (documents, brief.build(entry, audience="player")[1]):
                self.assertNotIn("PRIVATE_WORKER_CANARY", json.dumps(view))
            self.assertNotIn("seed", json.dumps(documents))
            self.assertEqual(action["declaration"], declaration)
            self.assertEqual(protected_fingerprints(), protected)
            timings = row["processing"]["stages"]
            values = list(timings.values())
            self.assertEqual(values, sorted(values))
            report = {"passed": True, "stages": stages, "elapsed_ms": values[-1]-values[0],
                      "stage_durations_ms": {name: values[i+1]-values[i] for i, name in enumerate(stages[:-1])},
                      "public_revision_before": before["revision"], "public_revision_after": refreshed["revision"],
                      "state_bytes": export_state.doc_bytes(documents["state"]),
                      "pages": len(documents["pages"]), "source_campaign_files_unchanged": True,
                      "ledger_retry_dice_unchanged": True, "pending_steps_preserved": True,
                      "transport": "disposable SQLite CAS test double", "adjudication": "scripted sandbox fixture",
                      "production_deployed": False, "live_worker_tested": False}
            (QA / "worker_roundtrip.json").write_text(json.dumps(report, indent=2)+"\n")


if __name__ == "__main__":
    unittest.main()
