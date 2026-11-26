// CC-008 C: explicit experience thresholds — curve evaluator, table generator, validator rejections, candidate curves.
const F = require("./framework.js"), CU = require("./curves.js"), V = require("./validate.js"), M = require("./mastery.js"), fs = require("fs"), path = require("path");
let fails = 0, n = 0; const ok = (c, m, x) => { n++; console.log((c ? "ok " : "FAIL ") + m + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 400))); if (!c) fails++; };
const J = (p) => JSON.parse(fs.readFileSync(path.join(__dirname, p)));
const TK = J("trees/telekinetic_control.tree.json"), TK7 = J("skills/telekinetic_control.v0.1.json"), CAND = J("candidates/class_level_curves.json");
const clone = (x) => JSON.parse(JSON.stringify(x)), codes = (r) => r.errors.map((e) => e.code);
// ---- curve evaluator & tables ----
ok(V.validateTrees([TK]).ok, "Telekinetic Control (CC-007 owner numbers) validates as a CC-008 tree", V.validateTrees([TK]).errors);
const t8 = CU.table(TK.track), t7 = M.table(TK7);
ok(t8.length === 21 && t8.every((r, i) => r.xp_to_next === t7[i].xp_to_next && r.cumulative_xp === t7[i].cumulative_xp), "CC-008 curves.js reproduces CC-007 mastery.js exactly (L0–L20 steps and cumulative)");
ok(CU.cumulative(TK.track, 20) === 3620 && CU.levelFor(TK.track, 129) === 4 && CU.levelFor(TK.track, 130) === 5 && CU.levelFor(TK.track, 99999) === 20, "thresholds: L20 at 3620; 129 XP = L4, 130 XP = L5; capped at max level");
const tableTrack = { start_level: 1, max_level: 4, xp_quantity: "class_xp", curve: { id: "table/1", table: [0, 300, 900, 2700] } };
ok(CU.validate(tableTrack).length === 0 && CU.levelFor(tableTrack, 899) === 2 && CU.stepXp(tableTrack, 3) === 1800, "explicit tables: levels, steps and cumulative from the table");
// ---- malformed thresholds rejected ----
const bad = (curve, extra) => CU.validate(Object.assign({ start_level: 1, max_level: 4, xp_quantity: "class_xp", curve }, extra || {})).map((e) => e.code);
ok(bad({ id: "table/1", table: [0, 300, 200, 900] }).includes("NOT_MONOTONIC"), "non-monotonic table rejected");
ok(bad({ id: "table/1", table: [0, 300, 900] }).includes("TABLE_LENGTH"), "incomplete table rejected");
ok(bad({ id: "table/1", table: [10, 300, 900, 2700] }).includes("TABLE_START_NOT_ZERO"), "a table not starting at 0 rejected");
ok(bad({ id: "linear/1", params: { a: 0, b: 0 } }).includes("NON_POSITIVE_OR_FRACTIONAL_STEP"), "zero-XP steps rejected");
ok(bad({ id: "geometric/1", params: { base: 10.5, ratio: 1 } }).length === 0 && bad({ id: "linear/1", params: { a: 1.5, b: 0 } }).includes("NON_POSITIVE_OR_FRACTIONAL_STEP"), "fractional steps rejected (geometric rounds; linear 1.5 does not)");
ok(bad({ id: "quadratic/1", params: { a: 10 } }).includes("MISSING_PARAM") && bad({ id: "cubic/9" }).includes("UNKNOWN_CURVE"), "missing parameters and unknown curves rejected");
// ---- every levelable track must declare its thresholds ----
const noDecl = clone(TK); delete noDecl.track.max_level; delete noDecl.track.curve_status; delete noDecl.track.cadence; delete noDecl.evidence; delete noDecl.provenance;
const nd = codes(V.validateTrees([noDecl])); ok(["MISSING_MAX_LEVEL", "MISSING_CURVE_STATUS", "MISSING_CADENCE", "MISSING_EVIDENCE_RULES", "MISSING_PROVENANCE"].every((c) => nd.includes(c)), "missing max level, curve status, cadence, evidence or provenance rejected", nd);
const appr = clone(TK); appr.status = "approved"; appr.track.curve_status = "candidate"; ok(codes(V.validateTrees([appr])).includes("APPROVED_TREE_WITH_CANDIDATE_CURVE"), "an approved tree cannot carry a candidate curve");
const cm = clone(TK); cm.layer = "class"; ok(codes(V.validateTrees([cm])).includes("CLASS_LEVEL_ON_MASTERY_XP") && codes(V.validateTrees([Object.assign(clone(TK), { track: Object.assign(clone(TK.track), { xp_quantity: "class_xp" }) })])).includes("CLASS_XP_ON_NON_CLASS_TRACK"), "class level and mastery XP cannot be mixed in either direction");
// ---- prerequisites, cycles, duplicate rewards, choice groups ----
const base = () => ({ schema: F.SCHEMA, id: "mastery:t", version: "1", status: "candidate", layer: "specialized_mastery", provenance: { source: "test" },
  track: { start_level: 0, max_level: 6, xp_quantity: "mastery_xp", curve: { id: "linear/1", params: { a: 10, b: 5 } }, curve_status: "candidate", cadence: [3, 6] },
  evidence: { accepted_authorities: ["atomic"], event_types: { use: { xp: 1 } } }, choice_groups: [{ id: "g", picks: 1, exclusive: true, offer_size: 3, milestones: [3] }],
  nodes: [{ id: "a", kind: "choice", level: 3, choice_group: "g", status: "candidate", grants: [{ type: "feature", ref: "feature:a", authority: "mastery" }] },
          { id: "b", kind: "choice", level: 3, choice_group: "g", status: "candidate", grants: [{ type: "feature", ref: "feature:b", authority: "mastery" }] },
          { id: "c", kind: "choice", level: 3, choice_group: "g", status: "candidate", grants: [{ type: "feature", ref: "feature:c", authority: "mastery" }] }] });
