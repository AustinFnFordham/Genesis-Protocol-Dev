"""Encounter controller tests. Synthetic actors only; no campaign is read or written.
Run: python3 -B development/encounter/test_encounter.py
"""
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import encounter as E

N = [0]


def ev(kind, **details):
    N[0] += 1
    return {"event_id": f"evt_{N[0]:04d}", "kind": kind, "details": details}


def start(wick="gm", mode="combat", role=None):
    """wick="player_directed" stands for a formally recruited companion: the recruitment is recorded first."""
    N[0] = 0
    P = lambda i, label, side, init, **k: dict(actor_id=i, label=label, side=side, initiative=init, **k)
    recruited = [ev("party_joined", member_id="wick", name="Wick", basis="test: the player recruited him on the record")] if wick == "player_directed" or role == "party_member" else []
    return recruited + [ev("encounter_start", encounter_id="barn", mode=mode, participants=[
        P("aero", "Aero", "party", 21, control={"decides": "player", "basis": "CAMPAIGN_CHARTER: the player controls Aero"}),
        P("wick", "Wick", "party", 12, control={"decides": wick, "basis": "test"}, **({"role": role} if role else {})),
        P("dog_a", "SECRET_ALPHA", "pack", 7, group="pack", hidden=True, speed_ft=40, control={"decides": "gm"}),
        P("dog_b", "SECRET_BETA", "pack", 7, group="pack", hidden=True, speed_ft=40, control={"decides": "gm"}),
        P("dog_c", "SECRET_GAMMA", "pack", 7, group="pack", hidden=True, speed_ft=40, control={"decides": "gm"})])]


def turn(actor, *spends):
    return [ev("turn_start", actor_id=actor)] + list(spends) + [ev("turn_end", actor_id=actor)]


def spend(actor, resource, amount=1, **more):
    return ev("resource_spent", actor_id=actor, resource=resource, amount=amount, **more)


def code(events, extra):
    try:
        E.fold(events + extra)
    except E.EncounterError as error:
        return error.code
    return None


def test_order_and_each_actor_exactly_once():
    events = start()
    assert E.fold(events)["order"] == ["aero", "wick", "dog_a", "dog_b", "dog_c"]
    assert code(events, [ev("turn_start", actor_id="wick")]) == "OUT_OF_ORDER"
    events += turn("aero")
    assert code(events, [ev("turn_start", actor_id="aero")]) == "OUT_OF_ORDER"          # not twice in a round
    assert code(events, [ev("turn_start", actor_id="wick"), ev("turn_start", actor_id="dog_a")]) == "TURN_OPEN"
    events += turn("wick") + turn("dog_a") + turn("dog_b") + turn("dog_c")
    state = E.fold(events)
    assert state["round"] == 1 and state["acted"] == state["order"]
    state = E.fold(events + [ev("turn_start", actor_id="aero")])
    assert state["round"] == 2 and state["current"] == "aero" and all(a["turns_taken"] == 1 for k, a in state["actors"].items() if k != "aero")


def test_wick_has_his_own_turn_and_budget():
    events = start() + turn("aero", spend("aero", "object_interaction"))
    events += [ev("turn_start", actor_id="wick"), spend("wick", "action", **{"for": "fires the blaster"})]
    state = E.fold(events)
    assert state["actors"]["wick"]["budget"]["action"] == 0 and state["actors"]["aero"]["budget"]["action"] == 0   # Aero's turn is over
    assert code(events, [spend("wick", "action")]) == "NO_BUDGET"                          # one action, not two
    assert code(events, [spend("wick", "movement_ft", 35)]) == "NO_BUDGET"
    assert code(events, [spend("wick", "bonus_action")]) == "NO_BUDGET"                    # none unless a feature grants one
    dashed = E.fold(start() + turn("aero") + [ev("turn_start", actor_id="wick"), spend("wick", "action", grants_movement_ft=30), spend("wick", "movement_ft", 55)])
    assert dashed["actors"]["wick"]["budget"]["movement_ft"] == 5


