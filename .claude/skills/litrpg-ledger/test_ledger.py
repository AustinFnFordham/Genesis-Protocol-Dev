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

if __name__ == "__main__":
    test_all(); print("ok test_all")
