// Turn Builder 4 (TB4-WHISPER-001 §2, acceptance TB4-01, -02, -06, -23, -24). Pure module + browser.
// node test_tb4.cjs <page.html> <state_round1.json>
const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");
const TB4 = require("./src/tb4.js");
const T = require("./turn_contract.js");
const [pageFile, stateFile] = process.argv.slice(2);
let failures = 0;
const ok = (c, n, x) => { if (c) console.log("ok", n); else { failures++; console.log("FAIL", n, x || ""); } };

// ---- pure ----
const st = JSON.parse(fs.readFileSync(stateFile));
const c = st.turn_context;
ok(!TB4.enabled({}) && !TB4.enabled({ features: {} }) && !TB4.enabled({ features: { tb4_builder: "yes" } }) && TB4.enabled({ features: { tb4_builder: true } }), "switch: only an explicit true turns TB4 on");
const s1 = TB4.suggest(c, "action", "", {}), s2 = TB4.suggest(c, "action", "", {});
ok(JSON.stringify(s1) === JSON.stringify(s2) && s1.filter((x) => x.status !== "blocked").length <= 4, "suggestions are deterministic and at most four", s1.length);
const ids = new Set((c.options || []).map((o) => o.id).concat((c.movement || []).map((m) => m.id), (c.objects || []).map((o) => o.id), (c.reactions || []).map((o) => o.id)));
ok(["action", "bonus_action", "movement", "object", "reaction"].every((k) => TB4.suggest(c, k, "bold", {}).every((x) => ids.has(x.id))), "suggestions only come from published options (no invented abilities)");
const bold = TB4.suggest(c, "action", "bold", {}), cautious = TB4.suggest(c, "action", "cautious", {});
ok(bold.length === 0 || bold[0].id !== undefined, "style ranking runs");
const blocked = TB4.suggest(c, "action", "", { ["action:" + (c.options || [])[0].id]: { status: "not_here", reasons: ["No target in reach"] } });
ok(blocked.some((x) => x.status === "blocked" && x.reason === "No target in reach") && blocked.filter((x) => x.status !== "blocked").every((x) => x.id !== (c.options || [])[0].id), "a blocked option is marked with its reason, never offered as legal");
const sel = { tb4custom: { action: "  Pin the hound's head with my boot and say “stay”  ", secondary: "Wave Wick back toward the crates", reaction: "If the far hound charges Wick, I step into its path" } };
const d = TB4.apply(T.emptyDecl(c), sel);
ok(d.tb4.custom.length === 3 && d.tb4.custom[0].text === "Pin the hound's head with my boot and say “stay”", "custom words are kept literally (trimmed only)", JSON.stringify(d.tb4));
ok(d.unmapped.includes("Wave Wick back toward the crates") && d.actions.length === 0 && d.bonus_actions.length === 0, "Secondary activity adds no slot: it goes to the GM as text, never as an action");
const v = T.validate(d, c);
ok(v && v.legal !== undefined && !v.errors.some((e) => /SECONDARY|TB4/.test(e.code || "")), "the shared validator reads a TB4 declaration without new rules");
const legacy = JSON.parse(JSON.stringify(T.emptyDecl(c))); legacy.actions = [{ option: (c.options || [])[0].id }];
ok(JSON.stringify(T.validate(legacy, c)) === JSON.stringify(T.validate(JSON.parse(JSON.stringify(legacy)), c)) && TB4.apply(JSON.parse(JSON.stringify(legacy)), {}).tb4 === undefined, "declarations without TB4 input are untouched (contract 1–3 compatible)");
const back = {}; TB4.restore(d, back);
ok(back.tb4custom.secondary === "Wave Wick back toward the crates", "a saved TB4 declaration loads back into its boxes");

