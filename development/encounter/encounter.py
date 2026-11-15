"""Encounter controller: initiative, per-actor turn budgets and encounter mode, derived from the ledger.

There is no encounter state store. The state is a pure fold over committed ledger events, so it is
replayable, survives interruption wherever the ledger does, and cannot disagree with the record.
Rules: campaigns/starwars_litrpg/creator/ENCOUNTER_RULING.md (provisional, scoped to this campaign).

Events it reads (`details` shown):
  encounter_start   {encounter_id, mode, participants: [participant...]}
  encounter_join    {participant}                       joins at its initiative; acts from its next slot
  encounter_leave   {actor_id, reason}
  encounter_mode    {mode: combat|standoff|scene, reason, cites: [event ids]}
  turn_start        {actor_id}                          must be the next actor in order
  resource_spent    {actor_id, resource, amount, for}   action | bonus_action | reaction | object_interaction | movement_ft
  ready_set         {actor_id, trigger, does}           spends the action, on the actor's own turn
  ready_fired       {actor_id}                          spends the reaction, any time before the actor's next turn
  turn_end          {actor_id}
  condition_change  {target, add: [...], remove: [...]} (existing kind)
  encounter_end     {reason}

participant: {actor_id, label, side, initiative, group, hidden, speed_ft, bonus_action_eligible,
              control: {decides: "player" | "gm" | "player_directed" | null, basis}}

`group` puts several actors on one initiative count. It is an ordering convenience only: every member
has its own budget, its own reaction and its own single turn, taken one after another.
`hidden` actors are tracked in full here and never named, counted or located in the public view.
"""
import copy
import json

RESOURCES = ("action", "bonus_action", "reaction", "object_interaction", "movement_ft")
MODES = ("combat", "standoff", "scene")
CONTROL = ("player", "gm", "player_directed")
NO_TURN = {"incapacitated", "unconscious", "dead", "stunned", "paralyzed", "petrified"}
NO_REACTION = NO_TURN | {"surprised"}
KINDS = {"encounter_start", "encounter_join", "encounter_leave", "encounter_mode", "turn_start", "resource_spent",
         "ready_set", "ready_fired", "turn_end", "condition_change", "encounter_end"}


class EncounterError(ValueError):
    def __init__(self, code, message, event_id=None):
        super().__init__(f"{code}: {message}")
        self.code, self.message, self.event_id = code, message, event_id


def empty():
    return {"active": False, "encounter_id": None, "mode": "scene", "round": 0, "actors": {}, "order": [],
            "current": None, "acted": [], "mode_history": [], "left": {}}


def _participant(raw):
    need = ("actor_id", "label", "side", "initiative")
    if not isinstance(raw, dict) or any(raw.get(k) in (None, "") for k in need):
        raise EncounterError("BAD_PARTICIPANT", "a participant needs actor_id, label, side and initiative")
    control = raw.get("control") or {}
    decides = control.get("decides")
    if decides is not None and decides not in CONTROL:
        raise EncounterError("BAD_CONTROL", "control.decides is player, gm, player_directed or null (undecided)")
    return {"actor_id": raw["actor_id"], "label": raw["label"], "side": raw["side"], "initiative": raw["initiative"],
            "group": raw.get("group") or raw["actor_id"], "hidden": bool(raw.get("hidden")),
            "speed_ft": int(raw.get("speed_ft", 30)), "bonus_action_eligible": bool(raw.get("bonus_action_eligible")),
            "control": {"decides": decides, "basis": control.get("basis")}, "conditions": [],
            "budget": {"action": 0, "bonus_action": 0, "reaction": 1, "object_interaction": 0, "movement_ft": 0},
            "spent": [], "ready": None, "turns_taken": 0}


def _order(state):
    """Initiative order: highest count first; ties keep the order of entry. Group members stay adjacent."""
    actors = list(state["actors"].values())
    groups = {}
    for position, actor in enumerate(actors):
        groups.setdefault(actor["group"], {"initiative": actor["initiative"], "first": position, "members": []})["members"].append(actor["actor_id"])
    ranked = sorted(groups.values(), key=lambda g: (-g["initiative"], g["first"]))
    return [member for group in ranked for member in group["members"]]


def _next(state):
    """The actor whose turn must start next, or None when the round is complete."""
    for actor_id in state["order"]:
        if actor_id not in state["acted"]:
            return actor_id
    return None


