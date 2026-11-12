import json
from pathlib import Path
import tempfile
import audit_rng as A
import roll

with tempfile.TemporaryDirectory() as root:
    camp = Path(root)
    roll.save_state(camp / "hidden/dice_state.json", {"seed": 3, "turn_no": 0, "draws_used": 0, "roll_count": 0})
    for formula, mode in [("1d20-2", "normal"), ("1d20+3", "advantage"), ("4d6kh3", "normal")]:
        assert roll.main(["--campaign", str(camp), formula, "--mode", mode]) == 0
    assert A.audit(camp, samples=1000)["ok"]
    path = camp / "records/roll_log.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["final_total"] += 1
    path.write_text("\n".join(json.dumps(row) for row in rows))
    result = A.audit(camp, samples=1000)
    assert not result["ok"] and result["problems"][0]["roll_id"] == rows[0]["roll_id"]
print("PASS independent audit detects altered totals and replays modifiers/advantage/keep-high")
