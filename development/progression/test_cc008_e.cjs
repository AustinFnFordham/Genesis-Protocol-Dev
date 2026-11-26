// CC-008 E: shared Discipline XP allocation + anti-farming.
const F = require("./framework.js"), D = require("./disciplines.js"), V = require("./validate.js"), P = require("./policies/discipline_allocation.v0.1.json");
let fails = 0, n = 0; const ok = (c, m, x) => { n++; console.log((c ? "ok " : "FAIL ") + m + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 400))); if (!c) fails++; };
const T = F.registry(D.treesForPolicy(P)); ok(V.validateTrees(Object.values(T)).ok, "implied discipline and mastery tracks validate", V.validateTrees(Object.values(T)).errors.slice(0, 3));
const OWN = ["saber_strike", "saber_strike_2h", "unarmed_strike", "flow_strike", "parry", "grapple", "escape_grapple", "release_grapple", "readied_dodge", "dodge_reaction", "minor_telekinesis", "recover_weapon", "speak", "move", "traverse", "tactical_glance", "blaster_shot"];
let seq = 0; const ob = (pid, facts, extra) => Object.assign({ observation_id: "obs" + (++seq), actor: "aero", pid, authority: "atomic", committed: true, validated: true, scene: "scene1", facts: facts || {} }, extra || {});
const xpOf = (ch, t) => F.trackState(ch, t).xp;
let ch = F.newCharacter("aero");
const step = (o, owned) => { const r = D.apply(T, ch, P, o, owned || OWN); ch = r.state; return r; };
// Parry: ordinary vs Force-augmented
let r = step(ob("parry")); ok(r.awarded.map((a) => a.track).join() === "mastery:lightsaber_defense,discipline:reaction_timing", "ordinary Parry → its own mastery track + Reaction/Timing", r.awarded);
r = step(ob("parry", { force_augmented: true })); ok(r.awarded.map((a) => a.track).includes("discipline:force") && r.awarded.length === 3, "Force-augmented Parry additionally credits the Force discipline (from the event fact)", r.awarded);
// Echani Strike & Martial Arts; one- vs two-handed lightsaber
r = step(ob("unarmed_strike")); ok(r.awarded.map((a) => a.track).join() === "mastery:echani_strike,discipline:martial_arts", "Echani Strike → Echani Strike mastery + Martial Arts");
step(ob("saber_strike")); step(ob("saber_strike_2h"));
ok(xpOf(ch, "mastery:lightsaber_one_hand") === 1 && xpOf(ch, "mastery:lightsaber_two_hand") === 1 && xpOf(ch, "discipline:armed_combat") === 2, "one-hand and two-hand lightsaber are separate masteries sharing Armed Combat");
// Grapple family shares one parent track; release earns nothing
step(ob("grapple")); step(ob("escape_grapple")); r = step(ob("release_grapple"));
ok(xpOf(ch, "mastery:grappling") === 2 && !T["mastery:escape_grapple"] && r.awarded.length === 0, "Grapple and Escape share the Grappling parent; Release earns nothing");
// Readied Dodge + Dodge Reaction: one observation
const before = xpOf(ch, "mastery:dodge"); r = step(ob("readied_dodge", {}, { chain_id: "d1" })); ok(r.awarded.length === 0 && r.reason === "SETUP_ONLY", "the readied setup alone earns nothing");
step(ob("dodge_reaction", {}, { chain_id: "d1" })); r = step(ob("dodge_reaction", {}, { chain_id: "d1" }));
ok(xpOf(ch, "mastery:dodge") === before + 1 && r.awarded.length === 0, "setup + triggered dodge are ONE credited observation (no duplicate credit)");
// Telekinetic retrieval vs physical recovery
r = step(ob("minor_telekinesis")); ok(r.awarded.map((a) => a.track).join() === "mastery:telekinetic_control,discipline:force", "Telekinetic retrieval → Telekinetic Control + Force");
r = step(ob("recover_weapon")); ok(r.awarded.length === 0 && r.reason === "NOT_MEANINGFUL", "picking up your own weapon unthreatened earns nothing");
r = step(ob("recover_weapon", { threatened: true })); ok(r.awarded.map((a) => a.track).join() === "discipline:equipment_handling", "recovering it under threat → Equipment Handling only (no Force, no mastery)");
// Speech: meaningful vs spam
for (let i = 0; i < 10; i++) step(ob("speak")); ok(xpOf(ch, "discipline:social_influence") === 0, "ten lines of arbitrary conversation earn nothing");
for (let i = 0; i < 5; i++) step(ob("speak", { social_check_committed: true })); ok(xpOf(ch, "discipline:social_influence") === 2, "meaningful speech (committed social check) credits, capped at 2 per scene");
step(ob("speak", { social_check_committed: true }, { scene: "scene2" })); ok(xpOf(ch, "discipline:social_influence") === 3, "the cap is per scene");
// Traversal vs footsteps
for (let i = 0; i < 30; i++) step(ob("move")); ok(xpOf(ch, "discipline:mobility") === 0, "thirty moves (every footstep) earn nothing");
step(ob("traverse", { traversal_challenge: "climb" })); ok(xpOf(ch, "discipline:mobility") === 1, "a committed traversal challenge earns Mobility");
// Compound maneuver with multiple prerequisites
r = step(ob("controlled_takedown"), OWN.concat(["controlled_takedown"])); ok(r.reason === "MISSING_COMPONENT", "a compound Maneuver without all its component grants earns nothing");
const ownAll = OWN.concat(["controlled_takedown", "blade_bind"]); r = step(ob("controlled_takedown"), ownAll);
ok(r.awarded.map((a) => a.track).join() === "mastery:maneuver_controlled_takedown,discipline:martial_arts,discipline:armed_combat" && xpOf(ch, "mastery:grappling") === 2, "with every component owned, the Maneuver credits its own track (components not double-credited)");
// Bounds
const many = Object.assign({}, P, { rules: [{ id: "wide", pids: ["x"], primary: null, pools: ["force", "martial_arts", "mobility", "marksmanship"] }] });
ok(D.allocate(many, ob("x"), ["x"]).credit.pools.length === 2, "at most 2 pools per observation (bounded)");
// Unlearned / narrated / uncommitted
ok(D.apply(T, ch, P, ob("minor_telekinesis"), ["saber_strike"]).reason === "UNLEARNED_CAPABILITY", "an unlearned capability earns no XP");
ok(D.apply(T, ch, P, ob("saber_strike", {}, { authority: "narration" }), OWN).reason === "UNTRUSTED_AUTHORITY" && D.apply(T, ch, P, ob("saber_strike", {}, { committed: false }), OWN).reason === "NOT_COMMITTED_OR_VALIDATED", "narrated or uncommitted actions earn nothing");
// Determinism, idempotency, replay
const dup = ob("saber_strike"); const a1 = D.apply(T, ch, P, dup, OWN); const a2 = D.apply(T, a1.state, P, dup, OWN);
ok(a1.awarded.length === 2 && a2.awarded.length === 0 && a2.skipped.every((s) => s.reason === "DUPLICATE"), "re-applying the same observation credits nothing");
const replay = (obs) => obs.reduce((c, o) => D.apply(T, c, P, o, OWN).state, F.newCharacter("aero")), list = [ob("parry"), ob("unarmed_strike"), ob("speak", { social_check_committed: true })];
ok(JSON.stringify(replay(list)) === JSON.stringify(replay(list)), "replaying the same observation history is byte-identical");
// Multi-PC team event
let chars = { aero: F.newCharacter("aero"), kass: F.newCharacter("kass"), tala: F.newCharacter("tala") };
const team = { team_event_id: "team1", authority: "atomic", scene: "s", participants: [{ actor: "aero", pid: "grapple", committed: true, validated: true }, { actor: "kass", pid: "saber_strike", committed: true, validated: true }, { actor: "tala", pid: "blaster_shot", committed: false, validated: false }] };
const tr = D.applyTeam(T, chars, P, team, { aero: OWN, kass: ["saber_strike"], tala: ["blaster_shot"] });
ok(xpOf(tr.aero.state, "mastery:grappling") === 1 && xpOf(tr.aero.state, "mastery:lightsaber_one_hand") === 0 && xpOf(tr.kass.state, "mastery:lightsaber_one_hand") === 1 && xpOf(tr.kass.state, "mastery:grappling") === 0, "team event: each PC is credited only for their own committed contribution");
ok(tr.tala.awarded.length === 0, "a participant whose part wasn't committed earns nothing");
ok(D.applyTeam(T, { aero: tr.aero.state }, P, team, { aero: OWN }).aero.awarded.length === 0, "replaying the team event credits nobody twice");
console.log(fails ? fails + " FAILED" : "all " + n + " passed"); process.exit(fails ? 1 : 0);
