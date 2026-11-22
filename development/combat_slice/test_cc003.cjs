// CC-003 tests: probabilities, synergy recognition, compound costs, prone, enemy-HP debug view, Soul narration
// safety, RNG uniformity and reproducible balance. node test_cc003.cjs
const assert = require("assert");
const E = require("./engine.js"), P = require("./predict.js"), N = require("./soul.js");
const C = require("./catalog.json"), S = require("./scenarios.json");
let pass = 0, fail = 0;
function t(name, fn) { try { fn(); pass++; console.log("ok", name); } catch (e) { fail++; console.log("FAIL", name, "\n  ", e.message); } }
const near = (a, b, eps, m) => assert(Math.abs(a - b) <= eps, (m || "") + " " + a + " vs " + b);
function duel(seed) { const s = E.newState(C, S, "duelist", { seed }); s.dist["aero|ilsa"] = 5; return s; }
function play(s, actor, plan, pol) { let ch = {}, r; for (let g = 0; g < 12; g++) { r = E.resolveTurn(s, actor, plan, ch); if (!r.paused) break; const c = pol ? pol(r.paused) : null; ch[r.paused.key] = r.paused.options.includes(c) ? c : null; } return r; }

// ---- exact math ----
t("d20 distributions sum to 1 and advantage P(>=11) = 75%", () => {
  ["normal", "advantage", "disadvantage"].forEach((m) => near(P.d20(m).reduce((a, b) => a + b, 0), 1, 1e-12, m));
  near(P.d20("advantage").slice(11).reduce((a, b) => a + b, 0), 0.75, 1e-12); near(P.d20("disadvantage").slice(11).reduce((a, b) => a + b, 0), 0.25, 1e-12);
});
t("attack odds: +5 vs AC 15 = 55% (nat 1 misses, nat 20 crits); Parry +2 turns 10% of hits", () => {
  const a = P.attackOdds(5, 15, "normal"); near(a.hit, 0.55, 1e-12); near(a.crit, 0.05, 1e-12);
  const b = P.attackOdds(5, 15, "normal", { parry: 2 }); near(b.hit, 0.45, 1e-12); near(b.parried, 0.10, 1e-12);
  near(P.attackOdds(5, 40, "normal").hit, 0.05, 1e-12, "nat 20 always hits"); near(P.attackOdds(30, 2, "normal").hit, 0.95, 1e-12, "nat 1 always misses");
});
t("damage ranges: 1d8+3 is 4..11 mean 7.5; critical doubles dice (5..19, mean 12)", () => {
  const d = P.damage("1d8+3"); assert.deepStrictEqual([d.min, d.max], [4, 11]); near(d.mean, 7.5, 1e-9);
  const c = P.damage("1d8+3", true); assert.deepStrictEqual([c.min, c.max], [5, 19]); near(c.mean, 12, 1e-9);
});
t("contest: equal modifiers, ties to defender → 47.5%", () => near(P.contestOdds(0, false, 0, false), 0.475, 1e-12));
t("exact predictions match the real engine empirically (saber vs Ilsa, feint, Force-guided)", () => {
  const s0 = duel(1), str = JSON.stringify(s0), n = 4000;
  const cases = [[[{ pid: "saber_strike", target: "ilsa" }], 0], [[{ pid: "feint", target: "ilsa" }], 0], [[{ pid: "saber_strike", target: "ilsa", augment: true }], 0]];
  cases.forEach(([plan, ix]) => {
    const pred = P.analyzePlan(s0, "aero", plan).steps[ix], exp = pred.kind === "attack" ? pred.hit : pred.success; let k = 0;
    for (let i = 0; i < n; i++) { const c = JSON.parse(str); c.rng.seed = 90000 + i; const r = play(c, "aero", plan);
      if (pred.kind === "attack" ? r.log.some((l) => l.ev === "damage" && l.attacker === "aero") : r.log.some((l) => l.ev === "contest" && l.win)) k++; }
    near(k / n, exp, 3 * Math.sqrt(exp * (1 - exp) / n) + 0.005, plan[0].pid + (plan[0].augment ? "+aug" : ""));
  });
});
t("feint → strike: conditional hit chance = P(feint)·P(hit|adv) + (1−P)·P(hit)", () => {
  const s = duel(2), a = P.analyzePlan(s, "aero", [{ pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }]).steps;
  const pf = a[0].success; near(a[1].hit, pf * a[1].if_feint_wins + (1 - pf) * a[1].if_feint_fails, 1e-12); assert(a[1].if_feint_wins > a[1].if_feint_fails);
});
t("predictions never consume or change authoritative dice, receipts or state", () => {
  const s = duel(3), before = JSON.stringify(s), plan = [{ pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }];
  P.analyzePlan(s, "aero", plan); const sim = P.simulate(s, "aero", plan, { n: 200 }); P.defenseOdds(s, "ilsa", "aero", "npc_blade");
  assert.strictEqual(JSON.stringify(s), before); assert.strictEqual(sim.authoritative_dice_used, false);
  const r1 = play(s, "aero", plan), r2 = play(JSON.parse(before), "aero", plan); assert.deepStrictEqual(r1.receipts, r2.receipts);
});
t("simulation is reproducible and labels its sample count and interval", () => {
  const s = duel(4), plan = [{ pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }];
  const a = P.simulate(s, "aero", plan, { n: 300 }), b = P.simulate(s, "aero", plan, { n: 300 });
  assert.deepStrictEqual(a, b); assert.strictEqual(a.samples, 300); assert(a.full_combo.lo <= a.full_combo.p && a.full_combo.p <= a.full_combo.hi);
  assert.strictEqual(P.simulate(s, "aero", [{ pid: "flow_strike", target: "ilsa" }]), null, "no simulation for an illegal plan");
});
t("narrative assessment is words only", () => assert(!/\d/.test(P.assess(0.62))));

