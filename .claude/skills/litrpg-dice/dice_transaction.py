"""Durable legacy CLI transactions. Private plans retain exact bytes, never reroll.

Stable request IDs make completion/response-loss retries unambiguous. Unkeyed
legacy calls remain distinct operations and require explicit pending recovery.
"""
import json
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'litrpg-ledger'))
import batch

PENDING = 'hidden/dice_cli_pending.json'
LOGS = ('records/roll_log.jsonl', 'hidden/roll_dcs.jsonl')


def fingerprint(request):
    return batch.digest(json.dumps(request, sort_keys=True, separators=(',', ':')).encode())


def validate_cursor(campaign, state, parse):
    """Refuse old unjournaled interrupted writes; never guess a repair."""
    rows = {}
    for relative in LOGS:
        path = campaign / relative
        raw = path.read_bytes() if path.exists() else b''
        if raw and not raw.endswith(b'\n'):
            raise ValueError('incomplete prior dice log; manual reconciliation required')
        rows[relative] = [json.loads(line) for line in raw.splitlines() if line.strip()]
    public = rows[LOGS[0]]
    counts = [int(row['roll_id'].rsplit('_', 1)[1]) for row in public]
    if counts != list(range(1, state['roll_count'] + 1)) or any(
            row['roll_id'] != f"roll_t{row['turn_no']}_{i}" or row['turn_no'] > state['turn_no']
            for i, row in enumerate(public, 1)):
        raise ValueError('legacy dice log/cursor mismatch; manual reconciliation required')
    draws = sum(sum(t[2] for t in parse(row['formula']) if t[0] == 'dice') *
                (2 if row['mode'] != 'normal' else 1) for row in public if row['turn_no'] == state['turn_no'])
    ids = {row['roll_id'] for row in public}
    dc_ids = [row['roll_id'] for row in rows[LOGS[1]]]
    if draws != state['draws_used'] or len(set(dc_ids)) != len(dc_ids) or not set(dc_ids) <= ids:
        raise ValueError('legacy dice log/cursor mismatch; manual reconciliation required')


def execute(campaign, request, generate, *, recover=False, after_write=None):
    campaign = Path(campaign)
    pending = campaign / PENDING
    state_path = campaign / 'hidden/dice_state.json'
    def checkpoint(name):
        if after_write:
            after_write(name)
    with batch.writer_lock(campaign):
        for name in ('ledger_batch_pending.json', 'experimental_dice_pending.json'):
            if (campaign / 'hidden' / name).exists():
                raise ValueError('another accepted transaction needs recovery before dice CLI writes')
        receipts = campaign / 'hidden/dice_cli_receipts'
        request_id = request.get('request_id')
        request_hash = fingerprint(request)
        receipt = receipts / (fingerprint(request_id) + '.json') if request_id else None
        if pending.exists():
            plan = json.loads(pending.read_text(encoding='utf-8'))
            if not recover and (not request_id or plan['request'] != request):
                raise ValueError('dice transaction pending; retry its exact request ID or use --recover-pending')
            receipt = receipts / (fingerprint(plan['receipt_id']) + '.json')
        elif recover:
            raise ValueError('no pending dice transaction; consult receipts/logs before repeating an unkeyed call')
        elif receipt and receipt.exists():
            done = json.loads(receipt.read_text(encoding='utf-8'))
            if done['fingerprint'] != request_hash:
                raise ValueError('request ID already accepted with different dice arguments')
            return done['result']
        else:
            before = state_path.read_bytes() if state_path.exists() else None
            state, records, result = generate()
            streams = {}
            for relative in LOGS:
                path = campaign / relative
                original = path.read_bytes() if path.exists() else b''
                streams[relative] = {'size': len(original), 'hash': batch.digest(original),
                                     'tail': json.dumps(records[relative]) + '\n' if relative in records else ''}
            plan = {'version': 1, 'request': request, 'fingerprint': request_hash,
                    'receipt_id': request_id or 'unkeyed:' + uuid.uuid4().hex,
                    'streams': streams, 'state': {'before': before.decode() if before is not None else None,
                                                'after': json.dumps(state, indent=1)}, 'result': result}
            receipts.mkdir(exist_ok=True)
            batch.sync_directory(receipts.parent)
            receipt = receipts / (fingerprint(plan['receipt_id']) + '.json')
            batch.durable_json(pending, plan)
            checkpoint('accepted')
        # Check every destination BEFORE finishing any one of them.
        for relative, stream in plan['streams'].items():
            path = campaign / relative
            current = path.read_bytes() if path.exists() else b''
            prefix, tail = current[:stream['size']], current[stream['size']:]
            if len(prefix) != stream['size'] or batch.digest(prefix) != stream['hash'] or not stream['tail'].encode().startswith(tail):
                raise ValueError('dice log diverged from accepted bytes; manual reconciliation required')
        current = state_path.read_bytes().decode() if state_path.exists() else None
        if current not in (plan['state']['before'], plan['state']['after']):
            raise ValueError('dice cursor diverged from accepted bytes; manual reconciliation required')
        for relative, stream in plan['streams'].items():
            if not stream['tail']:
                continue
            path = campaign / relative
            path.parent.mkdir(exist_ok=True)
            batch.sync_directory(path.parent.parent)
            offset = path.stat().st_size - stream['size'] if path.exists() else 0
            remaining = stream['tail'].encode()[offset:]
            with path.open('ab') as handle:
                split = len(remaining) // 2
                handle.write(remaining[:split])
                handle.flush()
                os.fsync(handle.fileno())
                checkpoint('partial:' + relative)
                handle.write(remaining[split:])
                handle.flush()
                os.fsync(handle.fileno())
            batch.sync_directory(path.parent)
            checkpoint('append:' + relative)
        temporary = state_path.with_suffix('.dice-cli.tmp')
        raw = plan['state']['after'].encode()
        with temporary.open('wb') as handle:
            split = len(raw) // 2
            handle.write(raw[:split])
            handle.flush()
            os.fsync(handle.fileno())
            checkpoint('state:partial')
            handle.write(raw[split:])
            handle.flush()
            os.fsync(handle.fileno())
        checkpoint('state:temporary')
        os.replace(temporary, state_path)
        batch.sync_directory(state_path.parent)
        checkpoint('state:replaced')
        batch.durable_json(receipt, {'fingerprint': plan['fingerprint'], 'result': plan['result']})
        checkpoint('receipt')
        pending.unlink()
        batch.sync_directory(pending.parent)
        checkpoint('complete')
        return plan['result']
