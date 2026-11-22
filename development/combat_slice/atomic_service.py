"""Genesis CC-004 sandbox Atomic dice authority (noncanonical; never campaign rolls).

The combat engine never makes up a die in Atomic mode. It pauses with `need_dice`, and the caller asks this service.
Guarantees:
  * The seed is generated and kept server-side (secrets). Clients never see it until the session is closed.
  * Dice are drawn only under a COMMITTED plan for that turn (plan hash). Once a die is drawn under a commit, the plan
    for that turn is locked: a different plan for the same turn is refused (no fishing for better rolls).
  * Sequence numbers are contiguous. A retry of an already-drawn seq returns the identical stored value and roll id
    (idempotent; no reroll after a reconnect). A request that disagrees with the stored die (different sides) is refused.
  * Player decisions (reaction choices) are journaled and locked the same way.
  * Everything is appended to a JSONL journal, so a client that reconnects rebuilds the exact state by replay.
Value function: the same mulberry32 draw the engine's local sandbox stream uses, keyed by (secret seed, seq).
"""
import hashlib
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
JOURNAL_DIR = Path(os.environ.get('GENESIS_ATOMIC_DIR', HERE / 'out' / 'atomic'))
ALLOWED_SIDES = {4, 6, 8, 10, 12, 20, 100}
MAX_BATCH = 16
TURN_KEY = re.compile(r'^R(\d{1,4})\.T(\d{1,3})\.([a-z][a-z0-9_]{0,31})$')


def _order(turn_key):
    m = TURN_KEY.match(turn_key)
    if not m:
        raise AtomicError(400, 'BAD_TURN_KEY', 'turn_key must look like R1.T0.aero')
    return (int(m.group(1)), int(m.group(2))), m.group(3)


def _imul(a, b):
    return ((a & 0xFFFFFFFF) * (b & 0xFFFFFFFF)) & 0xFFFFFFFF


def _i32(x):
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x & 0x80000000 else x


def die_value(seed, n, sides):
    """Exact port of engine.js localDie: mulberry32((seed*7919 + n*104729)|0), first output."""
    st = _i32(seed * 7919 + n * 104729)
    st = _i32(st + 0x6D2B79F5)
    t = _imul(st ^ ((st & 0xFFFFFFFF) >> 15), 1 | st)
    t = (t + _imul(t ^ (t >> 7), 61 | t)) & 0xFFFFFFFF ^ t
    r = ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return 1 + int(r * sides)


class AtomicError(Exception):
    def __init__(self, status, code, text):
        super().__init__(text)
        self.status, self.code, self.text = status, code, text


def plan_hash(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:16]


class Session:
    def __init__(self, sid, meta, seed, journal):
        self.sid, self.meta, self.seed, self.journal = sid, meta, seed, journal
        self.tape = []            # [{seq, sides, value, roll_id, roller, turn_key, purpose}]
        self.commits = {}         # turn_key -> {plan_hash, plan, actor, locked}
        self.decisions = {}       # turn_key|key -> choice
        self.closed = False
        self.active = None        # newest committed turn_key; dice can only be drawn for it


