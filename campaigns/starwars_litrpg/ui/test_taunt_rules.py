"""TB4 grants behind owner switches (tb4_rules.py). TB4-03/04/05 rule side."""
import copy, json, sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import tb4_rules as R  # noqa: E402

ctx = json.loads((H.parents[2] / "development/.qa/state_round1.json").read_text())["turn_context"]
before = copy.deepcopy(ctx)
assert R.apply_switches(ctx, {}) is ctx and R.apply_switches(ctx, {"tb4_taunt": False}) == before, "switch off: unchanged"
on = R.apply_switches(ctx, {"tb4_taunt": True})
t = [o for o in on["options"] if o["id"] == "taunt"]
assert len(t) == 1 and t[0]["slot"] == "bonus_action" and t[0]["needs_target"], "switch on in combat with a visible foe: one Taunt bonus option"
assert ctx == before, "the input context is never mutated"
assert [o for o in on["options"] if o["id"] != "taunt"] == before["options"], "GM options are kept as published"
again = R.apply_switches(on, {"tb4_taunt": True})
assert sum(o["id"] == "taunt" for o in again["options"]) == 1, "never duplicated"
scene = dict(ctx, mode="scene")
assert not any(o["id"] == "taunt" for o in R.apply_switches(scene, {"tb4_taunt": True}).get("options", [])), "no Taunt outside combat"
nofoe = dict(ctx, visible=[dict(v, hostile=False) for v in ctx.get("visible", [])])
assert not any(o["id"] == "taunt" for o in R.apply_switches(nofoe, {"tb4_taunt": True})["options"]), "no Taunt without a visible foe"
assert R.resolve_taunt(15, 14)["success"] and not R.resolve_taunt(14, 14)["success"], "contested: ties go to the target"
eff = R.resolve_taunt(18, 3)["effect"]
assert eff["compels"] is False and "disadvantage" in eff["mechanic"] and "anyone other than the taunter" in eff["mechanic"], "effect: disadvantage only, never compels"
for bad in [(None, 3), (3.5, 2), ("12", 3)]:
    try:
        R.resolve_taunt(*bad)
    except ValueError:
        pass
    else:
        raise AssertionError("non-roll totals must be refused")
print("tb4 rules tests ok")
