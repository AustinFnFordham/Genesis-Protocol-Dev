// CC-008 runner: every milestone test, each in its own process. node test_cc008.cjs
const { spawnSync } = require("child_process"), path = require("path"), fs = require("fs");
let bad = 0; for (const m of ["b", "c", "d", "e", "f", "g"]) { const f = path.join(__dirname, "test_cc008_" + m + ".cjs"); if (!fs.existsSync(f)) continue;
  const r = spawnSync(process.execPath, [f], { encoding: "utf8" }); const last = (r.stdout || "").trim().split("\n").pop(); console.log("CC-008 " + m.toUpperCase() + ": " + last); if (r.status !== 0) { bad++; console.log(r.stdout.split("\n").filter((l) => l.startsWith("FAIL")).join("\n")); } }
console.log(bad ? bad + " milestone suite(s) FAILED" : "all passed"); process.exit(bad ? 1 : 0);
