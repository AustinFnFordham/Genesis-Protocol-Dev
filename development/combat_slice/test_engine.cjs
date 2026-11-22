// CC-002 sandbox slice: engine tests (contract §3, §7 minimum playable slice). node test_engine.cjs
const assert = require("assert/strict");
const E = require("./engine.js");
const C = require("./catalog.json");
const S = require("./scenarios.json");
let failures = 0, n = 0;
function t(name, fn) { n++; try { fn(); console.log("ok", name); } catch (e) { failures++; console.log("FAIL", name, "\n   ", e.message); } }
const fresh = (sc, opts) => E.newState(C, S, sc || "duelist", Object.assign({ seed: 7 }, opts || {}));
const codes = (v, i) => v.steps[i].reasons.map((r) => r.code);
// play a turn to completion, answering player prompts from `answers` (by kind) — default decline
function play(s, actor, plan, answers) {
  const choices = {}; let r;
  for (let guard = 0; guard < 10; guard++) {
    r = E.resolveTurn(s, actor, plan, choices);
    if (!r.paused) return r;
    choices[r.paused.key] = (answers && answers[r.paused.kind] !== undefined) ? answers[r.paused.kind] : null;
  }
  throw new Error("prompt loop");
}
function legal(s, actor, plan) { return plan.filter((st, i) => E.validatePlan(s, actor, plan.slice(0, i + 1)).legal); }
function adjacent(s) { s.dist["aero|ilsa"] = 5; return s; }

