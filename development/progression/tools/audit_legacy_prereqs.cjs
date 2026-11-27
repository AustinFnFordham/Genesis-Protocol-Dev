#!/usr/bin/env node
// Legacy prerequisite audit (CC-008.1). Runs framework.fromLegacyClass over EVERY legacy progression tree in the repo's
// candidate builds and in the verbatim hub extract, and writes a machine-readable report. Read-only on all sources.
// node development/progression/tools/audit_legacy_prereqs.cjs [--out <file>]   (default: legacy/legacy_prereq_audit.json)
const fs = require("fs"), path = require("path"), crypto = require("crypto"), F = require("../framework.js");
const REPO = path.join(__dirname, "../../.."), sha = (b) => crypto.createHash("sha256").update(b).digest("hex");
function walk(d, out) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p, out); else if (e.name.endsWith(".json")) out.push(p); } return out; }
function audit() {
  const entries = [];
  const cand = walk(path.join(REPO, "registry/candidate_builds"), []).filter((p) => /cand_(classes|subclasses)_/.test(p)).sort();
  for (const p of cand) { const raw = fs.readFileSync(p); let d; try { d = JSON.parse(raw); } catch (e) { continue; }
    const rec = d && (d.record || d); if (!rec || !Array.isArray(rec.progression_tree) || !rec.progression_tree.length) continue;
    entries.push({ family: "candidate_build", source: path.relative(REPO, p), source_sha256: sha(raw), id: rec.id, kind: /cand_subclasses_/.test(p) ? "subclass" : "class", rec }); }
  const hubFile = path.join(__dirname, "../legacy/hub_trees_extract.json"), hub = JSON.parse(fs.readFileSync(hubFile));
  for (const t of hub.trees) entries.push({ family: "hub_archive", source: hub.archive.path + "!" + t.member, source_sha256: t.member_sha256, id: t.id, kind: t.kind, rec: { id: t.id, progression_tree: t.progression_tree } });
  const records = entries.map((e) => { const { tree, notes } = F.fromLegacyClass(e.rec, { source: e.source, legacy_source: { path: e.source, sha256: e.source_sha256 } });
    const codes = {}; notes.forEach((n) => (codes[n.code] = (codes[n.code] || 0) + 1));
    return { family: e.family, source: e.source, source_sha256: e.source_sha256, id: e.id, kind: e.kind, nodes: e.rec.progression_tree.length, codes,
             reinterpreted: notes.filter((n) => n.code === "AMBIGUOUS_EXCLUSIVE_GROUP").map((n) => ({ node: n.node, original_prerequisites: n.original_prerequisites, interpretation: n.interpretation, groups: n.groups, partial_group_listing: n.partial_group_listing })),
             invalid: notes.filter((n) => n.invalid).map((n) => ({ code: n.code, node: n.node, note: n.note })),
             promotion: { requires_explicit_validation: tree.promotion.requires_explicit_validation, promotable: false, reason: tree.promotion.requires_explicit_validation ? "reinterpreted or invalid prerequisites need an explicit validation record" : "legacy content is candidate until owner approval" } }; });
  const sum = (fam) => { const r = records.filter((x) => !fam || x.family === fam); return { trees: r.length, reinterpreted_trees: r.filter((x) => x.reinterpreted.length).length, reinterpreted_nodes: r.reduce((a, x) => a + x.reinterpreted.length, 0),
    trees_with_invalid_prerequisites: r.filter((x) => x.invalid.length).length, invalid_findings: r.reduce((a, x) => a + x.invalid.length, 0), requiring_validation: r.filter((x) => x.promotion.requires_explicit_validation).length }; };
  return { schema: "genesis-legacy-prereq-audit/0.1", adapter: "framework.fromLegacyClass legacy-adapter-0.2", note: "Sources are unchanged. No record is promotable from this report; each reinterpretation needs an explicit validation record (tree.promotion.validated).",
           summary: { all: sum(), candidate_build: sum("candidate_build"), hub_archive: sum("hub_archive") }, records };
}
module.exports = { audit };
if (require.main === module) { const i = process.argv.indexOf("--out"), out = i > 0 ? process.argv[i + 1] : path.join(__dirname, "../legacy/legacy_prereq_audit.json");
  const r = audit(); fs.writeFileSync(out, JSON.stringify(r, null, 1) + "\n"); console.log(JSON.stringify(r.summary)); }
