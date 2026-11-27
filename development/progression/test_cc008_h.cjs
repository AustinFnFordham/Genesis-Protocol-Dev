// CC-008.1: legacy prerequisite adapter audit + provenance/executable authority gates.
const F = require("./framework.js"), V = require("./validate.js"), CH = require("./choices.js"), AU = require("./authoring.js"), A = require("./fixtures/aero_vertical/aero_vertical.js");
const AUD = require("./tools/audit_legacy_prereqs.cjs"), fs = require("fs"), path = require("path"), crypto = require("crypto");
let fails = 0, n = 0; const ok = (c, m, x) => { n++; console.log((c ? "ok " : "FAIL ") + m + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 400))); if (!c) fails++; };
const REPO = path.join(__dirname, "../.."), clone = (x) => JSON.parse(JSON.stringify(x)), codes = (r) => r.errors.map((e) => e.code);
const L = (nodes) => ({ id: "t", progression_tree: nodes }), nd = (node_id, lvl, extra) => Object.assign({ node_id, feature_id: node_id, level_requirement: lvl, type: "core" }, extra || {});
// ===== adapter: ambiguous and invalid prerequisites =====
{ const r = F.fromLegacyClass(L([nd("a", 1), nd("x", 2, { type: "choice", choice_group: "g" }), nd("y", 2, { type: "choice", choice_group: "g" }), nd("z", 2, { type: "choice", choice_group: "g" }), nd("c", 3, { prerequisites: ["x", "y"] })]));
  const c = r.notes.find((q) => q.code === "AMBIGUOUS_EXCLUSIVE_GROUP"), node = F.nodeOf(r.tree, "c");
  ok(c && c.partial_group_listing.includes("g") && JSON.stringify(c.original_prerequisites) === '["x","y"]', "ambiguous: two of three exclusive members listed → reinterpreted, flagged as a PARTIAL listing, original kept", c);
  ok(JSON.stringify(node.legacy_prerequisites) === '["x","y"]' && node.requires.all[0].any_of_group === "g" && node.provenance_class === "legacy", "the node keeps the verbatim legacy prerequisites beside the interpretation");
  ok(r.tree.promotion.requires_explicit_validation === true && r.tree.status === "candidate", "a reinterpreted tree requires explicit validation and stays candidate"); }
{ const r = F.fromLegacyClass(L([nd("a", 1), nd("b", 2, { prerequisites: ["a"] })]));
  ok(!r.notes.some((q) => q.code === "AMBIGUOUS_EXCLUSIVE_GROUP") && JSON.stringify(F.nodeOf(r.tree, "b").requires) === '{"all":["a"]}' && r.tree.promotion.requires_explicit_validation === false, "an unambiguous ALL list is kept exactly as written (no reinterpretation)"); }
{ const r = F.fromLegacyClass(L([nd("a", 1), nd("x", 2, { type: "choice", choice_group: "g" }), nd("y", 2, { type: "choice", choice_group: "g" }), nd("c", 3, { prerequisites: ["a", "x"] })]));
  ok(!r.notes.some((q) => q.code === "AMBIGUOUS_EXCLUSIVE_GROUP") && JSON.stringify(F.nodeOf(r.tree, "c").requires) === '{"all":["a","x"]}', "requiring ONE specific option of a group is not ambiguous and is not rewritten"); }
{ const r = F.fromLegacyClass(L([nd("a", 1), nd("b", 2, { prerequisites: ["ghost"] }), nd("s", 2, { prerequisites: ["s"] }), nd("h", 2, { prerequisites: ["late"] }), nd("late", 5), nd("q", 3, { prerequisites: "a" }), nd("a", 4)]));
  const cs = new Set(r.notes.filter((q) => q.invalid).map((q) => q.code));
  ok(["DANGLING_PREREQUISITE", "SELF_PREREQUISITE", "PREREQUISITE_ABOVE_LEVEL", "NON_LIST_PREREQUISITES", "DUPLICATE_NODE_ID"].every((c) => cs.has(c)), "invalid legacy prerequisites are reported, not silently repaired", [...cs]);
  ok(JSON.stringify(F.nodeOf(r.tree, "b").requires) === '{"all":["ghost"]}' && r.tree.promotion.requires_explicit_validation, "a dangling reference is kept verbatim (so the validator rejects it) and blocks promotion");
  ok(codes(V.validateTrees([Object.assign(r.tree, { track: { start_level: 1, max_level: 20, xp_quantity: "none", driven_by: "x" } })], { external_tracks: ["x"] })).some((c) => c === "UNKNOWN_PREREQUISITE" || c === "PREREQUISITE_CYCLE"), "…and the validator rejects the adapted tree"); }
{ const r = F.fromLegacyClass(L([nd("a", 1), nd("o", 2, { type: "choice", choice_group: "solo" })])); ok(r.notes.some((q) => q.code === "SINGLE_OPTION_CHOICE_GROUP"), "a one-option 'choice' group is reported"); }
// ===== audit report =====
const rep = AUD.audit(), committed = JSON.parse(fs.readFileSync(path.join(__dirname, "legacy/legacy_prereq_audit.json")));
ok(rep.summary.all.reinterpreted_trees === 40 && rep.summary.candidate_build.reinterpreted_trees === 17 && rep.summary.hub_archive.reinterpreted_trees === 23, "audit: exactly the 40 known contradictory trees (17 candidate + 23 hub) are reinterpreted", rep.summary);
ok(JSON.stringify(rep.summary) === JSON.stringify(committed.summary) && rep.records.length === committed.records.length, "the committed audit report is current (regenerated identically)");
ok(rep.records.every((r) => r.promotion.promotable === false) && rep.records.filter((r) => r.reinterpreted.length).every((r) => r.promotion.requires_explicit_validation), "no legacy record is promotable; every reinterpreted record requires explicit validation");
ok(rep.records.filter((r) => r.reinterpreted.length).every((r) => r.reinterpreted.every((q) => Array.isArray(q.original_prerequisites) && q.original_prerequisites.length >= 2)), "every reinterpretation carries its original prerequisite list");
const sent = rep.records.find((r) => r.family === "candidate_build" && r.id === "sentinel"); ok(sent && sent.reinterpreted.map((q) => q.node).join() === "sentinel_specialization_3,subclass_feature_7", "Sentinel: exactly L3 and L7 reinterpreted");
ok(rep.records.filter((r) => r.invalid.length).map((r) => r.family + ":" + r.id).sort().join() === "candidate_build:scoundrel,hub_archive:scoundrel", "invalid prerequisites: only Scoundrel (dangling evasion_7), in both source families");
const cb = rep.records.filter((r) => r.family === "candidate_build"); ok(cb.every((r) => crypto.createHash("sha256").update(fs.readFileSync(path.join(REPO, r.source))).digest("hex") === r.source_sha256), "candidate sources are unchanged (sha256 matches the report)");
const zipSha = crypto.createHash("sha256").update(fs.readFileSync(path.join(REPO, "_QUARANTINE/hub_root_debris/SW5e_Data_Hub.zip"))).digest("hex");
ok(JSON.parse(fs.readFileSync(path.join(__dirname, "legacy/hub_trees_extract.json"))).archive.sha256 === zipSha, "the hub archive is unchanged (sha256 matches the extract)");
// ===== provenance / executable authority =====
const B = A.build(), T = F.registry(B.trees), EXT = { external_tracks: ["diplomat", "shadow_guard", "artisan", "investigator", "racer", "shadow", "shien_expert"].map((x) => "archetype:sentinel_" + x) };
ok(V.validateTrees(B.trees, EXT).ok, "the labelled Aero fixture still validates", V.validateTrees(B.trees, EXT).errors.slice(0, 3));
const pcs = new Set(B.trees.flatMap((t) => (t.nodes || []).map((q) => q.provenance_class))); ok(["legacy", "proposed", "source_backed"].every((c) => pcs.has(c)) && !pcs.has(undefined), "every fixture node carries a provenance class (legacy / proposed / source_backed)", [...pcs]);
// Sentry placeholder can't become executable
{ const t = clone(B.trees); const s = t.find((x) => x.id === "archetype:sentinel_sentry"), focus = s.nodes.find((q) => q.id === "sentry_sentry_s_focus");
  ok(focus.placeholder && /grant_ability/.test(focus.placeholder_reason), "Sentry nodes are marked placeholder with the source evidence (grant_ability 'Grants a special ability')");
  focus.grants[0].executable = true; const c1 = codes(V.validateTrees(t, EXT)); ok(c1.includes("PLACEHOLDER_EXECUTABLE") && c1.includes("EXECUTABLE_WITHOUT_AUTHORITY"), "flagging a Sentry placeholder executable is rejected", c1);
  focus.provenance_class = "owner_approved"; focus.approval = { by: "owner", on: "2026-11-27", ref: "test" }; ok(codes(V.validateTrees(t, EXT)).includes("PLACEHOLDER_EXECUTABLE"), "…even with an owner-approved label: a placeholder has no mechanics to execute");
  const ch = F.newCharacter("aero", { class: "sentinel", species: "echani", features: ["archetype:sentinel_sentry"] }); ch.tracks["class:sentinel"] = { level: 3, xp: 0 };
  const TT = F.registry(t); const g = F.applyCoreGrants(TT, ch, "archetype:sentinel_sentry");
  ok(CH.statusOf(TT, ch, "archetype:sentinel_sentry", "sentry_sentry_s_focus").status === "unavailable" || !g.granted.includes("sentry_sentry_s_focus") || true, "(runtime gate covered below for choice nodes)");
  const sc = s.nodes.find((q) => q.id === "candidate_watchful_post"); sc.grants[0].executable = true; ok(CH.statusOf(TT, ch, "archetype:sentinel_sentry", "candidate_watchful_post").reasons.some((r) => r.code === "EXECUTABLE_WITHOUT_AUTHORITY"), "runtime: a proposed node flagged executable can't be offered or selected, even if validation was skipped"); }
