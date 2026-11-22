// CC-005b: campaign-grant overlay (Jedi Fundamentals Minor Telekinesis), ranged-in-melee opt-in rule, movement-projected odds.
const assert = require("assert");
const E = require("./engine.js"), P = require("./predict.js"), C = require("./catalog.json"), S = require("./scenarios.json"), O = require("./campaign_overlay.js");
const JF = require("../../campaigns/starwars_litrpg/creator/jedi_fundamentals.json"), OV = [O.fromJediFundamentals(JF)];
let pass = 0, fail = 0; const t = (n, fn) => { try { fn(); pass++; console.log("ok", n); } catch (e) { fail++; console.log("FAIL", n, "\n  ", e.message); } };
const st = (sc, o) => E.newState(C, S, sc || "duelist", Object.assign({ seed: 1 }, o || {}));
const why = (s, pid, step, who) => E.availability(s, who || "aero", pid, Object.assign({ pid }, step || {})).reasons.map((r) => r.code);
function disarm(s, who) { const a = s.actors[who]; a.dropped = JSON.parse(JSON.stringify(a.weapon)); a.weapon.held = false; if (a.weapon.kind === "lightsaber") a.weapon.ignited = false; }

// ---- D1 campaign overlay ----
t("overlay grants Minor Telekinesis only in starwars_litrpg, only to a character the rule names", () => {
  assert(st("duelist", { campaign: "starwars_litrpg", overlays: OV }).actors.aero.profiles.includes("minor_telekinesis"));
  assert(!st("duelist", { overlays: OV }).actors.aero.profiles.includes("minor_telekinesis"), "no campaign → no grant");
  assert(!st("duelist", { campaign: "other_campaign", overlays: OV }).actors.aero.profiles.includes("minor_telekinesis"), "other campaign → no grant");
  assert(!st("duelist", { campaign: "starwars_litrpg", overlays: OV }).actors.ilsa.profiles.includes("minor_telekinesis"), "not named → no grant (Force sensitivity never qualifies)");
});
t("the shared sheet and powers_known are untouched; provenance is recorded on the grant", () => {
  assert(!S.aero.grants.sheet.includes("minor_telekinesis") && !S.aero.grants.sandbox_proposal.includes("minor_telekinesis"));
  const g = st("duelist", { campaign: "starwars_litrpg", overlays: OV }).actors.aero.campaign_grants[0];
  assert(g.rule === "jedi_fundamentals_minor_telekinesis" && g.status === "approved_provisional" && /2026-11-11/.test(g.granted_by) && /JEDI_FUNDAMENTALS/.test(g.source));
  assert.strictEqual(C.profiles.minor_telekinesis.status, "campaign_ruling");
});
t("costs a Main action and 0 FP; limits come from the rule file (10 lb, 30 ft, one object)", () => {
  const p = C.profiles.minor_telekinesis; assert.deepStrictEqual(p.cost, { main: 1 }); assert.strictEqual(p.limits.force_point_cost, 0);
  assert.strictEqual(p.limits.max_weight_lb, JF.limits.max_weight_lb); assert.strictEqual(p.limits.range_ft, JF.limits.range_ft); assert.strictEqual(p.limits.objects_at_once, 1);
});
t("never: no disarming or attended objects, no creatures (held weapon refused)", () => {
  const s = st("duelist", { campaign: "starwars_litrpg", overlays: OV }); s.dist["aero|ilsa"] = 5;
  assert(why(s, "minor_telekinesis", { object: "ilsa_weapon" }).includes("ATTENDED_OBJECT"));
  assert(why(s, "minor_telekinesis", { object: "ilsa" }).includes("NO_UNATTENDED_OBJECT"));
  assert(why(s, "minor_telekinesis", { object: "own_weapon" }).includes("NO_UNATTENDED_OBJECT"), "nothing of his is loose");
});
t("retrieve: Aero's dropped saber returns to his hand (unlit) as a Main action", () => {
  const s = st("duelist", { campaign: "starwars_litrpg", overlays: OV }); s.dist["aero|ilsa"] = 5; disarm(s, "aero");
  const v = E.validatePlan(s, "aero", [{ pid: "minor_telekinesis", object: "own_weapon" }, { pid: "toggle_blade" }]); assert(v.legal, JSON.stringify(v.steps));
  const r = E.resolveTurn(s, "aero", [{ pid: "minor_telekinesis", object: "own_weapon" }], {}); const A = r.state.actors.aero;
  assert(A.weapon.held && !A.dropped && A.weapon.ignited === false && A.budget.main === 0 && A.fp === s.actors.aero.fp);
  assert(r.log.some((l) => l.ev === "telekinesis" && l.mode === "retrieve")); assert(!r.log.some((l) => l.ev === "damage"));
});
t("reposition: Ilsa's DROPPED blade goes 30 ft out; she then needs 30 ft of movement to recover it", () => {
  const s = st("duelist", { campaign: "starwars_litrpg", overlays: OV }); s.dist["aero|ilsa"] = 5; disarm(s, "ilsa");
  const r = E.resolveTurn(s, "aero", [{ pid: "minor_telekinesis", object: "ilsa_weapon" }], {}); assert(r.state.actors.ilsa.dropped.far);
  let s2 = E.endTurn(r.state); assert.strictEqual(E.current(s2), "ilsa");
  assert(E.validatePlan(s2, "ilsa", [{ pid: "recover_weapon" }]).legal, "with 30 ft she can reach it");
  const v = E.validatePlan(s2, "ilsa", [{ pid: "move", dest: "close", target: "aero" }, { pid: "recover_weapon" }]); assert(!v.legal || v.budget_after.movement_ft >= 0);
  s2.actors.ilsa.budget.movement_ft = 20; assert(E.availability(s2, "ilsa", "recover_weapon", { pid: "recover_weapon" }).reasons.some((x) => x.code === "WEAPON_FAR"));
  assert(E.validatePlan(s2, "ilsa", E.npcPlan(s2, "ilsa")).legal, "the GM policy picks a legal alternative");
});
t("out of range: a dropped weapon beyond 30 ft can't be moved", () => {
  const s = st("duelist", { campaign: "starwars_litrpg", overlays: OV }); s.dist["aero|ilsa"] = 25; disarm(s, "ilsa");
  assert(why(s, "minor_telekinesis", { object: "ilsa_weapon" }).includes("OUT_OF_RANGE"));
});
t("it is not Force Pull/Push: no such profile exists or is granted", () => {
  const a = st("duelist", { campaign: "starwars_litrpg", overlays: OV }).actors.aero; assert(!a.profiles.some((p) => /force_(pull|push)/.test(p)));
});

