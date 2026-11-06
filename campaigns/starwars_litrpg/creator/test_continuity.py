#!/usr/bin/env python3
"""Test E: catastrophic defeat under Protagonist Continuity v2, on run-1 evidence (read-only).

Checks: the would-die moment is found; survival paths and costs cite real ledger events; dice sizes
are handed to the GM (no rolling here); mark n applies n cumulative costs with grievous wounds from
mark 2/3 and NO automatic termination; the window ends only when arc AND level 3 are both met, with
an explicit expiring step; established loss is preserved (ledger + roll log byte-identical); no ally
or escape is invented. Run: python3 -I test_continuity.py
"""
import hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMP = HERE.parent  # run 1 (archived UAT evidence)
TOOL = HERE / "continuity.py"


def digest(c):
    h = hashlib.sha256()
    for f in ("records/events.jsonl", "hidden/events.jsonl", "records/roll_log.jsonl"):
        h.update((c / f).read_bytes())
    return h.hexdigest()


def run(cmd, camp, *args):
    p = subprocess.run([sys.executable, "-I", str(TOOL), cmd, "--campaign", str(camp), *args], capture_output=True, text=True)
    assert p.returncode in (0, 3), p.stderr
    return json.loads(p.stdout)


def synthetic(camp, extra):
    tmp = Path(tempfile.mkdtemp())
    for d in ("records", "hidden"):
        shutil.copytree(camp / d, tmp / d)
    with open(tmp / "hidden" / "events.jsonl", "a", encoding="utf-8") as f:
        for i, e in enumerate(extra):
            base = {"event_id": f"evt_{9000 + i}", "session": 1, "turn_no": 9, "world_time": "later", "actor": "gm", "summary": e["kind"],
                    "visibility": "gm_only", "knowledge_type": "fact", "known_to": [], "caused_by": [], "roll_ids": [], "tags": [], "details": {}}
            base.update(e); f.write(json.dumps(base) + "\n")
    return tmp


before = digest(CAMP)

# GM path: no dice in the tool, sizes handed over
need = run("propose", CAMP)
assert need["needs_rolls"] and need["mark"] == 1 and need["cost_count"] == 1, need
assert need["survival_die"] == "1d2" and [p["id"] for p in need["survival_paths"]] == ["taken", "left_for_dead"], need
assert need["survival_paths"][0]["evidence"] == ["evt_0079"]                     # the pack table said drag
ids = {c["id"]: c for c in need["eligible_costs"]}
assert set(ids) == {"lasting_wound", "lost_equipment", "exhaustion", "escalation"}, ids
assert ids["lasting_wound"]["evidence"] == ["evt_0076"] and not ids["lasting_wound"]["grievous"]
assert ids["lost_equipment"]["evidence"] == ["evt_0087"]

# Applying the GM's rolls
out = run("propose", CAMP, "--path-roll", "1", "--cost-rolls", "2")
assert out["trigger"] == "evt_0084" and out["survival_path"]["id"] == "taken" and [c["id"] for c in out["chosen_costs"]] == ["lost_equipment"]
assert out["state"] == {"hp": 0, "conditions": ["unconscious", "stable"], "wake": "1d4 hours, 1 HP"}
blob = json.dumps(out["events_to_commit"]).lower()
assert "rescued" not in blob and "unharmed" not in blob and " ally" not in blob

# Escalation: a third defeat applies three cumulative costs, grievous wounds, and does NOT end protection
tmp = synthetic(CAMP, [{"kind": "continuity_invoked", "details": {"target": "aero", "mark": 1}, "caused_by": ["evt_0001"]},
                       {"kind": "continuity_invoked", "details": {"target": "aero", "mark": 2}, "caused_by": ["evt_0002"]}])
out3 = run("propose", tmp, "--dry-run", "--seed", "3")
assert out3["mark"] == 3 and len(out3["chosen_costs"]) == 3, out3["chosen_costs"]
lw = [c for c in out3["eligible_costs"] if c["id"] == "lasting_wound"][0]
assert lw["grievous"] and "bacta" in lw["effect"]
assert any(e["kind"] == "lasting_injury" and e["details"]["grievous"] for e in out3["events_to_commit"])
assert run("status", tmp)["window"] == "active"

# Window: arc alone is not enough; arc + level 3 meets the conditions; expired means mortal
tmp2 = synthetic(CAMP, [{"kind": "arc_completed", "details": {"arc": "hask_meadow"}}])
assert not run("status", tmp2, "--level", "2")["end_conditions_met"]
st = run("status", tmp2, "--level", "3")
assert st["end_conditions_met"] and st["next_step"].startswith("commit continuity_expiring")
tmp3 = synthetic(CAMP, [{"kind": "continuity_expiring", "details": {"target": "aero"}}, {"kind": "continuity_expired", "details": {"target": "aero"}}])
gone = run("propose", tmp3, "--path-roll", "1", "--cost-rolls", "1")
assert gone["applies"] is False and "permanent" in gone["reason"]

assert digest(CAMP) == before, "the run-1 ledger or roll log changed"
print("ok test_E_catastrophic_defeat_continuity_v2")
