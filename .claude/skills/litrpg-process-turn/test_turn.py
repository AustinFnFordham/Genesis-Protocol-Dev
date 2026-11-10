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

# Byte budget: view/state never exceeds its budget; the newest feed entry survives; omissions are recorded.
sys.path.insert(0, str(TURN.parents[3] / "campaigns" / "starwars_litrpg" / "ui"))
import export_state as xs  # noqa: E402
big = {"revision": 1, "feed": [{"who": "gm", "event_id": f"evt_{i:04d}", "text": "\u00e9" * 3000} for i in range(100)],
       "journal": [{"event_id": f"evt_{i:04d}", "text": "x" * 2000} for i in range(100)]}
b = xs.bound(big, budget=60_000)
assert xs.doc_bytes(b) <= 60_000 and b["history"]["bytes"] == xs.doc_bytes(b), b["history"]
assert b["feed"][-1]["event_id"] == "evt_0099" and b["history"]["feed"]["omitted"] > 0 and b["history"]["journal"]["omitted"] > 0
assert b["history"]["feed"]["shown"] + b["history"]["feed"]["omitted"] == 100
small = xs.bound({"revision": 1, "feed": big["feed"][:2], "journal": []}, budget=60_000)
assert small["history"]["feed"]["omitted"] == 0 and len(small["feed"]) == 2
try:
    xs.bound({"revision": 1, "pad": "y" * 70_000, "feed": [], "journal": []}, budget=60_000); assert False
except ValueError:
    pass
print("ok state_byte_budget")

# An oversized export returns exit 5 and neither creates nor overwrites the output file.
import os
out = tempfile.mktemp(suffix=".json")
p = subprocess.run([sys.executable, "-I", str(TURN), "export", "sandbox", "--out", out, "--budget", "2000"], capture_output=True, text=True)
assert p.returncode == 5 and json.loads(p.stdout)["out"] is None and not os.path.exists(out), p.stdout
Path(out).write_text("keep me", encoding="utf-8")
p = subprocess.run([sys.executable, "-I", str(TURN), "export", "sandbox", "--out", out, "--budget", "2000"], capture_output=True, text=True)
assert p.returncode == 5 and Path(out).read_text(encoding="utf-8") == "keep me"
os.unlink(out)
print("ok oversized_export_exit5_writes_nothing")

# History pages: every document under its budget, nothing lost, earlier pages stable as the story grows,
# the snapshot preview is the newest tail, and the manifest names every page.
def mk(n):
    return {"revision": n, "campaign_id": "t", "feed": [{"who": "gm", "event_id": f"evt_{i:04d}", "text": "n" * 900} for i in range(n)],
            "journal": [{"event_id": f"evt_{i:04d}", "kind": "observation" if i % 2 else "speech", "text": "j" * 300} for i in range(n)]}
s1 = xs.publish_set(mk(60), state_budget=12_000, page_budget=8_000)
s2 = xs.publish_set(mk(75), state_budget=12_000, page_budget=8_000)
for ps in (s1, s2):
    assert xs.doc_bytes(ps["state"]) <= 12_000 and all(xs.doc_bytes(d) <= 8_000 for d in ps["pages"].values())
    for kind in ("feed", "journal"):
        man = ps["state"]["history"][kind]["pages"]
        ids = [x["event_id"] for m in man for x in ps["pages"][m["id"]]["entries"]]
        assert ids == [f"evt_{i:04d}" for i in range(ps["state"]["revision"])], kind
        assert all(ps["pages"][m["id"]]["hash"] == m["hash"] for m in man)
    assert ps["state"]["feed"][-1]["event_id"] == f"evt_{ps['state']['revision'] - 1:04d}"
    assert ps["state"]["history"]["journal"]["observations"] == ps["state"]["revision"] // 2
full1 = [k for k in s1["pages"] if k != "feed-%04d" % len(s1["state"]["history"]["feed"]["pages"]) and k != "journal-%04d" % len(s1["state"]["history"]["journal"]["pages"])]
assert full1 and all(s1["pages"][k]["hash"] == s2["pages"][k]["hash"] for k in full1)
try:
    xs.paginate([{"event_id": "evt_0001", "text": "x" * 9000}], "feed", 8_000); assert False
except ValueError:
    pass
print("ok history_pages_bounded_and_stable")

# Publication is separate from resolution: publish plans from the committed revision, is repeatable, and an older
# retry never overwrites a newer Datapad.
d = tempfile.mkdtemp()
c, r = run("publish", "sandbox", "--outdir", d, "--allow-unpushed")
assert c == 0 and r["ok"] and r["state"]["bytes"] <= r["state"]["budget"] and r["pages"], r
snap = json.loads(Path(r["state"]["file"]).read_text(encoding="utf-8"))
assert snap["history"]["published"]["revision"] == snap["revision"]
cur = tmp(json.dumps(snap))
c, r2 = run("publish", "sandbox", "--current", cur, "--outdir", d, "--allow-unpushed")
assert c == 0 and r2["already_published"] and r2["pages"] == [], r2
newer = dict(snap); newer["revision"] = snap["revision"] + 5
c, r3 = run("publish", "sandbox", "--current", tmp(json.dumps(newer)), "--outdir", d, "--allow-unpushed")
assert c == 6 and not r3["ok"] and "stale" in r3["reason"], r3
print("ok publish_repeatable_and_revision_fenced")
