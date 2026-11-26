// Genesis unified progression framework (CC-008) — SANDBOX / NONCANONICAL, schema genesis-progression-tree/0.1.
// Extends genesis-mastery/0.1 (mastery.js, CC-007) without replacing it: CC-007 mastery tracks keep working unchanged.
// Layers: class · archetype · species · proficiency · specialized_mastery · parent_linked · discipline.
// Ledger quantities are TYPED and never exchanged: class_xp, mastery_xp, discipline_xp, purchase_currency.
"use strict";
const crypto = require("crypto");
const CURVES = require("./curves.js");
const sha = (s) => crypto.createHash("sha256").update(s).digest("hex");
const clone = (x) => JSON.parse(JSON.stringify(x));
const stable = (o) => JSON.stringify(o, Object.keys(o).sort());
const SCHEMA = "genesis-progression-tree/0.1", CHAR_SCHEMA = "genesis-progression-character/0.1";
const LAYERS = ["class", "archetype", "species", "proficiency", "specialized_mastery", "parent_linked", "discipline"];
const QUANTITIES = ["class_xp", "mastery_xp", "discipline_xp", "none"];

// ---------- registry of trees (one per track id) ----------
function registry(trees) { const r = {}; trees.forEach((t) => { if (r[t.id]) throw new Error("DUPLICATE_TRACK " + t.id); r[t.id] = t; }); return r; }
const nodeOf = (tree, id) => (tree.nodes || []).find((n) => n.id === id) || null;

// ---------- legacy adapter: Class.schema progression_tree → genesis-progression-tree/0.1 ----------
// Legacy `prerequisites` is a bare list documented as ALL-of, but 17/100 candidate trees list two members of one exclusive
// choice_group (CC-008 A §2.2). Such a list is read as any_of_group, and the node records the reinterpretation.
function fromLegacyClass(rec, opts) {
  opts = opts || {};
  const legacy = rec.progression_tree || [], byId = {}; legacy.forEach((n) => (byId[n.node_id] = n));
  const groups = {}, notes = [];
  const nodes = legacy.map((n) => {
    const pre = n.prerequisites || [], inGroup = {};
    pre.forEach((p) => { const g = byId[p] && byId[p].choice_group; if (g) (inGroup[g] = inGroup[g] || []).push(p); });
    let requires, reint = null;
    const multi = Object.keys(inGroup).filter((g) => inGroup[g].length > 1);
    if (multi.length) {
      const rest = pre.filter((p) => !multi.some((g) => inGroup[g].includes(p)));
      requires = { all: rest.concat(multi.map((g) => ({ any_of_group: g }))) };
      reint = "legacy prerequisites " + JSON.stringify(pre) + " name several members of exclusive group(s) " + multi.join(",") + " → read as any_of_group";
      notes.push({ node: n.node_id, note: reint });
    } else requires = pre.length ? { all: pre.slice() } : undefined;
    if (n.choice_group) groups[n.choice_group] = groups[n.choice_group] || { id: n.choice_group, picks: 1, exclusive: true, milestones: [] };
    if (n.choice_group && !groups[n.choice_group].milestones.includes(n.level_requirement)) groups[n.choice_group].milestones.push(n.level_requirement);
    const kind = n.type === "choice" ? "choice" : n.type === "subclass_entry" ? "subclass_entry" : "core_grant";
    const out = { id: n.node_id, kind, level: n.level_requirement, status: opts.status || "candidate", provenance: opts.source || "legacy progression_tree",
                  grants: [{ type: kind === "subclass_entry" ? "track_unlock" : "feature", ref: (kind === "subclass_entry" ? "archetype:" : "feature:") + String(n.feature_id), authority: "class" }] };
    if (n.choice_group) out.choice_group = n.choice_group;
    if (requires) out.requires = requires;
    if (reint) out.legacy_reinterpretation = reint;
    return out;
  });
  return { tree: { schema: SCHEMA, id: "class:" + rec.id, version: opts.version || "legacy-adapter-0.1", status: opts.status || "candidate", layer: "class",
                   registry_urid: "class_" + rec.id, provenance: { source: opts.source || "legacy", notes: "adapted by fromLegacyClass; legacy fields preserved in the source" },
                   track: { start_level: 1, max_level: 20, xp_quantity: "class_xp", curve: opts.curve || { id: "none/1" }, curve_status: opts.curve_status || "candidate" },
                   choice_groups: Object.values(groups), nodes }, notes };
}

