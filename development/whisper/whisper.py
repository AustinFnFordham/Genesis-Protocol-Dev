"""WHISPER — pure, noncanonical evaluators (TB4-WHISPER-001 §3). No ledger writes, no model calls, no numbers invented.

M3: the start-of-turn context boundary. A player-explicit context (`declaration.whisper`, schema genesis-whisper-context/1)
is PC-private. Observers learn only what Aero lets show (`expression`), and only through a perception channel the GM
has established; felt emotion, motive and reflection never reach an observer, an NPC prompt or a public event.
"""
SCHEMA = "genesis-whisper-context/1"
STYLES = ("open", "controlled", "masked")
PRIVATE = ("felt_emotion", "motive", "reflection")


def validate(ctx):
    """Return a list of problems (empty when valid). Unspecified is a value, never a default feeling."""
    if ctx is None:
        return []
    errors = []
    if ctx.get("schema") != SCHEMA:
        errors.append("schema")
    if ctx.get("source") != "player_explicit":
        errors.append("source must be player_explicit (only the player authors a PC's inner state)")
    if ctx.get("visibility") != "pc_private":
        errors.append("visibility must be pc_private")
    felt = ctx.get("felt_emotion")
    if not (felt == "unspecified" or (isinstance(felt, list) and felt and all(isinstance(f, str) and f.strip() for f in felt))):
        errors.append("felt_emotion is 'unspecified' or a non-empty list of the player's words")
    exp = ctx.get("expression")
    if not (exp == "unspecified" or (isinstance(exp, dict) and exp.get("style") in STYLES)):
        errors.append("expression is 'unspecified' or {style: open|controlled|masked, text}")
    return errors


def observer_view(ctx, perceives=True):
    """What an observer can know from the context itself: only the outward expression, and only if they perceive Aero.
    A masked expression shows only its stated surface text. Never felt emotion, motive or reflection."""
    if not ctx or not perceives:
        return {}
    exp = ctx.get("expression")
    if not isinstance(exp, dict):
        return {}
    shown = {"style": exp["style"]}
    if exp.get("text"):
        shown["text"] = exp["text"]
    if exp["style"] == "open" and isinstance(ctx.get("felt_emotion"), list):
        shown["visible_emotion"] = list(ctx["felt_emotion"])   # shown openly by the player's own choice
    return {"expression": shown}


def public_declaration(decl):
    """The declaration as it may appear in a public event: the WHISPER block is removed (kept GM-side only)."""
    out = dict(decl or {})
    out.pop("whisper", None)
    return out


def interpretations(ctx):
    """What the system may conclude from the context alone: nothing about morality, diagnosis or alignment."""
    return {"moral_change": None, "diagnosis": None, "alignment_delta": None,
            "felt": ctx.get("felt_emotion") if ctx else "unspecified"}
