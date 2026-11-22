// Genesis CC-003 tactical prediction (noncanonical sandbox). Pure, read-only.
// Exact probabilities come from the same numbers the engine uses (profile bonus, AC, skills, advantage sources,
// NPC reaction policy). Multi-step outcomes come from a labeled seeded simulation that runs the real engine on a
// CLONED state with a separate, non-authoritative seed. Nothing here touches the authoritative dice stream.
(function (root, factory) { if (typeof module === "object" && module.exports) module.exports = factory(require("./engine.js")); else root.GenesisPredict = factory(root.GenesisCombat); })(this, function (E) {
  "use strict";
  function clone(x) { return JSON.parse(JSON.stringify(x)); }
  function parse(f) { var m = /^(\d+)d(\d+)([+-]\d+)?$/.exec(f); return { n: +m[1], d: +m[2], k: +(m[3] || 0) }; }

  // P(kept d20 = k) for normal / advantage / disadvantage (k = 1..20); exact.
  function d20(mode) {
    var p = [0];
    for (var k = 1; k <= 20; k++) p[k] = mode === "advantage" ? (2 * k - 1) / 400 : mode === "disadvantage" ? (41 - 2 * k) / 400 : 1 / 20;
    return p;
  }
  // distribution of a sum of dice: {value: probability}
  function diceDist(n, sides) { var d = { 0: 1 }; for (var i = 0; i < n; i++) { var nd = {}; Object.keys(d).forEach(function (v) { for (var f = 1; f <= sides; f++) nd[+v + f] = (nd[+v + f] || 0) + d[v] / sides; }); d = nd; } return d; }
  function damage(formula, crit) {
    var f = parse(formula), d = diceDist(f.n * (crit ? 2 : 1), f.d), out = {}, mean = 0;
    Object.keys(d).forEach(function (v) { out[+v + f.k] = d[v]; mean += (+v + f.k) * d[v]; });
    var vals = Object.keys(out).map(Number);
    return { formula: formula + (crit ? " (critical: dice doubled)" : ""), min: Math.min.apply(null, vals), max: Math.max.apply(null, vals), mean: mean, dist: out };
  }
  function modeOf(adv, dis) { return adv && !dis ? "advantage" : dis && !adv ? "disadvantage" : "normal"; }

  // Exact attack: nat 1 always misses, nat 20 always hits (critical); parryWindow = NPC parries when total < AC+bonus.
  function attackOdds(bonus, ac, mode, o) {
    o = o || {}; var p = d20(mode), ext = o.extraD4 ? diceDist(1, 4) : { 0: 1 };
    var r = { hit: 0, crit: 0, miss: 0, parried: 0 };
    for (var k = 1; k <= 20; k++) Object.keys(ext).forEach(function (e) {
      var pr = p[k] * ext[e], tot = k + bonus + (+e);
      if (k === 1) r.miss += pr;
      else if (k === 20) { r.crit += pr; r.hit += pr; }
      else if (tot >= ac) { if (o.parry && tot < ac + o.parry) { r.parried += pr; r.miss += pr; } else r.hit += pr; }
      else r.miss += pr;
    });
    return r;
  }
  function contestOdds(am, aAdv, tm, tAdv) {   // actor wins on strictly higher total (engine: a.total > t.total)
    var pa = d20(aAdv ? "advantage" : "normal"), pt = d20(tAdv ? "advantage" : "normal"), w = 0;
    for (var i = 1; i <= 20; i++) for (var j = 1; j <= 20; j++) if (i + am > j + tm) w += pa[i] * pt[j];
    return w;
  }
  function wilson(k, n) { if (!n) return [0, 0]; var z = 1.96, p = k / n, d = 1 + z * z / n, c = (p + z * z / (2 * n)) / d, h = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d; return [Math.max(0, c - h), Math.min(1, c + h)]; }

  function skillOf(A, sk) { return A.skills[sk] != null ? A.skills[sk] : (A.abilities && A.abilities.wis) || 0; }

  // Per-step exact analysis of a plan, tracking the feint/insight/prone setups the engine would apply.
  // Returns one entry per step plus a narrative note kept separate from the mechanical numbers.
  function analyzePlan(s, actorId, plan) {
    var v = E.validatePlan(s, actorId, plan), A = s.actors[actorId], steps = [], pFeint = {}, insight = {}, usedAug = false;
    Object.keys(s.actors).forEach(function (t) { var c = s.actors[t].conds; if (c.insight && c.insight.by === actorId) insight[t] = 1; });
    var reactionLeft = {}; Object.keys(s.actors).forEach(function (t) { reactionLeft[t] = s.actors[t].reaction_left; });
    plan.forEach(function (st, i) {
      var p = s.catalog.profiles[st.pid], out = { index: i, pid: st.pid, name: p.name, legal: !!(v.steps[i] && v.steps[i].ok), kind: "other" };
      var T = st.target && s.actors[st.target];
      if (p.resolution && p.resolution.type === "contest" && T) {
        var tsk = p.resolution.target_skill, am = skillOf(A, p.resolution.actor_skill);
        var tm = tsk === "athletics_or_acrobatics" ? Math.max(T.skills.athletics || 0, T.skills.acrobatics || 0) : skillOf(T, tsk);
        var w = contestOdds(am, !!(A.advantage_on && A.advantage_on[p.resolution.actor_skill]), tm, !!(T.advantage_on && T.advantage_on[tsk]));
        out.kind = "contest"; out.success = w; out.math = "d20" + fmt(am) + " vs d20" + fmt(tm) + " (" + p.resolution.actor_skill + " vs " + tsk.replace(/_/g, " ") + "), win on higher; ties go to the defender";
        if (p.effect.on_success === "feinted") pFeint[st.target] = w;
      }
      if (p.resolution && p.resolution.type === "attack" && T) {
        var base = E.hasAdv(s, actorId, st.target, p, {}), adv = base.adv.slice(), dis = base.dis.slice();
        if (insight[st.target]) { if (adv.indexOf("Battle Insight") < 0) adv.push("Battle Insight"); }
        if (T.conds.dodge_ready || T.conds.dodging) { if (dis.indexOf("dodging") < 0) dis.push(T.conds.dodging ? "dodging" : "readied dodge"); }
        var parryOpt = reactionLeft[st.target] > 0 && p.resolution.melee && E.reactionOptions(s, st.target, "melee_hit_on_me", { attacker: actorId, defender: st.target, depth: 0 });
        var parry = parryOpt && parryOpt.length ? s.catalog.profiles[parryOpt[0]].resolution.bonus : 0;
        var rip = p.resolution.melee && reactionLeft[st.target] > 0 && E.reactionOptions(s, st.target, "melee_miss_on_me", { attacker: actorId, defender: st.target, depth: 0 }).length > 0;
        var aug = !!st.augment && !usedAug; if (aug) usedAug = true;
        var pf = p.resolution.melee && pFeint[st.target] != null ? pFeint[st.target] : null;
        var withAdv = attackOdds(p.resolution.bonus, T.ac, modeOf(true, dis.length > 0), { parry: parry, extraD4: aug });
        var noAdv = attackOdds(p.resolution.bonus, T.ac, modeOf(adv.length > 0, dis.length > 0), { parry: parry, extraD4: aug });
        var odds = pf == null ? noAdv : mix(withAdv, noAdv, pf);
        out.kind = "attack"; out.target = st.target; out.adv = adv; out.dis = dis; out.feint_conditional = pf; out.parry_bonus = parry; out.riposte_risk = rip ? odds.miss : 0;
        out.hit = odds.hit; out.crit = odds.crit; out.parried = odds.parried; out.miss = odds.miss;
        out.if_feint_wins = pf == null ? null : withAdv.hit; out.if_feint_fails = pf == null ? null : noAdv.hit;
        out.mode = pf == null ? modeOf(adv.length > 0, dis.length > 0) : "conditional";
        out.damage = damage(p.resolution.damage, false); out.crit_damage = damage(p.resolution.damage, true);
        out.expected_damage = (odds.hit - odds.crit) * out.damage.mean + odds.crit * out.crit_damage.mean;
        out.math = "d20+" + p.resolution.bonus + (aug ? " +1d4 (Force-guided)" : "") + " vs AC " + T.ac + "; nat 1 misses, nat 20 crits" + (parry ? "; its Parry adds +" + parry + " AC when that would turn the hit (its policy)" : "");
        if (pf != null) delete pFeint[st.target];   // the engine consumes the feint on the first melee attack
        if (insight[st.target]) delete insight[st.target];
        if (parry) reactionLeft[st.target] -= odds.parried > 0 ? 0 : 0;   // reaction use is probabilistic: simulation covers the dependency
      }
      steps.push(out);
    });
    return { exact: true, steps: steps, note: "Exact per step. Steps after the first parry or riposte depend on earlier dice; see the simulation for the whole-turn numbers." };
  }
  function mix(a, b, p) { var r = {}; Object.keys(a).forEach(function (k) { r[k] = p * a[k] + (1 - p) * b[k]; }); return r; }
  function fmt(n) { return n >= 0 ? "+" + n : "" + n; }

  // Exact defense: chance an enemy attack hits Aero, and how much a Parry/Dodge changes it.
  function defenseOdds(s, attackerId, defenderId, pid) {
    var p = s.catalog.profiles[pid], D = s.actors[defenderId], base = E.hasAdv(s, attackerId, defenderId, p, {});
    var m = modeOf(base.adv.length > 0, base.dis.length > 0), plain = attackOdds(p.resolution.bonus, D.ac, m);
    var withParry = attackOdds(p.resolution.bonus, D.ac, m, { parry: 2 });
    var dodge = attackOdds(p.resolution.bonus, D.ac, modeOf(base.adv.length > 0, true));
    return { hit: plain.hit, crit: plain.crit, parry_prevents: withParry.parried, dodge_hit: dodge.hit, damage: damage(p.resolution.damage), mode: m, adv: base.adv, dis: base.dis };
  }

  // Seeded simulation of the whole declared turn on a CLONE with its own seed. Player reaction pauses are answered
  // by `reactionPolicy` (default: decline). Reports frequencies with Wilson 95% intervals.
  function simulate(s, actorId, plan, opts) {
    opts = opts || {}; var n = opts.n || 600, seed0 = opts.seed == null ? 0x5EED : opts.seed, pol = opts.reactionPolicy || function () { return null; };
    var v = E.validatePlan(s, actorId, plan); if (!v.legal || !plan.length) return null;
    var base = clone(s), tgts = {}, k = { feint: 0, feintN: 0, allHit: 0, down: 0, dmg: 0, dmgTaken: 0 }, hits = plan.map(function () { return 0; }), atks = plan.map(function () { return 0; });
    plan.forEach(function (st) { if (st.target) tgts[st.target] = 1; });
    for (var i = 0; i < n; i++) {
      var c = clone(base); c.rng = { seed: (seed0 + i * 2654435761) | 0, n: 0 }; c.receipts = []; c.log = [];
      var ch = {}, r;
      for (var g = 0; g < 12; g++) { r = E.resolveTurn(c, actorId, plan, ch); if (!r.paused) break; var pick = pol(r.paused); ch[r.paused.key] = r.paused.options.indexOf(pick) >= 0 ? pick : null; }
      var att = r.log.filter(function (l) { return l.ev === "attack" && l.attacker === actorId && !l.counter; });
      var dmgEv = r.log.filter(function (l) { return l.ev === "damage"; });
      var con = r.log.filter(function (l) { return l.ev === "contest" && l.actor === actorId && l.pid === "feint"; });
      if (con.length) { k.feintN++; if (con[0].win) k.feint++; }
      var allH = att.length > 0;
      att.forEach(function (a, j) { var hit = dmgEv.some(function (d) { return d.attacker === actorId && d.target === a.defender && d.pid === a.pid && r.log.indexOf(d) > r.log.indexOf(a) && (j + 1 >= att.length || r.log.indexOf(d) < r.log.indexOf(att[j + 1])); }); if (!hit) allH = false; });
      if (allH && (!con.length || con[0].win)) k.allHit++;
      dmgEv.forEach(function (d) { if (d.attacker === actorId) k.dmg += d.amount; if (d.target === actorId) k.dmgTaken += d.amount; });
      if (Object.keys(tgts).some(function (t) { return r.state.actors[t].down; })) k.down++;
    }
    var w = function (x) { var ci = wilson(x, n); return { p: x / n, lo: ci[0], hi: ci[1] }; };
    return { method: "seeded simulation of the real engine on a cloned state", samples: n, seed: seed0, authoritative_dice_used: false,
             feint_success: k.feintN ? w(k.feint) : null, full_combo: w(k.allHit), target_down: w(k.down), avg_damage_dealt: k.dmg / n, avg_damage_taken: k.dmgTaken / n };
  }

  // Narrative assessment: words only, derived from the numbers above; never a number of its own.
  function assess(p) { if (p == null) return ""; return p >= 0.75 ? "very likely" : p >= 0.55 ? "better than even" : p >= 0.45 ? "a coin flip" : p >= 0.25 ? "risky" : "a long shot"; }

  return { d20: d20, damage: damage, attackOdds: attackOdds, contestOdds: contestOdds, analyzePlan: analyzePlan, defenseOdds: defenseOdds, simulate: simulate, wilson: wilson, assess: assess };
});