// ---- synergy ----
t("Echani Flow Line recognized for Feint → Lightsaber Strike → Flow Strike, grounded in profile rules", () => {
  const s = duel(5), sy = E.synergies(s, "aero", [{ pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }]);
  assert.deepStrictEqual(sy.map((x) => x.id), ["echani_flow_line"]); assert(sy[0].legal); assert(sy[0].basis.length && /only if/i.test(sy[0].conditional));
});
t("no synergy for unrelated or illegal sequences; illegal links are flagged", () => {
  const s = duel(6); assert.deepStrictEqual(E.synergies(s, "aero", [{ pid: "feint", target: "ilsa" }]), []);
  const s2 = duel(6); s2.dist["aero|ilsa"] = 20; const sy = E.synergies(s2, "aero", [{ pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }]);
  assert.strictEqual(sy[0].legal, false);
});
t("every synergy references only profiles that exist in the catalog", () => {
  C.synergies.forEach((sy) => sy.sequence.forEach((st) => [].concat(st.pid).forEach((pid) => assert(C.profiles[pid], sy.id + ": " + pid))));
});

// ---- compound cost, prone, debug view ----
t("Blade Bind & Takedown consumes 1 Main + 1 Secondary; a strike after it is refused NO_MAIN", () => {
  const s = duel(7), p = C.profiles.controlled_takedown; assert.deepStrictEqual(p.cost, { main: 1, secondary: 1 }); assert(p.compound);
  const v = E.validatePlan(s, "aero", [{ pid: "controlled_takedown", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }]);
  assert(v.steps[0].ok); assert(v.steps[1].reasons.some((r) => r.code === "NO_MAIN"));
  const off = E.newState(C, S, "duelist", { seed: 7, switches: { secondary_action: false } }); off.dist["aero|ilsa"] = 5;
  assert(E.validatePlan(off, "aero", [{ pid: "controlled_takedown", target: "ilsa" }]).steps[0].reasons.some((r) => r.code === "SA001_DISABLED"));
});
t("prone: advantage on melee against it, disadvantage on its attacks, stands for 15 ft at its turn start", () => {
  const s = duel(8); s.actors.ilsa.conds.prone = { by: "aero" };
  const p = C.profiles.saber_strike; assert(E.hasAdv(s, "aero", "ilsa", p, {}).adv.includes("prone target"));
  assert(E.hasAdv(s, "ilsa", "aero", C.profiles.npc_blade, {}).dis.includes("attacking from the ground"));
  let s2 = E.endTurn(s); assert.strictEqual(E.current(s2), "ilsa"); assert(!s2.actors.ilsa.conds.prone); assert.strictEqual(s2.actors.ilsa.budget.movement_ft, C.ruleset.budget.movement_ft - 15);
});
t("a won takedown leaves the target disarmed and prone (found by seed search, not forced)", () => {
  let found = false; for (let seed = 1; seed < 60 && !found; seed++) { const s = duel(seed), r = play(s, "aero", [{ pid: "controlled_takedown", target: "ilsa" }]);
    if (r.log.some((l) => l.ev === "takedown")) { found = true; const I = r.state.actors.ilsa; assert(I.conds.prone && I.dropped && !I.weapon.held); } }
  assert(found);
});
t("full-mechanics view shows enemy HP/AC; the default view still hides them; hidden actors stay hidden", () => {
  const s = duel(9); assert.strictEqual(E.publicView(s, "aero").actors.ilsa.hp, null);
  const v = E.publicView(s, "aero", { full_mechanics: true }); assert.strictEqual(v.actors.ilsa.hp, 20); assert.strictEqual(v.actors.ilsa.ac, 15);
  const p = E.newState(C, S, "predator", { seed: 1 }); assert(!E.publicView(p, "aero", { full_mechanics: true }).actors.stalker);
});

