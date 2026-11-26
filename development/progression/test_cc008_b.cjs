// CC-008 unified progression framework tests (sandbox). node test_framework.cjs
const F = require("./framework.js"), CU = require("./curves.js"), path = require("path"), fs = require("fs");
let fails = 0, n = 0; const ok = (c, m, x) => { n++; console.log((c ? "ok " : "FAIL ") + m + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 300))); if (!c) fails++; };
const sentinelRec = JSON.parse(fs.readFileSync(path.join(__dirname, "../../registry/candidate_builds/cand_classes_861acd817b14421e/validated_candidate/sentinel.json"))).record;
const ev = (id, type, extra) => Object.assign({ event_id: id, authority: "atomic", committed: true, validated: true, type, actor: "aero", facts: {} }, extra || {});

// ===== B. unified schema: layers, typed quantities, legacy adapter, requirement modes =====
console.log("# B");
{ const { tree, notes } = F.fromLegacyClass(sentinelRec, { source: "registry/candidate_builds/.../sentinel.json (candidate)", curve: { id: "none/1" } });
  ok(tree.id === "class:sentinel" && tree.layer === "class" && tree.status === "candidate" && tree.track.xp_quantity === "class_xp", "legacy Sentinel tree adapts to a candidate class track (never approved by adaptation)");
  const spec = F.nodeOf(tree, "sentinel_specialization_3"), s7 = F.nodeOf(tree, "subclass_feature_7");
  ok(spec.requires.all.some((t) => t.any_of_group === "sentinel_focus_level_2") && /any_of_group/.test(spec.legacy_reinterpretation), "L3 'both L2 choices' prerequisite is read as any_of_group and the reinterpretation is recorded");
  ok(s7.requires.all.some((t) => t.any_of_group === "sentinel_enhancement_level_6") && notes.filter((q) => /any_of_group/.test(q.note)).length === 2, "the same at L7; exactly two any_of_group reinterpretations noted", notes);
  ok(F.nodeOf(tree, "sentinel_specialization_3").grants[0].type === "track_unlock" && F.nodeOf(tree, "force_connection_1").grants[0].type === "feature", "subclass_entry unlocks a track; core nodes grant features");
  // literal reading would be unsatisfiable: with only one L2 pick, strict ALL fails, any_of_group passes
  const T = F.registry([tree]); let ch = F.newCharacter("aero", { class: "sentinel" }); ch.tracks["class:sentinel"] = { level: 3, xp: 0 }; ch.held["class:sentinel/force_connection_1"] = {}; ch.held["class:sentinel/investigation_focus_2"] = {};
  const strict = F.evalReq({ all: ["investigation_focus_2", "diplomacy_focus_2"] }, F.ctxFor(T, ch), "class:sentinel");
  ok(!strict && F.evalReq(spec.requires, F.ctxFor(T, ch), "class:sentinel"), "legacy literal reading is unsatisfiable; adapted requirement is satisfiable with one L2 pick"); }
