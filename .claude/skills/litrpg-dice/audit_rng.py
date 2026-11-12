#!/usr/bin/env python3
"""Read-only RNG replay and distribution diagnostics. Output is GM-private.
Uses an independent JavaScript mulberry32 reference for the random stream.
Never repairs dice state or rewrites historical rolls.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import roll

REFERENCE = """
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
let a = input.seed >>> 0;
const draws = Array.from({length: input.count}, () => {
  a = (a + 0x6D2B79F5) >>> 0;
  let t = Math.imul(a ^ (a >>> 15), a | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
});
process.stdout.write(JSON.stringify(draws));
"""


def reference(seed, count):
    p = subprocess.run(["node", "-e", REFERENCE], input=json.dumps({"seed": seed, "count": count}),
                       text=True, capture_output=True, check=True)
    return json.loads(p.stdout)


def audit(campaign, samples=100000):
    state = json.loads((campaign / "hidden/dice_state.json").read_text())
    records = [json.loads(line) for line in (campaign / "records/roll_log.jsonl").read_text().splitlines() if line.strip()]
    problems, verified, groups = [], 0, {}
    for record in records:
        groups.setdefault(record["turn_no"], []).append(record)
    latest_draws = 0
    counts = []
    for turn, rows in groups.items():
        count = sum(sum(term[2] for term in roll.parse(row["formula"]) if term[0] == "dice") *
                    (2 if row["mode"] != "normal" else 1) for row in rows)
        draws = iter(reference((state["seed"] ^ (turn * 0x9E3779B9)) & 0xFFFFFFFF, count))
        for row in rows:
            dice, alt, total, modifiers, single = roll.do_roll(row["formula"], row["mode"], lambda: next(draws))
            # Legacy rows predate original-face retention. Compare only recorded fields.
            recorded_dice = row.get("dice", [])
            for index, die in enumerate(dice):
                if index < len(recorded_dice) and "original" not in recorded_dice[index]:
                    die.pop("original", None)
            expected = {"dice": dice, "alt_dice": alt, "raw_total": total, "modifiers": modifiers,
                        "final_total": total + modifiers, "nat20": single and dice[0]["rolled"][0] == 20,
                        "nat1": single and dice[0]["rolled"][0] == 1}
            if any(row.get(key) != value for key, value in expected.items()):
                problems.append({"roll_id": row["roll_id"], "error": "record differs from independent replay"})
            else:
                verified += 1
            counts.append(int(row["roll_id"].rsplit("_", 1)[1]))
        if turn == state["turn_no"]:
            latest_draws = count
    if counts != list(range(1, state["roll_count"] + 1)):
        problems.append({"error": "roll count sequence incomplete or mismatched; cannot certify complete replay"})
    if latest_draws != state["draws_used"]:
        problems.append({"error": "current turn draw cursor differs from replay"})
    faces = Counter(1 + int(value * 20) for value in reference(0x12345678, samples))
    mean = sum(face * n for face, n in faces.items()) / samples
    return {"ok": not problems, "records": len(records), "verified": verified, "problems": problems,
            "sample": {"seed": "fixed synthetic seed", "count": samples, "mean_d20": mean,
                       "histogram": dict(sorted(faces.items())),
                       "chi_square": sum((faces[i] - samples / 20) ** 2 / (samples / 20) for i in range(1, 21))},
            "limits": "Checks deterministic replay, not unpredictability. Missing historical draws invalidate replay certification. Flat modifiers apply after raw dice."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    args = parser.parse_args()
    result = audit(args.campaign)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)
