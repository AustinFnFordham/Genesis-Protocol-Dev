#!/usr/bin/env python3
"""LitRPG event ledger: append-only events with causal ancestry, typed knowledge, and a visibility split.

Public events (visibility != gm_only)  -> campaigns/starwars_litrpg/records/events.jsonl
Hidden events (visibility == gm_only)  -> campaigns/starwars_litrpg/hidden/events.jsonl
Event ids share one sequence (evt_0001...). caused_by may only reference EARLIER events, so ancestry is acyclic by construction.

  ledger.py add --kind attack_resolved --summary "Aero's shot misses the guard" --actor aero \
      --world-time "Day 1, dusk" --visibility player --type fact --roll roll_t3_2 --caused-by evt_0004 --idem t3_attack
  ledger.py validate
  ledger.py show --as player [--session 2]
  ledger.py show --as gm
"""
import argparse, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CAMPAIGN = ROOT / "campaigns" / "starwars_litrpg"
VISIBILITY = {"player", "party", "gm_only"}
KNOWLEDGE = {"fact", "report", "belief"}
ID_RE = re.compile(r"^evt_(\d{4,})$")
REQUIRED = ("event_id", "session", "turn_no", "world_time", "kind", "summary", "visibility", "knowledge_type", "known_to", "caused_by", "roll_ids")


def paths(camp):
    return camp / "records" / "events.jsonl", camp / "hidden" / "events.jsonl", camp / "records" / "roll_log.jsonl", camp / "hidden" / "dice_state.json"


def read_jsonl(p):
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_all(camp):
    pub, hid, _, _ = paths(camp)
    events = read_jsonl(pub) + read_jsonl(hid)
    return sorted(events, key=lambda e: int(ID_RE.match(e["event_id"]).group(1)))


def validate_event(e, by_id, roll_ids):
    errs = []
    for k in REQUIRED:
        if k not in e:
            errs.append(f"missing {k}")
    if errs:
        return errs
    m = ID_RE.match(e["event_id"])
    if not m:
        return [f"bad event_id {e['event_id']}"]
    seq = int(m.group(1))
    if e["visibility"] not in VISIBILITY:
        errs.append(f"bad visibility {e['visibility']}")
    if e["knowledge_type"] not in KNOWLEDGE:
        errs.append(f"bad knowledge_type {e['knowledge_type']}")
    if e["knowledge_type"] in ("report", "belief") and not e["known_to"]:
        errs.append(f"{e['knowledge_type']} needs known_to (whose report/belief)")
    if not str(e["summary"]).strip() or not str(e["world_time"]).strip():
        errs.append("empty summary or world_time")
    for c in e["caused_by"]:
        cm = ID_RE.match(c)
        if not cm or c not in by_id:
            errs.append(f"caused_by {c} does not resolve")
        elif int(cm.group(1)) >= seq:
            errs.append(f"caused_by {c} is not earlier than {e['event_id']}")
    for r in e["roll_ids"]:
        if r not in roll_ids:
            errs.append(f"roll {r} not in roll_log")
    return errs


def validate_all(camp):
    _, _, rolls, _ = paths(camp)
    roll_ids = {r["roll_id"] for r in read_jsonl(rolls)}
    events = load_all(camp)
    by_id, problems, seen_idem = {}, [], {}
    all_ids = {e.get("event_id"): e for e in events}   # so a forward reference reads "not earlier", not "unresolved"
    pub, hid, _, _ = paths(camp)
    for e in read_jsonl(pub):
        if e.get("visibility") == "gm_only":
            problems.append((e.get("event_id"), "gm_only event stored in public file"))
    for e in read_jsonl(hid):
        if e.get("visibility") != "gm_only":
            problems.append((e.get("event_id"), "non-gm_only event stored in hidden file"))
    for e in events:
        if e.get("event_id") in by_id:
            problems.append((e["event_id"], "duplicate event_id"))
        for msg in validate_event(e, all_ids, roll_ids):
            problems.append((e.get("event_id"), msg))
        k = e.get("idempotency_key")
        if k:
            if k in seen_idem:
                problems.append((e.get("event_id"), f"duplicate idempotency_key {k}"))
            seen_idem[k] = e["event_id"]
        by_id[e.get("event_id")] = e
    return events, problems


