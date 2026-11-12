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
    (root / "records").mkdir()
    (root / "hidden/dice_state.json").write_text(json.dumps({"seed": 17, "turn_no": 1, "draws_used": 1, "roll_count": 1}))
    (root / "records/roll_log.jsonl").write_text(json.dumps({"roll_id": "roll_existing"})+"\n")
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
    dice_before = (camp / "hidden/dice_state.json").read_bytes()
    rolls_before = (camp / "records/roll_log.jsonl").read_bytes()
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
    assert (camp / "hidden/dice_state.json").read_bytes() == dice_before
    assert (camp / "records/roll_log.jsonl").read_bytes() == rolls_before
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

# A second process holding the writer lock is rejected, without accepting a journal.
import subprocess
with tempfile.TemporaryDirectory() as temporary:
    camp, lock, request = fixture(temporary)
    holder = subprocess.Popen([sys.executable, "-c",
        "import fcntl,sys; f=open(sys.argv[1],'a'); fcntl.flock(f,fcntl.LOCK_EX); print('ready',flush=True); sys.stdin.read()",
        str(camp/"hidden/.ledger_writer.lock")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "ready"
        try:
            batch.apply(camp, request, lock, "worker", ledger)
        except ValueError as error:
            assert "local lock" in str(error)
        else:
            raise AssertionError("concurrent writer accepted")
        assert not (camp/"hidden/ledger_batch_pending.json").exists()
    finally:
        holder.communicate("")
        assert holder.returncode == 0

# A torn append is resumed byte-for-byte rather than truncated or rewritten.
with tempfile.TemporaryDirectory() as temporary:
    camp, lock, request = fixture(temporary)
    try:
        batch.apply(camp, request, lock, "worker", ledger, after_stream=lambda _: (_ for _ in ()).throw(RuntimeError()))
    except RuntimeError:
        pass
    accepted = json.loads((camp/"hidden/ledger_batch_pending.json").read_text())
    tail = accepted["streams"]["hidden/events.jsonl"]["tail"].encode()
    (camp/"hidden/events.jsonl").write_bytes(tail[:17])
    batch.apply(camp, request, lock, "worker", ledger)
    assert (camp/"hidden/events.jsonl").read_bytes() == tail
    assert not ledger.validate_all(camp)[1]
print("PASS separate-process writer rejection and torn-byte append recovery")
