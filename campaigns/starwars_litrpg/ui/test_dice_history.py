"""Isolated dice projection and byte budget regression tests."""
import copy
import json
from pathlib import Path
import tempfile
import export_state as E

def event(n, rolls, visibility="player"):
    return {"event_id": f"evt_{n:04d}", "kind": "player_declaration" if n == 1 else "ruling",
            "details": {}, "summary": "public", "world_time": "test", "actor": "aero",
            "visibility": visibility, "knowledge_type": "fact", "caused_by": [], "roll_ids": rolls}

def test_projection():
    def roll(rid, who):
        return {"roll_id": rid, "requested_by": who, "purpose": "[action] test", "turn_no": 1,
                "formula": "1d20-2", "mode": "normal", "dice": [{"kept": [7]}],
                "raw_total": 7, "modifiers": -2, "final_total": 5, "nat1": False}
    with tempfile.TemporaryDirectory() as directory:
        camp = Path(directory)
        (camp / "records").mkdir()
        events = [event(1, ["one", "two", "hidden", "unreferenced-hidden"]),
                  event(2, ["three"]), event(3, ["one"])]
        rows = [roll("one", "player"), roll("two", "gm"), roll("hidden", "gm_hidden"), roll("three", "aero")]
        (camp / "records/events.jsonl").write_text("\n".join(map(json.dumps, events)))
        (camp / "records/roll_log.jsonl").write_text("\n".join(map(json.dumps, rows)))
        s = E.build(campaign_dir=camp)
        assert [r["roll_id"] for r in s["dice_history"]] == ["one", "two", "three"]
        own, enemy = s["dice_history"][:2]
        assert own["modifier"] == -2 and own["raw_total"] == 7
        assert set(enemy) == {"roll_id", "purpose", "summary", "by", "redacted", "event_id", "time", "turn_no"}
        assert "hidden" not in json.dumps(s["dice_history"])
        s["dice_history"] *= 1500
        # Repeated event ids are allowed: one event can reference multiple unique rolls.
        documents = E.publish_set(s)
        assert E.doc_bytes(documents["state"]) <= E.STATE_BUDGET
        assert all(E.doc_bytes(p) <= E.PAGE_BUDGET for p in documents["pages"].values())
        history = [row for page in documents["pages"].values() if page["kind"] == "dice_history" for row in page["entries"]]
        assert history == s["dice_history"]
        assert documents == E.publish_set(s)
        legacy = copy.deepcopy(s)
        del legacy["dice_history"]
        E.publish_set(legacy)

if __name__ == "__main__":
    test_projection()
    print("PASS dice history projection, redaction, pagination and legacy snapshots")
