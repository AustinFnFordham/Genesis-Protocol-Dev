import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "campaigns/starwars_litrpg/ui"))
import export_state as E
sys.path.insert(0, str(ROOT / ".claude/skills/litrpg-dice"))
import roll

faces = iter([0.1, 0.9])
dice, alternate, total, modifier, _ = roll.do_roll("1d20-2", "advantage", lambda: next(faces))
assert dice[0]["original"] == [3] and alternate == [19]
assert dice[0]["rolled"] == [19] and total == 19 and modifier == -2
faces = iter([0.1, 0.9])
dice, alternate, total, _, _ = roll.do_roll("1d20", "disadvantage", lambda: next(faces))
assert dice[0]["original"] == [3] and alternate == [19] and total == 3
state = E.build(campaign_dir=ROOT / "campaigns/starwars_litrpg/runs/hask_meadow_r2", campaign_id="hask_meadow_r2")
documents = E.publish_set(state)
size = E.doc_bytes(documents["state"])
assert E.STATE_BUDGET-size >= 12000, size
for kind in ("feed", "journal", "dice_history"):
    flattened = [entry for page in documents["pages"].values() if page["kind"] == kind for entry in page["entries"]]
    assert flattened == state[kind]
assert all(E.doc_bytes(page) <= E.PAGE_BUDGET for page in documents["pages"].values())
print("PASS 12KB snapshot margin, complete history navigation and unmodified advantage draw order", size)
