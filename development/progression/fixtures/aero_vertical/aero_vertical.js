// Aero Echani + Sentinel vertical fixture (CC-008 F) — SANDBOX. Builds the trees from real sources where they exist and labels
// every gap 'candidate'. Never reads or writes Aero's runtime sheet beyond hashing it in tests.
"use strict";
const path = require("path"), fs = require("fs"), F = require("../../framework.js"), D = require("../../disciplines.js"), CAND = require("../../candidates/class_level_curves.json");
const POLICY = require("../../policies/discipline_allocation.v0.1.json"), SRC = require("./source_extract.json");
const REPO = path.join(__dirname, "../../../..");
const g = (type, ref, authority, extra) => Object.assign({ type, ref, authority }, extra || {});
const cand = (id, level, group, ref, extra) => { const { authority, ...rest } = extra || {};   // authority belongs on the grant, not the node
  return Object.assign({ id, name: id.replace(/^candidate_/, "").replace(/_/g, " "), kind: "choice", level, choice_group: group, status: "candidate",
  provenance: "CC-008 F candidate content — NOT owner-approved", provenance_class: "proposed", grants: [g("feature", "feature:" + id, authority || "mastery")] }, rest); };
function build() {
  // ---- 1. class:sentinel from the real candidate record (legacy adapter) + labelled candidate thresholds ----
  const rec = JSON.parse(fs.readFileSync(path.join(REPO, "registry/candidate_builds/cand_classes_861acd817b14421e/validated_candidate/sentinel.json"))).record;
  const { tree: cls, notes } = F.fromLegacyClass(rec, { source: "registry/candidate_builds/cand_classes_861acd817b14421e/validated_candidate/sentinel.json (candidate) ← SW5e_Data_Hub backend/classes/sentinel.yml",
    curve: CAND.curves[0].track.curve, curve_status: "candidate" });
  cls.track.cadence = [2, 3, 4, 8, 12, 16, 19];
  cls.evidence = { accepted_authorities: ["atomic"], event_types: { encounter_completed: { xp: 450, requires_facts: ["encounter_id"] } }, never_from: ["narration", "client assertion"] };
  cls.restrictions = { classes: ["sentinel"] };
  // expand the single legacy subclass_entry into one archetype option per Sentinel subclass source file (offer all: the player must see every archetype)
  const entry = F.nodeOf(cls, "sentinel_specialization_3"), groupId = "sentinel_specialization";
  cls.nodes = cls.nodes.filter((n) => n.id !== "sentinel_specialization_3");
  SRC.sentinel_subclasses.forEach((s) => { const sid = String(s.resolved_id).replace(/^sentinel_/, "");
    cls.nodes.push({ id: "archetype_" + sid, name: s.name, kind: "subclass_entry", level: 3, choice_group: groupId, status: "candidate", requires: entry.requires, provenance_class: "legacy",
                     legacy_reinterpretation: entry.legacy_reinterpretation, legacy_prerequisites: entry.legacy_prerequisites,
                     provenance: s.member + (s.ids_in_file.length > 1 ? " (file defines id " + s.ids_in_file.length + "×: " + s.ids_in_file.join(", ") + ")" : ""), grants: [g("track_unlock", "archetype:sentinel_" + sid, "class")] }); });
  const grp = cls.choice_groups.find((x) => x.id === groupId); grp.offer_size = SRC.sentinel_subclasses.length;
  cls.nodes.forEach((n) => { if (n.requires && n.requires.all) n.requires.all = n.requires.all.map((t) => t === "sentinel_specialization_3" ? { any_of_group: groupId } : t); });
  // ---- 2. archetype:sentinel_sentry — prospective until selected; source core nodes + labelled candidate specialty choices (3/6/9…) ----
  const sentry = { schema: F.SCHEMA, id: "archetype:sentinel_sentry", version: "0.1-fixture", status: "candidate", layer: "archetype", registry_urid: "subclass_sentry",
    restrictions: { classes: ["sentinel"], requires_features: ["archetype:sentinel_sentry"] },
    provenance: { source: SRC.sentry.member + " (hub, candidate; registry lane global_validated, tag 'planned', scope meridian_reach)", notes: "Aero's sheet: subclass_plan Sentry (prospective)" },
    track: { start_level: 3, xp_quantity: "none", driven_by: "class:sentinel", curve: { id: "none/1" }, cadence: [3, 6, 9, 12, 15, 18] },
    choice_groups: [{ id: "sentry_specialties", picks: 1, offer_size: 3, exclusive: false, milestones: [3, 6, 9] }],
    nodes: SRC.sentry.progression_tree.map((x) => ({ id: "sentry_" + String(x.feature_id).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, ""), name: x.feature_id, kind: "core_grant", level: x.level, status: "candidate",
      provenance_class: "legacy", placeholder: true, placeholder_reason: "Sentry source mechanics are placeholder or contradictory: " + SRC.sentry.feature_file_sample.member + " has effect " + JSON.stringify(SRC.sentry.feature_file_sample.mechanics[0].effect) + " (\"" + SRC.sentry.feature_file_sample.mechanics[0].description + "\"); tree effect fields contradict their descriptions (CC-008 A §2.3)",
      provenance: SRC.sentry.member + " progression_tree " + x.node_id + " (description only; effect fields contradict it — CC-008 A §2.3)", grants: [g("feature", "feature:sentry_" + String(x.feature_id).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, ""), "archetype")] }))
      .concat([cand("candidate_watchful_post", 3, "sentry_specialties", null, { authority: "archetype" }), cand("candidate_guardian_reflex", 3, "sentry_specialties", null, { authority: "archetype" }),
               cand("candidate_threat_read", 3, "sentry_specialties", null, { authority: "archetype" }),
               cand("candidate_unbroken_watch", 6, "sentry_specialties", null, { authority: "archetype", upgrades: "candidate_watchful_post", requires: { all: ["candidate_watchful_post"] } }),
               cand("candidate_echani_bulwark", 9, "sentry_specialties", null, { authority: "archetype", requires: { all: [{ node: "species:echani/echani_combat_discipline" }, { track: "mastery:echani_strike", level: 3 }] } })]) };
  // ---- 3. species:echani — source traits at L1, source tiers at 5/10/15/20 (free text → candidate, not executable) ----
  const tierNode = (L) => ({ id: "echani_tier_" + L, name: "Echani tier " + L, kind: "core_grant", level: L, status: "candidate", provenance_class: "source_backed", placeholder: true, placeholder_reason: "free-text mechanical_benefit, not an executable effect", provenance: SRC.echani.member + " species_progression.level_" + L + " — free-text mechanical_benefit: \"" + SRC.echani.tiers["level_" + L] + "\" (not executable; needs structured effect)",
    grants: [g("feature", "feature:candidate_echani_tier_" + L, "species")] });
  const species = { schema: F.SCHEMA, id: "species:echani", version: "0.1-fixture", status: "candidate", layer: "species", registry_urid: "species_echani", restrictions: { species: ["echani"] },
    provenance: { source: SRC.echani.member + " (cited by api_bridge/gm/aero_character_runtime.yml)", notes: "Driven by class level here — an owner decision (CC-008 A §4.4)" },
    track: { start_level: 1, xp_quantity: "none", driven_by: "class:sentinel", curve: { id: "none/1" }, cadence: [5, 10, 15, 20] },
    source_copies: SRC.echani.copies.map((c) => ({ path: SRC.echani.member.replace(/official_species_playable\/echani\.yml$/, "") + c.member.replace(/^SW5e_Data_Hub\//, ""), sha256: c.sha256, progression_sha256: c.species_progression_sha256, cited_by_sheet: c.cited_by_sheet })),
    source_choice: null,
    nodes: SRC.echani.innate_traits.map((t) => ({ id: "echani_" + t.toLowerCase().replace(/[^a-z0-9]+/g, "_"), name: t, kind: "core_grant", level: 1, status: "candidate", provenance_class: "source_backed", provenance: SRC.echani.member + " innate_traits", grants: [g("feature", "feature:" + t.toLowerCase().replace(/[^a-z0-9]+/g, "_"), "species")] }))
      .concat([5, 10, 15, 20].map(tierNode)) };
  // ---- 4. mastery:echani_strike — an independent specialized mastery (candidate curve) with three-choice techniques ----
  const strike = { schema: F.SCHEMA, id: "mastery:echani_strike", version: "0.1-fixture", status: "candidate", layer: "specialized_mastery", restrictions: { requires_features: ["feature:martial_arts_training"] },
    provenance: { source: "CC-008 F fixture; anchored to the Echani Martial Arts Training species feature and the unarmed_strike/flow_strike profiles" },
    track: { start_level: 0, max_level: 20, xp_quantity: "mastery_xp", curve: { id: "quadratic/1", params: { a: 10, b: 5, c: 1 } }, curve_status: "candidate", cadence: [3, 6, 9, 12, 15, 18] },
    evidence: { accepted_authorities: ["atomic", "atomic_exploration"], event_types: { observation: { xp: 1 } }, never_from: ["narration", "client assertion"] },
    choice_groups: [{ id: "echani_strike_techniques", picks: 1, offer_size: 3, exclusive: false, milestones: [3, 6, 9] }],
    nodes: [cand("candidate_quick_followup", 3, "echani_strike_techniques"), cand("candidate_pressure_point", 3, "echani_strike_techniques"), cand("candidate_low_sweep", 3, "echani_strike_techniques"),
            cand("candidate_flowing_chain", 6, "echani_strike_techniques", null, { upgrades: "candidate_quick_followup", requires: { all: ["candidate_quick_followup"] } }),
            cand("candidate_sentinel_counterbalance", 6, "echani_strike_techniques", null, { requires: { all: [{ node: "class:sentinel/sentinel_balance_1" }, { node: "species:echani/echani_martial_arts_training" }] } })] };
  // ---- 5. incompatible trees (for rejection tests) ----
  const operativeArch = { schema: F.SCHEMA, id: "archetype:operative_fixture", version: "t", status: "candidate", layer: "archetype", restrictions: { classes: ["operative"] }, provenance: { source: "fixture" },
    track: { start_level: 3, xp_quantity: "none", driven_by: "class:sentinel", curve: { id: "none/1" } }, choice_groups: [{ id: "op", picks: 1, milestones: [3], offer_size: 3 }], nodes: [cand("candidate_op_trick", 3, "op", null, { authority: "archetype" })] };
  const wookiee = { schema: F.SCHEMA, id: "species:wookiee_fixture", version: "t", status: "candidate", layer: "species", restrictions: { species: ["wookiee"] }, provenance: { source: "Contracts/wookiee_progression_example.yml (example)" },
    track: { start_level: 1, xp_quantity: "none", driven_by: "class:sentinel", curve: { id: "none/1" } }, nodes: [{ id: "feral_strength", kind: "core_grant", level: 1, status: "candidate", provenance_class: "proposed", grants: [g("feature", "feature:feral_strength", "species")] }] };
  const policyTrees = D.treesForPolicy(POLICY).filter((t) => t.id !== "mastery:echani_strike");
  return { trees: [cls, sentry, species, strike, operativeArch, wookiee].concat(policyTrees), adapterNotes: notes, policy: POLICY };
}
module.exports = { build, REPO };
