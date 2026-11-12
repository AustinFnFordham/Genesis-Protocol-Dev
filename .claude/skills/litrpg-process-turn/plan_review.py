#!/usr/bin/env python3
"""Optional pre-roll plan approval, bound to the exact declaration and scene."""
import hashlib
import json
import secrets
import time


def fingerprint(declaration):
    return hashlib.sha256(json.dumps(declaration, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def create(action, validation, action_id):
    if not action.get("request_plan_review") or not validation.get("legal"):
        raise ValueError("a legal, explicitly requested plan review is required")
    return {"status": "needs_plan_approval", "review_plan": {
        "review_id": secrets.token_hex(16), "action_id": action_id,
        "declaration_hash": fingerprint(action["declaration"]),
        "based_on_revision": action["based_on_revision"], "ledger_head": action["ledger_head"],
        "summary": [entry["text"] for entry in validation.get("preview", [])],
        "created_ms": time.time_ns() // 1_000_000}}


def approved(action, approval, action_id):
    review = action.get("review_plan", {})
    return (action.get("status") == "needs_plan_approval" and
            approval.get("decision") == "approved" and approval.get("action_id") == action_id and
            approval.get("campaign_id") == action.get("campaign_id") and
            approval.get("review_id") == review.get("review_id") and bool(review.get("review_id")) and
            approval.get("based_on_revision") == review.get("based_on_revision") == action.get("based_on_revision") and
            approval.get("ledger_head") == review.get("ledger_head") == action.get("ledger_head") and
            review.get("declaration_hash") == fingerprint(action["declaration"]))


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["create", "verify"])
    parser.add_argument("action", type=Path)
    parser.add_argument("input", type=Path, help="validated preflight output, or player approval")
    parser.add_argument("action_id")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    action = json.loads(args.action.read_text())
    action = action.get("data", action)
    value = json.loads(args.input.read_text())
    value = value.get("data", value)
    try:
        if args.mode == "create":
            result = create(action, value.get("validation", value), args.action_id)
        else:
            result = {"approved": approved(action, value, args.action_id)}
        if args.out:
            args.out.write_text(json.dumps(result))
        else:
            print(json.dumps(result))
        if args.mode == "verify" and not result["approved"]:
            parser.exit(3)
    except ValueError as error:
        parser.exit(3, str(error)+"\n")
