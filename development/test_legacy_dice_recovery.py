"""Process-death recovery tests; synthetic campaigns only, never source runs."""
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
POINTS = ['accepted', 'append:records/roll_log.jsonl', 'append:hidden/roll_dcs.jsonl',
          'state:temporary', 'state:replaced', 'receipt', 'complete']


class Recovery(unittest.TestCase):
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
        plan = json.loads((self.camp/'hidden/legacy_dice_pending.json').read_text())
        for relative, stream in plan['streams'].items():
            path = self.camp/relative
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(stream['tail'].encode()[:17])
        self.state.with_suffix('.legacy.tmp').write_bytes(b'{"seed":')
        expected = plan['result']
        self.assertEqual(self.run_roll(self.args()),expected)
        self.assertFalse(self.state.with_suffix('.legacy.tmp').exists())
        self.assert_replay()

    def test_process_death_inside_partial_writes(self):
        targets = ['records/roll_log.jsonl', 'hidden/roll_dcs.jsonl',
                   'hidden/dice_state.legacy.tmp', 'hidden/legacy_dice_pending.tmp', 'receipt']
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
    selected = ('legacy_dice_receipts' in str(path) and path.suffix=='.tmp') if target=='receipt' else str(path).endswith(target)
    return Torn(handle) if selected and ('w' in mode or 'a' in mode) else handle
Path.open=opened
roll.main(json.loads(sys.argv[2]))
"""
        for target in targets:
            with self.subTest(target=target):
                self.tearDown_fixture()
                child = subprocess.run([sys.executable,'-B','-c',code,str(HERE),json.dumps(self.args()),target],capture_output=True,text=True)
                self.assertEqual(child.returncode,79,child.stderr)
                accepted = self.camp/'hidden/legacy_dice_pending.json'
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

    def test_legacy_unkeyed_commands_remain_distinct_and_recover_pending(self):
        args = ['1d20','--campaign',str(self.camp)]
        self.kill('state:replaced',args)
        first = self.run_roll(args)
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
        self.assertFalse((self.camp/'hidden/legacy_dice_pending.json').exists())
        result = self.run_roll(self.args())
        self.assertEqual(result['roll_id'],'roll_t0_1')
        self.assert_replay()


if __name__ == '__main__':
    unittest.main()
