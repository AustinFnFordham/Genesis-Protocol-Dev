// CC-008 F: Aero Echani + Sentinel vertical prototype (sandbox). Writes fixtures/aero_vertical/evidence.json.
const F = require("./framework.js"), CH = require("./choices.js"), D = require("./disciplines.js"), V = require("./validate.js"), A = require("./fixtures/aero_vertical/aero_vertical.js");
const fs = require("fs"), path = require("path"), crypto = require("crypto");
let fails = 0, n = 0; const ok = (c, m, x) => { n++; console.log((c ? "ok " : "FAIL ") + m + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 400))); if (!c) fails++; };
const SHEET = path.join(A.REPO, "api_bridge/gm/aero_character_runtime.yml"), sheetHash = () => crypto.createHash("sha256").update(fs.readFileSync(SHEET)).digest("hex"), h0 = sheetHash();
const B = A.build(), T = F.registry(B.trees), OTHER_ARCH = ["diplomat", "shadow_guard", "artisan", "investigator", "racer", "shadow", "shien_expert"].map((x) => "archetype:sentinel_" + x);
ok(V.validateTrees(B.trees, { external_tracks: OTHER_ARCH }).ok, "every fixture tree validates (sources adapted, gaps labelled candidate)");
ok(B.adapterNotes.filter((q) => /any_of_group/.test(q.note)).length === 2, "the legacy Sentinel L3/L7 reinterpretations are carried into the fixture as recorded notes");
// The authoritative event history for this synthetic run. Replaying it must reproduce the state exactly.
const OWN = ["unarmed_strike", "flow_strike", "grapple", "escape_grapple", "release_grapple", "saber_strike", "speak", "move"];
const history = [];
const E_ = (id) => ({ event_id: id, authority: "atomic", committed: true, validated: true, type: "encounter_completed", actor: "aero", facts: { encounter_id: id } });
const OB = (i, scene) => ({ observation_id: "strike_" + i, actor: "aero", pid: i % 3 === 0 ? "flow_strike" : "unarmed_strike", authority: "atomic", committed: true, validated: true, scene, facts: {} });
function run(hist) {
  let ch = F.newCharacter("aero", { class: "sentinel", species: "echani" }); ch.tracks["class:sentinel"] = { level: 1, xp: 0 }; const log = [];
  const coreAll = () => ["class:sentinel", "species:echani", "archetype:sentinel_sentry"].forEach((t) => { if (!F.trackAllowed(T[t], ch).length && F.levelOfTrack(T, ch, t) >= T[t].track.start_level) ch = F.applyCoreGrants(T, ch, t).state; });
  coreAll();
  for (const h of hist) {
    if (h.kind === "class_xp") { const r = F.awardXp(T, ch, "class:sentinel", E_(h.id)); if (!r.ok) throw new Error(r.code); ch = r.state; coreAll(); }
    else if (h.kind === "obs") { ch = D.apply(T, ch, B.policy, OB(h.i, h.scene), OWN).state; }
    else if (h.kind === "pick") { const o = CH.offer(T, ch, h.track, h.group, h.milestone); ch = o.state; const r = CH.select(T, ch, o.offer.id, h.node); if (!r.ok) throw new Error(h.node + " " + r.code + " " + JSON.stringify(r.status || "")); ch = r.state; coreAll(); log.push({ offer: o.offer.presented, picked: h.node, milestone: h.milestone, track: h.track }); }
  }
  return { ch, log };
}
// ---- L1: species and class feature sources ----
let { ch } = run([]);
const sheetText = fs.readFileSync(SHEET, "utf8");
ok(["feature:force_connection", "feature:sentinel_balance", "feature:martial_arts_training", "feature:combat_discipline", "feature:combat_communication"].every((f) => ch.features.includes(f)), "L1: class (Force Connection, Sentinel Balance) and species (three Echani traits) features granted from their sources", ch.features);
ok(["Force Connection", "Sentinel Balance", "Martial Arts Training", "Combat Discipline"].every((nm) => sheetText.includes(nm)), "…and they match the names on Aero's runtime sheet");
const prov = ch.receipts.filter((r) => r.automatic).map((r) => r.authority); ok(prov.includes("class") && prov.includes("species") && ch.receipts.every((r) => F.verifyReceipt(r)), "each grant records its authority (class / species) in a sealed receipt");
ok(CH.statusOf(T, ch, "archetype:sentinel_sentry", "candidate_watchful_post").status === "unavailable" && CH.statusOf(T, ch, "archetype:sentinel_sentry", "candidate_watchful_post").reasons.some((r) => r.code === "FEATURE"), "Sentry is prospective: its track is unavailable until it is selected");
// ---- class level progression, archetype entry ----
history.push({ kind: "class_xp", id: "enc_001" }); ({ ch } = run(history));
ok(F.levelOfTrack(T, ch, "class:sentinel") === 2 && F.trackState(ch, "mastery:echani_strike").xp === 0, "class XP (candidate thresholds) → class level 2; no mastery XP moved");
let o2 = CH.offer(T, ch, "class:sentinel", "sentinel_focus_level_2", 2).offer; ok(o2.presented.length === 2 && o2.fewer_than_offer_size, "L2 focus: the source has two options, so two are offered (no filler)");
history.push({ kind: "pick", track: "class:sentinel", group: "sentinel_focus_level_2", milestone: 2, node: "investigation_focus_2" }, { kind: "class_xp", id: "enc_002" });
({ ch } = run(history));
const o3 = CH.offer(T, ch, "class:sentinel", "sentinel_specialization", 3).offer;
ok(F.levelOfTrack(T, ch, "class:sentinel") === 3 && o3.presented.length === 8 && o3.presented.includes("archetype_sentry"), "L3 archetype entry: all eight Sentinel archetypes from the source are offered (the legacy L3 requirement is satisfiable with ONE focus)");
history.push({ kind: "pick", track: "class:sentinel", group: "sentinel_specialization", milestone: 3, node: "archetype_sentry" }); ({ ch } = run(history));
ok(ch.features.includes("archetype:sentinel_sentry") && F.levelOfTrack(T, ch, "archetype:sentinel_sentry") === 3 && ch.held["archetype:sentinel_sentry/sentry_sentry_s_focus"], "choosing Sentry unlocks its track (driven by class level 3) and its L3 source feature (Sentry's Focus)");
ok(CH.statusOf(T, ch, "class:sentinel", "archetype_investigator").status === "unavailable", "the other archetypes close (exclusive)");
const o3s = CH.offer(T, ch, "archetype:sentinel_sentry", "sentry_specialties", 3).offer; ok(o3s.presented.length === 3 && o3s.presented.every((x) => /^candidate_/.test(x)), "Sentry L3 specialty milestone: three labelled candidate upgrades");
history.push({ kind: "pick", track: "archetype:sentinel_sentry", group: "sentry_specialties", milestone: 3, node: "candidate_watchful_post" });
// ---- an independent specialized mastery + shared Discipline XP ----
for (let i = 1; i <= 50; i++) history.push({ kind: "obs", i, scene: "scene_" + Math.ceil(i / 5) });
({ ch } = run(history));
ok(F.trackState(ch, "mastery:echani_strike").level === 3 && F.trackState(ch, "mastery:echani_strike").xp === 50 && F.levelOfTrack(T, ch, "class:sentinel") === 3, "50 committed Echani strikes → Echani Strike mastery 3 (50 XP); class level is still 3");
ok(F.trackState(ch, "discipline:martial_arts").xp === 50, "each strike also credited the shared Martial Arts discipline (one bounded allocation per observation)");
const o3m = CH.offer(T, ch, "mastery:echani_strike", "echani_strike_techniques", 3).offer;
ok(o3m.presented.length === 3 && ["candidate_quick_followup", "candidate_pressure_point", "candidate_low_sweep"].every((x) => o3m.presented.includes(x)), "three valid upgrade candidates at mastery 3");
history.push({ kind: "pick", track: "mastery:echani_strike", group: "echani_strike_techniques", milestone: 3, node: "candidate_quick_followup" }); ({ ch } = run(history));
ok(ch.held["mastery:echani_strike/candidate_quick_followup"] && ch.features.includes("feature:candidate_quick_followup"), "one recorded choice");
// ---- future prerequisite-dependent and cross-tree unlocks ----
ok(CH.statusOf(T, ch, "mastery:echani_strike", "candidate_flowing_chain").reasons.map((r) => r.code).join() === "LEVEL", "Flowing Chain (needs Quick Follow-up + mastery 6) is locked only by level now");
ok(CH.statusOf(T, ch, "archetype:sentinel_sentry", "candidate_echani_bulwark").reasons.map((r) => r.code).join() === "LEVEL", "cross-tree Echani Bulwark (species trait + mastery 3) is locked only by archetype level 9");
for (let i = 51; i <= 190; i++) history.push({ kind: "obs", i, scene: "scene_" + Math.ceil(i / 5) }); ({ ch } = run(history));
ok(F.trackState(ch, "mastery:echani_strike").level === 6, "190 XP → mastery 6");
ok(CH.statusOf(T, ch, "mastery:echani_strike", "candidate_flowing_chain").status === "eligible" && CH.statusOf(T, ch, "mastery:echani_strike", "candidate_sentinel_counterbalance").status === "eligible", "at mastery 6: the upgrade chain and the cross-tree class+species technique are eligible");
const noBal = JSON.parse(JSON.stringify(ch)); delete noBal.held["class:sentinel/sentinel_balance_1"];
ok(CH.statusOf(T, noBal, "mastery:echani_strike", "candidate_sentinel_counterbalance").reasons.some((r) => r.node === "class:sentinel/sentinel_balance_1"), "cross-tree requirement: without the class Sentinel Balance node it is locked");
// ---- rejections: unearned, incompatible ----
ok(D.apply(T, ch, B.policy, { observation_id: "tk1", actor: "aero", pid: "minor_telekinesis", authority: "narration", committed: true, validated: true }, OWN.concat(["minor_telekinesis"])).reason === "UNTRUSTED_AUTHORITY", "a narrated Telekinesis use earns nothing");
ok(D.apply(T, ch, B.policy, { observation_id: "tk2", actor: "aero", pid: "minor_telekinesis", authority: "atomic", committed: true, validated: true }, OWN).reason === "UNLEARNED_CAPABILITY", "a committed use of a capability this fixture doesn't grant earns nothing");
ok(CH.statusOf(T, ch, "archetype:operative_fixture", "candidate_op_trick").reasons[0].code === "CLASS_RESTRICTED", "an Operative archetype is refused for a Sentinel");
ok(F.trackAllowed(T["species:wookiee_fixture"], ch)[0].code === "SPECIES_RESTRICTED", "a Wookiee heritage is refused for an Echani");
const inv = F.newCharacter("rival", { class: "sentinel", species: "echani" }); inv.tracks["class:sentinel"] = { level: 3, xp: 0 }; inv.features.push("archetype:sentinel_investigator");
ok(CH.statusOf(T, inv, "archetype:sentinel_sentry", "candidate_watchful_post").status === "unavailable", "a Sentinel who chose Investigator can't take Sentry options");
ok(F.awardXp(T, ch, "class:sentinel", Object.assign(E_("enc_x"), { facts: {} })).code === "MISSING_FACTS" && F.awardXp(T, ch, "class:sentinel", Object.assign(E_("enc_y"), { authority: "client" })).code === "UNTRUSTED_AUTHORITY", "class XP needs a committed encounter fact; client claims earn nothing");
// ---- replay safety ----
const r1 = run(history), r2 = run(history); ok(JSON.stringify(r1.ch) === JSON.stringify(r2.ch), "replaying the full event history reproduces the state byte for byte");
const dupHist = history.concat(history.filter((h) => h.kind !== "pick")); const r3 = run(dupHist);
ok(F.trackState(r3.ch, "mastery:echani_strike").xp === F.trackState(r1.ch, "mastery:echani_strike").xp && r3.ch.ledger.class_xp === r1.ch.ledger.class_xp, "replaying duplicated events awards nothing extra");
ok(sheetHash() === h0, "Aero's live runtime sheet is byte-identical (never modified)");
// evidence
const fin = r1.ch; fs.writeFileSync(path.join(__dirname, "fixtures/aero_vertical/evidence.json"), JSON.stringify({ status: "sandbox evidence — candidate content, not canonical", class_level: F.levelOfTrack(T, fin, "class:sentinel"), class_xp: fin.ledger.class_xp,
  tracks: fin.tracks, features: fin.features, picks: r1.log, receipts: fin.receipts.length, sheet_sha256_unchanged: h0 }, null, 1) + "\n");
console.log(fails ? fails + " FAILED" : "all " + n + " passed"); process.exit(fails ? 1 : 0);
