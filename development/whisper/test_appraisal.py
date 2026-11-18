"""Algorithm B tests on TB4-MORAL-001 and CMP-001 (TB4-13, -14, -15, -17, -26, -27, -28)."""
import copy, json, sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import appraisal as B  # noqa: E402

cases = json.loads((H / "fixtures/tb4_moral_001.json").read_text())["cases"]
frozen = copy.deepcopy(cases)
M = {k: B.moral(v)["finding"] for k, v in cases.items()}
# TB4-13 attempted unjustified harm that misses still matters
assert M["attempted_harm_missed"] == "attempted_unjustified_harm", M
# TB4-27 same dice outcome (miss), different intent/justification -> different finding
assert M["attempted_harm_missed_defensive"] == "justified_force", M
# TB4-14 failed rescue in good faith is not a fault
assert M["failed_rescue"] == "good_faith_effort_failed", M
# TB4-15 omission needs awareness, capacity, risk and alternatives
assert M["declined_help_aware_capable"] == "omission_relevant", M
unaware = B.moral(cases["declined_help_unaware"])
assert unaware["finding"] == "omission_unresolved" and "awareness" in unaware["missing"], unaware
# compelled act
assert M["compelled"] == "compelled_mitigates", M
# TB4-28 same emotion, opposite conduct: emotion decides nothing, conduct does
assert M["anger_spares"] != M["anger_strikes_surrendered"] and M["anger_strikes_surrendered"] == "unjustified_harm", M
for k, v in cases.items():
    r = B.appraise(v)
    assert r["canonical"] is False and all(c["status"] == "proposed" for c in r["psychological"]), "everything is a candidate"
    assert all(e["event_id"] in [x["event_id"] for x in v] for e in [{"event_id": c} for c in r["moral"]["citations"]]), "citations exist"
    def numbers(o):
        if isinstance(o, bool): return []
        if isinstance(o, (int, float)): return [o]
        if isinstance(o, dict): return [n for v in o.values() for n in numbers(v)]
        if isinstance(o, list): return [n for v in o for n in numbers(v)]
        return []
    assert numbers(r) == [], "no scores, weights or meters anywhere in an appraisal"
# TB4-26 the PC's feeling is never imposed: candidates carry player choices, and none without support
p = B.psychological(cases["failed_rescue"])
assert p[0]["status"] == "proposed" and "reject" in p[0]["player_choices"] and p[0]["basis"] == ["evt_0202"]
assert B.psychological(cases["anger_spares"])[0]["candidate"] == "no_supported_change"
# social: only those who perceived it; private context never visible
s = B.social(cases["attempted_harm_missed"])
assert [x["observer"] for x in s] == ["wick"] and s[0]["private_context_visible"] is False and "evt_0103" in s[0]["perceived"]
assert B.social(cases["declined_help_aware_capable"]) == [], "no one else saw Aero walk on"
# TB4-17 memories: an absent observer remembers nothing; a listener remembers a claim as heard
cmp = json.loads((H / "fixtures/cmp001_ten_missing_crates.json").read_text())
assert B.memories(cmp["events"], "neri", cmp["entities"]) == []
m7 = B.memories(cmp["events"], "dockworker_7", cmp["entities"])
assert [(m["source_event"], m["channel"]) for m in m7] == [("evt_0003", "heard")], m7
assert not any(m["type"] == "intention" for m in B.memories(cmp["events"], "aero", cmp["entities"])), "private context is not an episodic memory"
assert cases == frozen, "accepted events never mutated"
print("appraisal tests ok")
