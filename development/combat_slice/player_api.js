// CC-005c server-side PLAYER API (runs inside the Atomic engine worker, never in the browser).
// Everything a thin player client may see is computed here from the authoritative state, using only what the
// viewer may know: own sheet and own capability cards in full; others via engine.playerProjection; enemy AC only as
// learned bounds; odds as ranges over those bounds. No NPC stat block, profile catalog or plan leaves the server.
const E = require("./engine.js"), P = require("./predict.js"), SOUL = require("./soul.js");
const VIEWER = "aero";
function clone(x) { return JSON.parse(JSON.stringify(x)); }
// Action-economy category, derived from the profile's own data (cost, trigger, maneuver) — never from its display name.
const CATEGORIES = ["maneuver", "attack", "main", "secondary", "bonus", "reaction", "movement", "object", "free"];
function categoryOf(p, pid) {
  const c = p.cost || {}, m = p.maneuver || "";
  if (p.trigger) return "reaction";
  if (p.compound || /^(Feint|Disarm|Dodge|Setup|Provoke)/.test(m)) return "maneuver";
  if ((m === "Attack" || m === "Grapple") && c.main) return "attack";
  if (c.main) return "main"; if (c.secondary) return "secondary"; if (c.bonus) return "bonus";
  if (pid === "move" || c.movement_ft) return "movement"; if (c.object) return "object";
  return "free";
}
function cardOf(p, pid) {   // own capability card: the player's own sheet data (safe to show)
  return { pid, name: p.name, category: categoryOf(p, pid), maneuver: p.maneuver, technique: p.technique || null, status: p.status, cost: p.cost || {}, trigger: p.trigger || null,
           rules: p.rules, source: p.source, compound: !!p.compound, inert_note: p.inert_note || null, needs_target: !!(p.requires && (p.requires.target === "enemy" || p.requires.target === "beast")),
           needs_object: !!(p.requires && p.requires.telekinesis), resolution: p.resolution && p.resolution.type === "attack" ? { bonus: p.resolution.bonus, damage: p.resolution.damage, melee: p.resolution.melee } : null };
}
function visibleFoes(s) { const v = E.publicView(s, VIEWER); return Object.keys(v.actors).filter((id) => v.actors[id].side !== s.actors[VIEWER].side && !v.actors[id].down); }
function defaultStep(s, pid) {
  const p = s.catalog.profiles[pid], r = p.requires || {}, foes = visibleFoes(s);
  if (pid === "move") return { pid, dest: foes.length ? "close" : "withdraw", target: foes[0] };
  if (r.target === "enemy" || r.target === "beast") return { pid, target: foes[0] };
  if (pid === "minor_telekinesis") { const A = s.actors[VIEWER]; if (A.dropped) return { pid, object: "own_weapon" }; const f = Object.keys(s.actors).find((id) => id !== VIEWER && s.actors[id].dropped && !s.actors[id].dropped.far && visibleFoes(s).includes(id)); return { pid, object: f ? f + "_weapon" : null }; }
  return { pid };
}
// Reasons are about the viewer's own state, or about facts the viewer can see (distance, held weapon); never NPC numbers.
function cards(s, plan) {
  const A = s.actors[VIEWER], myTurn = !s.over && E.current(s) === VIEWER, v = E.validatePlan(s, VIEWER, plan || []), proj = v.proj || E.project(s, VIEWER);
  return A.profiles.filter((pid) => s.catalog.profiles[pid] && pid !== "force_augment").map((pid) => {
    const p = s.catalog.profiles[pid], c = cardOf(p, pid);
    if (p.trigger) { c.reaction = true; c.ready = A.reaction_left > 0; return c; }
    const ps = proj && proj.dist ? Object.assign({}, s, { dist: proj.dist }) : s;   // judge targets at the projected distances
    const av = E.availability(s, VIEWER, pid, defaultStep(ps, pid), proj);
    c.available = myTurn && av.ok; c.reason = !myTurn ? (s.over ? "The fight is over." : "Not your turn.") : av.ok ? null : bestReason(av.reasons); c.cost_now = av.cost || p.cost || {};
    return c;
  });
}
function bestReason(rs) { const spec = rs.filter((r) => !/^NO_(MAIN|BONUS|SECONDARY|OBJECT|MOVEMENT_FT|REACTION|FP)$/.test(r.code)); return (spec[0] || rs[0]).text; }
// Preflight for a proposed plan: legality per step, costs, budget after, predicted synergies, odds RANGES from known state.
function preflight(s, plan) {
  const v = E.validatePlan(s, VIEWER, plan || []), know = E.knowledge(s, VIEWER), an = P.analyzePlan(s, VIEWER, plan || []);
  const steps = (plan || []).map((st, i) => {
    const sv = v.steps[i] || { ok: false, reasons: [] }, a = an.steps[i] || {}, out = { pid: st.pid, ok: sv.ok, reasons: sv.reasons.map((r) => r.text), cost: sv.cost || {} };
    if (a.kind === "attack") {
      const T = s.actors[st.target], mine = T && T.side === s.actors[VIEWER].side, b = know[st.target] || {}, lo = b.ac_min != null ? b.ac_min : 10, hi = b.ac_max != null ? b.ac_max : 20;
      const mode = a.mode === "conditional" ? "normal" : a.mode, bonus = s.catalog.profiles[st.pid].resolution.bonus, x = a.adv.length > 0 && a.dis.length === 0, ext = !!st.augment;
      out.odds = mine ? { hit: a.hit } : { hit_min: P.attackOdds(bonus, hi, mode, { extraD4: ext }).hit, hit_max: P.attackOdds(bonus, lo, mode, { extraD4: ext }).hit, ac_known: b, assumed_unknown: b.ac_min == null || b.ac_max == null };
      out.mode = a.mode; out.adv = a.adv; out.dis = a.dis; out.distance_ft = a.distance_ft; out.damage = { min: a.damage.min, max: a.damage.max, crit_min: a.crit_damage.min, crit_max: a.crit_damage.max };
      if (a.feint_conditional != null) out.conditional_on_feint = true;
    }
    if (a.kind === "contest") out.odds = { contest: "opposed by a skill you do not know" };
    return out;
  });
  const sy = E.synergies(s, VIEWER, plan || []).map((x) => ({ id: x.id, name: x.name, status: x.status, steps: x.steps, legal: x.legal, links: x.links, conditional: x.conditional }));
  return { legal: v.legal && (plan || []).length > 0, steps, budget_after: v.budget_after, fp_after: v.fp_after, synergies: sy, cards: cards(s, plan || []),
           compound: (plan || []).filter((st) => { const p = s.catalog.profiles[st.pid]; return p && (p.compound || ["main", "secondary", "bonus", "reaction"].filter((k) => (p.cost || {})[k]).length > 1); }).map((st) => ({ name: s.catalog.profiles[st.pid].name, cost: s.catalog.profiles[st.pid].cost })) };
}
// The whole player view: projection + own cards + scenario intro + pending player checkpoint (sanitized) + last-turn combos.
function playerView(s, pending, scenarios, scenarioId) {
  const v = E.playerProjection(s, VIEWER), know = E.knowledge(s, VIEWER), sc = scenarios.scenarios[scenarioId] || {};
  v.scenario = { id: scenarioId, title: sc.title, intro: sc.intro };
  v.me = { id: VIEWER, name: s.actors[VIEWER].name, campaign_grants: s.actors[VIEWER].campaign_grants || [], sidearm: clone(s.actors[VIEWER].sidearm || null), dropped: !!s.actors[VIEWER].dropped, fp_max: s.actors[VIEWER].fp_max };
  v.cards = cards(s, []);
  v.not_on_sheet = (scenarios.aero.not_on_sheet || []).filter((x) => !(s.actors[VIEWER].profiles.includes("minor_telekinesis") && /Telekinesis/.test(x.name)));
  if (pending && pending.need && pending.need.controller === "player") {
    const n = pending.need, vs = clone(n.vs || null);
    if (vs && vs.type === "ac" && s.actors[vs.target] && s.actors[vs.target].side !== s.actors[VIEWER].side) { delete vs.value; vs.known = know[vs.target] || null; }
    v.checkpoint = { kind: "roll", turn_key: pending.turn_key, purpose: n.purpose, formula: n.formula, mode: n.mode, dice: n.dice, extra: n.extra, vs, roll_kind: n.kind };
  } else if (pending && pending.paused && pending.paused.controller === "player") {
    const pz = pending.paused;
    v.checkpoint = { kind: "decision", turn_key: pending.turn_key, key: pz.key, decision: pz.kind, options: pz.options.map((o) => s.catalog.profiles[o] ? { id: o, name: s.catalog.profiles[o].name, rules: s.catalog.profiles[o].rules } : { id: o, name: s.actors[o] ? s.actors[o].name : o, distance_ft: s.actors[o] ? E.distance(s, VIEWER, o) : null }), context: pz.public_context || null };
  } else if (pending) v.checkpoint = { kind: "waiting", on: "gm" };
  else v.checkpoint = s.over ? { kind: "over", result: s.over } : E.current(s) === VIEWER ? { kind: "plan" } : { kind: "waiting", on: "gm" };
  // confirmed combos of the viewer's most recent completed turn (from resolved events only)
  let start = -1; for (let i = s.log.length - 1; i >= 0; i--) if (s.log[i].turn_start && s.log[i].who === VIEWER) { start = i; break; }
  if (start >= 0) { let end = s.log.length; for (let i = start + 1; i < s.log.length; i++) if (s.log[i].turn_start) { end = i; break; } v.last_combos = E.confirmedCombos(s, s.log.slice(start, end)).map((c) => ({ name: c.name, hits: c.hits, attacks: c.attacks })); }
  // Soul narration runs HERE, on the player-visible log only (frozen facts); the browser just displays it.
  const names = {}; Object.keys(v.actors).forEach((id) => { names[id] = v.actors[id].name; });
  // narrate from the visible events with their internal ids (for move-specific wording); only the TEXT leaves the server
  const visibleLog = E.publicView(s, VIEWER).log.filter((l) => [l.actor, l.attacker, l.target, l.defender].every((id) => !id || !!v.actors[id]));
  const turns = []; let cur = null; visibleLog.forEach((l) => { if (l.turn_start) { cur = { who: l.who, round: l.round, log: [] }; turns.push(cur); } else if (cur) cur.log.push(l); });
  v.story = turns.map((t) => ({ round: t.round, who: names[t.who] || "Someone", beats: SOUL.narrate(t.log, names).beats.map((b) => b.text) })).filter((t) => t.beats.length);
  return v;
}
module.exports = { CATEGORIES, categoryOf, cards, preflight, playerView };
