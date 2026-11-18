"""Algorithm B — event-grounded episodic memory and appraisal candidates (TB4-WHISPER-001 §3, §4.B). Pure, read-only.

Nothing here is canonical. It returns *candidates* with citations; a PC's feelings change only if the player accepts
one, and an NPC's only through the GM's existing review (npc_review.py). No numbers, weights, meters or diagnoses.

Moral appraisal reads conduct: what was attempted or done, with what declared intent, what was known, what was
feasible, under what coercion and justification. Outcome and dice do not decide it: a miss is not mercy, a failed rescue
is not cruelty. An omission counts only with established awareness, capacity, low enough risk and an alternative.
Emotion alone never decides anything.
"""
from evidence import envelopes, knows, retrieve

HARM_ACTS = {"attack"}
HELP_ACTS = {"rescue", "help", "heal"}
LEAVE_ACTS = {"leave", "ignore", "walk_away"}


def memories(events, actor, entities=None):
    """Episodic memories for one actor: only events the actor witnessed, heard or authored; each cites its event."""
    envs = envelopes(events, entities)
    seen = retrieve(envs, ("pc", actor)) if actor == "aero" else knows(envs, actor)
    out, done = [], set()
    for x in seen:
        if x["source_event"] in done or x["type"] == "intention":
            continue
        done.add(x["source_event"])
        channel = "authored" if x.get("actor") == actor else "heard" if x["type"] in ("claim", "speech") else "witnessed"
        out.append({"memory_id": f"{actor}:{x['source_event']}", "actor": actor, "source_event": x["source_event"],
                    "channel": channel, "world_time": x.get("world_time"), "about": x["content"].get("subject") or x.get("summary"),
                    "type": x["type"], "salience": "unscored"})
    return out


def _cite(*events):
    return [e["event_id"] for e in events if e]


def moral(events, actor="aero"):
    """Return {finding, considered, citations}. finding is a label, never a score."""
    decl = [e for e in events if e["kind"] == "player_declaration" and e.get("actor") == actor]
    if not decl:
        return {"finding": "no_act_declared", "considered": [], "citations": []}
    d = decl[-1]; dd = d.get("details") or {}
    act, target = dd.get("act"), dd.get("target")
    motive = (dd.get("whisper") or {}).get("motive")
    coercion = [e for e in events if (e.get("details") or {}).get("coercion") and (e.get("details") or {}).get("subject") == actor]
    outcome = [e for e in events if e["kind"] in ("attack_resolved", "check_resolved") and (e.get("details") or {}).get("target") == target]
    considered = ["act", "target"] + (["declared_motive"] if motive else []) + (["coercion"] if coercion else [])
    if coercion:
        return {"finding": "compelled_mitigates", "considered": considered, "citations": _cite(coercion[0], d),
                "note": "Acted under coercion; responsibility for the result is shared with whoever coerced."}
    if act in HARM_ACTS:
        just = [e for e in outcome if (e.get("details") or {}).get("justification")]
        j = just[-1]["details"]["justification"] if just else "unruled"
        surrendered = [e for e in events if (e.get("details") or {}).get("condition") == "surrendered" and (e.get("details") or {}).get("subject") == target]
        considered += ["justification", "target_state", "outcome"]
        if j in ("defense_of_self", "defense_of_other"):
            return {"finding": "justified_force", "considered": considered, "citations": _cite(d, *just)}
        if j == "none_established" or surrendered:
            return {"finding": "attempted_unjustified_harm" if not any((e.get("details") or {}).get("hit") for e in outcome) else "unjustified_harm",
                    "considered": considered, "citations": _cite(*(surrendered[:1]), d, *outcome),
                    "note": "The attempt matters whether or not it landed; the outcome changes the harm, not the choice."}
        return {"finding": "unresolved", "considered": considered, "citations": _cite(d), "missing": ["justification ruling"]}
    if act in HELP_ACTS:
        failed = [e for e in outcome if (e.get("details") or {}).get("success") is False]
        return {"finding": "good_faith_effort" + ("_failed" if failed else ""), "considered": considered + ["outcome"],
                "citations": _cite(d, *failed), "note": "Failure to save is not a moral fault."}
    if act in LEAVE_ACTS:
        aware = [e for e in events if e["kind"] == "observation" and actor in (e.get("known_to") or []) and (e.get("details") or {}).get("subject") == target]
        able = [e for e in events if (e.get("details") or {}).get("subject") == actor and (e.get("details") or {}).get("capacity") == "able"
                and actor in (e.get("known_to") or [])]
        low_risk = [e for e in able if (e["details"].get("risk") == "low") and e["details"].get("alternatives")]
        considered += ["awareness", "capacity", "risk", "alternatives"]
        if aware and able and low_risk:
            return {"finding": "omission_relevant", "considered": considered, "citations": _cite(aware[0], able[0], d)}
        missing = [k for k, v in (("awareness", aware), ("capacity", able), ("risk_and_alternatives", low_risk)) if not v]
        return {"finding": "omission_unresolved", "considered": considered, "citations": _cite(d), "missing": missing}
    return {"finding": "no_moral_weight_established", "considered": considered, "citations": _cite(d)}


def psychological(events, actor="aero", player_context=None):
    """Candidate inner responses for a PC, all status 'proposed' (accept | edit | reject | defer). Only from the player's
    own stated context plus what happened; never a diagnosis. Empty when nothing supports a change."""
    decl = [e for e in events if e["kind"] == "player_declaration" and e.get("actor") == actor]
    ctx = player_context or ((decl[-1].get("details") or {}).get("whisper") if decl else None) or {}
    felt = ctx.get("felt_emotion") if isinstance(ctx.get("felt_emotion"), list) else []
    failed_help = [e for e in events if e["kind"] == "check_resolved" and (e.get("details") or {}).get("success") is False
                   and (e.get("details") or {}).get("act") in HELP_ACTS]
    out = []
    if failed_help and ctx.get("motive"):
        out.append({"candidate": "grief or self-blame may follow; it is Aero's to feel or not", "basis": _cite(*failed_help),
                    "uses_player_context": ["motive"] + (["felt_emotion"] if felt else []), "status": "proposed",
                    "player_choices": ["accept", "edit", "reject", "defer"]})
    return out or [{"candidate": "no_supported_change", "basis": [], "status": "proposed", "player_choices": ["accept", "defer"]}]


def social(events, actor="aero", entities=None):
    """Who could form a view, and from what they actually perceived (no omniscient broadcast)."""
    decl = [e for e in events if e["kind"] == "player_declaration" and e.get("actor") == actor]
    if not decl:
        return []
    witnesses = sorted(set(w for e in events if e["event_id"] >= decl[-1]["event_id"] for w in (e.get("known_to") or []) if w != actor))
    return [{"observer": w, "perceived": [m["source_event"] for m in memories(events, w, entities) if m["source_event"] >= decl[-1]["event_id"]],
             "private_context_visible": False} for w in witnesses]


def appraise(events, actor="aero", entities=None, player_context=None):
    return {"moral": moral(events, actor), "psychological": psychological(events, actor, player_context),
            "social": social(events, actor, entities), "canonical": False}
