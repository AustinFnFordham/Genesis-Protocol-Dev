#!/usr/bin/env python3
"""Contest planning and append-only adjudication. Never rolls or deletes history."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import batch
import ledger

CATEGORIES = {"intent", "rules", "unfavorable"}


def plan(campaign, request):
    if request.get("category") not in CATEGORIES:
        raise ValueError("invalid contest category")
    events, problems = ledger.validate_all(campaign)
    if problems:
        raise ValueError("invalid ledger")
    by_id = {event["event_id"]: event for event in events}
    declaration = by_id.get(request.get("declaration_event"))
    if not declaration or declaration["kind"] != "player_declaration" or declaration["visibility"] == "gm_only":
        raise ValueError("original public declaration is required")
    if request["category"] == "unfavorable":
        return {"status": "no_correction", "reason": "A valid unfavorable outcome does not authorize rerolling.",
                "declaration": declaration["event_id"], "affected": [], "rolls": []}
    step = request.get("step_id")
    steps = declaration.get("details", {}).get("declaration", {}).get("steps", [])
    if step not in {entry["id"] for entry in steps}:
        raise ValueError("disputed step is not in the original declaration")
    # Restrict initial matches to the original action's region in the event stream.
    after = False
    seeds = set()
    for event in events:
        if event is declaration:
            after = True
            continue
        if after and event["kind"] == "player_declaration":
            break
        if after and event.get("details", {}).get("step_id") == step:
            seeds.add(event["event_id"])
    if not seeds:
        return {"status": "needs_adjudication", "reason": "No committed event maps uniquely to that step. The GM must establish its provenance first.",
                "declaration": declaration["event_id"], "affected": [], "rolls": []}
    closure = set(seeds)
    for event in events:
        if set(event.get("caused_by", [])) & closure:
            closure.add(event["event_id"])
    if declaration["event_id"] in closure or any(by_id[key]["kind"] == "player_declaration" for key in closure):
        raise ValueError("dependency closure includes a later player declaration; requires a broader adjudication")
    first = min(int(key.split("_")[1]) for key in seeds)
    unlinked = [event["event_id"] for event in events
                if int(event["event_id"].split("_")[1]) > first and event["event_id"] not in closure
                and not event.get("caused_by")]
    return {"unlinked_requires_review": unlinked, "status": "awaiting_adjudication", "declaration": declaration["event_id"], "step_id": step,
            "head": events[-1]["event_id"], "revision": len(events),
            "affected": [event["event_id"] for event in events if event["event_id"] in closure],
            "public_affected": [event["event_id"] for event in events if event["event_id"] in closure and event["visibility"] != "gm_only"],
            "rolls": sorted({rid for event in events if event["event_id"] in closure for rid in event.get("roll_ids", [])}),
            "request_hash": hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()}


def accepted_batch(campaign, request, adjudication):
    proposal = plan(campaign, request)
    if proposal["status"] != "awaiting_adjudication":
        raise ValueError(proposal["reason"] if "reason" in proposal else "not ready for adjudication")
    if adjudication.get("request_hash") != proposal["request_hash"] or adjudication.get("head") != proposal["head"]:
        raise ValueError("stale or mismatched adjudication")
    if adjudication.get("decision") != "approve" or not adjudication.get("basis") or not adjudication.get("rule_sources"):
        raise ValueError("an explicit reasoned rules adjudication is required")
    if sorted(adjudication.get("preserve_unlinked", [])) != sorted(proposal["unlinked_requires_review"]):
        raise ValueError("adjudication must review and explicitly preserve events without causal links")
    replacements = adjudication.get("replacements", [])
    if not isinstance(replacements, list) or not replacements:
        raise ValueError("approved correction requires replacement events")
    for event in replacements:
        if event["kind"] in ("player_declaration", "ruling_void", "repair_adjudication"):
            raise ValueError("replacement cannot overwrite declarations or create nested repairs")
        if not set(event.get("roll_ids", [])) <= set(proposal["rolls"]):
            raise ValueError("repair must reuse the affected rolls")
    public_ids = proposal["public_affected"]
    hidden_ids = [key for key in proposal["affected"] if key not in public_ids]
    common = {"session": 1, "turn_no": replacements[0]["turn_no"], "world_time": replacements[0]["world_time"],
              "actor": "gm", "known_to": [], "caused_by": [], "roll_ids": [], "knowledge_type": "fact"}
    corrections = []
    for visibility, ids in (("player", public_ids), ("gm_only", hidden_ids)):
        if ids:
            corrections.append({**common, "kind": "ruling_void", "visibility": visibility,
                                "summary": "An adjudicated correction supersedes the disputed consequences.",
                                "details": {"voids": ids, "declaration": proposal["declaration"]}})
    corrections.append({**common, "kind": "repair_adjudication", "visibility": "gm_only",
                        "summary": adjudication["basis"],
                        "details": {"request_hash": proposal["request_hash"], "category": request["category"],
                                    "rule_sources": adjudication["rule_sources"], "preserved_rolls": proposal["rolls"]}})
    return {"batch_id": "repair-" + proposal["request_hash"], "expected_head": proposal["head"],
            "expected_revision": proposal["revision"], "events": corrections + replacements}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path); parser.add_argument("request", type=Path)
    parser.add_argument("--adjudication", type=Path); parser.add_argument("--lock"); parser.add_argument("--run")
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text())
        if args.adjudication:
            # Deliberately limited to explicit experimental copies in this development increment.
            if not (args.campaign / "experimental_run.json").exists():
                raise ValueError("repair application requires a marked isolated campaign copy")
            accepted = accepted_batch(args.campaign, request, json.loads(args.adjudication.read_text()))
            print(json.dumps(batch.apply(args.campaign, accepted, args.lock, args.run, ledger)))
        else:
            print(json.dumps(plan(args.campaign, request)))
    except (ValueError, OSError) as error:
        parser.exit(3, str(error)+"\n")