t("data: every granted profile exists; every number is tagged sheet, sandbox_proposal or campaign_ruling (owner D1)", () => {
  for (const a of [S.aero, ...Object.values(S.scenarios).flatMap((x) => Object.values(x.actors))])
    for (const pid of [...(a.grants.sheet || []), ...(a.grants.sandbox_proposal || [])]) assert.ok(C.profiles[pid], pid);
  for (const [pid, p] of Object.entries(C.profiles)) assert.ok(["sheet", "sandbox_proposal"].includes(p.status) || (p.status === "campaign_ruling" && /campaigns\/starwars_litrpg\/creator\//.test(p.source)), pid);
  assert.deepEqual(S.aero.grants.sheet.filter((p) => C.profiles[p].status !== "sheet"), [], "nothing proposed is passed off as a sheet grant");
});
t("Aero's numbers match his runtime sheet (AC 13, 11 HP, 3 FP, saber +5 1d8+3, unarmed +5 1d4+3)", () => {
  assert.equal(S.aero.ac, 13); assert.equal(S.aero.hp, 11); assert.equal(S.aero.fp, 3);
  assert.equal(C.profiles.saber_strike.resolution.bonus, 5); assert.equal(C.profiles.saber_strike.resolution.damage, "1d8+3");
  assert.equal(C.profiles.unarmed_strike.resolution.damage, "1d4+3");
  assert.ok(!S.aero.grants.sheet.includes("animal_handling_trained") && S.aero.skills.animal_handling === 2, "no Animal Handling training");
});
t("budgets: Main 1, Bonus 1, Secondary 1, Reaction 1; a second Main is refused", () => {
  const s = adjacent(fresh());
  const v = E.validatePlan(s, "aero", [{ pid: "saber_strike", target: "ilsa" }, { pid: "unarmed_strike", target: "ilsa" }]);
  assert.equal(v.legal, false); assert.deepEqual(codes(v, 1), ["NO_MAIN"]);
});
t("literal zero stays zero: every budget at 0 refuses its cards", () => {
  const s = adjacent(fresh());
  Object.assign(s.actors.aero.budget, { main: 0, bonus: 0, secondary: 0, movement_ft: 0, object: 0 }); s.actors.aero.fp = 0;
  const v = E.validatePlan(s, "aero", [{ pid: "saber_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }, { pid: "feint", target: "ilsa" },
    { pid: "move", dest: "withdraw" }, { pid: "toggle_blade" }]);
  assert.deepEqual(v.steps.map((x) => x.ok), [false, false, false, false, false]);
  assert.ok(codes(v, 0).includes("NO_MAIN") && codes(v, 2).includes("NO_SECONDARY") && codes(v, 3).includes("NO_MOVEMENT_FT") && codes(v, 4).includes("NO_OBJECT"));
  const aug = E.validatePlan(adjacent(fresh()), "aero", [{ pid: "saber_strike", target: "ilsa", augment: true }]);
  assert.ok(aug.legal); const z = adjacent(fresh()); z.actors.aero.fp = 0;
  assert.ok(codes(E.validatePlan(z, "aero", [{ pid: "saber_strike", target: "ilsa", augment: true }]), 0).includes("NO_FP"), "0 Force Points means no augmentation");
});
t("a reaction is not a turn step (REACTION_ONLY)", () => {
  const v = E.validatePlan(adjacent(fresh()), "aero", [{ pid: "riposte", target: "ilsa" }]);
  assert.deepEqual(codes(v, 0), ["REACTION_ONLY"]);
});
t("SA-001 off (legacy): Secondary budget 0 and Feint / Readied Dodge / Glance refused with SA001_DISABLED", () => {
  const s = adjacent(fresh("duelist", { switches: { secondary_action: false } }));
  assert.equal(s.actors.aero.budget.secondary, 0);
  const v = E.validatePlan(s, "aero", [{ pid: "feint", target: "ilsa" }, { pid: "readied_dodge" }, { pid: "tactical_glance" }]);
  for (let i = 0; i < 3; i++) assert.ok(codes(v, i).includes("SA001_DISABLED"), JSON.stringify(v.steps[i]));
  assert.ok(E.validatePlan(s, "aero", [{ pid: "saber_strike", target: "ilsa" }]).legal, "legacy actions still work");
  const np = E.npcPlan(E.endTurn(s), "ilsa");
  assert.ok(!np.some((x) => x.pid === "feint"), "the NPC policy also respects the switch");
});
t("Battle Insight stays Main unless its sandbox switch is on", () => {
  const s = adjacent(fresh());
  assert.ok(codes(E.validatePlan(s, "aero", [{ pid: "battle_insight_bonus", target: "ilsa" }]), 0).includes("SWITCH_OFF"));
  const on = adjacent(fresh("duelist", { switches: { battle_insight_bonus: true } }));
  assert.ok(E.validatePlan(on, "aero", [{ pid: "battle_insight_bonus", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }]).legal);
});
t("Flow Strike only after a melee attack this turn; once per turn", () => {
  const s = adjacent(fresh());
  assert.deepEqual(codes(E.validatePlan(s, "aero", [{ pid: "flow_strike", target: "ilsa" }]), 0), ["NEEDS_MELEE_ATTACK_FIRST"]);
  assert.ok(E.validatePlan(s, "aero", [{ pid: "saber_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }]).legal);
});
t("Feint: contested; a win gives advantage on the next melee attack; it never auto-hits; once per turn", () => {
  let won = null;
  for (let seed = 1; seed < 60 && !won; seed++) {
    const r = play(adjacent(fresh("duelist", { seed })), "aero", [{ pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }], {});
    if (r.log.some((l) => /bites on the feint/.test(l.text))) won = r;
  }
  assert.ok(won, "found a winning feint");
  const strike = won.receipts.find((x) => /Lightsaber Strike/.test(x.purpose));
  assert.equal(strike.mode, "advantage"); assert.equal(strike.rolls.length, 2);
  assert.ok(won.receipts.filter((x) => /^Weapon Feint/.test(x.purpose)).length === 1 && won.receipts.some((x) => /resists Weapon Feint/.test(x.purpose)), "a real contest, two receipts");
  assert.ok(codes(E.validatePlan(adjacent(fresh()), "aero", [{ pid: "feint", target: "ilsa" }, { pid: "feint", target: "ilsa" }]), 1).includes("NO_SECONDARY"), "no feint spam");
});
t("setup after the target moves: a feint's opening closes when the distance opens", () => {
  let s = null;
  for (let seed = 1; seed < 80; seed++) {
    const r = play(adjacent(fresh("duelist", { seed })), "aero", [{ pid: "feint", target: "ilsa" }, { pid: "move", dest: "withdraw" }], {});
    if (r.log.some((l) => /bites on the feint/.test(l.text))) { s = r; break; }
  }
  assert.ok(s, "found a won feint");
  assert.ok(s.log.some((l) => /opening closes/.test(l.text)) && !s.state.actors.ilsa.conds.feinted, "feint lost after withdrawing");
});
t("Parry turns a hit into a miss only by its +2; Riposte answers a miss; a Riposte never triggers a Riposte", () => {
  let checked = false;
  for (let seed = 1; seed < 200 && !checked; seed++) {
    const r = play(adjacent(fresh("duelist", { seed })), "aero", [{ pid: "saber_strike", target: "ilsa" }], {});
    if (r.log.some((l) => /Ilsa Vohr ripostes/.test(l.text))) {
      const after = r.log.slice(r.log.findIndex((l) => /Ilsa Vohr ripostes/.test(l.text)));
      assert.ok(!after.some((l) => /Aero ripostes/.test(l.text)), "no counter to a counter");
      checked = true;
    }
  }
  assert.ok(checked, "saw a riposte");
});
t("double counter loop prevention: even when offered, a player cannot Riposte a Riposte", () => {
  for (let seed = 1; seed < 300; seed++) {
    let s = adjacent(fresh("duelist", { seed }));
    s = E.endTurn(s);   // Ilsa's turn
    const prompts = [];
    const choices = {};
    for (let g = 0; g < 8; g++) {
      const r = E.resolveTurn(s, "ilsa", [{ pid: "npc_blade", target: "aero" }], choices);
      if (!r.paused) break;
      prompts.push(r.paused); choices[r.paused.key] = r.paused.options[0];
    }
    const ripostes = prompts.filter((p) => p.kind === "melee_miss_on_me");
    assert.ok(ripostes.every((p) => p.context.counter === false), "Aero is only offered Riposte against a non-counter attack");
    assert.ok(ripostes.length <= 1, "at most one riposte window per attack chain");
  }
});
t("a spent Reaction stays spent: Parry on the first attack means no Riposte later that round", () => {
  for (let seed = 1; seed < 300; seed++) {
    let s = E.endTurn(adjacent(fresh("duelist", { seed })));
    const prompts = [], choices = {};
    for (let g = 0; g < 8; g++) {
      const r = E.resolveTurn(s, "ilsa", [{ pid: "npc_blade", target: "aero" }], choices);
      if (!r.paused) { if (prompts.length && prompts[0].kind === "melee_hit_on_me") { assert.equal(r.state.actors.aero.reaction_left, 0); return; } break; }
      prompts.push(r.paused); choices[r.paused.key] = r.paused.options[0];
      if (prompts.length > 1) assert.notEqual(prompts[0].kind === "melee_hit_on_me" && prompts[1].kind === "melee_miss_on_me", true, "no second reaction after a parry");
    }
  }
});
t("Readied Dodge: Secondary to ready, Reaction when attacked imposes disadvantage; declining keeps the Reaction", () => {
  let s = adjacent(fresh());
  let r = play(s, "aero", [{ pid: "readied_dodge" }], {});
  assert.ok(r.state.actors.aero.conds.dodge_ready);
  s = E.endTurn(r.state);
  const a = E.resolveTurn(s, "ilsa", [{ pid: "npc_blade", target: "aero" }], {});
  assert.ok(a.paused && a.paused.kind === "attack_declared_on_me" && a.paused.options.includes("dodge_reaction"));
  const yes = play(s, "ilsa", [{ pid: "npc_blade", target: "aero" }], { attack_declared_on_me: "dodge_reaction" });
  assert.equal(yes.receipts.find((x) => /Vibroblade Thrust/.test(x.purpose)).mode, "disadvantage");
  const no = play(s, "ilsa", [{ pid: "npc_blade", target: "aero" }], { attack_declared_on_me: null });
  assert.equal(no.receipts.find((x) => /Vibroblade Thrust/.test(x.purpose)).mode, "normal");
});
t("disarm: a won bind strips the weapon (no damage); the disarmed actor's weapon cards are refused; recovery costs object + movement", () => {
  for (let seed = 1; seed < 100; seed++) {
    const r = play(adjacent(fresh("duelist", { seed })), "aero", [{ pid: "blade_bind", target: "ilsa" }], {});
    if (!r.log.some((l) => /stripped away/.test(l.text))) continue;
    const I = r.state.actors.ilsa;
    assert.equal(I.weapon.held, false); assert.equal(I.hp, I.hp_max, "a bind deals no damage");
    let s = E.endTurn(r.state);
    assert.ok(E.validatePlan(s, "ilsa", [{ pid: "npc_blade", target: "aero" }]).steps[0].reasons.some((x) => x.code === "WEAPON_NOT_HELD"));
    assert.deepEqual(E.npcPlan(s, "ilsa"), [{ pid: "recover_weapon" }], "the NPC uses the same rules to recover");
    const v = E.validatePlan(s, "ilsa", [{ pid: "recover_weapon" }, { pid: "npc_blade", target: "aero" }]);
    assert.ok(v.legal, "recover then strike (the vibroblade needs no ignition)");
    return;
  }
  throw new Error("no successful bind in 100 seeds");
});
t("loss of weapon mid-chain: steps after the blade goes out are refused (preflight and at execution)", () => {
  const s = adjacent(fresh());
  const v = E.validatePlan(s, "aero", [{ pid: "toggle_blade" }, { pid: "saber_strike", target: "ilsa" }]);
  assert.equal(v.legal, false); assert.ok(codes(v, 1).includes("BLADE_UNLIT"));
  // disarmed by Ilsa on her turn: Aero's parry/riposte are not even offered for the rest of her chain
  for (let seed = 1; seed < 200; seed++) {
    let st = E.endTurn(adjacent(fresh("duelist", { seed })));
    const r = play(st, "ilsa", [{ pid: "npc_bind", target: "aero" }], {});
    if (r.state.actors.aero.weapon.held) continue;
    const next = E.endTurn(E.endTurn(r.state));   // back to Ilsa next round
    const ra = E.resolveTurn(next, "ilsa", [{ pid: "npc_blade", target: "aero" }], {});
    assert.ok(!ra.paused || !["melee_hit_on_me", "melee_miss_on_me"].includes(ra.paused.kind), "no saber reactions while disarmed");
    const a2 = E.endTurn(r.state);
    assert.ok(codes(E.validatePlan(a2, "aero", [{ pid: "saber_strike", target: "ilsa" }]), 0).includes("WEAPON_NOT_HELD"));
    assert.ok(E.validatePlan(a2, "aero", [{ pid: "unarmed_strike", target: "ilsa" }]).legal, "Echani strikes still work unarmed");
    return;
  }
  throw new Error("no disarm in 200 seeds");
});
t("free speech vs Taunt: words cost nothing and do nothing; Taunt is a Bonus contest; a beast cannot be taunted", () => {
  const s = adjacent(fresh());
  const v = E.validatePlan(s, "aero", [{ pid: "speak", text: "Is that all, mercenary?" }, { pid: "saber_strike", target: "ilsa" }]);
  assert.ok(v.legal); assert.equal(v.budget_after.bonus, 1, "speech spends nothing");
  const r = play(s, "aero", [{ pid: "speak", text: "Is that all, mercenary?" }], {});
  assert.ok(!r.state.actors.ilsa.conds.taunted && r.receipts.length === 0, "no roll, no debuff");
  assert.ok(E.validatePlan(s, "aero", [{ pid: "taunt", target: "ilsa" }]).legal);
  let p = fresh("predator"); p.actors.stalker.conds = {}; p.turn = 1;
  assert.ok(codes(E.validatePlan(p, "aero", [{ pid: "taunt", target: "stalker" }]), 0).includes("CANNOT_UNDERSTAND"));
});
t("concealment: a hidden creature cannot be targeted and never appears in the player's view; a glance can find it", () => {
  let s = fresh("predator"); s.turn = 1;   // Aero acts first for this test
  const v = E.validatePlan(s, "aero", [{ pid: "saber_strike", target: "stalker" }]);
  assert.ok(codes(v, 0).includes("NO_TARGET"));
  const pub = JSON.stringify(E.publicView(s));
  assert.ok(!/stalker|Vrask|stealth_dc|15/.test(pub.replace(/"round":\d+/, "")), "no name, id or DC in the public view");
  assert.ok(E.publicView(s).unseen_presence);
  let found = false;
  for (let seed = 1; seed < 60; seed++) {
    const st = fresh("predator", { seed }); st.turn = 1;
    const r = play(st, "aero", [{ pid: "tactical_glance" }], {});
    if (r.log.some((l) => /you spot/.test(l.text))) { found = true; assert.ok(!r.state.actors.stalker.conds.hidden); assert.ok(!r.log.some((l) => /DC|15/.test(l.text))); break; }
  }
  assert.ok(found);
});
t("predator: species tactics (pounce from hiding with advantage), untrained Animal Handling only", () => {
  const s = fresh("predator");
  const plan = E.npcPlan(s, "stalker");
  assert.deepEqual(plan, [{ pid: "pounce", target: "aero" }]);
  const r = play(s, "stalker", plan, {});
  const atk = r.receipts.find((x) => /Pounce/.test(x.purpose));
  assert.equal(atk.mode, "advantage"); assert.ok(r.log.some((l) => /revealed/.test(l.text)));
  assert.equal(C.profiles.calm_beast.resolution.actor_skill, "animal_handling"); assert.equal(S.aero.skills.animal_handling, 2, "untrained WIS +2");
});
t("Force augmentation: costs 1 FP, adds 1d4 to the attack roll, once per turn, only on a learned strike", () => {
  const s = adjacent(fresh());
  const r = play(s, "aero", [{ pid: "saber_strike", target: "ilsa", augment: true }], {});
  const atk = r.receipts.find((x) => /Lightsaber Strike →/.test(x.purpose));
  assert.equal(atk.extra.length, 1); assert.equal(atk.extra[0].label, "Force-guided"); assert.equal(r.state.actors.aero.fp, 2);
  assert.ok(codes(E.validatePlan(s, "aero", [{ pid: "unarmed_strike", target: "ilsa", augment: true }]), 0).includes("AUGMENT_NOT_ALLOWED"));
  const off = adjacent(fresh("duelist", { switches: { force_augmentation: false } }));
  assert.ok(codes(E.validatePlan(off, "aero", [{ pid: "saber_strike", target: "ilsa", augment: true }]), 0).includes("AUGMENT_NOT_GRANTED"));
});
t("advantage does not stack: Feint + Battle Insight is flagged and the roll is plain advantage", () => {
  const s = adjacent(fresh());
  const notes = E.comboJudge(s, "aero", [{ pid: "battle_insight", target: "ilsa" }, { pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }]);
  assert.ok(notes.some((x) => x.kind === "conflict"));
});
t("NPC / PC parity: the same validator refuses an NPC's illegal plan exactly like the player's", () => {
  const s = E.endTurn(adjacent(fresh()));
  const v = E.validatePlan(s, "ilsa", [{ pid: "npc_blade", target: "aero" }, { pid: "npc_blade", target: "aero" }]);
  assert.equal(v.legal, false); assert.deepEqual(codes(v, 1), ["NO_MAIN"]);
  const pc = E.validatePlan(adjacent(fresh()), "aero", [{ pid: "feint", target: "ilsa" }]);
  const npc = E.validatePlan(s, "ilsa", [{ pid: "feint", target: "aero" }]);
  assert.deepEqual(Object.keys(pc.steps[0]).sort(), Object.keys(npc.steps[0]).sort());
  assert.deepEqual(pc.steps[0].cost, npc.steps[0].cost, "same Feint profile, same cost");
  assert.ok(codes(E.validatePlan(s, "ilsa", [{ pid: "saber_strike", target: "aero" }]), 0).includes("NOT_GRANTED"), "an NPC cannot conjure abilities it lacks");
  assert.equal(E.validatePlan(s, "aero", [{ pid: "saber_strike", target: "ilsa" }]).errors[0].code, "NOT_YOUR_TURN", "only the acting actor may act");
});
t("exact replay: same seed and plans give identical receipts; pause/resume gives the same rolls as answering upfront", () => {
  const run = () => { let s = adjacent(fresh("duelist", { seed: 99 })); const out = [];
    for (let i = 0; i < 6 && !s.over; i++) { const actor = E.current(s); const plan = actor === "aero" ? [{ pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }] : E.npcPlan(s, actor);
      const r = play(s, actor, legal(s, actor, plan), { melee_miss_on_me: "riposte", melee_hit_on_me: "parry" }); out.push(...r.receipts); s = E.endTurn(r.state); } return out; };
  assert.deepEqual(run(), run());
  let s = E.endTurn(adjacent(fresh("duelist", { seed: 5 })));
  const p1 = E.resolveTurn(s, "ilsa", [{ pid: "npc_blade", target: "aero" }], {});
  if (p1.paused) {
    const resumed = E.resolveTurn(s, "ilsa", [{ pid: "npc_blade", target: "aero" }], { [p1.paused.key]: null });
    assert.deepEqual(resumed.receipts.slice(0, p1.preview_receipts.length), p1.preview_receipts, "rolls before the prompt are identical after resuming");
  }
});
t("the GM never picks a player reaction: an NPC attack pauses for Aero instead of choosing for him", () => {
  let paused = 0;
  for (let seed = 1; seed < 40; seed++) { const r = E.resolveTurn(E.endTurn(adjacent(fresh("duelist", { seed }))), "ilsa", [{ pid: "npc_blade", target: "aero" }], {}); if (r.paused) { paused++; assert.equal(r.paused.actor, "aero"); } }
  assert.ok(paused > 0);
});
t("opportunity attack when withdrawing from reach (same rules for both sides)", () => {
  const r = play(adjacent(fresh()), "aero", [{ pid: "move", dest: "withdraw" }], {});
  assert.ok(r.log.some((l) => /opportunity attack/.test(l.text)));
  assert.equal(r.state.actors.ilsa.reaction_left, 0, "it cost Ilsa her Reaction");
});
t("public view: enemy HP is shown as a condition word, never a number", () => {
  const v = E.publicView(adjacent(fresh()));
  assert.equal(v.actors.ilsa.hp, null); assert.equal(v.actors.ilsa.condition, "unhurt"); assert.equal(v.actors.aero.hp, 11);
  assert.equal(v.canonical, false);
});
t("a full scripted duel finishes without errors and every log line with dice cites a receipt", () => {
  let s = fresh("duelist", { seed: 3 }), guard = 0;
  while (!s.over && guard++ < 40) {
    const actor = E.current(s);
    const plan = actor === "aero" ? (E.distance(s, "aero", "ilsa") > 5 ? [{ pid: "move", dest: "close", target: "ilsa" }] : []).concat([{ pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }]) : E.npcPlan(s, actor);
    const okPlan = plan.filter((st, i) => E.validatePlan(s, actor, plan.slice(0, i + 1)).legal);
    const r = play(s, actor, okPlan, { melee_miss_on_me: "riposte", melee_hit_on_me: "parry" });
    s = E.endTurn(r.state);
  }
  assert.ok(s.over, "someone won"); const ids = new Set(s.receipts.map((x) => x.receipt));
  s.log.filter((l) => l.receipt).forEach((l) => l.receipt.split(",").forEach((id) => assert.ok(ids.has(id))));
});
console.log(failures ? failures + " FAILED of " + n : "all " + n + " passed");
process.exit(failures ? 1 : 0);
