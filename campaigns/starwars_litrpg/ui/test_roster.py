#!/usr/bin/env python3
"""Roster rules for the Genesis Datapad. Run: python3 ui/test_roster.py"""
import sys, copy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_state as ex

base = ex.la.player_events()
def ev(kind, **d):
    return {"event_id": "evt_t", "kind": kind, "actor": "gm", "world_time": "Day 1", "summary": kind, "knowledge_type": "fact", "known_to": [], "tags": [], "details": d}

def ids(evs): return [m["id"] for m in ex.build(evs)["roster"]]

# 1. Real public ledger: Aero only, even though Varon/Rassira runtimes exist elsewhere.
assert ids(base) == ["aero"], ids(base)
# 2. Join adds a member, mechanics pending, and no stats leak into the character panel.
j = base + [ev("party_joined", member_id="varon", name="Varon", line="Chiss Trooper")]
st = ex.build(j)
assert ids(j) == ["aero", "varon"]
assert [m for m in st["roster"] if m["id"] == "varon"][0]["mechanics"] == "pending"
assert st["character"]["name"].startswith("Aeleron") and st["active_actor"] == "aero"
# 3. Leaving removes; Aero can be neither replaced nor removed.
assert ids(j + [ev("party_left", member_id="varon")]) == ["aero"]
assert ids(base + [ev("party_joined", member_id="aero", name="Impostor"), ev("party_left", member_id="aero")]) == ["aero"]
assert ex.build(base + [ev("party_joined", member_id="aero", name="Impostor")])["roster"][0]["name"].startswith("Aeleron")
# 4. Join/leave events never appear in the journal.
assert not [x for x in st["journal"] if x["kind"].startswith("party_")]
print("ok roster tests")