def test_a_command_gives_no_extra_turn_and_costs_the_speaker_nothing():
    events = start() + [ev("turn_start", actor_id="aero")]
    before = copy.deepcopy(E.fold(events)["actors"]["aero"]["budget"])
    # Aero says "Fire." Speech is not a resource event at all: nothing is spent.
    assert E.fold(events)["actors"]["aero"]["budget"] == before
    # Wick cannot answer with his action on Aero's turn...
    assert code(events, [spend("wick", "action", **{"for": "fires on the word"})]) == "OFF_TURN"
    assert code(events, [ev("ready_fired", actor_id="wick")]) == "NOTHING_READIED"
    # ...unless he readied it on his own earlier turn; then it costs his reaction, once.
    N[0] = 0
    events = start() + turn("aero") + [ev("turn_start", actor_id="wick"), ev("ready_set", actor_id="wick", trigger="Aero says fire", does="one shot at the door"),
                                      ev("turn_end", actor_id="wick")] + turn("dog_a") + turn("dog_b") + turn("dog_c") + [ev("turn_start", actor_id="aero")]
    assert code(events, [ev("ready_set", actor_id="wick", trigger="t", does="d")]) == "OFF_TURN"
    events += [ev("ready_fired", actor_id="wick")]
    state = E.fold(events)
    assert state["actors"]["wick"]["budget"]["reaction"] == 0 and state["actors"]["wick"]["ready"] is None
    assert state["actors"]["aero"]["budget"] == before and state["current"] == "aero"
    assert code(events, [ev("ready_fired", actor_id="wick")]) == "NO_BUDGET"               # the word does not buy a second shot
    assert code(events, [spend("wick", "reaction")]) == "NO_BUDGET"


def test_reaction_resets_at_the_start_of_the_actors_own_turn_only():
    events = start() + turn("aero") + [spend("wick", "reaction", **{"for": "flinch"})]      # off-turn, before his turn this round
    assert E.fold(events)["actors"]["wick"]["budget"]["reaction"] == 0
    events += turn("wick")
    state = E.fold(events)
    assert state["actors"]["wick"]["budget"]["reaction"] == 1, "regained at the start of his turn"
    events += [spend("wick", "reaction")] + turn("dog_a") + turn("dog_b") + turn("dog_c") + turn("aero")   # round boundary passes
    assert E.fold(events)["actors"]["wick"]["budget"]["reaction"] == 0, "a new round does not return it; his turn does"
    assert code(events, [spend("wick", "reaction")]) == "NO_BUDGET"
    assert E.fold(events + [ev("turn_start", actor_id="wick")])["actors"]["wick"]["budget"]["reaction"] == 1
    lapse = start() + turn("aero") + [ev("turn_start", actor_id="wick"), ev("ready_set", actor_id="wick", trigger="t", does="d"), ev("turn_end", actor_id="wick")] \
        + turn("dog_a") + turn("dog_b") + turn("dog_c") + turn("aero") + [ev("turn_start", actor_id="wick")]
    assert E.fold(lapse)["actors"]["wick"]["ready"] is None, "an unused readied action lapses at his next turn"


def test_dogs_share_a_count_not_a_pool():
    events = start() + turn("aero") + turn("wick") + [ev("turn_start", actor_id="dog_a"), spend("dog_a", "movement_ft", 40), spend("dog_a", "action", **{"for": "bite"})]
    assert code(events, [spend("dog_a", "movement_ft", 5)]) == "NO_BUDGET"                 # no unlimited movement
    assert code(events, [spend("dog_a", "action")]) == "NO_BUDGET"                         # no extra attack
    assert code(events, [spend("dog_b", "action")]) == "OFF_TURN"                          # B cannot lend A its action
    events += [ev("turn_end", actor_id="dog_a")]
    assert code(events, [ev("turn_start", actor_id="dog_c")]) == "OUT_OF_ORDER"
    events += [ev("turn_start", actor_id="dog_b"), spend("dog_b", "movement_ft", 40)]
    state = E.fold(events)
    assert state["actors"]["dog_b"]["budget"]["action"] == 1 and state["actors"]["dog_a"]["budget"]["action"] == 0
    assert state["actors"]["dog_c"]["budget"]["reaction"] == 1
    events += [spend("dog_c", "reaction", **{"for": "opportunity attack"})]
    assert code(events, [spend("dog_c", "reaction")]) == "NO_BUDGET"                       # each reaction tracked
    assert E.fold(events)["actors"]["dog_a"]["budget"]["reaction"] == 1


