"""CC-004 Atomic sandbox dice authority: python -B test_atomic_service.py"""
import json, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import atomic_service as A

fails = 0
def check(cond, name, extra=''):
    global fails
    print(('ok ' if cond else 'FAIL ') + name, '' if cond else extra)
    fails += 0 if cond else 1

def err(fn):
    try:
        fn(); return None
    except A.AtomicError as e:
        return e.code

with tempfile.TemporaryDirectory() as d:
    svc = A.AtomicDice(d)
    sid = svc.open({'scenario': 'duelist'})['session']
    check(err(lambda: svc.roll(sid, 'R1.T0.aero', 'x', [{'seq': 0, 'sides': 20}], 'player', 'aero')) == 'NO_COMMIT', 'no dice without a committed plan')
    c = svc.commit(sid, 'R1.T0.aero', 'aero', [{'pid': 'saber_strike', 'target': 'ilsa'}])
    check(svc.commit(sid, 'R1.T0.aero', 'aero', [{'pid': 'saber_strike', 'target': 'ilsa'}])['duplicate'], 'same commit twice is idempotent')
    check(err(lambda: svc.roll(sid, 'R1.T0.aero', 'bogus', [{'seq': 0, 'sides': 20}], 'player', 'aero')) == 'PLAN_MISMATCH', 'dice must match the committed plan hash')
    r1 = svc.roll(sid, 'R1.T0.aero', c['plan_hash'], [{'seq': 0, 'sides': 20}], 'player', 'aero', 'Lightsaber Strike')
    r2 = svc.roll(sid, 'R1.T0.aero', c['plan_hash'], [{'seq': 0, 'sides': 20}], 'player', 'aero', 'Lightsaber Strike')
    check(r1['dice'] == r2['dice'] and r2['replayed'], 'retrying the same seq returns the identical die (no reroll)')
    check(err(lambda: svc.commit(sid, 'R1.T0.aero', 'aero', [{'pid': 'feint', 'target': 'ilsa'}])) == 'PLAN_LOCKED', 'plan locked once dice were drawn')
    check(err(lambda: svc.roll(sid, 'R1.T0.aero', c['plan_hash'], [{'seq': 5, 'sides': 8}], 'player', 'aero')) == 'SEQ_GAP', 'sequence gaps refused (no fishing ahead)')
    check(err(lambda: svc.roll(sid, 'R1.T0.aero', c['plan_hash'], [{'seq': 0, 'sides': 6}], 'player', 'aero')) == 'TAPE_CONFLICT', 'a different die at a drawn seq is refused')
    check(err(lambda: svc.roll(sid, 'R1.T0.aero', c['plan_hash'], [{'seq': 1, 'sides': 7}], 'player', 'aero')) == 'BAD_SIDES', 'only game dice')
    check(err(lambda: svc.roll(sid, 'R1.T0.aero', c['plan_hash'], [{'seq': 1, 'sides': 8}], 'wizard', 'aero')) == 'BAD_ROLLER', 'roller is player or gm')
    # peeking: a decoy turn cannot be used to see dice and then reuse them
    sid2 = svc.open({'scenario': 'duelist'})['session']
    d1 = svc.commit(sid2, 'R1.T0.aero', 'aero', [{'pid': 'feint', 'target': 'ilsa'}])
    svc.roll(sid2, 'R1.T0.aero', d1['plan_hash'], [{'seq': 0, 'sides': 20}], 'player', 'aero')
    check(err(lambda: svc.commit(sid2, 'R1.T0.aero', 'aero', [{'pid': 'saber_strike', 'target': 'ilsa'}])) == 'PLAN_LOCKED', 'peek attempt: the turn cannot be re-planned after a die is seen')
    check(err(lambda: svc.commit(sid2, 'R0.T9.aero', 'aero', [])) == 'TURN_ORDER', 'turns cannot be committed out of order')
    check(err(lambda: svc.commit(sid2, 'R1.T1.aero', 'ilsa', [])) == 'ACTOR_MISMATCH', 'turn key names its actor')
    check(err(lambda: svc.commit(sid2, 'garbage', 'aero', [])) == 'BAD_TURN_KEY', 'turn keys are validated')
    d2 = svc.commit(sid2, 'R1.T1.ilsa', 'ilsa', [{'pid': 'npc_blade', 'target': 'aero'}])
    check(err(lambda: svc.roll(sid2, 'R1.T1.ilsa', d2['plan_hash'], [{'seq': 0, 'sides': 20}], 'gm', 'ilsa')) == 'TAPE_CONFLICT', 'a die drawn in one turn cannot be reused by another')
    check(err(lambda: svc.roll(sid2, 'R1.T0.aero', d1['plan_hash'], [{'seq': 1, 'sides': 20}], 'player', 'aero')) == 'TURN_CLOSED', 'dice only for the current turn')
    svc.decide(sid, 'R1.T0.aero', 't1', 'parry')
    check(err(lambda: svc.decide(sid, 'R1.T0.aero', 't1', None)) == 'DECISION_LOCKED', 'player decisions are locked once made')
    j = svc.journal(sid)
    check('seed' not in json.dumps(j), 'the journal a client sees never contains the seed')
    # reload from disk: a fresh service (server restart) gives identical answers
    svc2 = A.AtomicDice(d)
    r3 = svc2.roll(sid, 'R1.T0.aero', c['plan_hash'], [{'seq': 0, 'sides': 20}], 'player', 'aero')
    check(r3['dice'] == r1['dice'], 'after a server restart the journal returns the same die')
    check(svc2.journal(sid) == j, 'journal survives restart unchanged')
    closed = svc2.close(sid)
    check(A.die_value(closed['seed'], 0, 20) == r1['dice'][0]['value'], 'after close, the revealed seed reproduces every die (audit)')
    check(err(lambda: svc2.commit(sid, 'R1.T1.ilsa', 'ilsa', [])) == 'SESSION_CLOSED', 'closed sessions accept nothing')
    check(err(lambda: svc2.journal('../../etc')) == 'NO_SESSION', 'session ids cannot escape the journal folder')
    # parity with the engine's local stream (JS), large seeds included
    js = "const E=require('./engine.js');const o=[];for(const sd of [0,1,77,2147483646,123456789])for(let n=0;n<30;n++)for(const k of [4,6,8,10,12,20,100])o.push(E._localDie(sd,n,k));console.log(JSON.stringify(o))"
    out = json.loads(subprocess.check_output(['node', '-e', js], cwd=HERE))
    py = [A.die_value(sd, n, k) for sd in [0, 1, 77, 2147483646, 123456789] for n in range(30) for k in [4, 6, 8, 10, 12, 20, 100]]
    check(out == py, 'server die function is bit-identical to the engine stream (1,050 draws)')
print('all passed' if not fails else f'{fails} FAILED')
sys.exit(1 if fails else 0)
