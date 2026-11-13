#!/usr/bin/env python3
"""LitRPG dice roller. Every roll in the Star Wars LitRPG goes through this script.

Same RNG family as Genesis DiceService (api_bridge/gm_controllers.py): mulberry32 seeded
with campaign_seed ^ (turn_no * 0x9E3779B9). Rolls are appended to a public roll log, so a
roll cannot be quietly rewritten after the fact. DCs go to the hidden ledger, never the public log.

Usage:
  roll.py 1d20+5 --purpose "Aero: Insight vs Dax" --dc 12
  roll.py 1d20+4 --mode advantage --purpose "Stealth"
  roll.py 2d6+1d4+3 --purpose "Sneak attack damage"
  roll.py 4d6kh3 --purpose "Ability score"
  roll.py --advance-turn            # new turn: bumps turn_no, resets the draw stream
"""
import argparse, json, os, re, secrets, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAMPAIGN = ROOT / "campaigns" / "starwars_litrpg"
MAX_DICE, MAX_SIDES = 100, 1000
TERM = re.compile(r"([+-]?)\s*(?:(\d*)d(\d+)(?:(kh|kl)(\d+))?|(\d+))", re.I)


def mulberry(seed):
    """Verbatim port of api_bridge/gm_controllers._mulberry (parity-tested)."""
    a = seed & 0xFFFFFFFF
    def rand():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = (t ^ (t >> 15)) * (t | 1) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF)) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return rand


def parse(formula):
    s = formula.strip().replace(" ", "")
    if not s:
        raise ValueError("empty dice formula")
    pos, terms = 0, []
    while pos < len(s):
        m = TERM.match(s, pos)
        if not m or m.end() == pos:
            raise ValueError(f"bad dice formula: {formula}")
        sign = -1 if m.group(1) == "-" else 1
        if m.group(3):
            count, sides = int(m.group(2) or 1), int(m.group(3))
            keep = (m.group(4).lower(), int(m.group(5))) if m.group(4) else None
            if not (1 <= count <= MAX_DICE and 2 <= sides <= MAX_SIDES):
                raise ValueError(f"dice out of range: {m.group(0)}")
            if keep and not (1 <= keep[1] <= count):
                raise ValueError(f"bad keep count: {m.group(0)}")
            terms.append(("dice", sign, count, sides, keep))
        else:
            terms.append(("flat", sign, int(m.group(6))))
        pos = m.end()
    if not any(t[0] == "dice" for t in terms):
        raise ValueError("formula has no dice")
    return terms


def do_roll(formula, mode, rand):
    terms = parse(formula)
    dice_terms = [t for t in terms if t[0] == "dice"]
    # one 1d20 (any flat modifiers allowed, e.g. 1d20+4); advantage/disadvantage never applies to other dice
    first_d20 = len(dice_terms) == 1 and dice_terms[0][1] == 1 and dice_terms[0][2:4] == (1, 20) and dice_terms[0][4] is None
    if mode != "normal" and not first_d20:
        raise ValueError("advantage/disadvantage only applies to a single 1d20")
    dice_out, alt, total, mods = [], None, 0, 0
    for t in terms:
        if t[0] == "flat":
            mods += t[1] * t[2]
            continue
        _, sign, count, sides, keep = t
        faces = [1 + int(rand() * sides) for _ in range(count)]
        original = faces[:]
        if mode != "normal":
            alt = [1 + int(rand() * sides) for _ in range(count)]
            faces = [(max if mode == "advantage" else min)(faces[0], alt[0])]
        kept = faces
        if keep:
            kept = sorted(faces, reverse=(keep[0] == "kh"))[:keep[1]]
        dice_out.append({"sign": sign, "sides": sides, "rolled": faces, "kept": kept, "original": original})
        total += sign * sum(kept)
    return dice_out, alt, total, mods, first_d20


def load_state(path):
    if path.exists():
        return json.loads(path.read_text())
    return {"seed": secrets.randbits(32), "turn_no": 0, "draws_used": 0, "roll_count": 0}


def save_state(path, st):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1))
    os.replace(tmp, path)