class AtomicDice:
    def __init__(self, journal_dir=JOURNAL_DIR):
        self.dir = Path(journal_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.sessions = {}
        self.lock = threading.Lock()

    # ---- persistence ----
    def _append(self, sess, rec):
        rec = dict(rec, at=time.time())
        with open(sess.journal, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, separators=(',', ':')) + '\n')

    def _load(self, sid):
        if sid in self.sessions:
            return self.sessions[sid]
        path = self.dir / f'{sid}.jsonl'
        if not sid.isalnum() or not path.exists():
            raise AtomicError(404, 'NO_SESSION', 'Unknown session.')
        sess = None
        for line in path.read_text(encoding='utf-8').splitlines():
            r = json.loads(line)
            if r['op'] == 'open':
                sess = Session(sid, r['meta'], r['seed'], path)
            elif r['op'] == 'commit':
                sess.commits[r['turn_key']] = {'plan_hash': r['plan_hash'], 'plan': r['plan'], 'actor': r['actor'], 'locked': False}
                sess.active = r['turn_key']
            elif r['op'] == 'dice':
                for d in r['dice']:
                    sess.tape.append(d)
                    sess.commits[d['turn_key']]['locked'] = True
            elif r['op'] == 'decide':
                sess.decisions[r['turn_key'] + '|' + r['key']] = r['choice']
            elif r['op'] == 'close':
                sess.closed = True
        self.sessions[sid] = sess
        return sess

    # ---- API ----
    def open(self, meta):
        with self.lock:
            sid = secrets.token_hex(8)
            seed = secrets.randbits(31)
            sess = Session(sid, meta, seed, self.dir / f'{sid}.jsonl')
            self._append(sess, {'op': 'open', 'meta': meta, 'seed': seed, 'canonical': False})
            self.sessions[sid] = sess
            return {'session': sid, 'authority': 'atomic-sandbox', 'canonical': False}

    def commit(self, sid, turn_key, actor, plan):
        with self.lock:
            sess = self._load(sid)
            if sess.closed:
                raise AtomicError(409, 'SESSION_CLOSED', 'Session closed.')
            h = plan_hash(plan)
            order, who = _order(turn_key)
            if who != actor:
                raise AtomicError(409, 'ACTOR_MISMATCH', 'The turn key names another actor.')
            have = sess.commits.get(turn_key)
            if not have and sess.active and order <= _order(sess.active)[0]:
                raise AtomicError(409, 'TURN_ORDER', 'Turns are committed in order; ' + turn_key + ' is not after ' + sess.active + '.')
            if have:
                if have['plan_hash'] == h:
                    return {'turn_key': turn_key, 'plan_hash': h, 'duplicate': True, 'locked': have['locked']}
                if have['locked']:
                    raise AtomicError(409, 'PLAN_LOCKED', 'Dice were already drawn for this turn; the plan cannot change.')
                if have['actor'] != actor:
                    raise AtomicError(409, 'ACTOR_MISMATCH', 'This turn belongs to another actor.')
            sess.commits[turn_key] = {'plan_hash': h, 'plan': plan, 'actor': actor, 'locked': False}
            sess.active = turn_key
            self._append(sess, {'op': 'commit', 'turn_key': turn_key, 'actor': actor, 'plan': plan, 'plan_hash': h})
            return {'turn_key': turn_key, 'plan_hash': h, 'duplicate': False, 'locked': False}

    def roll(self, sid, turn_key, plan_hash_, dice, roller, actor, purpose=''):
        """dice: [{seq, sides}] contiguous. Returns the accepted values (stored ones on retry)."""
        with self.lock:
            sess = self._load(sid)
            if sess.closed:
                raise AtomicError(409, 'SESSION_CLOSED', 'Session closed.')
            c = sess.commits.get(turn_key)
            if not c:
                raise AtomicError(409, 'NO_COMMIT', 'Commit the plan for this turn before rolling.')
            if turn_key != sess.active:
                raise AtomicError(409, 'TURN_CLOSED', 'Dice are only drawn for the current turn (' + str(sess.active) + ').')
            if c['plan_hash'] != plan_hash_:
                raise AtomicError(409, 'PLAN_MISMATCH', 'These dice belong to a different plan than the one committed.')
            if roller not in ('player', 'gm'):
                raise AtomicError(400, 'BAD_ROLLER', 'roller must be player or gm.')
            if not dice or len(dice) > MAX_BATCH:
                raise AtomicError(400, 'BAD_BATCH', 'Ask for 1..16 dice.')
            out, new = [], []
            for i, d in enumerate(dice):
                seq, sides = int(d['seq']), int(d['sides'])
                if sides not in ALLOWED_SIDES:
                    raise AtomicError(400, 'BAD_SIDES', f'd{sides} is not a game die.')
                if seq < len(sess.tape):
                    have = sess.tape[seq]
                    if have['sides'] != sides:
                        raise AtomicError(409, 'TAPE_CONFLICT', f'seq {seq} was a d{have["sides"]}, not a d{sides}.')
                    if have['turn_key'] != turn_key:
                        raise AtomicError(409, 'TAPE_CONFLICT', f'seq {seq} belongs to turn {have["turn_key"]}.')
                    out.append(have)
                    continue
                if seq != len(sess.tape) + len(new):
                    raise AtomicError(409, 'SEQ_GAP', f'next die is seq {len(sess.tape) + len(new)}, not {seq}.')
                rec = {'seq': seq, 'sides': sides, 'value': die_value(sess.seed, seq, sides), 'roll_id': f'{sid}:{seq}',
                       'roller': roller, 'actor': actor, 'turn_key': turn_key, 'purpose': purpose[:120]}
                new.append(rec)
                out.append(rec)
            if new:
                sess.tape.extend(new)
                c['locked'] = True
                self._append(sess, {'op': 'dice', 'dice': new})
            return {'dice': [{k: r[k] for k in ('seq', 'sides', 'value', 'roll_id', 'roller')} for r in out],
                    'replayed': not new, 'authority': 'atomic-sandbox'}

    def decide(self, sid, turn_key, key, choice):
        with self.lock:
            sess = self._load(sid)
            k = turn_key + '|' + key
            if k in sess.decisions:
                if sess.decisions[k] != choice:
                    raise AtomicError(409, 'DECISION_LOCKED', 'That decision was already made.')
                return {'duplicate': True, 'choice': choice}
            sess.decisions[k] = choice
            self._append(sess, {'op': 'decide', 'turn_key': turn_key, 'key': key, 'choice': choice})
            return {'duplicate': False, 'choice': choice}

    def journal(self, sid):
        """Everything a reconnecting client needs to rebuild the exact state (never the seed)."""
        with self.lock:
            sess = self._load(sid)
            return {'session': sid, 'meta': sess.meta, 'closed': sess.closed,
                    'commits': [{'turn_key': k, 'actor': v['actor'], 'plan': v['plan'], 'plan_hash': v['plan_hash']} for k, v in sess.commits.items()],
                    'decisions': [{'turn_key': k.split('|')[0], 'key': k.split('|')[1], 'choice': v} for k, v in sess.decisions.items()],
                    'tape': [{k2: d[k2] for k2 in ('seq', 'sides', 'value', 'roll_id', 'roller')} for d in sess.tape]}

    def close(self, sid):
        with self.lock:
            sess = self._load(sid)
            if not sess.closed:
                sess.closed = True
                self._append(sess, {'op': 'close'})
            return {'closed': True, 'seed': sess.seed, 'note': 'Seed revealed after close for audit: every die is die_value(seed, seq, sides).'}


def handle(service, path, body):
    """Route /atomic/* requests. Returns (status, dict)."""
    try:
        b = body or {}
        if path == '/atomic/open':
            return 200, service.open({'scenario': str(b.get('scenario', ''))[:40], 'switches': b.get('switches') or {}})
        if path == '/atomic/commit':
            return 200, service.commit(b['session'], str(b['turn_key']), str(b['actor']), b['plan'])
        if path == '/atomic/roll':
            return 200, service.roll(b['session'], str(b['turn_key']), str(b['plan_hash']), b['dice'], b['roller'], str(b.get('actor', '')), str(b.get('purpose', '')))
        if path == '/atomic/decide':
            return 200, service.decide(b['session'], str(b['turn_key']), str(b['key']), b.get('choice'))
        if path == '/atomic/journal':
            return 200, service.journal(b['session'])
        if path == '/atomic/close':
            return 200, service.close(b['session'])
        return 404, {'error': 'NO_ROUTE'}
    except AtomicError as e:
        return e.status, {'error': e.code, 'text': e.text}
    except (KeyError, TypeError, ValueError) as e:
        return 400, {'error': 'BAD_REQUEST', 'text': str(e)[:200]}
