"""Real CLI/process-kill checks; all writes go to disposable synthetic campaigns."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DICE = ROOT / '.claude/skills/litrpg-dice'
QA = ROOT / 'development/.qa'
QA.mkdir(exist_ok=True)
sys.path.insert(0, str(DICE))
import roll

# No production crash environment variable: the subprocess injects an internal hook.
KILL = '''
import os, sys
sys.path.insert(0, sys.argv[1])
import roll, dice_transaction
boundary = sys.argv[2]
original = dice_transaction.execute
def wrapped(*args, **kwargs):
    def stop(name):
        if name == boundary:
            os._exit(71)
    return original(*args, **kwargs, after_write=stop)
dice_transaction.execute = wrapped
raise SystemExit(roll.main(sys.argv[3:]))
'''


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=QA)
        self.addCleanup(self.tmp.cleanup)
        self.camp = Path(self.tmp.name)
        (self.camp / 'hidden').mkdir()
        roll.save_state(self.camp / 'hidden/dice_state.json',
                        {'seed': 99, 'turn_no': 0, 'draws_used': 0, 'roll_count': 0})

    def cli(self, *args, boundary=None, ok=True, no_generate=False):
        command = ([sys.executable, '-B', '-c', KILL, str(DICE), boundary] if boundary else
                   [sys.executable, '-B', str(DICE / 'roll.py')])
        if no_generate:
            code = "import sys;sys.path.insert(0,sys.argv[1]);import roll;roll.prepare=lambda *a:(_ for _ in ()).throw(AssertionError('recovery generated new dice'));raise SystemExit(roll.main(sys.argv[2:]))"
            command = [sys.executable, '-B', '-c', code, str(DICE)]
        p = subprocess.run(command + ['--campaign', str(self.camp), *args], capture_output=True, text=True)
        if boundary:
            self.assertEqual(p.returncode, 71, p.stderr)
        elif ok:
            self.assertEqual(p.returncode, 0, p.stderr)
            return json.loads(p.stdout)
        else:
            self.assertNotEqual(p.returncode, 0)
        return p

    def state(self):
        return json.loads((self.camp / 'hidden/dice_state.json').read_text())

    def bytes(self):
        return {str(p.relative_to(self.camp)): p.read_bytes() for p in self.camp.rglob('*')
                if p.is_file() and p.suffix != '.tmp' and p.name != '.ledger_writer.lock'}

    def rows(self, path):
        p = self.camp / path
        return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []

    def test_keyed_retry_and_advance_are_once_only(self):
        args = ['1d20+3', '--dc', '10', '--request-id', 'action-1:check']
        first = self.cli(*args)
        before = self.bytes()
        self.assertEqual(self.cli(*args), first)
        self.assertEqual(self.bytes(), before)
        self.cli('--advance-turn', '--request-id', 'action-2:advance')
        self.cli('--advance-turn', '--request-id', 'action-2:advance')
        self.assertEqual(self.state()['turn_no'], 1)
        self.assertEqual(self.state()['draws_used'], 0)
        self.assertEqual(self.state()['roll_count'], 1)
        # Even after later writes, an old receipt returns its original result.
        self.assertEqual(self.cli(*args), first)
        self.assertEqual(self.state()['turn_no'], 1)

    def test_roll_crashes_recover_exact_bytes_and_independent_replay(self):
        for boundary in ('accepted', 'partial:records/roll_log.jsonl', 'append:records/roll_log.jsonl',
                         'partial:hidden/roll_dcs.jsonl', 'append:hidden/roll_dcs.jsonl',
                         'state:partial', 'state:temporary', 'state:replaced', 'receipt', 'complete'):
            with self.subTest(boundary=boundary):
                # Use distinct requests to also test recovery over nonempty prefixes.
                args = ['1d20+3', '--mode', 'advantage', '--dc', '10', '--request-id', boundary]
                count = self.state()['roll_count']
                self.cli(*args, boundary=boundary)
                out = self.cli(*args, no_generate=True)
                self.assertEqual(self.state()['roll_count'], count + 1)
                self.assertEqual(len(self.rows('records/roll_log.jsonl')), count + 1)
                self.assertEqual(len(self.rows('hidden/roll_dcs.jsonl')), count + 1)
                self.assertEqual(out['roll_id'], f'roll_t0_{count+1}')
                before = self.bytes()
                self.assertEqual(self.cli(*args), out)
                self.assertEqual(self.bytes(), before)
        import audit_rng
        self.assertTrue(audit_rng.audit(self.camp, samples=100)['ok'])
        public = (self.camp / 'records/roll_log.jsonl').read_text()
        for private in ('"dc"', '"seed"', '"request_id"', '"outcome"'):
            self.assertNotIn(private, public)

    def test_advance_crashes_never_advance_twice(self):
        for boundary in ('accepted', 'state:partial', 'state:temporary', 'state:replaced', 'receipt', 'complete'):
            with self.subTest(boundary=boundary):
                turn = self.state()['turn_no']
                args = ['--advance-turn', '--request-id', boundary]
                self.cli(*args, boundary=boundary)
                self.assertEqual(self.cli(*args, no_generate=True), {'turn_no': turn + 1})
                self.assertEqual(self.cli(*args, no_generate=True), {'turn_no': turn + 1})
                self.assertEqual(self.state()['turn_no'], turn + 1)

    def test_changed_request_or_other_pending_request_rejected(self):
        args = ['1d20', '--dc', '10', '--request-id', 'fixed']
        self.cli(*args, boundary='accepted')
        before = self.bytes()
        for changed in (['1d20', '--dc', '11', '--request-id', 'fixed'],
                        ['1d20', '--request-id', 'other'], ['--advance-turn', '--request-id', 'fixed'],
                        ['1d20', '--by', 'aero', '--dc', '10', '--request-id', 'fixed']):
            self.cli(*changed, ok=False)
            self.assertEqual(self.bytes(), before)
        self.cli(*args)
        self.cli('1d20', '--dc', '11', '--request-id', 'fixed', ok=False)

    def test_divergence_is_never_truncated_or_repaired(self):
        for relative in ('records/roll_log.jsonl', 'hidden/roll_dcs.jsonl', 'hidden/dice_state.json'):
            with self.subTest(relative=relative):
                args = ['1d20', '--dc', '10', '--request-id', relative]
                self.cli(*args, boundary='accepted')
                p = self.camp / relative
                p.parent.mkdir(exist_ok=True)
                original = p.read_bytes() if p.exists() else None
                p.write_bytes(b'foreign bytes')
                before = self.bytes()
                self.cli(*args, ok=False)
                self.assertEqual(self.bytes(), before)
                if original is None:
                    p.unlink()
                else:
                    p.write_bytes(original)
                self.cli(*args)

    def test_unkeyed_interruption_needs_explicit_recovery(self):
        self.cli('1d20', boundary='append:records/roll_log.jsonl')
        self.cli('1d20', ok=False)
        out = self.cli('--recover-pending', no_generate=True)
        self.assertEqual(out['roll_id'], 'roll_t0_1')
        self.assertEqual(self.state()['roll_count'], 1)
        self.assertEqual(self.cli('1d20')['roll_id'], 'roll_t0_2')
        self.cli('--recover-pending', ok=False)

    def test_old_unjournaled_divergence_and_other_writers_block(self):
        self.cli('1d20')
        p = self.camp / 'hidden/dice_state.json'
        state = self.state()
        state['draws_used'] = 0
        p.write_text(json.dumps(state))
        before = self.bytes()
        self.cli('1d20', '--request-id', 'next', ok=False)
        self.cli('--advance-turn', '--request-id', 'advance', ok=False)
        self.assertEqual(self.bytes(), before)
        state['draws_used'] = 1
        p.write_text(json.dumps(state))
        for name in ('experimental_dice_pending.json', 'ledger_batch_pending.json'):
            pending = self.camp / 'hidden' / name
            pending.write_text('{}')
            self.cli('1d20', '--request-id', 'next', ok=False)
            pending.unlink()
        sys.path.insert(0, str(ROOT / '.claude/skills/litrpg-ledger'))
        import batch
        with batch.writer_lock(self.camp):
            self.cli('1d20', '--request-id', 'next', ok=False)

    def test_readers_and_experimental_writer_refuse_pending_legacy_roll(self):
        self.cli('1d20', '--request-id', 'fixed', boundary='accepted')
        sys.path.insert(0, str(ROOT / '.claude/skills/litrpg-ledger'))
        import ledger
        for path in ('records/events.jsonl', 'hidden/events.jsonl', 'records/roll_log.jsonl'):
            with self.assertRaisesRegex(ValueError, 'dice transaction'):
                ledger.read_jsonl(self.camp / path)
        self.cli('1d20', '--request-id', 'fixed')

    def test_first_campaign_state_creation_is_recoverable(self):
        (self.camp / 'hidden/dice_state.json').unlink()
        args = ['1d20', '--request-id', 'first']
        self.cli(*args, boundary='state:partial')
        out = self.cli(*args, no_generate=True)
        self.assertEqual(out['roll_id'], 'roll_t0_1')
        self.assertEqual(self.state()['roll_count'], 1)


if __name__ == '__main__':
    unittest.main()
