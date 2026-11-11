"""Isolated acceptance tests for progress, projections, contest and draft foundations."""
import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "campaigns/starwars_litrpg/ui"))
import projections
import export_state

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

progress = module("progress", ".claude/skills/litrpg-process-turn/progress.py")
plan_review = module("plan_review", ".claude/skills/litrpg-process-turn/plan_review.py")
genesis = module("genesis", "development/campaign_genesis/genesis.py")
sys.path.insert(0, str(ROOT / ".claude/skills/litrpg-ledger"))
import batch
import ledger
import repair

def rejects(function):
    try:
        function()
    except ValueError:
        return
    raise AssertionError("operation was not rejected")

def test_progress():
    row = {"status": "processing"}
    lock = {"holder": "r", "expires_ms": 10000}
    for index, stage in enumerate(progress.STAGES[:-1]):
        row.update(progress.patch(row, lock, "r", stage, now=1000+index*100))
    assert row["processing"]["stages"]["claimed"] == 1000
    rejects(lambda: progress.patch(row, lock, "r", "dice", now=1900))
    rejects(lambda: progress.patch(row, lock, "r", "complete", now=1900))
    rejects(lambda: progress.patch(row, lock, "other", "claimed", now=1900))
    row["publication"] = {"status": "published"}
    result = progress.patch(row, lock, "r", "complete", now=2000)
    assert result["processing"]["stage_started_ms"] == 2000
    retry = progress.patch(row, lock, "r", "publishing", now=2000)
    assert retry["processing"]["started_ms"] == 1000
    new = progress.patch(row, {"holder": "new", "expires_ms": 10000}, "new", "claimed", now=3000)
    assert new["processing"]["started_ms"] == 3000

def ev(n, kind, details=None, summary="Aero and Wick act together", visibility="player"):
    return {"event_id": f"evt_{n:04d}", "session": 1, "turn_no": n, "world_time": "test", "kind": kind,
            "details": details or {}, "summary": summary, "actor": "aero", "visibility": visibility,
            "knowledge_type": "fact", "known_to": [], "caused_by": [], "roll_ids": []}

def test_optional_review():
    action = {"request_plan_review": True, "campaign_id": "sandbox", "based_on_revision": 4,
              "ledger_head": "evt_0004", "declaration": {"actor": "aero", "steps": [{"id": "s", "type": "speech", "text": "Wait"}]}}
    action.update(plan_review.create(action, {"legal": True, "preview": [{"text": "Say Wait"}]}, "action"))
    approval = {"decision": "approved", "action_id": "action", "campaign_id": "sandbox",
                "review_id": action["review_plan"]["review_id"], "based_on_revision": 4, "ledger_head": "evt_0004"}
    assert plan_review.approved(action, approval, "action")
    assert not plan_review.approved(action, {**approval, "ledger_head": "stale"}, "action")
    changed = copy.deepcopy(action)
    changed["declaration"]["steps"][0]["text"] = "Attack"
    assert not plan_review.approved(changed, approval, "action")
    rejects(lambda: plan_review.create({**action, "request_plan_review": False}, {"legal": True}, "action"))


def test_projections():
    events = []
    for n in range(10):
        events += [ev(3*n+1, "player_declaration"), ev(3*n+2, "gm_narration", {"text": f"Public outcome {n}."}),
                   ev(3*n+3, "turn_context")]
    out = projections.project(events)
    assert len(out["chapters"]) == 2 and all(row["sources"] for row in out["chapters"])
    changed = projections.project([event for event in events if event["event_id"] != "evt_0002"])
    assert len(changed["chapters"]) == 1
    assert "evt_0002" not in json.dumps(changed)
    with tempfile.TemporaryDirectory() as directory:
        corrected = export_state.build(ev=events+[ev(31, "ruling_void", {"voids": ["evt_0002"]})],
                                       campaign_dir=Path(directory))
        assert len(corrected["chapters"]) == 1
        assert "evt_0002" not in json.dumps(corrected["chapters"])
    objective = ev(31, "objective_set", {"id": "goal", "label": "Find the public exit"})
    assert projections.project(events+[objective])["objectives"] == ["Find the public exit"]
    assert not projections.project(events+[objective,ev(32,"objective_completed",{"id":"goal"})])["objectives"]
    relation = projections.relationships(events)
    assert all(not rows for rows in relation["dimensions"].values())
    assert relation["recruitment"] == "undetermined"
    evidence = ev(31, "npc_reaction", {"relationship_evidence": {"source": "wick", "target": "aero",
                       "dimension": "respect", "observation": "Wick explicitly said he respects Aero's decision."}})
    relation = projections.relationships(events+[evidence])
    assert relation["dimensions"]["respect"][0]["event_id"] == evidence["event_id"]
    hidden = ev(32, "npc_plan", summary="PRIVATE_CANARY", visibility="gm_only")
    rejects(lambda: projections.project(events+[hidden]))
    rejects(lambda: projections.relationships(events+[hidden]))

