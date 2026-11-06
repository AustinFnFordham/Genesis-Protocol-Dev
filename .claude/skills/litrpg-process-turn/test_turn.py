#!/usr/bin/env python3
"""Processor helper tests: Test F (narration integrity lint), stale-revision and archived-run guards,
recovery classification. Run: python3 -I test_turn.py"""
import json, subprocess, sys, tempfile
from pathlib import Path

TURN = Path(__file__).resolve().parent / "turn.py"


def run(*a):
    p = subprocess.run([sys.executable, "-I", str(TURN), *a], capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


def tmp(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False); f.write(text); f.close(); return f.name


# Test F: severe but non-permanent injury passes; invented lasting damage and invented death fail.
ok_text = ("The dog's jaws close on your thigh above the knee and wrench sideways. Blood sheets down your leg, hot, too fast. "
           "The leg will not hold you; you go down hard on the gravel, the world tilting.")
c, r = run("lint", "sandbox", tmp(ok_text))
assert c == 0 and r["ok"], r
c, r = run("lint", "sandbox", tmp("Its teeth meet through the shattered femur and the leg is bitten clean off."))
assert c == 3 and len(r["problems"]) >= 2 and all("lasting_injury" in p for p in r["problems"]), r
c, r = run("lint", "sandbox", tmp("Aero dies in the grass."))
assert c == 3 and "not dead" in r["problems"][0], r
print("ok test_F_horror_narration_integrity")

# Stale action and archived run are sent back without dice.
info = json.loads(subprocess.run([sys.executable, "-I", str(TURN), "info", "sandbox"], capture_output=True, text=True).stdout)
c, r = run("check", "sandbox", tmp(json.dumps({"text": "Dodge.", "actor": "aero", "campaign_id": "sandbox", "based_on_revision": info["revision"] - 1})))
assert c == 3 and r["verdict"] == "needs_revision" and "moved on" in r["reason"], r
c, r = run("check", "starwars_litrpg", tmp(json.dumps({"text": "Dodge.", "actor": "aero", "based_on_revision": 1})))
assert c == 3 and r["verdict"] == "failed", r
print("ok stale_and_archived_guards")

# Recovery: the committed sandbox action is complete; an unknown one is none.
c, r = run("recover", "sandbox", "sbtest-001")
assert r["status"] == "complete" and r["rolls"], r
c, r = run("recover", "sandbox", "nope")
assert r["status"] == "none"
print("ok recovery_classification")
