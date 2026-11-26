// CC-008 D: three-choice milestone system (headless, server-authoritative).
const F = require("./framework.js"), CH = require("./choices.js"), V = require("./validate.js");
let fails = 0, n = 0; const ok = (c, m, x) => { n++; console.log((c ? "ok " : "FAIL ") + m + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 400))); if (!c) fails++; };
const node = (id, level, group, extra) => Object.assign({ id, kind: "choice", level, choice_group: group, status: "candidate", grants: [{ type: "feature", ref: "feature:" + id, authority: "mastery" }] }, extra || {});
const tree = { schema: F.SCHEMA, id: "mastery:blade", version: "1", status: "candidate", layer: "specialized_mastery", provenance: { source: "CC-008 D fixture (candidate content)" },
  restrictions: { classes: ["sentinel", "guardian"] },
  track: { start_level: 0, max_level: 18, xp_quantity: "mastery_xp", curve: { id: "linear/1", params: { a: 10, b: 5 } }, curve_status: "candidate", cadence: [3, 6, 9, 12, 15, 18] },
  evidence: { accepted_authorities: ["atomic"], event_types: { strike: { xp: 1 } } },
  choice_groups: [{ id: "forms", picks: 1, offer_size: 3, exclusive: false, milestones: [3, 6, 9] }, { id: "stance", picks: 1, offer_size: 3, exclusive: true, milestones: [6] }],
  nodes: [node("guard", 3, "forms"), node("flow", 3, "forms"), node("press", 3, "forms"), node("lunge", 3, "forms"), node("sweep", 6, "forms"),
          node("guard_ii", 6, "forms", { upgrades: "guard", requires: { all: ["guard"] } }),
          node("hybrid_cut", 9, "forms", { requires: { all: [{ node: "mastery:grapple/hold" }, "flow"] } }),
          node("shield_stance", 6, "stance"), node("storm_stance", 6, "stance", { conflicts_with: ["shield_stance"] }), node("echani_only", 6, "forms", { requires: { all: [{ feature: "species:echani" }] } })] };
const other = { schema: F.SCHEMA, id: "mastery:grapple", version: "1", status: "candidate", layer: "specialized_mastery", provenance: { source: "fixture" },
  track: { start_level: 0, max_level: 18, xp_quantity: "mastery_xp", curve: { id: "linear/1", params: { a: 10, b: 5 } }, curve_status: "candidate", cadence: [3] },
  evidence: { accepted_authorities: ["atomic"], event_types: { grapple: { xp: 1 } } }, choice_groups: [{ id: "g", picks: 1, milestones: [3], offer_size: 3 }], nodes: [node("hold", 3, "g")] };
