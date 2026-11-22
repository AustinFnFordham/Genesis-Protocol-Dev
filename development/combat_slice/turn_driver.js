// Genesis CC-004 turn driver: runs a declared turn through the engine and obtains EVERY die from an Atomic authority.
// The engine pauses with need_dice / paused; the driver asks Atomic (player dice wait for the player's Roll button,
// GM dice are requested by the GM side), appends accepted dice to the tape, and re-runs the same turn from the same
// snapshot. Nothing here invents a die. Reconnect = fetch the journal and replay (no reroll, identical state).
(function (root, factory) { if (typeof module === "object" && module.exports) module.exports = factory(require("./engine.js")); else root.GenesisDriver = factory(root.GenesisCombat); })(this, function (E) {
  "use strict";
  function clone(x) { return JSON.parse(JSON.stringify(x)); }
  function turnKey(s) { return "R" + s.round + ".T" + s.turn + "." + E.current(s); }

  // ---- Atomic over HTTP (the preview server's /atomic/* routes). Retries are safe: every call is idempotent. ----
  function HttpAtomic(base, fetchImpl) {
    var f = fetchImpl || (typeof fetch !== "undefined" ? fetch.bind(typeof window !== "undefined" ? window : globalThis) : null);
    function call(path, body, tries) {
      tries = tries == null ? 3 : tries;
      return f(base + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
        .then(function (r) { return r.json().then(function (j) { if (r.status >= 400) { var e = new Error(j.text || j.error); e.code = j.error; e.status = r.status; throw e; } return j; }); })
        .catch(function (e) { if (!e.status && tries > 1) return new Promise(function (res) { setTimeout(res, 300); }).then(function () { return call(path, body, tries - 1); }); throw e; });
    }
    return { authority: "atomic-sandbox", authoritative: true,
      open: function (meta) { return call("/atomic/open", meta); },
      commit: function (sid, tk, actor, plan) { return call("/atomic/commit", { session: sid, turn_key: tk, actor: actor, plan: plan }); },
      roll: function (sid, tk, ph, dice, roller, actor, purpose) { return call("/atomic/roll", { session: sid, turn_key: tk, plan_hash: ph, dice: dice, roller: roller, actor: actor, purpose: purpose }); },
      decide: function (sid, tk, key, choice) { return call("/atomic/decide", { session: sid, turn_key: tk, key: key, choice: choice }); },
      journal: function (sid) { return call("/atomic/journal", { session: sid }); },
      complete: function (sid, tk, hash) { return call("/atomic/complete", { session: sid, turn_key: tk, state_hash: hash }); },
      state: function (sid) { return call("/atomic/state", { session: sid }); } };
  }
  // ---- Offline practice dice: same protocol, in the page. NOT authoritative; the UI says so. ----
  function OfflineAtomic() {
    var seed = (typeof crypto !== "undefined" && crypto.getRandomValues) ? crypto.getRandomValues(new Uint32Array(1))[0] >>> 1 : Math.floor(Math.random() * 2147483647);
    var tape = [], commits = {}, decisions = {};
    function die(n, sides) { return E._localDie(seed, n, sides); }
    function h(p) { return JSON.stringify(p); }
    return { authority: "offline-practice", authoritative: false,
      open: function () { return Promise.resolve({ session: "offline" }); },
      commit: function (sid, tk, actor, plan) { var c = commits[tk]; if (c && c.h !== h(plan) && c.locked) return Promise.reject(Object.assign(new Error("PLAN_LOCKED"), { code: "PLAN_LOCKED" })); commits[tk] = c && c.h === h(plan) ? c : { h: h(plan), locked: false }; return Promise.resolve({ plan_hash: h(plan) }); },
      roll: function (sid, tk, ph, dice, roller) { var out = dice.map(function (d) { if (d.seq < tape.length) return tape[d.seq]; var r = { seq: d.seq, sides: d.sides, value: die(d.seq, d.sides), roll_id: "offline:" + d.seq, roller: roller }; tape.push(r); return r; }); commits[tk].locked = true; return Promise.resolve({ dice: out }); },
      decide: function (sid, tk, key, choice) { decisions[tk + "|" + key] = choice; return Promise.resolve({ choice: choice }); },
      journal: function () { return Promise.resolve({ tape: tape, commits: [], decisions: [] }); },
      complete: function () { return Promise.resolve({ verified: false, offline: true }); } };
  }

  // runTurn: resolve one actor's turn to completion. hooks:
  //   playerRoll(need) -> Promise   (resolves when the player presses Roll; the driver then asks Atomic)
  //   gmRoll(need)     -> Promise   (presentation pacing for GM dice; may resolve immediately)
  //   decide(paused, preview) -> Promise<choice|null>  (player reaction decisions)
  //   onDice(accepted, need)        (each accepted batch, for the Roll Theater)
  // The NPC reaction policy stays inside the engine (GM decides GM reactions); the PC's are always the player's.
  function runTurn(ctx, state, actor, plan, hooks) {
    hooks = hooks || {};
    var at = ctx.atomic, sid = ctx.session, tk = turnKey(state), choices = Object.assign({}, hooks.choices || {}), ph = null, s = state;
    return at.commit(sid, tk, actor, plan).then(function (c) { ph = c.plan_hash; return loop(); });
    function loop() {
      var r = E.resolveTurn(s, actor, plan, choices);
      if (hooks.onProgress) hooks.onProgress(r, s);
      if (r.refused) return Promise.resolve({ refused: r.refused, state: s });
      if (r.need_dice) {
        var need = r.need_dice, mine = s.actors[need.actor] && s.actors[need.actor].controller === "player";
        var want = need.dice.filter(function (d) { return !s.tape[d.seq]; });
        var gate = mine ? (hooks.playerRoll ? hooks.playerRoll(need, r) : Promise.resolve()) : (hooks.gmRoll ? hooks.gmRoll(need, r) : Promise.resolve());
        return gate.then(function () { return at.roll(sid, tk, ph, want, mine ? "player" : "gm", need.actor, need.purpose); })
          .then(function (res) { s = E.acceptDice(s, res.dice); if (hooks.onDice) hooks.onDice(res.dice, need, s); return loop(); });
      }
      if (r.paused) {
        var p = r.paused, pc = s.actors[p.actor] && s.actors[p.actor].controller === "player";
        if (!pc) return Promise.reject(new Error("engine paused for a non-player decision"));
        return (hooks.decide ? hooks.decide(p, r) : Promise.resolve(null)).then(function (choice) {
          choice = p.options.indexOf(choice) >= 0 ? choice : null;
          return at.decide(sid, tk, p.key, choice).then(function (d) { choices[p.key] = d.choice; return loop(); });
        });
      }
      var done = E.endTurn(r.state), out = { state: done, log: r.log, receipts: r.receipts, tape: s.tape, turn_key: tk };
      if (!at.complete) return Promise.resolve(out);
      return at.complete(sid, tk, stateHash(done)).then(function (v) { out.verification = v; return out; }, function (e) {
        if (e.code !== "STATE_MISMATCH" || !at.state) throw e;
        // The server's reconstruction is authoritative: adopt it and report the divergence instead of the client's result.
        return at.state(sid).then(function (st) { out.state = st.state; out.verification = { verified: false, tamper: true, server_hash: st.hash, error: e.message }; return out; });
      });
    }
  }

  // replay(journal): rebuild the exact state from the Atomic journal (commits in order, decisions, accepted tape).
  // Pure and synchronous. Any divergence (a die the journal doesn't have, a turn out of order) throws.
  function replay(catalog, scenarios, journal) {
    var m = journal.meta || {}, s = E.newState(catalog, scenarios, m.scenario, { atomic: true, switches: m.switches || {} });
    s = E.acceptDice(s, journal.tape || []);
    var dec = {}; (journal.decisions || []).forEach(function (d) { dec[d.turn_key + "|" + d.key] = d.choice; });
    var commits = journal.commits || [];
    for (var i = 0; i < commits.length; i++) {
      var c = commits[i];
      if (c.turn_key !== turnKey(s)) throw new Error("REPLAY_ORDER: journal turn " + c.turn_key + " but state is at " + turnKey(s));
      var ch = {}, r;
      for (var g = 0; g < 32; g++) {
        r = E.resolveTurn(s, c.actor, c.plan, ch);
        if (r.paused) { var k = c.turn_key + "|" + r.paused.key; if (!(k in dec)) return { state: s, pending: { turn_key: c.turn_key, plan: c.plan, actor: c.actor, choices: ch, paused: r.paused } }; ch[r.paused.key] = dec[k]; continue; }
        break;
      }
      if (r.need_dice) return { state: s, pending: { turn_key: c.turn_key, plan: c.plan, actor: c.actor, choices: ch, need_dice: r.need_dice } };
      if (r.refused) throw new Error("REPLAY_REFUSED at " + c.turn_key);
      s = E.endTurn(r.state);
    }
    return { state: s, pending: null };
  }
  function stateHash(s) { var x = clone(s); delete x.catalog; var str = JSON.stringify(x), h = 2166136261; for (var i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0).toString(16); }
  return { HttpAtomic: HttpAtomic, OfflineAtomic: OfflineAtomic, runTurn: runTurn, replay: replay, turnKey: turnKey, stateHash: stateHash };
});