def apply(state, event):
    """Fold one committed event. Raises EncounterError when the event breaks the rules."""
    kind, d, eid = event.get("kind"), event.get("details") or {}, event.get("event_id")
    def fail(code, message):
        raise EncounterError(code, message, eid)
    if kind not in KINDS:
        return state
    if kind == "encounter_start":
        if state["active"]:
            fail("ALREADY_ACTIVE", "an encounter is already running")
        if d.get("mode", "combat") not in MODES:
            fail("BAD_MODE", "unknown encounter mode")
        state = empty()
        state.update(active=True, encounter_id=d.get("encounter_id") or eid, mode=d.get("mode", "combat"), round=1,
                     mode_history=[{"mode": d.get("mode", "combat"), "at": eid, "reason": d.get("reason") or "encounter began"}])
        for raw in d.get("participants") or []:
            p = _participant(raw)
            if p["actor_id"] in state["actors"]:
                fail("DUPLICATE_ACTOR", f"{p['actor_id']} is listed twice")
            state["actors"][p["actor_id"]] = p
        if not state["actors"]:
            fail("BAD_PARTICIPANT", "an encounter needs participants")
        state["order"] = _order(state)
        return state
    if kind == "condition_change":
        actor = state["actors"].get(d.get("target"))
        if actor:
            actor["conditions"] = sorted((set(actor["conditions"]) | {str(c).lower() for c in d.get("add", [])}) - {str(c).lower() for c in d.get("remove", [])})
            if set(actor["conditions"]) & NO_REACTION and actor["ready"]:
                actor["ready"] = None                     # a readied action is lost with the ability to react
        return state
    if not state["active"]:
        fail("NO_ENCOUNTER", f"{kind} needs a running encounter")
    if kind == "encounter_end":
        state["active"], state["current"], state["mode"] = False, None, "scene"
        state["mode_history"].append({"mode": "scene", "at": eid, "reason": d.get("reason") or "encounter ended"})
        return state
    if kind == "encounter_mode":
        if d.get("mode") not in MODES or not str(d.get("reason") or "").strip():
            fail("BAD_MODE", "a mode change needs a known mode and a stated reason")
        if state["current"]:
            fail("MID_TURN", "the mode changes between turns, not in the middle of one")
        if d["mode"] != state["mode"]:
            state["mode"] = d["mode"]
            state["mode_history"].append({"mode": d["mode"], "at": eid, "reason": d["reason"], "cites": d.get("cites", [])})
        return state
    if kind == "encounter_join":
        p = _participant(d.get("participant"))
        if p["actor_id"] in state["actors"]:
            fail("DUPLICATE_ACTOR", f"{p['actor_id']} is already in the encounter")
        state["actors"][p["actor_id"]] = p
        state["order"] = _order(state)
        # A count that has already come up this round (someone at or after it has acted or is acting) waits for the
        # next round; a count still ahead is taken this round.
        frontier = [state["order"].index(a) for a in state["acted"] + ([state["current"]] if state["current"] else []) if a in state["order"]]
        if frontier and state["order"].index(p["actor_id"]) < max(frontier):
            state["acted"].append(p["actor_id"])
        return state
    actor = state["actors"].get(d.get("actor_id"))
    if actor is None:
        fail("UNKNOWN_ACTOR", f"{d.get('actor_id')} is not in this encounter")
    aid = actor["actor_id"]
    if kind == "encounter_leave":
        if state["current"] == aid:
            state["current"] = None
        state["left"][aid] = {"reason": d.get("reason"), "at": eid}
        del state["actors"][aid]
        state["order"] = [a for a in state["order"] if a != aid]
        state["acted"] = [a for a in state["acted"] if a != aid]
        return state
    if kind == "turn_start":
        if state["mode"] != "combat":
            fail("NOT_IN_INITIATIVE", "turns are taken in initiative only in combat mode")
        if state["current"]:
            fail("TURN_OPEN", f"{state['current']}'s turn has not ended")
        expected = _next(state)
        if expected is None:
            state["round"] += 1
            state["acted"] = []
            expected = _next(state)
        if aid != expected:
            fail("OUT_OF_ORDER", f"it is {expected}'s turn, not {aid}'s")
        if actor["control"]["decides"] is None:
            fail("CONTROL_UNDECIDED", f"who decides {aid}'s actions has not been ruled; it cannot take a turn until it is")
        state["current"] = aid
        actor["ready"] = None                              # an unused readied action lapses at the start of the next turn
        skip = bool(set(actor["conditions"]) & NO_TURN)
        actor["budget"] = {"action": 0 if skip else 1, "bonus_action": 0 if skip or not actor["bonus_action_eligible"] else 1,
                           "reaction": 0 if set(actor["conditions"]) & NO_REACTION else 1,
                           "object_interaction": 0 if skip else 1, "movement_ft": 0 if skip else actor["speed_ft"]}
        actor["spent"] = []
        actor["turns_taken"] += 1
        return state
    if kind == "turn_end":
        if state["current"] != aid:
            fail("NOT_YOUR_TURN", f"{aid} has no open turn to end")
        state["current"] = None
        state["acted"].append(aid)
        for resource in ("action", "bonus_action", "object_interaction", "movement_ft"):
            actor["budget"][resource] = 0                  # nothing but the reaction carries past the end of a turn
        return state
    if kind in ("resource_spent", "ready_set", "ready_fired"):
        resource = {"ready_set": "action", "ready_fired": "reaction"}.get(kind, d.get("resource"))
        amount = 1 if kind != "resource_spent" else d.get("amount", 1)
        if resource not in RESOURCES or type(amount) is not int or amount < 1:
            fail("BAD_RESOURCE", "unknown resource or amount")
        if resource != "reaction" and state["current"] != aid:
            fail("OFF_TURN", f"{aid} can spend its {resource.replace('_', ' ')} only on its own turn; off-turn it has a reaction and nothing else")
        if resource == "reaction" and set(actor["conditions"]) & NO_REACTION:
            fail("NO_REACTION", f"{aid} cannot take reactions now")
        if kind == "resource_spent" and resource == "movement_ft" and d.get("dash"):
            fail("BAD_RESOURCE", "Dash is an action that adds movement; record the action, then the movement")
        if kind == "resource_spent" and d.get("grants_movement_ft"):
            actor["budget"]["movement_ft"] += int(d["grants_movement_ft"])       # Dash
        if actor["budget"][resource] < amount:
            fail("NO_BUDGET", f"{aid} has no {resource.replace('_', ' ')} left ({actor['budget'][resource]} available, {amount} asked)")
        if kind == "ready_fired" and not actor["ready"]:
            fail("NOTHING_READIED", f"{aid} has no readied action to release")
        if kind == "ready_set" and (not str(d.get("trigger") or "").strip() or not str(d.get("does") or "").strip()):
            fail("BAD_READY", "a readied action names its trigger and what is done")
        actor["budget"][resource] -= amount
        actor["spent"].append({"resource": resource, "amount": amount, "for": d.get("for") or kind, "at": eid})
        if kind == "ready_set":
            actor["ready"] = {"trigger": d["trigger"], "does": d["does"], "set_at": eid}
        if kind == "ready_fired":
            actor["ready"] = None
        return state
    return state