def test_incapacitated_join_leave_and_round_boundary():
    events = start() + turn("aero") + [ev("condition_change", target="wick", add=["Unconscious"])]
    events += [ev("turn_start", actor_id="wick")]
    state = E.fold(events)
    assert state["actors"]["wick"]["budget"] == {"action": 0, "bonus_action": 0, "reaction": 0, "object_interaction": 0, "movement_ft": 0}
    assert code(events, [spend("wick", "action")]) == "NO_BUDGET" and code(events, [spend("wick", "reaction")]) == "NO_REACTION"
    events += [ev("turn_end", actor_id="wick")]
    late = dict(actor_id="dog_d", label="SECRET_DELTA", side="pack", initiative=7, group="pack", hidden=True, control={"decides": "gm"})
    early = dict(actor_id="settler", label="A settler", side="party", initiative=15, control={"decides": "gm"})
    events += [ev("encounter_join", participant=early), ev("encounter_join", participant=late)]
    state = E.fold(events)
    assert state["order"] == ["aero", "settler", "wick", "dog_a", "dog_b", "dog_c", "dog_d"]
    assert "settler" in state["acted"], "its count already passed this round; it waits"
    assert "dog_d" not in state["acted"], "its count is still to come this round"
    events += turn("dog_a") + [ev("encounter_leave", actor_id="dog_b", reason="withdrew out of the fight")] + turn("dog_c") + turn("dog_d")
    events += [ev("turn_start", actor_id="aero")]
    state = E.fold(events)
    assert state["round"] == 2 and "dog_b" not in state["actors"] and state["left"]["dog_b"]["reason"]
    assert code(events, [spend("dog_b", "reaction")]) == "UNKNOWN_ACTOR"


def test_undecided_control_is_surfaced_never_assumed():
    events = start(wick=None) + turn("aero")
    state = E.fold(events)
    decision = E.whose_decision(state)
    assert decision == {"kind": "ruling_needed", "actor_id": "wick", "options": ["player_directed", "gm"],
                        "why": "who decides this character's actions in an encounter has not been ruled"}
    assert code(events, [ev("turn_start", actor_id="wick")]) == "CONTROL_UNDECIDED"
    assert code(events, [ev("turn_start", actor_id="dog_a")]) == "OUT_OF_ORDER", "he is not skipped either"
    assert E.public(state)["order"][1]["control"] == "undecided"
    assert E.whose_decision(E.fold(start(wick="player_directed") + turn("aero")))["kind"] == "player"
    assert E.whose_decision(E.fold(start(wick="gm") + turn("aero")))["kind"] == "gm"


def test_mode_transitions_are_explicit_and_reasoned():
    events = start() + turn("aero")
    facts_quiet = {"can_affect": [], "hazards": [{"what": "an ember in the boards", "scale": "minutes", "cites": ["evt_0001"]}]}
    advice = E.assess_mode(E.fold(events), events, facts_quiet)
    assert advice["recommend"] == "standoff" and advice["resume_combat_when"]
    assert E.fold(events)["mode"] == "combat", "advice changes nothing"
    assert code(events, [ev("encounter_mode", mode="standoff")]) == "BAD_MODE"            # no reason, no change
    assert code(events, [ev("turn_start", actor_id="wick"), ev("encounter_mode", mode="standoff", reason="r")]) == "MID_TURN"
    events += [ev("encounter_mode", mode="standoff", reason="every way in is shut; neither side can reach the other", cites=["evt_0001"])]
    state = E.fold(events)
    assert state["mode"] == "standoff" and len(state["actors"]) == 5, "nobody leaves; positions and wounds stand"
    assert code(events, [ev("turn_start", actor_id="wick")]) == "NOT_IN_INITIATIVE"
    view = E.public(state)
    assert view["mode"] == "standoff" and view["round"] is None and view["decision"]["kind"] == "player"
    hot = {"can_affect": [{"from": "pack", "to": "party", "how": "the hatch is open", "cites": ["evt_0003"]}], "hazards": []}
    assert E.assess_mode(state, events, hot)["recommend"] == "combat"
    assert E.assess_mode(state, events, {"can_affect": [{"from": "pack", "to": "party", "how": "uncited claim"}], "hazards": []})["recommend"] == "standoff"
    events += [ev("encounter_mode", mode="combat", reason="the hatch was opened", cites=["evt_0003"])]
    resumed = E.fold(events + [ev("turn_start", actor_id="wick")])
    assert resumed["mode"] == "combat" and resumed["current"] == "wick" and resumed["round"] == 1, "initiative resumes where it stood"
    assert E.fold(events + [ev("encounter_end", reason="the pack withdrew")])["active"] is False