// fixture trees for the remaining B checks
const curveQ = { id: "quadratic/1", params: { a: 10, b: 5, c: 1 } };
const trees = F.registry([
  { schema: F.SCHEMA, id: "class:fixture", version: "t", status: "candidate", layer: "class", provenance: { source: "test" }, track: { start_level: 1, max_level: 20, xp_quantity: "class_xp", curve: { id: "linear/1", params: { a: 100, b: 100 } }, curve_status: "candidate" },
    evidence: { accepted_authorities: ["atomic"], event_types: { encounter_completed: { xp: 150 } } }, nodes: [{ id: "c1", kind: "core_grant", level: 1, status: "candidate", grants: [{ type: "feature", ref: "feature:fx_core", authority: "class" }] }] },
  { schema: F.SCHEMA, id: "mastery:grappling", version: "t", status: "candidate", layer: "specialized_mastery", provenance: { source: "test" }, track: { start_level: 0, max_level: 20, xp_quantity: "mastery_xp", curve: curveQ, curve_status: "candidate" },
    evidence: { accepted_authorities: ["atomic"], event_types: { grapple_attempt: { xp: 1 } } }, nodes: [] },
  { schema: F.SCHEMA, id: "mastery:escape_grapple", version: "t", status: "candidate", layer: "parent_linked", parent: "mastery:grappling", provenance: { source: "test" }, track: { start_level: 0, xp_quantity: "none", driven_by: "mastery:grappling", curve: { id: "none/1" } }, nodes: [] },
  { schema: F.SCHEMA, id: "species:fixture", version: "t", status: "candidate", layer: "species", restrictions: { species: ["echani"] }, provenance: { source: "test" }, track: { start_level: 1, xp_quantity: "none", driven_by: "class:fixture", curve: { id: "none/1" }, cadence: [5, 10, 15, 20] }, nodes: [] }
]);
{ let ch = F.newCharacter("aero", { class: "fixture", species: "echani" });
  let r = F.awardXp(trees, ch, "class:fixture", ev("enc1", "encounter_completed")); ch = r.state;
  ok(ch.ledger.class_xp === 150 && F.levelOfTrack(trees, ch, "class:fixture") === 2 && F.trackState(ch, "mastery:grappling").xp === 0, "class XP raises class level only; no mastery XP moves");
  r = F.awardXp(trees, ch, "mastery:grappling", ev("g1", "grapple_attempt")); ch = r.state;
  ok(F.trackState(ch, "mastery:grappling").xp === 1 && ch.ledger.class_xp === 150, "mastery XP never touches class XP (class level ≠ mastery level)");
  ok(F.awardXp(trees, ch, "mastery:grappling", ev("g1", "grapple_attempt")).duplicate, "one award per (track, event): replay is a duplicate");
  ok(F.awardXp(trees, ch, "class:fixture", ev("g1", "grapple_attempt")).code === "NOT_ELIGIBLE_EVIDENCE", "evidence must be eligible for THAT track");
  ok(F.awardXp(trees, ch, "mastery:escape_grapple", ev("e1", "grapple_attempt")).code === "TRACK_HAS_NO_XP" && F.levelOfTrack(trees, ch, "mastery:escape_grapple") === F.levelOfTrack(trees, ch, "mastery:grappling"), "parent-linked track shares its parent's level and owns no XP");
  ok(F.levelOfTrack(trees, ch, "species:fixture") === F.levelOfTrack(trees, ch, "class:fixture"), "a track driven_by class follows class level");
  ok(F.trackAllowed(trees["species:fixture"], F.newCharacter("x", { species: "human" }))[0].code === "SPECIES_RESTRICTED", "species restriction enforced");
  ok(["narration", "client"].every((a) => F.awardXp(trees, ch, "mastery:grappling", ev("n" + a, "grapple_attempt", { authority: a })).code === "UNTRUSTED_AUTHORITY"), "narrated / client-asserted evidence earns nothing");
  const g = F.applyCoreGrants(trees, ch, "class:fixture"); ok(g.granted.join() === "c1" && g.state.features.includes("feature:fx_core") && F.applyCoreGrants(trees, g.state, "class:fixture").granted.length === 0, "core grants apply once at their level (idempotent)");
  ok(F.verifyReceipt(g.state.receipts.slice(-1)[0]) && g.state.receipts.every((x) => x.hash), "every transaction is hash-sealed"); }
{ // requirement modes
  const t = F.registry([{ id: "k", nodes: [{ id: "a", choice_group: "g" }, { id: "b", choice_group: "g" }] }]), ctx = { held: { "k/a": true }, levels: { k: 4 }, features: ["f1"], training: [], trees: t };
  ok(F.evalReq({ all: ["a", { track: "k", level: 3 }, { feature: "f1" }] }, ctx, "k") && !F.evalReq({ all: ["a", "b"] }, ctx, "k") && F.evalReq({ any: ["a", "b"] }, ctx, "k") && F.evalReq({ any_of_group: "g" }, ctx, "k") && !F.evalReq({ not: ["a"] }, ctx, "k"), "requirement modes: all / any / any_of_group / not / track level / feature");
  ok(F.missing({ all: ["b", { track: "k", level: 9 }] }, ctx, "k").map((m) => m.code).join() === "NODE,TRACK_LEVEL", "missing() explains locked reasons"); }
console.log(fails ? fails + " FAILED" : "all " + n + " passed"); process.exit(fails ? 1 : 0);
