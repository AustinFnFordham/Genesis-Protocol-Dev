// CC-007 §4/§5: mastery substrate + Telekinetic Control prototype (sandbox, noncanonical). node test_progression.cjs
const M = require("./mastery.js"), A = require("./adapters.js"), fs = require("fs"), path = require("path");
const TK = require("./skills/telekinetic_control.v0.1.json"), GR = require("./skills/grappling.scaffold.v0.1.json"), SCENE = require("./fixtures/scene_objects.json");
const E = require("../combat_slice/engine.js"), C = require("../combat_slice/catalog.json"), S = require("../combat_slice/scenarios.json");
let fails = 0, n = 0; const ok = (c, m, x) => { n++; console.log((c ? "ok " : "FAIL ") + m + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 300))); if (!c) fails++; };
const ev = (id, f, extra) => Object.assign({ event_id: id, authority: "atomic_exploration", committed: true, validated: true, type: "telekinesis_use", skill: "telekinetic_control", actor: "aero", facts: Object.assign({ weight_lb: 1, distance_ft: 5, object_kind: "tool", in_encounter: false }, f || {}) }, extra || {});

// ---- curve & table (owner baseline) ----
ok([0, 1, 2, 3].map((L) => M.xpToNext(TK, L)).join() === "10,16,24,34", "XP(L→L+1) = 10 + 5L + L² (10, 16, 24, 34 …)");
ok(M.cumulativeXp(TK, 5) === 130 && M.cumulativeXp(TK, 10) === 610 && M.cumulativeXp(TK, 15) === 1690 && M.cumulativeXp(TK, 20) === 3620, "cumulative XP: L5 130, L10 610, L15 1690, L20 3620");
ok(M.xpToNext(TK, 1) - M.xpToNext(TK, 0) < M.xpToNext(TK, 11) - M.xpToNext(TK, 10), "the curve gets steeper (second difference 2)");
const c0 = M.capability(TK, 0).values, c5 = M.capability(TK, 5).values, c20 = M.capability(TK, 20).values;
ok(c0.range_ft === 30 && c0.max_weight_lb === 10, "level 0 = the Jedi Fundamentals limits (30 ft, 10 lb)");
ok(c5.range_ft === 55 && c5.max_weight_lb === 20 && c20.range_ft === 130 && c20.max_weight_lb === 45, "+5 ft & +1 lb per level, +5 lb at 5/10/15 (L5 55/20, L20 130/45)");
ok(M.capability(TK, 7).provenance.max_weight_lb.length === 3 && M.capability(TK, 0).provenance.range_ft[0].source.includes("jedi_fundamentals"), "every number carries provenance (base rule + per-level + milestone)");
ok(c20.objects_at_once === 1, "no level adds a second object");
// ---- the event gate: no XP from narration or client assertions ----
let s = M.newCharacter("aero");
ok(M.award(TK, s, ev("e1", {}, { authority: "narration" })).code === "UNTRUSTED_AUTHORITY", "narrated use: refused");
ok(M.award(TK, s, ev("e1", {}, { authority: "client" })).code === "UNTRUSTED_AUTHORITY", "client-asserted use: refused");
ok(M.award(TK, s, ev("e1", {}, { committed: false })).code === "NOT_COMMITTED", "uncommitted use: refused");
ok(M.award(TK, s, ev("e1", {}, { validated: false })).code === "NOT_VALIDATED", "unvalidated use: refused");
ok(M.award(TK, s, ev("e1", {}, { actor: "ilsa" })).code === "WRONG_ACTOR" && M.award(TK, s, ev("e1", {}, { type: "speech" })).code === "NOT_A_SKILL_USE", "another character's event or a non-use: refused");
// ---- awards, classification, idempotency ----
let r = M.award(TK, s, ev("e1")); s = r.state;
ok(r.ok && r.receipt.xp === 3 && r.receipt.parts.map((p) => p.rule).join() === "base:telekinesis_use,novel_object", "first use of a new object kind: 1 + 2 (novel)", r.receipt);
const again = M.award(TK, s, ev("e1")); ok(again.duplicate && again.receipt.id === r.receipt.id && again.state.skills.telekinetic_control.xp === 3, "the same committed event never awards twice (same receipt)");
r = M.award(TK, s, ev("e2")); s = r.state; ok(r.receipt.xp === 1, "routine repeat: exactly the minimum 1 XP");
r = M.award(TK, s, ev("e3", { weight_lb: 8, object_kind: "tool" })); s = r.state; ok(r.receipt.parts.some((p) => p.rule === "demanding_load") && r.receipt.xp === 2, "≥75% of capacity: +1 (from the event's weight fact)");
r = M.award(TK, s, ev("e4", { distance_ft: 25, object_kind: "tool" })); s = r.state; ok(r.receipt.parts.some((p) => p.rule === "demanding_reach"), "≥75% of range: +1");
r = M.award(TK, s, ev("e5", { in_encounter: true })); s = r.state; ok(!r.receipt.parts.some((p) => p.rule === "under_pressure"), "the 'under pressure' bonus is off until the owner decides");
ok(M.verifyReceipt(r.receipt) && !M.verifyReceipt(Object.assign({}, r.receipt, { xp: 99 })), "receipts are hash-sealed (tampering detected)");
ok(M.receiptId("aero", TK, ev("e1")) === M.receiptId("aero", TK, ev("e1")), "receipt ids are deterministic");
// level up
let t = M.newCharacter("aero"); for (let i = 0; i < 10; i++) t = M.award(TK, t, ev("lvl" + i, { object_kind: "tool" })).state;
ok(t.skills.telekinetic_control.level === 1 && t.skills.telekinetic_control.xp === 12, "10 uses (12 XP with the first novel bonus) → level 1");
// ---- two-phase transactions & recovery ----
let b = M.begin(TK, s, ev("crash1")); ok(b.phase === "pending" && !b.state.applied["telekinetic_control|crash1"], "phase 1 writes a pending receipt only");
ok(M.begin(TK, b.state, ev("other")).code === "TXN_PENDING", "a second award waits while one is pending");
const rec = M.recover(b.state); ok(rec.ok && rec.state.applied["telekinetic_control|crash1"] && !rec.state.pending && rec.state.skills.telekinetic_control.xp === s.skills.telekinetic_control.xp + b.receipt.xp, "interrupted after phase 1: recovery applies it exactly once");
ok(M.recover(rec.state).nothing && M.award(TK, rec.state, ev("crash1")).duplicate, "recovery is idempotent; replaying the event afterwards is a duplicate");
const dup = JSON.parse(JSON.stringify(rec.state)); dup.pending = b.receipt; ok(M.commit(dup).duplicate && M.commit(dup).state.skills.telekinetic_control.xp === rec.state.skills.telekinetic_control.xp, "a stale pending copy of an applied award is discarded, not re-applied");
// ---- replay: the ledger is rebuilt from committed events alone ----
const log = ["e1", "e2", "e1", "e3", "e2", "e4"].map((id, i) => ev(id, id === "e3" ? { weight_lb: 8 } : id === "e4" ? { distance_ft: 25 } : {}));
const rp1 = M.replay([TK], "aero", log), rp2 = M.replay([TK], "aero", log);
ok(JSON.stringify(rp1) === JSON.stringify(rp2) && rp1.receipts.length === 4, "replay is deterministic and duplicates in the log award nothing (6 events, 4 receipts)");
// ---- milestones: eligibility only; never an auto-grant of unlearned powers ----
let hi = M.newCharacter("aero"); hi.skills.telekinetic_control = { level: 15, xp: M.cumulativeXp(TK, 15), version: TK.version };
const ms = M.milestoneStatus(TK, hi, ["minor_telekinesis"]);
ok(ms.length === 3 && ms.every((m) => m.eligible && !m.granted), "at level 15 all three milestones are ELIGIBLE, none granted");
ok(ms.every((m) => m.never_grants.includes("force_pull") && m.never_grants.includes("force_push") && m.never_grants.includes("creature_manipulation") && m.never_grants.includes("damage")), "no milestone grants Force Pull/Push, creature manipulation or damage");
ok(M.milestoneStatus(TK, hi, []).every((m) => !m.eligible && m.missing.some((x) => x.code === "FEATURE")), "prerequisite: the Jedi Fundamentals feature is required");
ok(M.recordGrant(TK, hi, "tk_m5_fine_manipulation", null, ["minor_telekinesis"]).code === "APPROVAL_REQUIRED", "a milestone grant needs a recorded approval (never automatic)");
const g = M.recordGrant(TK, hi, "tk_m5_fine_manipulation", { by: "owner", event_id: "train_001", source: "sandbox test" }, ["minor_telekinesis"]);
ok(g.ok && g.grant.status === "sandbox_proposal" && g.grant.approved_by === "owner", "an approved grant records who, which event and its status");
ok(M.recordGrant(TK, M.newCharacter("aero"), "tk_m5_fine_manipulation", { by: "owner", event_id: "x", source: "x" }, ["minor_telekinesis"]).code === "NOT_ELIGIBLE", "not eligible below level 5");
ok(!("class_level" in hi) && TK.class_level_independent === true, "mastery is independent of class level");
// ---- exploration: at-will, validated against scene data; limits are real ----
const m0 = M.newCharacter("aero"), use = (o, extra) => A.explorationUse(TK, m0, SCENE, Object.assign({ use_id: "u-" + o, object: o }, extra || {}));
ok(use("hydrospanner").ok && use("hydrospanner").event.authority === "atomic_exploration", "ordinary out-of-combat use: at-will, no roll");
ok(use("supply_crate").code === "TOO_HEAVY" && use("power_cell").code === "OUT_OF_RANGE", "weight (14 lb) and range (40 ft) limits are validated at level 0");
ok(use("mechanic_wrench").code === "ATTENDED_OBJECT" && use("behind_bulkhead").code === "NOT_VISIBLE" && use("wall_lever").code === "FIXED_OBJECT", "attended, unseen and fixed objects are refused");
ok(use("datapad", { uncertain: true }).code === "ROLL_RULE_UNSET", "an uncertain use is refused until the owner sets the roll rule (open item 1)");
const m6 = M.newCharacter("aero"); m6.skills.telekinetic_control = { level: 4, xp: M.cumulativeXp(TK, 4) };
ok(A.explorationUse(TK, m6, SCENE, { use_id: "c", object: "supply_crate" }).ok && A.explorationUse(TK, m6, SCENE, { use_id: "p", object: "power_cell" }).ok, "at level 4 (50 ft, 14 lb) the crate and the power cell come within reach");
ok(A.explorationUse(TK, m6, SCENE, { use_id: "L", object: "wall_lever" }, []).code === "FIXED_OBJECT" && A.explorationUse(TK, m6, SCENE, { use_id: "L", object: "wall_lever" }, [{ milestone: "tk_m5_fine_manipulation" }]).ok, "mechanisms only after the level-5 training is recorded");
const x1 = use("hydrospanner").event, x2 = use("hydrospanner").event; ok(x1.event_id === x2.event_id, "the same declared use maps to the same event id (no double XP on retry)");
// ---- combat: XP only from server-verified engine events; limits flow in as a session overlay ----
let st = E.newState(C, S, "duelist", { seed: 7, campaign: "starwars_litrpg", overlays: [require("../combat_slice/campaign_overlay.js").fromJediFundamentals(JSON.parse(fs.readFileSync(path.join(__dirname, "../../campaigns/starwars_litrpg/creator/jedi_fundamentals.json"))))] });
st.actors.aero.dropped = JSON.parse(JSON.stringify(st.actors.aero.weapon)); st.actors.aero.weapon.held = false;
const before = st.log.length, rt = E.resolveTurn(st, "aero", [{ pid: "minor_telekinesis", object: "own_weapon" }], {});
ok(rt.state && rt.state.actors.aero.weapon.held && rt.state.actors.aero.weapon.ignited === false, "combat: Telekinesis retrieves the lightsaber unlit (R-2), Main action as before");
ok(A.combatEvents(TK, "sess", "R1.T0.aero", rt.state, before, false, "aero").code === "TURN_NOT_VERIFIED", "combat XP is refused until the server verified the turn");
const ce = A.combatEvents(TK, "sess", "R1.T0.aero", rt.state, before, true, "aero");
ok(ce.ok && ce.events.length === 1 && ce.events[0].facts.weight_lb === 3 && ce.events[0].facts.in_encounter, "a verified turn yields one committed telekinesis event with its facts");
const cs = M.award(TK, M.newCharacter("aero"), ce.events[0]); ok(cs.ok && cs.receipt.xp >= 1, "and earns XP (combat and exploration count alike)");
ok(A.combatEvents(TK, "sess", "R1.T0.aero", rt.state, before, true, "aero").events[0].event_id === ce.events[0].event_id, "re-reading the same verified turn gives the same event id (idempotent)");
let lv = M.newCharacter("aero"); lv.skills.telekinetic_control = { level: 4, xp: M.cumulativeXp(TK, 4) };
const ov = E.newState(C, S, "duelist", { seed: 7, tk_limits: A.tkLimits(TK, lv) }); ok(ov.tk_limits.range_ft === 50 && ov.tk_limits.max_weight_lb === 14 && /sandbox overlay/.test(ov.tk_limits.source), "mastery limits enter a session only as a labelled overlay");
ok(!JSON.stringify(require("../combat_slice/scenarios.json").aero).includes("telekinetic_control"), "nothing is written into Aero's runtime fixture/sheet");
ok(E.newState(C, S, "duelist", { seed: 7 }).tk_limits === undefined, "without the overlay the Jedi Fundamentals limits apply unchanged");
// ---- grappling scaffold: reuses the substrate but grants nothing yet ----
ok(GR.status === "scaffold" && (GR.milestones || []).every((m) => !m.bonuses && m.kind === "family_placeholder") && GR.curve.id === "quadratic/1", "grapple scaffold: placeholders only, no numbers or grants, same substrate");
console.log(fails ? fails + " FAILED" : "all " + n + " passed"); process.exit(fails ? 1 : 0);
