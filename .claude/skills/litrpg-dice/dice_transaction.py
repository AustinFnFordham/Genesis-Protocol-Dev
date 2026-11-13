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


def validate_plan(plan):
    """Accept only this resolver's v1 destinations and immutable request binding."""
    if not isinstance(plan, dict) or type(plan.get('version')) is not int or plan['version'] != 1:
        raise ValueError('unsupported dice transaction version; use its original compatible resolver')
    request = plan['request']
    if not isinstance(request, dict) or fingerprint(request) != plan['fingerprint']:
        raise ValueError('dice journal request fingerprint differs; manual reconciliation required')
    receipt_id = plan['receipt_id']
    if (not isinstance(receipt_id, str) or not receipt_id or
            (request.get('request_id') is not None and receipt_id != request['request_id'])):
        raise ValueError('dice journal receipt identity differs; manual reconciliation required')
    if not isinstance(plan.get('streams'), dict) or set(plan['streams']) != set(LOGS):
        raise ValueError('dice journal destinations differ; manual reconciliation required')
    for stream in plan['streams'].values():
        if (not isinstance(stream, dict) or type(stream.get('size')) is not int or stream['size'] < 0 or
                not isinstance(stream['tail'], str) or not isinstance(stream['hash'], str)):
            raise ValueError('invalid dice journal stream; manual reconciliation required')
    state = plan.get('state')
    if (not isinstance(state, dict) or
            (state['before'] is not None and not isinstance(state['before'], str)) or
            not isinstance(state['after'], str)):
        raise ValueError('invalid dice journal cursor; manual reconciliation required')
    if not isinstance(plan['result'], dict):
        raise ValueError('invalid dice journal result; manual reconciliation required')


def execute(campaign, request, generate, *, recover=False, after_write=None):
    campaign = Path(campaign)
    request_id = request.get('request_id')
    if request_id is not None and (not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 200):
        raise ValueError('request ID must contain 1 to 200 characters')
    pending = campaign / PENDING
    state_path = campaign / 'hidden/dice_state.json'
    def checkpoint(name):
        if after_write:
            after_write(name)
    with batch.writer_lock(campaign):
        batch.sync_directory(campaign)  # retain a newly created hidden directory
        foreign_receipts = campaign / 'hidden/legacy_dice_receipts'
        if ((campaign / 'hidden/legacy_dice_pending.json').exists() or
                (foreign_receipts.exists() and any(foreign_receipts.iterdir()))):
            raise ValueError('Candidate A dice state requires its original compatible resolver or reviewed migration')
        for name in ('ledger_batch_pending.json', 'experimental_dice_pending.json'):
            if (campaign / 'hidden' / name).exists():
                raise ValueError('another accepted transaction needs recovery before dice CLI writes')
        receipts = campaign / 'hidden/dice_cli_receipts'
        request_hash = fingerprint(request)
        receipt = receipts / (fingerprint(request_id) + '.json') if request_id else None
        if pending.exists():
            plan = json.loads(pending.read_text(encoding='utf-8'))
            validate_plan(plan)
            if not recover and (not request_id or plan['request'] != request):
                raise ValueError('dice transaction pending; retry its exact request ID or use --recover-pending')
            receipt = receipts / (fingerprint(plan['receipt_id']) + '.json')
        elif recover:
            raise ValueError('no pending dice transaction; consult receipts/logs before repeating an unkeyed call')
        elif receipt and receipt.exists():
            done = json.loads(receipt.read_text(encoding='utf-8'))
            if (not isinstance(done, dict) or done.get('fingerprint') != request_hash or
                    not isinstance(done.get('result'), dict)):
                raise ValueError('request ID receipt is invalid or accepted with different dice arguments')
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
            validate_plan(plan)
            batch.durable_json(pending, plan)
            checkpoint('accepted')
        # A completed receipt alongside pending is valid only if it agrees exactly.
        expected_receipt = {'fingerprint': plan['fingerprint'], 'result': plan['result']}
        if receipt.exists() and json.loads(receipt.read_text(encoding='utf-8')) != expected_receipt:
            raise ValueError('dice receipt diverged from accepted bytes; manual reconciliation required')
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
        batch.durable_json(receipt, expected_receipt)
        checkpoint('receipt')
        pending.unlink()
        batch.sync_directory(pending.parent)
        checkpoint('complete')
        return plan['result']
