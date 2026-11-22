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

CC-005 additions (when constructed with an EngineWorker):
  * The server rebuilds every session from its own journal with the real engine (atomic_engine_worker.cjs) and is the
    authority on: whose turn it is, the GM's plan for an NPC, plan legality, which dice are needed next and by whom,
    which player decision is pending, and the state after each turn. The client's numbers are only ever compared.
  * /atomic/complete verifies a finished turn: the server's reconstruction is the result; a client whose state hash
    differs is told STATE_MISMATCH (tampering or a client bug) and can fetch the authoritative state.
  * Session-shopping: a "bound" session belongs to one encounter id. Opening that encounter again returns the SAME
    session (same seed, same history); abandoning it is a recorded forfeit, never a fresh seed. "practice" sessions
    get a fresh seed each time and are labelled ineligible for campaign authority.
"""
import hashlib
import json
import os
import re
import secrets
import subprocess
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


class EngineWorker:
    """Long-lived `node atomic_engine_worker.cjs` child. One request at a time (the service lock serialises calls)."""

    def __init__(self, script=HERE / 'atomic_engine_worker.cjs'):
        self.script, self.proc, self.n = str(script), None, 0

    def _start(self):
        self.proc = subprocess.Popen(['node', self.script], cwd=str(HERE), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, bufsize=1)

    def inspect(self, journal, candidate=None):
        for attempt in (0, 1):
            try:
                if not self.proc or self.proc.poll() is not None:
                    self._start()
                self.n += 1
                self.proc.stdin.write(json.dumps({'id': self.n, 'op': 'inspect', 'journal': journal, 'candidate': candidate}) + '\n')
                self.proc.stdin.flush()
                line = self.proc.stdout.readline()
                if not line:
                    raise OSError('engine worker exited')
                res = json.loads(line)
                if res.get('error'):
                    raise AtomicError(500, res['error'], res.get('text', 'engine error'))
                return res
            except (OSError, ValueError):
                self.proc = None
                if attempt:
                    raise AtomicError(503, 'ENGINE_UNAVAILABLE', 'The server-side engine is not available; nothing was accepted.')

    def close(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()


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
        self.verified = {}        # turn_key -> {server_hash, client_hash, ok}
        self.active = None        # newest committed turn_key; dice can only be drawn for it


class AtomicDice:
    def __init__(self, journal_dir=JOURNAL_DIR, engine=None):
        self.dir = Path(journal_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.sessions = {}
        self.lock = threading.Lock()
        self.engine = engine      # EngineWorker: enables server-side verification (CC-005)
        self.index_path = self.dir / 'encounters.json'

    def _index(self):
        try:
            return json.loads(self.index_path.read_text())
        except (OSError, ValueError):
            return {}

    def _jobj(self, sess):
        return {'meta': sess.meta,
                'commits': [{'turn_key': k, 'actor': v['actor'], 'plan': v['plan']} for k, v in sess.commits.items()],
                'decisions': [{'turn_key': k.split('|')[0], 'key': k.split('|')[1], 'choice': v} for k, v in sess.decisions.items()],
                'tape': [{k2: d[k2] for k2 in ('seq', 'sides', 'value', 'roll_id', 'roller')} for d in sess.tape]}

    def _inspect(self, sess, candidate=None):
        return self.engine.inspect(self._jobj(sess), candidate) if self.engine else None

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
            elif r['op'] == 'verify':
                sess.verified[r['turn_key']] = {'server_hash': r['server_hash'], 'client_hash': r['client_hash'], 'ok': r['ok']}
            elif r['op'] in ('close', 'abandon'):
                sess.closed = True
        self.sessions[sid] = sess
        return sess

    # ---- API ----
    def open(self, meta, mode='practice', encounter_id=None):
        with self.lock:
            if mode not in ('practice', 'bound'):
                raise AtomicError(400, 'BAD_MODE', 'mode is practice or bound')
            if mode == 'bound':
                if not encounter_id or not re.match(r'^[A-Za-z0-9_.:-]{3,80}$', str(encounter_id)):
                    raise AtomicError(400, 'NEED_ENCOUNTER', 'A bound session needs an encounter id issued by the campaign authority.')
                idx = self._index()
                if encounter_id in idx:   # never a second seed for the same encounter
                    sess = self._load(idx[encounter_id])
                    return {'session': sess.sid, 'authority': 'atomic-sandbox', 'canonical': False, 'mode': 'bound', 'resumed': True,
                            'closed': sess.closed, 'encounter_id': encounter_id}
            sid = secrets.token_hex(8)
            seed = secrets.randbits(31)
            meta = dict(meta, mode=mode, encounter_id=encounter_id)
            sess = Session(sid, meta, seed, self.dir / f'{sid}.jsonl')
            self._append(sess, {'op': 'open', 'meta': meta, 'seed': seed, 'canonical': False})
            self.sessions[sid] = sess
            if mode == 'bound':
                idx = self._index(); idx[encounter_id] = sid
                tmp = self.index_path.with_suffix('.tmp'); tmp.write_text(json.dumps(idx)); os.replace(tmp, self.index_path)
            return {'session': sid, 'authority': 'atomic-sandbox', 'canonical': False, 'mode': mode, 'resumed': False,
                    'eligible_for_campaign_authority': mode == 'bound'}

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
            if not have and self.engine:
                insp = self._inspect(sess, {'actor': actor, 'plan': plan})
                if insp.get('over'):
                    raise AtomicError(409, 'ENCOUNTER_OVER', 'The encounter is over.')
                if insp.get('pending'):
                    raise AtomicError(409, 'TURN_PENDING', 'Finish ' + insp['pending']['turn_key'] + ' first.')
                nxt = insp['next']
                if turn_key != nxt['turn_key'] or actor != nxt['actor']:
                    raise AtomicError(409, 'NOT_YOUR_TURN', 'The server says the next turn is ' + nxt['turn_key'] + '.')
                if nxt['controller'] == 'npc' and plan != nxt['npc_plan']:
                    raise AtomicError(409, 'GM_PLAN_MISMATCH', 'NPC plans come from the GM policy on the server, not from the client.')
                if not insp.get('validation') or not insp['validation']['legal']:
                    raise AtomicError(422, 'ILLEGAL_PLAN', json.dumps((insp.get('validation') or {}).get('reasons') or 'unknown actor')[:400])
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
            if self.engine and any(int(d['seq']) >= len(sess.tape) for d in dice):
                insp = self._inspect(sess)
                need = (insp.get('pending') or {}).get('need')
                if not need or insp['pending']['turn_key'] != turn_key:
                    raise AtomicError(409, 'NOT_NEEDED', 'The engine is not waiting for dice in this turn.')
                want = [{'seq': d['seq'], 'sides': d['sides']} for d in need['dice']]
                got = [{'seq': int(d['seq']), 'sides': int(d['sides'])} for d in dice if int(d['seq']) >= len(sess.tape)]
                if got != want:
                    raise AtomicError(409, 'NOT_NEEDED', 'The engine needs exactly ' + json.dumps(want) + '.')
                if roller != ('player' if need['controller'] == 'player' else 'gm'):
                    raise AtomicError(403, 'ROLLER_MISMATCH', 'These dice belong to ' + need['actor'] + ' (' + need['controller'] + ').')
                purpose = need['purpose'] or purpose
                identity = {'step': need.get('step'), 'rules': need.get('rules'), 'target': need.get('target'), 'kind': need.get('kind')}
            else:
                identity = {}
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
                       'roller': roller, 'actor': actor, 'turn_key': turn_key, 'purpose': purpose[:120], **identity}
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
            if self.engine:
                pz = ((self._inspect(sess) or {}).get('pending') or {}).get('paused')
                if not pz or pz['key'] != key or (self._inspect(sess)['pending']['turn_key'] != turn_key):
                    raise AtomicError(409, 'DECISION_NOT_PENDING', 'No such decision is waiting.')
                if pz['controller'] != 'player':
                    raise AtomicError(403, 'NOT_PLAYER_DECISION', 'The GM decides NPC reactions.')
                if choice is not None and choice not in pz['options']:
                    raise AtomicError(422, 'BAD_CHOICE', 'Choose one of ' + json.dumps(pz['options']) + ' or decline.')
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

    def complete(self, sid, turn_key, client_hash):
        """Server-side verification of a finished turn: the server's own reconstruction decides."""
        with self.lock:
            if not self.engine:
                raise AtomicError(503, 'ENGINE_UNAVAILABLE', 'Verification needs the server-side engine.')
            sess = self._load(sid)
            if turn_key in sess.verified:
                v = sess.verified[turn_key]
                if v['ok'] and v['client_hash'] == client_hash:
                    return {'verified': True, 'server_hash': v['server_hash'], 'duplicate': True}
            if turn_key not in sess.commits:
                raise AtomicError(409, 'NOT_COMMITTED', 'Unknown turn.')
            insp = self._inspect(sess)
            if insp.get('pending'):
                raise AtomicError(409, 'TURN_INCOMPLETE', 'The server is still waiting on ' + insp['pending']['turn_key'] + '.')
            if sess.active != turn_key:
                raise AtomicError(409, 'NOT_LATEST', 'Only the latest finished turn can be verified now.')
            ok = insp['hash'] == client_hash
            sess.verified[turn_key] = {'server_hash': insp['hash'], 'client_hash': client_hash, 'ok': ok}
            self._append(sess, {'op': 'verify', 'turn_key': turn_key, 'server_hash': insp['hash'], 'client_hash': client_hash, 'ok': ok})
            if not ok:
                raise AtomicError(409, 'STATE_MISMATCH', 'Your result differs from the server reconstruction (' + insp['hash'] + '). The server result stands.')
            return {'verified': True, 'server_hash': insp['hash'], 'over': insp.get('over')}

    def state(self, sid):
        """The server's authoritative reconstruction (sandbox: full state; a campaign must project it per viewer)."""
        with self.lock:
            if not self.engine:
                raise AtomicError(503, 'ENGINE_UNAVAILABLE', 'No server-side engine.')
            sess = self._load(sid)
            insp = self.engine.inspect(self._jobj(sess), {'actor': '', 'plan': [], 'want_state': True})
            return {'hash': insp['hash'], 'state': insp['state'], 'pending': insp.get('pending'), 'over': insp.get('over')}

    def abandon(self, sid):
        """A bound session can be abandoned only as a recorded forfeit; it never yields a fresh seed."""
        with self.lock:
            sess = self._load(sid)
            if not sess.closed:
                sess.closed = True
                self._append(sess, {'op': 'abandon', 'forfeit': sess.meta.get('mode') == 'bound'})
            return {'closed': True, 'forfeit': sess.meta.get('mode') == 'bound'}

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
            camp = b.get('campaign')
            if camp not in (None, 'starwars_litrpg'):
                return 400, {'error': 'BAD_CAMPAIGN', 'text': 'Unknown campaign overlay.'}
            return 200, service.open({'scenario': str(b.get('scenario', ''))[:40], 'switches': b.get('switches') or {}, 'campaign': camp},
                                     str(b.get('mode') or 'practice'), b.get('encounter_id'))
        if path == '/atomic/complete':
            return 200, service.complete(b['session'], str(b['turn_key']), str(b['state_hash']))
        if path == '/atomic/state':
            return 200, service.state(b['session'])
        if path == '/atomic/abandon':
            return 200, service.abandon(b['session'])
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
