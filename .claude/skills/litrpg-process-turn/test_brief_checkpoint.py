import copy
import json
from pathlib import Path
import tempfile
import brief as B

entry = B.run_entry("sandbox")
state, full = B.build(entry)
with tempfile.TemporaryDirectory() as root:
    checkpoint = Path(root) / "checkpoint.json"
    forged = copy.deepcopy(state)
    forged["hp_delta"] = 99999
    checkpoint.write_text(json.dumps(forged))
    _, repaired = B.build(entry, checkpoint=checkpoint)
    assert repaired["meta"]["build"]["mode"].startswith("full_replay")
    assert repaired["fields"] == full["fields"]
    checkpoint.write_text(json.dumps(state))
    _, resumed = B.build(entry, checkpoint=checkpoint)
    assert resumed["fields"] == full["fields"]
    compact = B.compact(full)
    assert compact["fields"] == full["fields"]
    assert compact["meta"]["ledger"] == full["meta"]["ledger"]
    assert "hidden" not in B.compact(B.build(entry, audience="player")[1])
print("PASS checkpoint payload verification, compact provenance and player isolation")
# Hidden typed state must not overwrite player-visible fields or presentation.
events = B.load_events(entry["path"])
state, _ = B.build(entry)
before = B.bundle(state, entry, "player", B.load_sheet(), {"valid": True, "problems": 0})
fake = copy.deepcopy(events[-1])
fake.update(event_id=f"evt_{B.seq(state['head']) + 1:04d}", kind="turn_context",
            visibility="gm_only", details={"hands": {"left": "SECRET_CANARY"}, "state_flags": ["SECRET_CANARY"]},
            summary="SECRET_CANARY", actor="aero")
changed = B.reduce(state, fake)
after = B.bundle(changed, entry, "player", B.load_sheet(), {"valid": True, "problems": 0})
assert before == after
assert "SECRET_CANARY" not in json.dumps(after)
print("PASS hidden typed context cannot alter the player projection")
