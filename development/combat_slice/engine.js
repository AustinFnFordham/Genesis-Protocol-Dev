/* Genesis CC-002 sandbox combat engine (noncanonical). One resolver for every actor: the player's plan and an NPC's
 * plan go through the same validatePlan and resolveTurn. Pure functions over a plain JSON state; dice are a seeded
 * stream with receipts, so a turn replays to identical receipts. A player reaction pauses the turn; resuming re-runs
 * the same turn from the same snapshot with the player's choice, so earlier rolls are identical (no rerolls possible).
 * Cards and UI are presentation only: they read profiles from the catalog and ask this engine what is legal.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.GenesisCombat = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  var COST_KEYS = ["main", "bonus", "secondary", "reaction", "movement_ft", "object", "fp"];

  function clone(x) { return JSON.parse(JSON.stringify(x)); }
  function key(a, b) { return a < b ? a + "|" + b : b + "|" + a; }

  // ---------------- dice: seeded, receipted ----------------
  function mulberry(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  // Dice authority. s.rng.mode "local" = the sandbox stream (tests, balance runs, offline practice; NOT authoritative).
  // s.rng.mode "atomic" = values come only from s.tape, the dice Atomic has accepted, indexed by sequence number.
  // A missing value throws NeedDice; resolveTurn turns that into {need_dice} and the caller asks Atomic, appends the
  // accepted values to the tape and re-runs the same turn from the same snapshot (identical to reaction pauses).
  function localDie(seed, n, sides) { var r = mulberry((seed * 7919 + n * 104729) | 0)(); return 1 + Math.floor(r * sides); }
  function NeedDice(need) { this.need = need; }
  function drawDice(s, sidesList, meta) {
    var start = s.rng.n;
    if (s.rng.mode === "atomic") {
      var missing = [];
      sidesList.forEach(function (sd, i) { var t = s.tape[start + i]; if (!t) missing.push({ seq: start + i, sides: sd }); else if (t.sides !== sd) throw new Error("TAPE_MISMATCH at seq " + (start + i) + ": tape d" + t.sides + ", engine needs d" + sd); });
      if (missing.length) throw new NeedDice(Object.assign({ from: start, dice: sidesList.map(function (sd, i) { return { seq: start + i, sides: sd }; }) }, meta));
    }
    var out = sidesList.map(function (sd, i) { return s.rng.mode === "atomic" ? s.tape[start + i].value : localDie(s.rng.seed, start + i, sd); });
    s.rng.n += sidesList.length;
    return out;
  }
  function parse(formula) { var m = /^(\d+)d(\d+)([+-]\d+)?$/.exec(formula); if (!m) throw new Error("bad formula " + formula); return { n: +m[1], d: +m[2], k: +(m[3] || 0) }; }
  function rollDice(s, actor, purpose, formula, opts) {
    opts = opts || {};
    var f = parse(formula), rolls = [], kept, n = f.n * (opts.crit ? 2 : 1), pair = f.d === 20 && f.n === 1 && (opts.adv || opts.dis) && !(opts.adv && opts.dis);
    var mode = opts.adv && !opts.dis ? "advantage" : opts.dis && !opts.adv ? "disadvantage" : "normal";
    var sides = []; for (var i = 0; i < (pair ? 2 : n); i++) sides.push(f.d); (opts.extra || []).forEach(function (e) { sides.push(e.sides); });
    var drawn = drawDice(s, sides, { step: s._step == null ? null : s._step, rules: s.catalog ? (s.catalog.ruleset.rules_version || s.catalog.ruleset.id) : null, target: opts.vs && opts.vs.target || null, actor: actor, purpose: purpose, formula: formula, mode: mode, crit: !!opts.crit, extra: (opts.extra || []).map(function (e) { return e.label; }), vs: opts.vs || null, kind: opts.kind || "check" });
    if (pair) { rolls = drawn.slice(0, 2); kept = opts.adv ? Math.max(rolls[0], rolls[1]) : Math.min(rolls[0], rolls[1]); }
    else { rolls = drawn.slice(0, n); kept = rolls.reduce(function (a, b) { return a + b; }, 0); }
    var extra = (opts.extra || []).map(function (e, j) { return { label: e.label, value: drawn[(pair ? 2 : n) + j] }; });
    var total = kept + f.k + extra.reduce(function (a, e) { return a + e.value; }, 0);
    var rec = { receipt: "r" + (s.receipts.length + 1), seq: s.rng.n, first_seq: s.rng.n - sides.length, authority: s.rng.mode === "atomic" ? "atomic" : "local_sandbox", vs: opts.vs || null, kind: opts.kind || "check", actor: actor, purpose: purpose, formula: formula,
                mode: opts.adv && !opts.dis ? "advantage" : opts.dis && !opts.adv ? "disadvantage" : "normal", rolls: rolls, kept: kept, extra: extra, total: total };
    s.receipts.push(rec);
    return rec;
  }

  // ---------------- state ----------------
  function newState(catalog, scenarios, scenarioId, opts) {
    opts = opts || {};
    var sc = scenarios.scenarios[scenarioId];
    var switches = {}; Object.keys(catalog.ruleset.switches).forEach(function (k) { switches[k] = catalog.ruleset.switches[k].default; });
    Object.assign(switches, opts.switches || {});
    var actors = {}, all = Object.assign({ aero: scenarios.aero }, sc.actors);
    Object.keys(all).forEach(function (id) {
      var a = clone(all[id]);
      a.conds = {}; if (a.hidden) a.conds.hidden = true; delete a.hidden;
      a.used = {}; a.down = false; a.dropped = null; a.reaction_left = 1;
      a.profiles = [].concat((a.grants && a.grants.sheet) || [], (a.grants && a.grants.sandbox_proposal) || []);
      actors[id] = a;
    });
    Object.keys(catalog.profiles).forEach(function (k) { catalog.profiles[k].id = k; });
    var s = { schema: "genesis-cc002-state/0.1", canonical: false, scenario: scenarioId, title: sc.title, intro: sc.intro,
              catalog: catalog, switches: switches, round: 1, order: sc.initiative.slice(), turn: 0, actors: actors,
              dist: clone(sc.distance), rng: { mode: opts.atomic ? "atomic" : "local", seed: opts.atomic ? null : (opts.seed == null ? 20261121 : opts.seed), n: 0 }, tape: [], receipts: [], log: [], trigger: 0, over: null };
    Object.keys(actors).forEach(function (id) { actors[id].budget = budgetFor(s); });   // everyone starts the round with a full budget
    startTurn(s);
    return s;
  }
  function budgetFor(s) { var b = clone(s.catalog.ruleset.budget); if (!s.switches.secondary_action) b.secondary = 0; return b; }
  function current(s) { return s.order[s.turn]; }
  function startTurn(s) {
    var a = s.actors[current(s)];
    a.budget = budgetFor(s);   // a new turn restores the actor's own budget
    a.used = {};
    ["dodging", "dodge_ready", "taunted"].forEach(function (c) { if (a.conds[c] && a.conds[c].until === a.id) delete a.conds[c]; });
    Object.keys(s.actors).forEach(function (id) { var o = s.actors[id]; ["taunted"].forEach(function (c) { if (o.conds[c] && o.conds[c].until === a.id) delete o.conds[c]; }); });
    a.reaction_left = 1;
    if (a.conds.prone) { delete a.conds.prone; a.budget.movement_ft = Math.max(0, (a.budget.movement_ft || 0) - 15); log(s, a.id, a.name + " gets up (15 ft of movement).", { ev: "stand", actor: a.id }); }
  }
  function distance(s, a, b) { if (a === b) return 0; var d = s.dist[key(a, b)]; return d == null ? 60 : d; }
  function setDistance(s, a, b, v) { s.dist[key(a, b)] = Math.max(5, v); }
  function profile(s, pid) { return s.catalog.profiles[pid]; }
  function enemiesOf(s, id) { var side = s.actors[id].side; return Object.keys(s.actors).filter(function (o) { return s.actors[o].side !== side && !s.actors[o].down; }); }
  function visibleTo(s, viewer, target) { var t = s.actors[target]; return !t.conds.hidden || s.actors[viewer].side === t.side; }

  // ---------------- legality (shared by player and NPC) ----------------
  // proj: projected actor-local state while walking a plan
  function project(s, actorId) {
    var a = s.actors[actorId];
    return { budget: clone(a.budget), reaction_left: a.reaction_left, used: clone(a.used), weapon: clone(a.weapon || null), sidearm: clone(a.sidearm || null), dropped: a.dropped,
             dist: clone(s.dist), melee_attacked: !!a.used.melee_attacked, fp: a.fp, conds: clone(a.conds), down: a.down };
  }
  function costOf(s, actorId, pid, step, proj) {
    var p = profile(s, pid), c = Object.assign({}, p.cost || {});
    if (pid === "move") {
      var t = step.target; var d = t ? proj.dist[key(actorId, t)] : null;
      c = { movement_ft: step.dest === "close" ? Math.max(0, (d == null ? 60 : d) - 5) : 15 };
    }
    if (step.augment) c.fp = (c.fp || 0) + 1;
    return c;
  }
  function availability(s, actorId, pid, step, proj) {
    step = step || {}; proj = proj || project(s, actorId);
    var a = s.actors[actorId], p = profile(s, pid), why = [];
    if (!p) return { ok: false, reasons: [{ code: "UNKNOWN_PROFILE", text: "Not a known capability." }] };
    if (a.profiles.indexOf(pid) < 0) why.push({ code: "NOT_GRANTED", text: "You have not learned this." });
    if (proj.down) why.push({ code: "ACTOR_DOWN", text: "Down." });
    var r = p.requires || {};
    if (r.switch && !s.switches[r.switch]) why.push({ code: "SWITCH_OFF", text: "Sandbox switch " + r.switch + " is off." });
    if (r.secondary_action && !s.switches.secondary_action) why.push({ code: "SA001_DISABLED", text: "Secondary Action (SA-001) is off in this ruleset." });
    var cost = costOf(s, actorId, pid, step, proj);
    COST_KEYS.forEach(function (k) {
      if (!cost[k]) return;
      var have = k === "fp" ? proj.fp : k === "reaction" ? proj.reaction_left : proj.budget[k];
      if ((have || 0) < cost[k]) why.push({ code: "NO_" + k.toUpperCase(), text: "Not enough " + label(k) + " left (" + (have || 0) + ")." });
    });
    if (p.cap) { var used = proj.used["cap:" + p.cap.group] || 0; if (used >= p.cap.max) why.push({ code: "CAP_REACHED", text: "Already used this " + p.cap.per + "." }); }
    var w = proj.weapon;
    if (r.weapon_kind && (!w || w.kind !== r.weapon_kind || !w.held)) why.push({ code: "WEAPON_NOT_HELD", text: "Needs your " + r.weapon_kind + " in hand." });
    if (r.held && (!w || !w.held)) why.push({ code: "WEAPON_NOT_HELD", text: "Needs a weapon in hand." });
    if (r.ignited && w && w.held && w.kind === "lightsaber" && !w.ignited) why.push({ code: "BLADE_UNLIT", text: "Your blade is not lit." });
    if (r.weapon_dropped && !proj.dropped) why.push({ code: "NOTHING_DROPPED", text: "Your weapon is in hand." });
    var sa = proj.sidearm;
    if (r.sidearm_holstered && !(sa && !sa.held)) why.push({ code: sa ? "ALREADY_DRAWN" : "NO_SIDEARM", text: sa ? "Your " + sa.name + " is already in hand." : "You carry no sidearm." });
    if (r.sidearm_held && !(sa && sa.held)) why.push({ code: sa ? "SIDEARM_HOLSTERED" : "NO_SIDEARM", text: sa ? "Draw your " + sa.name + " first (object interaction)." : "You carry no sidearm." });
    if (r.ammo && sa && sa.held && sa.ammo < r.ammo) why.push({ code: "OUT_OF_AMMO", text: "Empty: reload (Main action)." });
    if (r.reloadable && sa && sa.held && sa.ammo >= sa.capacity) why.push({ code: "FULL_MAGAZINE", text: "Already full (" + sa.ammo + "/" + sa.capacity + ")." });
    if (r.reloadable && sa && sa.held && sa.reserve < 1) why.push({ code: "NO_RESERVE", text: "No ammunition left to load." });
    if (r.offhand_free && ((sa && sa.held) || proj.conds.grappling)) why.push({ code: "HAND_OCCUPIED", text: (sa && sa.held ? "Your off hand holds the " + sa.name : "Your off hand is holding a grapple") + "; this needs a free hand." });
    if (r.no_ability && a.profiles.indexOf(pid) < 0) {}
    if (r.always_unavailable) why.push({ code: r.always_unavailable.code, text: r.always_unavailable.text });
    if (r.condition && !proj.conds[r.condition]) why.push({ code: "NEEDS_" + r.condition.toUpperCase(), text: r.condition === "hidden" ? "Needs to be hidden." : "Needs " + r.condition.replace("_", " ") + "." });
    if (r.after_melee_attack_this_turn && !proj.melee_attacked) why.push({ code: "NEEDS_MELEE_ATTACK_FIRST", text: "Only after a melee attack this turn." });
    if (r.augments && step.augment) {}
    if (r.target === "enemy" || r.target === "beast") {
      var t = step.target;
      if (!t || !s.actors[t] || (s.actors[t].side === a.side) || !visibleTo(s, actorId, t)) why.push({ code: "NO_TARGET", text: "Choose a target you can see." });
      else {
        var T = s.actors[t], d = proj.dist[key(actorId, t)]; d = d == null ? 60 : d;
        if (T.down) why.push({ code: "TARGET_DOWN", text: "Already down." });
        if (r.target === "beast" && T.kind !== "beast") why.push({ code: "NOT_A_BEAST", text: "Only for animals." });
        if (r.reach_ft && d > r.reach_ft) why.push({ code: "OUT_OF_REACH", text: "Out of reach (" + d + " ft; needs " + r.reach_ft + ")." });
        if (r.range_ft && d > r.range_ft) why.push({ code: "OUT_OF_RANGE", text: "Out of range (" + d + " ft)." });
        if (r.understands && !T.understands) why.push({ code: "CANNOT_UNDERSTAND", text: "It does not understand words; insults do nothing." });
        if (r.target_holds_weapon && !(T.weapon && T.weapon.held)) why.push({ code: "TARGET_UNARMED", text: "It holds no weapon." });
        if (r.max_range_ft && d > r.max_range_ft) why.push({ code: "OUT_OF_RANGE", text: "Out of range (" + d + " ft; max " + r.max_range_ft + ")." });
        if (r.not_grappled_by_me && T.conds.grappled && T.conds.grappled.by === actorId) why.push({ code: "ALREADY_GRAPPLED", text: "You already hold it." });
      }
    }
    if (step.augment) {
      if (!s.switches.force_augmentation || a.profiles.indexOf("force_augment") < 0) why.push({ code: "AUGMENT_NOT_GRANTED", text: "Force augmentation is not available." });
      else if (["saber_strike", "riposte"].indexOf(pid) < 0) why.push({ code: "AUGMENT_NOT_ALLOWED", text: "Only a lightsaber strike or Riposte can be Force-guided." });
      else if (proj.used["cap:augment"]) why.push({ code: "CAP_REACHED", text: "Force-guided once per turn." });
    }
    if (pid === "move" && proj.conds.grappled) why.push({ code: "GRAPPLED", text: "Grappled: your speed is 0." });
    if (pid === "move") {
      if (step.dest === "close" && !(step.target && s.actors[step.target] && visibleTo(s, actorId, step.target))) why.push({ code: "NO_TARGET", text: "Choose who to close on." });
    }
    return { ok: why.length === 0, reasons: why, cost: cost };
  }
  function label(k) { return { main: "Main action", bonus: "Bonus action", secondary: "Secondary action", reaction: "Reaction", movement_ft: "movement", object: "object interaction", fp: "Force Points" }[k] || k; }
  function spend(proj, cost) { COST_KEYS.forEach(function (k) { if (!cost[k]) return; if (k === "fp") proj.fp -= cost[k]; else if (k === "reaction") proj.reaction_left -= cost[k]; else proj.budget[k] -= cost[k]; }); }
  function applyProjection(s, actorId, pid, step, proj) {
    var p = profile(s, pid);
    if (p.cap) proj.used["cap:" + p.cap.group] = (proj.used["cap:" + p.cap.group] || 0) + 1;
    if (step.augment) proj.used["cap:augment"] = 1;
    if (p.resolution && p.resolution.melee) proj.melee_attacked = true;
    if (pid === "move" && step.target) {
      var k = key(actorId, step.target), d = proj.dist[k] == null ? 60 : proj.dist[k];
      proj.dist[k] = step.dest === "close" ? 5 : d + 15;
    } else if (pid === "move") enemiesOfProj(s, actorId).forEach(function (e) { var k2 = key(actorId, e); proj.dist[k2] = (proj.dist[k2] == null ? 60 : proj.dist[k2]) + 15; });
    if (pid === "toggle_blade" && proj.weapon) proj.weapon.ignited = !proj.weapon.ignited;
    if (pid === "draw_sidearm" && proj.sidearm) proj.sidearm.held = true;
    if (pid === "holster_sidearm" && proj.sidearm) proj.sidearm.held = false;
    if (p.resolution && p.resolution.ammo && proj.sidearm) proj.sidearm.ammo -= 1;
    if (pid === "reload_sidearm" && proj.sidearm) { var need = proj.sidearm.capacity - proj.sidearm.ammo, take = Math.min(need, proj.sidearm.reserve); proj.sidearm.ammo += take; proj.sidearm.reserve -= take; }
    if (pid === "grapple") proj.conds.grappling = { by: actorId };
    if (pid === "recover_weapon" && proj.dropped) { proj.weapon = clone(proj.dropped); proj.weapon.held = true; if (proj.weapon.kind === "lightsaber") proj.weapon.ignited = false; proj.dropped = null; }
    if (p.effect && p.effect.sets) proj.conds[p.effect.sets] = { until: actorId };
  }
  function enemiesOfProj(s, id) { return enemiesOf(s, id).filter(function (e) { return visibleTo(s, id, e); }); }

  // Validate a whole ordered plan against projected state. Same function for every actor.
  function validatePlan(s, actorId, plan) {
    var proj = project(s, actorId), out = [], legal = true;
    if (current(s) !== actorId) return { legal: false, steps: [], errors: [{ code: "NOT_YOUR_TURN", text: "It is not this actor's turn." }] };
    (plan || []).forEach(function (step, i) {
      var p = profile(s, step.pid);
      if (p && p.trigger) { out.push({ i: i, pid: step.pid, ok: false, reasons: [{ code: "REACTION_ONLY", text: "A reaction happens when its trigger happens, not as a turn step." }] }); legal = false; return; }
      var av = availability(s, actorId, step.pid, step, proj);
      var w = proj.weapon, hand = w && w.held ? w.kind + (w.kind === "lightsaber" ? (w.ignited ? ":lit" : ":unlit") : "") : "empty";
      out.push({ i: i, pid: step.pid, ok: av.ok, reasons: av.reasons, cost: av.cost, main_hand: hand, off_hand: proj.sidearm && proj.sidearm.held ? proj.sidearm.kind : (proj.conds.grappling ? "grapple" : "free") });
      if (av.ok) { spend(proj, av.cost); applyProjection(s, actorId, step.pid, step, proj); } else legal = false;
    });
    return { legal: legal, steps: out, budget_after: proj.budget, reaction_left: proj.reaction_left, fp_after: proj.fp, proj: proj, errors: [] };
  }

  // Combo Judge (Atomic part): known conditional synergies and conflicts. Facts only, no score.
  function comboJudge(s, actorId, plan) {
    var notes = [], hasFeint = false, hasInsight = s.actors[actorId] && Object.keys(s.actors).some(function (t) { var c = s.actors[t].conds.insight; return c && c.by === actorId; });
    (plan || []).forEach(function (st) {
      if (st.pid === "feint") { hasFeint = true; notes.push({ kind: "conditional", text: "If the feint wins its contest, your next melee attack on that target this turn has advantage." }); }
      if (st.pid === "battle_insight" || st.pid === "battle_insight_bonus") { hasInsight = true; notes.push({ kind: "known", text: "Battle Insight: advantage on your next attack against that target." }); }
      if ((st.pid === "saber_strike" || st.pid === "unarmed_strike") && hasFeint && hasInsight) notes.push({ kind: "conflict", text: "Feint and Battle Insight both give advantage. Advantage does not stack; one is wasted." });
      if (st.pid === "flow_strike") notes.push({ kind: "conditional", text: "Flow Strike needs a melee attack earlier this turn; it still rolls to hit." });
      if (st.augment) notes.push({ kind: "known", text: "Force-guided: spends 1 Force Point for +1d4 on that attack roll." });
      if (st.pid === "move" && st.dest !== "close") notes.push({ kind: "risk", text: "Leaving an enemy's reach can provoke an opportunity attack." });
      if (st.pid === "speak") notes.push({ kind: "known", text: "Words are free and change nothing mechanically. Use Taunt for a mechanical effect." });
    });
    return notes;
  }
  // Synergy recognition: an ordered subsequence of plan steps (same target) that matches catalog.synergies.
  // Recognition is presentation; the mechanical basis is the listed profile rules, and every link stays conditional.
  function synergies(s, actorId, plan) {
    var out = [], list = s.catalog.synergies || [], v = validatePlan(s, actorId, plan || []);
    list.forEach(function (sy) {
      var idx = [], j = 0, tgt = null;
      for (var i = 0; i < (plan || []).length && j < sy.sequence.length; i++) {
        var st = plan[i], want = sy.sequence[j], vs = v.steps[i] || {};
        if ([].concat(want.pid).indexOf(st.pid) < 0) continue;
        if (want.main_hand && vs.main_hand && [].concat(want.main_hand).indexOf(vs.main_hand) < 0) continue;   // judged on what is actually in hand at that step
        if (st.target) { if (tgt && st.target !== tgt) continue; tgt = st.target; }
        idx.push(i); j++;
      }
      if (j < sy.sequence.length) return;
      var legal = idx.every(function (i) { return v.steps[i] && v.steps[i].ok; });
      out.push({ id: sy.id, name: sy.name, status: "predicted", steps: idx, target: tgt, legal: legal, links: sy.links, basis: sy.basis, conditional: sy.conditional });
    });
    // keep the most specific match when one synergy's steps contain another's
    return out.filter(function (a) { return !out.some(function (b) { return b !== a && b.steps.length > a.steps.length && a.steps.every(function (i) { return b.steps.indexOf(i) >= 0; }); }); });
  }
  // Confirmed combos: read from RESOLVED events of one turn, never from card labels. Every link must have happened
  // (feint won, the attack was made with the right weapon in hand, follow-up made). Hits are reported, not required.
  function confirmedCombos(s, turnLog) {
    var out = [], L = turnLog || [];
    (s.catalog.synergies || []).forEach(function (sy) {
      var j = 0, tgt = null, used = [], hits = 0;
      for (var i = 0; i < L.length && j < sy.sequence.length; i++) {
        var e = L[i], want = sy.sequence[j], pids = [].concat(want.pid);
        if (e.counter) continue;
        var isStep = (e.ev === "attack" && pids.indexOf(e.pid) >= 0) || (e.ev === "contest" && pids.indexOf(e.pid) >= 0) || (e.ev === "effect" && pids.indexOf(e.pid) >= 0);
        if (!isStep) continue;
        var who = e.attacker || e.actor, t = e.defender || e.target; if (tgt && t !== tgt) continue; tgt = t;
        if (e.ev === "contest" && !e.win) return;   // the setup failed: no confirmed combo
        if (want.main_hand && e.main_hand && [].concat(want.main_hand).indexOf(e.main_hand) < 0) return;
        if (e.ev === "attack") { var nx = L.slice(i + 1, i + 6); if (nx.some(function (x) { return x.ev === "damage" && x.attacker === who && x.target === t && x.pid === e.pid; })) hits++; }
        used.push(i); j++;
      }
      if (j === sy.sequence.length) out.push({ id: sy.id, name: sy.name, status: "confirmed", events: used, target: tgt, hits: hits, attacks: used.filter(function (i) { return L[i].ev === "attack"; }).length });
    });
    return out.filter(function (a) { return !out.some(function (b) { return b !== a && b.events.length > a.events.length && a.events.every(function (i) { return b.events.indexOf(i) >= 0; }); }); });
  }
  function cinematicNote(s, plan) {   // descriptive only; grants nothing (switch cinematic_judge)
    if (!s.switches.cinematic_judge || !plan || !plan.length) return null;
    var ids = plan.map(function (p) { return p.pid; });
    if (ids.indexOf("feint") >= 0 && ids.indexOf("saber_strike") >= 0) return "A classic duelist's line: sell the false cut, then commit.";
    if (ids.indexOf("flow_strike") >= 0) return "Blade and body in one motion — Echani flow.";
    if (ids.indexOf("readied_dodge") >= 0) return "Patience as a weapon.";
    return null;
  }

  // ---------------- resolution ----------------
  function log(s, who, text, extra) { var e = Object.assign({ round: s.round, who: who, text: text }, extra || {}); s.log.push(e); return e; }
  function Pause(p) { this.pause = p; }

  // decide(s, defender, kind, ctx) -> chosen profile id or null. Player decisions come from choices[trigger key];
  // a missing player choice pauses the whole turn. NPC decisions come from its policy (deterministic).
  function decide(s, ctrl, defenderId, kind, options, ctx) {
    s.trigger++;
    var tkey = "t" + s.trigger, d = s.actors[defenderId];
    if (!options.length) return null;
    if (d.controller === "player") {
      if (!(tkey in ctrl.choices)) throw new Pause({ key: tkey, actor: defenderId, kind: kind, options: options, context: ctx });
      var c = ctrl.choices[tkey];
      if (c !== null && options.indexOf(c) < 0) throw new Error("choice " + c + " is not one of the offered reactions");
      return c;
    }
    return npcReaction(s, defenderId, kind, options, ctx);
  }
  function reactionOptions(s, defenderId, trigger, ctx) {
    var d = s.actors[defenderId];
    if (d.down || d.reaction_left < 1) return [];
    return d.profiles.filter(function (pid) {
      var p = profile(s, pid); if (!p || p.trigger !== trigger) return false;
      if (p.resolution && p.resolution.counter && ctx.counter) return false;   // trigger fence: no counter from a counter
      if (ctx.depth >= s.catalog.ruleset.trigger_depth_max && p.resolution && p.resolution.counter) return false;
      var r = p.requires || {}, w = d.weapon;
      if (r.weapon_kind && (!w || w.kind !== r.weapon_kind || !w.held)) return false;
      if (r.held && (!w || !w.held)) return false;
      if (r.ignited && w && w.kind === "lightsaber" && !w.ignited) return false;
      if (r.condition && !d.conds[r.condition]) return false;
      if (r.reach_ft && distance(s, defenderId, ctx.attacker) > r.reach_ft) return false;
      return true;
    });
  }

  function hasAdv(s, attacker, defender, p, opts) {
    var A = s.actors[attacker], D = s.actors[defender], adv = [], dis = [];
    if (p.resolution.advantage) adv.push("ambush");
    if (A.conds.hidden) adv.push("unseen");
    if (D.conds.prone && p.resolution.melee) adv.push("prone target");
    if (A.conds.prone) dis.push("attacking from the ground");
    var f = D.conds.feinted; if (f && f.by === attacker && p.resolution.melee) adv.push("feint");
    var bi = D.conds.insight; if (bi && bi.by === attacker) adv.push("Battle Insight");
    if (D.conds.dodging) dis.push("dodging");
    if (opts.dodged) dis.push("readied dodge");
    var t = A.conds.taunted; if (t && t.by !== defender) dis.push("taunted");
    if (A.conds.wary) dis.push("wary");
    return { adv: adv, dis: dis };
  }
  function rangeMods(s, attacker, defender, p) {
    if (p.resolution.melee) return [];
    var out = [], d = distance(s, attacker, defender);
    if (p.resolution.range && d > p.resolution.range.normal) out.push("long range");
    if (s.switches.ranged_in_melee_disadvantage && enemiesOf(s, attacker).some(function (e) { return distance(s, attacker, e) <= 5 && !s.actors[e].conds.hidden; })) out.push("enemy within 5 ft");
    return out;
  }
  function attack(s, ctrl, attacker, defender, pid, opts) {
    opts = opts || {};
    var p = profile(s, pid), A = s.actors[attacker], D = s.actors[defender];
    var ctx = { attacker: attacker, defender: defender, pid: pid, counter: !!p.resolution.counter || !!opts.counter, depth: opts.depth || 0 };
    // reaction window 1: attack declared (readied dodge)
    var dodged = false, o1 = reactionOptions(s, defender, "attack_declared_on_me", ctx);
    if (o1.length) { var c1 = decide(s, ctrl, defender, "attack_declared_on_me", o1, ctx); if (c1) { D.reaction_left--; delete D.conds.dodge_ready; dodged = true; log(s, defender, D.name + " slips the line (Dodge): disadvantage on the attack.", { ev: "dodge", actor: defender, attacker: attacker }); } }
    var ad = hasAdv(s, attacker, defender, p, { dodged: dodged });
    var extra = opts.augment ? [{ label: "Force-guided", sides: 4 }] : [];
    var rng = rangeMods(s, attacker, defender, p); ad.dis = ad.dis.concat(rng);
    var r = rollDice(s, attacker, p.name + " → " + D.name, "1d20+" + p.resolution.bonus, { adv: ad.adv.length > 0, dis: ad.dis.length > 0, extra: extra, kind: "attack", vs: { type: "ac", target: defender, value: D.ac, adv: ad.adv, dis: ad.dis } });
    if (p.resolution.ammo) { A.sidearm.ammo -= 1; }
    // consumed setups
    if (D.conds.feinted && D.conds.feinted.by === attacker && p.resolution.melee) delete D.conds.feinted;
    if (D.conds.insight && D.conds.insight.by === attacker) delete D.conds.insight;
    if (A.conds.wary) delete A.conds.wary;
    if (A.conds.hidden) { delete A.conds.hidden; log(s, attacker, A.name + " is revealed!", { ev: "revealed", actor: attacker }); }
    var nat = r.kept, crit = nat === 20, hit = nat !== 1 && (crit || r.total >= D.ac);
    var why = (ad.adv.length ? " (advantage: " + ad.adv.join(", ") + ")" : "") + (ad.dis.length ? " (disadvantage: " + ad.dis.join(", ") + ")" : "");
    log(s, attacker, A.name + " — " + p.name + " at " + D.name + ": " + r.total + (crit ? " CRITICAL" : "") + why, { main_hand: A.weapon && A.weapon.held ? A.weapon.kind + (A.weapon.kind === "lightsaber" ? (A.weapon.ignited ? ":lit" : ":unlit") : "") : "empty", receipt: r.receipt, ev: "attack", attacker: attacker, defender: defender, pid: pid, total: r.total, nat: nat, crit: crit, adv: ad.adv, dis: ad.dis, counter: ctx.counter, augment: !!opts.augment });
    // reaction window 2: would hit (parry)
    if (hit && !crit && p.resolution.melee) {
      var o2 = reactionOptions(s, defender, "melee_hit_on_me", ctx);
      if (o2.length) { var c2 = decide(s, ctrl, defender, "melee_hit_on_me", o2, Object.assign({ total: r.total }, ctx));
        if (c2) { D.reaction_left--; var bonus = profile(s, c2).resolution.bonus; log(s, defender, D.name + " parries (+" + bonus + " AC).", { ev: "parry", actor: defender, attacker: attacker, turned: r.total < D.ac + bonus }); if (r.total < D.ac + bonus) hit = false; } }
    }
    if (hit) {
      var dmg = rollDice(s, attacker, p.name + " damage", p.resolution.damage, { crit: crit, kind: "damage", vs: { type: "damage", target: defender } });
      var amount = dmg.total;
      // reaction window: ranged energy hit (Lightsaber Deflect)
      if (!p.resolution.melee && p.resolution.damage_type === "energy") {
        var o4 = reactionOptions(s, defender, "ranged_energy_hit_on_me", ctx);
        if (o4.length) { var c4 = decide(s, ctrl, defender, "ranged_energy_hit_on_me", o4, Object.assign({ total: r.total, damage: amount }, ctx));
          if (c4) { D.reaction_left--; var dp = profile(s, c4), red = rollDice(s, defender, dp.name + " (reduce)", dp.resolution.reduce, { kind: "reduce", vs: { type: "reduce", against: amount } });
            var before = amount; amount = Math.max(0, amount - red.total);
            log(s, defender, D.name + " catches the bolt on the blade: " + before + " → " + amount + ".", { receipt: red.receipt, ev: "deflect", actor: defender, attacker: attacker, reduced: before - amount, amount: amount });
            if (amount === 0) {
              // Sheet: "redirect it at one visible creature within 30 ft". The defender's controller picks (or declines).
              var cands = Object.keys(s.actors).filter(function (id) { var X = s.actors[id]; return id !== defender && !X.down && !X.conds.hidden && distance(s, defender, id) <= dp.resolution.redirect_range_ft; });
              var tgt = cands.length ? decide(s, ctrl, defender, "deflect_redirect", cands, Object.assign({ damage: before, shooter: attacker }, ctx)) : null;
              if (tgt) {
                var X = s.actors[tgt], rr = rollDice(s, defender, dp.name + " redirect → " + X.name, "1d20+" + dp.resolution.redirect_bonus, { kind: "attack", vs: { type: "ac", target: tgt, value: X.ac, adv: [], dis: [] } });
                var rhit = rr.kept !== 1 && (rr.kept === 20 || rr.total >= X.ac);
                log(s, defender, D.name + " sends it at " + X.name + ": " + rr.total + (rhit ? " — hit for " + before + "." : " — miss."), { receipt: rr.receipt, ev: "redirect", actor: defender, target: tgt, hit: rhit, amount: rhit ? before : 0, total: rr.total });
                if (rhit) { X.hp = Math.max(0, X.hp - before); log(s, defender, X.name + " takes " + before + " energy damage (" + X.hp + "/" + X.hp_max + ").", { ev: "damage", attacker: defender, target: tgt, pid: c4, amount: before, hp: X.hp, hp_max: X.hp_max, crit: false }); if (X.hp === 0) { X.down = true; log(s, tgt, X.name + " is down.", { ev: "down", actor: tgt }); } }
              } else if (cands.length) log(s, defender, D.name + " lets the stopped bolt die on the blade.", { ev: "redirect_declined", actor: defender });
            } } }
      }
      D.hp = Math.max(0, D.hp - amount);
      log(s, attacker, D.name + " takes " + amount + " " + p.resolution.damage_type + " damage (" + D.hp + "/" + D.hp_max + ").", { receipt: dmg.receipt, ev: "damage", attacker: attacker, target: defender, pid: pid, amount: amount, rolled: dmg.total, hp: D.hp, hp_max: D.hp_max, crit: crit });
      if (D.hp === 0) { D.down = true; log(s, defender, D.name + " is down.", { ev: "down", actor: defender }); }
    } else {
      log(s, attacker, "Miss.", { ev: "miss", attacker: attacker, defender: defender, pid: pid });
      // reaction window 3: missed (riposte) — fenced: never from a counter, bounded depth
      if (p.resolution.melee && !D.down) {
        var o3 = reactionOptions(s, defender, "melee_miss_on_me", ctx);
        if (o3.length) { var c3 = decide(s, ctrl, defender, "melee_miss_on_me", o3, ctx);
          if (c3) { D.reaction_left--; log(s, defender, D.name + " ripostes!", { ev: "riposte", actor: defender }); attack(s, ctrl, defender, attacker, c3, { counter: true, depth: (ctx.depth || 0) + 1 }); } }
      }
    }
    return { hit: hit, crit: crit, receipt: r.receipt };
  }
  function contest(s, actorId, targetId, p) {
    var A = s.actors[actorId], T = s.actors[targetId];
    var ask = p.resolution.actor_skill, tsk = p.resolution.target_skill;
    var am = A.skills[ask] != null ? A.skills[ask] : (A.abilities.wis || 0);
    var tm = tsk === "athletics_or_acrobatics" ? Math.max(T.skills.athletics || 0, T.skills.acrobatics || 0) : (T.skills[tsk] != null ? T.skills[tsk] : (T.abilities.wis || 0));
    if (p.resolution.actor_bonus != null) am = p.resolution.actor_bonus;
    var tl = tsk === "athletics_or_acrobatics" ? "athletics/acrobatics" : tsk;
    var a = rollDice(s, actorId, p.name + " (" + (p.resolution.actor_bonus != null ? "martial check" : ask.replace("_", " ")) + ")", "1d20" + (am >= 0 ? "+" : "") + am, { adv: !!(A.advantage_on && A.advantage_on[ask]), kind: "contest", vs: { type: "opposed", target: targetId, skill: tl } });
    var t = rollDice(s, targetId, "resists " + p.name + " (" + tl + ")", "1d20" + (tm >= 0 ? "+" : "") + tm, { adv: !!(T.advantage_on && T.advantage_on[tsk]), kind: "contest", vs: { type: "opposed_against", target: actorId, value: a.total } });
    var win = a.total > t.total;
    log(s, actorId, A.name + " — " + p.name + ": " + a.total + " vs " + t.total + " → " + (win ? "success" : "fails"), { receipt: a.receipt + "," + t.receipt, ev: "contest", actor: actorId, target: targetId, pid: p.id || null, a: a.total, t: t.total, win: win });
    return win;
  }

  function execStep(s, ctrl, actorId, step) {
    var a = s.actors[actorId], p = profile(s, step.pid);
    var av = availability(s, actorId, step.pid, step, project(s, actorId));   // revalidate against current, real state
    if (!av.ok) { log(s, actorId, a.name + " cannot " + p.name + " now: " + av.reasons.map(function (r) { return r.text; }).join(" "), { refused: true }); return false; }
    var proj = project(s, actorId); spend(proj, av.cost);
    a.budget = proj.budget; a.fp = proj.fp; a.reaction_left = proj.reaction_left;
    if (p.cap) a.used["cap:" + p.cap.group] = (a.used["cap:" + p.cap.group] || 0) + 1;
    if (step.augment) a.used["cap:augment"] = 1;
    var T = step.target && s.actors[step.target];
    if (step.pid === "move") return doMove(s, ctrl, actorId, step);
    if (step.pid === "speak") { log(s, actorId, a.name + ": “" + (step.text || "…") + "”", { speech: true }); return true; }
    if (step.pid === "toggle_blade") { a.weapon.ignited = !a.weapon.ignited; log(s, actorId, a.name + (a.weapon.ignited ? " ignites" : " deactivates") + " the blade."); return true; }
    if (step.pid === "draw_sidearm") { a.sidearm.held = true; log(s, actorId, a.name + " draws the " + a.sidearm.name + " (" + a.sidearm.ammo + "/" + a.sidearm.capacity + ").", { ev: "draw", actor: actorId }); return true; }
    if (step.pid === "holster_sidearm") { a.sidearm.held = false; log(s, actorId, a.name + " holsters the " + a.sidearm.name + ".", { ev: "holster", actor: actorId }); return true; }
    if (step.pid === "reload_sidearm") { var need = a.sidearm.capacity - a.sidearm.ammo, take = Math.min(need, a.sidearm.reserve); a.sidearm.ammo += take; a.sidearm.reserve -= take; log(s, actorId, a.name + " reloads: " + a.sidearm.ammo + "/" + a.sidearm.capacity + " (" + a.sidearm.reserve + " in reserve).", { ev: "reload", actor: actorId }); return true; }
    if (p.resolution && p.resolution.type === "area_save") return areaSave(s, ctrl, actorId, p);
    if (step.pid === "recover_weapon") { a.weapon = clone(a.dropped); a.weapon.held = true; if (a.weapon.kind === "lightsaber") a.weapon.ignited = false; a.dropped = null; log(s, actorId, a.name + " recovers the " + a.weapon.name + "."); return true; }
    if (p.effect && p.effect.sets_on_target && T) { T.conds[p.effect.sets_on_target] = { by: actorId }; log(s, actorId, a.name + " — " + p.name + " on " + T.name + ". " + p.effect.note, { ev: "effect", actor: actorId, target: step.target, pid: step.pid }); return true; }
    if (p.effect && p.effect.sets) { a.conds[p.effect.sets] = { until: actorId }; log(s, actorId, a.name + " — " + p.name + ". " + p.effect.note); return true; }
    if (step.pid === "battle_insight" || step.pid === "battle_insight_bonus") { T.conds.insight = { by: actorId }; log(s, actorId, a.name + " reads " + T.name + " through the Force: advantage on the next attack.", { ev: "effect", actor: actorId, target: step.target, pid: step.pid }); return true; }
    if (step.pid === "tactical_glance") {
      var hiddenFoes = enemiesOf(s, actorId).filter(function (e) { return s.actors[e].conds.hidden; });
      var r = rollDice(s, actorId, "Tactical Glance (perception)", "1d20+" + (a.skills.perception || 0));
      var found = hiddenFoes.filter(function (e) { return r.total >= (s.actors[e].stealth_dc || 10); });   // DC stays engine-side
      found.forEach(function (e) { delete s.actors[e].conds.hidden; });
      log(s, actorId, a.name + " scans: " + r.total + (found.length ? " — you spot " + found.map(function (e) { return s.actors[e].name; }).join(", ") + "." : " — nothing you can pin down."), { receipt: r.receipt });
      return true;
    }
    if (p.resolution && p.resolution.type === "attack") {
      if (step.pid === "pounce") { setDistance(s, actorId, step.target, 5); }
      attack(s, ctrl, actorId, step.target, step.pid, { augment: !!step.augment });
      a.used.melee_attacked = true;
      return true;
    }
    if (p.resolution && p.resolution.type === "contest") {
      var win = contest(s, actorId, step.target, p);
      if (win) {
        var eff = p.effect.on_success;
        if (eff === "disarmed") { T.dropped = clone(T.weapon); T.weapon.held = false; if (T.weapon.kind === "lightsaber") T.weapon.ignited = false; log(s, step.target, T.name + "'s " + T.weapon.name + " is stripped away and lands 10 ft off.", { ev: "disarm", actor: actorId, target: step.target }); }
        else if (eff === "feinted") { T.conds.feinted = { by: actorId }; log(s, step.target, T.name + " bites on the feint.", { ev: "feinted", actor: actorId, target: step.target }); }
        else if (eff === "taunted") { T.conds.taunted = { by: actorId, until: actorId }; log(s, step.target, T.name + " is drawn to " + a.name + "."); }
        else if (eff === "disarmed_prone") { T.dropped = clone(T.weapon); T.weapon.held = false; if (T.weapon.kind === "lightsaber") T.weapon.ignited = false; T.conds.prone = { by: actorId }; log(s, step.target, T.name + " is bound, stripped and swept to the ground; the " + T.weapon.name + " skids 10 ft off.", { ev: "takedown", actor: actorId, target: step.target }); }
        else if (eff === "grappled") { T.conds.grappled = { by: actorId }; a.conds.grappling = { target: step.target }; log(s, step.target, T.name + " is caught in an Echani hold: speed 0.", { ev: "grapple", actor: actorId, target: step.target }); }
        else if (eff === "wary") { T.conds.wary = { by: actorId }; log(s, step.target, T.name + " hesitates."); }
      } else if (step.pid === "feint") log(s, step.target, T.name + " reads the feint and does not commit.");
      return true;
    }
    return true;
  }
  function areaSave(s, ctrl, actorId, p) {
    var a = s.actors[actorId], R = p.resolution;
    log(s, actorId, a.name + " — " + p.name + ".", { ev: "power", actor: actorId, pid: p.id });
    var inside = Object.keys(s.actors).filter(function (id) { return id !== actorId && !s.actors[id].down && distance(s, actorId, id) <= R.radius_ft; });
    if (!inside.length) { log(s, actorId, "Nothing is close enough to catch it.", { ev: "no_targets", actor: actorId }); return true; }
    inside.forEach(function (id) {
      var T = s.actors[id], mod = (T.abilities && T.abilities[R.save]) || 0;
      var sv = rollDice(s, id, T.name + " " + R.save.toUpperCase() + " save vs " + p.name, "1d20" + (mod >= 0 ? "+" : "") + mod, { kind: "save", vs: { type: "dc", value: R.dc } });
      var ok = sv.total >= R.dc;
      log(s, id, T.name + " " + (ok ? "rides it out" : "is thrown") + " (" + sv.total + " vs DC " + R.dc + ").", { receipt: sv.receipt, ev: "save", actor: id, pid: p.id, total: sv.total, dc: R.dc, win: ok });
      if (!ok) {
        var dmg = rollDice(s, actorId, p.name + " damage", R.damage, { kind: "damage", vs: { type: "damage", target: id } });
        T.hp = Math.max(0, T.hp - dmg.total); T.conds.prone = { by: actorId };
        log(s, actorId, T.name + " takes " + dmg.total + " " + R.damage_type + " damage and goes prone (" + T.hp + "/" + T.hp_max + ").", { receipt: dmg.receipt, ev: "damage", attacker: actorId, target: id, pid: p.id, amount: dmg.total, hp: T.hp, hp_max: T.hp_max, crit: false });
        if (T.hp === 0) { T.down = true; log(s, id, T.name + " is down.", { ev: "down", actor: id }); }
      }
    });
    return true;
  }
  function doMove(s, ctrl, actorId, step) {
    var a = s.actors[actorId];
    if (a.conds.grappling) { var g = a.conds.grappling.target; delete a.conds.grappling; if (s.actors[g]) delete s.actors[g].conds.grappled; log(s, actorId, a.name + " lets go of the hold to move.", { ev: "release", actor: actorId }); }
    // leaving reach of adjacent enemies provokes (closing on a target does not)
    var leaving = enemiesOf(s, actorId).filter(function (e) { return distance(s, actorId, e) <= 5 && !(step.dest === "close" && e === step.target); });
    for (var i = 0; i < leaving.length; i++) {
      var e = leaving[i], E = s.actors[e];
      if (E.reaction_left < 1 || E.down) continue;
      var melee = E.profiles.filter(function (pid) { var p = profile(s, pid); return p && p.resolution && p.resolution.melee && !p.trigger && !(p.requires || {}).condition && (!((p.requires || {}).weapon_kind) || (E.weapon && E.weapon.held && E.weapon.kind === p.requires.weapon_kind && (E.weapon.kind !== "lightsaber" || E.weapon.ignited))); });
      if (!melee.length) continue;
      var choice = decide(s, ctrl, e, "opportunity_attack", melee.slice(0, 1), { attacker: actorId, defender: e, depth: 0 });
      if (choice) { E.reaction_left--; log(s, e, E.name + " takes an opportunity attack as " + a.name + " pulls away."); attack(s, ctrl, e, actorId, choice, { depth: 1 }); if (a.down) return true; }
    }
    if (step.dest === "close") { setDistance(s, actorId, step.target, 5); log(s, actorId, a.name + " closes on " + s.actors[step.target].name + ".", { ev: "close", actor: actorId, target: step.target }); }
    else { enemiesOf(s, actorId).forEach(function (e2) { setDistance(s, actorId, e2, distance(s, actorId, e2) + 15); }); log(s, actorId, a.name + " withdraws 15 ft."); }
    // a feint only holds while you stay engaged
    Object.keys(s.actors).forEach(function (t) { var f = s.actors[t].conds.feinted; if (f && (f.by === actorId || t === actorId) && distance(s, f.by, t) > 5) { delete s.actors[t].conds.feinted; log(s, t, "The feint's opening closes as the distance opens."); } });
    return true;
  }

  // Resolve one actor's whole declared plan. Pure: returns a new state. Throws nothing on a player reaction:
  // returns {paused} with the prompt, and the caller re-runs with choices[prompt.key] set.
  function resolveTurn(s0, actorId, plan, choices) {
    var v = validatePlan(s0, actorId, plan);
    if (!v.legal) return { state: s0, refused: v };
    var s = clone(s0), ctrl = { choices: choices || {} }, a = s.actors[actorId];
    var startLog = s.log.length, startRec = s.receipts.length;
    try {
      log(s, actorId, a.name + "'s turn.", { turn_start: true });
      for (var i = 0; i < plan.length; i++) {
        if (a.down) { log(s, actorId, "Remaining steps cancelled: " + a.name + " is down.", { refused: true }); break; }
        s._step = i; execStep(s, ctrl, actorId, plan[i]);
        checkOver(s);
        if (s.over) break;
      }
    } catch (e) {
      if (e instanceof Pause) return { state: s0, paused: e.pause, preview_log: s.log.slice(startLog), preview_receipts: s.receipts.slice(startRec) };
      if (e instanceof NeedDice) return { state: s0, need_dice: e.need, preview_log: s.log.slice(startLog), preview_receipts: s.receipts.slice(startRec) };
      throw e;
    }
    delete s._step;
    return { state: s, log: s.log.slice(startLog), receipts: s.receipts.slice(startRec) };
  }
  // acceptDice: append Atomic-accepted values. Same seq + same value = no-op (idempotent retry); anything else is refused.
  function acceptDice(s0, rolls) {
    var s = clone(s0);
    rolls.forEach(function (r) {
      var have = s.tape[r.seq];
      if (have) { if (have.sides !== r.sides || have.value !== r.value) throw new Error("TAPE_CONFLICT at seq " + r.seq); return; }
      if (r.seq !== s.tape.length) throw new Error("TAPE_GAP: expected seq " + s.tape.length + ", got " + r.seq);
      if (!(r.value >= 1 && r.value <= r.sides)) throw new Error("TAPE_VALUE_OUT_OF_RANGE at seq " + r.seq);
      s.tape.push({ seq: r.seq, sides: r.sides, value: r.value, roll_id: r.roll_id || null, roller: r.roller || null });
    });
    return s;
  }
  function checkOver(s) {
    var sides = {}; Object.keys(s.actors).forEach(function (id) { var a = s.actors[id]; sides[a.side] = sides[a.side] || !a.down; });
    if (!sides.party) s.over = "defeat"; else if (Object.keys(sides).some(function (k) { return k !== "party" && sides[k] === false; }) && !Object.keys(sides).some(function (k) { return k !== "party" && sides[k]; })) s.over = "victory";
  }
  function endTurn(s0) {
    var s = clone(s0);
    if (s.over) return s;
    do { s.turn++; if (s.turn >= s.order.length) { s.turn = 0; s.round++; } } while (s.actors[current(s)].down);
    // reactions refresh at the start of each actor's own turn
    startTurn(s);
    return s;
  }

  // ---------------- NPC policies (decide plans; the same validator judges them) ----------------
  function npcPlan(s, actorId) {
    var a = s.actors[actorId], foes = enemiesOf(s, actorId).filter(function (e) { return visibleTo(s, actorId, e); });
    if (!foes.length) return [];
    var t = foes[0], d = distance(s, actorId, t), plan = [];
    if (a.policy === "ambusher") {
      if (a.conds.hidden && d <= 25) return [{ pid: "pounce", target: t }];
      if (d > 5 && !a.conds.grappled) plan.push({ pid: "move", dest: "close", target: t });
      plan.push({ pid: "bite", target: t });
      return plan;
    }
    if (a.policy === "gunner") {   // keeps shooting; slams if someone is in its face
      if (d <= 5) return [{ pid: "npc_slam", target: t }];
      if (d > 120) plan.push({ pid: "move", dest: "close", target: t });
      plan.push({ pid: "npc_blaster", target: t });
      return plan;
    }
    // duelist: recover a dropped blade first; feint when it can; bind an armed foe when the blade is ready; else strike
    if (a.dropped) return [{ pid: "recover_weapon" }];
    if (d > 5) plan.push({ pid: "move", dest: "close", target: t });
    var T = s.actors[t];
    if (s.switches.secondary_action && !(T.conds.feinted)) plan.push({ pid: "feint", target: t });
    if (T.weapon && T.weapon.held && s.round % 2 === 0) plan.push({ pid: "npc_bind", target: t });
    else plan.push({ pid: "npc_blade", target: t });
    var v = validatePlan(s, actorId, plan);
    if (!v.legal) plan = plan.filter(function (st, i) { return v.steps[i] && v.steps[i].ok; });
    return plan;
  }
  function npcReaction(s, defenderId, kind, options, ctx) {
    var D = s.actors[defenderId];
    if (kind === "opportunity_attack") return options[0];
    if (kind === "melee_hit_on_me") return ctx.total < D.ac + 2 ? options[0] : null;   // parry only when it can matter
    if (kind === "melee_miss_on_me") return options[0];
    if (kind === "attack_declared_on_me") return options[0];
    return null;
  }

  // ---------------- public view: what the player may see ----------------
  // opts.full_mechanics (sandbox debug only): enemy HP and budgets are shown. Campaign play must follow the adopted
  // player-information policy instead. Hidden actors stay hidden either way.
  function publicView(s, viewer, opts) {
    viewer = viewer || "aero"; opts = opts || {}; var full = !!opts.full_mechanics, showHp = full || !!opts.show_enemy_hp;
    var actors = {};
    Object.keys(s.actors).forEach(function (id) {
      var a = s.actors[id];
      if (!visibleTo(s, viewer, id)) return;
      var own = a.side === s.actors[viewer].side;
      actors[id] = { id: id, name: a.name, side: a.side, kind: a.kind, down: a.down, distance: distance(s, viewer, id),
                     hp: own || showHp ? a.hp : null, hp_max: own || showHp ? a.hp_max : null, ac: own || full ? a.ac : null, condition: own ? null : (a.hp <= a.hp_max / 2 ? "bloodied" : a.hp < a.hp_max ? "hurt" : "unhurt"),
                     conds: Object.keys(a.conds).filter(function (c) { return c !== "hidden"; }), weapon: a.weapon ? { name: a.weapon.name, held: a.weapon.held, ignited: a.weapon.ignited } : null, sidearm: own && a.sidearm ? clone(a.sidearm) : null,
                     budget: own || full ? a.budget : null, reaction_left: own || full ? a.reaction_left : null, fp: own ? a.fp : null };
    });
    var hiddenSeen = Object.keys(s.actors).some(function (id) { return !visibleTo(s, viewer, id); });
    return { canonical: false, round: s.round, current: current(s), actors: actors, unseen_presence: hiddenSeen ? "Something is out there you cannot see." : null,
             log: s.log.filter(function (e) { return !e.hidden; }), receipts: s.receipts, over: s.over, switches: s.switches };
  }

  return { newState: newState, validatePlan: validatePlan, availability: availability, resolveTurn: resolveTurn, endTurn: endTurn,
           acceptDice: acceptDice, _localDie: localDie, rangeMods: rangeMods, confirmedCombos: confirmedCombos, npcPlan: npcPlan, comboJudge: comboJudge, synergies: synergies, hasAdv: hasAdv, reactionOptions: reactionOptions, cinematicNote: cinematicNote, publicView: publicView, current: current,
           distance: distance, project: project, _rollDice: rollDice };
});
