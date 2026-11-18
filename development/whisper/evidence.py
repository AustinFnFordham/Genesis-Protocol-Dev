"""Algorithm A — evidence-grounded knowledge (TB4-WHISPER-001 §4.A). Pure and read-only.

Typed envelopes are *derived views* over accepted ledger events; they are never a second source of truth and never
written anywhere. Every envelope cites its accepted event. Visibility is enforced before anything else, so a GM-only
or PC-private record cannot reach a player suggestion, an NPC prompt or a ranking step.

Types: fact, claim, speech, observation, belief, inference, intention, attempt, outcome.
Mapping from the ledger (knowledge_type ∈ {fact, report, belief}):
  report  -> claim (with its speech)     belief -> belief      fact -> by kind (observation, attempt, outcome, fact)
  whisper_context -> intention (pc_private: only the GM and the player)
"""
ATTEMPT_KINDS = {"player_declaration"}
OUTCOME_KINDS = {"attack_resolved", "check_resolved", "hp_change", "condition_change", "save_resolved"}
TYPES = ("fact", "claim", "speech", "observation", "belief", "inference", "intention", "attempt", "outcome")


class Ghost(ValueError):
    pass


def envelopes(events, entities=None):
    """Derive envelopes from accepted events. entities: optional registry of valid ids (unknown ids -> Ghost)."""
    out, known = [], set(entities) if entities is not None else None
    for e in events:
        d = e.get("details") or {}
        if known is not None:
            for k in ("subject", "speaker", "observer"):
                if d.get(k) and d[k] not in known:
                    raise Ghost(f"{e['event_id']}: {k} {d[k]!r} is not a registered entity")
        base = {"source_event": e["event_id"], "world_time": e.get("world_time"), "actor": e.get("actor"),
                "visibility": e.get("visibility", "player"), "known_to": list(e.get("known_to") or []),
                "content": {k: d[k] for k in ("subject", "predicate", "object") if k in d}, "summary": e.get("summary")}
        kt, kind = e.get("knowledge_type"), e.get("kind")
        if kind in ("whisper_review", "whisper_response"):   # the PC's private review lane: player only, never NPCs
            out.append(dict(base, id=e["event_id"] + ":intention", type="intention", visibility="pc_private",
                            provenance="player_explicit" if kind == "whisper_response" else "whisper_candidate", content={}))
        elif kind == "whisper_context":
            out.append(dict(base, id=e["event_id"] + ":intention", type="intention", visibility="pc_private",
                            provenance="player_explicit", content={"context": d.get("context")}))
        elif kt == "report":
            out.append(dict(base, id=e["event_id"] + ":speech", type="speech", provenance=d.get("channel", "heard")))
            if d.get("retracts"):
                out.append(dict(base, id=e["event_id"] + ":retraction", type="claim", provenance="retraction", retracts=d["retracts"]))
            elif base["content"]:
                out.append(dict(base, id=e["event_id"] + ":claim", type="claim", provenance="speaker:" + str(d.get("speaker") or e.get("actor"))))
        elif kt == "belief":
            out.append(dict(base, id=e["event_id"] + ":belief", type="belief", provenance="actor"))
        elif kind == "observation":
            out.append(dict(base, id=e["event_id"] + ":observation", type="observation", provenance="perceived"))
        elif kind in ATTEMPT_KINDS:
            out.append(dict(base, id=e["event_id"] + ":attempt", type="attempt", provenance="declared"))
        elif kind in OUTCOME_KINDS:
            out.append(dict(base, id=e["event_id"] + ":outcome", type="outcome", provenance="resolved"))
        else:
            out.append(dict(base, id=e["event_id"] + ":fact", type="fact", provenance="accepted_event"))
    return out


def visible_to(env, viewer):
    """viewer: 'gm' | 'player' | ('npc', id) | ('pc', id). Enforced before any retrieval or ranking."""
    v = env["visibility"]
    if viewer == "gm":
        return True
    if v == "gm_only":   # hidden from the player; an NPC who was part of it still knows it (GM-side prompts only)
        return isinstance(viewer, tuple) and viewer[0] == "npc" and viewer[1] in env["known_to"]
    if v == "pc_private":
        return viewer == "player" or viewer == ("pc", env.get("actor"))
    if viewer in ("player",) or (isinstance(viewer, tuple) and viewer[0] == "pc"):
        return v in ("player", "party")
    if isinstance(viewer, tuple) and viewer[0] == "npc":
        return viewer[1] in env["known_to"] or viewer[1] == env.get("actor")
    return False


def retrieve(envs, viewer, subject=None, types=None):
    """Visibility first, then filters; retracted claims are returned with retracted=True, never silently dropped."""
    allowed = [x for x in envs if visible_to(x, viewer)]
    retracted = {x["retracts"] for x in allowed if x.get("retracts")}
    out = []
    for x in allowed:
        if types and x["type"] not in types:
            continue
        if subject and x["content"].get("subject") != subject and x["content"].get("object") != subject:
            continue
        y = dict(x)
        if y["type"] == "claim" and y["source_event"] in retracted:
            y["retracted"] = True
        out.append(y)
    return sorted(out, key=lambda x: (x["source_event"], x["id"]))


def world_truth(envs):
    """Objective accepted facts only. A claim never becomes a fact, however many people heard it."""
    return [x for x in envs if x["type"] in ("fact", "observation", "outcome")]


def knows(envs, actor):
    """What an NPC may draw on: only envelopes it witnessed or authored, typed as they are (claims stay claims)."""
    return retrieve(envs, ("npc", actor))


if __name__ == "__main__":   # diagnostic: python3 evidence.py fixtures/cmp001_ten_missing_crates.json player|gm|npc:<id>
    import json, sys
    from pathlib import Path
    src = Path(sys.argv[1])
    if src.is_dir():   # a campaign run directory: read its whole ledger (GM-side tool)
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude/skills/litrpg-ledger"))
        import ledger
        fx = {"events": ledger.load_all(src)}
    else:
        fx = json.loads(src.read_text())
    who = sys.argv[2] if len(sys.argv) > 2 else "player"
    viewer = ("npc", who[4:]) if who.startswith("npc:") else who
    for x in retrieve(envelopes(fx["events"], fx.get("entities")), viewer):
        if isinstance(viewer, tuple) and x["type"] == "intention":
            continue
        print(f"{x['source_event']}  {x['type']:<11} {'(retracted) ' if x.get('retracted') else ''}{x['summary']}")
