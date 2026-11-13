#!/usr/bin/env python3
"""Generate the ignored fixtures the browser suites expect under development/.qa (read-only on campaigns).

  .qa/state_hask.json     bounded snapshot of the current Hask Meadow public record
  .qa/state_round1.json   the same snapshot with the round-1 combat context fixture (test_datapad_ui.cjs)
  .qa/ui/view/*.json      full publish set (history and player-experience suites)
  .qa/dice_ui/*.json      synthetic dice-history set with one older page (test_dice_history_ui.cjs)
"""
import json
import subprocess
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "campaigns/starwars_litrpg/ui"
QA = ROOT / "development/.qa"
sys.path.insert(0, str(UI))
import export_state as E   # noqa: E402


def dump(directory, documents):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "state.json").write_text(json.dumps(documents["state"]))
    for name, page in documents["pages"].items():
        (directory / f"{name}.json").write_text(json.dumps(page))


def main():
    state = E.build(campaign_dir=ROOT / "campaigns/starwars_litrpg/runs/hask_meadow_r2", campaign_id="hask_meadow_r2")
    documents = E.publish_set(state)
    dump(QA / "ui/view", documents)
    # The single-snapshot suites use the worker's own export (it adds the processor block the page reads).
    subprocess.run([sys.executable, "-B", str(ROOT / ".claude/skills/litrpg-process-turn/turn.py"), "export", "hask_meadow_r2",
                    "--out", str(QA / "state_hask.json")], check=True, capture_output=True)
    exported = json.loads((QA / "state_hask.json").read_text())
    round1 = dict(exported, turn_context=json.loads((UI / "fixtures/hask_round1.json").read_text()))
    (QA / "state_round1.json").write_text(json.dumps(round1))
    (QA / "shots").mkdir(exist_ok=True)
    def roll(rid, who, purpose="[action] test"):
        return {"roll_id": rid, "requested_by": who, "purpose": purpose, "turn_no": 1, "formula": "1d20-2", "mode": "normal",
                "dice": [{"kept": [7]}], "raw_total": 7, "modifiers": -2, "final_total": 5, "nat1": False}
    with tempfile.TemporaryDirectory() as directory:
        camp = Path(directory)
        (camp / "records").mkdir()
        (camp / "records/events.jsonl").write_text(json.dumps(
            {"event_id": "evt_0001", "kind": "player_declaration", "details": {}, "summary": "public", "world_time": "test", "actor": "aero",
             "visibility": "player", "knowledge_type": "fact", "caused_by": [], "roll_ids": ["roll_history_one", "two", "hidden"]}))
        (camp / "records/roll_log.jsonl").write_text("\n".join(json.dumps(r) for r in (
            roll("roll_history_one", "aero"), roll("two", "aero"), roll("hidden", "gm_hidden", "SECRET_CANARY"))))
        synthetic = E.build(campaign_dir=camp)
    synthetic["dice_history"] = synthetic["dice_history"][:1] + synthetic["dice_history"][1:] * 300
    dump(QA / "dice_ui", E.publish_set(synthetic))
    print("fixtures ready under development/.qa")


if __name__ == "__main__":
    main()
