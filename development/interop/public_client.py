#!/usr/bin/env python3
"""Provider-neutral client for read-only authoritative public refresh.
The provider label identifies a client instance; it is not provider certification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "campaigns/starwars_litrpg/ui"))
import export_state


def refresh(campaign_dir, campaign_id, cursor=None):
    state = export_state.build(campaign_dir=campaign_dir, campaign_id=campaign_id)
    if cursor:
        if cursor["campaign_id"] != campaign_id or cursor["revision"] > state["revision"]:
            raise ValueError("wrong campaign or revision moved backwards")
        if cursor["revision"] == state["revision"] and cursor["ledger_head"] != state["ledger_head"]:
            raise ValueError("same revision has a different ledger head")
    documents = export_state.publish_set(state)
    fingerprint = hashlib.sha256(json.dumps(state, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return {"cursor": {"campaign_id": campaign_id, "revision": state["revision"], "ledger_head": state["ledger_head"],
                       "public_sha256": fingerprint},
            "changed": cursor is None or cursor.get("public_sha256") != fingerprint, "public": documents}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign_dir", type=Path); parser.add_argument("campaign_id")
    parser.add_argument("--cursor", type=Path); parser.add_argument("--client", required=True)
    args = parser.parse_args()
    try:
        result = refresh(args.campaign_dir, args.campaign_id, json.loads(args.cursor.read_text()) if args.cursor else None)
        print(json.dumps(dict(result, client=args.client)))
    except (ValueError, OSError) as error:
        parser.exit(3, str(error)+"\n")
