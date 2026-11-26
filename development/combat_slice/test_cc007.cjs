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
// ---- C. Grapple basics (R-4; aero_character_runtime.yml Echani Grappling Training) ----
const win = (who) => (need, i, d) => { if (!/contest/.test(need.kind || "") && !/resists|holds against|Escape/.test(need.purpose || "")) return 1; return need.actor === who ? 19 : 2; };
function held(seed) { const b = E.newState(C, S, "duelist", { seed: seed || 7 }); b.dist["aero|ilsa"] = 5;
  const r = scripted(b, "aero", [{ pid: "grapple", target: "ilsa" }], win("aero")); return r.state; }
{ const b = E.newState(C, S, "duelist", { seed: 7 }); b.dist["aero|ilsa"] = 5;
  const av = (sz) => { const x = JSON.parse(JSON.stringify(b)); x.actors.ilsa.size = sz; return E.availability(x, "aero", "grapple", { pid: "grapple", target: "ilsa" }); };
  ok(av("large").ok, "size: one size larger can be grappled");
  ok(!av("huge").ok && av("huge").reasons.some((r) => r.code === "TOO_LARGE"), "size: two sizes larger is refused (TOO_LARGE)");
  ok(av(undefined).reasons.some((r) => r.code === "SIZE_UNKNOWN"), "size: missing size data refuses rather than guessing (SIZE_UNKNOWN)");
  const v = E.validatePlan(b, "aero", [{ pid: "grapple", target: "ilsa" }]); ok(v.legal && v.steps[0].cost.main === 1, "grapple costs the Main action (special melee attack, one attack per Main here)"); }
{ const s = held(); ok(s.actors.ilsa.conds.grappled && s.actors.aero.conds.grappling, "fixture: Aero holds Ilsa");
  ok(E.availability(s, "aero", "release_grapple", { pid: "release_grapple" }).ok && JSON.stringify(E.availability(s, "aero", "release_grapple", { pid: "release_grapple" }).cost) === "{}", "release is free (no budget)");
  const rel = E.resolveTurn(s, "aero", [{ pid: "release_grapple" }], {}).state; ok(!rel.actors.ilsa.conds.grappled && !rel.actors.aero.conds.grappling && rel.actors.aero.budget.main === s.actors.aero.budget.main, "releasing ends the hold and spends nothing");
  // drag: half speed
  const t0 = JSON.parse(JSON.stringify(s)); t0.actors.aero.budget.movement_ft = 30;
  const v = E.validatePlan(t0, "aero", [{ pid: "move", dest: "withdraw", drag: true }]); ok(v.legal && v.steps[0].cost.movement_ft === 30, "dragging costs double movement (15 ft withdraw → 30 ft)", v.steps[0]);
  const dr = E.resolveTurn(t0, "aero", [{ pid: "move", dest: "withdraw", drag: true }], {}).state;
  ok(!!dr.actors.ilsa.conds.grappled && !!dr.actors.aero.conds.grappling, "drag: the hold is kept");
  ok(dr.dist["aero|ilsa"] === 5 && dr.log.some((l) => l.ev === "drag") && !dr.log.some((l) => /opportunity/.test(l.text || "")), "drag: the held creature stays adjacent and provokes no opportunity attack", dr.dist);
  const t1 = JSON.parse(JSON.stringify(s)); t1.actors.aero.budget.movement_ft = 10;
  ok(!E.validatePlan(t1, "aero", [{ pid: "move", dest: "withdraw", drag: true }]).legal, "drag needs the doubled movement (10 ft left: refused)");
  const nd = scripted(s, "aero", [{ pid: "move", dest: "withdraw" }], () => 1).state;   // leaving reach provokes Ilsa's opportunity attack
  ok(!nd.actors.ilsa.conds.grappled && nd.log.some((l) => l.ev === "release" && l.why === "moved"), "moving without drag releases the hold");
  const fresh = E.newState(C, S, "duelist", { seed: 7 }); ok(E.validatePlan(fresh, "aero", [{ pid: "move", dest: "withdraw", drag: true }]).steps[0].reasons.some((r) => r.code === "NOT_GRAPPLING"), "drag without a hold is refused (NOT_GRAPPLING)"); }
{ // escape contest on Ilsa's turn: NPC policy tries to escape; tie keeps the hold; a win breaks it; it costs her Main
  let s = E.endTurn(held());
  ok(JSON.stringify(E.npcPlan(s, "ilsa")) === JSON.stringify([{ pid: "escape_grapple" }]), "a held NPC spends its action trying to escape");
  let aTot; const tie = scripted(s, "ilsa", [{ pid: "escape_grapple" }], (need) => { if (need.actor === "ilsa") { aTot = 10 + mod(need.formula); return 10; } return aTot - mod(need.formula); });
  const c = tie.state.log.find((l) => l.pid === "escape_grapple"); ok(c && c.a === c.t && tie.state.actors.ilsa.conds.grappled, "escape tie goes to the grappler (R-1)", c);
  ok(tie.state.actors.ilsa.budget.main === 0, "escape spends the escaper's Main action");
  const out = scripted(s, "ilsa", [{ pid: "escape_grapple" }], win("ilsa")).state;
  ok(!out.actors.ilsa.conds.grappled && !out.actors.aero.conds.grappling, "winning the escape ends the hold for both sides");
  const r = out.receipts.filter((x) => x.kind === "contest").slice(-2); ok(r.length === 2 && r[1].formula === "1d20+5", "escape is opposed by the grappler's grapple check (+5)", r.map((x) => x.formula)); }
{ // release conditions: the held creature going down; the grappler going down
  let s = E.endTurn(held()); s = E.endTurn(E.resolveTurn(s, "ilsa", [], {}).state);   // Aero's next turn, still holding
  s.actors.ilsa.hp = 1; s.actors.ilsa.ac = 1;
  const k = scripted(s, "aero", [{ pid: "unarmed_strike", target: "ilsa" }], (need, i, d) => need.actor === "aero" ? (d.sides === 20 ? 15 : 4) : 1).state;
  ok(k.actors.ilsa.down && !k.actors.aero.conds.grappling && k.log.some((l) => l.ev === "release" && l.why === "target_down"), "the hold ends when the held creature goes down");
  const g = held(); g.actors.aero.down = true; const e = E.endTurn(g); ok(!e.actors.aero.conds.grappling && !e.actors.ilsa.conds.grappled, "the hold ends when the grappler goes down"); }
{ const s = held(); const e = E.endTurn(s); ok(!E.availability(e, "ilsa", "move", { pid: "move", dest: "withdraw" }).ok, "the held creature's speed is 0");
  ok(E.availability(s, "aero", "escape_grapple", { pid: "escape_grapple" }).reasons.some((r) => r.code === "NEEDS_GRAPPLED"), "you can only escape while grappled"); }