// ---- Soul ----
function turnLog(seed) { const s = duel(seed); return play(s, "aero", [{ pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }], () => "parry"); }
t("Soul narration leaves log, receipts and state untouched and hands out frozen facts only", () => {
  const r = turnLog(10), before = JSON.stringify(r); const out = N.narrate(r.log, { aero: "Aero", ilsa: "Ilsa Vohr" });
  assert.strictEqual(JSON.stringify(r), before); assert(Object.isFrozen(out.facts) && Object.isFrozen(out.facts[0]));
  assert(out.beats.length > 0 && out.source === "deterministic fallback");
  assert.throws(() => { "use strict"; out.facts[0].amount = 99; });
});
t("every damage number Soul writes comes from an accepted damage event", () => {
  for (let seed = 11; seed < 40; seed++) { const r = turnLog(seed), out = N.narrate(r.log, { aero: "Aero", ilsa: "Ilsa Vohr" }); const ok = new Set(out.facts.filter((f) => f.amount != null).map((f) => String(f.amount)));
    out.beats.forEach((b) => (b.text.match(/\d+/g) || []).forEach((n) => assert(ok.has(n), "seed " + seed + ": " + b.text))); }
});
t("an AI provider's text is shown only if it invents no numbers; failures fall back", async () => {
  const r = turnLog(12), F = N.facts(r.log, {}); const dmg = F.find((f) => f.amount != null);
  assert(!N.guard("Ilsa staggers back, but strikes for 99.", F).ok);
  if (dmg) assert(N.guard("The blade lands for " + dmg.amount + ".", F).ok);
});

// ---- RNG + balance (reproducible) ----
t("RNG audit: chi-square uniformity and advantage means within tolerance", () => {
  const out = JSON.parse(require("child_process").execFileSync("node", [__dirname + "/audit/rng_audit.cjs", "--json"], { encoding: "utf8" }));
  assert(out.single_stream.chi2_df19 < out.single_stream.critical_999 && out.single_stream.uniform);
  assert(out.across_seeds.uniform); near(out.across_seeds.neighbour_equal_rate, 0.05, 0.01);
  near(out.advantage.adv_mean, out.advantage.adv_expected, 0.1); near(out.advantage.dis_mean, out.advantage.dis_expected, 0.1);
  near(out.single_stream.lag1_autocorrelation, 0, 0.01);
});
t("balance simulation is deterministic and the baseline duel is the hard outlier (sandbox evidence)", () => {
  const B = require("./audit/balance_sim.cjs"); B.setN(150);
  const a = B.runAll(), b = B.runAll(); assert.deepStrictEqual(a, b);
  const get = (lbl) => a.find((r) => r.label.startsWith(lbl)).win_rate;
  assert(get("Baseline duel (simple") < 30, "baseline simple duel is hard"); assert(get("P1") > get("Baseline duel (tactical"), "intro proposal is easier");
});

setTimeout(() => { console.log(fail ? `${fail} FAILED, ${pass} passed` : `all ${pass} passed`); process.exit(fail ? 1 : 0); }, 50);