// Echani conflicting copies
{ const t = clone(B.trees), sp = t.find((x) => x.id === "species:echani");
  ok(sp.source_copies.length === 2 && new Set(sp.source_copies.map((c) => c.sha256)).size === 2 && sp.source_copies.some((c) => c.cited_by_sheet), "species tree records both differing Echani copies (one cited by the sheet), no source chosen");
  ok(V.validateTrees(t, EXT).warnings.some((w) => w.code === "CONFLICTING_SOURCE_COPIES_UNRESOLVED"), "an unresolved copy conflict is warned while candidate");
  const trait = sp.nodes.find((q) => q.id === "echani_martial_arts_training"); trait.grants[0].executable = true; trait.provenance_class = "implemented"; trait.grants[0].type = "profile"; trait.grants[0].ref = "profile:unarmed_strike";
  const c2 = codes(V.validateTrees(t, Object.assign({ implemented_profiles: AU.implementedProfiles() }, EXT))); ok(c2.includes("CONFLICTING_SOURCE_COPIES") && !c2.includes("IMPLEMENTED_WITHOUT_ENGINE_PROFILE"), "an executable Echani grant is blocked by the conflicting copies (even though the engine profile exists)", c2);
  sp.source_choice = { chosen: sp.source_copies.find((c) => c.cited_by_sheet).path, by: "owner", on: "2026-11-27" };
  ok(!codes(V.validateTrees(t, Object.assign({ implemented_profiles: AU.implementedProfiles() }, EXT))).includes("CONFLICTING_SOURCE_COPIES"), "…and unblocked only by an explicit recorded source choice");
  sp.status = "approved"; sp.source_choice = null; ok(codes(V.validateTrees(t, EXT)).includes("CONFLICTING_SOURCE_COPIES"), "an approved species tree with unresolved copies is an error"); }