def append(path, rec):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def generate_plan(a, camp):
    """Compute once, then persist an immutable plan before touching log/cursor."""
    from transactions import batch
    state_path = camp / "hidden/dice_state.json"
    before = state_path.read_bytes().decode() if state_path.exists() else None
    st = load_state(state_path)
    public_path = camp / "records/roll_log.jsonl"
    original = public_path.read_bytes() if public_path.exists() else b""
    if original and not original.endswith(b"\n"):
        raise ValueError("incomplete prior roll log; manual reconciliation required")
    rows = [json.loads(line) for line in original.splitlines() if line.strip()]
    expected_draws = sum(sum(t[2] for t in parse(row["formula"]) if t[0] == "dice") *
                         (2 if row["mode"] != "normal" else 1) for row in rows if row["turn_no"] == st["turn_no"])
    if ([row["roll_id"] for row in rows] != [f"roll_t{row['turn_no']}_{i}" for i, row in enumerate(rows, 1)] or
            len(rows) != st["roll_count"] or expected_draws != st["draws_used"] or
            any(row["turn_no"] > st["turn_no"] for row in rows)):
        raise ValueError("legacy dice log/cursor mismatch; manual reconciliation required")
    if a.advance_turn:
        st["turn_no"] += 1
        st["draws_used"] = 0
        return {"streams":{}, "state":{"before":before,"after":json.dumps(st,indent=1)},
                "result":{"turn_no":st["turn_no"]}}

    parse(a.formula)
    rand = mulberry((st["seed"] ^ (st["turn_no"] * 0x9E3779B9)) & 0xFFFFFFFF)
    for _ in range(st["draws_used"]):      # resume this turn's stream where it left off
        rand()
    used = [0]
    def counted():
        used[0] += 1
        return rand()
    dice, alt, total, mods, single_d20 = do_roll(a.formula, a.mode, counted)
    st["draws_used"] += used[0]
    st["roll_count"] += 1
    final = total + mods
    nat = dice[0]["rolled"][0] if single_d20 else None
    rec = {
        "roll_id": f"roll_t{st['turn_no']}_{st['roll_count']}",
        "turn_no": st["turn_no"], "requested_by": a.by, "purpose": a.purpose,
        "formula": a.formula, "mode": a.mode, "dice": dice, "alt_dice": alt,
        "raw_total": total, "modifiers": mods, "final_total": final,
        "nat20": nat == 20, "nat1": nat == 1,
    }
    logs = {"records/roll_log.jsonl":rec}
    out = dict(rec)
    if a.dc is not None:
        out["outcome"] = "success" if final >= a.dc else "failure"
        logs["hidden/roll_dcs.jsonl"] = {"roll_id":rec["roll_id"],"dc":a.dc,"outcome":out["outcome"]}
    shown = "+".join(str(d["kept"]) for d in dice)
    out["summary"] = f"{a.formula} {shown}{'%+d' % mods if mods else ''} = {final}" + (f" ({out['outcome']})" if a.dc is not None else "")
    streams = {}
    for relative, row in logs.items():
        path = camp / relative
        original = path.read_bytes() if path.exists() else b""
        if original and not original.endswith(b"\n"):
            raise ValueError("incomplete prior dice log; manual reconciliation required")
        streams[relative] = {"size":len(original),"hash":batch.digest(original),"tail":json.dumps(row)+"\n"}
    return {"streams":streams, "state":{"before":before,"after":json.dumps(st,indent=1)}, "result":out}


def main(argv=None, after_write=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("formula", nargs="?")
    ap.add_argument("--purpose", default="")
    ap.add_argument("--by", default="gm", help="who requested the roll")
    ap.add_argument("--mode", choices=["normal", "advantage", "disadvantage"], default="normal")
    ap.add_argument("--dc", type=int, help="target number; stored in the hidden ledger only")
    ap.add_argument("--campaign", default=str(DEFAULT_CAMPAIGN))
    ap.add_argument("--advance-turn", action="store_true")
    ap.add_argument("--request-id", help="stable unique operation ID; reuse verbatim for every retry")
    a = ap.parse_args(argv)
    if not a.advance_turn and not a.formula:
        ap.error("formula required")
    from transactions import execute
    request = {key:value for key,value in vars(a).items() if key != "campaign"}
    try:
        out = execute(Path(a.campaign), request, lambda:generate_plan(a,Path(a.campaign)), after_write)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"error":str(error)}),file=sys.stderr)
        return 2
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