def test_initiative_is_kept_for_contests_not_only_attack_range():
    events = start() + turn("aero")
    state = E.fold(events)
    quiet = {"can_affect": [], "contests": [], "hazards": []}
    assert E.assess_mode(state, events, quiet)["recommend"] == "standoff"
    # Nobody is in reach of anybody, but something is being decided this round.
    for contest in ("a dog is digging under the sill and will be through in two rounds", "Wick is running for the switch box", "the fire is climbing the wall"):
        key = "hazards" if "fire" in contest else "contests"
        advice = E.assess_mode(state, events, dict(quiet, **{key: [{"what": contest, "scale": "rounds", "cites": ["evt_0002"]}]}))
        assert advice["recommend"] == "combat", contest
    assert E.assess_mode(state, events, dict(quiet, contests=[{"what": "uncited worry", "scale": "rounds"}]))["recommend"] == "standoff"
    slow = E.assess_mode(state, events, dict(quiet, contests=[{"what": "they are waiting for dawn", "scale": "minutes", "cites": ["evt_0002"]}]))
    assert slow["recommend"] == "standoff" and any("slower" in line for line in slow["because"])
    # A readied action waiting on a trigger is a live contest by itself.
    waiting = events + [ev("turn_start", actor_id="wick"), ev("ready_set", actor_id="wick", trigger="the door opens", does="one shot"), ev("turn_end", actor_id="wick")]
    advice = E.assess_mode(E.fold(waiting), waiting, quiet)
    assert advice["recommend"] == "combat" and any("readied" in line for line in advice["because"])
    assert E.fold(waiting)["mode"] == "combat", "advice never changes the mode"


def test_control_classification_is_not_changed_by_play():
    """Who decides an actor is set when it joins. No turn, command, readied action or reaction rewrites it,
    and the controller exposes nothing a dice resolver could mistake for player control."""
    events = start(wick="gm") + turn("aero") + [ev("turn_start", actor_id="wick"), ev("ready_set", actor_id="wick", trigger="Aero says fire", does="one shot"),
                                               ev("turn_end", actor_id="wick")] + turn("dog_a") + turn("dog_b") + turn("dog_c") + [ev("turn_start", actor_id="aero"), ev("ready_fired", actor_id="wick")]
    state = E.fold(events)
    assert state["actors"]["wick"]["control"] == {"decides": "gm", "basis": "test"}
    assert E.fold(start(wick="player_directed") + turn("aero"))["actors"]["wick"]["control"]["decides"] == "player_directed"
    assert "controlled_actors" not in json.dumps(E.private(state)) and "resolution" not in json.dumps(E.public(state))
    # Only the explicit, owner-level records change who decides. Nothing that happens in play does.
    assert {k for k in E.KINDS if k.startswith(("control", "party"))} == set(E.OWNER_KINDS)
    for played in ("turn_start", "turn_end", "resource_spent", "ready_set", "ready_fired", "encounter_mode", "condition_change", "encounter_join"):
        assert played not in E.OWNER_KINDS