// ---- D. Sentinel Balance: 2 uses per long rest (sheet), spend and recharge ----
function burstOnAero(state, choices, saveTotal, d4) {   // Ilsa (given Burst for the test) forces Aero's DEX save
  const s = JSON.parse(JSON.stringify(state)); if (s.actors.ilsa.profiles.indexOf("burst") < 0) s.actors.ilsa.profiles.push("burst"); s.dist["aero|ilsa"] = 5; s.turn = s.order.indexOf("ilsa");
  s.actors.ilsa.budget.main = 1; s.actors.aero.down = false;
  return scripted(s, "ilsa", [{ pid: "burst" }], (need, i, d) => need.actor === "aero" && d.sides === 20 ? saveTotal - mod(need.formula) : d.sides === 4 && need.actor === "aero" ? d4 : 1, choices);
}
{ const s0 = E.newState(C, S, "duelist", { seed: 7 });
  ok(s0.actors.aero.resources.sentinel_balance.current === 2 && s0.actors.aero.resources.sentinel_balance.max === 2, "starts at 2/2 from the sheet");
  const p = burstOnAero(s0, {}, 10, 4); ok(p.paused && p.paused.kind === "failed_dex_or_cha_save" && p.paused.options.includes("sentinel_balance"), "a failed DEX save offers Sentinel Balance (player decision)", p.paused);
  const used = burstOnAero(s0, { [p.paused.key]: "sentinel_balance" }, 10, 4).state, a = used.actors.aero;
  ok(a.resources.sentinel_balance.current === 1 && a.reaction_left === 0, "using it spends one use and the reaction");
  ok(used.log.some((l) => l.ev === "sentinel_balance" && l.total === 14 && l.win) && used.log.some((l) => l.ev === "save" && l.actor === "aero" && l.win), "+1d4 can turn the failure into a success (10 + 4 ≥ DC 12)");
  ok(!used.log.some((l) => l.ev === "damage" && l.target === "aero"), "success after Sentinel Balance: no damage, not prone");
  const miss = burstOnAero(s0, { [p.paused.key]: "sentinel_balance" }, 7, 2).state; ok(miss.log.some((l) => l.ev === "sentinel_balance" && !l.win) && miss.log.some((l) => l.ev === "damage" && l.target === "aero"), "if +1d4 isn't enough the failure stands");
  const dec = burstOnAero(s0, { [p.paused.key]: null }, 10, 4).state; ok(dec.actors.aero.resources.sentinel_balance.current === 2 && dec.actors.aero.reaction_left === 1, "declining spends nothing");
  const pass = burstOnAero(s0, {}, 15, 4); ok(!pass.paused && !pass.state.log.some((l) => l.ev === "sentinel_balance"), "a successful save offers nothing (cannot affect successful saves)");
  // spend both uses, then none is offered
  let t = JSON.parse(JSON.stringify(used)); t.actors.aero.reaction_left = 1;
  const p2 = burstOnAero(t, {}, 10, 4); const u2 = burstOnAero(t, { [p2.paused.key]: "sentinel_balance" }, 10, 4).state;
  ok(u2.actors.aero.resources.sentinel_balance.current === 0, "second use leaves 0/2");
  let z = JSON.parse(JSON.stringify(u2)); z.actors.aero.reaction_left = 1; const p3 = burstOnAero(z, {}, 10, 4);
  ok(!p3.paused && !p3.state.log.slice(z.log.length).some((l) => l.ev === "sentinel_balance"), "with no uses left it is not offered");
  const nr = JSON.parse(JSON.stringify(s0)); nr.actors.aero.reaction_left = 0; ok(!burstOnAero(nr, {}, 10, 4).paused, "not offered without a reaction");
  ok(E.rest(u2, "aero", "short_rest").actors.aero.resources.sentinel_balance.current === 0, "a short rest does not recharge it");
  const lr = E.rest(u2, "aero", "long_rest"); ok(lr.actors.aero.resources.sentinel_balance.current === 2 && lr.log.some((l) => l.ev === "rest_recover"), "a long rest recharges it to 2/2");
  // replay determinism: the same choice and tape give the same state
  const r1 = burstOnAero(s0, { [p.paused.key]: "sentinel_balance" }, 10, 4).state, r2 = burstOnAero(s0, { [p.paused.key]: "sentinel_balance" }, 10, 4).state;
  ok(JSON.stringify(r1) === JSON.stringify(r2), "replaying the same decision and dice is identical"); }
console.log(fails ? fails + " FAILED" : "all " + n + " passed"); process.exit(fails ? 1 : 0);
}
