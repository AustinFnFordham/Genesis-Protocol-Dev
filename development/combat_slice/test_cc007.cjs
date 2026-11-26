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
// Scripted dice: atomic mode, every die chosen by pick(need, i). Returns the finished state (or the pause).
function scripted(s0, who, plan, pick, opts) {
  let s = JSON.parse(JSON.stringify(s0)); s.rng.mode = "atomic"; s.tape = s.tape || {}; const needs = [];
  for (let k = 0; k < 60; k++) {
    const r = E.resolveTurn(s, who, plan, opts || {});
    if (!r.need_dice) return Object.assign(r, { needs });
    needs.push(r.need_dice); r.need_dice.dice.forEach((d, i) => { s.tape[d.seq] = { seq: d.seq, sides: d.sides, value: pick(r.need_dice, i, d) }; });
  }
  throw new Error("dice loop");
}
const mod = (f) => { const m = /([+-]\d+)$/.exec(f || ""); return m ? +m[1] : 0; };
module.exports.scripted = scripted;

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
// ---- B. R-1: natural 20, Parry, contest ties (verifying existing behaviour) ----
{ const base = E.newState(C, S, "duelist", { seed: 7 }); base.dist["aero|ilsa"] = 5;
  const r = scripted(base, "aero", [{ pid: "saber_strike", target: "ilsa" }], (need, i, d) => need.actor === "aero" && d.sides === 20 ? 20 : 1);
  const st = r.state, atk = st.receipts.find((x) => x.kind === "attack" && x.actor === "aero"), dmg = st.receipts.find((x) => x.kind === "damage" && x.actor === "aero");
  ok(atk && atk.kept === 20 && st.log.some((l) => l.ev === "attack" && l.crit), "natural 20 is a critical hit", atk);
  ok(dmg && dmg.rolls.length === 2 && dmg.total === 2 + 3, "critical doubles the damage dice (1d8+3 → 2d8+3), modifier not doubled", dmg);
  ok(!st.log.some((l) => l.ev === "parry"), "Parry is not used against a critical hit", st.log.map((l) => l.ev));
  // same strike, not a crit, a hit Ilsa can parry: d20 such that total = AC (hit by exactly 0)
  const ac = base.actors.ilsa.ac, r2 = scripted(base, "aero", [{ pid: "saber_strike", target: "ilsa" }], (need, i, d) => need.actor === "aero" && d.sides === 20 ? ac - 5 : 1);
  ok(r2.state.log.some((l) => l.ev === "parry"), "Parry is available against an ordinary hit (control)", r2.state.log.map((l) => l.ev)); }
{ // natural 1 always misses even with a huge bonus; natural 20 always hits
  const base = E.newState(C, S, "duelist", { seed: 7 }); base.dist["aero|ilsa"] = 5; base.actors.ilsa.ac = 2;
  const r = scripted(base, "aero", [{ pid: "saber_strike", target: "ilsa" }], (need, i, d) => d.sides === 20 && need.actor === "aero" ? 1 : 1);
  const L = r.state.log, i = L.findIndex((l) => l.ev === "attack");
  ok(i >= 0 && L[i + 1] && L[i + 1].ev === "miss" && !L.slice(0, L.findIndex((l) => l.ev === "riposte")).some((l) => l.ev === "damage"), "natural 1 misses even against AC 2", L.slice(i, i + 2)); }
for (const pid of ["feint", "blade_bind", "grapple"]) {   // defender wins ties, in every contest
  const base = E.newState(C, S, "duelist", { seed: 7 }); base.dist["aero|ilsa"] = 5; let aTot = null;
  const r = scripted(base, "aero", [{ pid, target: "ilsa" }], (need, i, d) => { if (need.kind !== "contest" && !/resists/.test(need.purpose || "")) return 1;
    if (need.actor === "aero") { aTot = 10 + mod(need.formula); return 10; } return aTot - mod(need.formula); });
  const c = r.state.log.find((l) => l.ev === "contest");
  ok(c && c.a === c.t && /fails/.test(c.text), pid + ": a tied contest goes to the defender", c); }
console.log(fails ? fails + " FAILED" : "all " + n + " passed"); process.exit(fails ? 1 : 0);
}