def test_an_allied_npc_is_gm_run_and_cannot_be_directed_without_recruitment():
    """Wick today: a temporary ally, not a party member. The GM decides his turn from his own motives. Asking, ordering,
    being obeyed or fighting on the same side changes nothing; only a recorded recruitment does."""
    events = start(wick="gm", role="allied_npc") + turn("aero")
    state = E.fold(events)
    assert (state["actors"]["wick"]["role"], state["actors"]["wick"]["control"]["decides"], state["party"]) == ("allied_npc", "gm", {})
    assert E.whose_decision(state) == {"kind": "gm", "actor_id": "wick", "control": "gm"}
    row = E.public(state)["order"][1]
    assert (row["role"], row["control"]) == ("allied_npc", "gm")
    assert code([], start(wick="player_directed", role="allied_npc")[1:]) == "CONTROL_NEEDS_RECRUITMENT"
    assert code([], start(wick="player_directed")[1:]) == "NOT_RECRUITED", "player-directed without a recorded recruitment"
    assert code([], start(wick="player", role="allied_npc")) == "BAD_CONTROL", "only the active player character is decided outright by the player"
    assert code(events, [ev("control_changed", actor_id="wick", decides="player_directed", basis="Aero told him to")]) == "CONTROL_NEEDS_RECRUITMENT"
    # An allied NPC with no control stated is the GM's by default: his turn is never blocked waiting for a ruling.
    default = start(wick=None, role="allied_npc") + turn("aero")
    assert E.fold(default)["actors"]["wick"]["control"]["decides"] == "gm" and not E.check(default, [ev("turn_start", actor_id="wick")])[1]
    # He acts on his own turn with his own budget, exactly once a round, and never on Aero's.
    assert code(start(wick="gm", role="allied_npc") + [ev("turn_start", actor_id="aero")], [spend("wick", "action")]) == "OFF_TURN"
    assert not E.check(events, [ev("turn_start", actor_id="wick"), spend("wick", "action"), spend("wick", "movement_ft", 30), ev("turn_end", actor_id="wick")])[1]


def test_recruitment_and_control_are_explicit_recorded_transitions():
    """Joining the party is a committed party_joined; from then the companion is player-directed in combat by default.
    Control can be handed to the GM and back only by control_changed with a basis, between that character's turns."""
    events = start(wick="gm", role="allied_npc") + turn("aero")
    joined = events + [ev("party_joined", member_id="wick", name="Wick", basis="the player recruited Wick; he agreed (owner record)")]
    state = E.fold(joined)
    assert (state["actors"]["wick"]["role"], state["actors"]["wick"]["control"]["decides"]) == ("party_member", "player_directed")
    assert "wick" in state["party"] and E.whose_decision(state) == {"kind": "player", "actor_id": "wick", "control": "player_directed"}
    assert (E.public(state)["order"][1]["role"], E.public(state)["order"][1]["control"]) == ("party_member", "player_directed")
    # His turn still uses his own budget and his own place in the order; directing him grants nobody an extra action.
    assert code(joined, [ev("turn_start", actor_id="dog_a")]) == "OUT_OF_ORDER"
    assert code(joined + [ev("turn_start", actor_id="wick"), spend("wick", "action")], [spend("wick", "action")]) == "NO_BUDGET"
    assert code(joined + [ev("turn_start", actor_id="wick")], [spend("aero", "action")]) == "OFF_TURN"
    # Explicit hand-over to the GM and back; never in the middle of his own turn, never without a basis.
    assert code(joined, [ev("control_changed", actor_id="wick", decides="gm")]) == "BAD_CONTROL"
    assert code(joined + [ev("turn_start", actor_id="wick")], [ev("control_changed", actor_id="wick", decides="gm", basis="x")]) == "MID_TURN"
    handed = joined + [ev("control_changed", actor_id="wick", decides="gm", basis="the player asked the GM to run him this fight")]
    assert E.fold(handed)["actors"]["wick"]["control"]["decides"] == "gm" and E.whose_decision(E.fold(handed))["kind"] == "gm"
    assert E.fold(handed + [ev("control_changed", actor_id="wick", decides="player_directed", basis="the player took him back")])["actors"]["wick"]["control"]["decides"] == "player_directed"
    assert code(joined, [ev("control_changed", actor_id="aero", decides="gm", basis="x")]) == "CONTROL_NEEDS_RECRUITMENT", "the player character is never handed over this way"
    # Leaving the party is as explicit, and returns him to the GM.
    left = E.fold(joined + [ev("party_left", member_id="wick", reason="he goes home")])
    assert (left["actors"]["wick"]["role"], left["actors"]["wick"]["control"]["decides"], left["party"]) == ("allied_npc", "gm", {})
    # Recruitment recorded outside a fight carries into the next one.
    N[0] = 100
    before = [ev("party_joined", member_id="wick", name="Wick", basis="recruited on the road")]
    later = E.fold(before + start(wick=None, role="party_member")[1:])
    assert later["actors"]["wick"]["control"]["decides"] == "player_directed"


