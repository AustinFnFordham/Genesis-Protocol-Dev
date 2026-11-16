#!/usr/bin/env python3
"""Bridge between the test Datapad's Artifact database and the gateway for the noncanonical mobile test.

The Artifact database is only a mailbox and a mirror. The queue, the lease, the dice, the encounter record and the
ledger are the gateway's (development/gm_provider/gateway.py), in the staging branch's git history. This file adds no
rules: it reshapes documents in both directions. The worker session moves them with the ArtifactData tool.

  bridge.py env                          the environment: campaign id, artifact URL, worker task, code commit, revision
  bridge.py submit ROW.json [--id ID]    queue the player's action row (as read from the Artifact database) in the gateway
  bridge.py row ACTION_ID                the patch to write back onto the Artifact action row (status, review, stage...)
  bridge.py mirror --out DIR             write DIR/<doc_id>.json for every published view document, state last in the list
  bridge.py pending                      in-flight action and recovery state, for a run that finds no submitted row

Exit 0 done; 3 refused (the JSON says why and carries the row patch to write back); 2 usage.
"""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "development/gm_provider"))
import staging                      # noqa: E402
from gateway import Refused         # noqa: E402

SCOPE = ROOT / "staging/mobile-test-1"
PROVIDER = "claude-session"
STATE_BUDGET = 250_000              # Artifact database document limit is 262,144 bytes


def environment():
    return json.loads((SCOPE / "environment.json").read_text())


def gateway():
    return staging.open_shared(SCOPE)


def row_patch(gw, action_id):
    status = gw.action_status(action_id)
    _, row = gw.store.read("actions/" + action_id)
    patch = {"status": status["status"], "gateway": {"provider": status.get("provider"), "mechanical": status.get("mechanical")}}
    for key in ("review", "error", "publication", "published_revision"):
        if status.get(key) is not None:
            patch[key] = status[key]
    processing = (row or {}).get("processing") or {}
    if processing:
        patch["processing"] = {k: processing.get(k) for k in ("stage", "started_ms", "run", "heartbeat_ms", "stages") if processing.get(k) is not None}
    if row and row.get("ledger_events"):
        patch["ledger_events"] = row["ledger_events"]
        patch["event_id"] = row["ledger_events"][0]
    return patch


def cmd_env(a):
    env = environment()
    gw = gateway()
    public = gw.public_state()
    print(json.dumps({"campaign_id": env["campaign_id"], "canonical": env["canonical"], "artifact_url": env.get("artifact_url"),
                      "worker": env.get("worker"), "code_commit": env.get("code_commit"), "provider": PROVIDER,
                      "cursor": public["cursor"], "in_flight": public["in_flight"]}, indent=1))


def cmd_submit(a):
    env = environment()
    raw = json.loads(Path(a.row).read_text())
    row = raw.get("data", raw)
    action_id = a.id or raw.get("id") or row.get("action_id")
    if row.get("campaign_id") != env["campaign_id"]:
        print(json.dumps({"refused": "WRONG_CAMPAIGN", "patch": {"status": "failed", "error": "this action belongs to another campaign; the test worker handles only " + env["campaign_id"]}}))
        return 3
    action = {"action_id": action_id, "campaign_id": env["campaign_id"], "actor": row.get("actor"), "text": row.get("text", ""),
              "declaration": row.get("declaration"), "contract": row.get("contract"), "source": row.get("source", "composer"),
              "based_on_revision": row.get("based_on_revision"), "ledger_head": row.get("ledger_head"), "context_id": row.get("context_id"),
              "confirmed_warnings": bool(row.get("confirmed_warnings")), "gm_provider": PROVIDER}
    if row.get("resolution_settings"):
        action["resolution_settings"] = row["resolution_settings"]
    gw = gateway()
    try:
        status = gw.submit(action)
    except Refused as refusal:
        message = {"STALE": "The scene moved on after this was written. Look at the latest scene and submit again. No dice were rolled.",
                   "TURN_IN_FLIGHT": "Another turn is still being resolved. Wait for it, then submit again."}.get(refusal.code, refusal.message)
        patch = {"status": "needs_revision" if refusal.code in ("STALE", "TURN_IN_FLIGHT", "NOT_ACTIVE_ACTOR", "UNSUPPORTED_SETTINGS", "BAD_SETTINGS") else "failed",
                 "review": {"summary": message, "errors": [{"code": refusal.code, "message": refusal.message}], "warnings": [], "alternatives": []}, "error": refusal.code}
        print(json.dumps({"refused": refusal.code, "message": refusal.message, "patch": patch}, indent=1))
        return 3
    print(json.dumps({"queued": status, "gm_alternative": row.get("gm_alternative"), "patch": row_patch(gw, action_id)}, indent=1))
    return 0


def cmd_row(a):
    print(json.dumps({"action_id": a.action_id, "patch": row_patch(gateway(), a.action_id)}, indent=1))


def cmd_pending(a):
    print(json.dumps(gateway().recovery(), indent=1))


def cmd_mirror(a):
    env = environment()
    gw = gateway()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    names = [k[len("view/"):] for k in gw.store.keys("view/")]
    documents = []
    for name in sorted(n for n in names if n != "state") + ["state"]:
        _, data = gw.store.read("view/" + name)
        if name == "state":
            # Presentation wiring only: how the page starts its own isolated worker, and the test label. No game state.
            data = dict(data, artifact_url=env.get("artifact_url"),
                        processor={"server": env["worker"]["server"], "trigger_id": env["worker"]["trigger_id"]} if env.get("worker") else None,
                        test_build={"canonical": False, "code_commit": env.get("code_commit"),
                                    "note": "Wick is GM-run, each creature has its own turn, enemies share one initiative count. Test settings only; nothing here changes Hask Meadow."})
        text = json.dumps(data, ensure_ascii=False)
        size = len(text.encode("utf-8"))
        if size > STATE_BUDGET:
            print(json.dumps({"refused": "TOO_LARGE", "doc_id": name, "bytes": size}))
            return 3
        (out / f"{name}.json").write_text(text, encoding="utf-8")
        documents.append({"doc_id": name, "file": str(out / f"{name}.json"), "bytes": size})
    _, state = gw.store.read("view/state")
    print(json.dumps({"collection": "view", "write_in_this_order": documents, "revision": state["revision"], "ledger_head": state["ledger_head"],
                      "note": "write every page first and state last; never write state if a page write failed"}, indent=1))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("env")
    sub.add_parser("pending")
    s = sub.add_parser("submit"); s.add_argument("row"); s.add_argument("--id")
    s = sub.add_parser("row"); s.add_argument("action_id")
    s = sub.add_parser("mirror"); s.add_argument("--out", required=True)
    a = parser.parse_args()
    try:
        return {"env": cmd_env, "submit": cmd_submit, "row": cmd_row, "pending": cmd_pending, "mirror": cmd_mirror}[a.command](a) or 0
    except Refused as refusal:
        print(json.dumps(refusal.as_dict(), indent=1))
        return 3


if __name__ == "__main__":
    sys.exit(main())