const T = F.registry([tree, other]); ok(V.validateTrees([tree, other]).ok, "fixture trees validate", V.validateTrees([tree, other]).errors);
const at = (lvl, opts) => { const c = F.newCharacter("aero", Object.assign({ class: "sentinel", species: "echani", features: ["species:echani"] }, opts || {})); c.tracks["mastery:blade"] = { level: lvl, xp: 0 }; return c; };
// ---- offers ----
let ch = at(3); let o = CH.offer(T, ch, "mastery:blade", "forms", 3); ch = o.state;
ok(o.ok && o.offer.presented.length === 3 && new Set(o.offer.presented).size === 3, "L3: three distinct eligible candidates presented (4 eligible exist)");
ok(o.offer.presented.every((x) => CH.statusOf(T, ch, "mastery:blade", x).status === "eligible"), "every presented candidate is eligible on the character's actual state");
ok(o.offer.statuses.find((s) => s.node === "sweep").status === "locked" && o.offer.statuses.find((s) => s.node === "sweep").reasons[0].code === "LEVEL", "higher-level options show as locked with a reason");
const again = CH.offer(T, ch, "mastery:blade", "forms", 3); ok(again.existing && again.offer.hash === o.offer.hash, "the same milestone yields the same offer (deterministic, stored once)");
const other_char = F.newCharacter("kass", { class: "sentinel" }); other_char.tracks["mastery:blade"] = { level: 3, xp: 0 }; const o2 = CH.offer(T, other_char, "mastery:blade", "forms", 3).offer;
ok(o2.presentation.rule === o.offer.presentation.rule && o2.statuses.filter((s) => s.status === "eligible").length >= 3, "presentation may rotate per character (roguelike feel), legality does not", [o.offer.presented, o2.presented]);
ok(CH.offer(T, at(2), "mastery:blade", "forms", 3).code === "MILESTONE_NOT_REACHED" && CH.offer(T, ch, "mastery:blade", "forms", 4).code === "NOT_A_MILESTONE_OF_GROUP", "no offer before the milestone or at a non-milestone level");
// ---- selection ----
const pick = o.offer.presented.includes("guard") ? "guard" : o.offer.presented[0];
const notOffered = ["guard", "flow", "press", "lunge"].find((x) => !o.offer.presented.includes(x));
ok(CH.select(T, ch, o.offer.id, notOffered).code === "NOT_IN_OFFER", "a candidate that wasn't presented can't be selected");
let r = CH.select(T, ch, o.offer.id, pick); ch = r.state;
ok(r.ok && ch.held["mastery:blade/" + pick] && ch.features.includes("feature:" + pick) && F.verifyReceipt(r.receipt), "one choice recorded as a sealed transaction and its feature unlocked");
ok(CH.select(T, ch, o.offer.id, pick).duplicate && CH.select(T, ch, o.offer.id, o.offer.presented.find((x) => x !== pick)).code === "OFFER_ALREADY_RESOLVED", "replaying the selection is a duplicate; a second pick from the same offer is refused");
ok(CH.statusOf(T, ch, "mastery:blade", pick).status === "purchased", "the chosen node reads as purchased");
ok(CH.due(T, ch, "mastery:blade").every((d) => d.milestone !== 3 || d.group !== "forms"), "the L3 milestone is no longer due");
// ---- unchosen options remain for later milestones (non-exclusive group) ----
ch.tracks["mastery:blade"].level = 6; o = CH.offer(T, ch, "mastery:blade", "forms", 6); ch = o.state;
const unchosen = ["guard", "flow", "press", "lunge"].filter((x) => x !== pick);
ok(o.offer.statuses.filter((s) => unchosen.includes(s.node)).every((s) => s.status === "eligible"), "unchosen L3 options are still eligible at L6");
ok(!o.offer.presented.includes(pick) && o.offer.statuses.find((s) => s.node === pick).status === "purchased", "an owned option is never offered again (no repeated purchase)");
ok(pick !== "guard" || o.offer.statuses.find((s) => s.node === "guard_ii").status === "eligible", "upgrade chain: Guard II becomes eligible once Guard is held");
const ng = at(6); ok(CH.statusOf(T, ng, "mastery:blade", "guard_ii").reasons.some((x) => x.code === "UPGRADE_OF_UNHELD"), "an upgrade is locked without its base node");
// ---- exclusive group, conflicts ----
let s6 = at(6); let os = CH.offer(T, s6, "mastery:blade", "stance", 6); s6 = os.state; ok(os.offer.presented.length === 2 && os.offer.fewer_than_offer_size, "only two stances exist: two are offered and NO filler is invented");
s6 = CH.select(T, s6, os.offer.id, "shield_stance").state; ok(CH.statusOf(T, s6, "mastery:blade", "storm_stance").status === "unavailable", "exclusive group closes after its pick (and Storm conflicts with Shield)");
// ---- hybrid / cross-tree unlock, restrictions ----
let h = at(9); h.held["mastery:blade/flow"] = { txn: "t" }; ok(CH.statusOf(T, h, "mastery:blade", "hybrid_cut").reasons.some((x) => x.code === "NODE" && x.node === "mastery:grapple/hold"), "hybrid unlock locked until the other tree's node is held");
h.held["mastery:grapple/hold"] = { txn: "t" }; ok(CH.statusOf(T, h, "mastery:blade", "hybrid_cut").status === "eligible", "…and eligible once both trees' prerequisites are held");
ok(CH.statusOf(T, at(6, { class: "operative" }), "mastery:blade", "guard").reasons[0].code === "CLASS_RESTRICTED", "class restriction: an Operative is refused");
ok(CH.statusOf(T, at(6, { features: [] }), "mastery:blade", "echani_only").status === "locked", "species-feature prerequisite: locked without Echani heritage");
// ---- duplicate grants from another source ----
const d = at(3); d.features.push("feature:flow"); ok(CH.statusOf(T, d, "mastery:blade", "flow").reasons[0].code === "ALREADY_GRANTED_ELSEWHERE", "a feature already granted by another source is not sold again");
// ---- fresh re-validation at confirm ----
let fr = at(3); const of = CH.offer(T, fr, "mastery:blade", "forms", 3); fr = of.state; fr.features.push("feature:" + of.offer.presented[0]);
ok(CH.select(T, fr, of.offer.id, of.offer.presented[0]).code === "NO_LONGER_ELIGIBLE", "selection re-validates against fresh state (stale offers can't grant)");
// ---- replay determinism ----
const run = () => { let c = at(3); const x = CH.offer(T, c, "mastery:blade", "forms", 3); c = x.state; return CH.select(T, c, x.offer.id, x.offer.presented[1]).state; };
ok(JSON.stringify(run()) === JSON.stringify(run()), "the same history replays to byte-identical state");
// ---- interrupted selection ----
let ir = at(3); const io = CH.offer(T, ir, "mastery:blade", "forms", 3); ir = io.state; const sel = CH.select(T, ir, io.offer.id, io.offer.presented[0]);
const crashed = JSON.parse(JSON.stringify(ir)); crashed.pending = sel.receipt; const rec = F.recover(crashed);
ok(rec.ok && rec.state.held["mastery:blade/" + io.offer.presented[0]] && F.recover(rec.state).nothing, "an interrupted selection is recovered exactly once");
console.log(fails ? fails + " FAILED" : "all " + n + " passed"); process.exit(fails ? 1 : 0);
