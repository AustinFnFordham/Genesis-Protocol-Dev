// Browser tests for the scene-mode composer (turn-contract/3 palette and plan; contract-2 behaviours kept): ordered steps, hands/position checks,
// "only if" conditions, GM review reasons, pending steps that need re-authorization, timing panel.
// Usage: node test_datapad_scene_ui.cjs <page.html> <state.json> [shotDir]
// The state's turn_context is replaced by the NON-canonical fixture fixtures/hask_r2_barn_scene.json.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const [page_file, state_file, shotDir] = process.argv.slice(2);
const url = "file://" + path.resolve(page_file);
const state = JSON.parse(fs.readFileSync(state_file, "utf8"));
state.turn_context = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "hask_r2_barn_scene.json"), "utf8"));
const MOCK = fs.readFileSync(path.join(__dirname, "test_datapad_ui.cjs"), "utf8").match(/const MOCK = `([\s\S]*?)`;/)[1];

let fails = 0;
function ok(c, name, extra) { if (c) console.log("ok", name); else { fails++; console.log("FAIL", name, extra === undefined ? "" : extra); } }

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
  const page = await ctx.newPage();
  const errors = []; page.on("pageerror", e => errors.push(e.message));
  await page.addInitScript(({ mock, st }) => { window.__store = { "view/state": st }; eval(mock); }, { mock: MOCK, st: state });
  await page.goto(url);
  await page.waitForSelector("#submitTurn");
  const composer = () => page.locator(".composer").innerText();
  const live = () => page.locator("#liveCheck").innerText();
  async function add(v) { await page.click(`[data-pal="${v}"]`); await page.waitForTimeout(80); }
  const sid = i => page.evaluate(i => document.querySelectorAll(".plan li.step")[i].getAttribute("data-sid"), i);

  // scene terminology: no combat slots, no "free / uses your action" hints
  ok(await page.locator("fieldset.grp legend", { hasText: "Primary action" }).count() === 0, "scene hides the combat 'Primary action' slot");
  ok(await page.locator(".plan .seqcard").count() === 1 && await page.locator("select#w_addstep").count() === 0, "scene shows a sequence plan and a visible palette");
  ok(/no action economy/.test(await composer()) && !/first one each turn is free/.test(await composer()), "scene explains sequencing, no free-object hint");

  // a legal sequence in the player's order: holster, walk to the silo door (cart within reach), take the torch
  ok(await page.locator('[data-pal="object:take_torch"]').isDisabled(), "taking the torch from 35 ft is disabled until a move is planned");
  await add("object:holster_blaster"); await add("move:to_silo_door"); await add("object:take_torch");
  let t = await live();
  ok(/Legal turn/.test(t), "holster → walk → take torch is legal", t);
  const items = await page.locator("#liveCheck ol li").allInnerTexts();
  ok(/Holster/.test(items[0]) && /Silo Three/.test(items[1]) && /welding torch/.test(items[2]), "preview keeps the player's order", items);
  ok(!/uses your action|free object interaction/.test(t), "no combat economy labels in scene preview", t);

  // a third item with two hands: refused before it is added, with the reason and a way to say how
  const b = page.locator('[data-pal="object:take_bottle_a"]');
  ok(await b.isDisabled() && /needs 1 free hand/.test(await b.innerText()) && /left hand holds the welding torch/.test(await b.innerText()), "carrying limit enforced and explained in the palette", await b.innerText());
  ok(await page.locator('.pal:has([data-pal="object:take_bottle_a"]) [data-how]').count() === 1, "needs-your-choice offers a custom action");
  // reorder: taking the torch first breaks it (no move yet, no free hand)
  const torch = await sid(2);
  await page.click(`[data-up="${torch}"]`); await page.waitForTimeout(60); await page.click(`[data-up="${torch}"]`); await page.waitForTimeout(80);
  t = await live();
  ok(/Not legal yet/.test(t) && /Take the welding torch/.test(t) && await page.locator("li.st-fix").count() === 1, "taking the torch before moving is marked on the step", t);
  ok(await page.locator("#submitTurn").isDisabled(), "submit disabled while physically impossible");
  await page.click(`[data-down="${torch}"]`); await page.waitForTimeout(60); await page.click(`[data-down="${torch}"]`); await page.waitForTimeout(80);
  ok(/Legal turn/.test(await live()), "reordering back makes it legal");

  // conditional intent: ask first, cut only if...; the GM stops there
  await page.click("#clearTurn"); await page.waitForTimeout(80);
  ok(await page.locator(".plan li.step").count() === 0, "clear empties the plan");
  await add("speech:d2"); await add("action:ask_wick"); await add("action:cut_chain");
  const cut = await sid(2);
  await page.click(`[data-cond="${cut}"]`); await page.waitForTimeout(60);
  await page.fill(`#w_cond_${cut}`, "Wick says it was sealed to keep something out");
  await page.waitForTimeout(400);
  t = await live();
  ok(/Only if Wick says it was sealed to keep something out: Cut the barn/.test(t) && /GM resolves the steps before it and stops there/.test(t), "condition shown as a halt point", t);
  await page.locator(`#w_cond_${cut}`).blur(); await page.waitForTimeout(80);
  ok(await page.locator("li.halt").count() === 1, "the decision point is marked in the plan");
  if (shotDir) await page.screenshot({ path: shotDir + "/scene_steps_desktop.png" });
  await page.click("#submitTurn"); await page.waitForTimeout(300);
  const acts = await page.evaluate(() => Object.keys(window.__store).filter(k => k.startsWith("actions/")));
  const doc = acts.length ? await page.evaluate(k => window.__store[k], acts[0]) : null;
  ok(doc && doc.contract === "turn-contract/3" && doc.declaration.steps.map(s => s.type).join(",") === "speech,action,action" &&
     doc.declaration.steps[2].condition && /keep something out/.test(doc.declaration.steps[2].condition.text) &&
     doc.declaration.actions.length === 2, "submitted document carries ordered steps, the condition and legacy fields", doc && doc.declaration);

  // a GM review now shows its reasons, not only the summary
  await page.evaluate(k => { const a = window.__store[k]; a.status = "needs_revision"; a.review = { summary: "Two parts can't be carried out as written.",
    errors: ["Both of your hands are full.", { code: "CONDITION_UNRESOLVED", message: "The cut depends on an answer Aero does not have yet." }], warnings: ["Cutting throws sparks."], alternatives: [] }; window.__notify(); }, acts[0]);
  await page.waitForTimeout(150);
  const act = await page.locator(".act").first().innerText();
  ok(/Both of your hands are full/.test(act) && /does not have yet/.test(act) && /throws sparks/.test(act), "review reasons and warnings are visible", act);

  // pending steps from a halted sequence: shown, run only after "Continue" and a new Submit
  await page.evaluate(() => { const v = window.__store["view/state"]; v.revision += 2;
    v.turn_context = Object.assign({}, v.turn_context, { context_id: "fixture_after_halt", pending_reason: "Wick doesn't know. The cut was not done.",
      pending_steps: [{ type: "action", option: "cut_chain", condition: { text: "Wick says it was sealed to keep something out" }, pending: true }, { type: "action", option: "search_dark", pending: true }] });
    window.__notify(); });
  await page.waitForTimeout(200);
  let c = await composer();
  ok(/Not done yet[\s\S]*Wick doesn't know[\s\S]*Only if Wick says[\s\S]*Search around/.test(c), "pending steps and the reason are shown", c);
  ok(await page.locator(".plan li.step").count() === 0, "pending steps are not loaded on their own");
  await page.click("#continuePending"); await page.waitForTimeout(120);
  c = await composer();
  ok(await page.locator(".plan li.step").count() === 2 && /continued/i.test(c), "Continue loads them as authorized steps", c);
  await page.click(`[data-cond="${await sid(0)}"]`); await page.waitForTimeout(60);  // the player drops the condition: their decision
  ok(/Legal turn/.test(await live()), "continued steps validate");

  // read-only timing panel from usage records
  await page.evaluate(() => { const v = window.__store["view/state"];
    window.__store["usage/r9"] = { campaign_id: v.campaign_id, outcome: "committed", started_ms: Date.now() - 300000, finished_ms: Date.now(),
      timings: { submit_to_visible_ms: 304000, "3_context_loading_ms": 95000, "7_narration_ms": 50000, "9_git_sync_ms": 5300, model_ms: 266000, tool_ms: 23000, model_calls: 32, tool_calls: 36, output_tokens: 26000 } }; window.__notify(); });
  await page.waitForTimeout(150);
  const right = await page.locator(".col.right").innerText();
  ok(/Turn timing · last 304 s · median 304 s/.test(right), "timing panel shows measured submit-to-visible", right.slice(0, 400));
  const writes0 = await page.evaluate(() => window.__writes || 0);
  await page.locator(".perf summary").click(); await page.waitForTimeout(80);
  ok(/Git push\s*5\.3 s/.test(await page.locator(".perf").innerText()) && (await page.evaluate(() => window.__writes || 0)) === writes0, "timing details render without any write");

  // phone: no horizontal scroll with the steps list
  const m = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, hasTouch: true });
  const mp = await m.newPage();
  await mp.addInitScript(({ mock, st }) => { window.__store = { "view/state": st }; eval(mock); }, { mock: MOCK, st: state });
  await mp.goto(url); await mp.waitForSelector("#submitTurn");
  await mp.click('[data-pal="object:holster_blaster"]'); await mp.waitForTimeout(80);
  await mp.click('[data-pal="move:to_silo_door"]'); await mp.waitForTimeout(80);
  const sw = await mp.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  ok(sw <= 0, "no horizontal scroll on phone", sw);
  const small = await mp.evaluate(() => [...document.querySelectorAll(".btn.mini")].filter(e => e.getBoundingClientRect().height < 40 && e.offsetParent).length);
  ok(small === 0, "step buttons are at least 40px tall", small);
  if (shotDir) await mp.screenshot({ path: shotDir + "/scene_steps_phone.png", fullPage: true });

  ok(errors.length === 0, "no page errors", errors);
  await browser.close();
  console.log(fails ? fails + " failed" : "all passed");
  process.exit(fails ? 1 : 0);
})();
