// CC-008.2: source reconciliation reports + the owner-approval / engine-implementation boundary.
const F = require("./framework.js"), V = require("./validate.js"), CH = require("./choices.js");
const fs = require("fs"), path = require("path"), crypto = require("crypto"), os = require("os"), cp = require("child_process");
let fails = 0, n = 0; const ok = (c, m, x) => { n++; console.log((c ? "ok " : "FAIL ") + m + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 400))); if (!c) fails++; };
const REPO = path.join(__dirname, "../.."), RD = path.join(__dirname, "reconciliation"), codes = (r) => r.errors.map((e) => e.code), clone = (x) => JSON.parse(JSON.stringify(x));
const load = (f) => JSON.parse(fs.readFileSync(path.join(RD, f + ".json"), "utf8")), NAMES = ["echani_copy_comparison", "sentinel_prereq_repairs", "scoundrel_evasion_trace", "sentry_reconciliation"];
const R = Object.fromEntries(NAMES.map((k) => [k, load(k)]));
// ===== reports are current, source-faithful and non-canonical =====
{ const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "recon_"));
  cp.execFileSync("python3", ["-I", path.join(__dirname, "tools/reconcile_sources.py")], { env: Object.assign({}, process.env, { RECON_OUT: tmp }), stdio: "ignore" });
  ok(NAMES.every((k) => fs.readFileSync(path.join(tmp, k + ".json"), "utf8") === fs.readFileSync(path.join(RD, k + ".json"), "utf8")), "the committed reconciliation reports regenerate byte-identically from the sources"); }
const zipSha = crypto.createHash("sha256").update(fs.readFileSync(path.join(REPO, "_QUARANTINE/hub_root_debris/SW5e_Data_Hub.zip"))).digest("hex");
ok(NAMES.every((k) => R[k].sources.archive.sha256 === zipSha), "every report pins the unchanged hub archive");
ok(NAMES.every((k) => R[k].sources.files.filter((f) => !f.path.includes("!")).every((f) => crypto.createHash("sha256").update(fs.readFileSync(path.join(REPO, f.path))).digest("hex") === f.sha256)), "every repo source a report read is unchanged since (sha256)");
ok(NAMES.every((k) => R[k].canonical === false && R[k].status === "candidate" && R[k].schema === "genesis-progression-reconciliation/0.1"), "every report is a non-canonical candidate in the reconciliation schema");
// ===== 1. Echani =====
{ const e = R.echani_copy_comparison, src = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures/aero_vertical/source_extract.json")));
  ok(e.copies.official.sha256 === src.echani.copies[0].sha256 && e.copies.backend.sha256 === src.echani.copies[1].sha256, "Echani copies are the same two hashes the fixture records");
  ok(e.baseline.copy === "official" && e.baseline.promoted === false && e.copies.official.cited_by_sheet && !e.copies.backend.cited_by_sheet, "official copy (cited by Aero's sheet) is the proposed baseline, not promoted");
  ok(e.fields.filter((f) => f.status === "backend_only").every((f) => f.proposed_disposition === "retain_for_review" && f.backend !== undefined), "no backend-only data is discarded: each is retained verbatim for review");
  ok(e.fields.filter((f) => f.status === "differs").every((f) => f.official !== undefined && f.backend !== undefined), "differing fields keep both values");
  ok(e.fields.every((f) => f.decision === null), "every disposition awaits a decision");
  ok(e.summary.mechanical_values_identical_where_both_define && e.fields.filter((f) => f.mechanical).map((f) => f.field).sort().join() === "innate_traits.[id=echani_combat_communication].corruption_transform,innate_traits.[id=echani_martial_arts_training].corruption_transform",
     "mechanically, the copies differ only by the backend's two corruption_transform hooks", e.fields.filter((f) => f.mechanical).map((f) => f.field)); }
