"""Reconciled recovery coverage from A (97620de) and B (883308e).
A's unkeyed retry expectation is explicitly changed to B's recovery-only contract.
All writes use disposable synthetic campaigns.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / '.claude/skills/litrpg-dice'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / '.claude/skills/litrpg-ledger'))
import roll
import ledger
import batch
import audit_rng

QA = ROOT / 'development/.qa'
QA.mkdir(exist_ok=True)
PROCESS_INTERRUPTION_RESULTS = []
POINTS = ['accepted', 'append:records/roll_log.jsonl', 'append:hidden/roll_dcs.jsonl',
          'state:temporary', 'state:replaced', 'receipt', 'complete']


class CandidateACoverage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=QA)
        self.addCleanup(self.temp.cleanup)
        self.camp = Path(self.temp.name)
        (self.camp/'hidden').mkdir()
        self.state = self.camp/'hidden/dice_state.json'
        self.state.write_text(json.dumps({'seed':99,'turn_no':0,'draws_used':0,'roll_count':0}))

    def args(self, *extra):
        return ['1d20+3','--dc','10','--purpose','synthetic public check',
                '--by','aero','--request-id','action-1:check', '--campaign',str(self.camp),*extra]

    def run_roll(self, args):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(roll.main(args), 0)
        return json.loads(out.getvalue())

    def kill(self, point, args=None):
        code = ("import sys,os,json;sys.path.insert(0,sys.argv[1]);import roll;"
                "roll.main(json.loads(sys.argv[2]),after_write=lambda p:os._exit(77) if p==sys.argv[3] else None)")
        child = subprocess.run([sys.executable,'-B','-c',code,str(HERE),json.dumps(args or self.args()),point],capture_output=True,text=True)
        self.assertEqual(child.returncode,77,child.stderr)
        PROCESS_INTERRUPTION_RESULTS.append({'suite':type(self).__name__,'point':point,'operation':'advance' if '--advance-turn' in (args or self.args()) else 'roll','exit_code':77})

    def files(self):
        return {str(p.relative_to(self.camp)):p.read_bytes() for p in self.camp.rglob('*') if p.is_file()}

    def assert_replay(self):
        self.assertTrue(audit_rng.audit(self.camp,samples=100)['ok'])
        rows = ledger.read_jsonl(self.camp/'records/roll_log.jsonl')
        self.assertEqual(len(rows),1)
        self.assertNotIn('dc',rows[0])
        self.assertNotIn('outcome',rows[0])
        self.assertNotIn('request_id',rows[0])

    def test_process_death_at_each_boundary_and_completed_retry(self):
        for point in POINTS:
            with self.subTest(point=point):
                # Reset only this disposable fixture between separate crash cases.
                self.tearDown_fixture()
                self.kill(point)
                if point != 'complete':
                    with self.assertRaises(ValueError):
                        ledger.load_all(self.camp)
                original = roll.do_roll
                roll.do_roll = lambda *a: (_ for _ in ()).throw(AssertionError('retry rerolled'))
                try:
                    result = self.run_roll(self.args())
                    before = self.files()
                    self.assertEqual(self.run_roll(self.args()),result)
                    self.assertEqual(self.files(),before)
                finally:
                    roll.do_roll = original
                self.assert_replay()

    def tearDown_fixture(self):
        import shutil
        for child in self.camp.iterdir():
            if child.is_dir(): shutil.rmtree(child)
            else: child.unlink()
        (self.camp/'hidden').mkdir()
        self.state.write_text(json.dumps({'seed':99,'turn_no':0,'draws_used':0,'roll_count':0}))

    def test_torn_log_and_state_temporary_recover_exact_bytes(self):
        self.kill('accepted')
        plan = json.loads((self.camp/'hidden/dice_cli_pending.json').read_text())
        for relative, stream in plan['streams'].items():
            path = self.camp/relative
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(stream['tail'].encode()[:17])
        self.state.with_suffix('.dice-cli.tmp').write_bytes(b'{"seed":')
        expected = plan['result']
        self.assertEqual(self.run_roll(self.args()),expected)
        self.assertFalse(self.state.with_suffix('.dice-cli.tmp').exists())
        self.assert_replay()

    def test_process_death_inside_partial_writes(self):
        targets = ['records/roll_log.jsonl', 'hidden/roll_dcs.jsonl',
                   'hidden/dice_state.dice-cli.tmp', 'hidden/dice_cli_pending.tmp', 'receipt']
        code = r"""
