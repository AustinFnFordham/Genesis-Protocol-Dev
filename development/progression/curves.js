// Deterministic curve evaluator and table generator (CC-008 B/C). Curves are versioned by id; parameters live in the track.
"use strict";
const DEFS = {
  // XP(L→L+1) = a + b·L + c·L², L measured from start_level (CC-007 mastery.js convention)
  "quadratic/1": { step: (p, i) => p.a + p.b * i + p.c * i * i, params: ["a", "b", "c"] },
  // XP(L→L+1) = round(base · ratio^i)
  "geometric/1": { step: (p, i) => Math.round(p.base * Math.pow(p.ratio, i)), params: ["base", "ratio"] },
  // XP(L→L+1) = a + b·i
  "linear/1": { step: (p, i) => p.a + p.b * i, params: ["a", "b"] },
  // explicit cumulative table (authoritative tables, e.g. a published level/XP table)
  "table/1": { table: true },
  // no XP (driven by another track or milestone-only)
  "none/1": { none: true }
};
function startOf(track) { return track.start_level || 0; }
function maxOf(track) { return track.max_level == null ? startOf(track) + 20 : track.max_level; }
function stepXp(track, L) {
  const c = track.curve || {}, d = DEFS[c.id]; if (!d) throw new Error("UNKNOWN_CURVE " + c.id);
  if (d.none) return null;
  if (d.table) { const i = L - startOf(track); return c.table[i + 1] - c.table[i]; }
  return d.step(c.params, L - startOf(track));
}
function cumulative(track, L) {
  const c = track.curve || {}, d = DEFS[c.id]; if (!d) throw new Error("UNKNOWN_CURVE " + c.id);
  if (d.none) return null; if (d.table) return c.table[L - startOf(track)];
  let t = 0; for (let l = startOf(track); l < L; l++) t += stepXp(track, l); return t;
}
function levelFor(track, xp) { const d = DEFS[(track.curve || {}).id]; if (!d || d.none) return startOf(track);
  let L = startOf(track); const M = maxOf(track); while (L < M && xp >= cumulative(track, L + 1)) L++; return L; }
// validation: every step a positive integer, cumulative strictly increasing, table complete and starting at 0
function validate(track) {
  const errs = [], c = track.curve || {}, d = DEFS[c.id];
  if (!d) return [{ code: "UNKNOWN_CURVE", curve: c.id }];
  if (d.none) return track.xp_quantity !== "none" ? [{ code: "XP_TRACK_WITHOUT_CURVE" }] : [];
  if (track.xp_quantity === "none") errs.push({ code: "CURVE_ON_NON_XP_TRACK" });
  (d.params || []).forEach((p) => { if (typeof (c.params || {})[p] !== "number") errs.push({ code: "MISSING_PARAM", param: p }); });
  if (errs.length) return errs;
  if (d.table) { const want = maxOf(track) - startOf(track) + 1;
    if (!Array.isArray(c.table) || c.table.length !== want) return [{ code: "TABLE_LENGTH", need: want, have: (c.table || []).length }];
    if (c.table[0] !== 0) errs.push({ code: "TABLE_START_NOT_ZERO" }); }
  let prev = -1;
  for (let L = startOf(track); L < maxOf(track); L++) { const s = stepXp(track, L);
    if (!Number.isInteger(s) || s <= 0) errs.push({ code: "NON_POSITIVE_OR_FRACTIONAL_STEP", level: L, step: s });
    const cu = cumulative(track, L + 1); if (!(cu > prev)) errs.push({ code: "NOT_MONOTONIC", level: L + 1 }); prev = cu; }
  return errs;
}
function table(track) { const rows = []; for (let L = startOf(track); L <= maxOf(track); L++) rows.push({ level: L, xp_to_next: L < maxOf(track) ? stepXp(track, L) : null, cumulative_xp: cumulative(track, L) }); return rows; }
module.exports = { DEFS, stepXp, cumulative, levelFor, validate, table, startOf, maxOf };
