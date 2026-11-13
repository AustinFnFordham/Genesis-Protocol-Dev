"""Structural guard against NPC re-evaluations that ignore changed circumstances.

A GM provider that decides what an NPC or enemy does this round records one evaluation
per NPC with the tables it fixes before rolling:

  {"npc": "dog_c", "since": "evt_0412" | null, "changes": ["evt_0415", ...],
   "no_change_reason": "...", "outcome_key": "hold", "repeat_reason": "...", "basis": "..."}

The guard is mechanical and proves bookkeeping, not judgment:
  NPC_SINCE          `since` is not the NPC's last recorded evaluation.
  NPC_UNKNOWN_EVENT  a cited change is not a committed event after `since`.
  NPC_IGNORED_CHANGE a committed event after `since` names this NPC (as actor, target or npc)
                     and is not cited: the evaluation did not look at it.
  NPC_NO_CHANGE      nothing is cited and no reason says why nothing changed.
  NPC_REPEAT         the same outcome a third time running without a stated reason that cites
                     what was considered. Repeating is allowed; repeating blindly is not.
It never forces an outcome, never makes an NPC aggressive or passive, and reads only events.
Legacy rulings without structured evaluations count as "no previous evaluation".
"""
import re

ID = re.compile(r"^evt_(\d+)$")


def seq(event_id):
    m = ID.match(event_id or "")
    return int(m.group(1)) if m else -1


def history(events, npc):
    """Recorded structured evaluations for one NPC, oldest first: [(event_id, evaluation)]."""
    out = []
    for e in events:
        for ev in (e.get("details") or {}).get("npc_evaluations", []) or []:
            if isinstance(ev, dict) and ev.get("npc") == npc:
                out.append((e["event_id"], ev))
    return out


def names(event, npc):
    d = event.get("details") or {}
    return event.get("actor") == npc or d.get("target") == npc or d.get("npc") == npc or npc in (d.get("targets") or [])


def check(evaluations, events):
    """Return [{code, npc, message}] for the evaluations a provider wants to record now."""
    problems, by_id = [], {e["event_id"]: e for e in events}
    def bad(code, npc, message):
        problems.append({"code": code, "npc": npc, "message": message})
    seen = set()
    for ev in evaluations or []:
        npc = ev.get("npc") if isinstance(ev, dict) else None
        if not isinstance(npc, str) or not npc or npc in seen:
            bad("NPC_SHAPE", npc, "each evaluation names one NPC once")
            continue
        seen.add(npc)
        if not isinstance(ev.get("outcome_key"), str) or not ev["outcome_key"] or not isinstance(ev.get("basis"), str) or not ev["basis"].strip():
            bad("NPC_SHAPE", npc, "outcome_key and basis (motive, knowledge, position, injuries, orders) are required")
        past = history(events, npc)
        last = past[-1][0] if past else None
        if ev.get("since") != last:
            bad("NPC_SINCE", npc, f"since must be the last recorded evaluation ({last})")
            continue
        floor = seq(last) if last else -1
        changes = ev.get("changes") or []
        for c in changes:
            if c not in by_id or seq(c) <= floor:
                bad("NPC_UNKNOWN_EVENT", npc, f"{c} is not a committed event after {last}")
        if last:
            missed = [e["event_id"] for e in events if seq(e["event_id"]) > floor and names(e, npc)
                      and e["event_id"] not in changes and not history([e], npc)]
            if missed:
                bad("NPC_IGNORED_CHANGE", npc, "committed events naming this NPC were not considered: " + ", ".join(missed[:8]))
        if not changes and not str(ev.get("no_change_reason") or "").strip():
            bad("NPC_NO_CHANGE", npc, "cite what changed since the last evaluation, or say why nothing relevant did")
        streak = [p[1].get("outcome_key") for p in past[-2:]]
        if len(streak) == 2 and streak[0] == streak[1] == ev.get("outcome_key") and not str(ev.get("repeat_reason") or "").strip():
            bad("NPC_REPEAT", npc, "third identical outcome in a row: state the causal reason it still holds")
    return problems
