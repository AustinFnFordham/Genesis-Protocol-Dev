"""NPC re-evaluation guard: bookkeeping that a GM looked at what changed. Synthetic events only.
Run: python3 -B development/gm_provider/test_npc_review.py
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import npc_review


def ev(n, kind="world_fact", actor="gm", **details):
    return {"event_id": f"evt_{n:04d}", "kind": kind, "actor": actor, "details": details}


def evaluation(since, changes=(), key="hold", **more):
    return {"npc": "dog_c", "since": since, "changes": list(changes), "outcome_key": key, "basis": "lure, do not charge; lying flat in the grass", **more}


def codes(evaluations, events):
    return sorted({p["code"] for p in npc_review.check(evaluations, events)})


def test_first_evaluation_needs_no_history():
    assert codes([evaluation(None, no_change_reason="first structured evaluation")], [ev(1)]) == []
    assert codes([evaluation(None)], [ev(1)]) == ["NPC_NO_CHANGE"]
    assert codes([evaluation("evt_0001", no_change_reason="x")], [ev(1)]) == ["NPC_SINCE"]


def test_events_naming_the_npc_cannot_be_ignored():
    events = [ev(1, "gm_ruling", npc_evaluations=[evaluation(None, no_change_reason="first")]),
              ev(2, "hp_change", target="dog_c", amount=7),          # it was hurt
              ev(3, "observation", actor="aero"),                    # unrelated
              ev(4, "npc_reaction", actor="dog_c")]                  # it acted
    assert codes([evaluation("evt_0001", no_change_reason="nothing changed")], events) == ["NPC_IGNORED_CHANGE"]
    assert codes([evaluation("evt_0001", ["evt_0002"])], events) == ["NPC_IGNORED_CHANGE"]
    assert codes([evaluation("evt_0001", ["evt_0002", "evt_0004"])], events) == []
    assert codes([evaluation("evt_0001", ["evt_0002", "evt_0003", "evt_0004"], key="withdraw")], events) == []
    assert codes([evaluation("evt_0001", ["evt_0002", "evt_0004", "evt_0009"])], events) == ["NPC_UNKNOWN_EVENT"]
    assert codes([evaluation("evt_0001", ["evt_0001", "evt_0002", "evt_0004"])], events) == ["NPC_UNKNOWN_EVENT"]


def test_third_identical_outcome_needs_a_causal_reason():
    events = [ev(1, "gm_ruling", npc_evaluations=[evaluation(None, no_change_reason="first")]),
              ev(2, "gm_ruling", npc_evaluations=[evaluation("evt_0001", no_change_reason="quiet round")]),
              ev(3, "environment_change", target="hatch")]
    assert codes([evaluation("evt_0002", ["evt_0003"])], events) == ["NPC_REPEAT"]
    assert codes([evaluation("evt_0002", ["evt_0003"], repeat_reason="the hatch is still bolted from inside; nothing to reach")], events) == []
    assert codes([evaluation("evt_0002", ["evt_0003"], key="probe_hatch")], events) == []      # a changed outcome needs no excuse
    two = events[:1]
    assert codes([evaluation("evt_0001", no_change_reason="quiet")], two) == []                # second in a row is fine


def test_shape_and_other_npcs_are_independent():
    events = [ev(1, "gm_ruling", npc_evaluations=[evaluation(None, no_change_reason="first")]), ev(2, "hp_change", target="dog_b")]
    assert codes([evaluation("evt_0001", no_change_reason="nothing names dog_c")], events) == []
    assert codes([{"npc": "dog_c", "since": "evt_0001"}], events) == ["NPC_NO_CHANGE", "NPC_SHAPE"]
    assert codes([evaluation("evt_0001", no_change_reason="x"), evaluation("evt_0001", no_change_reason="x")], events) == ["NPC_SHAPE"]
    assert codes([], events) == [] and codes(None, events) == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok npc review tests")
