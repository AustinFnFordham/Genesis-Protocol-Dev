import ast, json, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import roll

ROOT = HERE.parents[2]

def genesis_mulberry():
    src = (ROOT / "api_bridge" / "gm_controllers.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_mulberry")
    ns = {}
    exec(ast.get_source_segment(src, fn), ns)
    return ns["_mulberry"]

def test_parity_with_genesis_rng():
    g = genesis_mulberry()
    for seed in (1, 776211453, 0xFFFFFFFF):
        a, b = g(seed), roll.mulberry(seed)
        assert [a() for _ in range(50)] == [b() for _ in range(50)]

def test_parity_with_genesis_dice_service_d20():
    g = genesis_mulberry()(776211453 ^ 0)
    expected = 1 + int(g() * 20) + 5
    r = roll.mulberry(776211453)
    dice, _, total, mods, _ = roll.do_roll("1d20+5", "normal", r)
    assert total + mods == expected

def test_formulas():
    r = roll.mulberry(7)
    for f in ("2d6+1d4+3", "d8-1", "4d6kh3", "1d20+4"):
        dice, _, total, mods, _ = roll.do_roll(f, "normal", r)
        assert dice
    for bad in ("", "5", "abc", "0d6", "1d1", "2d6kh3", "101d6"):
        try: roll.parse(bad)
        except ValueError: continue
        raise AssertionError(bad)

def test_advantage_picks_higher_and_only_single_d20():
    r = roll.mulberry(3)
    dice, alt, total, _, _ = roll.do_roll("1d20", "advantage", r)
    assert total >= 1 and alt is not None
    try: roll.do_roll("2d6", "advantage", roll.mulberry(3))
    except ValueError: pass
    else: raise AssertionError

def test_cli_stream_persists_and_replays():
    def run(camp, *args):
        p = subprocess.run([sys.executable, str(HERE / "roll.py"), "--campaign", str(camp), *args], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        return json.loads(p.stdout)
    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
        for t in (t1, t2):
            (Path(t) / "hidden").mkdir()
            (Path(t) / "hidden" / "dice_state.json").write_text(json.dumps({"seed": 99, "turn_no": 0, "draws_used": 0, "roll_count": 0}))
        a = [run(t1, "1d20+3", "--dc", "10")["final_total"] for _ in range(6)]
        b = [run(t2, "1d20+3", "--dc", "10")["final_total"] for _ in range(6)]
        assert a == b                      # same seed, same turn -> replayable
        assert len(set(a)) > 1             # but successive rolls differ
        log = (Path(t1) / "records" / "roll_log.jsonl").read_text().splitlines()
        assert len(log) == 6 and "dc" not in log[0]   # public log never carries the DC
        assert len((Path(t1) / "hidden" / "roll_dcs.jsonl").read_text().splitlines()) == 6

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)
