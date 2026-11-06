// Browser tests for the Datapad composer (Playwright + a mock window.claude db/mcp).
// Usage: node test_datapad_ui.cjs <page.html> <state.json> [shotDir]
// Covers: composer render, Test B in the UI (illegal composite flagged, alternatives), Test C (risk
// confirmation), idempotent submit (Test H, client side), automatic GM start call (Test G, client
// side), status rendering, reload recovery (Test I, client side), Test J (viewing ≠ control), mobile.
const { chromium, devices } = require("playwright");
const fs = require("fs");
const [page_file, state_file, shotDir] = process.argv.slice(2);
const path = require("path");
const url = "file://" + path.resolve(page_file);
const state = JSON.parse(fs.readFileSync(state_file, "utf8"));

const MOCK = `
(function(){
  const store = window.__store = window.__store || {};
  const subs = [];
  window.__mcpCalls = [];
  function snapDoc(p){ return { exists: p in store, data: () => JSON.parse(JSON.stringify(store[p])), id: p.split('/').pop() }; }
  function notify(){ subs.forEach(s => s()); }
  window.__notify = notify;
  function docRef(p){ return {
    id: p.split('/').pop(), path: p,
    get: () => Promise.resolve(snapDoc(p)),
    set: d => { window.__writes = (window.__writes||0)+1; store[p] = JSON.parse(JSON.stringify(d)); setTimeout(notify, 5); return Promise.resolve(); },
    update: d => { if(!(p in store)) return Promise.reject({code:'invalid_argument'}); Object.assign(store[p], d); setTimeout(notify,5); return Promise.resolve(); },
    delete: () => { delete store[p]; setTimeout(notify,5); return Promise.resolve(); },
    onSnapshot: (next) => { const f = () => next(snapDoc(p)); subs.push(f); setTimeout(f, 5); return () => {}; } }; }
  function coll(c){ const q = { orderBy(){ return q; }, limit(){ return q; },
    onSnapshot(next){ const f = () => { const docs = Object.keys(store).filter(k => k.startsWith(c+'/')).map(k => ({ id: k.slice(c.length+1), data: () => JSON.parse(JSON.stringify(store[k])) })).sort((a,b)=>b.data().created_ms-a.data().created_ms); next({ docs }); }; subs.push(f); setTimeout(f,5); return () => {}; },
    doc: id => docRef(c + '/' + (id || Math.random().toString(36).slice(2))) }; return q; }
  const db = { doc: docRef, collection: coll };
  const mcp = { callTool: (s,t,i) => { window.__mcpCalls.push({s,t,i}); return window.__mcpFail ? Promise.reject({code: window.__mcpFail}) : Promise.resolve({payload:{ok:true}}); } };
  window.claude = { use: n => Promise.resolve(n === 'db' ? db : n === 'mcp' ? mcp : null) };
})();`;

