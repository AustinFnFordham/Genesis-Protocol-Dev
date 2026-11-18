// WHISPER start-of-turn panel (switch whisper_context): TB4-10, -11, -12, -24. node test_whisper_ui.cjs <page> <state>
const fs = require("fs"), path = require("path");
const { chromium } = require("playwright");
const [pageFile, stateFile] = process.argv.slice(2);
const st = JSON.parse(fs.readFileSync(stateFile));
const MOCK = fs.readFileSync(path.join(__dirname, "test_datapad_ui.cjs"), "utf8").match(/const MOCK = `([\s\S]*?)`;/)[1];
let failures = 0;
const ok = (c, n, x) => { if (c) console.log("ok", n); else { failures++; console.log("FAIL", n, x || ""); } };
(async () => {
  const browser = await chromium.launch();
  try {
    async function open(features, vp) {
      const page = await (await browser.newContext({ viewport: vp || { width: 820, height: 1180 } })).newPage();
      const errors = []; page.on("pageerror", (e) => errors.push(e.message));
      const s = JSON.parse(JSON.stringify(st)); if (features) s.features = features; s.processor = null;
      await page.addInitScript(({ mock, st }) => { window.__store = { "view/state": st }; eval(mock); }, { mock: MOCK, st: s });
      await page.goto("file://" + path.resolve(pageFile)); await page.waitForSelector("#submitTurn");
      return { page, errors };
    }
    { const { page } = await open(null); ok(await page.locator("#whisperPanel").count() === 0, "switch off: no WHISPER panel"); }
    const { page, errors } = await open({ whisper_context: true });
    ok(await page.locator("#whisperPanel").count() === 1, "switch on: WHISPER panel present");
    const writes0 = await page.evaluate(() => window.__writes || 0);
    await page.locator("#whisperPanel > summary").click();
    await page.locator("#whatIf > summary").click(); await page.waitForTimeout(150);
    await page.locator("#whatIf > summary").click(); await page.waitForTimeout(150);
    const d0 = await page.evaluate(() => window.__lastValidation && true);
    ok(await page.evaluate(() => window.__writes || 0) === writes0, "TB4-12 opening and closing What-if writes nothing");
    ok(await page.locator("#submitTurn").isDisabled(), "a WHISPER context alone is not a turn (no act declared)");
    await page.locator('[data-whfeel="fear"]').click(); await page.waitForTimeout(100);
    await page.selectOption("#w_wh_expr", "controlled"); await page.waitForTimeout(100);
    await page.fill("#w_wh_exprtext", "steady voice, saber low");
    await page.fill("#w_wh_motive", "protect Wick, not prove anything");
    await page.locator('input[data-g="action"]').nth(1).check(); await page.waitForTimeout(500);
    if (await page.locator("#confirmRisk").count()) await page.check("#confirmRisk");
    await page.locator("#submitTurn").click(); await page.waitForTimeout(500);
    const row = await page.evaluate(() => { const k = Object.keys(window.__store).find((x) => x.startsWith("actions/")); return k && window.__store[k]; });
    const w = row && row.declaration.whisper;
    ok(w && w.felt_emotion[0] === "fear" && w.expression.style === "controlled" && w.motive === "protect Wick, not prove anything" && w.visibility === "pc_private" && w.source === "player_explicit", "TB4-11 the player's context is sent as private, player-authored", JSON.stringify(w));
    ok(row && /WHISPER \(private\): feels fear/.test(row.text) && row.declaration.actions.length === 1, "the act is still the act; the context rides alongside it");
    // unspecified: a turn with nothing written in WHISPER carries no whisper block
    const { page: p2 } = await open({ whisper_context: true });
    await p2.locator('input[data-g="action"]').nth(1).check(); await p2.waitForTimeout(400);
    if (await p2.locator("#confirmRisk").count()) await p2.check("#confirmRisk");
    await p2.locator("#submitTurn").click(); await p2.waitForTimeout(500);
    const r2 = await p2.evaluate(() => { const k = Object.keys(window.__store).find((x) => x.startsWith("actions/")); return k && window.__store[k]; });
    ok(r2 && !("whisper" in r2.declaration) && !/WHISPER/.test(r2.text), "TB4-10 blank WHISPER stays unspecified: nothing is inferred or sent");
    const { page: ph } = await open({ whisper_context: true, tb4_builder: true }, { width: 390, height: 844 });
    await ph.locator("#whisperPanel > summary").click();
    ok(await ph.evaluate(() => document.documentElement.scrollWidth - innerWidth) <= 0, "TB4-24 no horizontal scroll at phone width");
    if (process.argv[4]) { await ph.locator("#whisperPanel").scrollIntoViewIfNeeded(); await ph.screenshot({ path: process.argv[4] }); }
    ok(errors.length === 0, "no page errors", errors.join("|"));
  } finally { await browser.close(); }
  console.log(failures ? failures + " FAILED" : "all passed"); process.exit(failures ? 1 : 0);
})();
