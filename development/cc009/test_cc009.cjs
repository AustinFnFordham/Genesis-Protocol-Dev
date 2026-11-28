// CC-009 acceptance matrix (12 scenarios) for Combat Turn Builder v2 over the live turn contract and the Atomic combat slice.
// Uses read-only copies of committed Hask Meadow r2 contexts; never writes a campaign, ledger or dice file.
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto"), cp = require("child_process");
const REPO = path.join(__dirname, "../.."), P = require("./turn_plan_v2.js"), T = require(path.join(REPO, "campaigns/starwars_litrpg/ui/turn_contract.js"));
const E = require(path.join(REPO, "development/combat_slice/engine.js")), C = require(path.join(REPO, "development/combat_slice/catalog.json")), S = require(path.join(REPO, "development/combat_slice/scenarios.json"));
const FX = require("./fixtures/hask_r2_round9_10.json"), R1 = require(path.join(REPO, "campaigns/starwars_litrpg/ui/fixtures/hask_round1.json"));
let fails = 0, n = 0; const ok = (c, m, x) => { n++; console.log((c ? "ok " : "FAIL ") + m + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 500))); if (!c) fails++; };
const clone = (x) => JSON.parse(JSON.stringify(x)), ctxOf = (k) => clone(FX.contexts[k].ctx), codes = (v) => v.errors.map((e) => e.code);
const sha = (p) => crypto.createHash("sha256").update(fs.readFileSync(path.join(REPO, p))).digest("hex");
const PROTECT = ["campaigns/starwars_litrpg/runs/hask_meadow_r2/records/events.jsonl", "campaigns/starwars_litrpg/runs/hask_meadow_r2/records/roll_log.jsonl",
  "campaigns/starwars_litrpg/runs/hask_meadow_r2/hidden/events.jsonl", "campaigns/starwars_litrpg/runs/hask_meadow_r2/hidden/dice_state.json", "campaigns/starwars_litrpg/runs/sandbox/records/events.jsonl"];
const before = Object.fromEntries(PROTECT.filter((p) => fs.existsSync(path.join(REPO, p))).map((p) => [p, sha(p)]));
ok(FX.source.sha256 === sha(FX.source.path), "fixtures are exact copies of the committed Hask Meadow record (source sha256 unchanged)");
const plan = (ctx, acts, extra) => acts.reduce((p, a) => P.add(p, a), P.newPlan(ctx, extra));

// 1. Spent object interaction, action and bonus action remain (round 9 after the stop, evt_1385)
{ const c = ctxOf("round9_after_stop");
  const v = P.evaluate(plan(c, [{ slot: "main", capability: { option: "look_up_floor" } }]), c);
  ok(c.budget.object_interaction === 0 && c.budget.action === 1 && c.budget.bonus_action === 1 && v.legal && v.used.action === 1 && v.used.object_interaction === 0, "1. OI spent: the action is still available and legal", v.errors);
  const w = P.evaluate(plan(c, [{ slot: "object", capability: { option: "release_blaster" } }, { slot: "object", capability: { option: "take_lantern" } }]), c);
  ok(w.used.action >= 1 && !codes(w).includes("RESOURCE"), "1b. a further object handling is billed to the action, visibly, not refused for a missing OI", w.used); }
// 2. Two-handed activity conflicts with occupied hands (round 10: lantern left, hilt right; the rake needs two hands)
{ const c = ctxOf("round10_start"), v = P.evaluate(plan(c, [{ slot: "object", capability: { option: "pick_up_rake" } }]), c);
  ok(!v.legal && codes(v).some((x) => /HANDS/.test(x)) && v.layers[0].authorization.verdict === "blocked", "2. two-handed pickup with both hands full is blocked with a hands reason", codes(v));
  const f = P.evaluate(plan(c, [{ slot: "object", capability: { option: "set_lantern_down" } }, { slot: "object", capability: { option: "clip_hilt" } }, { slot: "object", capability: { option: "pick_up_rake" } }]), c);
  ok(!codes(f).some((x) => /HANDS/.test(x)), "2b. freeing both hands first, in order, clears the hands conflict (any remaining issue is budget, not hands)", codes(f)); }
