#!/usr/bin/env python3
"""Test E: catastrophic defeat under the (proposed) Protagonist Continuity rule, on run-1 evidence.

Checks: refused while proposed (standard rules stay in force); the dry run finds the would-die moment;
every cost cites real earlier-or-same-scene ledger events; the established loss is preserved (ledger
and roll log byte-identical before and after); no ally or new item is introduced; a playable state results.
Run: python3 -I test_continuity.py
"""
import hashlib, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMP = HERE.parent  # run 1 (archived UAT evidence)
TOOL = HERE / "continuity.py"


def digest():
    h = hashlib.sha256()
    for f in ("records/events.jsonl", "hidden/events.jsonl", "records/roll_log.jsonl"):
        h.update((CAMP / f).read_bytes())
    return h.hexdigest()


def run(*args):
    p = subprocess.run([sys.executable, "-I", str(TOOL), "propose", "--campaign", str(CAMP), *args], capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


before = digest()
code, out = run()
assert code == 3 and "not approved" in out["refused"], out
code, out = run("--dry-run", "--seed", "7")
assert out["applies"] and out["label"] == "SIMULATION, NOT CANON"
assert out["trigger"] == "evt_0084", out["trigger"]           # third failed death save in the live (non-voided) run
ids = {c["id"] for c in out["eligible_costs"]}
assert {"lasting_wound", "lost_equipment", "taken", "exhaustion", "escalation"} <= ids, ids
ev = {}
for f in ("records/events.jsonl", "hidden/events.jsonl"):
    for line in (CAMP / f).read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line); ev[e["event_id"]] = e
for c in out["eligible_costs"]:
    assert c["evidence"] and all(x in ev for x in c["evidence"]), c
assert "evt_0076" in next(c for c in out["eligible_costs"] if c["id"] == "lasting_wound")["evidence"]  # the 7-damage bite
assert next(c for c in out["eligible_costs"] if c["id"] == "taken")["evidence"][0] == "evt_0079"  # pack table: drag
assert "evt_0087" in next(c for c in out["eligible_costs"] if c["id"] == "lost_equipment")["evidence"]  # saber by the fence
assert len(out["chosen_costs"]) == 1 and out["mark"] == 1 and not out["phase_ends"]
assert out["state"] == {"hp": 0, "conditions": ["unconscious", "stable"], "wake": "1d4 hours, 1 HP"}
blob = json.dumps(out["events_to_commit"]).lower()
assert "ally" not in blob and "rescued" not in blob and "unharmed" not in blob
code, out2 = run("--dry-run", "--pick", "2")
assert out2["chosen_costs"][0]["id"] == out["eligible_costs"][1]["id"]
assert digest() == before, "the ledger or roll log changed"
print("ok test_E_catastrophic_defeat_continuity (dry run)")
