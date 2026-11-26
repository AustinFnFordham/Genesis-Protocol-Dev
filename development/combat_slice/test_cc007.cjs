// CC-007: approved correctness fixes (owner rulings CC007_OWNER_RULINGS.md, sandbox only).
const E = require("./engine.js"), C = require("./catalog.json"), S = require("./scenarios.json");
let fails = 0, n = 0; const ok = (c, m, x) => { n++; console.log((c ? "ok " : "FAIL ") + m + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 300))); if (!c) fails++; };
const run = (s, who, plan) => E.resolveTurn(s, who, plan, {});
function feintWon(extra) {   // first seed where Aero closes, feints and wins (optionally followed by more steps)
  for (let seed = 1; seed < 2000; seed++) {
    let s = E.newState(C, S, "duelist", { seed }); const r = run(s, "aero", [{ pid: "move", dest: "close", target: "ilsa" }, { pid: "feint", target: "ilsa" }].concat(extra || []));
    if (!r.state || r.paused || r.need_dice) continue;
    const won = r.state.log.some((l) => l.ev === "feinted"); if (won) return { seed, s: r.state };
  }
}
module.exports.feintWon = feintWon;
if (require.main === module) {
// ---- A. Feint expiry ----
{ const f = feintWon(); ok(!!f, "fixture: a won feint exists");
  ok(!!f.s.actors.ilsa.conds.feinted, "unused feint is live during the feinter's own turn");
  let s = E.endTurn(f.s); ok(!s.actors.ilsa.conds.feinted, "unused feint lapses at the end of the feinter's turn (X-1 regression)", s.actors.ilsa.conds);
  ok(s.log.some((l) => l.ev === "feint_lapsed" && l.target === "ilsa"), "the lapse is a logged event");
  // across the boundary: Ilsa's turn, then Aero's next turn has no feint advantage
  const r2 = run(s, "ilsa", []); s = E.endTurn(r2.state || s);
  ok(E.current(s) === "aero" && !s.actors.ilsa.conds.feinted, "no feint carried into the feinter's next turn");
  // reproduction from the audit, verbatim seed 1
  let s1 = E.newState(C, S, "duelist", { seed: 1 }); const a = run(s1, "aero", [{ pid: "move", dest: "close", target: "ilsa" }, { pid: "feint", target: "ilsa" }]);
  if (a.state && a.state.actors.ilsa.conds.feinted) { let t = E.endTurn(a.state); t = E.endTurn((run(t, "ilsa", []).state) || t); ok(!t.actors.ilsa.conds.feinted, "audit reproduction (seed 1) no longer carries over"); } }
{ // used feint: consumed by the strike, gives advantage that turn
  const f = feintWon([{ pid: "saber_strike", target: "ilsa" }]); ok(!!f, "fixture: feint then strike");
  const atk = f.s.receipts.filter((r) => r.kind === "attack" && r.actor === "aero").pop();
  ok(atk && atk.mode === "advantage", "used feint gives advantage on the same-turn strike", atk && atk.mode);
  ok(!f.s.actors.ilsa.conds.feinted, "used feint is consumed by that strike"); }
console.log(fails ? fails + " FAILED" : "all " + n + " passed"); process.exit(fails ? 1 : 0);
}
