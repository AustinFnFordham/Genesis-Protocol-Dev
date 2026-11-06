#!/usr/bin/env python3
"""Deterministic helpers for the Datapad turn processor (see SKILL.md in this folder).

  turn.py info     <campaign_id>                       registry entry + current revision + turn context
  turn.py check    <campaign_id> <action.json>         stale check + contract validation (no dice)
  turn.py recover  <campaign_id> <action_id>           ledger state for an action: none | partial | complete
  turn.py lint     <campaign_id> <narration.txt> [--target aero]   horror-narration integrity (Test F)
  turn.py export   <campaign_id> --out FILE            player-visible view/state for the Datapad

Exit codes: 0 ok, 3 needs revision / lint failure, 2 usage or registry error.
Nothing here rolls dice, writes the ledger, or touches the Artifact database; those stay with the
dice skill, the ledger skill and the ArtifactData tool, in the order the runbook gives.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
REGISTRY = REPO / "campaigns" / "starwars_litrpg" / "runs" / "registry.json"
UI = REPO / "campaigns" / "starwars_litrpg" / "ui"
sys.path.insert(0, str(UI))
import export_state  # noqa: E402

# Words that describe lasting damage. Narration may use them only when a committed public
# `lasting_injury` event exists for the target (NARRATIVE_SPEC §B, Test F).
LASTING = re.compile(r"\b(sever(?:ed|s)?|amputat\w*|shatter(?:ed|s)?\s+(?:bone|femur|knee|leg|arm|skull|spine)|"
                     r"(?:broken|snapped|splintered)\s+(?:bone|femur|tibia|knee|leg|arm|spine|ribs?)|"
                     r"bit(?:ten)?\s+(?:clean\s+)?off|torn\s+off|crippled|paralys\w+|blinded|lost\s+(?:his|her|their)\s+(?:leg|arm|hand|eye))\b", re.I)
DEATH = re.compile(r"\b(is dead|dies\b|died\b|killed\b|his death)\b", re.I)


def run_entry(cid):
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))["runs"]
    if cid not in reg:
        sys.exit(f"unknown campaign id {cid!r}; registry has {sorted(reg)}")
    e = dict(reg[cid]); e["id"] = cid; e["path"] = REPO / e["dir"]
    return e


def events(entry):
    return export_state.public_events(entry["path"])


def state(entry):
    return export_state.build(campaign_dir=entry["path"], campaign_id=entry["id"])


def node_validate(decl, ctx):
    tmp = Path("/tmp") / f"ctx_{abs(hash(json.dumps(ctx, sort_keys=True)))}.json"
    tmp.write_text(json.dumps(ctx), encoding="utf-8")
    p = subprocess.run(["node", str(UI / "turn_contract.js"), "validate", "-", str(tmp)], input=json.dumps(decl), capture_output=True, text=True)
    if p.returncode not in (0, 3):
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


def node_parse(text, ctx):
    tmp = Path("/tmp") / f"ctx_{abs(hash(json.dumps(ctx, sort_keys=True)))}.json"
    tmp.write_text(json.dumps(ctx), encoding="utf-8")
    p = subprocess.run(["node", str(UI / "turn_contract.js"), "parse", text, str(tmp)], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


def cmd_info(a):
    e = run_entry(a.campaign); st = state(e)
    print(json.dumps({"campaign_id": e["id"], "dir": e["dir"], "artifact_url": e["artifact_url"], "status": e["status"], "canon": e["canon"],
                      "revision": st["revision"], "ledger_head": st["ledger_head"], "turn_context": st["turn_context"]}, indent=1))


def cmd_check(a):
    e = run_entry(a.campaign)
    if e["status"] != "active":
        print(json.dumps({"verdict": "failed", "reason": f"campaign {e['id']} is {e['status']}; it is not processed"})); return 3
    act = json.loads(Path(a.action).read_text(encoding="utf-8"))
    act = act.get("data", act)  # accept a raw ArtifactData document or its data
    st = state(e)
    out = {"campaign_id": e["id"], "current_revision": st["revision"], "based_on_revision": act.get("based_on_revision")}
    if act.get("campaign_id") not in (None, e["id"]):
        out.update(verdict="needs_revision", reason=f"action belongs to campaign {act.get('campaign_id')}")
    elif act.get("based_on_revision") != st["revision"]:
        out.update(verdict="needs_revision", reason="The story moved on after this action was written (revision "
                   f"{act.get('based_on_revision')} vs {st['revision']}). Review the latest scene and resubmit.")
    elif not st["turn_context"]:
        out.update(verdict="gm_judgment", reason="No turn context is published; the GM interprets the text freely under the charter.")
    else:
        ctx = st["turn_context"]
        decl = act.get("declaration")
        if decl:
            r = node_validate(decl, ctx); out.update(declaration=decl, validation=r["validation"], summary=r["summary"])
        else:
            r = node_parse(act.get("text", ""), ctx); out.update(declaration=r["declaration"], validation=r["validation"], summary=r["summary"],
                                                               note="Parsed from free text; the GM may correct the reading but must re-validate it.")
        v = out["validation"]
        if not v["legal"]:
            out["verdict"] = "needs_revision"
        elif v["warnings"] and not act.get("confirmed_warnings"):
            out.update(verdict="needs_revision", reason="Known risks were not confirmed by the player.")
        else:
            out["verdict"] = "legal"
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0 if out["verdict"] in ("legal", "gm_judgment") else 3


def cmd_recover(a):
    e = run_entry(a.campaign)
    led = export_state.la._ledger()
    allev = led.load_all(e["path"])
    mine = [x for x in allev if str(x.get("idempotency_key") or "").startswith(a.action_id + ":")]
    rolls = [r["roll_id"] for r in led.read_jsonl(e["path"] / "records" / "roll_log.jsonl") if str(r.get("purpose", "")).startswith("[" + a.action_id + "]")]
    kinds = [x["kind"] for x in mine]
    status = "complete" if "gm_narration" in kinds and "turn_context" in kinds else ("none" if not mine and not rolls else "partial")
    print(json.dumps({"action_id": a.action_id, "status": status, "events": [x["event_id"] + ":" + x["kind"] for x in mine], "rolls": rolls}, indent=1))


def cmd_lint(a):
    e = run_entry(a.campaign)
    text = Path(a.narration).read_text(encoding="utf-8")
    ev = events(e)
    problems = []
    lasting = [x for x in ev if x["kind"] == "lasting_injury" and x["details"].get("target") == a.target]
    for m in LASTING.finditer(text):
        if not lasting:
            problems.append(f"'{m.group(0)}' describes lasting damage but no committed lasting_injury event exists for {a.target}")
    st = export_state.build(ev, campaign_id=e["id"]) if ev else None
    dead = st and "dead" in [c.lower() for c in st["character"]["conditions"]]
    for m in DEATH.finditer(text):
        if not dead:
            problems.append(f"'{m.group(0)}' narrates death but {a.target} is not dead in the ledger")
    print(json.dumps({"ok": not problems, "problems": problems}, indent=1))
    return 0 if not problems else 3


def cmd_export(a):
    e = run_entry(a.campaign)
    st = state(e)
    st["artifact_url"] = e["artifact_url"]
    Path(a.out).write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"out": a.out, "revision": st["revision"], "ledger_head": st["ledger_head"], "has_turn_context": bool(st["turn_context"])}))


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("info"); s.add_argument("campaign")
    s = sub.add_parser("check"); s.add_argument("campaign"); s.add_argument("action")
    s = sub.add_parser("recover"); s.add_argument("campaign"); s.add_argument("action_id")
    s = sub.add_parser("lint"); s.add_argument("campaign"); s.add_argument("narration"); s.add_argument("--target", default="aero")
    s = sub.add_parser("export"); s.add_argument("campaign"); s.add_argument("--out", required=True)
    a = ap.parse_args()
    return {"info": cmd_info, "check": cmd_check, "recover": cmd_recover, "lint": cmd_lint, "export": cmd_export}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