def fold(events, state=None):
    state = copy.deepcopy(state) if state else empty()
    for event in events:
        state = apply(state, event)
    return state


def check(committed, drafts):
    """Would these draft events, appended in order, keep the encounter legal? Returns (state_after, problems).
    Nothing is written. Drafts are judged against the fold of the committed record only."""
    state = fold(committed)
    problems = []
    for index, draft in enumerate(drafts, 1):
        try:
            state = apply(state, dict(draft, event_id=draft.get("event_id") or f"draft_{index}"))
        except EncounterError as error:
            problems.append({"code": "ENCOUNTER_" + error.code, "message": f"event {index}: {error.message}"})
            break
    return state, problems


def whose_decision(state):
    """Who must speak next: the player (their own character or one they direct), the GM, or an owner ruling."""
    if not state["active"]:
        return {"kind": "none"}
    if state["mode"] != "combat":
        return {"kind": "player", "why": f"{state['mode']}: no initiative order; the player declares, the world answers"}
    aid = state["current"] or _next(state) or (state["order"][0] if state["order"] else None)
    if aid is None:
        return {"kind": "none"}
    decides = state["actors"][aid]["control"]["decides"]
    if decides is None:
        return {"kind": "ruling_needed", "actor_id": aid, "options": ["player_directed", "gm"],
                "why": "who decides this character's actions in an encounter has not been ruled"}
    return {"kind": "gm" if decides == "gm" else "player", "actor_id": aid, "control": decides}