// ---------- requirements ----------
// ctx: { held: {"track/node": true}, levels: {track: level}, features: [..], training: [..], trees }
function holds(ctx, track, id) { return !!ctx.held[track + "/" + id]; }
function evalTerm(term, ctx, track) {
  if (typeof term === "string") return holds(ctx, track, term);
  if (term.track) return (ctx.levels[term.track] || 0) >= term.level;
  if (term.node) { const [t, n] = term.node.split("/"); return holds(ctx, t, n); }
  if (term.feature) return (ctx.features || []).includes(term.feature);
  if (term.training) return (ctx.training || []).includes(term.training);
  return evalReq(term, ctx, track);
}
function evalReq(req, ctx, track) {
  if (!req) return true;
  if (req.all && !req.all.every((t) => evalTerm(t, ctx, track))) return false;
  if (req.any && !req.any.some((t) => evalTerm(t, ctx, track))) return false;
  if (req.any_of_group) { const tree = ctx.trees[track]; if (!(tree.nodes || []).some((n) => n.choice_group === req.any_of_group && holds(ctx, track, n.id))) return false; }
  if (req.not && req.not.some((t) => evalTerm(t, ctx, track))) return false;
  return true;
}
// explain why a requirement fails (for 'locked' reasons)
function missing(req, ctx, track, out) {
  out = out || []; if (!req) return out;
  (req.all || []).forEach((t) => { if (!evalTerm(t, ctx, track)) out.push(typeof t === "string" ? { code: "NODE", node: track + "/" + t } : t.track ? { code: "TRACK_LEVEL", track: t.track, need: t.level } : t.node ? { code: "NODE", node: t.node } : t.feature ? { code: "FEATURE", feature: t.feature } : t.training ? { code: "TRAINING", training: t.training } : { code: "NESTED" }); });
  if (req.any && !req.any.some((t) => evalTerm(t, ctx, track))) out.push({ code: "ANY_OF", options: req.any });
  if (req.any_of_group && !evalReq({ any_of_group: req.any_of_group }, ctx, track)) out.push({ code: "GROUP", group: req.any_of_group });
  if (req.not && req.not.some((t) => evalTerm(t, ctx, track))) out.push({ code: "EXCLUDED_BY", terms: req.not });
  return out;
}

// ---------- character progression state ----------
function newCharacter(character, opts) {
  opts = opts || {};
  return { schema: CHAR_SCHEMA, character, ruleset: opts.ruleset || "sandbox", class_level_is_not_mastery: true,
           ledger: { class_xp: 0, purchase_currency: 0 }, tracks: {}, held: {}, features: (opts.features || []).slice(), training: (opts.training || []).slice(),
           restrictions: { class: opts.class || null, species: opts.species || null }, applied: {}, receipts: [], txns: [], pending: null, offers: {} };
}
function trackState(ch, id) { return ch.tracks[id] || { level: 0, xp: 0 }; }
function levelOfTrack(trees, ch, id) {
  const t = trees[id]; if (!t) return 0;
  if (t.track.xp_quantity === "none" || t.layer === "parent_linked") { const d = t.track.driven_by || t.parent; return d ? levelOfTrack(trees, ch, d) : trackState(ch, id).level; }
  return trackState(ch, id).level;
}
function ctxFor(trees, ch) {
  const levels = {}; Object.keys(trees).forEach((id) => (levels[id] = levelOfTrack(trees, ch, id)));
  const held = {}; Object.keys(ch.held).forEach((k) => (held[k] = true));
  return { held, levels, features: ch.features, training: ch.training, trees };
}
// restriction check: class/species/required features of the track itself
function trackAllowed(tree, ch) {
  const r = tree.restrictions || {}, why = [];
  if (r.classes && !r.classes.includes(ch.restrictions.class)) why.push({ code: "CLASS_RESTRICTED", need: r.classes });
  if (r.species && !r.species.includes(ch.restrictions.species)) why.push({ code: "SPECIES_RESTRICTED", need: r.species });
  (r.requires_features || []).forEach((f) => { if (!ch.features.includes(f)) why.push({ code: "FEATURE", feature: f }); });
  return why;
}

