#!/usr/bin/env python3
"""Ordered, recoverable ledger batches. Local lock plus existing worker lease.
A durable pending journal gates all ledger readers until both streams are complete.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import time
import threading

_held = threading.local()

def acquire(handle, exclusive, blocking):
    if os.name == "nt":
        import msvcrt
        if exclusive and os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        mode = (msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK) if exclusive else msvcrt.LK_RLCK
        msvcrt.locking(handle.fileno(), mode, 1)
    else:
        import fcntl
        fcntl.flock(handle, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | (0 if blocking else fcntl.LOCK_NB))


def release(handle):
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_UN)


@contextmanager
def writer_lock(campaign):
    directory = campaign / "hidden"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".ledger_writer.lock").open("a+b") as handle:
        try:
            acquire(handle, exclusive=True, blocking=False)
        except (BlockingIOError, OSError):
            raise ValueError("another ledger writer holds the local lock")
        owners = getattr(_held, "campaigns", set())
        _held.campaigns = owners | {str(campaign.resolve())}
        try:
            yield
        finally:
            _held.campaigns = owners
            release(handle)


@contextmanager
def reader_lock(campaign):
    key = str(campaign.resolve())
    if key in getattr(_held, "campaigns", set()) or key in getattr(_held, "readers", set()):
        yield
        return
    path = campaign / "hidden/.ledger_writer.lock"
    if not path.exists():
        yield
        if path.exists():
            raise ValueError("ledger writer appeared while reading; retry the read")
        return
    with path.open("r+b" if os.name == "nt" else "rb") as handle:
        acquire(handle, exclusive=False, blocking=True)
        readers = getattr(_held, "readers", set())
        _held.readers = readers | {key}
        try:
            yield
        finally:
            _held.readers = readers
            release(handle)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def durable_json(path, data):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as handle:
        json.dump(data, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    sync_directory(path.parent)


def sync_directory(directory):
    if os.name == "nt":
        return  # Windows has no portable directory fsync; file data is still flushed.
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def lease_valid(lock, run):
    value = json.loads(Path(lock).read_text())
    value = value.get("data", value)
    if value.get("holder") != run or value.get("expires_ms", 0) <= time.time_ns() // 1_000_000:
        raise ValueError("worker lease is missing, expired or belongs to another worker")


def apply(campaign, request, lock, run, ledger, after_stream=None):
    """Append one prevalidated batch; retries finish the exact accepted bytes."""
    if not isinstance(request, dict) or type(request.get("expected_revision")) is not int:
        raise ValueError("batch request requires an integer expected_revision")
    lease_valid(lock, run)
    batch_id = request.get("batch_id", "")
    if not isinstance(batch_id, str) or not batch_id or len(batch_id) > 100:
        raise ValueError("batch_id is required")
    fingerprint = digest(json.dumps(request, sort_keys=True).encode())
    key = digest(batch_id.encode())
    pending = campaign / "hidden/ledger_batch_pending.json"
    receipts = campaign / "hidden/ledger_batch_receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    receipt = receipts / (key + ".json")
    with writer_lock(campaign):
        if receipt.exists() and not pending.exists():
            done = json.loads(receipt.read_text())
            if done["fingerprint"] != fingerprint:
                raise ValueError("batch ID already accepted with a different payload")
            return done["result"]
        if pending.exists():
            plan = json.loads(pending.read_text())
            if plan["fingerprint"] != fingerprint or plan["batch_id"] != batch_id:
                raise ValueError("another accepted batch needs recovery first")
        else:
            events, problems = ledger.validate_all(campaign)
            if problems:
                raise ValueError("ledger must validate before accepting a batch")
            head = events[-1]["event_id"] if events else None
            if request.get("expected_head") != head or request.get("expected_revision") != len(events):
                raise ValueError("stale ledger revision or head")
            drafts = request.get("events")
            if not isinstance(drafts, list) or not 1 <= len(drafts) <= 100:
                raise ValueError("a batch requires 1 to 100 ordered events")
            by_id = {event["event_id"]: event for event in events}
            idempotencies = {event.get("idempotency_key") for event in events}
            rolls = {row["roll_id"] for row in ledger.read_jsonl(campaign / "records/roll_log.jsonl")}
            accepted = []
            seq = int(head.split("_")[1]) if head else 0
            for index, draft in enumerate(drafts, 1):
                if not isinstance(draft, dict):
                    raise ValueError("batch event must be an object")
                if any(not isinstance(draft.get(key, []), list) or
                       any(not isinstance(value, str) for value in draft.get(key, []))
                       for key in ("caused_by", "roll_ids")):
                    raise ValueError("batch causal and roll references must be lists of strings")
                event = dict(draft)
                event["event_id"] = f"evt_{seq + index:04d}"
                event["idempotency_key"] = f"batch:{batch_id}:{index}"
                # '$1' refers to the first event in this ordered batch.
                event["caused_by"] = [accepted[int(ref[1:])-1]["event_id"] if isinstance(ref, str) and ref.startswith("$")
                                      and ref[1:].isdigit() and 1 <= int(ref[1:]) <= len(accepted) else ref
                                      for ref in event.get("caused_by", [])]
                if event["idempotency_key"] in idempotencies:
                    raise ValueError("batch provenance already exists without a receipt")
                problems = ledger.validate_event(event, by_id, rolls)
                if problems:
                    raise ValueError("invalid batch event: " + "; ".join(problems))
                by_id[event["event_id"]] = event
                accepted.append(event)
            streams = {}
            for visibility, relative in ((False, "records/events.jsonl"), (True, "hidden/events.jsonl")):
                path = campaign / relative
                before = path.read_bytes() if path.exists() else b""
                if before and not before.endswith(b"\n"):
                    raise ValueError("ledger stream has an incomplete trailing line")
                tail = "".join(json.dumps(e) + "\n" for e in accepted if (e["visibility"] == "gm_only") == visibility)
                streams[relative] = {"size": len(before), "hash": digest(before), "tail": tail}
            plan = {"batch_id": batch_id, "fingerprint": fingerprint, "streams": streams,
                    "result": {"status": "committed", "batch_id": batch_id,
                               "events": [event["event_id"] for event in accepted],
                               "head": accepted[-1]["event_id"], "revision": len(events)+len(accepted)}}
            lease_valid(lock, run)
            durable_json(pending, plan)
        lease_valid(lock, run)
        # Prove both files are exact prefixes before resuming either stream.
        for relative, stream in plan["streams"].items():
            path = campaign / relative
            current = path.read_bytes() if path.exists() else b""
            prefix, suffix = current[:stream["size"]], current[stream["size"]:]
            if len(prefix) != stream["size"] or digest(prefix) != stream["hash"] or not stream["tail"].encode().startswith(suffix):
                raise ValueError("ledger differs from the accepted batch; manual investigation required")
        for relative, stream in plan["streams"].items():
            lease_valid(lock, run)
            path = campaign / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            size = path.stat().st_size if path.exists() else 0
            remaining = stream["tail"].encode()[size-stream["size"]:]
            with path.open("ab") as handle:
                handle.write(remaining)
                handle.flush()
                os.fsync(handle.fileno())
            sync_directory(path.parent)
            if after_stream:
                after_stream(relative)
        lease_valid(lock, run)
        durable_json(receipt, {"fingerprint": fingerprint, "result": plan["result"]})
        pending.unlink()
        sync_directory(pending.parent)
        return plan["result"]