def assess_mode(state, events, facts):
    """Advisory only. `facts` come from the GM, each citing committed events:
        {"can_affect": [{"from", "to", "how", "cites"}],
         "contests":   [{"what", "scale": "rounds"|"minutes", "cites"}],
         "hazards":    [{"what", "scale": "rounds"|"minutes", "cites"}]}
    Initiative is warranted by any meaningful contest decided round by round, not only by attack range: a chase, a
    race to a door or a switch, a breach in progress, someone slipping away unseen, a countdown, a readied action
    waiting on a trigger, a hazard spreading by the round. `can_affect` is any cited way one side can act on the
    other within a round (reach, a line of fire, a power, a thrown thing), whether or not anyone has attacked. Otherwise the same people in the same place are a standoff: no initiative, time
    passes as the fiction needs, and combat resumes the moment a listed trigger happens. Never changes anything."""
    if not state["active"]:
        return {"recommend": "scene", "because": ["no encounter is running"]}
    seq = lambda e: int(str(e.get("event_id", "evt_0")).split("_")[1]) if str(e.get("event_id", "")).startswith("evt_") else -1
    contact = [e["event_id"] for e in events if e.get("kind") in ("hp_change", "attack_resolved") and
               (e.get("details") or {}).get("target") in state["actors"]]
    reach = [f for f in facts.get("can_affect", []) if f.get("cites")]
    fast = [h for h in facts.get("hazards", []) if h.get("scale") == "rounds" and h.get("cites")]
    racing = [c for c in facts.get("contests", []) if c.get("scale") == "rounds" and c.get("cites")]
    readied = [a["actor_id"] for a in state["actors"].values() if a["ready"]]
    because = []
    if racing:
        because.append(f"{len(racing)} cited contest(s) being decided round by round")
    if readied:
        because.append(f"{len(readied)} readied action(s) waiting on a trigger")
    if reach:
        because.append(f"{len(reach)} cited way(s) one side can act on the other within a round")
    if fast:
        because.append(f"{len(fast)} cited hazard(s) running round by round")
    if reach or fast or racing or readied:
        return {"recommend": "combat", "because": because, "last_contact": contact[-1] if contact else None}
    slow = [h for h in facts.get("hazards", []) + facts.get("contests", []) if h.get("scale") == "minutes"]
    return {"recommend": "standoff", "last_contact": contact[-1] if contact else None,
            "because": ["no cited way for either side to act on the other within a round",
                        "no cited contest or hazard being decided round by round", "no readied action waiting on a trigger"]
                       + ([f"{len(slow)} slower contest(s) or hazard(s) keep running in scene time"] if slow else []),
            "resume_combat_when": ["an attack or hostile contact", "a barrier between the sides is opened or breached",
                                   "either side moves to where it can act on the other", "a contest or hazard starts to be decided round by round"],
            "requires": "a committed encounter_mode event with this reason; hostile actors keep their positions, wounds and reactions"}


def public(state):
    """What the player may see. Hidden actors are never named, counted, ordered individually or located."""
    if not state["active"]:
        return None
    def row(actor):
        b = actor["budget"]
        return {"actor_id": actor["actor_id"], "label": actor["label"], "side": actor["side"], "initiative": actor["initiative"],
                "control": actor["control"]["decides"] or "undecided", "conditions": actor["conditions"],
                "budget": {"action": b["action"], "bonus_action": b["bonus_action"] if actor["bonus_action_eligible"] else None,
                           "reaction": b["reaction"], "object_interaction": b["object_interaction"],
                           "movement_ft": b["movement_ft"], "speed_ft": actor["speed_ft"]},
                "ready": {"trigger": actor["ready"]["trigger"], "does": actor["ready"]["does"]} if actor["ready"] else None}
    slots, seen = [], set()
    for actor_id in state["order"]:
        actor = state["actors"][actor_id]
        if actor["hidden"]:
            key = ("hidden", actor["side"], actor["initiative"])
            if key not in seen:                               # one anonymous slot per side and count, however many there are
                seen.add(key)
                slots.append({"slot": f"hidden:{actor['side']}:{actor['initiative']}", "label": "Others you cannot see", "side": actor["side"],
                              "initiative": actor["initiative"], "unseen": True, "members": [actor_id]})
            else:
                next(s for s in slots if s.get("slot") == f"hidden:{actor['side']}:{actor['initiative']}")["members"].append(actor_id)
        else:
            slots.append(dict(row(actor), unseen=False, members=[actor_id]))
    def status(slot):
        members = slot["members"]
        if state["current"] in members:
            return "acting"
        return "done" if all(m in state["acted"] for m in members) else "waiting"
    out_slots = []
    for slot in slots:
        entry = {k: v for k, v in slot.items() if k != "members"}
        entry["status"] = status(slot) if state["mode"] == "combat" else "no order"
        out_slots.append(entry)
    current = next((s for s in out_slots if s["status"] == "acting"), None)
    waiting = [s for s in out_slots if s["status"] == "waiting"]
    nxt = waiting[0] if waiting else (out_slots[0] if out_slots and state["mode"] == "combat" else None)
    if current is None and waiting and state["mode"] == "combat":
        current, nxt = None, waiting[0]
    decision = whose_decision(state)
    if decision.get("actor_id") and state["actors"].get(decision["actor_id"], {}).get("hidden"):
        decision = {"kind": decision["kind"]}
    return {"mode": state["mode"], "round": state["round"] if state["mode"] == "combat" else None,
            "current": current and current["label"], "next": nxt and nxt["label"], "order": out_slots,
            "decision": decision, "mode_since": state["mode_history"][-1]["at"], "mode_reason": state["mode_history"][-1]["reason"]}


def private(state):
    """Full GM view, hidden actors included. Never publish."""
    return copy.deepcopy(state)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / ".claude/skills/litrpg-ledger"))
    import ledger
    campaign = Path(sys.argv[1])
    state = fold(ledger.load_all(campaign))
    print(json.dumps({"public": public(state), "decision": whose_decision(state)}, indent=1))
