#!/usr/bin/env python3
"""Regression tests for brief.py (read-only). Hask Meadow run 2 is the regression scenario; nothing is written to it.
Run: python3 -I .claude/skills/litrpg-process-turn/test_brief.py"""
import copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import brief as B

E = B.run_entry("hask_meadow_r2")
EV = B.load_events(E["path"])
SHEET = B.load_sheet()
FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILS.append(name)


def at(head, audience="gm"):
    s = B.fold(B.empty(E["id"]), [e for e in EV if B.seq(e["event_id"]) <= B.seq(head)])
    return s, B.bundle(s, E, audience, SHEET, {"valid": True, "problems": 0})


s, gm = at("evt_0127"); _, pl = at("evt_0127", "player")
f, fp = gm["fields"], pl["fields"]
# Ruddick's countdown: typed value kept as recorded, never replaced from prose
c = f["clock.ruddick_lift"]
check("ruddick clock keeps last typed value (evt_0079, 28)", c["source"] == "evt_0079" and c["value"].get("clock_minutes_left") == 28, c)
check("ruddick clock flagged stale_suspect with prose refs", c["status"] == "stale_suspect" and "evt_0127" in c["refs"], c)
check("ruddick clock never takes the prose value 24", c["value"].get("clock_minutes_left") != 24)
check("player clock refs contain no hidden ids", all(s["lines"][r]["vis"] != "gm_only" for r in fp["clock.ruddick_lift"].get("refs", [])))
# Aero's hands and equipment
h = f["aero.hands"]
check("hands sourced from evt_0052 and marked uncertain", h["source"] == "evt_0052" and h["status"] == "uncertain", h)
check("hands uncertainty cites the saber deactivation and the hold", set(h["refs"]) >= {"evt_0114", "evt_0117"}, h)
check("flags: saber flag removed, blaster drawn", f["aero.flags"]["status"] == "typed" and f["aero.flags"]["value"] == ["blaster_drawn"], f["aero.flags"])
check("equipment is labelled static", f["aero.equipment"]["status"] == "typed_static")
# Wick's private intentions
check("wick intent never typed (gm)", f["npc.wick.intent"]["status"] == "missing" and f["npc.wick.intent"]["value"] is None)
check("wick intent: player refs are only Aero's public Insight reads", fp["npc.wick.intent"]["refs"] == ["evt_0026", "evt_0080"], fp["npc.wick.intent"])
check("wick intent: gm refs include hidden material", any(s["lines"][r]["vis"] == "gm_only" for r in f["npc.wick.intent"]["refs"]))
# Uncertain creature positions
cp = f["creatures.positions"]
check("creature positions: gm gets latest hidden positions ref, marked uncertain", cp["status"] == "uncertain" and cp["source"] == "evt_0122", cp)
check("creature positions: player told unknown, refs public only", fp["creatures.positions"]["status"] == "unknown_to_player"
      and all(s["lines"][r]["vis"] != "gm_only" for r in fp["creatures.positions"]["refs"]), fp["creatures.positions"])
check("comm channel typed open (evt_0097)", f["comm.channel"]["value"] == "open" and f["comm.channel"]["source"] == "evt_0097")
check("light/visibility explicitly missing", f["scene.light_and_visibility"]["status"] == "missing")
# Provenance
m = gm["meta"]["ledger"]
check("gm bundle tied to exact head and chain", m["head"] == "evt_0127" and len(m["chain"]) == 64 and m["valid"])
check("player bundle carries no global head or chain", "head" not in pl["meta"]["ledger"] and "chain" not in pl["meta"]["ledger"])
check("player bundle has no hidden section", "hidden" not in pl)
# Turn 6 -> 7 causal coverage: every earlier event turn 7 cites is reachable from the bundle
_, g6 = at("evt_0092")
txt = json.dumps(g6)
cited = sorted({c for e in EV if "evt_0093" <= e["event_id"] <= "evt_0110" for c in e["caused_by"] if c < "evt_0093"})
check("turn 7 cited causes all present in turn-6 bundle", all(c in txt for c in cited), [c for c in cited if c not in txt])
# Conflict: two typed sources disagree -> conflict, not a guess
s2 = copy.deepcopy(s)
fake = dict(EV[-1]); fake.update(event_id="evt_0128", kind="object_interaction", actor="aero", visibility="player",
                                 details={"object": "ignite_saber", "grants": ["saber_ignited"]}, summary="synthetic test event")
s2 = B.reduce(s2, fake)
check("conflicting typed sources reported as conflict", B.fields(s2, SHEET, "gm")["aero.flags"]["status"] == "conflict")
# Stale / duplicate / out of order
try:
    B.reduce(copy.deepcopy(s), EV[-1]); check("duplicate rejected", False)
except B.Rejected:
    check("duplicate rejected", True)
print(f"\n{len(FAILS)} failed")
sys.exit(1 if FAILS else 0)
