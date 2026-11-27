#!/usr/bin/env node
// Validate proposed progression tree(s) without touching the game runtime (CC-008 G).
// node development/progression/tools/validate_tree.cjs <tree.json>... [--policy <policy.json>] [--external a,b] [--md <out.md>] [--json] [--no-registry]
// Exit code 0 = pass, 1 = errors, 2 = usage. A file may hold one tree or an array of trees.
const fs = require("fs"), path = require("path"), AU = require("../authoring.js");
const a = process.argv.slice(2); if (!a.length || a.includes("-h") || a.includes("--help")) { console.log(fs.readFileSync(__filename, "utf8").split("\n").slice(1, 4).join("\n")); process.exit(2); }
const opt = (k) => { const i = a.indexOf(k); return i >= 0 ? a[i + 1] : null; };
const skip = new Set(); ["--policy", "--external", "--md"].forEach((k) => { const i = a.indexOf(k); if (i >= 0) { skip.add(i); skip.add(i + 1); } });
const files = a.filter((x, i) => !skip.has(i) && !x.startsWith("--"));
const trees = []; for (const f of files) { const d = JSON.parse(fs.readFileSync(f, "utf8")); (Array.isArray(d) ? d : d.trees || [d]).forEach((t) => trees.push(t)); }
const rep = AU.review(trees, { policy: opt("--policy") ? JSON.parse(fs.readFileSync(opt("--policy"), "utf8")) : null, external_tracks: (opt("--external") || "").split(",").filter(Boolean), registry: !a.includes("--no-registry") });
if (opt("--md")) fs.writeFileSync(opt("--md"), AU.markdown(trees, rep));
if (a.includes("--json")) console.log(JSON.stringify(rep, null, 1));
else { console.log((rep.ok ? "PASS" : "FAIL") + " — " + trees.length + " tree(s), " + rep.errors.length + " error(s), " + rep.warnings.length + " warning(s), " + rep.reachability.reachable + " reachable node(s)");
  rep.errors.forEach((e) => console.log("  ERROR " + e.code + " @ " + e.where)); rep.warnings.forEach((e) => console.log("  warn  " + e.code + " @ " + e.where)); }
process.exit(rep.ok ? 0 : 1);