// ===== 2. Sentinel repairs =====
{ const s = R.sentinel_prereq_repairs, audit = JSON.parse(fs.readFileSync(path.join(__dirname, "legacy/legacy_prereq_audit.json")));
  ok(s.repairs.map((r) => r.family + ":" + r.node).sort().join() === "candidate_build:sentinel_specialization_3,candidate_build:subclass_feature_7,hub_archive:sentinel_specialization_3,hub_archive:subclass_feature_7", "exactly Sentinel L3 and L7, in both source families");
  ok(s.repairs.every((r) => r.group_is_exclusive_choice && JSON.stringify([...r.original_prerequisites].sort()) === JSON.stringify(r.group_members) && JSON.stringify(r.proposed_requires) === JSON.stringify({ all: [{ any_of_group: r.group }] })), "each repair: the original list is the whole exclusive group → any_of_group");
  ok(s.repairs.every((r) => r.original_record && r.source_sha256 && r.status === "candidate" && r.legacy_validation.by === null), "original record and source hash kept; repair unsigned and candidate");
  const ad = audit.records.filter((r) => r.id === "sentinel").flatMap((r) => r.reinterpreted.map((q) => JSON.stringify(q.interpretation)));
  ok(s.repairs.every((r) => ad.includes(JSON.stringify(r.proposed_requires))), "repairs agree with the CC-008.1 adapter's interpretation");
  ok(s.not_in_scope.count === 38 && !s.not_in_scope.reinterpreted_trees_not_repaired.some((x) => /:sentinel$/.test(x)), "the other 38 reinterpreted trees are listed, untouched and not approved");
  // applying the repair does not make the node executable or promotable: it is still an unvalidated legacy reinterpretation
  const rec = JSON.parse(fs.readFileSync(path.join(REPO, "registry/candidate_builds/cand_classes_861acd817b14421e/validated_candidate/sentinel.json"))).record;
  const t = F.fromLegacyClass(rec).tree, node = F.nodeOf(t, "subclass_feature_7");
  ok(JSON.stringify(node.requires) === JSON.stringify(s.repairs.find((r) => r.node === "subclass_feature_7").proposed_requires) && !node.legacy_validation, "the adapted tree already carries the repair, still without legacy_validation");
  Object.assign(t, { status: "approved", track: Object.assign(t.track, { curve_status: "owner_proposal" }) }); t.nodes.forEach((q) => (q.status = "approved"));
  ok(codes(V.validateTrees([t], { external_tracks: [] })).includes("PROMOTION_WITHOUT_LEGACY_VALIDATION"), "the candidate repair cannot be promoted without an explicit legacy_validation"); }
// ===== 3. Scoundrel =====
{ const s = R.scoundrel_evasion_trace;
  ok(/genuine source gap/.test(s.finding.verdict) && s.finding.searched.filter((x) => "defines_evasion_7" in x).every((x) => !x.defines_evasion_7 && !x.evasion_like_nodes.length), "no searched Scoundrel/Smuggler/Spy tree defines evasion_7 → reported as a genuine source gap");
  ok(s.finding.searched.length >= 10 && s.finding.searched.some((x) => /feature_registry/.test(x.source) && x.references_to_evasion_7.length >= 1 && !x.defines_evasion_feature), "the feature registry only references evasion_7; it defines no Evasion feature");
  ok(s.external_evidence.some((x) => /Uncanny Dodge.*Evasion.*Ability Score Improvement/.test(x.excerpt || "")) && s.external_evidence.some((x) => /instead take no damage/.test(x.excerpt || "")), "external evidence: SW5e Operative table (Evasion at 7) and the Evasion rule text");
  ok(s.alternatives.map((a) => a.id).join() === "A_point_at_level_7_node,B_add_evasion_7_node,C_leave_unrepaired" && s.alternatives.find((a) => a.id[0] === "B").proposed_node.placeholder === true && s.decision === null, "three alternatives, the added-node option is a placeholder, no decision taken"); }
// ===== 4. Sentry =====
{ const s = R.sentry_reconciliation;
  ok(s.specialization_features.length === 5 && s.specialization_features.every((f) => f.placeholder && f.issues.some((i) => i.code === "PLACEHOLDER_MECHANICS")), "all five specialization feature files are grant_ability placeholders");
  ok(s.cross_reference.overlap.length === 0 && s.cross_reference.specialization_features_without_tree_node.length === 5 && s.cross_reference.tree_nodes_without_feature_file.length === 5, "specialization_features and progression_tree name disjoint sets (5 vs 5, no overlap)");
  ok(s.progression_tree.every((q) => q.issues.some((i) => i.code === "NO_STRUCTURED_MECHANICS")) && s.progression_tree.filter((q) => q.issues.some((i) => i.code === "EFFECT_CONTRADICTS_DESCRIPTION")).length === 4, "every tree node lacks structured mechanics; four contradict their own descriptions");
  ok(s.missing_mechanical_definitions.length === 10, "ten missing mechanical definitions listed");
  ok(JSON.stringify(s.cadence.sentry_progression_tree) === "[3,7,11,15,18]" && JSON.stringify(s.cadence.sw5e_phb_calling_features) === "[3,7,13,18]" && JSON.stringify(s.cadence.genesis_archetype_cadence) === "[3,6,9,12,15,18]", "cadences: source tree 3/7/11/15/18, SW5e PHB 3/7/13/18, Genesis 3/6/9/12/15/18");
  ok(JSON.stringify(s.cadence.aligned_with_genesis) === "[3,15,18]" && JSON.stringify(s.cadence.genesis_milestones_without_source_feature) === "[6,9,12]", "aligned at 3/15/18; Genesis milestones 6/9/12 have no source feature");
  ok(s.design_session_inputs.chooses_final_abilities === false, "the packet does not choose Sentry's abilities"); }
