#!/usr/bin/env python3
"""Protagonist Continuity v2 (campaign rule, approved provisionally 2026-11-06).

  continuity.py status  --campaign DIR [--target aero] [--level N]
  continuity.py propose --campaign DIR [--target aero] [--path-roll N] [--cost-rolls N ...] [--dry-run --seed S]

GM tool: reads the ledger (public + hidden), never writes it, never rolls. The GM rolls the
survival-path die and the cost dice with the dice skill (sizes are given here), passes the
results back with --path-roll / --cost-rolls, and commits the returned events with the ledger skill.
--dry-run picks with a seeded RNG and labels the output SIMULATION, NOT CANON.
"""
import argparse, json, random, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULE = HERE / "continuity_rule.json"
LEDGER = HERE.parents[2] / ".claude" / "skills" / "litrpg-ledger" / "ledger.py"
PRESENTATION = {"gm_narration", "scene_state", "gm_suggestions", "turn_context", "adjudication"}


def ledger():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ledger_mod", LEDGER)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def live_events(camp):
    ev = ledger().load_all(Path(camp))
    voided = {v for e in ev if e["kind"] == "ruling_void" for v in e["details"].get("voids", [])}
    return [e for e in ev if e["event_id"] not in voided]


def num(e): return int(e["event_id"][4:])


def about(e, target):
    d = e.get("details") or {}
    return d.get("target") == target or e.get("actor") == target or target in (e.get("summary") or "").lower()


def window_state(ev, rule, target, level):
    """active | expiring | expired, and whether the end conditions are met."""
    kinds = [e["kind"] for e in ev if (e.get("details") or {}).get("target") in (None, target)]
    arc_done = any(e["kind"] == "arc_completed" and (e.get("details") or {}).get("arc") == rule["window"]["arc"] for e in ev)
    met = arc_done and level >= rule["window"]["min_level"]
    state = "expired" if "continuity_expired" in kinds else "expiring" if "continuity_expiring" in kinds else "active"
    return state, met, arc_done


def would_die(ev, target):
    """The latest would-die moment not yet answered by a continuity_invoked event."""
    answered = {c for e in ev if e["kind"] == "continuity_invoked" for c in (e.get("caused_by") or [])}
    hits = []
    for e in ev:
        d = e.get("details") or {}
        if e["kind"] == "death_save" and about(e, target) and d.get("failures", 0) >= 3: hits.append(e)
        elif e["kind"] in ("character_death", "would_die") and d.get("target") == target: hits.append(e)
    hits = [h for h in hits if h["event_id"] not in answered]
    return hits[0] if hits else None


def survival_paths(ev, trig):
    hidden_rule = [e for e in ev if e["visibility"] == "gm_only" and "downed_prey_behavior" in (e.get("tags") or [])]
    if hidden_rule:  # established hidden truth decides; no roll
        return [{"id": "hidden_truth", "evidence": [hidden_rule[-1]["event_id"]], "effect": hidden_rule[-1]["summary"]}], True
    paths = []
    moved = [e for e in ev if e["kind"] not in PRESENTATION and num(e) <= num(trig) + 50 and
             re.search(r"\b(drag\w*|carr(?:y|ied)|haul\w*|captur\w*|taken (?:away|by))\b", e.get("summary") or "", re.I)]
    if moved:
        paths.append({"id": "taken", "evidence": [moved[0]["event_id"]], "effect": "wakes where the established actors took them; the place comes from hidden truth or a table fixed before rolling"})
    enroute = [e for e in ev if e["kind"] in ("npc_plan", "npc_state", "npc_move") and "en_route" in (e.get("tags") or [])]
    if enroute:
        paths.append({"id": "interrupted", "evidence": [enroute[-1]["event_id"]], "effect": "the already-established actor arrives and the hostiles break off"})
    paths.append({"id": "left_for_dead", "evidence": [trig["event_id"]], "effect": "the hostiles believe the body finished and move on"})
    return paths, False


def eligible_costs(ev, target, trig, mark, rule):
    upto = [e for e in ev if num(e) <= num(trig)]
    costs = []
    dmg = [e for e in upto if e["kind"] == "damage_applied" and about(e, target)]
    grievous = mark >= rule["grievous_from_mark"]
    if dmg:
        costs.append({"id": "lasting_wound", "grievous": grievous, "evidence": [dmg[-1]["event_id"]],
                      "effect": ("grievous wound: persists until bacta-tank treatment at a medical facility or a cybernetic replacement"
                                 if grievous else "lasting wound: disadvantage on checks using the part (-10 ft speed for a leg) until treated (Medicine DC 15, safe place) and two long rests")})
    items = [e for e in ev if e["kind"] == "world_fact" and "item_location" in (e.get("tags") or [])]
    if items:
        costs.append({"id": "lost_equipment", "evidence": [items[-1]["event_id"]], "effect": "the item stays where the ledger left it; recovering it is a goal"})
    costs.append({"id": "exhaustion", "evidence": [trig["event_id"]], "effect": f"two levels of exhaustion (capped at {rule['exhaustion_cap_while_protected']} while protected); one recovers per long rest"})
    plans = [e for e in ev if e["visibility"] == "gm_only" and e["kind"] in ("npc_plan", "npc_state") and re.search(r"hunt|plan|review|next", e["summary"], re.I)]
    if plans:
        costs.append({"id": "escalation", "evidence": [plans[0]["event_id"]], "effect": "that actor's next scheduled move comes one step sooner or stronger (gm_only)"})
    return costs


