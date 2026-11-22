// Balance simulation for the CC-002 sandbox (noncanonical). Every fight goes through the real engine with its own
// validator and seeded dice; nothing is rerolled or adjusted. Alternatives change *fixture data* only, and are
// labeled as sandbox proposals. node audit/balance_sim.cjs [N] [--json]
const E = require("../engine.js");
const C = require("../catalog.json");
const S0 = require("../scenarios.json");
let N = +(process.argv.find((a) => /^\d+$/.test(a)) || 2000);
const clone = (x) => JSON.parse(JSON.stringify(x));

// ---- Aero strategies (what a player might do; the engine decides legality) ----
function aeroPlan(s, style) {
  const foes = Object.keys(s.actors).filter((id) => s.actors[id].side === "enemy" && !s.actors[id].down && !s.actors[id].conds.hidden);
  const A = s.actors.aero, plan = [];
  if (!foes.length) return style === "tactical" && s.switches.secondary_action ? [{ pid: "tactical_glance" }] : [];
  const t = foes[0], d = E.distance(s, "aero", t);
  if (A.dropped) plan.push({ pid: "recover_weapon" });
  else if (A.weapon && A.weapon.kind === "lightsaber" && !A.weapon.ignited) plan.push({ pid: "toggle_blade" });
  if (d > 5) plan.push({ pid: "move", dest: "close", target: t });
  if (style === "tactical") {
    if (A.hp <= 4 && s.switches.secondary_action) plan.push({ pid: "readied_dodge" });
    else if (s.switches.secondary_action && s.actors[t].kind !== "beast") plan.push({ pid: "feint", target: t });
    plan.push({ pid: "saber_strike", target: t, augment: A.fp > 0 && s.round === 1 });
  } else plan.push({ pid: "saber_strike", target: t });
  plan.push({ pid: "unarmed_strike", target: t });   // fallback if the saber is gone (validator filters)
  plan.push({ pid: "flow_strike", target: t });
  return plan;   // legalPrefix keeps only the steps the engine accepts, in order
}
function aeroReaction(style) { return (p) => style === "simple" ? null : (p.kind === "melee_hit_on_me" ? "parry" : p.kind === "melee_miss_on_me" ? "riposte" : p.kind === "attack_declared_on_me" ? "dodge_reaction" : p.kind === "opportunity_attack" ? p.options[0] : null); }

function legalPrefix(s, actor, plan) { const out = []; for (const st of plan) { if (E.validatePlan(s, actor, out.concat([st])).legal) out.push(st); } return out; }

function fight(scenarios, sc, seed, style, switches) {
  let s = E.newState(C, scenarios, sc, { seed, switches });
  const stats = { aeroAttacks: 0, aeroHits: 0, enemyAttacks: 0, enemyHits: 0, dmgTaken: 0, round1Taken: 0, crits: 0, killer: null };
  const react = aeroReaction(style);
  for (let guard = 0; guard < 60 && !s.over; guard++) {
    const actor = E.current(s);
    const plan = actor === "aero" ? legalPrefix(s, "aero", aeroPlan(s, style)) : E.npcPlan(s, actor);
    const choices = {}; let r;
    for (let g = 0; g < 12; g++) { r = E.resolveTurn(s, actor, plan, choices); if (!r.paused) break; const c = react(r.paused); choices[r.paused.key] = r.paused.options.includes(c) ? c : null; }
    if (r.refused) throw new Error("refused plan for " + actor + ": " + JSON.stringify(r.refused.steps));
    const hpBefore = s.actors.aero.hp;
    for (const rc of r.receipts) {
      if (/ → /.test(rc.purpose)) { const aero = rc.actor === "aero"; aero ? stats.aeroAttacks++ : stats.enemyAttacks++; if (rc.kept === 20) stats.crits++; }
    }
    for (const l of r.log) { if (/takes \d+/.test(l.text)) { const own = /^Aero takes/.test(l.text); if (own) stats.enemyHits++; else stats.aeroHits++; } }
    s = E.endTurn(r.state);
    const lost = hpBefore - s.actors.aero.hp; stats.dmgTaken += lost; if (s.round === 1 || (s.round === 2 && E.current(s) === s.order[0])) stats.round1Taken += lost;
    if (s.over === "defeat" && !stats.killer) { const hits = r.log.filter((l) => /Aero takes \d+/.test(l.text)); const atk = r.log.filter((l) => / at Aero: /.test(l.text)).slice(-1)[0];
      stats.killer = (atk ? atk.text.replace(/^.* — /, "").replace(/ at Aero:.*$/, "") + (/CRITICAL/.test(atk.text) ? " (critical)" : "") : "?") + (s.round === 1 ? " in round 1" : ""); }
  }
  return Object.assign(stats, { result: s.over || "timeout", rounds: s.round });
}