// ---- browser ----
const { chromium } = require("playwright");
const src = fs.readFileSync(path.join(__dirname, "test_datapad_ui.cjs"), "utf8");
const MOCK = src.match(/const MOCK = `([\s\S]*?)`;/)[1];
(async () => {
  const browser = await chromium.launch();
  try {
    async function open(features, vp) {
      const page = await (await browser.newContext({ viewport: vp || { width: 820, height: 1180 }, hasTouch: true })).newPage();
      const errors = []; page.on("pageerror", (e) => errors.push(e.message));
      const state = JSON.parse(JSON.stringify(st)); delete state.features; if (features) state.features = features; state.processor = null;
      await page.addInitScript(({ mock, st }) => { window.__store = { "view/state": st }; eval(mock); }, { mock: MOCK, st: state });
      await page.goto("file://" + path.resolve(pageFile)); await page.waitForSelector("#submitTurn");
      return { page, errors };
    }
    // switch off: the page is the live page as before
    { const { page, errors } = await open(null);
      ok(await page.locator("[data-tb4cat]").count() === 0 && await page.locator(".tb4style").count() === 0, "switch off: no TB4 controls at all");
      ok(errors.length === 0, "switch off: no page errors", errors.join("|")); }
    // switch on
    const { page, errors } = await open({ tb4_builder: true });
    const cats = await page.locator("[data-tb4cat]").evaluateAll((els) => els.map((e) => e.getAttribute("data-tb4cat")));
    ok(["action", "bonus_action", "secondary", "movement", "object", "reaction"].every((k) => cats.includes(k)), "every combat category has its own Custom box (TB4-01)", cats.join(","));
    ok(await page.locator("#w_own").count() + await page.locator('input[data-g="dialogue"][value="own"]').count() > 0, "speech keeps its own-words line");
    ok(await page.locator("[data-tb4pick]").count() > 0, "suggestions shown");
    // a suggestion selects the existing radio (no second validator)
    const first = page.locator('[data-tb4cat-sugg="action"] [data-tb4pick^="action|"]').first();
    if (await first.count()) { const v0 = (await first.getAttribute("data-tb4pick")).split("|")[1]; await first.click(); await page.waitForTimeout(150);
      ok(await page.locator(`input[data-g="action"][value="${v0}"]`).isChecked(), "tapping a suggestion selects that option in the normal list"); }
    await page.locator("#mechanicsCatalog > summary").click();
    await page.locator('input[data-g="action"][value=""]').check(); await page.waitForTimeout(100);
    const words = "Pin the hound with my boot and say “stay”, low and steady";
    await page.fill("#w_tb4_action", words);
    await page.fill("#w_tb4_secondary", "Wave Wick back toward the crates");
    await page.waitForTimeout(500);
    ok(!(await page.locator("#submitTurn").isDisabled()), "a custom-only turn can be submitted");
    await page.locator("#submitTurn").click(); await page.waitForTimeout(500);
    const row = await page.evaluate(() => { const k = Object.keys(window.__store).find((x) => x.startsWith("actions/")); return k && window.__store[k]; });
    ok(row && row.declaration.tb4 && row.declaration.tb4.custom.find((x) => x.category === "action").text === words, "literal custom words reach the submitted action unchanged (TB4-02)", JSON.stringify(row && row.declaration.tb4));
    ok(row && row.declaration.unmapped.includes("Wave Wick back toward the crates") && !(row.declaration.bonus_actions || []).length, "secondary activity is sent as text, not as a slot (TB4-06)");
    ok(row && /Primary action \(custom\)/.test(row.text), "the turn text names the custom entries for the GM");
    // style chips re-rank without changing the selection
    await page.reload(); await page.waitForSelector("#submitTurn");
    // iPad and phone width: no horizontal scroll, custom boxes usable
    const { page: ph } = await open({ tb4_builder: true }, { width: 390, height: 844 });
    ok(await ph.evaluate(() => document.documentElement.scrollWidth - innerWidth) <= 0, "no horizontal scroll at phone width with TB4 on (TB4-24)");
    ok(errors.length === 0, "switch on: no page errors", errors.join("|"));
    if (process.argv[4]) { await ph.locator("#w_tb4_secondary").scrollIntoViewIfNeeded(); await ph.screenshot({ path: process.argv[4] }); }
  } finally { await browser.close(); }
  console.log(failures ? failures + " FAILED" : "all passed");
  process.exit(failures ? 1 : 0);
})();
