// Tree validator (CC-008 C/G). Pure function over tree documents; never touches the game runtime.
// validateTrees(trees, opts) → { ok, errors[], warnings[], report }
"use strict";
const CU = require("./curves.js");
const LAYER_AUTH = { class: ["class", "training", "campaign_ruling"], archetype: ["archetype", "class", "training"], species: ["species"], proficiency: ["mastery", "training"],
                     specialized_mastery: ["mastery", "training"], parent_linked: ["mastery", "training"], discipline: ["discipline"] };
const XP_LAYERS = ["proficiency", "specialized_mastery", "discipline"];
function termsOf(req, out) { out = out || []; if (!req) return out; ["all", "any", "not"].forEach((k) => (req[k] || []).forEach((t) => { if (typeof t === "object" && (t.all || t.any || t.not || t.any_of_group)) termsOf(t, out); else out.push({ mode: k, t }); }));
  if (req.any_of_group) out.push({ mode: "group", t: { any_of_group: req.any_of_group } }); return out; }
function validateTrees(list, opts) {
  opts = opts || {}; const errors = [], warnings = [], E = (code, where, x) => errors.push(Object.assign({}, x || {}, { code, where })), W = (code, where, x) => warnings.push(Object.assign({}, x || {}, { code, where }));
  const byId = {}; list.forEach((t) => { if (byId[t.id]) E("DUPLICATE_TRACK_ID", t.id); byId[t.id] = t; });
  const known = new Set((opts.registry || []).concat(opts.known_refs || []));
  for (const t of list) {
    const w = t.id, tr = t.track || {};
    if (t.schema !== "genesis-progression-tree/0.1") E("BAD_SCHEMA", w);
    ["id", "version", "status", "layer", "provenance"].forEach((k) => { if (t[k] == null) E("MISSING_FIELD", w, { field: k }); });
    if (!t.provenance || !t.provenance.source) E("MISSING_PROVENANCE", w);
    // ---- C: explicit experience thresholds ----
    if (tr.start_level == null) E("MISSING_START_LEVEL", w);
    if (tr.xp_quantity !== "none") {
      if (tr.max_level == null) E("MISSING_MAX_LEVEL", w);
      if (!tr.curve) E("MISSING_CURVE", w); else CU.validate(tr).forEach((x) => E("CURVE_" + x.code, w, x));
      if (!tr.curve_status) E("MISSING_CURVE_STATUS", w);
      if (!t.evidence || !(t.evidence.accepted_authorities || []).length || !Object.keys(t.evidence.event_types || {}).length) E("MISSING_EVIDENCE_RULES", w);
      if (!(tr.cadence || []).length) E("MISSING_CADENCE", w);
      if (tr.curve_status === "candidate" && t.status === "approved") E("APPROVED_TREE_WITH_CANDIDATE_CURVE", w);
    } else {
      const d = tr.driven_by || t.parent; if (!d) E("NON_XP_TRACK_NOT_DRIVEN", w); else if (!byId[d] && !(opts.external_tracks || []).includes(d)) E("UNKNOWN_DRIVER_TRACK", w, { driven_by: d });
      if (XP_LAYERS.includes(t.layer)) E("XP_LAYER_WITHOUT_XP", w);
    }
    if (t.layer === "parent_linked" && !t.parent) E("PARENT_LINKED_WITHOUT_PARENT", w);
    if (t.layer === "class" && tr.xp_quantity === "mastery_xp") E("CLASS_LEVEL_ON_MASTERY_XP", w);
    if (t.layer !== "class" && tr.xp_quantity === "class_xp") E("CLASS_XP_ON_NON_CLASS_TRACK", w);
    (tr.cadence || []).forEach((L) => { if (L < (tr.start_level || 0) || (tr.max_level != null && L > tr.max_level)) E("CADENCE_OUT_OF_RANGE", w, { level: L }); });
    // ---- nodes ----
    const nodes = t.nodes || [], nid = {}; nodes.forEach((n) => { if (nid[n.id]) E("DUPLICATE_NODE_ID", w + "/" + n.id); nid[n.id] = n; });
    const groups = {}; (t.choice_groups || []).forEach((g) => { if (groups[g.id]) E("DUPLICATE_CHOICE_GROUP", w + "#" + g.id); groups[g.id] = g; });
    const maxL = tr.max_level != null ? tr.max_level : 20, seenGrant = {};
    for (const n of nodes) {
      const at = w + "/" + n.id;
      if (n.level > maxL) E("NODE_ABOVE_MAX_LEVEL", at, { level: n.level });
      if (n.kind === "choice" && !n.choice_group) E("CHOICE_WITHOUT_GROUP", at);
      if (n.choice_group && !groups[n.choice_group]) E("UNKNOWN_CHOICE_GROUP", at, { group: n.choice_group });
      if (t.status === "approved" && n.status !== "approved" && n.status !== "approved_provisional") E("UNAPPROVED_NODE_IN_APPROVED_TREE", at);
      (n.grants || []).forEach((g) => {
        if (!(LAYER_AUTH[t.layer] || []).includes(g.authority)) E("GRANT_AUTHORITY_MISMATCH", at, { authority: g.authority, layer: t.layer });
        const k = g.type + ":" + g.ref; if (seenGrant[k] && !g.repeatable && !n.upgrades && !(n.effects || []).some((e) => e.stacking_group)) E("DUPLICATE_REWARD", at, { grant: k, also: seenGrant[k] }); seenGrant[k] = seenGrant[k] || n.id;
        if (opts.registry && (g.type === "feature" || g.type === "profile") && !known.has(g.ref) && !/^(feature|profile|archetype|track):candidate_/.test(g.ref)) W("UNRESOLVED_REGISTRY_REF", at, { ref: g.ref });
        if (g.type === "track_unlock" && !byId[g.ref.replace(/^archetype:/, "archetype:")] && !(opts.external_tracks || []).includes(g.ref)) W("TRACK_UNLOCK_TARGET_NOT_LOADED", at, { ref: g.ref });
      });
      if (n.upgrades && !nid[n.upgrades]) E("UPGRADE_OF_UNKNOWN_NODE", at, { upgrades: n.upgrades });
      (n.conflicts_with || []).forEach((c) => { if (!nid[c]) E("CONFLICT_WITH_UNKNOWN_NODE", at, { conflicts_with: c }); });
      // stacking: two effects on the same key without a stacking group or upgrade relation
      (n.effects || []).forEach((e) => { if (!e.key) E("EFFECT_WITHOUT_KEY", at); });
      // requirement references
      const terms = termsOf(n.requires);
      const exclusivePairs = {};
      terms.forEach(({ mode, t: x }) => {
        if (typeof x === "string") { if (!nid[x]) E("UNKNOWN_PREREQUISITE", at, { ref: x }); else { if (nid[x].level > n.level && mode === "all") E("PREREQUISITE_ABOVE_NODE_LEVEL", at, { ref: x, ref_level: nid[x].level, level: n.level });
            const g = nid[x].choice_group; if (g && mode === "all" && groups[g] && groups[g].exclusive && groups[g].picks === 1) (exclusivePairs[g] = exclusivePairs[g] || []).push(x); } }
        else if (x.node) { const [tt, nn] = x.node.split("/"); if (!byId[tt] && !(opts.external_tracks || []).includes(tt)) E("UNKNOWN_CROSS_TREE_TRACK", at, { ref: x.node }); else if (byId[tt] && !(byId[tt].nodes || []).some((q) => q.id === nn)) E("UNKNOWN_CROSS_TREE_NODE", at, { ref: x.node }); }
        else if (x.track) { if (!byId[x.track] && !(opts.external_tracks || []).includes(x.track)) E("UNKNOWN_TRACK_REQUIREMENT", at, { ref: x.track }); else if (byId[x.track] && byId[x.track].track.max_level != null && x.level > byId[x.track].track.max_level) E("UNREACHABLE_TRACK_LEVEL", at, { ref: x.track, level: x.level }); }
        else if (x.any_of_group) { if (!groups[x.any_of_group]) E("UNKNOWN_GROUP_REQUIREMENT", at, { group: x.any_of_group }); }
      });
      Object.keys(exclusivePairs).forEach((g) => { if (exclusivePairs[g].length > 1) E("UNSATISFIABLE_EXCLUSIVE_REQUIREMENT", at, { group: g, requires_all_of: exclusivePairs[g] }); });
    }
    // ---- choice groups ----
    Object.values(groups).forEach((g) => {
      const members = nodes.filter((n) => n.choice_group === g.id), at = w + "#" + g.id;
      if (!members.length) E("EMPTY_CHOICE_GROUP", at);
      else if (members.length < g.picks) E("UNSATISFIABLE_CHOICE_GROUP", at, { picks: g.picks, members: members.length });
      (g.milestones || []).forEach((L) => { const open = members.filter((m) => m.level <= L).length; if (open === 0) E("MILESTONE_WITH_NO_ELIGIBLE_LEVEL", at, { milestone: L });
        else if (open < (g.offer_size || 3)) W("FEWER_THAN_OFFER_SIZE", at, { milestone: L, available: open, offer_size: g.offer_size || 3 }); });
      if (g.exclusive && (g.milestones || []).length > g.picks) W("EXCLUSIVE_GROUP_MORE_MILESTONES_THAN_PICKS", at);
    });
  }
  // ---- cycles over hard prerequisites (within and across trees) ----
  const edges = {}; list.forEach((t) => (t.nodes || []).forEach((n) => { const k = t.id + "/" + n.id; edges[k] = [];
    termsOf(n.requires).forEach(({ mode, t: x }) => { if (mode === "not") return; if (typeof x === "string") edges[k].push(t.id + "/" + x); else if (x.node) edges[k].push(x.node); });
    if (n.upgrades) edges[k].push(t.id + "/" + n.upgrades); }));
  const color = {}, stack = [];
  const dfs = (u) => { color[u] = 1; stack.push(u); for (const v of edges[u] || []) { if (color[v] === 1) { E("PREREQUISITE_CYCLE", u, { cycle: stack.slice(stack.indexOf(v)).concat([v]) }); } else if (!color[v] && edges[v]) dfs(v); } stack.pop(); color[u] = 2; };
  Object.keys(edges).forEach((u) => { if (!color[u]) dfs(u); });
  return { ok: errors.length === 0, errors, warnings };
}
module.exports = { validateTrees, termsOf, LAYER_AUTH };