ok(V.validateTrees([base()]).ok, "fixture tree is valid", V.validateTrees([base()]).errors);
let x = base(); x.nodes.push({ id: "d", kind: "improvement", level: 6, status: "candidate", requires: { all: ["a", "b"] } }); ok(codes(V.validateTrees([x])).includes("UNSATISFIABLE_EXCLUSIVE_REQUIREMENT"), "requiring two members of an exclusive pick-one group is rejected (the legacy Sentinel defect)");
x = base(); x.nodes.push({ id: "d", kind: "improvement", level: 6, status: "candidate", requires: { all: ["zz"] } }); ok(codes(V.validateTrees([x])).includes("UNKNOWN_PREREQUISITE"), "unknown prerequisite rejected");
x = base(); x.nodes.push({ id: "d", kind: "improvement", level: 6, status: "candidate", requires: { all: [{ track: "mastery:t", level: 9 }] } }); ok(codes(V.validateTrees([x])).includes("UNREACHABLE_TRACK_LEVEL"), "a track level above that track's max is unreachable");
x = base(); x.nodes.push({ id: "d", kind: "improvement", level: 2, status: "candidate", requires: { all: ["a"] } }); ok(codes(V.validateTrees([x])).includes("PREREQUISITE_ABOVE_NODE_LEVEL"), "a prerequisite that can only be held after the node's own level is flagged");
x = base(); x.nodes.push({ id: "d", kind: "improvement", level: 9, status: "candidate" }); ok(codes(V.validateTrees([x])).includes("NODE_ABOVE_MAX_LEVEL"), "node above max level rejected");
x = base(); x.nodes[0].requires = { all: ["c"] }; x.nodes[2].requires = { any: ["a"] }; ok(codes(V.validateTrees([x])).includes("PREREQUISITE_CYCLE"), "a prerequisite cycle is rejected (all + any edges)");
const y = base(); y.id = "mastery:u"; y.nodes[0].requires = { all: [{ node: "mastery:t/a" }] }; x = base(); x.nodes[0].requires = { all: [{ node: "mastery:u/a" }] };
ok(codes(V.validateTrees([x, y])).includes("PREREQUISITE_CYCLE"), "a cross-tree cycle is rejected");
x = base(); x.nodes[1].grants = [{ type: "feature", ref: "feature:a", authority: "mastery" }]; ok(codes(V.validateTrees([x])).includes("DUPLICATE_REWARD"), "the same reward granted twice is rejected");
x = base(); x.nodes[1].upgrades = "a"; x.nodes[1].grants = [{ type: "feature", ref: "feature:a", authority: "mastery" }]; ok(!codes(V.validateTrees([x])).includes("DUPLICATE_REWARD"), "…unless it is an explicit upgrade chain");
x = base(); x.choice_groups[0].picks = 4; ok(codes(V.validateTrees([x])).includes("UNSATISFIABLE_CHOICE_GROUP"), "a group needing more picks than members is unsatisfiable");
x = base(); x.choice_groups.push({ id: "empty", picks: 1, milestones: [6] }); ok(codes(V.validateTrees([x])).includes("EMPTY_CHOICE_GROUP"), "an empty choice group is rejected");
x = base(); x.choice_groups[0].milestones = [1]; ok(codes(V.validateTrees([x])).includes("MILESTONE_WITH_NO_ELIGIBLE_LEVEL"), "a milestone with nothing eligible yet is rejected");
x = base(); x.nodes[0].grants[0].authority = "species"; ok(codes(V.validateTrees([x])).includes("GRANT_AUTHORITY_MISMATCH"), "a mastery tree cannot issue a species grant");
x = base(); x.nodes.push({ id: "a", kind: "improvement", level: 1, status: "candidate" }); ok(codes(V.validateTrees([x])).includes("DUPLICATE_NODE_ID"), "duplicate node ids rejected");
// ---- the legacy Sentinel tree: literal vs adapted ----
const rec = JSON.parse(fs.readFileSync(path.join(__dirname, "../../registry/candidate_builds/cand_classes_861acd817b14421e/validated_candidate/sentinel.json"))).record;
const literal = F.fromLegacyClass(rec).tree; literal.nodes.forEach((nd_) => { if (nd_.legacy_reinterpretation) { const orig = rec.progression_tree.find((q) => q.node_id === nd_.id).prerequisites; nd_.requires = { all: orig.slice() }; } });
const lit = V.validateTrees([literal], { external_tracks: ["archetype:sentinel_specialization"] });
ok(lit.errors.filter((e) => e.code === "UNSATISFIABLE_EXCLUSIVE_REQUIREMENT").map((e) => e.where).join() === "class:sentinel/sentinel_specialization_3,class:sentinel/subclass_feature_7", "the LITERAL legacy Sentinel tree is rejected at exactly L3 and L7");
ok(lit.errors.some((e) => e.code === "CURVE_XP_TRACK_WITHOUT_CURVE"), "…and has no class XP thresholds (none exist in source)");
const adapted = F.fromLegacyClass(rec, { curve: CAND.curves[0].track.curve, curve_status: "candidate" }).tree; adapted.track.cadence = [4, 8, 12, 16, 19]; adapted.evidence = { accepted_authorities: ["atomic"], event_types: { encounter_completed: { xp: 450 } } };
const ad = V.validateTrees([adapted], { external_tracks: ["archetype:sentinel_specialization"] }); ok(!ad.errors.some((e) => e.code === "UNSATISFIABLE_EXCLUSIVE_REQUIREMENT"), "the adapted tree (any_of_group) has no unsatisfiable requirement", ad.errors.slice(0, 4));
// ---- candidate curves for tracks without thresholds: compared, never adopted ----
const pace = {};
CAND.curves.forEach((cv) => { const tr = cv.track; ok(cv.track.curve_status === "candidate" && CU.validate(tr).length === 0, "candidate curve " + cv.id + " is well-formed and labelled candidate");
  if (tr.xp_quantity === "none") return; const row = {};
  for (const a of ["flat_450", "scaling"]) { let xp = 0, L = 1, s = 0; const at = {}; while (L < 20 && s < 2000) { s++; xp += a === "flat_450" ? 450 : 150 * L; L = CU.levelFor(tr, xp); [3, 5, 10, 20].forEach((k) => { if (L >= k && !at[k]) at[k] = s; }); } row[a] = at; }
  pace[cv.id] = { cumulative_L5: CU.cumulative(tr, 5), cumulative_L10: CU.cumulative(tr, 10), cumulative_L20: CU.cumulative(tr, 20), sessions_to_level: row }; });
fs.writeFileSync(path.join(__dirname, "candidates/class_level_pacing.json"), JSON.stringify({ status: "candidate comparison — not adopted", assumptions: CAND.pacing_assumptions, results: pace }, null, 1) + "\n");
ok(Object.keys(pace).length === 3 && Object.values(pace).every((p) => p.sessions_to_level.flat_450[20] > 0), "pacing comparison written for the three XP candidates (candidates/class_level_pacing.json)");
console.log(fails ? fails + " FAILED" : "all " + n + " passed"); process.exit(fails ? 1 : 0);
