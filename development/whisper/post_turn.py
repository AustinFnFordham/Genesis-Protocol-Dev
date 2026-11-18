"""WHISPER post-turn review and the PC's private episodic history (owner decisions 1 and 2, 2026-11-17). Pure.

After a consequential turn, `propose` reads the accepted events of that action, the PC's established private history,
the start-of-turn context and the declared intention, and returns *candidates* with their evidence. The player answers
each with accept / edit / reject / defer, or writes a custom response. Nothing becomes part of the PC's history without
that answer, and a long-term candidate (a lasting change in feeling, conviction or outlook) only appears when the
history already holds repeated, player-confirmed experience of the same theme — and still needs confirmation.

No numbers, weights, meters, diagnoses or alignment. Mechanical conditions (fear, exhaustion, stress) stay with the rules.

Ledger lane: `whisper_review` and `whisper_response` are ordinary ledger events, visibility "player", tag "pc_private"
(seen by the owner only; never by NPCs — evidence.py treats every whisper_* kind as pc_private).
"""
import hashlib
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "campaigns/starwars_litrpg/ui"))
from hp_compat import hp_delta

REVIEW, RESPONSE = "whisper_review", "whisper_response"
CHOICES = ("accept", "edit", "reject", "defer", "custom")
OUTCOME_KINDS = {"attack_resolved", "check_resolved", "save_resolved", "hp_change", "condition_change"}
HELP_ACTS = {"rescue", "help", "heal", "protect"}


def _d(e):
    return e.get("details") or {}


def _cid(review_basis, theme):
    return "wc_" + hashlib.sha256(f"{review_basis}:{theme}".encode()).hexdigest()[:10]


def history(events, pc="aero"):
    """The PC's private episodic history: only player-confirmed responses, each with its sources."""
    out = []
    for e in events:
        if e["kind"] == RESPONSE and _d(e).get("pc") == pc and _d(e).get("choice") in ("accept", "edit", "custom"):
            d = _d(e)
            out.append({"entry_id": e["event_id"], "theme": d.get("theme"), "kind": d.get("candidate_kind", "temporary"),
                        "text": d["text"], "sources": d.get("evidence", []), "review_id": d.get("review_id"),
                        "world_time": e.get("world_time"), "player_confirmed": True})
    return out


def pending(events, pc="aero"):
    """Latest review whose candidates are not all answered (defer keeps a candidate open)."""
    answered = {}
    for e in events:
        if e["kind"] == RESPONSE and _d(e).get("pc") == pc:
            answered.setdefault(_d(e).get("review_id"), {})[_d(e).get("candidate_id")] = _d(e).get("choice")
    for e in reversed(events):
        if e["kind"] == REVIEW and _d(e).get("pc") == pc:
            done = answered.get(e["event_id"], {})
            open_ = [c for c in _d(e)["candidates"] if done.get(c["candidate_id"]) in (None, "defer")]
            closed_by_custom = any(v == "custom" for k, v in done.items() if k is None)
            if open_ and not closed_by_custom:
                return {"review_id": e["event_id"], "action_id": _d(e).get("action_id"), "candidates": open_,
                        "note": _d(e).get("note")}
            return None
    return None