function run(label, scenarios, sc, style, switches, note) {
  const agg = { label, scenario: sc, style, note: note || "", n: N, wins: 0, rounds: 0, dmg: 0, r1: 0, aA: 0, aH: 0, eA: 0, eH: 0, timeouts: 0, killers: {} };
  for (let seed = 1; seed <= N; seed++) {
    const f = fight(scenarios, sc, seed, style, switches);
    if (f.result === "victory") agg.wins++; if (f.result === "timeout") agg.timeouts++;
    agg.rounds += f.rounds; agg.dmg += f.dmgTaken; agg.r1 += f.round1Taken; agg.aA += f.aeroAttacks; agg.aH += f.aeroHits; agg.eA += f.enemyAttacks; agg.eH += f.enemyHits;
    if (f.killer) agg.killers[f.killer] = (agg.killers[f.killer] || 0) + 1;
  }
  const p = agg.wins / N, ci = 1.96 * Math.sqrt(p * (1 - p) / N);
  return { label, scenario: sc, style, note: agg.note, fights: N, win_rate: +(p * 100).toFixed(1), ci95: +(ci * 100).toFixed(1),
           avg_rounds: +(agg.rounds / N).toFixed(2), avg_damage_taken: +(agg.dmg / N).toFixed(2), avg_round1_damage: +(agg.r1 / N).toFixed(2),
           aero_hit_rate: +(100 * agg.aH / Math.max(1, agg.aA)).toFixed(1), enemy_hit_rate: +(100 * agg.eH / Math.max(1, agg.eA)).toFixed(1), timeouts: agg.timeouts,
           defeat_causes: Object.entries(agg.killers).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k, v]) => k + ": " + v) };
}

// ---- configurations ----
function variant(fn) { const s = clone(S0); fn(s); return s; }
const ilsa = (s) => s.scenarios.duelist.actors.ilsa;
const configs = [
  ["Baseline duel (simple play)", S0, "duelist", "simple"],
  ["Baseline duel (tactical play)", S0, "duelist", "tactical"],
  ["Baseline predator (simple)", S0, "predator", "simple"],
  ["Baseline predator (tactical)", S0, "predator", "tactical"],
  ["P1 Intro duelist: Ilsa AC 14, HP 16, blade +4 / 1d6+3 (tactical)", variant((s) => { Object.assign(ilsa(s), { ac: 14, hp: 16, hp_max: 16 }); s.__blade = { bonus: 4, damage: "1d6+3" }; }), "duelist", "tactical", "sandbox proposal"],
  ["P2 Intro duelist: Ilsa keeps stats, no Riposte (tactical)", variant((s) => { ilsa(s).grants.sandbox_proposal = ilsa(s).grants.sandbox_proposal.filter((g) => g !== "npc_riposte"); }), "duelist", "tactical", "sandbox proposal"],
  ["P3 Predator: Aero notices it first (not hidden at start)", variant((s) => { s.scenarios.predator.actors.stalker.hidden = false; s.scenarios.predator.initiative = ["aero", "stalker"]; }), "predator", "tactical", "sandbox proposal: stealth vs passive Perception decides"],
  ["P4 Predator: HP 11, bite 1d6+2", variant((s) => { Object.assign(s.scenarios.predator.actors.stalker, { hp: 11, hp_max: 11 }); s.__bite = "1d6+2"; }), "predator", "tactical", "sandbox proposal"],
];
function runAll() {
const results = [];
for (const [label, sc, id, style, note] of configs) {
  const cat = clone(C);
  if (sc.__blade) { Object.assign(cat.profiles.npc_blade.resolution, sc.__blade); Object.assign(cat.profiles.npc_riposte.resolution, sc.__blade); }
  if (sc.__bite) { cat.profiles.bite.resolution.damage = sc.__bite; cat.profiles.pounce.resolution.damage = sc.__bite; }
  const savedC = Object.assign({}, C.profiles); Object.assign(C.profiles, cat.profiles);
  results.push(run(label, sc, id, style, {}, note));
  Object.keys(C.profiles).forEach((k) => delete C.profiles[k]); Object.assign(C.profiles, savedC);
}
return results;
}
if (require.main === module) {
  const results = runAll();
  if (process.argv.includes("--json")) console.log(JSON.stringify(results, null, 1));
  else { console.log(`${N} fights per configuration, seeds 1..${N}`); for (const r of results) console.log(JSON.stringify(r)); }
}
module.exports = { runAll, run, fight, aeroPlan, configs, setN: (n) => { N = n; } };