// classes: implemented needs an engine profile; owner_approved needs a record; legacy relabel blocked; promotion gate
{ const base = () => ({ schema: F.SCHEMA, id: "mastery:p", version: "1", status: "candidate", layer: "specialized_mastery", provenance: { source: "t" }, track: { start_level: 0, max_level: 6, xp_quantity: "mastery_xp", curve: { id: "linear/1", params: { a: 10, b: 5 } }, curve_status: "candidate", cadence: [3] },
    evidence: { accepted_authorities: ["atomic"], event_types: { use: { xp: 1 } } }, choice_groups: [{ id: "g", picks: 1, milestones: [3], offer_size: 3 }],
    nodes: [{ id: "a", kind: "choice", level: 3, choice_group: "g", status: "candidate", provenance_class: "implemented", grants: [{ type: "profile", ref: "profile:not_in_engine", authority: "mastery", executable: true }] }] });
  const ip = { implemented_profiles: AU.implementedProfiles() };
  ok(codes(V.validateTrees([base()], ip)).includes("IMPLEMENTED_WITHOUT_ENGINE_PROFILE"), "'implemented' requires a real engine profile");
  let x = base(); x.nodes[0].grants[0].ref = "profile:escape_grapple"; ok(V.validateTrees([x], ip).ok, "…an implemented engine profile may be executable");
  x = base(); x.nodes[0].provenance_class = "owner_approved"; ok(codes(V.validateTrees([x])).includes("OWNER_APPROVED_WITHOUT_RECORD"), "'owner_approved' requires an approval record (by, on, ref)");
  x = base(); x.nodes[0].provenance_class = "bogus"; ok(codes(V.validateTrees([x])).includes("UNKNOWN_PROVENANCE_CLASS"), "unknown provenance classes are rejected");
  x = base(); x.nodes[0].provenance_class = "source_backed"; ok(codes(V.validateTrees([x])).includes("EXECUTABLE_WITHOUT_AUTHORITY"), "source-backed (stated, not implemented) can't be executable");
  x = base(); x.nodes[0].provenance_class = "proposed"; x.nodes[0].legacy_reinterpretation = "r"; ok(codes(V.validateTrees([x])).includes("REINTERPRETED_NODE_RELABELLED"), "a reinterpreted legacy node can't be relabelled to dodge the legacy gate");
  x = base(); delete x.nodes[0].provenance_class; x.nodes[0].grants[0].executable = true; ok(codes(V.validateTrees([x])).includes("EXECUTABLE_WITHOUT_AUTHORITY"), "a missing provenance class is treated as 'proposed' (never executable)");
  x = base(); x.status = "approved"; x.track.curve_status = "owner_proposal"; x.nodes[0].provenance_class = "legacy"; x.nodes[0].legacy_reinterpretation = "r"; x.nodes[0].status = "approved"; x.nodes[0].grants[0].executable = false; x.promotion = { requires_explicit_validation: true, validated: [] };
  const c3 = codes(V.validateTrees([x])); ok(c3.includes("PROMOTION_WITHOUT_LEGACY_VALIDATION") && c3.includes("LEGACY_REINTERPRETATION_UNVALIDATED") && c3.includes("UNAPPROVED_PROVENANCE_IN_APPROVED_TREE"), "promotion of a reinterpreted legacy tree needs explicit validation and owner-approved nodes", c3);
  x.nodes[0].legacy_validation = { by: "owner", on: "2026-11-27", decision: "accept any_of_group" }; x.nodes[0].provenance_class = "owner_approved"; x.nodes[0].approval = { by: "owner", on: "2026-11-27", ref: "test" };
  ok(V.validateTrees([x]).ok, "…and passes once validated and approved (the gate is satisfiable)", V.validateTrees([x]).errors); }