// 3. A conditional pickup waits for its prerequisite
{ const c = ctxOf("round9_start");
  const p = plan(c, [{ id: "sig", slot: "speech", speech: { text: "(to Wick) Lantern to me." }, target: { kind: "ally", id: "wick" } },
                     { id: "take", slot: "free", intent: { text: "Take the lantern from Wick" }, target: { kind: "ally", id: "wick" }, condition: { text: "if Wick holds it out" }, after: ["sig"] }]);
  const v = P.evaluate(p, c), L = v.layers.find((x) => x.id === "take");
  ok(v.legal && L.authorization.verdict === "waits_on_condition" && v.contract.halts.length === 1, "3. the conditional pickup is accepted as waiting on its condition, not executed", { L, h: v.contract.halts });
  const bad = P.evaluate(P.move(p, "take", 0), c); ok(codes(bad).includes("DEPENDENCY_ORDER"), "3b. reordering it before what it depends on is rejected with an explanation"); }
// 4. A compound declaration executes in the intended order (the real round-9 declaration, evt_1375)
{ const c = ctxOf("round9_start"), d = clone(FX.declarations.round9_first.declaration), v = T.validate(d, c);
  const ids = (d.steps || T.normalize(d, c).steps).map((s) => s.id), tr = v.trace.map((t) => t.step_id);
  ok(JSON.stringify(tr) === JSON.stringify(ids.slice(0, tr.length)) && tr.length >= 3, "4. the compound declaration is walked in the player's order", { ids, tr });
  const p = plan(c, [{ id: "x1", slot: "speech", speech: { text: "Breathe." } }, { id: "x2", slot: "main", capability: { option: "look_up_floor" } }, { id: "x3", slot: "movement", capability: { option: "hold" } }]);
  ok(JSON.stringify(P.toDeclaration(p, c).steps.map((s) => s.id)) === '["x1","x2","x3"]', "4b. v2 preserves activity order into the live declaration"); }
// 5. An interrupted action preserves unresolved work (evt_1385 pending: s4 interrupted, s5 unattempted)
{ const c = ctxOf("round9_after_stop"), pend = c.pending_steps;
  ok(pend.map((s) => s.id + ":" + s.status).join() === "s4:interrupted,s5:unattempted" && pend.every((s) => T.CONTINUABLE.includes(s.status)), "5. the interrupted lantern step and the unattempted instruction are kept and continuable", pend);
  const p = plan(c, pend.map((s) => ({ id: s.id, slot: s.type === "speech" ? "speech" : "free", speech: s.type === "speech" ? { text: s.text } : undefined, intent: s.type !== "speech" ? { text: s.text } : undefined, pending: true, status: s.status })));
  const v = P.evaluate(p, c); ok(v.layers.length === 2 && !codes(v).includes("NOT_CONTINUABLE"), "5b. the pending work can be continued from the plan", codes(v)); }
// 6. A submitted turn continues while legal activity remains (the real round-9 continuation, evt_1386)
{ const c = ctxOf("round9_after_stop"), v = T.validate(FX.declarations.round9_continuation.declaration, c);
  ok(v.legal && v.ends_turn === false && v.info.some((i) => i.code === "TURN_CONTINUES"), "6. the round-9 continuation no longer ends the turn (the record ended it; see evidence/hask_replay.json)", v.info);
  const p = plan(c, [{ slot: "speech", speech: { text: "Steady." } }]); ok(P.evaluate(p, c).ends_turn === false && P.evaluate(Object.assign(clone(p), { end_turn: true }), c).ends_turn === true, "6b. only the player's explicit end_turn ends a turn with budget left"); }
