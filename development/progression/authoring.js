// Authoring and quality checks for proposed progression trees (CC-008 G). Read-only: never touches the game runtime.
// review(trees, opts) → { ok, errors, warnings, reachability, tables, edges } ; markdown(report) → readable tables + dependency graph.
"use strict";
const fs = require("fs"), path = require("path"), V = require("./validate.js"), CU = require("./curves.js");
const REPO = path.join(__dirname, "../..");
function registryUrids() {   // approved Registry identities (golden slice global definitions + campaign-local)
  const out = new Set(), dirs = ["registry/golden_slice/global_definitions", "registry/golden_slice/campaign_local"];
  dirs.forEach((d) => { const p = path.join(REPO, d); if (!fs.existsSync(p)) return; fs.readdirSync(p).filter((f) => f.endsWith(".yml")).forEach((f) => { const m = /^urid:\s*(\S+)/m.exec(fs.readFileSync(path.join(p, f), "utf8")); if (m) out.add(m[1]); }); });
  return out;
}
const refToUrid = (ref) => { const [kind, id] = ref.split(":"); return kind === "feature" ? "feature_" + id : kind === "archetype" ? "subclass_" + id.replace(/^sentinel_/, "") : null; };
function reachability(trees) {
  // Optimistic fixed point: a node is reachable if its level ≤ its track's max and its requirements can be met by reachable nodes/levels.
  const byId = {}; trees.forEach((t) => (byId[t.id] = t));
  const reach = new Set(), max = (tid) => { const t = byId[tid]; return !t ? 0 : t.track.max_level != null ? t.track.max_level : t.track.driven_by ? max(t.track.driven_by) : 20; };
  const term = (x, tid) => typeof x === "string" ? reach.has(tid + "/" + x) : x.node ? reach.has(x.node) : x.track ? (byId[x.track] ? max(x.track) >= x.level : false) : x.feature || x.training ? true : req(x, tid);
  const req = (r, tid) => !r || ((!r.all || r.all.every((x) => term(x, tid))) && (!r.any || r.any.some((x) => term(x, tid))) && (!r.any_of_group || (byId[tid].nodes || []).some((n) => n.choice_group === r.any_of_group && reach.has(tid + "/" + n.id))));
  let changed = true; while (changed) { changed = false; trees.forEach((t) => (t.nodes || []).forEach((n) => { const k = t.id + "/" + n.id; if (reach.has(k)) return;
    if (n.level <= max(t.id) && req(n.requires, t.id) && (!n.upgrades || reach.has(t.id + "/" + n.upgrades))) { reach.add(k); changed = true; } })); }
  const unreachable = []; trees.forEach((t) => (t.nodes || []).forEach((n) => { if (!reach.has(t.id + "/" + n.id)) unreachable.push(t.id + "/" + n.id); }));
  return { reachable: reach.size, unreachable };
}
function policyChecks(policy, trees) {
  const E = [], byId = new Set(trees.map((t) => t.id)), seen = {};
  (policy.rules || []).forEach((r) => { r.pids.forEach((p) => { if (seen[p]) E.push({ code: "PID_IN_TWO_RULES", pid: p, rules: [seen[p], r.id] }); seen[p] = r.id; });
    (r.pools || []).forEach((pl) => { if (!policy.disciplines.includes(pl)) E.push({ code: "UNKNOWN_DISCIPLINE", rule: r.id, pool: pl }); });
    if (r.primary && /^discipline:/.test(r.primary)) E.push({ code: "PRIMARY_IS_A_POOL", rule: r.id });
    if (r.primary && !byId.has(r.primary)) E.push({ code: "PRIMARY_TRACK_NOT_LOADED", rule: r.id, track: r.primary });
    if (new Set(r.pools || []).size !== (r.pools || []).length) E.push({ code: "DUPLICATE_POOL_IN_RULE", rule: r.id }); });
  if (!(policy.bounds && policy.bounds.max_pools_per_observation > 0 && policy.bounds.max_discipline_xp_per_observation > 0)) E.push({ code: "UNBOUNDED_ALLOCATION" });
  return E;
}
function implementedProfiles() { try { return Object.keys(JSON.parse(fs.readFileSync(path.join(REPO, "development/combat_slice/catalog.json"))).profiles); } catch (e) { return []; } }
function review(trees, opts) {
  opts = Object.assign({ implemented_profiles: implementedProfiles() }, opts || {}); const base = V.validateTrees(trees, Object.assign({}, opts, { registry: undefined, policy: undefined })), errors = base.errors.slice(), warnings = base.warnings.slice();
  const W = (code, where, x) => warnings.push(Object.assign({}, x || {}, { code, where })), Er = (code, where, x) => errors.push(Object.assign({}, x || {}, { code, where }));
  const urids = opts.registry === false ? null : registryUrids();
  trees.forEach((t) => {
    if (urids && t.registry_urid && !urids.has(t.registry_urid)) W("REGISTRY_URID_NOT_APPROVED", t.id, { urid: t.registry_urid });
    if (t.registry_urid && !/^[a-z]+_[a-z0-9_]+$/.test(t.registry_urid)) Er("MALFORMED_URID", t.id, { urid: t.registry_urid });
    const keys = {}; (t.nodes || []).forEach((n) => (n.effects || []).forEach((e) => { (keys[e.key] = keys[e.key] || []).push({ node: n.id, group: e.stacking_group, upgrades: n.upgrades }); }));
    Object.keys(keys).forEach((k) => { const l = keys[k]; if (l.length > 1 && l.some((x) => !x.group) && !l.every((x, i) => i === 0 || x.upgrades)) W("STACKING_UNDECLARED", t.id, { key: k, nodes: l.map((x) => x.node) }); });
    (t.nodes || []).forEach((n) => (n.conflicts_with || []).forEach((c) => { const o = (t.nodes || []).find((m) => m.id === c); if (o && !(o.conflicts_with || []).includes(n.id)) W("CONFLICT_NOT_RECIPROCAL", t.id + "/" + n.id, { with: c }); }));
    (t.nodes || []).forEach((n) => (n.grants || []).forEach((g) => { if (urids && (g.type === "feature") && !/^feature:candidate_/.test(g.ref)) { const u = refToUrid(g.ref); if (u && !urids.has(u)) W("GRANT_NOT_IN_APPROVED_REGISTRY", t.id + "/" + n.id, { ref: g.ref, urid: u }); } }));
    if (t.track.xp_quantity !== "none" && !(t.balance_tests || []).length) W("NO_BALANCE_TEST_COVERAGE", t.id);
    (t.balance_tests || []).forEach((b) => { if (!fs.existsSync(path.join(REPO, b))) Er("BALANCE_TEST_MISSING", t.id, { file: b }); });
    if (t.status !== "approved" && t.status !== "approved_provisional") W("NOT_APPROVED_CONTENT", t.id, { status: t.status });
  });
  const reach = reachability(trees); reach.unreachable.forEach((u) => Er("UNREACHABLE_NODE", u));
  if (opts.policy) policyChecks(opts.policy, trees).forEach((e) => errors.push(Object.assign({ where: "policy" }, e)));
  const tables = {}; trees.forEach((t) => { if (t.track.xp_quantity !== "none" && CU.validate(t.track).length === 0) tables[t.id] = CU.table(t.track); });
  const edges = []; trees.forEach((t) => (t.nodes || []).forEach((n) => { V.termsOf(n.requires).forEach(({ mode, t: x }) => edges.push({ from: typeof x === "string" ? t.id + "/" + x : x.node || (x.track ? x.track + "@" + x.level : x.feature ? "feature:" + x.feature : x.training ? "training:" + x.training : "group:" + t.id + "#" + x.any_of_group), to: t.id + "/" + n.id, mode }));
    if (n.upgrades) edges.push({ from: t.id + "/" + n.upgrades, to: t.id + "/" + n.id, mode: "upgrade" }); (n.grants || []).forEach((g) => { if (g.type === "track_unlock") edges.push({ from: t.id + "/" + n.id, to: g.ref, mode: "unlocks" }); }); }));
  return { ok: errors.length === 0, errors, warnings, reachability: reach, tables, edges };
}
function markdown(trees, rep) {
  const L = []; L.push("# Progression review", "", rep.ok ? "**Result: PASS**" : "**Result: FAIL** (" + rep.errors.length + " errors)", "");
  if (rep.errors.length) { L.push("## Errors", ""); rep.errors.forEach((e) => L.push("- `" + e.code + "` at `" + e.where + "` " + JSON.stringify(Object.assign({}, e, { code: undefined, where: undefined })))); L.push(""); }
  if (rep.warnings.length) { L.push("## Warnings", ""); rep.warnings.forEach((e) => L.push("- `" + e.code + "` at `" + e.where + "`")); L.push(""); }
  trees.forEach((t) => { L.push("## " + t.id + " (" + t.layer + ", " + t.status + ")", "", "Source: " + t.provenance.source, "");
    const rows = rep.tables[t.id], byLvl = {}; (t.nodes || []).forEach((n) => (byLvl[n.level] = byLvl[n.level] || []).push(n.id + (n.choice_group ? " [" + n.choice_group + "]" : "") + (n.status !== "approved" ? " (" + n.status + ")" : "")));
    if (rows) { L.push("Curve `" + t.track.curve.id + "` " + JSON.stringify(t.track.curve.params || {}) + " — **" + t.track.curve_status + "**", "", "| Level | XP to next | Cumulative | Milestone | Nodes |", "|---:|---:|---:|:-:|---|");
      rows.forEach((r) => L.push("| " + r.level + " | " + (r.xp_to_next == null ? "—" : r.xp_to_next) + " | " + r.cumulative_xp + " | " + ((t.track.cadence || []).includes(r.level) ? "●" : "") + " | " + (byLvl[r.level] || []).join(", ") + " |")); }
    else { L.push("Driven by `" + (t.track.driven_by || t.parent) + "` (no XP of its own).", "", "| Level | Nodes |", "|---:|---|"); Object.keys(byLvl).sort((a, b) => a - b).forEach((k) => L.push("| " + k + " | " + byLvl[k].join(", ") + " |")); }
    L.push(""); });
  L.push("## Dependency graph", "", "```mermaid", "flowchart LR"); const idOf = (s) => '"' + s.replace(/"/g, "'") + '"';
  rep.edges.forEach((e, i) => L.push("  e" + i + "a[" + idOf(e.from) + "] -->|" + e.mode + "| e" + i + "b[" + idOf(e.to) + "]")); L.push("```", "");
  return L.join("\n");
}
module.exports = { implementedProfiles, review, markdown, reachability, policyChecks, registryUrids };