def test_outside_combat_companions_are_gm_performed():
    """In standoff or scene the player declares for the active player character only; a recruited companion is performed
    by the GM unless the player has explicitly taken them as the active character (a separate record, not modelled here)."""
    state = E.fold(start(wick="player_directed", mode="standoff"))
    assert E.whose_decision(state)["kind"] == "player" and "actor_id" not in E.whose_decision(state)
    assert code(start(wick="player_directed", mode="standoff"), [ev("turn_start", actor_id="wick")]) == "NOT_IN_INITIATIVE"
    assert all(row["status"] == "no order" for row in E.public(state)["order"])


def test_public_view_hides_hidden_actors():
    events = start() + turn("aero") + turn("wick") + [ev("turn_start", actor_id="dog_a"), spend("dog_a", "movement_ft", 40)]
    state = E.fold(events)
    view = E.public(state)
    text = json.dumps(view)
    for secret in ("SECRET", "dog_a", "dog_b", "dog_c", "speed_ft\": 40"):
        assert secret not in text, secret
    assert [s["label"] for s in view["order"]] == ["Aero", "Wick", "Others you cannot see"], "one slot, however many there are"
    assert view["current"] == "Others you cannot see" and view["next"] == "Aero" and view["round"] == 1   # next known: the top of the next round
    assert "budget" not in view["order"][2] and view["order"][2]["status"] == "acting"
    assert view["order"][0]["budget"]["reaction"] == 1 and view["order"][0]["status"] == "done"
    assert "actor_id" not in view["decision"]
    assert "SECRET_ALPHA" in json.dumps(E.private(state))                                  # the GM view has it
    waiting = E.public(E.fold(start() + [ev("turn_start", actor_id="aero")]))
    assert (waiting["current"], waiting["next"]) == ("Aero", "Wick")


def test_duplicate_events_and_interrupted_recovery():
    events = start() + [ev("turn_start", actor_id="aero"), spend("aero", "object_interaction"), spend("aero", "movement_ft", 10)]
    # Interrupted mid-turn: the ledger holds the first steps. Folding the same record again gives the same state.
    state = E.fold(events)
    assert E.fold(events) == state and state["current"] == "aero" and state["actors"]["aero"]["budget"]["movement_ft"] == 20
    # A retry that would spend the same thing again is refused; the turn resumes with what is left.
    assert code(events, [spend("aero", "object_interaction")]) == "NO_BUDGET"
    after, problems = E.check(events, [dict(kind="resource_spent", details={"actor_id": "aero", "resource": "action"}),
                                       dict(kind="turn_end", details={"actor_id": "aero"})])
    assert not problems and after["current"] is None and E.fold(events) == state, "check never mutates the record"
    # Resuming from a prefix equals folding the whole record.
    rest = turn("wick")
    whole = events + [ev("turn_end", actor_id="aero")] + rest
    assert E.fold(whole[4:], E.fold(whole[:4])) == E.fold(whole)
    _, problems = E.check(whole, [dict(kind="turn_start", details={"actor_id": "aero"})])
    assert problems and problems[0]["code"] == "ENCOUNTER_OUT_OF_ORDER"
    assert E.fold([{"event_id": "evt_0001", "kind": "gm_narration", "details": {}}]) == E.empty(), "unrelated events are ignored"
    assert code([], [spend("aero", "action")]) == "NO_ENCOUNTER"




def test_an_encounter_already_under_way_starts_at_its_current_round():
    evs = start()
    evs[-1]["details"]["round"] = 11
    assert E.fold(evs)["round"] == 11
    evs[-1]["details"]["round"] = 0
    try:
        E.fold(evs)
    except Exception as error:  # noqa: BLE001
        assert "BAD_ROUND" in str(error) or "round" in str(error)
    else:
        raise AssertionError("round 0 accepted")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    print("ok encounter tests")
