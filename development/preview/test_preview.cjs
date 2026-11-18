// Smoke test of the development preview over real HTTP at iPad size.
// node development/preview/test_preview.cjs   (starts serve_preview.py on a free port itself)
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const port = 8000 + Math.floor(Math.random() * 900);
let failures = 0;
const ok = (c, n, x) => { if (c) console.log("ok", n); else { failures++; console.log("FAIL", n, x || ""); } };
(async () => {
  const srv = spawn("python3", ["-B", path.join(__dirname, "serve_preview.py"), "--port", String(port)], { stdio: ["ignore", "pipe", "inherit"] });
  await new Promise((res) => srv.stdout.on("data", (d) => { if (/dev preview/.test(String(d))) res(); }));
  const browser = await chromium.launch();
  try {
    const ctx = await browser.newContext({ viewport: { width: 820, height: 1180 }, hasTouch: true });
    const page = await ctx.newPage();
    const errors = []; page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(`http://127.0.0.1:${port}/`);
    await page.waitForSelector("#submitTurn");
    const banner = await page.locator("#devEnvBanner").innerText();
    const build = JSON.parse(fs.readFileSync(path.join(__dirname, "out/build.json")));
    ok(/Genesis Development \/ Test Environment/.test(banner) && banner.includes(build.milestone) && banner.includes(build.code_commit), "banner names environment, milestone and commit", banner);
    ok(/Sim Deck: Drill Seven/.test(banner), "banner names the fixture");
    const html = await page.content();
    ok(!/hound_3/.test(html) && !/hask_meadow/.test(html), "no hidden fixture creature or live campaign in the page");
    ok(await page.locator(".composer").count() > 0, "composer renders from fixture state");
    const sw = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    ok(sw <= 0, "no horizontal scroll at iPad width", sw);
    await page.locator('[data-mode="write"]').click().catch(() => {});
    const w = page.locator("#w_write");
    if (await w.count()) { await w.fill("I hold my ground and watch the crates."); }
    await page.waitForTimeout(400);
    const btn = page.locator("#submitTurn");
    if (!(await btn.isDisabled())) { await btn.click(); await page.waitForTimeout(1200); }
    const acts = await page.evaluate(() => Object.keys(window.__store).filter((k) => k.startsWith("actions/")).map((k) => window.__store[k]));
    ok(acts.length === 1 && acts[0].preview === true && /no GM is attached/.test(acts[0].error), "a submitted turn is kept and marked preview-only", JSON.stringify(acts).slice(0, 300));
    await page.reload(); await page.waitForSelector("#submitTurn");
    const kept = await page.evaluate(() => Object.keys(window.__store).filter((k) => k.startsWith("actions/")).length);
    ok(kept === 1, "preview state survives a reload (iPad tab switching)");
    if (process.argv[2]) await page.screenshot({ path: process.argv[2], fullPage: false });
    ok(errors.length === 0, "no page errors", errors.join(" | "));
  } finally { await browser.close(); srv.kill(); }
  console.log(failures ? failures + " FAILED" : "all passed");
  process.exit(failures ? 1 : 0);
})();