// 7. Free speech does not consume nonexistent action budgets
{ const c = ctxOf("round10_start"); c.budget = { action: 0, bonus_action: 0, reaction: 0, movement_ft: 0, object_interaction: 0 };
  const v = P.evaluate(plan(c, [{ slot: "speech", speech: { text: "Easy, Wick. Breathe." }, target: { kind: "ally", id: "wick" } }]), c);
  ok(v.legal && Object.values(v.used).every((x) => x === 0) && P.narrativeAvailable(c), "7. with every budget at zero, brief speech is still legal and spends nothing", { used: v.used, e: codes(v) });
  ok(/adjudicated/.test(v.layers[0].authorization.speech_effect), "7b. speech carries no automatic mechanical effect (effects on others are adjudicated)");
  const ex = P.evaluate(plan(c, [{ slot: "speech", speech: { text: "a long negotiation", extended: true } }]), c); ok(!ex.legal, "7c. an extended exchange still needs the action (none left) — speech is free, not unlimited", codes(ex)); }
// 8. A reaction is available only when a legal trigger occurs (round-1 context lists three reactions with triggers)
{ const c = clone(R1);
  const dv = P.evaluate(plan(c, [{ slot: "reaction", capability: { option: "deflect" }, trigger: "a ranged attack hits you" }]), c);
  ok(dv.legal && dv.layers[0].authorization.verdict === "declared_intent" && dv.used.reaction === 0, "8. on Aero's turn a reaction is only a declared intent; nothing is spent", { v: dv.layers[0], u: dv.used });
  c.reaction_prompt = { trigger: "A blaster bolt is hitting you", options: ["deflect"] };
  const wrong = T.validate({ actor: "aero", source: "composer", freeform: "", speech: null, actions: [], bonus_actions: [], movement: null, objects: [], reactions: ["opportunity_attack"], unmapped: [] }, c);
  const right = T.validate({ actor: "aero", source: "composer", freeform: "", speech: null, actions: [], bonus_actions: [], movement: null, objects: [], reactions: ["deflect"], unmapped: [] }, c);
  ok(!wrong.legal && wrong.errors.some((e) => e.code === "REACTION_NOT_OFFERED") && right.legal, "8b. when the trigger occurs only the offered reaction is legal", codes(wrong));
  const s0 = E.newState(C, S, "duelist", { seed: 7 }), rv = E.validatePlan(s0, "aero", [{ pid: "saber_riposte", target: "ilsa" }]);
  ok(!rv.legal, "8c. Atomic: a reaction profile cannot be declared as a turn step", rv.steps && rv.steps[0] && rv.steps[0].reasons); }
// 9. An NPC action updates the correct actor's state (Atomic engine)
{ let s = E.endTurn(E.newState(C, S, "duelist", { seed: 7 })); const aeroUsed = JSON.stringify(s.actors.aero.used), ilsaUsed0 = JSON.stringify(s.actors.ilsa.used);
  const pl = E.npcPlan(s, "ilsa"); let r = E.resolveTurn(s, "ilsa", pl, {}); for (let g = 0; g < 6 && r.paused; g++) { const ch = {}; ch[r.paused.key] = null; r = E.resolveTurn(s, "ilsa", pl, ch); }
  const t = r.state; ok(JSON.stringify(t.actors.ilsa.used) !== ilsaUsed0 && JSON.stringify(t.actors.aero.used) === aeroUsed, "9. the NPC's turn spends the NPC's budget, never Aero's", { ilsa: t.actors.ilsa.used, aero: t.actors.aero.used });
  ok(r.receipts.length > 0 && r.receipts.every((x) => x.roller === "ilsa" || x.actor === "ilsa" || JSON.stringify(x).includes("ilsa")), "9b. every die of that turn is receipted to the NPC who rolled it", r.receipts.slice(0, 2)); }
