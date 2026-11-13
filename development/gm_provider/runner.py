"""Drive one claimed action to a stop with one provider. Shared by every model-backed provider.

Outcomes (the `outcome` field):
  committed        resolved, committed, published
  needs_revision   sent back to the player before any die
  resolved_unpublished  committed; publication is pending and safe to repeat
  blocked          the routed provider cannot run; the action waits for it or for an explicit reroute
  released         the provider kept failing validation; accepted tables/rolls are kept, the lease is returned
  nothing / busy / not_routed   nothing was claimed
The runner never tries a second provider.
"""
import secrets

from gateway import Refused
from providers import BadMove, Unavailable

RECOVERABLE = {"PROPOSAL_REJECTED", "NPC_EVALUATION", "BAD_TABLES", "BAD_ROLL", "PURPOSE_LEAK", "NOT_DECLARED", "TABLES_FIRST",
               "BAD_REVIEW", "BAD_ALTERNATIVE", "TOO_LATE_FOR_REVIEW", "TABLES_FIXED", "BAD_PROPOSAL", "ROLL_KEY_REUSED"}


def run_turn(gateway, provider, run=None, max_moves=16, max_rejections=3, interrupt=None):
    run = run or f"run-{provider.id}-{secrets.token_hex(6)}"
    capability = provider.capabilities()
    item = gateway._in_flight()
    if not item:
        return {"outcome": "nothing", "run": run}
    action_id = item[2]["action_id"]
    routed = item[2].get("gm", {}).get("provider")
    if item[2]["status"] != "resolved" and routed != provider.id:
        return {"outcome": "not_routed", "run": run, "action_id": action_id, "routed_to": routed}
    if item[2]["status"] != "resolved" and not capability["available"]:
        gateway.block(action_id, provider.id, "PROVIDER_UNAVAILABLE", capability["reason"])
        return {"outcome": "blocked", "run": run, "action_id": action_id, "reason": capability["reason"]}
    try:
        claim = gateway.claim(provider.id, run, {"kind": capability.get("kind"), "model": capability.get("model"),
                                                "mock": capability.get("mock"), "session": None})
    except Refused as refusal:
        return {"outcome": {"PROVIDER_BUSY": "busy", "NOTHING_TO_DO": "nothing", "NOT_ROUTED_HERE": "not_routed"}.get(refusal.code, "refused"),
                "run": run, "action_id": action_id, **refusal.as_dict()}
    moves, rejections, feedback = [], 0, None
    try:
        if claim["phase"] == "publish":
            status = gateway.publish(provider.id, run)
            return {"outcome": "committed", "run": run, "action_id": action_id, "moves": ["publish"], "status": status, "authored": False}
        for _ in range(max_moves):
            context = gateway.context(provider.id, run)
            if feedback:
                context["feedback"] = feedback
            try:
                move = provider.step(context)
                kind = move.get("type") if isinstance(move, dict) else None
                if interrupt:
                    interrupt(kind, move)
                if kind == "review":
                    status = gateway.review(provider.id, run, move.get("review"))
                    return {"outcome": "needs_revision", "run": run, "action_id": action_id, "moves": moves + ["review"], "status": status}
                if kind == "tables":
                    gateway.fix_tables(provider.id, run, move.get("tables"))
                elif kind == "rolls":
                    if not isinstance(move.get("rolls"), list) or not move["rolls"]:
                        raise BadMove("a rolls move lists at least one request")
                    for request in move["rolls"]:
                        gateway.roll(provider.id, run, request)
                elif kind == "commit":
                    status = gateway.commit(provider.id, run, move.get("proposal"))
                    return {"outcome": "committed", "run": run, "action_id": action_id, "moves": moves + ["commit"], "status": status, "authored": True}
                else:
                    raise BadMove("a move needs type review, tables, rolls or commit")
                moves.append(kind)
                feedback = None
            except BadMove as error:
                rejections += 1
                feedback = {"rejected": str(error)}
            except Refused as refusal:
                if refusal.code == "PUBLICATION_PENDING":
                    return {"outcome": "resolved_unpublished", "run": run, "action_id": action_id, "moves": moves + ["commit"], **refusal.as_dict()}
                if refusal.code not in RECOVERABLE:
                    raise
                rejections += 1
                feedback = {"rejected": refusal.as_dict()["error"]}
            if rejections > max_rejections:
                gateway.release(provider.id, run, "provider kept failing validation")
                return {"outcome": "released", "run": run, "action_id": action_id, "moves": moves, "last_rejection": feedback}
        gateway.release(provider.id, run, "move limit reached")
        return {"outcome": "released", "run": run, "action_id": action_id, "moves": moves}
    except Unavailable as error:
        gateway.release(provider.id, run, "provider unavailable mid-turn")
        return {"outcome": "blocked", "run": run, "action_id": action_id, "moves": moves, "reason": str(error)[:300]}
    except Refused as refusal:
        return {"outcome": "refused", "run": run, "action_id": action_id, "moves": moves, **refusal.as_dict()}
