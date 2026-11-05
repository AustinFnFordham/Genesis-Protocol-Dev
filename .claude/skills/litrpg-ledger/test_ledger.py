import json, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent

def run(camp, *args, ok=True):
    p = subprocess.run([sys.executable, str(HERE / "ledger.py"), "--campaign", str(camp), *args], capture_output=True, text=True)
    assert (p.returncode == 0) == ok, (args, p.stdout, p.stderr)
    return p.stdout if args[0] == "show" else json.loads(p.stdout or p.stderr)

def add(camp, summary, *extra, ok=True):
    return run(camp, "add", "--kind", "test", "--summary", summary, "--world-time", "Day 1", *extra, ok=ok)

def test_all():
    with tempfile.TemporaryDirectory() as t:
        c = Path(t); (c / "records").mkdir(); (c / "hidden").mkdir()
        (c / "records" / "roll_log.jsonl").write_text(json.dumps({"roll_id": "roll_t0_1"}) + "\n")
        e1 = add(c, "public thing")["event"]; assert e1["event_id"] == "evt_0001"
        e2 = add(c, "secret thing", "--visibility", "gm_only")["event"]; assert e2["event_id"] == "evt_0002"
        assert (c / "hidden" / "events.jsonl").exists() and "secret" not in (c / "records" / "events.jsonl").read_text()
        # public event caused by hidden event: allowed, redacted in player view
        e3 = add(c, "visible consequence", "--caused-by", "evt_0002", "--roll", "roll_t0_1")["event"]
        out = run(c, "show", "--as", "player")
        assert "secret" not in out and "evt_0002" not in out and "visible consequence" in out
        assert "secret thing" in run(c, "show", "--as", "gm")
        # ancestry: unknown or future cause rejected
        add(c, "x", "--caused-by", "evt_0099", ok=False)
        # unknown roll rejected
        add(c, "x", "--roll", "roll_nope", ok=False)
        # belief needs known_to; supplied is fine
        add(c, "rumor", "--type", "belief", ok=False)
        assert add(c, "rumor", "--type", "belief", "--known-to", "companion_a")["status"] == "committed"
        # idempotency: duplicate does not append
        a = add(c, "once", "--idem", "k1")["event"]; b = add(c, "once again", "--idem", "k1")
        assert b["status"] == "duplicate" and b["event"]["event_id"] == a["event_id"]
        assert run(c, "validate")["problems"] == []
        # tampering is caught: future-pointing cause, and gm_only in public file
        pub = c / "records" / "events.jsonl"
        lines = [json.loads(l) for l in pub.read_text().splitlines()]
        lines[0]["caused_by"] = ["evt_0003"]; lines[1]["visibility"] = "gm_only"
        pub.write_text("\n".join(json.dumps(l) for l in lines) + "\n")
        bad = run(c, "validate", ok=False)
        msgs = " ".join(m for _, m in bad["problems"])
        assert "not earlier" in msgs and "public file" in msgs
        add(c, "blocked while invalid", ok=False)   # refuses to append onto a broken ledger

def test_moral_evaluations():
    def moral(c, facets, *extra, ok=True, subject_kind="pc"):
        d = {"subject": "aero", "subject_kind": subject_kind, "facets": facets}
        return run(c, "add", "--kind", "moral_evaluation", "--summary", "m", "--world-time", "Day 1",
                   "--details", json.dumps(d), "--visibility", "gm_only", *extra, ok=ok)
    with tempfile.TemporaryDirectory() as t:
        c = Path(t); (c / "records").mkdir(); (c / "hidden").mkdir()
        good = {"action": "spared a wounded guard", "intent_source": "declared", "intent": "he is no threat now",
                "knowledge": "believed unarmed", "consequences_accidental": "unknown"}
        e1 = moral(c, good)["event"]
        # undeclared intent must be empty; npc_soul is invalid for a PC; missing action rejected
        moral(c, {"action": "x", "intent_source": "undeclared", "intent": "guessed"}, ok=False)
        moral(c, {"action": "x", "intent_source": "npc_soul"}, ok=False)
        moral(c, {"intent_source": "declared", "intent": "y"}, ok=False)
        assert moral(c, {"action": "x", "intent_source": "undeclared"})["status"] == "committed"
        assert moral(c, {"action": "hired by captain", "intent_source": "npc_soul"}, subject_kind="npc")["status"] == "committed"
        # later revelation: new evaluation, same intent, new knowledge; rewriting intent is rejected
        later = dict(good, knowledge="later learned guard was a courier", consequences_accidental="courier delivered the warning")
        d = lambda f: {"subject": "aero", "subject_kind": "pc", "reevaluates": e1["event_id"], "facets": f}
        ok = run(c, "add", "--kind", "moral_evaluation", "--summary", "m2", "--world-time", "Day 3",
                 "--details", json.dumps(d(later)), "--visibility", "gm_only", "--caused-by", e1["event_id"])
        assert ok["status"] == "committed"
        rewritten = dict(later, intent="I wanted him to deliver the warning")
        run(c, "add", "--kind", "moral_evaluation", "--summary", "m3", "--world-time", "Day 3",
            "--details", json.dumps(d(rewritten)), "--visibility", "gm_only", ok=False)
        assert run(c, "validate")["problems"] == []


if __name__ == "__main__":
    test_all(); print("ok test_all"); test_moral_evaluations(); print("ok test_moral_evaluations")
