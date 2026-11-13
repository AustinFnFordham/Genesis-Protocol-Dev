"""Durable legacy dice writes under the existing campaign writer lock.

The journal is private: it includes the cursor, exact accepted output and DCs.
A retry finishes accepted bytes before any call to the deterministic roller.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'litrpg-ledger'))
import batch


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def execute(campaign, request, generate, after_write=None):
    pending = campaign / 'hidden/legacy_dice_pending.json'
    request_hash = fingerprint(request)
    request_id = request['request_id']
    if request_id is not None and (not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 200):
        raise ValueError('request ID must contain 1 to 200 characters')

    def checkpoint(point):
        if after_write:
            after_write(point)

    with batch.writer_lock(campaign):
        batch.sync_directory(campaign)  # persist a newly created hidden directory
        for other in ('experimental_dice_pending.json', 'ledger_batch_pending.json'):
            if (campaign / 'hidden' / other).exists():
                raise ValueError('recover the accepted dice/ledger transaction before rolling or advancing')
        receipt = (campaign / 'hidden/legacy_dice_receipts' / (fingerprint(request_id)+'.json')) if request_id is not None else None
        if pending.exists():
            plan = json.loads(pending.read_text(encoding='utf-8'))
            if plan['fingerprint'] != request_hash:
                raise ValueError('another legacy dice request needs recovery with its exact original arguments')
        elif receipt is not None and receipt.exists():
            done = json.loads(receipt.read_text(encoding='utf-8'))
            if done['fingerprint'] != request_hash:
                raise ValueError('request ID already accepted with different arguments')
            return done['result']
        else:
            plan = generate()
            plan['fingerprint'] = request_hash
            batch.durable_json(pending, plan)
            checkpoint('accepted')

        # Validate every stream and the cursor before writing ANY recovery bytes.
        for relative, stream in plan['streams'].items():
            path = campaign / relative
            current = path.read_bytes() if path.exists() else b''
            prefix, suffix = current[:stream['size']], current[stream['size']:]
            if (len(prefix) != stream['size'] or batch.digest(prefix) != stream['hash'] or
                    not stream['tail'].encode().startswith(suffix)):
                raise ValueError('dice log differs from the accepted plan; manual reconciliation required')
        state_path = campaign / 'hidden/dice_state.json'
        current = state_path.read_bytes().decode() if state_path.exists() else None
        if current not in (plan['state']['before'], plan['state']['after']):
            raise ValueError('dice cursor differs from the accepted plan; manual reconciliation required')
        for relative, stream in plan['streams'].items():
            path = campaign / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            batch.sync_directory(campaign)
            offset = path.stat().st_size-stream['size'] if path.exists() else 0
            with path.open('ab') as handle:
                handle.write(stream['tail'].encode()[offset:])
                handle.flush()
                os.fsync(handle.fileno())
            batch.sync_directory(path.parent)
            checkpoint('append:'+relative)
        temporary = state_path.with_suffix('.legacy.tmp')
        with temporary.open('wb') as handle:
            handle.write(plan['state']['after'].encode())
            handle.flush()
            os.fsync(handle.fileno())
        checkpoint('state:temporary')
        os.replace(temporary, state_path)
        batch.sync_directory(state_path.parent)
        checkpoint('state:replaced')
        if receipt is not None:
            receipt.parent.mkdir(exist_ok=True)
            batch.sync_directory(receipt.parent.parent)
            batch.durable_json(receipt, {'fingerprint':request_hash, 'result':plan['result']})
        checkpoint('receipt')
        pending.unlink()
        batch.sync_directory(pending.parent)
        checkpoint('complete')
        return plan['result']