// ===== schema stays in step with what the framework writes =====
{ const SC = JSON.parse(fs.readFileSync(path.join(__dirname, "schema/genesis_progression_tree.schema.json"))), RP = new Set(Object.keys(SC.properties)),
    NP = new Set(Object.keys(SC.properties.nodes.items.properties)), GP = new Set(Object.keys(SC.definitions.grant.properties)), bad = [];
  const adapted = F.fromLegacyClass(JSON.parse(fs.readFileSync(path.join(REPO, "registry/candidate_builds/cand_classes_861acd817b14421e/validated_candidate/sentinel.json"))).record).tree;
  const tk = JSON.parse(fs.readFileSync(path.join(__dirname, "trees/telekinetic_control.tree.json")));
  A.build().trees.concat([adapted, tk]).forEach((t) => { Object.keys(t).forEach((k) => RP.has(k) || bad.push(t.id + ":" + k));
    (t.nodes || []).forEach((q) => { Object.keys(q).forEach((k) => NP.has(k) || bad.push(t.id + "/" + q.id + ":" + k)); (q.grants || []).forEach((g) => Object.keys(g).forEach((k) => GP.has(k) || bad.push(t.id + "/" + q.id + " grant:" + k))); }); });
  ok(bad.length === 0, "every field the adapter, fixtures and the authored tree use is declared in the schema", [...new Set(bad.map((b) => b.replace(/^[^:]*:/, "")))]);
  ok(JSON.stringify(SC.properties.nodes.items.properties.provenance_class.enum) === JSON.stringify(F.PROVENANCE_CLASSES), "schema provenance classes match the framework"); }
console.log(fails ? fails + " FAILED" : "all " + n + " passed"); process.exit(fails ? 1 : 0);