def test_repair():
    with tempfile.TemporaryDirectory() as root:
        camp = Path(root)
        (camp / "records").mkdir()
        (camp / "hidden").mkdir()
        declaration = ev(1, "player_declaration", {"declaration": {"steps": [{"id": "s1", "type": "object"}]}})
        consequence = ev(2, "action_resolved", {"step_id": "s1"})
        consequence["caused_by"] = ["evt_0001"]
        dependent = ev(3, "world_event")
        dependent["caused_by"] = ["evt_0002"]
        unaffected = ev(4, "world_event", summary="unaffected")
        source = [declaration, consequence, dependent, unaffected]
        (camp / "records/events.jsonl").write_text("".join(json.dumps(row)+"\n" for row in source))
        request = {"category": "intent", "declaration_event": "evt_0001", "step_id": "s1"}
        proposal = repair.plan(camp, request)
        assert proposal["affected"] == ["evt_0002", "evt_0003"]
        assert "evt_0004" not in proposal["affected"]
        rejects(lambda: repair.accepted_batch(camp, request, {}))
        decision = {"request_hash": proposal["request_hash"], "head": proposal["head"], "decision": "approve",
                    "basis": "Original step was misread.", "rule_sources": ["TURN_CONTRACT.md"], "preserve_unlinked": ["evt_0004"],
                    "replacements": [ev(99, "action_resolved", {"step_id": "s1"}, summary="corrected")]}
        rejected = copy.deepcopy(decision)
        rejected["replacements"][0]["roll_ids"] = ["invented-roll"]
        rejects(lambda: repair.accepted_batch(camp, request, rejected))
        accepted = repair.accepted_batch(camp, request, decision)
        lease = camp / "lease.json"
        import time
        lease.write_text(json.dumps({"holder": "r", "expires_ms": int(time.time()*1000)+60000}))
        result = batch.apply(camp, accepted, lease, "r", ledger)
        assert batch.apply(camp, accepted, lease, "r", ledger) == result
        assert (camp / "records/events.jsonl").read_text().startswith("".join(json.dumps(row)+"\n" for row in source))
        assert repair.plan(camp, {**request, "category": "unfavorable"})["status"] == "no_correction"
        rejected = copy.deepcopy(decision)
        rejected["replacements"][0]["roll_ids"] = ["invented-roll"]
        rejects(lambda: repair.accepted_batch(camp, request, rejected))

def test_foundation():
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / "registry.sqlite"
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE canonical(proposed_urid TEXT, entity_name TEXT, entity_type TEXT, source_pointer TEXT, authority_lane TEXT)")
            db.executemany("INSERT INTO canonical VALUES(?,?,?,?,?)", [("a","A","Faction","source","validated"),("b","B","Faction","source","validated")])
        request = {"era": "player-selected era", "preferences": {"tone": "mystery"}, "worldbuilding": {"place": "frontier"},
                   "entities": ["a","b"], "connections": [{"source":"a","target":"b","type":"dependency","condition":"If supply stops"}]}
        result = genesis.foundation(request, path)
        assert result["status"] == "proposed" and result["relationships"][0]["status"] == "candidate"
        rejects(lambda: genesis.foundation({**request, "entities":["a","ghost"]}, path))
        rejects(lambda: genesis.foundation({**request,"before_the_fall":True}, path))
        rules = Path(root) / "original-rules.txt"
        rules.write_bytes(b"Unmodified original mechanics")
        before = rules.read_bytes()
        result = genesis.foundation({**request,"before_the_fall":True}, path, rules)
        assert rules.read_bytes() == before and result["chronology"]["mechanics_modified"] is False

if __name__ == "__main__":
    for test in (test_progress, test_optional_review, test_projections, test_repair, test_foundation):
        test()
        print("PASS", test.__name__)
