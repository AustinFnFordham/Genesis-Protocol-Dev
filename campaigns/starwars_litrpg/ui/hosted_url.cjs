// Load an artifact page the way the artifact host serves it (CC-008.1 flake fix).
// Artifact pages are published WITHOUT their own <!doctype>/<meta charset>: the host wraps them in a skeleton that declares
// UTF-8. Loading the raw file over file:// leaves Chromium to sniff the encoding from whatever bytes it has buffered, which under
// CPU load sometimes yields windows-1252 and garbles every non-ASCII glyph (· ✎ × …) — a nondeterministic test failure that
// says nothing about the page. hostedUrl() writes the published skeleton around the page, to a per-process file (concurrent
// suites never share it), and returns its file:// URL. The page source itself is never modified.
"use strict";
const fs = require("fs"), path = require("path"), os = require("os");
const SKELETON_HEAD = '<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>';
let seq = 0;
function hostedUrl(pageFile) {
  const src = fs.readFileSync(path.resolve(pageFile), "utf8");
  const html = /^\s*<!doctype/i.test(src) ? src : SKELETON_HEAD + src + "</body></html>";   // a full document is used as-is
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "hosted_" + process.pid + "_" + (seq++) + "_"));
  const out = path.join(dir, path.basename(pageFile));
  fs.writeFileSync(out, html);
  return "file://" + out;
}
module.exports = { hostedUrl, SKELETON_HEAD };
