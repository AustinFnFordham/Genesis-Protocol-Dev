// CC-008 G: authoring workflow — validate a proposed tree without touching the game runtime; tables + dependency report.
const AU = require("./authoring.js"), A = require("./fixtures/aero_vertical/aero_vertical.js"), CU = require("./curves.js"), F = require("./framework.js");
const { spawnSync } = require("child_process"), fs = require("fs"), path = require("path"), crypto = require("crypto");
let fails = 0, n = 0; const ok = (c, m, x) => { n++; console.log((c ? "ok " : "FAIL ") + m + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 400))); if (!c) fails++; };
const REPO = path.join(__dirname, "../.."), TOOL = path.join(__dirname, "tools/validate_tree.cjs"), TMP = fs.mkdtempSync(path.join(require("os").tmpdir(), "cc008g-"));
const RUNTIME = ["api_bridge/gm/aero_character_runtime.yml", "development/combat_slice/engine.js", "development/combat_slice/catalog.json", "development/combat_slice/scenarios.json", "campaigns/starwars_litrpg/creator/jedi_fundamentals.json"];
const hashes = () => RUNTIME.map((f) => crypto.createHash("sha256").update(fs.readFileSync(path.join(REPO, f))).digest("hex")).join();
const before = hashes(), tool = (args) => spawnSync(process.execPath, [TOOL].concat(args), { encoding: "utf8" });
const EXT = ["diplomat", "shadow_guard", "artisan", "investigator", "racer", "shadow", "shien_expert"].map((x) => "archetype:sentinel_" + x).join(",");
// ---- entry point ----
let r = tool(["trees/telekinetic_control.tree.json"].map((f) => path.join(__dirname, f)));
ok(r.status === 0 && /^PASS/.test(r.stdout), "validate_tree.cjs passes the Telekinetic Control tree (exit 0)", r.stdout);
ok(!/NO_BALANCE_TEST_COVERAGE/.test(r.stdout) && /REGISTRY_URID_NOT_APPROVED/.test(r.stdout), "it has balance-test coverage; its anchor feature_minor_telekinesis is NOT an approved Registry identity (a campaign ruling) — reported as a warning");
r = tool([path.join(__dirname, "fixtures/broken_tree.example.json"), "--no-registry", "--json"]); const rep = JSON.parse(r.stdout), codes = new Set(rep.errors.map((e) => e.code));
ok(r.status === 1, "a broken tree fails with exit 1");
["CURVE_NOT_MONOTONIC", "CURVE_NON_POSITIVE_OR_FRACTIONAL_STEP", "APPROVED_TREE_WITH_CANDIDATE_CURVE", "CADENCE_OUT_OF_RANGE", "DUPLICATE_REWARD", "UNSATISFIABLE_EXCLUSIVE_REQUIREMENT", "PREREQUISITE_CYCLE", "UNREACHABLE_TRACK_LEVEL",
 "UNREACHABLE_NODE", "GRANT_AUTHORITY_MISMATCH", "EMPTY_CHOICE_GROUP", "MALFORMED_URID", "BALANCE_TEST_MISSING", "UNAPPROVED_NODE_IN_APPROVED_TREE"].forEach((c) => ok(codes.has(c), "broken tree: " + c + " detected"));
ok(rep.warnings.some((w) => w.code === "STACKING_UNDECLARED") && rep.warnings.some((w) => w.code === "CONFLICT_NOT_RECIPROCAL"), "stacking without a stacking group and one-sided conflicts are flagged");
// ---- the Aero fixture through the tool, with the Discipline policy ----
const aeroFile = path.join(TMP, "aero_trees.json"); fs.writeFileSync(aeroFile, JSON.stringify(A.build().trees));
r = tool([aeroFile, "--policy", path.join(__dirname, "policies/discipline_allocation.v0.1.json"), "--external", EXT, "--md", path.join(TMP, "aero.md")]);
ok(r.status === 0 && /PASS — 24 tree/.test(r.stdout), "the full Aero vertical set (24 tracks) + Discipline policy passes", r.stdout.split("\n")[0]);
ok(/GRANT_NOT_IN_APPROVED_REGISTRY @ class:sentinel\/extra_attack_5/.test(r.stdout) && /NOT_APPROVED_CONTENT @ archetype:sentinel_sentry/.test(r.stdout), "registry identities: unapproved Sentinel/Sentry feature grants and unapproved content are reported");
const md = fs.readFileSync(path.join(TMP, "aero.md"), "utf8");
ok(/## mastery:echani_strike/.test(md) && /\| 3 \| 34 \| 50 \| ● \| candidate_quick_followup/.test(md) && /```mermaid/.test(md) && /-->\|unlocks\|/.test(md), "readable progression table and a dependency graph (mermaid) are generated");
// ---- duplicate XP allocation in a policy ----
const P = JSON.parse(fs.readFileSync(path.join(__dirname, "policies/discipline_allocation.v0.1.json"))); const bad = JSON.parse(JSON.stringify(P));
bad.rules.push({ id: "dup", pids: ["saber_strike"], primary: "discipline:force", pools: ["armed_combat", "armed_combat", "cooking"] }); bad.bounds = {};
const pc = new Set(AU.policyChecks(bad, A.build().trees).map((e) => e.code));
ok(["PID_IN_TWO_RULES", "PRIMARY_IS_A_POOL", "DUPLICATE_POOL_IN_RULE", "UNKNOWN_DISCIPLINE", "UNBOUNDED_ALLOCATION"].every((c) => pc.has(c)), "duplicate XP allocation, a pool used as a primary track, unknown pools and unbounded allocation are rejected", [...pc]);
// ---- reachability ----
const rr = AU.reachability(A.build().trees); ok(rr.unreachable.length === 0 && rr.reachable > 40, "every node in the Aero fixture is reachable", rr.unreachable);
// ---- usage and no runtime change ----
ok(tool([]).status === 2, "no arguments prints usage (exit 2)");
ok(hashes() === before, "validating trees changed no runtime or campaign file (sheet, engine, catalog, scenarios, Jedi Fundamentals)");
// ---- sample XP tables document ----
const sample = [JSON.parse(fs.readFileSync(path.join(__dirname, "trees/telekinetic_control.tree.json"))), A.build().trees.find((t) => t.id === "mastery:echani_strike")];
const cands = require("./candidates/class_level_curves.json").curves.filter((c) => c.track.xp_quantity !== "none");
let doc = "# Sample XP tables (CC-008) — generated by test_cc008_g.cjs\n\nEvery curve here is **owner_proposal** or **candidate**; none is adopted. Generated from the tree data with `curves.js`.\n\n";
{ const mdx = AU.markdown(sample, AU.review(sample, { registry: false, external_tracks: ["class:sentinel", "species:echani"] })).split("## Dependency graph")[0]; doc += mdx.slice(mdx.indexOf("## mastery:")); }
doc += "## Candidate class-level curves (no source thresholds exist)\n\n| Level | " + cands.map((c) => c.id).join(" | ") + " |\n|---:|" + cands.map(() => "---:").join("|") + "|\n";
for (let L = 1; L <= 20; L++) doc += "| " + L + " | " + cands.map((c) => CU.cumulative(c.track, L)).join(" | ") + " |\n";
fs.writeFileSync(path.join(__dirname, "XP_TABLES.md"), doc);
ok(/\| 20 \| — \| 3620 \|/.test(doc) && /\| 20 \| 355000 \|/.test(doc), "XP_TABLES.md written (Telekinetic Control, Echani Strike, candidate class curves)");
console.log(fails ? fails + " FAILED" : "all " + n + " passed"); process.exit(fails ? 1 : 0);
