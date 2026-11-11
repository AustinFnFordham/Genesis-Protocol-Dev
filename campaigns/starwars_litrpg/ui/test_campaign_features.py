#!/usr/bin/env python3
"""Campaign-scoped features (Jedi Fundamentals). Run: python3 ui/test_campaign_features.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_state as ex

RULE = Path(__file__).resolve().parents[1] / "creator" / "jedi_fundamentals.json"
rule = json.loads(RULE.read_text(encoding="utf-8"))
NAME = rule["feature"]["name"]

# 1. The grant is explicit: Aero is named; nobody else is.
assert [g["character"] for g in rule["granted_to"]] == ["aero"]
assert all(g.get("evidence") and g.get("granted_by") for g in rule["granted_to"])
# 2. Owner limits are recorded as stated.
lim = rule["limits"]
assert (lim["max_weight_lb"], lim["range_ft"], lim["force_point_cost"], lim["objects_at_once"]) == (10, 30, 0, 1)
assert set(rule["not_granted"]) == {"power_force_pull", "power_force_push"}
# 3. Shown for the granted actor in a run-2 style campaign, appended after the sheet's own features.
got = ex.campaign_features("aero", "hask_meadow_r2")
assert [f["name"] for f in got] == [NAME], got
# 4. Not granted to anyone unnamed, and not applied to the run-1 archive.
assert ex.campaign_features("wick", "hask_meadow_r2") == []
assert ex.campaign_features("varon", "hask_meadow_r2") == []
assert ex.campaign_features("aero", None) == [] and ex.campaign_features("aero", "starwars_litrpg") == []
# 5. It is a feature, never a power: the sheet's powers are untouched in the built state.
run = Path(__file__).resolve().parents[1] / "runs" / "hask_meadow_r2"
st = ex.build(campaign_dir=str(run), campaign_id="hask_meadow_r2")
assert [p["name"] for p in st["character"]["powers"]] == ["Battle Insight", "Burst"], st["character"]["powers"]
assert st["character"]["features"][-1]["name"] == NAME
assert NAME not in [f["name"] for f in ex.build()["character"]["features"]]
# 6. A rule that is not approved grants nothing.
orig = RULE.read_text(encoding="utf-8")
try:
    RULE.write_text(orig.replace('"approved_provisional"', '"proposed"'), encoding="utf-8")
    assert ex.campaign_features("aero", "hask_meadow_r2") == []
finally:
    RULE.write_text(orig, encoding="utf-8")
print("ok: campaign features")