// 10. An invalid or stale plan is rejected without corrupting the ledger
{ const c = ctxOf("round10_start"), p = plan(c, [{ slot: "main", capability: { option: "look_up_floor" } }]); p.based_on.context_id = "evt_1385";
  const v = P.evaluate(p, c); ok(!v.legal && codes(v).includes("STALE_PLAN") && v.submittable === false, "10. a plan written against an older context is refused (STALE_PLAN)");
  const tmp = path.join(require("os").tmpdir(), "cc009_stale_" + process.pid + ".json"); fs.writeFileSync(tmp, JSON.stringify({ text: "Dodge.", actor: "aero", campaign_id: "sandbox", based_on_revision: -1 }));
  let out; try { out = cp.execFileSync("python3", ["-B", path.join(REPO, ".claude/skills/litrpg-process-turn/turn.py"), "check", "sandbox", tmp], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }); } catch (e) { out = e.stdout; }
  ok(/needs_revision/.test(out), "10b. the processor's own check refuses a stale action (sandbox run)", out);
  const bad = P.evaluate(plan(c, [{ slot: "main" }]), c); ok(!bad.legal && codes(bad).includes("EMPTY_ACTIVITY"), "10c. a malformed activity is refused before anything is sent"); }
// 11. Secondary Action is absent from live Hask Meadow unless separately approved
{ const live = ["round9_start", "round9_after_stop", "round10_start"].map(ctxOf);
  ok(live.every((c) => !P.rulesetAllowsSecondary(c) && !("secondary" in (c.budget || {}))), "11. no live Hask Meadow context publishes a Secondary budget or ruleset switch");
  const c = live[2], v = P.evaluate(plan(c, [{ slot: "secondary", intent: { text: "keep the lantern steady" } }]), c);
  ok(!v.legal && codes(v).includes("SECONDARY_NOT_ENABLED") && !v.declaration.steps.length, "11b. a Secondary activity is refused and never reaches the live declaration", codes(v));
  const sb = E.newState(C, S, "duelist", { seed: 7 }); ok(sb.switches.secondary_action === true && P.rulesetAllowsSecondary({ ruleset: { secondary_action: sb.switches.secondary_action } }),
     "11c. Secondary exists only behind the sandbox's SA-001 switch (switches.secondary_action), the same key v2 gates on", sb.switches); }
// 12. WHISPER and post-combat narrative processing remain governed by their existing contract
{ const c = ctxOf("round10_start"), w = { felt: "fear", expression: "steady hands", private: true };
  const p = Object.assign(plan(c, [{ slot: "speech", speech: { text: "Breathe." } }]), { whisper: w }), d = P.toDeclaration(p, c);
  ok(JSON.stringify(d.whisper) === JSON.stringify(w) && P.evaluate(p, c).layers.every((l) => l.outcome === null), "12. WHISPER data passes through untouched and v2 produces no outcomes of its own");
  const src = fs.readFileSync(path.join(__dirname, "turn_plan_v2.js"), "utf8");
  ok(!/post_combat|appraisal|npc_review|fs\.write|ledger\.|roll\(/.test(src.replace(/\/\*[\s\S]*?\*\//, "")), "12b. v2 contains no post-combat, appraisal, ledger or dice code paths"); }
// F1 (isolated fix). The round-10 custom step was billed as Aero's action by the validator but the preview did not say so.
{ const c = ctxOf("round10_start"), v = T.validate(FX.declarations.round10.declaration, c), pv = v.preview.find((x) => x.id === "s1");
  ok(v.used.action === 1 && /Try: .*counts as your action until then/.test(pv.text), "F1. a combat custom step now states the cost the validator already bills", pv);
  const sc = clone(c); sc.mode = "scene"; const ps = T.validate(FX.declarations.round10.declaration, sc).preview.find((x) => x.id === "s1");
  ok(!/counts as your action/.test(ps.text), "F1b. outside combat no cost is claimed", ps); }
const after = Object.fromEntries(Object.keys(before).map((p) => [p, sha(p)]));
ok(JSON.stringify(before) === JSON.stringify(after), "no protected campaign, ledger or dice file changed during the run");
console.log(fails ? fails + " FAILED" : "all " + n + " passed"); process.exit(fails ? 1 : 0);
