import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger
import batch

def fixture(root):
    root = Path(root)
    (root / "hidden").mkdir()
    lock = root / "lease.json"
    lock.write_text(json.dumps({"holder": "worker", "expires_ms": int(time.time()*1000)+60000}))
    events = []
    for n in range(12):
        events.append({"session": 1, "turn_no": 1, "world_time": "test", "actor": "gm", "kind": "ruling",
                       "summary": "public" if n % 2 == 0 else "PRIVATE_CANARY", "visibility": "player" if n % 2 == 0 else "gm_only",
                       "knowledge_type": "fact", "known_to": [], "caused_by": [f"${n}"] if n else [],
                       "roll_ids": [], "details": {}})
    request = {"batch_id": "turn-one", "expected_head": None, "expected_revision": 0, "events": events}
    return root, lock, request

with tempfile.TemporaryDirectory() as temporary:
    camp, lock, request = fixture(temporary)
    seen = []
    def crash(relative):
        seen.append(relative)
        raise RuntimeError("injected interruption")
    try:
        batch.apply(camp, request, lock, "worker", ledger, after_stream=crash)
    except RuntimeError:
        pass
    else:
        raise AssertionError("failure injection did not happen")
    try:
        ledger.load_all(camp)
    except ValueError:
        pass
    else:
        raise AssertionError("partial batch was readable")
    result = batch.apply(camp, request, lock, "worker", ledger)
    assert result["revision"] == 12
    assert batch.apply(camp, request, lock, "worker", ledger) == result
    events, problems = ledger.validate_all(camp)
    assert not problems and len(events) == 12
    assert "PRIVATE_CANARY" not in (camp / "records/events.jsonl").read_text()
    assert [e["event_id"] for e in events] == [f"evt_{n:04d}" for n in range(1, 13)]
    assert events[1]["caused_by"] == ["evt_0001"]
    for mutate in ("payload", "stale", "lock"):
        bad = copy.deepcopy(request)
        if mutate == "payload":
            bad["events"][0]["summary"] = "different"
        elif mutate == "stale":
            bad["batch_id"] = "another"
        else:
            lock.write_text(json.dumps({"holder": "other", "expires_ms": int(time.time()*1000)+60000}))
        try:
            batch.apply(camp, bad, lock, "worker", ledger)
        except ValueError:
            pass
        else:
            raise AssertionError(mutate)
print("PASS batch ordering, causal refs, visibility, crash recovery, replay, stale and lease rejection")
