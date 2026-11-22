// CC-004 engine: capability coverage, equipment state, resource accounting, combo truth, roll ownership. node test_cc004.cjs
const assert = require("assert");
const E = require("./engine.js"), C = require("./catalog.json"), S = require("./scenarios.json");
let pass = 0, fail = 0; const t = (n, fn) => { try { fn(); pass++; console.log("ok", n); } catch (e) { fail++; console.log("FAIL", n, "\n  ", e.message); } };
const st = (sc, seed, d) => { const s = E.newState(C, S, sc || "duelist", { seed: seed || 1 }); if (d != null) Object.keys(s.dist).forEach((k) => s.dist[k] = d); return s; };
const why = (s, pid, step) => E.availability(s, "aero", pid, Object.assign({ pid }, step || {})).reasons.map((r) => r.code);
function play(s, a, plan, pick) { let ch = {}, r; for (let g = 0; g < 12; g++) { r = E.resolveTurn(s, a, plan, ch); if (!r.paused) break; ch[r.paused.key] = pick ? pick(r.paused) : null; } return r; }

// ---- coverage: every attack execution on the sheet exists and is legal when it should be ----
t("the attack selector covers lightsaber (1H and 2H), Echani unarmed, blaster shot and grapple", () => {
  ["saber_strike", "saber_strike_2h", "unarmed_strike", "blaster_shot", "grapple"].forEach((pid) => { assert(C.profiles[pid], pid); assert(S.aero.grants.sheet.includes(pid), pid + " is sheet-sourced"); });
  const s = st("duelist", 1, 5); ["saber_strike", "saber_strike_2h", "unarmed_strike", "grapple"].forEach((pid) => assert.deepStrictEqual(why(s, pid, { target: "ilsa" }), [], pid));
  assert(why(s, "blaster_shot", { target: "ilsa" }).includes("SIDEARM_HOLSTERED"));
});
t("Force powers come from the sheet only: Battle Insight, Burst, Force Connection; no telekinesis", () => {
  ["battle_insight", "burst", "force_connection"].forEach((pid) => assert(S.aero.grants.sheet.includes(pid)));
  assert(!Object.keys(C.profiles).some((k) => /telekin/i.test(k)) && S.aero.not_on_sheet.some((x) => /Telekinesis/.test(x.name)), "telekinesis is listed as not on the sheet, with a reason");
});
// ---- blaster: draw, range, ammo, reload ----
t("drawing the blaster costs the object interaction and occupies the off hand", () => {
  const s = st("relay_droid"); const v = E.validatePlan(s, "aero", [{ pid: "draw_sidearm" }, { pid: "blaster_shot", target: "droid" }]);
  assert(v.legal, JSON.stringify(v.steps)); assert.strictEqual(v.budget_after.object, 0); assert.strictEqual(v.budget_after.main, 0);
  const v2 = E.validatePlan(s, "aero", [{ pid: "draw_sidearm" }, { pid: "holster_sidearm" }]); assert(v2.steps[1].reasons.some((r) => r.code === "NO_OBJECT"), "only one object interaction");
  const v3 = E.validatePlan(st("duelist", 1, 5), "aero", [{ pid: "draw_sidearm" }, { pid: "saber_strike_2h", target: "ilsa" }]); assert(v3.steps[1].reasons.some((r) => r.code === "HAND_OCCUPIED"));
});
t("blaster: disadvantage beyond 40 ft (sheet); adjacent-enemy penalty only behind a proposal switch; refused beyond 160 ft", () => {
  const s = st("relay_droid"); s.actors.aero.sidearm.held = true;
  s.dist["aero|droid"] = 60; let r = E.resolveTurn(s, "aero", [{ pid: "blaster_shot", target: "droid" }], {}); assert(r.log.find((l) => l.ev === "attack").dis.includes("long range"));
  s.dist["aero|droid"] = 5; r = E.resolveTurn(s, "aero", [{ pid: "blaster_shot", target: "droid" }], {}); assert(!r.log.find((l) => l.ev === "attack").dis.includes("enemy within 5 ft"), "not a sheet rule: off by default");
  s.switches.ranged_in_melee_disadvantage = true; r = E.resolveTurn(s, "aero", [{ pid: "blaster_shot", target: "droid" }], {}); assert(r.log.find((l) => l.ev === "attack").dis.includes("enemy within 5 ft"), "switch on (sandbox proposal)"); s.switches.ranged_in_melee_disadvantage = false;
  s.dist["aero|droid"] = 30; r = E.resolveTurn(s, "aero", [{ pid: "blaster_shot", target: "droid" }], {}); assert.deepStrictEqual(r.log.find((l) => l.ev === "attack").dis, []);
  s.dist["aero|droid"] = 170; assert(why(s, "blaster_shot", { target: "droid" }).includes("OUT_OF_RANGE"));
});
t("each shot spends ammo; empty pistol refuses; reload is a Main action that draws from reserve", () => {
  const s = st("relay_droid"); s.actors.aero.sidearm.held = true; s.actors.aero.sidearm.ammo = 1;
  const r = E.resolveTurn(s, "aero", [{ pid: "blaster_shot", target: "droid" }], {}); assert.strictEqual(r.state.actors.aero.sidearm.ammo, 0);
  const s2 = st("relay_droid"); s2.actors.aero.sidearm.held = true; s2.actors.aero.sidearm.ammo = 0;
  assert(why(s2, "blaster_shot", { target: "droid" }).includes("OUT_OF_AMMO"));
  const rr = E.resolveTurn(s2, "aero", [{ pid: "reload_sidearm" }], {}); assert.strictEqual(rr.state.actors.aero.sidearm.ammo, 12); assert.strictEqual(rr.state.actors.aero.sidearm.reserve, 26);
  assert(E.validatePlan(s2, "aero", [{ pid: "reload_sidearm" }, { pid: "blaster_shot", target: "droid" }]).steps[1].reasons.some((x) => x.code === "NO_MAIN"), "reload uses the Main action");
  const s3 = st("relay_droid"); s3.actors.aero.sidearm.held = true; assert(why(s3, "reload_sidearm").includes("FULL_MAGAZINE"));
});
// ---- saber grips, Burst, grapple ----
t("two-handed grip does 1d10+3; one-handed 1d8+3", () => { assert.strictEqual(C.profiles.saber_strike_2h.resolution.damage, "1d10+3"); assert.strictEqual(C.profiles.saber_strike.resolution.damage, "1d8+3"); });
t("Burst: DEX save DC 12 for everyone else within 5 ft; failure = 1d4 force + prone; Aero unaffected", () => {
  let found = { fail: false, ok: false };
  for (let seed = 1; seed < 60; seed++) { const s = st("duelist", seed, 5); const hp = s.actors.aero.hp; const r = E.resolveTurn(s, "aero", [{ pid: "burst" }], {});
    const sv = r.log.find((l) => l.ev === "save"); assert(sv && sv.dc === 12 && sv.actor === "ilsa"); assert.strictEqual(r.state.actors.aero.hp, hp);
    if (sv.win) { found.ok = true; assert(!r.state.actors.ilsa.conds.prone); } else { found.fail = true; assert(r.state.actors.ilsa.conds.prone); assert(r.log.some((l) => l.ev === "damage" && l.target === "ilsa" && l.amount >= 1 && l.amount <= 4)); } }
  assert(found.fail && found.ok, "both outcomes seen");
  const far = st("duelist", 1, 20); const r = E.resolveTurn(far, "aero", [{ pid: "burst" }], {}); assert(r.log.some((l) => l.ev === "no_targets"));
});
t("grapple: free hand, +5 vs Athletics/Acrobatics, speed 0, no damage; moving away releases it", () => {
  let got = null; for (let seed = 1; seed < 80 && !got; seed++) { const s = st("predator", seed, 5); s.actors.stalker.conds = {}; s.order = ["aero", "stalker"]; s.turn = 0;
    const r = E.resolveTurn(s, "aero", [{ pid: "grapple", target: "stalker" }], {}); if (r.log.some((l) => l.ev === "grapple")) got = r; }
  assert(got); assert(got.state.actors.stalker.conds.grappled); assert(!got.log.some((l) => l.ev === "damage"));
  assert(got.receipts[0].formula === "1d20+5", "martial check +5 from the sheet");
  const s = E.endTurn(got.state); assert(E.availability(s, "stalker", "move", { pid: "move", dest: "close", target: "aero" }).reasons.some((r) => r.code === "GRAPPLED"));
});
// ---- reactions ----
t("Lightsaber Deflect: only vs ranged energy, blade lit; reduces by 1d10+2; full stop sends it back", () => {
  let reduced = false, redirected = false;
  for (let seed = 1; seed < 200 && !(reduced && redirected); seed++) { const s = st("relay_droid", seed); s.order = ["droid", "aero"]; s.turn = 0;
    const r = play(s, "droid", [{ pid: "npc_blaster", target: "aero" }], (p) => p.kind === "ranged_energy_hit_on_me" ? "lightsaber_deflect" : p.kind === "deflect_redirect" ? p.options[0] : null);
    const d = r.log.find((l) => l.ev === "deflect"); if (d) { reduced = true; assert(d.reduced >= 1); if (r.log.some((l) => l.ev === "redirect")) redirected = true; } }
  assert(reduced && redirected, "reduction and redirect both observed");
  const s = st("relay_droid"); s.actors.aero.weapon.ignited = false; s.order = ["droid", "aero"]; s.turn = 0;
  const r = play(s, "droid", [{ pid: "npc_blaster", target: "aero" }], () => "lightsaber_deflect"); assert(!r.log.some((l) => l.ev === "deflect"), "no deflect with an unlit blade");
});
t("Sentinel Balance is on the sheet but inert here (nothing forces Aero to save) and says so", () => { assert(C.profiles.sentinel_balance.inert_note); assert(C.profiles.sentinel_balance.trigger === "failed_dex_or_cha_save"); });
// ---- combo truth ----
t("Blade and Body is NOT predicted when Aero is disarmed and attacking unarmed (Unarmed Flow instead)", () => {
  const s = st("duelist", 1, 5); s.actors.aero.dropped = JSON.parse(JSON.stringify(s.actors.aero.weapon)); s.actors.aero.weapon.held = false; s.actors.aero.weapon.ignited = false;
  const sy = E.synergies(s, "aero", [{ pid: "unarmed_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }]).map((x) => x.id);
  assert(!sy.includes("blade_and_body"), sy.join()); assert(sy.includes("unarmed_flow"), sy.join());
  const lit = st("duelist", 1, 5); assert(E.synergies(lit, "aero", [{ pid: "saber_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }]).map((x) => x.id).includes("blade_and_body"));
  const unlit = st("duelist", 1, 5); unlit.actors.aero.weapon.ignited = false;
  assert(!E.synergies(unlit, "aero", [{ pid: "toggle_blade" }, { pid: "saber_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }]).some((x) => x.legal === false && x.id === "blade_and_body"), "lighting the blade earlier in the plan counts (projected state)");
});
t("predicted vs confirmed: a lost feint means no confirmed Echani Flow Line, a won one confirms it from events", () => {
  let lost = false, won = false;
  for (let seed = 1; seed < 80 && !(lost && won); seed++) { const s = st("duelist", seed, 5); const plan = [{ pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }];
    assert.strictEqual(E.synergies(s, "aero", plan)[0].status, "predicted");
    const r = play(s, "aero", plan); const cc = E.confirmedCombos(r.state, r.log).map((x) => x.id); const fw = r.log.find((l) => l.ev === "contest").win;
    if (fw) { won = true; assert(cc.includes("echani_flow_line"), cc.join()); } else { lost = true; assert(!cc.includes("echani_flow_line"), cc.join()); } }
  assert(lost && won);
});
t("confirmation uses the weapon actually in hand: a disarm mid-turn breaks Blade and Body", () => {
  const log = [{ ev: "attack", attacker: "aero", defender: "ilsa", pid: "saber_strike", main_hand: "empty" }, { ev: "attack", attacker: "aero", defender: "ilsa", pid: "flow_strike", main_hand: "empty" }];
  assert(!E.confirmedCombos(st(), log).some((x) => x.id === "blade_and_body"));
});
// ---- dice authority / roll ownership ----
t("Atomic mode: the engine never invents a die; it asks, with purpose, owner and target/DC", () => {
  const s = E.newState(C, S, "duelist", { atomic: true }); s.dist["aero|ilsa"] = 5;
  const r = E.resolveTurn(s, "aero", [{ pid: "saber_strike", target: "ilsa" }], {});
  assert(r.need_dice && r.need_dice.actor === "aero" && r.need_dice.kind === "attack" && r.need_dice.vs.type === "ac" && r.need_dice.vs.value === 15, JSON.stringify(r.need_dice));
  assert.strictEqual(r.state, s, "the snapshot is returned untouched");
  const s2 = E.acceptDice(s, [{ seq: 0, sides: 20, value: 14 }]); const r2 = E.resolveTurn(s2, "aero", [{ pid: "saber_strike", target: "ilsa" }], {});
  assert(r2.need_dice || r2.paused, "after the d20 it asks again (damage, or Ilsa's parry decision is the GM's)");
});
t("accepted dice are immutable: conflicting, gapped or out-of-range values are refused", () => {
  const s = E.acceptDice(E.newState(C, S, "duelist", { atomic: true }), [{ seq: 0, sides: 20, value: 7 }]);
  assert.throws(() => E.acceptDice(s, [{ seq: 0, sides: 20, value: 8 }]), /TAPE_CONFLICT/);
  assert.throws(() => E.acceptDice(s, [{ seq: 3, sides: 20, value: 8 }]), /TAPE_GAP/);
  assert.throws(() => E.acceptDice(s, [{ seq: 1, sides: 6, value: 9 }]), /OUT_OF_RANGE/);
  assert.doesNotThrow(() => E.acceptDice(s, [{ seq: 0, sides: 20, value: 7 }]), "same die again is a no-op");
});
t("NPC dice belong to the GM: the predator's pounce asks for a GM-owned die", () => {
  const s = E.newState(C, S, "predator", { atomic: true }); const plan = E.npcPlan(s, "stalker"); const r = E.resolveTurn(s, "stalker", plan, {});
  assert(r.need_dice && r.need_dice.actor === "stalker" && S.scenarios.predator.actors.stalker.controller === "npc");
});
t("Soul's combo name is a display-only proposal and leaves facts untouched", () => {
  const N = require("./soul.js"); const s = st("duelist", 3, 5); const r = play(s, "aero", [{ pid: "saber_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }]);
  const before = JSON.stringify(r.log); const F = N.facts(r.log, {}); const cc = E.confirmedCombos(r.state, r.log); assert(cc.length);
  const nm = N.proposeComboName(cc[0], F); assert(nm.name && nm.mechanical === false); assert.strictEqual(JSON.stringify(r.log), before);
  assert(!C.synergies.some((x) => x.name === nm.name), "a Soul name never enters the synergy registry");
});
t("predictions use the same range rule as the engine (blaster beyond 40 ft = disadvantage)", () => {
  const Pr = require("./predict.js"); const s = st("relay_droid"); s.actors.aero.sidearm.held = true; s.dist["aero|droid"] = 60;
  const a = Pr.analyzePlan(s, "aero", [{ pid: "blaster_shot", target: "droid" }]).steps[0]; assert(a.dis.includes("long range")); assert(Math.abs(a.hit - Pr.attackOdds(5, 13, "disadvantage").hit) < 1e-12);
});
t("Deflect redirect: the PLAYER picks one visible creature within 30 ft, or declines (sheet; GEP-001 §11.8)", () => {
  let offered = null, declinedOk = false;
  for (let seed = 1; seed < 300 && !(offered && declinedOk); seed++) {
    const s = st("relay_droid", seed); s.order = ["droid", "aero"]; s.turn = 0;
    const r = play(s, "droid", [{ pid: "npc_blaster", target: "aero" }], (p) => { if (p.kind === "deflect_redirect") { offered = p; return null; } return p.kind === "ranged_energy_hit_on_me" ? "lightsaber_deflect" : null; });
    if (offered && r.log.some((l) => l.ev === "redirect_declined")) declinedOk = !r.log.some((l) => l.ev === "redirect");
  }
  assert(offered, "a full stop offered the redirect choice"); assert.deepStrictEqual(offered.options, ["droid"], "only visible creatures within 30 ft (not Aero himself)");
  assert(offered.actor === "aero" && offered.context.shooter === "droid"); assert(declinedOk, "declining sends nothing back");
  const far = st("relay_droid", 1); far.dist["aero|droid"] = 45; far.order = ["droid", "aero"]; far.turn = 0; let off2 = null;
  for (let seed = 1; seed < 300 && !off2; seed++) { const x = st("relay_droid", seed); x.dist["aero|droid"] = 45; x.order = ["droid", "aero"]; x.turn = 0; play(x, "droid", [{ pid: "npc_blaster", target: "aero" }], (p) => { if (p.kind === "deflect_redirect") off2 = p; return p.kind === "ranged_energy_hit_on_me" ? "lightsaber_deflect" : null; }); }
  assert(!off2, "a shooter 45 ft away cannot be chosen; with no one in 30 ft there is no redirect offer");
});
t("every dice request carries its identity: actor, purpose, step, rules version, target", () => {
  const s = E.newState(C, S, "duelist", { atomic: true }); s.dist["aero|ilsa"] = 5; const n = E.resolveTurn(s, "aero", [{ pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }], {}).need_dice;
  assert(n.actor === "aero" && n.step === 0 && n.rules === "cc-sandbox-0.5" && n.target === "ilsa" && /Feint/.test(n.purpose), JSON.stringify(n));
});
setTimeout(() => { console.log(fail ? fail + " FAILED, " + pass + " passed" : "all " + pass + " passed"); process.exit(fail ? 1 : 0); }, 10);
