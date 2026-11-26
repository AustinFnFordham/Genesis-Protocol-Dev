// Telekinetic Control pacing / farming / environment study (CC-007 §5). Sandbox; uses the real substrate. node sim_telekinesis.cjs [--json]
const M = require("./mastery.js"), TK = require("./skills/telekinetic_control.v0.1.json"), SCENE = require("./fixtures/scene_objects.json");
const mulberry = (a) => () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const KINDS = ["tool", "device", "crate", "cell", "mechanism", "container", "weapon", "debris", "panel", "rope", "canister", "part"];
// A player's uses in one session. routine: lifts at modest load/range; some demanding; new object kinds appear over time.
function session(rng, perSession, cap, seenKinds, demandingShare) {
  const uses = []; for (let i = 0; i < perSession; i++) {
    const demanding = rng() < demandingShare, novel = rng() < 0.15 ? KINDS[Math.floor(rng() * KINDS.length)] : KINDS[Math.floor(rng() * 3)];
    uses.push({ weight_lb: demanding ? Math.ceil(0.8 * cap.max_weight_lb) : Math.ceil(0.3 * cap.max_weight_lb), distance_ft: demanding && rng() < 0.5 ? Math.ceil(0.8 * cap.range_ft) : Math.ceil(0.3 * cap.range_ft), object_kind: novel }); }
  return uses;
}
function run(label, perSession, demandingShare, sessions, routineCapPerScene) {
  const rng = mulberry(20261125), out = { label, perSession, demandingShare, routineCapPerScene: routineCapPerScene || null, reached: {} }; let s = M.newCharacter("aero"), id = 0;
  for (let k = 1; k <= sessions; k++) {
    const cap = M.capability(TK, (s.skills.telekinetic_control || { level: 0 }).level).values; let routineThisScene = 0;
    for (const u of session(rng, perSession, cap, s.seen, demandingShare)) {
      const ev = { event_id: "sim" + (++id), authority: "atomic_exploration", committed: true, validated: true, type: "telekinesis_use", skill: "telekinetic_control", actor: "aero", facts: Object.assign({ in_encounter: false }, u) };
      const preview = M.begin(TK, s, ev); if (!preview.ok) continue;
      const isRoutine = preview.receipt.parts.length === 1;
      if (routineCapPerScene && isRoutine && routineThisScene >= routineCapPerScene) continue;   // candidate anti-farm rule (not adopted)
      if (isRoutine) routineThisScene++; s = M.commit(preview.state).state;
    }
    const L = (s.skills.telekinetic_control || { level: 0 }).level; [5, 10, 15, 20].forEach((m) => { if (L >= m && !out.reached[m]) out.reached[m] = k; });
    if (L >= 20) break;
  }
  out.final_level = s.skills.telekinetic_control.level; out.final_xp = s.skills.telekinetic_control.xp; return out;
}
// pure farming: one trivial lift of the same tool, repeated (1 XP each after the first)
function farm() { let s = M.newCharacter("aero"), i = 0; const at = {};
  while (s.skills.telekinetic_control === undefined || s.skills.telekinetic_control.level < 20) { s = M.award(TK, s, { event_id: "f" + (++i), authority: "atomic_exploration", committed: true, validated: true, type: "telekinesis_use", skill: "telekinetic_control", actor: "aero", facts: { weight_lb: 1, distance_ft: 5, object_kind: "tool", in_encounter: false } }).state;
    const L = s.skills.telekinetic_control.level; [5, 10, 15, 20].forEach((m) => { if (L >= m && !at[m]) at[m] = i; }); }
  return at; }
// which fixture objects are in reach, by level (environmental interaction)
function environment() { return [0, 4, 5, 10, 15, 20].map((L) => { const c = M.capability(TK, L).values;
  const usable = SCENE.objects.filter((o) => o.visible && !o.attended && !o.fixed && o.weight_lb <= c.max_weight_lb && o.distance_ft <= c.range_ft).map((o) => o.id);
  return { level: L, range_ft: c.range_ft, max_weight_lb: c.max_weight_lb, movable_fixture_objects: usable.length + "/" + SCENE.objects.filter((o) => o.visible && !o.attended && !o.fixed).length, ids: usable }; }); }
const res = {
  table: M.table(TK).map((r) => ({ level: r.level, xp_to_next: r.xp_to_next, cumulative_xp: r.cumulative_xp, range_ft: r.values.range_ft, max_weight_lb: r.values.max_weight_lb, milestone: r.milestones[0] || "" })),
  pacing: [run("light: 5 uses/session", 5, 0.15, 400), run("typical: 10 uses/session", 10, 0.2, 400), run("heavy: 20 uses/session", 20, 0.25, 400),
           run("typical + routine cap 3/scene (candidate)", 10, 0.2, 400, 3), run("heavy + routine cap 3/scene (candidate)", 20, 0.25, 400, 3)],
  pure_farming_uses_to_level: farm(),
  environment: environment()
};
if (process.argv.includes("--json")) console.log(JSON.stringify(res, null, 1));
else { console.table(res.table); res.pacing.forEach((p) => console.log(p.label, "sessions to L5/L10/L15/L20:", [5, 10, 15, 20].map((m) => p.reached[m] || ">400").join(" / "))); console.log("pure farming, uses to L5/10/15/20:", res.pure_farming_uses_to_level); console.table(res.environment.map((e) => ({ level: e.level, range: e.range_ft, weight: e.max_weight_lb, movable: e.movable_fixture_objects }))); }