def pick(seq, rolls, n, rng):
    """Pick n distinct entries using 1-based die results (re-rolling duplicates is the GM's job), or the RNG in a dry run."""
    if rolls is None:
        return rng.sample(seq, min(n, len(seq)))
    out = []
    for r in rolls:
        c = seq[(r - 1) % len(seq)]
        if c not in out: out.append(c)
        if len(out) == min(n, len(seq)): break
    return out


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("status", "propose"):
        p = sub.add_parser(name); p.add_argument("--campaign", required=True); p.add_argument("--target", default="aero"); p.add_argument("--level", type=int, default=1)
        if name == "propose":
            p.add_argument("--path-roll", type=int); p.add_argument("--cost-rolls", type=int, nargs="*")
            p.add_argument("--dry-run", action="store_true"); p.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rule = json.loads(RULE.read_text(encoding="utf-8"))
    ev = live_events(a.campaign)
    state, met, arc_done = window_state(ev, rule, a.target, a.level)
    marks = sum(1 for e in ev if e["kind"] == "continuity_invoked" and (e.get("details") or {}).get("target") == a.target)
    if a.cmd == "status":
        print(json.dumps({"rule_status": rule["status"], "window": state, "end_conditions_met": met, "arc_complete": arc_done, "level": a.level,
                          "marks": marks, "next_step": "commit continuity_expiring and show the notice" if met and state == "active" else None}, indent=1)); return 0
    if not rule["status"].startswith("approved") and not a.dry_run:
        print(json.dumps({"refused": "Protagonist Continuity is not approved; standard death rules apply."})); return 3
    if a.target not in rule["protected_characters"] or state == "expired":
        print(json.dumps({"applies": False, "reason": "not protected" if state != "expired" else "window expired: death is permanent"})); return 0
    trig = would_die(ev, a.target)
    if not trig:
        print(json.dumps({"applies": False, "reason": "no unanswered would-die moment in the ledger"})); return 0
    if not a.dry_run and (a.path_roll is None or a.cost_rolls is None):
        mark = marks + 1
        paths, fixed = survival_paths(ev, trig)
        print(json.dumps({"needs_rolls": True, "mark": mark, "survival_die": None if fixed else f"1d{len(paths)}", "survival_paths": paths,
                          "cost_die": f"1d{len(eligible_costs(ev, a.target, trig, mark, rule))}", "cost_count": mark,
                          "eligible_costs": eligible_costs(ev, a.target, trig, mark, rule)}, indent=1)); return 0
    rng = random.Random(a.seed)
    mark = marks + 1
    paths, fixed = survival_paths(ev, trig)
    path = paths[0] if fixed else pick(paths, None if a.dry_run else [a.path_roll], 1, rng)[0]
    costs = eligible_costs(ev, a.target, trig, mark, rule)
    chosen = pick(costs, None if a.dry_run else a.cost_rolls, mark, rng)
    grievous_extra = mark >= rule["extra_grievous_from_mark"]
    T = a.target.title()
    events = [{"kind": "gm_decision", "visibility": "gm_only", "summary": f"Continuity survival path for {T}: {path['id']} ({'hidden truth' if fixed else 'rolled on ' + ', '.join(p['id'] for p in paths)}).",
               "caused_by": path["evidence"], "details": {"target": a.target, "path": path["id"], "eligible": [p["id"] for p in paths]}},
              {"kind": "continuity_invoked", "visibility": "player", "summary": f"{T} does not die. Unconscious and stable at 0 HP (Protagonist Continuity, defeat mark {mark}).",
               "caused_by": [trig["event_id"]], "details": {"target": a.target, "mark": mark, "costs": [c["id"] for c in chosen], "grievous_extra": grievous_extra}}]
    for c in chosen:
        events.append({"kind": "continuity_cost", "visibility": "gm_only" if c["id"] == "escalation" else "player", "summary": c["effect"], "caused_by": c["evidence"],
                       "details": {"target": a.target, "cost": c["id"], "grievous": c.get("grievous", False)}})
    if grievous_extra:
        events.append({"kind": "lasting_injury", "visibility": "player", "summary": f"{T} carries an additional grievous wound from defeat mark {mark} (persists until bacta-tank treatment or cybernetics).",
                       "caused_by": [trig["event_id"]], "details": {"target": a.target, "grievous": True, "source": "continuity_mark"}})
    events.append({"kind": "condition_change", "visibility": "player", "summary": f"{T} is unconscious and stable at 0 HP.", "details": {"target": a.target, "conditions": ["unconscious", "stable"]}})
    print(json.dumps({"applies": True, "label": "SIMULATION, NOT CANON" if a.dry_run else "authorized",
                      "trigger": trig["event_id"], "target": a.target, "mark": mark, "window": state,
                      "preserved": "all committed events stand; no roll is changed; no ally, item or escape is invented",
                      "state": {"hp": 0, "conditions": ["unconscious", "stable"], "wake": rule["wake"]},
                      "survival_path": path, "eligible_paths": paths, "eligible_costs": costs, "chosen_costs": chosen,
                      "events_to_commit": events}, indent=1)); return 0


if __name__ == "__main__":
    sys.exit(main())
