// SA-001 Secondary Activity study (CC-007 §3). Sandbox only, noncanonical. Every fight runs through the real engine with
// seeded local dice; nothing is adjusted. Three candidate rules are compared on the same seeds:
//   A  "SA-001 on"   : the current sandbox: one Secondary per turn, in addition to Main/Bonus/Reaction/Move/Object.
//   B  "SA-001 off"  : the live turn contract: no Secondary; Secondary-cost profiles unavailable.
//   C  "as Bonus"    : no Secondary budget; the same activities cost a Bonus action (so they compete with Flow Strike).
// node audit/sa001_sim.cjs [N] [--json]
const E = require("../engine.js"), C0 = require("../catalog.json"), S = require("../scenarios.json");
const N = +(process.argv.find((a) => /^\d+$/.test(a)) || 2000), clone = (x) => JSON.parse(JSON.stringify(x));
function catalogFor(rule) {
  const c = clone(C0); if (rule !== "C") return c;
  Object.values(c.profiles).forEach((p) => { if (p.cost && p.cost.secondary) { delete p.cost.secondary; p.cost.bonus = (p.cost.bonus || 0) + 1; if (p.requires) delete p.requires.secondary_action; } });
  return c;
}
const switchesFor = (rule) => ({ secondary_action: rule === "A" });
function legalPrefix(s, actor, plan) { const out = []; for (const st of plan) if (E.validatePlan(s, actor, out.concat([st])).legal) out.push(st); return out; }
// Aero, a reasonable tactical player: search when blind, recover/ignite, close, then (if allowed) the best opener, strike, follow up.
function aeroPlan(s) {
  const foes = Object.keys(s.actors).filter((id) => s.actors[id].side === "enemy" && !s.actors[id].down && !s.actors[id].conds.hidden);
  const A = s.actors.aero; if (!foes.length) return [{ pid: "tactical_glance" }];
  const t = foes[0], T = s.actors[t], d = E.distance(s, "aero", t), p = [];
  if (A.dropped) p.push({ pid: "recover_weapon" }); else if (A.weapon && A.weapon.kind === "lightsaber" && !A.weapon.ignited) p.push({ pid: "toggle_blade" });
  if (d > 5) p.push({ pid: "move", dest: "close", target: t });
  if (A.hp <= 4) p.push({ pid: "readied_dodge" }); else if (T.kind !== "beast" && T.kind !== "droid") p.push({ pid: "feint", target: t });
  p.push({ pid: "saber_strike", target: t, augment: A.fp > 0 && s.round === 1 }, { pid: "unarmed_strike", target: t }, { pid: "flow_strike", target: t });
  return p;
}
const react = (pp) => pp.kind === "melee_hit_on_me" ? "parry" : pp.kind === "melee_miss_on_me" ? "riposte" : pp.kind === "attack_declared_on_me" ? "dodge_reaction" : pp.kind === "opportunity_attack" ? pp.options[0] : pp.kind === "ranged_energy_hit_on_me" ? "lightsaber_deflect" : pp.options[0] || null;
function fight(rule, sc, seed) {
  let s = E.newState(catalogFor(rule), S, sc, { seed, switches: switchesFor(rule) });
  const st = { aeroTurns: 0, sig: {}, sec: 0, feint: 0, feintWon: 0, flow: 0, dealt: 0, taken: 0, npcSec: 0, lostFlowToOpener: 0 };
  for (let g = 0; g < 80 && !s.over; g++) {
    const a = E.current(s), want = a === "aero" ? aeroPlan(s) : null;
    let plan = a === "aero" ? legalPrefix(s, "aero", want) : E.npcPlan(s, a);
    // fairness under C: the NPC duelist's policy keys its feint on the SA-001 switch; give it the same Bonus-cost feint Aero gets
    if (rule === "C" && a !== "aero" && s.actors[a].profiles.includes("feint") && !plan.some((x) => x.pid === "feint")) { const t = plan.find((x) => x.target); if (t) { const i = plan.findIndex((x) => x.pid !== "move"); plan = legalPrefix(s, a, plan.slice(0, i).concat([{ pid: "feint", target: t.target }], plan.slice(i))); } }
    const ch = {}; let r; for (let k = 0; k < 12; k++) { r = E.resolveTurn(s, a, plan, ch); if (!r.paused) break; const c = react(r.paused); ch[r.paused.key] = r.paused.options.includes(c) ? c : null; }
    const before = s.log.length; s = r.state; const L = s.log.slice(before);
    if (a === "aero") { st.aeroTurns++; const sig = plan.map((x) => x.pid).join("+") || "(nothing)"; st.sig[sig] = (st.sig[sig] || 0) + 1;
      if (plan.some((x) => (C0.profiles[x.pid].cost || {}).secondary)) st.sec++;
      if (plan.some((x) => x.pid === "feint")) { st.feint++; if (L.some((l) => l.ev === "feinted")) st.feintWon++; }
      if (plan.some((x) => x.pid === "flow_strike")) st.flow++; else if (want.some((x) => x.pid === "flow_strike") && plan.some((x) => x.pid === "feint" || x.pid === "readied_dodge")) st.lostFlowToOpener++;
    } else if (plan.some((x) => x.pid === "feint")) st.npcSec++;
    L.forEach((l) => { if (l.ev === "damage") { if (l.attacker === "aero") st.dealt += l.amount; else if (l.target === "aero") st.taken += l.amount; } });
    if (!s.over) s = E.endTurn(s);
  }
  return Object.assign(st, { win: s.over === "victory", over: !!s.over, rounds: s.round });
}
const entropy = (counts) => { const t = Object.values(counts).reduce((a, b) => a + b, 0); return -Object.values(counts).reduce((h, c) => h + (c / t) * Math.log2(c / t), 0); };
const out = {};
for (const sc of ["duelist", "predator", "relay_droid"]) for (const rule of ["A", "B", "C"]) {
  const agg = { n: 0, win: 0, rounds: 0, turns: 0, dealt: 0, taken: 0, sec: 0, feint: 0, feintWon: 0, flow: 0, npcSec: 0, lost: 0, sig: {} };
  for (let i = 1; i <= N; i++) { const f = fight(rule, sc, 1000003 * i + 17); agg.n++; agg.win += f.win; agg.rounds += f.rounds; agg.turns += f.aeroTurns; agg.dealt += f.dealt; agg.taken += f.taken;
    agg.sec += f.sec; agg.feint += f.feint; agg.feintWon += f.feintWon; agg.flow += f.flow; agg.npcSec += f.npcSec; agg.lost += f.lostFlowToOpener; Object.entries(f.sig).forEach(([k, v]) => (agg.sig[k] = (agg.sig[k] || 0) + v)); }
  const top = Object.entries(agg.sig).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k, v]) => k + " " + (100 * v / agg.turns).toFixed(0) + "%");
  out[sc + ":" + rule] = { win_pct: +(100 * agg.win / agg.n).toFixed(1), rounds: +(agg.rounds / agg.n).toFixed(2), aero_dmg_per_turn: +(agg.dealt / agg.turns).toFixed(2), dmg_taken_per_fight: +(agg.taken / agg.n).toFixed(2),
    secondary_use_pct: +(100 * agg.sec / agg.turns).toFixed(1), feint_pct: +(100 * agg.feint / agg.turns).toFixed(1), feint_success_pct: agg.feint ? +(100 * agg.feintWon / agg.feint).toFixed(1) : null,
    flow_strike_pct: +(100 * agg.flow / agg.turns).toFixed(1), flow_lost_to_opener_pct: +(100 * agg.lost / agg.turns).toFixed(1), npc_feints_per_fight: +(agg.npcSec / agg.n).toFixed(2),
    plan_variety_bits: +entropy(agg.sig).toFixed(2), distinct_plans: Object.keys(agg.sig).length, top_plans: top };
}
if (process.argv.includes("--json")) console.log(JSON.stringify({ N, seeds: "1000003*i+17", results: out }, null, 1));
else { console.log("SA-001 study, N=" + N + " per cell (same seeds across rules)"); for (const [k, v] of Object.entries(out)) console.log(k.padEnd(16), JSON.stringify(v)); }