def propose(action_events, prior_events, pc="aero"):
    """Candidates for one committed action. action_events: accepted events of that action (declaration first).
    Returns None when the turn was not consequential for the PC."""
    decl = next((e for e in action_events if e["kind"] == "player_declaration" and e.get("actor") == pc), None)
    if not decl:
        return None
    dd = _d(decl)
    ctx = dd.get("whisper") or {}
    motive = ctx.get("motive") if ctx.get("motive") not in (None, "unspecified") else None
    felt = ctx.get("felt_emotion") if isinstance(ctx.get("felt_emotion"), list) else []
    outcomes = [e for e in action_events if e["kind"] in OUTCOME_KINDS]
    if not outcomes:
        return None
    basis = decl["event_id"]
    cands = []

    def add(theme, kind, proposed, why, ev, uses=()):
        cands.append({"candidate_id": _cid(basis, theme), "theme": theme, "kind": kind, "proposed": proposed,
                      "explanation": why, "evidence": [e["event_id"] for e in ev], "uses_player_context": list(uses)})

    hurt = [e for e in outcomes if e["kind"] == "hp_change" and _d(e).get("target") == pc and hp_delta(_d(e)) < 0]
    if hurt:
        add("pain_and_shock", "temporary", "The hit stays with him for a while: shaken, hurting.",
            "Aero took damage this turn.", hurt)
    failed_help = [e for e in outcomes if e["kind"] == "check_resolved" and _d(e).get("act") in HELP_ACTS and _d(e).get("success") is False]
    if failed_help:
        add("loss_after_trying", "temporary", "Grief, or blaming himself for not reaching them in time.",
            "He tried to help and it failed" + (f"; he did it to {motive}" if motive else "") + ".", failed_help, ["motive"] if motive else [])
    saved = [e for e in outcomes if e["kind"] == "check_resolved" and _d(e).get("act") in HELP_ACTS and _d(e).get("success") is True]
    if saved:
        add("relief_after_protecting", "temporary", "Relief that it worked.", "He tried to help and it worked.", saved)
    harm = [e for e in outcomes if e["kind"] == "attack_resolved" and _d(e).get("justification") == "none_established"]
    if harm:
        add("weight_of_the_strike", "prompt", None,
            "He struck when no justification was established. How does Aero feel about it — if anything? Your words only.", harm)
    if felt and not cands:
        add("stated_feeling_after", "temporary", f"Still {', '.join(felt)} — or not, after how it went.",
            "You said he felt " + ", ".join(felt) + " going in.", outcomes[:1], ["felt_emotion"])
    # Long-term candidates: only from repeated, player-confirmed history on the same theme.
    past = history(prior_events, pc)
    for c in list(cands):
        same = [h for h in past if h["theme"] == c["theme"]]
        if len(same) >= 2:
            add(c["theme"] + "_lasting", "long_term",
                {"loss_after_trying": "A lasting fear of failing the people he tries to save.",
                 "relief_after_protecting": "A growing confidence that he can protect the people with him.",
                 "pain_and_shock": "A lasting wariness of being hurt in a fight."}.get(c["theme"], "This becomes part of who he is."),
                f"You confirmed this kind of experience {len(same)} times before ({', '.join(h['entry_id'] for h in same)}).",
                outcomes[:1])
            cands[-1]["evidence"] = [h["entry_id"] for h in same] + cands[-1]["evidence"]
    if not cands:
        return None
    return {"pc": pc, "action_id": dd.get("action_id"), "basis": basis, "candidates": cands, "canonical": False,
            "note": "Suggestions only. Nothing changes for Aero unless you accept, edit or write your own."}


def response(review_event, candidate_id, choice, text=None, pc="aero"):
    """Validate one player answer; returns the details of the whisper_response event to record."""
    if choice not in CHOICES:
        raise ValueError("choice is accept, edit, reject, defer or custom")
    d = _d(review_event)
    cand = next((c for c in d["candidates"] if c["candidate_id"] == candidate_id), None) if candidate_id else None
    if choice != "custom" and cand is None:
        raise ValueError("unknown candidate for this review")
    text = (text or "").strip()
    if choice in ("edit", "custom") and not text:
        raise ValueError("edit and custom need the player's own words")
    if choice == "accept":
        if cand["kind"] == "prompt" or not cand.get("proposed"):
            raise ValueError("a prompt has no proposal to accept; answer it in your own words (edit or custom)")
        text = cand["proposed"]
    return {"pc": pc, "review_id": review_event["event_id"], "candidate_id": candidate_id, "choice": choice,
            "text": text or None, "theme": cand["theme"] if cand else "custom",
            "candidate_kind": cand["kind"] if cand else "temporary",
            "evidence": cand["evidence"] if cand else [review_event["event_id"]],
            "source": "player_explicit", "visibility": "pc_private"}