import json,os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import roll
original = Path.open
class Torn:
    def __init__(self,handle): self.handle=handle
    def __enter__(self): return self
    def __exit__(self,*args): self.handle.close()
    def write(self,data):
        self.handle.write(data[:max(1,len(data)//2)])
        self.handle.flush()
        os.fsync(self.handle.fileno())
        os._exit(79)
def opened(path,mode='r',*args,**kwargs):
    handle=original(path,mode,*args,**kwargs)
    target=sys.argv[3]
    selected = ('dice_cli_receipts' in str(path) and path.suffix=='.tmp') if target=='receipt' else str(path).endswith(target)
    return Torn(handle) if selected and ('w' in mode or 'a' in mode) else handle
Path.open=opened
roll.main(json.loads(sys.argv[2]))
"""
        for target in targets:
            with self.subTest(target=target):
                self.tearDown_fixture()
                child = subprocess.run([sys.executable,'-B','-c',code,str(HERE),json.dumps(self.args()),target],capture_output=True,text=True)
                self.assertEqual(child.returncode,79,child.stderr)
                PROCESS_INTERRUPTION_RESULTS.append({'suite':type(self).__name__,'point':'partial:'+target,'operation':'roll','exit_code':79})
                accepted = self.camp/'hidden/dice_cli_pending.json'
                plan = json.loads(accepted.read_text()) if accepted.exists() else None
                if plan:
                    original_roll = roll.do_roll
                    roll.do_roll = lambda *a: (_ for _ in ()).throw(AssertionError('partial-write retry rerolled'))
                    try:
                        self.assertEqual(self.run_roll(self.args()),plan['result'])
                    finally:
                        roll.do_roll = original_roll
                else:
                    self.assertFalse((self.camp/'records/roll_log.jsonl').exists())
                    self.assertEqual(json.loads(self.state.read_text())['roll_count'],0)
                    self.run_roll(self.args())
                self.assert_replay()

    def test_completed_request_rejects_changed_arguments(self):
        self.run_roll(self.args())
        before = self.files()
        for extra in (('--mode','advantage'),('--dc','11'),('--purpose','changed'),('--by','gm')):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(roll.main(self.args(*extra)),2)
            self.assertEqual(self.files(),before)

    def test_pending_dice_blocks_existing_batch_receipt_replay(self):
        import time
        lease = self.camp/'hidden/lease.json'
        lease.write_text(json.dumps({'holder':'test','expires_ms':time.time_ns()//1000000+60000}))
        request = {'batch_id':'test','expected_revision':0}
        receipts = self.camp/'hidden/ledger_batch_receipts'
        receipts.mkdir()
        fingerprint = batch.digest(json.dumps(request,sort_keys=True).encode())
        (receipts/(batch.digest(b'test')+'.json')).write_text(json.dumps({'fingerprint':fingerprint,'result':{}}))
        self.kill('accepted')
        with self.assertRaisesRegex(ValueError,'dice request'):
            batch.apply(self.camp,request,lease,'test',ledger)
        with self.assertRaisesRegex(ValueError,'dice transaction'):
            audit_rng.audit(self.camp,samples=100)

    def test_changed_retry_and_divergent_bytes_fail_without_writes(self):
        self.kill('append:records/roll_log.jsonl')
        before = self.files()
        for args in (self.args('--dc','11'),self.args('--request-id','renamed'),
                     ['--advance-turn','--campaign',str(self.camp)]):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(roll.main(args),2)
            self.assertEqual(self.files(),before)
        hidden = self.camp/'hidden/roll_dcs.jsonl'
        hidden.write_bytes(b'wrong')
        before = self.files()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(roll.main(self.args()),2)
        self.assertEqual(self.files(),before)

    def test_divergent_cursor_and_prior_log_are_not_repaired(self):
        self.kill('accepted')
        self.state.write_text('{}')
        before = self.files()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(roll.main(self.args()),2)
        self.assertEqual(self.files(),before)
        self.tearDown_fixture()
        self.run_roll(self.args())
        self.state.write_text(json.dumps({'seed':99,'turn_no':0,'draws_used':0,'roll_count':0}))
        before = self.files()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(roll.main(self.args('--request-id','new')),2)
        self.assertEqual(self.files(),before)

    def test_advance_turn_retry_is_once_only(self):
        args = ['--advance-turn','--request-id','action-1:advance','--campaign',str(self.camp)]
        for point in ('accepted','state:temporary','state:replaced','receipt','complete'):
            with self.subTest(point=point):
                self.tearDown_fixture()
                self.kill(point,args)
                self.assertEqual(self.run_roll(args),{'turn_no':1})
                self.run_roll(args)
                self.assertEqual(json.loads(self.state.read_text())['turn_no'],1)
                self.run_roll(self.args())
                self.run_roll(args)  # retry after later rolls must not reset the stream
                self.assertEqual(json.loads(self.state.read_text())['draws_used'],1)
                self.assert_replay()

    def test_legacy_unkeyed_commands_remain_distinct_and_explicitly_recover_pending(self):
        args = ['1d20','--campaign',str(self.camp)]
        self.kill('state:replaced',args)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(roll.main(args),2)
        first = self.run_roll(['--recover-pending','--campaign',str(self.camp)])
        second = self.run_roll(args)
        self.assertNotEqual(first['roll_id'],second['roll_id'])
        self.assertEqual(json.loads(self.state.read_text())['roll_count'],2)

    def test_shared_writer_lock_and_other_pending_transactions(self):
        with batch.writer_lock(self.camp), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(roll.main(self.args()),2)
        for filename in ('ledger_batch_pending.json','experimental_dice_pending.json'):
            path = self.camp/'hidden'/filename
            path.write_text('{}')
            before = self.files()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(roll.main(self.args()),2)
            self.assertEqual(self.files(),before)
            path.unlink()

    def test_new_campaign_and_invalid_formula_do_not_accept_a_roll(self):
        self.state.unlink()
        bad = self.args(); bad[0] = 'no dice'
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(roll.main(bad),2)
        self.assertFalse(self.state.exists())
        self.assertFalse((self.camp/'hidden/dice_cli_pending.json').exists())
        result = self.run_roll(self.args())
        self.assertEqual(result['roll_id'],'roll_t0_1')
        self.assert_replay()


# Candidate B retained coverage, including nonempty log prefixes.
DICE = HERE
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


class CandidateBCoverage(unittest.TestCase):
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
            PROCESS_INTERRUPTION_RESULTS.append({'suite':type(self).__name__,'point':boundary,'operation':'advance' if '--advance-turn' in args else 'roll','exit_code':71})
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


class CanonicalContractCoverage(unittest.TestCase):
    # Reuse fixture helpers without inheriting and rerunning either candidate suite.
    setUp = CandidateACoverage.setUp
    args = CandidateACoverage.args
    run_roll = CandidateACoverage.run_roll
    kill = CandidateACoverage.kill
    files = CandidateACoverage.files
    assert_replay = CandidateACoverage.assert_replay

    def recover_args(self):
        return ['--recover-pending','--campaign',str(self.camp)]

    def rejected_unchanged(self,args):
        # Acquiring a previously absent lock may create its empty lock file.
        snapshot=lambda:{k:v for k,v in self.files().items() if k!='hidden/.ledger_writer.lock'}
        before=snapshot()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(roll.main(args),2)
        self.assertEqual(snapshot(),before)

    def test_receipt_divergence_never_overwritten(self):
        self.kill('receipt')
        receipt=next((self.camp/'hidden/dice_cli_receipts').glob('*.json'))
        value=json.loads(receipt.read_text())
        value['result']={'foreign':'bytes'}
        receipt.write_text(json.dumps(value))
        self.rejected_unchanged(self.args())
        self.rejected_unchanged(self.recover_args())
        self.assertTrue((self.camp/'hidden/dice_cli_pending.json').exists())

    def test_unused_stream_is_checked_before_acceptance_and_during_recovery(self):
        self.run_roll(self.args())
        hidden=self.camp/'hidden/roll_dcs.jsonl'
        good=hidden.read_bytes()
        hidden.write_bytes(good+b'torn')
        self.rejected_unchanged(['--advance-turn','--request-id','advance','--campaign',str(self.camp)])
        self.rejected_unchanged(['1d6','--request-id','no-dc','--campaign',str(self.camp)])
        hidden.write_bytes(good)
        args=['--advance-turn','--request-id','advance','--campaign',str(self.camp)]
        self.kill('accepted',args)
        hidden.write_bytes(good+b'foreign')
        self.rejected_unchanged(args)
        hidden.write_bytes(good)
        self.assertEqual(self.run_roll(args),{'turn_no':1})

    def test_explicit_unkeyed_recovery_itself_can_be_interrupted(self):
        args=['1d20','--campaign',str(self.camp)]
        self.kill('accepted',args)
        self.rejected_unchanged(args)
        self.kill('state:replaced',self.recover_args())
        self.assertEqual(self.run_roll(self.recover_args())['roll_id'],'roll_t0_1')
        self.rejected_unchanged(self.recover_args())
        self.assert_replay()
        receipts=list((self.camp/'hidden/dice_cli_receipts').glob('*.json'))
        self.assertEqual(len(receipts),1)

    def test_keyed_explicit_recovery_retains_original_request_receipt(self):
        self.kill('partial:records/roll_log.jsonl')
        original=roll.prepare
        roll.prepare=lambda *a:(_ for _ in ()).throw(AssertionError('explicit recovery regenerated'))
        try:
            recovered=self.run_roll(self.recover_args())
            self.assertEqual(self.run_roll(self.args()),recovered)
        finally:roll.prepare=original
        self.assert_replay()

    def test_b_v1_journal_remains_compatible(self):
        # Exact plan captured from commit 883308e in a synthetic seed-99 campaign.
        fixture=json.loads((ROOT/'development/fixtures/dice_b_v1_plan.json').read_text())
        plan=fixture['plan']
        self.assertEqual(self.state.read_text(),plan['state']['before'])
        (self.camp/'hidden/dice_cli_pending.json').write_text(json.dumps(plan))
        (self.camp/'hidden/dice_cli_receipts').mkdir()
        original=roll.prepare
        roll.prepare=lambda *a:(_ for _ in ()).throw(AssertionError('B journal regenerated'))
        try:self.assertEqual(self.run_roll(self.recover_args()),plan['result'])
        finally:roll.prepare=original
        self.assert_replay()

    def test_foreign_a_artifacts_are_refused_without_migration(self):
        pending=self.camp/'hidden/legacy_dice_pending.json'
        pending.write_text('{}')
        self.rejected_unchanged(self.args())
        self.rejected_unchanged(self.recover_args())
        with self.assertRaises(ValueError):ledger.load_all(self.camp)
        with self.assertRaises(ValueError):audit_rng.audit(self.camp,samples=100)
        pending.unlink()
        receipts=self.camp/'hidden/legacy_dice_receipts';receipts.mkdir()
        (receipts/'old.json').write_text('{}')
        self.rejected_unchanged(self.args())

    def test_changed_journal_contract_is_not_reinterpreted(self):
        self.kill('accepted')
        path=self.camp/'hidden/dice_cli_pending.json'
        original=json.loads(path.read_text())
        import copy
        for change in ('version','request','destination','identity'):
            plan=copy.deepcopy(original)
            if change=='version':plan['version']=2
            if change=='request':plan['request']['dc']=999
            if change=='destination':plan['streams']['outside.json']=plan['streams'].pop('hidden/roll_dcs.jsonl')
            if change=='identity':plan['receipt_id']='different'
            path.write_text(json.dumps(plan))
            self.rejected_unchanged(self.recover_args())
        path.write_text(json.dumps(original))
        self.run_roll(self.args())
        self.assert_replay()

    def test_duplicate_or_orphan_dcs_block_new_operations(self):
        self.run_roll(self.args())
        hidden=self.camp/'hidden/roll_dcs.jsonl';good=hidden.read_bytes()
        for bad in (good+good,json.dumps({'roll_id':'roll_t0_999','dc':10,'outcome':'failure'}).encode()+b'\n'):
            hidden.write_bytes(bad)
            self.rejected_unchanged(['1d6','--request-id','new','--campaign',str(self.camp)])
        hidden.write_bytes(good)
        self.assert_replay()

    def test_process_death_between_rename_or_unlink_and_directory_sync(self):
        code=r"""
import json,os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import roll
point=sys.argv[3]
original_replace=os.replace
original_unlink=Path.unlink
def replace(source,destination):
    original_replace(source,destination)
    path=Path(destination)
    selected=(point=='journal' and path.name=='dice_cli_pending.json' or
              point=='state' and path.name=='dice_state.json' or
              point=='receipt' and path.parent.name=='dice_cli_receipts')
    if selected:os._exit(80)
def unlink(path,*args,**kwargs):
    original_unlink(path,*args,**kwargs)
    if point=='unlink' and path.name=='dice_cli_pending.json':os._exit(80)
os.replace=replace
Path.unlink=unlink
raise SystemExit(roll.main(json.loads(sys.argv[2])))
"""
        for point in ('journal','state','receipt','unlink'):
            with self.subTest(point=point):
                CandidateACoverage.tearDown_fixture(self)
                child=subprocess.run([sys.executable,'-B','-c',code,str(HERE),json.dumps(self.args()),point],capture_output=True,text=True)
                self.assertEqual(child.returncode,80,child.stderr)
                PROCESS_INTERRUPTION_RESULTS.append({'suite':type(self).__name__,'point':'before-directory-sync:'+point,'operation':'roll','exit_code':80})
                original=roll.prepare
                roll.prepare=lambda *a:(_ for _ in ()).throw(AssertionError('rename/unlink retry regenerated'))
                try:self.run_roll(self.args())
                finally:roll.prepare=original
                self.assert_replay()

    def test_invalid_flag_combinations_do_not_start_a_transaction(self):
        for args in (self.recover_args()+['1d20'],self.args()+['--advance-turn'],self.args('--request-id',' ')):
            before=self.files()
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as caught:
                roll.main(args)
            self.assertEqual(caught.exception.code,2)
            self.assertEqual(self.files(),before)


if __name__ == '__main__':
    program=unittest.main(exit=False)
    result=program.result
    report={'test_cases':result.testsRun,'passed':result.wasSuccessful(),
            'process_terminations':len(PROCESS_INTERRUPTION_RESULTS),
            'terminations':PROCESS_INTERRUPTION_RESULTS}
    (QA/'canonical_dice_process_tests.json').write_text(json.dumps(report,indent=2)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