// ===== 5. owner approval ≠ executable implementation =====
{ const ep = F.engineProfiles(); ok(Object.keys(ep).length > 0 && ep.unarmed_strike && ep.unarmed_strike.valid, "engine profiles are read from the combat catalog");
  const base = (pc, ref) => ({ schema: F.SCHEMA, id: "mastery:b", version: "1", status: "candidate", layer: "specialized_mastery", provenance: { source: "t" },
    track: { start_level: 0, max_level: 6, xp_quantity: "mastery_xp", curve: { id: "linear/1", params: { a: 10, b: 5 } }, curve_status: "candidate", cadence: [3] },
    evidence: { accepted_authorities: ["atomic"], event_types: { use: { xp: 1 } } }, choice_groups: [{ id: "g", picks: 1, milestones: [3], offer_size: 3 }],
    nodes: [{ id: "a", kind: "choice", level: 3, choice_group: "g", status: "candidate", provenance_class: pc, approval: { by: "owner", on: "2026-11-27", ref: "design-session" }, grants: [{ type: ref ? "profile" : "feature", ref: ref || "feature:sentry_watch", authority: "mastery", executable: true }] }] });
  const at = (t) => F.executableBlockers(t, t.nodes[0], t.nodes[0].grants[0]).map((b) => b.code);
  ok(at(base("owner_approved")).includes("APPROVED_DESIGN_NOT_IMPLEMENTED"), "owner-approved design with no engine profile is not executable (no opts: runtime default)");
  ok(at(base("owner_approved", "profile:not_a_real_profile")).includes("APPROVED_DESIGN_NOT_IMPLEMENTED"), "…nor with a profile name the engine doesn't have");
  ok(at(base("owner_approved", "profile:unarmed_strike")).length === 0, "owner-approved + a valid live engine profile is executable");
  ok(at(base("implemented", "profile:not_a_real_profile")).includes("IMPLEMENTED_WITHOUT_ENGINE_PROFILE"), "'implemented' is checked against the engine by default, without opts");
  const sp = Object.keys(ep).find((k) => ep[k].valid && !F.LIVE_PROFILE_STATUSES.includes(ep[k].status));
  ok(sp && at(base("owner_approved", "profile:" + sp)).includes("ENGINE_PROFILE_SANDBOX_ONLY") && F.executableBlockers(base("owner_approved", "profile:" + sp), base("owner_approved").nodes[0], { type: "profile", ref: "profile:" + sp, executable: true }, { sandbox: true }).length === 0,
     "a sandbox_proposal profile is executable only in the sandbox", sp);
  const T = F.registry([base("owner_approved")]), ch = F.newCharacter("x", { class: "sentinel" }); ch.tracks["mastery:b"] = { level: 3, xp: 0 };
  ok(CH.statusOf(T, ch, "mastery:b", "a").reasons.some((r) => r.code === "APPROVED_DESIGN_NOT_IMPLEMENTED"), "runtime: an approved-but-unimplemented node can't be offered or selected");
  ok(codes(V.validateTrees([base("owner_approved")])).includes("APPROVED_DESIGN_NOT_IMPLEMENTED"), "validator reports the same boundary");
  const des = clone(base("owner_approved")); des.nodes[0].grants[0].executable = false; ok(V.validateTrees([des]).ok, "approved design content without executable grants remains valid content (design is allowed, play is not)"); }
console.log(fails ? fails + " FAILED" : "all " + n + " passed"); process.exit(fails ? 1 : 0);
