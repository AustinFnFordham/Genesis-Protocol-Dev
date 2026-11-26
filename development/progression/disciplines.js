// Shared Discipline XP allocation (CC-008 E) — versioned, bounded, deterministic, replayable, evidence-justified. SANDBOX.
// observation: { observation_id, actor, pid, authority, committed, validated, scene, facts, chain_id?, participants? }
// One observation → { primary: {track, xp} | null, pools: [{track, xp}] } after bounds and anti-farming. Awards go through
// framework.awardXp with event_id = observation id, so each track credits an observation at most once.
"use strict";
const F = require("./framework.js");
function ruleFor(policy, pid) { return policy.rules.find((r) => r.pids.includes(pid)) || null; }
function obsKey(rule, ob) { return rule && rule.observation_from === "dodge_chain_id" && ob.chain_id ? "chain:" + ob.chain_id : ob.observation_id; }
// Pure allocation: what this observation may credit, before ledger state (anti-farming caps need ledger counters → apply()).
function allocate(policy, ob, owned) {
  const why = [];
  if (!ob || ob.committed !== true || ob.validated !== true) return { credit: null, reason: "NOT_COMMITTED_OR_VALIDATED" };
  if (ob.authority !== "atomic" && ob.authority !== "atomic_exploration") return { credit: null, reason: "UNTRUSTED_AUTHORITY" };
  if (!(owned || []).includes(ob.pid)) return { credit: null, reason: "UNLEARNED_CAPABILITY" };   // narrated or unowned: nothing
  const rule = ruleFor(policy, ob.pid); if (!rule) return { credit: null, reason: "NO_RULE" };
  if (rule.requires_owned && !rule.requires_owned.every((p) => (owned || []).includes(p))) return { credit: null, reason: "MISSING_COMPONENT" };
  if (rule.requires_fact && !(ob.facts || {})[rule.requires_fact]) return { credit: null, reason: "NOT_MEANINGFUL", rule: rule.id };
  if ((rule.setup_only_pids || []).includes(ob.pid)) return { credit: null, reason: "SETUP_ONLY", rule: rule.id };
  let pools = rule.pools.slice();
  Object.keys(rule.when_fact || {}).forEach((f) => { if ((ob.facts || {})[f]) pools = pools.concat(rule.when_fact[f].add_pools); });
  pools = Array.from(new Set(pools)).slice(0, policy.bounds.max_pools_per_observation);
  let budget = policy.bounds.max_discipline_xp_per_observation;
  const out = pools.map((p) => { const xp = Math.min(policy.bounds.max_pool_xp_per_observation, budget); budget -= xp; return { track: "discipline:" + p, xp, pool: p }; }).filter((x) => x.xp > 0);
  return { credit: { key: obsKey(rule, ob), rule: rule.id, primary: rule.primary ? { track: rule.primary, xp: 1 } : null, pools: out, policy: policy.version } };
}
// Apply to a character: anti-farming counters, then one idempotent award per target track.
function apply(trees, ch, policy, ob, owned) {
  const a = allocate(policy, ob, owned); if (!a.credit) return { ok: true, awarded: [], reason: a.reason, state: ch };
  let s = F.clone(ch); s.counters = s.counters || {}; const awarded = [], skipped = [];
  const ev = (track, xp) => ({ event_id: a.credit.key, authority: ob.authority, committed: true, validated: true, type: "observation", actor: ob.actor, facts: ob.facts || {}, _xp: xp });
  const targets = (a.credit.primary ? [a.credit.primary] : []).concat(a.credit.pools);
  for (const t of targets) {
    const tree = trees[t.track]; if (!tree) { skipped.push({ track: t.track, reason: "TRACK_NOT_LOADED" }); continue; }
    const pool = t.pool, cap = pool && policy.anti_farming[pool], ck = cap ? [ob.scene || "-", pool].join("|") : null;
    if (s.applied[t.track + "|" + a.credit.key]) { skipped.push({ track: t.track, reason: "DUPLICATE" }); continue; }
    if (cap && (s.counters[ck] || 0) >= cap.per_scene_cap) { skipped.push({ track: t.track, reason: "SCENE_CAP" }); continue; }
    const r = F.awardXp(trees, s, t.track, ev(t.track, t.xp), t.xp);
    if (!r.ok) { skipped.push({ track: t.track, reason: r.code }); continue; }
    if (r.duplicate) { skipped.push({ track: t.track, reason: "DUPLICATE" }); continue; }
    s = r.state; if (ck) { s.counters = s.counters || {}; s.counters[ck] = (s.counters[ck] || 0) + 1; }
    awarded.push({ track: t.track, xp: t.xp, receipt: r.receipt.id });
  }
  return { ok: true, awarded, skipped, rule: a.credit.rule, key: a.credit.key, state: s };
}
// Team event: each participant's own committed contribution is a separate observation for that actor only.
function applyTeam(trees, chars, policy, team, ownedBy) {
  const out = {}; for (const p of team.participants) { const ch = chars[p.actor]; if (!ch) continue;
    const ob = Object.assign({ authority: team.authority, committed: p.committed, validated: p.validated, scene: team.scene }, p, { observation_id: team.team_event_id + ":" + p.actor });
    out[p.actor] = apply(trees, ch, policy, ob, ownedBy[p.actor]); }
  return out;
}
// Discipline and mastery trees implied by a policy (candidate fixtures so awards have somewhere to land).
function treesForPolicy(policy, curve) {
  const c = curve || { id: "quadratic/1", params: { a: 10, b: 5, c: 1 } }, mk = (id, layer, q) => ({ schema: F.SCHEMA, id, version: policy.version, status: "candidate", layer, provenance: { source: "implied by " + policy.schema + " " + policy.version },
    track: { start_level: 0, max_level: 20, xp_quantity: q, curve: c, curve_status: "candidate", cadence: [5, 10, 15, 20] }, evidence: { accepted_authorities: ["atomic", "atomic_exploration"], event_types: { observation: { xp: 1 } } }, nodes: [] });
  const list = policy.disciplines.map((d) => mk("discipline:" + d, "discipline", "discipline_xp"));
  Array.from(new Set(policy.rules.map((r) => r.primary).filter(Boolean))).forEach((p) => list.push(mk(p, "specialized_mastery", "mastery_xp")));
  return list;
}
module.exports = { allocate, apply, applyTeam, treesForPolicy, ruleFor };