let failures = 0;
function ok(cond, name, extra) { if (cond) console.log("ok", name); else { failures++; console.log("FAIL", name, extra || ""); } }

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
  const page = await ctx.newPage();
  const errors = []; page.on("pageerror", e => errors.push(e.message));
  await page.addInitScript(({ mock, st }) => { window.__store = { "view/state": st }; eval(mock); }, { mock: MOCK, st: state });
  await page.goto(url);
  await page.waitForSelector("#submitTurn");
  ok(await page.locator(".budget").count() === 1, "budget pills render");
  ok(await page.locator("fieldset.grp legend", { hasText: "Primary action" }).count() === 1, "composer groups render");

  // Test B in the UI: write the illegal composite turn
  await page.click('[data-mode="write"]');
  await page.fill("#w_write", "I ignite my lightsaber, use Burst, ready a strike against the first dog that lunges, and retreat toward the ramp.");
  await page.waitForTimeout(500);
  const chk = await page.locator(".check").innerText();
  ok(/Not legal yet/.test(chk) && /both require your primary action/.test(chk), "illegal composite flagged before submit", chk);
  ok(/prone does not automatically prevent an opportunity attack/.test(chk), "prone opportunity-attack warning shown");
  ok(await page.locator("#submitTurn").isDisabled(), "submit disabled while illegal");
  ok(await page.locator("[data-alt]").count() >= 2, "legal alternatives offered");

  // pick "Burst + move toward the ramp"
  await page.locator("[data-alt]", { hasText: "Burst" }).first().click();
  await page.waitForTimeout(200);
  ok(await page.locator('input[data-g="action"][value="burst"]').isChecked(), "alternative loads into Build mode");
  ok(await page.locator("#submitTurn").isDisabled(), "risky turn needs confirmation (Test C)");
  ok(/Out of reach: Dog C/.test(await page.locator(".check").innerText()), "Burst area shows who is out of reach");
  await page.check('input[data-g="dialogue"][value="d1"]');
  await page.check("#confirmRisk");
  ok(!(await page.locator("#submitTurn").isDisabled()), "confirmed legal turn can be submitted");
  if (shotDir) await page.screenshot({ path: shotDir + "/composer_desktop.png", fullPage: false });

  // double tap submit (Test H client side)
  await Promise.all([page.click("#submitTurn"), page.click("#submitTurn").catch(() => {})]);
  await page.waitForTimeout(400);
  const acts = await page.evaluate(() => Object.keys(window.__store).filter(k => k.startsWith("actions/")));
  ok(acts.length === 1, "double tap creates exactly one action", acts);
  const doc = await page.evaluate(k => window.__store[k], acts[0]);
  ok(doc.status === "submitted" && doc.declaration.actions[0].option === "burst" && doc.declaration.speech.option === "d1" && doc.confirmed_warnings, "action document carries the validated declaration");
  ok(doc.based_on_revision === state.revision && doc.campaign_id === state.campaign_id, "action pinned to revision and campaign");
  const calls = await page.evaluate(() => window.__mcpCalls);
  ok(calls.length === 1 && calls[0].t === "fire_trigger" && JSON.parse(calls[0].i.text).action_id === acts[0].slice(8), "Submit starts the GM automatically (fire_trigger)", JSON.stringify(calls));
  ok(/GM started/.test(await page.locator(".act").first().innerText()), "player sees the GM was started");
  ok(await page.locator("#submitTurn").isDisabled(), "one turn at a time while the GM works");

  // processor claims, then commits: the page follows the store (no chat message)
  await page.evaluate(k => { window.__store[k].status = "processing"; window.__store[k].processing = { started_ms: Date.now() }; window.__notify(); }, acts[0]);
  await page.waitForTimeout(100);
  { const t = await page.locator(".act").first().innerText(); ok(/Processing/i.test(t), "processing state shown", t); }
  await page.evaluate(k => {
    const v = window.__store["view/state"]; window.__store[k].status = "committed"; window.__store[k].event_id = "evt_0099";
    v.revision += 3; v.feed.push({ who: "gm", event_id: "evt_0098", time: "Day 1, dusk", text: "The ring of force hits the dogs." }); v.turn_context = Object.assign({}, v.turn_context, { context_id: "evt_0100" });
    v.rolls = [{ roll_id: "roll_x", purpose: "Dog A: Dexterity save vs Burst", summary: "1d20+2 [8] +2 = 10", by: "gm" }]; window.__notify(); }, acts[0]);
  await page.waitForTimeout(150);
  ok(/Committed/i.test(await page.locator(".act").first().innerText()) && /ring of force/.test(await page.locator(".feed").innerText()), "committed result and narration appear without a chat message");
  ok(await page.locator(".dice li").count() === 1, "dice for the turn are listed");
  ok(!(await page.locator('input[data-g="action"][value="burst"]').isChecked()), "new turn context starts a fresh composer");

  // reload recovery (Test I client side): same store, fresh page
  const store = await page.evaluate(() => window.__store);
  const page2 = await ctx.newPage();
  await page2.addInitScript(({ mock, st }) => { window.__store = st; eval(mock); }, { mock: MOCK, st: store });
  await page2.goto(url); await page2.waitForSelector(".act");
  ok(/Committed/i.test(await page2.locator(".act").first().innerText()) && /ring of force/.test(await page2.locator(".feed").innerText()), "reopened page shows the actual committed state");

  // needs_revision from the processor shows alternatives and no dice
  await page2.evaluate(() => { window.__store["actions/b2"] = { text: "x", status: "needs_revision", created_ms: Date.now(), campaign_id: window.__store["view/state"].campaign_id, review: { summary: "Burst and Ready both require your primary action.", alternatives: [{ label: "Burst + hold position", declaration: { actor: "aero", actions: [{ option: "burst" }], objects: [], reactions: [], movement: { option: "hold" } } }] } }; window.__notify(); });
  await page2.waitForTimeout(100);
  ok(/No dice were rolled/.test(await page2.locator(".act").first().innerText()) && await page2.locator("[data-ralt]").count() === 1, "needs-revision shows the reason and alternatives");

  // mcp unavailable: submission still saved, honest fallback text
  await page2.evaluate(() => { window.__mcpFail = "approval_required"; });
  await page2.click('input[data-g="action"][value="dodge"]'); await page2.waitForTimeout(100);
  await page2.click("#submitTurn"); await page2.waitForTimeout(300);
  ok(/needs your permission/.test(await page2.locator(".act").first().innerText()), "denied GM start explains how to allow it");

  // Test J: viewing another member never changes the actor
  await page2.evaluate(() => { const v = window.__store["view/state"]; v.roster.push({ id: "varon", name: "Varon", line: "Chiss Trooper", role: "Companion", status: "In party", mechanics: "pending" }); window.__notify(); });
  await page2.waitForTimeout(100);
  await page2.selectOption(".col.left .member-sel", "varon"); await page2.waitForTimeout(100);
  ok(/Viewing only/.test(await page2.locator(".col.left").innerText()) && /Aero/.test(await page2.locator(".composer h2").first().innerText()), "viewing Varon keeps Aero as the actor");

  // usage accounting, continuity status and fair-warning notes are visible
  await page2.evaluate(() => { const v = window.__store["view/state"]; v.continuity = { status: "active", marks: 1 }; v.turn_context.notes = ["The grass is long enough to hide something lying flat."];
    window.__store["usage/r1"] = { campaign_id: v.campaign_id, outcome: "committed", started_ms: Date.now() - 120000, finished_ms: Date.now() }; window.__notify(); });
  await page2.waitForTimeout(150);
  await page2.selectOption(".col.left .member-sel", "aero"); await page2.waitForTimeout(100);
  ok(/Cloud GM usage[\s\S]*Sessions[\s\S]*1[\s\S]*2\.0 min/i.test(await page2.locator(".col.right").innerText()), "cloud usage shown");
  ok(/Protagonist Continuity\s*protected · 1 mark/i.test(await page2.locator(".col.left").innerText()), "continuity status shown");
  ok(/What you notice[\s\S]*hide something lying flat/i.test(await page2.locator(".composer").innerText()), "fair-warning notes shown");

  // mobile layout
  // The published skeleton adds a viewport meta; locally we emulate the phone layout viewport directly.
  const m = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, hasTouch: true });
  const mp = await m.newPage();
  await mp.addInitScript(({ mock, st }) => { window.__store = { "view/state": st }; eval(mock); }, { mock: MOCK, st: state });
  await mp.goto(url); await mp.waitForSelector("#submitTurn");
  const sw = await mp.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  ok(sw <= 0, "no horizontal scroll on phone", sw);
  const small = await mp.evaluate(() => [...document.querySelectorAll(".opt")].filter(e => e.getBoundingClientRect().height < 40 && e.offsetParent).length);
  ok(small === 0, "touch targets at least 40px tall", small);
  if (shotDir) { await mp.screenshot({ path: shotDir + "/composer_phone.png", fullPage: true }); }

  ok(errors.length === 0, "no page errors", errors.join(" | "));
  await browser.close();
  console.log(failures ? failures + " FAILED" : "all passed");
  process.exit(failures ? 1 : 0);
})();
