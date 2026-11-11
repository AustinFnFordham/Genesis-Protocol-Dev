#!/usr/bin/env python3
"""Build worker-authored progress patches for the existing action row.
Caller reads row/lease, applies the returned patch with if_version, and stops on conflict.
No database connection or campaign mutation is performed here.
"""
import argparse
import json
from pathlib import Path
import time

STAGES = ("claimed", "context", "rules", "dice", "ledger", "narration", "publishing", "complete")


def patch(row, lock, run, stage, now=None):
    now = time.time_ns() // 1_000_000 if now is None else now
    if type(now) is not int or now < 0:
        raise ValueError("worker timestamp must be a nonnegative integer")
    row, lock = row.get("data", row), lock.get("data", lock)
    if lock.get("holder") != run or lock.get("expires_ms", 0) <= now:
        raise ValueError("progress requires the active worker lease")
    if stage not in STAGES:
        raise ValueError("unknown stage")
    if row.get("status") not in ("submitted", "processing", "resolved", "committed"):
        raise ValueError("this action cannot report worker progress")
    previous = row.get("processing", {})
    if stage == "complete" and row.get("publication", {}).get("status") != "published":
        raise ValueError("complete requires published state")
    same = previous.get("run") == run
    old = previous.get("stage") if same else None
    if same:
        heartbeat = previous.get("heartbeat_ms")
        if type(heartbeat) is not int or now < heartbeat:
            raise ValueError("worker clock moved backwards; keep the newer progress row")
    if old and STAGES.index(stage) < STAGES.index(old):
        raise ValueError("stage cannot move backwards within a worker run")
    stages = dict(previous.get("stages", {})) if same else {}
    stages.setdefault(stage, now)
    if any(type(value) is not int or value > now for value in stages.values()):
        raise ValueError("invalid worker phase timestamps")
    return {"processing": {"run": run, "started_ms": previous.get("started_ms", now) if same else now,
                           "heartbeat_ms": now, "lease_ms": max(0, lock["expires_ms"]-now),
                           "stage": stage, "stage_started_ms": stages[stage], "stages": stages}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("row", type=Path); parser.add_argument("lock", type=Path)
    parser.add_argument("run"); parser.add_argument("stage", choices=STAGES); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = patch(json.loads(args.row.read_text()), json.loads(args.lock.read_text()), args.run, args.stage)
        args.out.write_text(json.dumps(result))
    except (ValueError, OSError) as error:
        parser.exit(3, str(error)+"\n")