def cmd_add(a, camp):
    pub, hid, rolls, dice = paths(camp)
    events, problems = validate_all(camp)
    if problems:
        print(json.dumps({"error": "ledger invalid; fix before appending", "problems": problems[:5]}), file=sys.stderr)
        return 2
    if a.idem:
        for e in events:
            if e.get("idempotency_key") == a.idem:
                print(json.dumps({"status": "duplicate", "event": e}))
                return 0
    turn = a.turn
    if turn is None:
        turn = json.loads(dice.read_text())["turn_no"] if dice.exists() else 0
    nxt = (int(ID_RE.match(events[-1]["event_id"]).group(1)) if events else 0) + 1
    e = {
        "event_id": f"evt_{nxt:04d}", "session": a.session, "turn_no": turn, "world_time": a.world_time,
        "actor": a.actor, "kind": a.kind, "summary": a.summary, "visibility": a.visibility,
        "knowledge_type": a.type, "known_to": a.known_to or [], "caused_by": a.caused_by or [],
        "roll_ids": a.roll or [], "tags": a.tag or [], "idempotency_key": a.idem,
    }
    by_id = {x["event_id"]: x for x in events}
    roll_ids = {r["roll_id"] for r in read_jsonl(rolls)}
    errs = validate_event(e, by_id, roll_ids)
    if errs:
        print(json.dumps({"error": "invalid event", "problems": errs}), file=sys.stderr)
        return 2
    target = hid if e["visibility"] == "gm_only" else pub
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8") as f:
        f.write(json.dumps(e) + "\n")
    print(json.dumps({"status": "committed", "event": e}))
    return 0


def player_view(events):
    """Player-safe projection: drop gm_only events, and redact caused_by links that point at hidden events."""
    hidden = {e["event_id"] for e in events if e["visibility"] == "gm_only"}
    out = []
    for e in events:
        if e["visibility"] == "gm_only":
            continue
        e = dict(e)
        e["caused_by"] = [c for c in e["caused_by"] if c not in hidden]
        out.append(e)
    return out


def cmd_show(a, camp):
    events, problems = validate_all(camp)
    if problems:
        print(json.dumps({"warning": "ledger has problems", "problems": problems[:5]}), file=sys.stderr)
    if a.as_ == "player":
        events = player_view(events)
    if a.session is not None:
        events = [e for e in events if e["session"] == a.session]
    for e in events:
        print(json.dumps(e))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaign", default=str(DEFAULT_CAMPAIGN))
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add")
    s.add_argument("--kind", required=True); s.add_argument("--summary", required=True)
    s.add_argument("--actor", default="gm"); s.add_argument("--world-time", required=True)
    s.add_argument("--visibility", choices=sorted(VISIBILITY), default="player")
    s.add_argument("--type", choices=sorted(KNOWLEDGE), default="fact")
    s.add_argument("--known-to", nargs="*"); s.add_argument("--caused-by", nargs="*")
    s.add_argument("--roll", nargs="*"); s.add_argument("--tag", nargs="*")
    s.add_argument("--idem"); s.add_argument("--session", type=int, default=1); s.add_argument("--turn", type=int)
    sub.add_parser("validate")
    w = sub.add_parser("show"); w.add_argument("--as", dest="as_", choices=["player", "gm"], default="player"); w.add_argument("--session", type=int)
    a = ap.parse_args(argv)
    camp = Path(a.campaign)
    if a.cmd == "add":
        return cmd_add(a, camp)
    if a.cmd == "show":
        return cmd_show(a, camp)
    events, problems = validate_all(camp)
    print(json.dumps({"events": len(events), "problems": problems}))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
