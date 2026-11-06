#!/usr/bin/env python3
"""Protagonist Continuity: detect a would-die moment and build the Spared continuation (PROPOSED rule).

  continuity.py propose --campaign DIR [--target aero] [--pick N ...] [--dry-run --seed S]

Reads the ledger (public + hidden, GM tool), never writes it and never rolls dice. While the rule's
status is "proposed" only --dry-run is allowed and the output is labeled SIMULATION, NOT CANON. When
approved, the GM rolls the cost die with the dice skill and passes the result(s) with --pick, then
commits the returned events with the ledger skill.
"""
import argparse, json, random, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULE = HERE / "continuity_rule.json"
LEDGER = HERE.parents[2] / ".claude" / "skills" / "litrpg-ledger" / "ledger.py"


def ledger():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ledger_mod", LEDGER)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def live_events(camp):
    ev = ledger().load_all(Path(camp))
    voided = {v for e in ev if e["kind"] == "ruling_void" for v in e["details"].get("voids", [])}
    return [e for e in ev if e["event_id"] not in voided]


def about(e, target):
    d = e.get("details") or {}
    return d.get("target") == target or e.get("actor") == target or target in (e.get("summary") or "").lower()


def trigger(ev, target):
    for e in ev:
        d = e.get("details") or {}
        if e["kind"] == "death_save" and about(e, target) and d.get("failures", 0) >= 3:
            return e
        if e["kind"] == "character_death" and d.get("target") == target:
            return e
    return None


def eligible_costs(ev, target, trig):
    upto = [e for e in ev if int(e["event_id"][4:]) <= int(trig["event_id"][4:])]
    later = ev
    costs = []
    dmg = [e for e in upto if e["kind"] == "damage_applied" and about(e, target)]
    if dmg:
        costs.append({"id": "lasting_wound", "evidence": [dmg[-1]["event_id"]],
                      "effect": "lasting_injury on the part the last hit damaged: disadvantage on checks using it (or -10 ft speed for a leg) until treated (Medicine DC 15, safe place) and two long rests"})
    items = [e for e in later if e["kind"] == "world_fact" and "item_location" in (e.get("tags") or [])]
    if items:
        costs.append({"id": "lost_equipment", "evidence": [items[-1]["event_id"]], "effect": "the item stays where the ledger left it; recovering it is a goal"})
    PRESENTATION = {"gm_narration", "scene_state", "gm_suggestions", "turn_context", "adjudication"}
    moved = [e for e in later if e["kind"] not in PRESENTATION and
             re.search(r"\b(drag\w*|carr(?:y|ied)|haul\w*|captur\w*|taken (?:away|by))\b", e.get("summary") or "", re.I)]
    if moved:
        costs.append({"id": "taken", "evidence": [moved[0]["event_id"], moved[-1]["event_id"]] if len(moved) > 1 else [moved[0]["event_id"]],
                      "effect": "wakes where the established actors took them; the place comes from hidden truth or a table fixed before rolling"})
    costs.append({"id": "exhaustion", "evidence": [trig["event_id"]], "effect": "two levels of exhaustion; one recovers per long rest"})
    plans = [e for e in later if e["visibility"] == "gm_only" and e["kind"] in ("npc_plan", "npc_state") and re.search(r"hunt|plan|review|next", e["summary"], re.I)]
    if plans:
        costs.append({"id": "escalation", "evidence": [plans[0]["event_id"]], "effect": "that actor's next scheduled move comes one step sooner or stronger (gm_only)"})
    return costs


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("propose"); p.add_argument("--campaign", required=True); p.add_argument("--target", default="aero")
    p.add_argument("--pick", type=int, nargs="*"); p.add_argument("--dry-run", action="store_true"); p.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rule = json.loads(RULE.read_text(encoding="utf-8"))
    if rule["status"] != "approved" and not a.dry_run:
        print(json.dumps({"refused": "Protagonist Continuity is not approved; standard death rules apply. Use --dry-run to simulate."})); return 3
    if a.target not in rule["protected_characters"] or rule["protected_phase"]["ended"]:
        print(json.dumps({"applies": False, "reason": "not protected or protected phase ended"})); return 0
    ev = live_events(a.campaign)
    trig = trigger(ev, a.target)
    if not trig:
        print(json.dumps({"applies": False, "reason": "no would-die moment in the ledger"})); return 0
    marks = sum(1 for e in ev if e["kind"] == "continuity_invoked" and (e.get("details") or {}).get("target") == a.target)
    n_costs = rule["costs_per_mark"][min(marks, len(rule["costs_per_mark"]) - 1)]
    costs = eligible_costs(ev, a.target, trig)
    if a.pick:
        chosen = [costs[(i - 1) % len(costs)] for i in a.pick[:n_costs]]
    else:
        rng = random.Random(a.seed); chosen = rng.sample(costs, min(n_costs, len(costs)))
    out = {
        "applies": True, "label": "SIMULATION, NOT CANON" if rule["status"] != "approved" else "authorized",
        "trigger": trig["event_id"], "target": a.target, "mark": marks + 1,
        "preserved": "all committed events stand; no roll is changed; no ally or item is invented",
        "state": {"hp": 0, "conditions": ["unconscious", "stable"], "wake": rule["wake"]},
        "cost_die": f"1d{len(costs)}", "eligible_costs": costs, "chosen_costs": chosen,
        "phase_ends": marks + 1 >= rule["phase_ends_after_marks"],
        "events_to_commit": [
            {"kind": "continuity_invoked", "visibility": "player", "summary": f"{a.target.title()} does not die. Stable at 0 HP and unconscious (Protagonist Continuity, mark {marks + 1}).",
             "caused_by": [trig["event_id"]], "details": {"target": a.target, "mark": marks + 1, "costs": [c["id"] for c in chosen]}},
            *[{"kind": "continuity_cost", "visibility": "player", "summary": c["effect"], "caused_by": c["evidence"], "details": {"target": a.target, "cost": c["id"]}} for c in chosen],
            {"kind": "condition_change", "visibility": "player", "summary": f"{a.target.title()} is unconscious and stable.", "details": {"target": a.target, "conditions": ["unconscious", "stable"]}},
        ],
    }
    print(json.dumps(out, indent=1)); return 0


if __name__ == "__main__":
    sys.exit(main())
