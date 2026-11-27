// Three-choice milestone selection (CC-008 D) — server-authoritative, deterministic, sandbox.
// statusOf → eligible | locked | purchased | unavailable (each with reasons). offer() presents up to offer_size (default 3) distinct
// ELIGIBLE authored candidates; never filler. Presentation order may rotate deterministically (roguelike feel) but legality never
// depends on it. select() re-validates against fresh state and records one sealed transaction.
"use strict";
const F = require("./framework.js");
const { sha, stable, clone } = F;
function grantRefs(ch) { return new Set(ch.features); }
function statusOf(trees, ch, trackId, nodeId) {
  const tree = trees[trackId], n = F.nodeOf(tree, nodeId); if (!n) return { status: "unavailable", reasons: [{ code: "UNKNOWN_NODE" }] };
  const key = trackId + "/" + nodeId; if (ch.held[key]) return { status: "purchased", txn: ch.held[key].txn };
  const tw = F.trackAllowed(tree, ch); if (tw.length) return { status: "unavailable", reasons: tw };
  if (n.status === "scaffold") return { status: "unavailable", reasons: [{ code: "SCAFFOLD_NODE" }] };
  const blocked = [].concat.apply([], (n.grants || []).map((gr) => F.executableBlockers(tree, n, gr)));   // runtime gate, independent of the validator
  if (blocked.length) return { status: "unavailable", reasons: blocked };
  const g = n.choice_group && (tree.choice_groups || []).find((x) => x.id === n.choice_group);
  if (g && g.exclusive) { const taken = (tree.nodes || []).filter((m) => m.choice_group === g.id && ch.held[trackId + "/" + m.id]).length; if (taken >= g.picks) return { status: "unavailable", reasons: [{ code: "GROUP_CLOSED", group: g.id }] }; }
  const conflicts = (n.conflicts_with || []).filter((c) => ch.held[trackId + "/" + c]); if (conflicts.length) return { status: "unavailable", reasons: [{ code: "CONFLICTS_WITH_HELD", nodes: conflicts }] };
  const held = grantRefs(ch), dup = (n.grants || []).filter((gr) => (gr.type === "feature" || gr.type === "profile") && !gr.repeatable && held.has(gr.ref));
  if (dup.length) return { status: "unavailable", reasons: [{ code: "ALREADY_GRANTED_ELSEWHERE", refs: dup.map((d) => d.ref) }] };
  const ctx = F.ctxFor(trees, ch), why = [];
  if (ctx.levels[trackId] < n.level) why.push({ code: "LEVEL", need: n.level, have: ctx.levels[trackId] });
  if (n.upgrades && !ch.held[trackId + "/" + n.upgrades]) why.push({ code: "UPGRADE_OF_UNHELD", node: n.upgrades });
  if (!F.evalReq(n.requires, ctx, trackId)) F.missing(n.requires, ctx, trackId, why);
  return why.length ? { status: "locked", reasons: why } : { status: "eligible" };
}
// milestones reached on a track that have no resolved offer for a given group
function due(trees, ch, trackId) {
  const tree = trees[trackId], L = F.levelOfTrack(trees, ch, trackId), out = [];
  (tree.choice_groups || []).forEach((g) => (g.milestones || []).forEach((m) => { if (m > L) return;
    const id = offerId(ch, trackId, g.id, m), o = ch.offers[id]; if (!o || !o.resolved) out.push({ group: g.id, milestone: m, offer_id: id }); }));
  return out;
}
function offerId(ch, trackId, groupId, milestone) { return "offer_" + sha([ch.character, trackId, groupId, milestone].join("|")).slice(0, 20); }
function offer(trees, ch, trackId, groupId, milestone) {
  const tree = trees[trackId], g = (tree.choice_groups || []).find((x) => x.id === groupId); if (!g) return { ok: false, code: "UNKNOWN_GROUP" };
  if (!(g.milestones || []).includes(milestone)) return { ok: false, code: "NOT_A_MILESTONE_OF_GROUP" };
  if (F.levelOfTrack(trees, ch, trackId) < milestone) return { ok: false, code: "MILESTONE_NOT_REACHED" };
  const id = offerId(ch, trackId, groupId, milestone); if (ch.offers[id]) return { ok: true, offer: ch.offers[id], state: ch, existing: true };
  const members = (tree.nodes || []).filter((n) => n.choice_group === groupId);
  const all = members.map((n) => Object.assign({ node: n.id, name: n.name || n.id, level: n.level }, statusOf(trees, ch, trackId, n.id)));
  const eligible = all.filter((x) => x.status === "eligible"), size = g.offer_size || 3;
  // deterministic presentation: authored order, rotated by a stable hash of (character, track, group, milestone)
  const rot = eligible.length > size ? parseInt(sha(id).slice(0, 8), 16) % eligible.length : 0;
  const presented = eligible.slice(rot).concat(eligible.slice(0, rot)).slice(0, size).map((x) => x.node);
  const o = { id, character: ch.character, track: trackId, group: groupId, milestone, presented, offer_size: size, fewer_than_offer_size: presented.length < size,
              statuses: all.map((x) => ({ node: x.node, status: x.status, reasons: x.reasons || [] })), presentation: { rule: "authored order rotated by sha256(offer id)", rotation: rot }, resolved: null };
  o.hash = sha(stable(o));
  const s = clone(ch); s.offers[id] = o; return { ok: true, offer: o, state: s };
}
function select(trees, ch, offerIdArg, nodeId) {
  const o = ch.offers[offerIdArg]; if (!o) return { ok: false, code: "UNKNOWN_OFFER" };
  if (o.resolved) return o.resolved === nodeId ? { ok: true, duplicate: true, state: ch } : { ok: false, code: "OFFER_ALREADY_RESOLVED", resolved: o.resolved };
  if (!o.presented.includes(nodeId)) return { ok: false, code: "NOT_IN_OFFER" };
  const st = statusOf(trees, ch, o.track, nodeId); if (st.status !== "eligible") return { ok: false, code: "NO_LONGER_ELIGIBLE", status: st };   // fresh re-validation
  const tree = trees[o.track], n = F.nodeOf(tree, nodeId);
  const rc = { id: "sel_" + sha([ch.character, o.track, nodeId, o.id, tree.version].join("|")).slice(0, 24), kind: "select", track: o.track, node: nodeId, offer_id: o.id, at_level: F.levelOfTrack(trees, ch, o.track),
               grants: n.grants || [], authority: (n.grants || [])[0] ? n.grants[0].authority : tree.layer, status: n.status, version: tree.version };
  rc.hash = sha(stable(rc));
  const s = clone(ch); s.pending = rc; return F.commit(s);
}
module.exports = { statusOf, due, offer, select, offerId };