// ---------- XP awards for any xp-owning track (class_xp / mastery_xp / discipline_xp), two-phase like mastery.js ----------
function validateEvidence(tree, ev, character) {
  const E = tree.evidence || {};
  if (!ev || !ev.event_id) return "NO_EVENT_ID";
  if (ev.committed !== true) return "NOT_COMMITTED";
  if (!(E.accepted_authorities || []).includes(ev.authority)) return "UNTRUSTED_AUTHORITY";
  if (ev.actor !== character) return "WRONG_ACTOR";
  if (ev.validated !== true) return "NOT_VALIDATED";
  const rule = (E.event_types || {})[ev.type]; if (!rule) return "NOT_ELIGIBLE_EVIDENCE";
  if ((rule.requires_facts || []).some((f) => ev.facts == null || ev.facts[f] == null || ev.facts[f] === false)) return "MISSING_FACTS";
  return null;
}
function awardXp(trees, ch, trackId, ev, amountOverride) {
  const tree = trees[trackId]; if (!tree) return { ok: false, code: "UNKNOWN_TRACK" };
  if (tree.track.xp_quantity === "none") return { ok: false, code: "TRACK_HAS_NO_XP" };
  const tw = trackAllowed(tree, ch); if (tw.length) return { ok: false, code: tw[0].code, reasons: tw };
  const why = validateEvidence(tree, ev, ch.character); if (why) return { ok: false, code: why };
  const key = trackId + "|" + ev.event_id;
  if (ch.applied[key]) return { ok: true, duplicate: true, receipt: ch.receipts.find((r) => r.id === ch.applied[key]), state: ch };
  if (ch.pending) return { ok: false, code: "TXN_PENDING" };
  const st = trackState(ch, trackId), xp = amountOverride != null ? amountOverride : tree.evidence.event_types[ev.type].xp;
  const after = st.xp + xp, lvl = CURVES.levelFor(tree.track, after);
  const rc = { id: "xp_" + sha([ch.character, trackId, tree.version, ev.event_id].join("|")).slice(0, 24), kind: "xp", quantity: tree.track.xp_quantity, track: trackId, version: tree.version,
               event_id: ev.event_id, type: ev.type, xp, xp_before: st.xp, xp_after: after, level_before: st.level, level_after: lvl };
  rc.hash = sha(stable(rc));
  const s = clone(ch); s.pending = rc; return commit(s);
}
function commit(ch) {
  const rc = ch.pending; if (!rc) return { ok: false, code: "NO_PENDING" };
  const s = clone(ch); s.pending = null;
  if (rc.kind === "xp") { const key = rc.track + "|" + rc.event_id; if (s.applied[key]) return { ok: true, duplicate: true, state: s };
    const st = trackState(s, rc.track); if (st.xp !== rc.xp_before) return { ok: false, code: "STALE_PENDING", state: s };
    s.tracks[rc.track] = { level: rc.level_after, xp: rc.xp_after }; if (rc.quantity === "class_xp") s.ledger.class_xp = rc.xp_after; s.applied[key] = rc.id; s.receipts.push(rc); return { ok: true, receipt: rc, state: s }; }
  if (rc.kind === "select") { if (s.held[rc.track + "/" + rc.node]) return { ok: true, duplicate: true, state: s };
    s.held[rc.track + "/" + rc.node] = { txn: rc.id, offer: rc.offer_id, at_level: rc.at_level }; (rc.grants || []).forEach((g) => { if (g.type === "feature" || g.type === "profile") s.features.push(g.ref); });
    if (rc.offer_id && s.offers[rc.offer_id]) s.offers[rc.offer_id].resolved = rc.node; s.txns.push(rc); s.receipts.push(rc); return { ok: true, receipt: rc, state: s }; }
  return { ok: false, code: "UNKNOWN_TXN" };
}
function recover(ch) { return ch.pending ? commit(ch) : { ok: true, nothing: true, state: ch }; }
function verifyReceipt(rc) { const c = clone(rc); delete c.hash; return sha(stable(c)) === rc.hash; }

// ---------- core grants: automatic nodes from an authoritative source at their level ----------
function applyCoreGrants(trees, ch, trackId) {
  const tree = trees[trackId], ctx = ctxFor(trees, ch), lvl = ctx.levels[trackId]; let s = ch; const granted = [];
  (tree.nodes || []).filter((n) => n.kind === "core_grant" && n.level <= lvl && !s.held[trackId + "/" + n.id]).forEach((n) => {
    if (!evalReq(n.requires, ctxFor(trees, s), trackId)) return;
    const rc = { id: "grant_" + sha([s.character, trackId, n.id, tree.version].join("|")).slice(0, 24), kind: "select", track: trackId, node: n.id, at_level: lvl, offer_id: null, grants: n.grants || [], authority: (n.grants || [])[0] ? n.grants[0].authority : tree.layer, automatic: true };
    rc.hash = sha(stable(rc)); const x = clone(s); x.pending = rc; s = commit(x).state; granted.push(n.id); });
  return { state: s, granted };
}
module.exports = { SCHEMA, CHAR_SCHEMA, LAYERS, QUANTITIES, registry, nodeOf, fromLegacyClass, evalReq, missing, newCharacter, trackState, levelOfTrack, ctxFor,
                   trackAllowed, validateEvidence, awardXp, commit, recover, verifyReceipt, applyCoreGrants, sha, stable, clone };
