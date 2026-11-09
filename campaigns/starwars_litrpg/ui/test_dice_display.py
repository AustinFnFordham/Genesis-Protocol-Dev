#!/usr/bin/env python3
"""Player-facing dice never carry unauthorized enemy mechanics (owner hardening item 1, 2026-11-09).
Run: python3 -I test_dice_display.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_state as es

def mk(by, formula="1d20+5", faces=(11,), mod=5, total=16, summary=None, nat20=False):
    r = {"requested_by": by, "formula": formula, "dice": [{"kept": list(faces)}], "modifiers": mod, "final_total": total, "nat20": nat20}
    if summary: r["summary"] = summary
    return r

def test_enemy_roll_shows_only_total():
    p = es.public_roll(mk("dog_1", summary="1d20+5 [11]+5 = 16 (success)"), "r1", "The dog's bite at Aero", ["11"])
    assert p["summary"] == "total 16" and p["redacted"] and "+5" not in json.dumps(p) and "success" not in json.dumps(p)

def test_gm_roll_for_anyone_is_redacted_and_crits_hidden():
    p = es.public_roll(mk("gm", total=25, faces=(20,), nat20=True, summary="1d20+5 [20]+5 = 25 (natural 20)"), "r2", "Attack from the dark", ["20"])
    assert p["summary"] == "total 25" and "natural" not in json.dumps(p)

def test_hidden_gm_tables_are_not_shown_at_all():
    assert es.public_roll(mk("gm_hidden", formula="1d6", total=3), "r3", "The dog inside, round 1", ["3"]) is None

def test_players_own_roll_is_full_but_without_hidden_dc_outcome():
    p = es.public_roll(mk("aero", formula="1d20-1", faces=(6,), mod=-1, total=5, summary="1d20-1 [6]-1 = 5 (failure)"), "r4", "Aero holds the door", ["6"])
    assert p["summary"] == "1d20-1 [6]-1 = 5" and not p.get("redacted")

def test_sandbox_exports_carry_no_enemy_modifiers():
    # The sandbox runs live only on the development branch; the live branch checks Hask Meadow's own record.
    runs = [r for r in ("sequencer_sandbox", "sequencer_sandbox_d", "hask_meadow_r2") if (es.ROOT / "campaigns" / "starwars_litrpg" / "runs" / r).is_dir()]
    assert runs
    for run in runs:
        d = es.build(campaign_dir=es.ROOT / "campaigns" / "starwars_litrpg" / "runs" / run, campaign_id=run)
        for r in d["rolls"]:
            if r["by"] != "aero":
                assert r["summary"].startswith("total ") and "[" not in r["summary"], r

if __name__ == "__main__":
    fails = 0
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            try: f(); print("ok", n)
            except Exception as e: fails += 1; print("FAIL", n, repr(e)[:300])
    print("all passed" if not fails else f"{fails} failed"); sys.exit(1 if fails else 0)