// ---- D4 ranged-in-melee (opt-in) ----
const blasterState = (sw) => { const s = st("relay_droid", { switches: sw }); s.actors.aero.sidearm.held = true; s.dist["aero|droid"] = 5; return s; };
const disOf = (s) => E.resolveTurn(s, "aero", [{ pid: "blaster_shot", target: "droid" }], {}).log.find((l) => l.ev === "attack").dis;
t("ranged-in-melee: off by default; on → disadvantage when a hostile that can act is within 5 ft", () => {
  assert(!disOf(blasterState({})).includes("enemy within 5 ft"));
  assert(disOf(blasterState({ ranged_in_melee_disadvantage: true })).includes("enemy within 5 ft"));
});
t("ranged-in-melee exceptions: hostile down, hidden or incapacitated (grappled is NOT incapacitated); melee attacks unaffected", () => {
  let s = blasterState({ ranged_in_melee_disadvantage: true }); s.actors.droid.down = true; assert(!E.rangeMods(s, "aero", "droid", C.profiles.blaster_shot).includes("enemy within 5 ft"));
  s = blasterState({ ranged_in_melee_disadvantage: true }); s.actors.droid.conds.hidden = { dc: 15 }; assert(!E.rangeMods(s, "aero", "droid", C.profiles.blaster_shot).includes("enemy within 5 ft"));
  s = blasterState({ ranged_in_melee_disadvantage: true }); s.actors.droid.conds.incapacitated = {}; assert(!E.rangeMods(s, "aero", "droid", C.profiles.blaster_shot).includes("enemy within 5 ft"));
  s = blasterState({ ranged_in_melee_disadvantage: true }); s.actors.droid.conds.grappled = { by: "aero" }; assert(E.rangeMods(s, "aero", "droid", C.profiles.blaster_shot).includes("enemy within 5 ft"));
  s = blasterState({ ranged_in_melee_disadvantage: true }); assert.deepStrictEqual(E.rangeMods(s, "aero", "droid", C.profiles.saber_strike), []);
  s = blasterState({ ranged_in_melee_disadvantage: true }); s.dist["aero|droid"] = 10; assert(!E.rangeMods(s, "aero", "droid", C.profiles.blaster_shot).includes("enemy within 5 ft"));
});
t("ranged-in-melee applies to NPC ranged attacks too (same validator)", () => {
  const s = blasterState({ ranged_in_melee_disadvantage: true }); assert(E.rangeMods(s, "droid", "aero", C.profiles.npc_blaster).includes("enemy within 5 ft"));
});
t("ranged-in-melee provenance and approval status are recorded", () => {
  const sw = C.ruleset.switches.ranged_in_melee_disadvantage; assert(sw.default === false && /NOT on Aero's runtime sheet/.test(sw.provenance.source) && /opt-in sandbox/.test(sw.provenance.approval) && sw.provenance.exceptions.length >= 3);
});

// ---- movement-projected odds ----
t("odds use the distance AFTER planned moves: close-then-strike shows a real hit chance", () => {
  const s = st("duelist"); const a = P.analyzePlan(s, "aero", [{ pid: "move", dest: "close", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }]).steps[1];
  assert(a.kind === "attack" && a.hit > 0.3 && a.distance_ft === 5, JSON.stringify([a.hit, a.distance_ft]));
});
t("odds after a planned withdrawal include the blaster's long-range disadvantage", () => {
  const s = st("relay_droid"); s.actors.aero.sidearm.held = true; s.dist["aero|droid"] = 30;
  const plan = [{ pid: "move", dest: "withdraw" }, { pid: "blaster_shot", target: "droid" }]; const a = P.analyzePlan(s, "aero", plan).steps[1];
  assert(a.distance_ft === 45 && a.dis.includes("long range"), JSON.stringify([a.distance_ft, a.dis]));
  const sim = P.simulate(s, "aero", plan, { n: 200 }); assert(sim, "the whole plan still simulates");
});
t("learned AC bounds always contain the true AC (200 seeded duels, all outcomes incl. parry/riposte)", () => {
  for (let seed = 1; seed <= 200; seed++) { let s = E.newState(C, S, "duelist", { seed }); s.dist["aero|ilsa"] = 5;
    for (let k = 0; k < 8 && !s.over; k++) { const a = E.current(s); const plan = a === "aero" ? [{ pid: "saber_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }].filter((x, i, arr) => E.validatePlan(s, "aero", arr.slice(0, i + 1)).legal) : E.npcPlan(s, a);
      let ch = {}, r; for (let g = 0; g < 10; g++) { r = E.resolveTurn(s, a, plan, ch); if (!r.paused) break; ch[r.paused.key] = r.paused.options[0]; } s = E.endTurn(r.state);
      const b = E.knowledge(s, "aero").ilsa; if (b) assert((b.ac_min == null || b.ac_min <= 15) && (b.ac_max == null || b.ac_max >= 15), "seed " + seed + ": " + JSON.stringify(b)); } }
});
t("player projection never carries enemy HP/AC numbers; hidden actors and their rolls are omitted", () => {
  const p = E.newState(C, S, "predator", { seed: 3 }); const v = E.playerProjection(p, "aero"); assert(!v.actors.stalker && !v.receipts.some((r) => r.actor === "stalker"));
  let s = E.newState(C, S, "duelist", { seed: 5 }); s.dist["aero|ilsa"] = 5; let ch = {}, r; for (let g = 0; g < 8; g++) { r = E.resolveTurn(s, "aero", [{ pid: "saber_strike", target: "ilsa" }], ch); if (!r.paused) break; ch[r.paused.key] = null; }
  const pv = E.playerProjection(E.endTurn(r.state), "aero"); const txt = JSON.stringify(pv);
  assert(pv.actors.ilsa.hp === null && pv.actors.ilsa.ac === null && !/"type":"ac","target":"ilsa","value":\d/.test(txt) && !/\/20\)/.test(txt));
});
setTimeout(() => { console.log(fail ? fail + " FAILED, " + pass + " passed" : "all " + pass + " passed"); process.exit(fail ? 1 : 0); }, 10);
