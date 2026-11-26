// Genesis skill-mastery substrate (CC-007 §4) — SANDBOX / NONCANONICAL, schema genesis-mastery/0.1.
// A reusable, deterministic progression ledger: XP only from validated, COMMITTED skill-use events; one receipt per
// (character, skill, event); versioned curves; per-level improvements; milestone ELIGIBILITY (never auto-grants of
// unlearned powers); prerequisite checks; independent of class level; two-phase transactions with recovery.
(function (root, factory) { if (typeof module === "object" && module.exports) module.exports = factory(require("crypto")); else root.GenesisMastery = factory(null); })(this, function (crypto) {
  "use strict";
  var SCHEMA = "genesis-mastery/0.1";
  function clone(x) { return JSON.parse(JSON.stringify(x)); }
  function sha(s) { return crypto.createHash("sha256").update(s).digest("hex"); }
  function stable(o) { return JSON.stringify(o, Object.keys(o).sort()); }

  // ---- curves (versioned, named; parameters live in the skill definition) ----
  var CURVES = {
    // XP from level L to L+1 = a + b·L + c·L²
    "quadratic/1": function (p, L) { return p.a + p.b * L + p.c * L * L; }
  };
  function xpToNext(def, L) { var f = CURVES[def.curve.id]; if (!f) throw new Error("UNKNOWN_CURVE " + def.curve.id); return f(def.curve.params, L); }
  function cumulativeXp(def, L) { var t = 0; for (var i = 0; i < L; i++) t += xpToNext(def, i); return t; }
  function levelFor(def, xp) { var L = 0; while (L < def.max_level && xp >= cumulativeXp(def, L + 1)) L++; return L; }

  // ---- capability at a level: base + per-level + milestone bonuses, with provenance for every number ----
  function capability(def, level) {
    var cap = {}, prov = {};
    Object.keys(def.base).forEach(function (k) { cap[k] = def.base[k].value; prov[k] = [{ amount: def.base[k].value, source: def.base[k].source }]; });
    (def.per_level || []).forEach(function (pl) { var add = pl.add * level; if (add) { cap[pl.key] += add; prov[pl.key].push({ amount: add, source: def.id + "@" + def.version + " per_level ×" + level }); } });
    (def.milestones || []).forEach(function (m) { if (level >= m.level) (m.bonuses || []).forEach(function (b) { cap[b.key] += b.add; prov[b.key].push({ amount: b.add, source: def.id + "@" + def.version + " milestone " + m.id }); }); });
    return { skill: def.id, version: def.version, level: level, values: cap, provenance: prov };
  }

  // ---- milestones: eligibility only; a grant needs its prerequisites AND an external, recorded approval ----
  function milestoneStatus(def, charState, features) {
    var st = charState.skills[def.id] || { level: 0 };
    return (def.milestones || []).map(function (m) {
      var missing = [];
      if (st.level < m.level) missing.push({ code: "LEVEL", need: m.level, have: st.level });
      (m.requires_skills || []).forEach(function (r) { var o = charState.skills[r.skill]; if (!o || o.level < r.level) missing.push({ code: "SKILL", skill: r.skill, need: r.level, have: o ? o.level : 0 }); });
      (m.requires_features || []).forEach(function (f) { if (!(features || []).includes(f)) missing.push({ code: "FEATURE", feature: f }); });
      var granted = (charState.grants || []).filter(function (g) { return g.milestone === m.id; })[0] || null;
      return { id: m.id, level: m.level, kind: m.kind, eligible: missing.length === 0, missing: missing, granted: granted, never_grants: m.never_grants || [] };
    });
  }
  // Recording a milestone grant requires eligibility plus an approval record (owner/GM/training event) — never automatic.
  function recordGrant(def, charState, milestoneId, approval, features) {
    var ms = milestoneStatus(def, charState, features).filter(function (m) { return m.id === milestoneId; })[0];
    if (!ms) return { ok: false, code: "UNKNOWN_MILESTONE" };
    if (!ms.eligible) return { ok: false, code: "NOT_ELIGIBLE", missing: ms.missing };
    if (ms.granted) return { ok: true, duplicate: true, grant: ms.granted, state: charState };
    if (!approval || !approval.by || !approval.event_id || !approval.source) return { ok: false, code: "APPROVAL_REQUIRED" };
    var s = clone(charState), g = { milestone: milestoneId, skill: def.id, version: def.version, approved_by: approval.by, event_id: approval.event_id, source: approval.source, status: "sandbox_proposal" };
    s.grants = (s.grants || []).concat([g]); return { ok: true, grant: g, state: s };
  }

  // ---- XP classification: ONLY from fields of the committed event, by the skill's explicit rules ----
  function classify(def, ev, charState, cap) {
    var rules = def.xp_rules, total = 0, parts = [];
    var base = rules.base[ev.type]; if (base == null) return null;
    total += base; parts.push({ rule: "base:" + ev.type, xp: base });
    (rules.bonuses || []).forEach(function (b) {
      var hit = false;
      if (b.when === "load_fraction_at_least") hit = ev.facts.weight_lb != null && ev.facts.weight_lb >= b.value * cap.values.max_weight_lb;
      else if (b.when === "range_fraction_at_least") hit = ev.facts.distance_ft != null && ev.facts.distance_ft >= b.value * cap.values.range_ft;
      else if (b.when === "first_object_kind") hit = !!ev.facts.object_kind && !((charState.seen || {})[def.id + ":" + ev.facts.object_kind]);
      else if (b.when === "in_encounter") hit = !!ev.facts.in_encounter && b.enabled !== false;
      if (hit && b.enabled !== false) { total += b.xp; parts.push({ rule: b.id, xp: b.xp }); }
    });
    return { xp: total, parts: parts };
  }

  // ---- the event gate: what counts as a validated, committed use ----
  function validateEvent(def, ev, character) {
    if (!ev || !ev.event_id) return "NO_EVENT_ID";
    if (ev.committed !== true) return "NOT_COMMITTED";
    if (def.accepted_authorities.indexOf(ev.authority) < 0) return "UNTRUSTED_AUTHORITY";   // narration, client assertions, prose: refused
    if (ev.actor !== character) return "WRONG_ACTOR";
    if (ev.skill !== def.id) return "WRONG_SKILL";
    if (def.xp_rules.base[ev.type] == null) return "NOT_A_SKILL_USE";
    if (ev.validated !== true) return "NOT_VALIDATED";   // range/weight/target legality was checked by the authority
    return null;
  }

  function newCharacter(character) { return { schema: SCHEMA, character: character, class_level_independent: true, skills: {}, applied: {}, receipts: [], seen: {}, grants: [], pending: null }; }
  function receiptId(character, def, ev) { return "xp_" + sha([character, def.id, def.version, ev.event_id].join("|")).slice(0, 24); }

  // Two-phase award. phase 1 writes `pending` (the intended receipt); phase 2 applies it. A crash between them is recovered
  // by recover(): the pending receipt is applied exactly once (or discarded if it was already applied).
  function begin(def, charState, ev) {
    var why = validateEvent(def, ev, charState.character); if (why) return { ok: false, code: why };
    var key = def.id + "|" + ev.event_id;
    if (charState.applied[key]) return { ok: true, duplicate: true, receipt: charState.receipts.filter(function (r) { return r.id === charState.applied[key]; })[0], state: charState };
    if (charState.pending) return { ok: false, code: "TXN_PENDING", pending: charState.pending.id };
    var st = charState.skills[def.id] || { level: 0, xp: 0, version: def.version };
    var cap = capability(def, st.level), cl = classify(def, ev, charState, cap);
    var xp = Math.max(def.xp_rules.min_per_use, cl.xp), after = st.xp + xp, lvl = levelFor(def, after);
    var rc = { id: receiptId(charState.character, def, ev), schema: SCHEMA, character: charState.character, skill: def.id, version: def.version, event_id: ev.event_id,
               authority: ev.authority, type: ev.type, xp: xp, parts: cl.parts, xp_before: st.xp, xp_after: after, level_before: st.level, level_after: lvl,
               object_kind: ev.facts.object_kind || null };
    rc.hash = sha(stable(rc));
    var s = clone(charState); s.pending = rc; return { ok: true, phase: "pending", receipt: rc, state: s };
  }
  function commit(charState) {
    var rc = charState.pending; if (!rc) return { ok: false, code: "NO_PENDING" };
    var s = clone(charState), key = rc.skill + "|" + rc.event_id;
    if (s.applied[key]) { s.pending = null; return { ok: true, duplicate: true, state: s }; }
    var st = s.skills[rc.skill] || { level: 0, xp: 0, version: rc.version };
    if (st.xp !== rc.xp_before) { s.pending = null; return { ok: false, code: "STALE_PENDING", state: s }; }   // another award landed first: re-run begin
    st.xp = rc.xp_after; st.level = rc.level_after; st.version = rc.version; s.skills[rc.skill] = st;
    s.applied[key] = rc.id; s.receipts.push(rc); if (rc.object_kind) s.seen[rc.skill + ":" + rc.object_kind] = true; s.pending = null;
    return { ok: true, receipt: rc, state: s };
  }
  function award(def, charState, ev) { var b = begin(def, charState, ev); if (!b.ok || b.duplicate) return b; return commit(b.state); }
  function recover(charState) { return charState.pending ? commit(charState) : { ok: true, state: charState, nothing: true }; }
  // Rebuild a character's mastery from its event log alone (the authority's committed events), in order.
  function replay(defs, character, events) {
    var s = newCharacter(character), byId = {}; defs.forEach(function (d) { byId[d.id] = d; });
    events.forEach(function (ev) { var d = byId[ev.skill]; if (!d) return; var r = award(d, s, ev); if (r.ok && r.state) s = r.state; });
    return s;
  }
  function verifyReceipt(rc) { var c = clone(rc); delete c.hash; return sha(stable(c)) === rc.hash; }
  function table(def) {
    var rows = []; for (var L = 0; L <= def.max_level; L++) { var cap = capability(def, L);
      rows.push({ level: L, xp_to_next: L < def.max_level ? xpToNext(def, L) : null, cumulative_xp: cumulativeXp(def, L), values: cap.values,
                  milestones: (def.milestones || []).filter(function (m) { return m.level === L; }).map(function (m) { return m.id; }) }); }
    return rows;
  }
  return { SCHEMA: SCHEMA, CURVES: CURVES, xpToNext: xpToNext, cumulativeXp: cumulativeXp, levelFor: levelFor, capability: capability, milestoneStatus: milestoneStatus,
           recordGrant: recordGrant, classify: classify, validateEvent: validateEvent, newCharacter: newCharacter, begin: begin, commit: commit, award: award,
           recover: recover, replay: replay, verifyReceipt: verifyReceipt, table: table, receiptId: receiptId };
});
