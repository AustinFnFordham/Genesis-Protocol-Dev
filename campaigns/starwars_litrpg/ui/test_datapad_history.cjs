// Browser tests for the bounded snapshot + on-demand history pages and the separate publication status.
// Usage: node test_datapad_history.cjs <page.html> <publish_dir>   (publish_dir = `turn.py publish --outdir`, holding view/*.json)
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
const [page_file, dir] = process.argv.slice(2);
const url = "file://" + path.resolve(page_file);
const store = {};
for (const f of fs.readdirSync(path.join(dir, "view"))) store["view/" + f.replace(/\.json$/, "")] = JSON.parse(fs.readFileSync(path.join(dir, "view", f), "utf8"));
const state = store["view/state"];
const MOCK = `
(function(){
  const store = window.__store; const subs = []; window.__gets = [];
  function snapDoc(p){ return { exists: p in store, data: () => JSON.parse(JSON.stringify(store[p])), id: p.split('/').pop() }; }
  window.__notify = () => subs.forEach(s => s());
  function docRef(p){ return { id: p.split('/').pop(), path: p,
    get: () => { window.__gets.push(p); return Promise.resolve(snapDoc(p)); },
    set: d => { store[p] = JSON.parse(JSON.stringify(d)); setTimeout(window.__notify, 5); return Promise.resolve(); },
    delete: () => { delete store[p]; setTimeout(window.__notify, 5); return Promise.resolve(); },
    onSnapshot: next => { const f = () => next(snapDoc(p)); subs.push(f); setTimeout(f, 5); return () => {}; } }; }
  function coll(c){ const q = { orderBy(){ return q; }, limit(){ return q; },
    onSnapshot(next){ const f = () => next({ docs: Object.keys(store).filter(k => k.startsWith(c + '/') && (c !== 'view')).map(k => ({ id: k.slice(c.length + 1), data: () => JSON.parse(JSON.stringify(store[k])) })) }); subs.push(f); setTimeout(f, 5); return () => {}; },
    doc: id => docRef(c + '/' + id) }; return q; }
  window.claude = { use: n => Promise.resolve(n === 'db' ? { doc: docRef, collection: coll } : null) };
})();`;
let failures = 0;
function ok(c, name, extra) { if (c) console.log("ok", name); else { failures++; console.log("FAIL", name, extra === undefined ? "" : extra); } }
(async () => {
  const browser = await chromium.launch();
  const page = await (await browser.newContext({ viewport: { width: 1400, height: 1000 } })).newPage();
  const errors = []; page.on("pageerror", e => errors.push(e.message));
  await page.addInitScript(({ mock, st }) => { window.__store = st; eval(mock); }, { mock: MOCK, st: store });
  await page.goto(url);
  await page.waitForSelector("#colCenter .feed > div");
  const h = state.history;
  ok(Buffer.byteLength(JSON.stringify(state)) <= h.budget_bytes, "snapshot is under its byte budget");
  ok(await page.locator("#colCenter .feed > div").count() === 1, "Scene renders only the latest complete GM narration");
  await page.locator("summary", { hasText: "Previous Turns" }).click();
  ok(await page.locator("#colRight .previous-history > div").count() === state.feed.length, "Journal starts with the bounded preview");
  ok((await page.evaluate(() => window.__gets)).every(p => !/feed-|journal-/.test(p)), "no history page is fetched until asked");
  const btn = page.locator('[data-older="feed"]');
  ok(await btn.count() === 1 && new RegExp("\\(" + h.feed.omitted + " older\\)").test(await btn.innerText()), "load-earlier shows how many are older", await btn.innerText().catch(() => ""));
  const firstBefore = await page.locator("#colRight .previous-history > div").first().getAttribute("data-eid");
  for (let i = 0; i < 20 && await btn.count(); i++) { await btn.click(); await page.waitForTimeout(80); }
  const ids = await page.locator("#colRight .previous-history > div").evaluateAll(els => els.map(e => e.getAttribute("data-eid")));
  ok(ids.length === h.feed.total && new Set(ids).size === ids.length, "after loading, every entry appears exactly once", ids.length + " of " + h.feed.total);
  ok(ids.join() === ids.slice().sort().join() && ids[ids.length - 1] === state.feed[state.feed.length - 1].event_id, "entries stay in story order, newest last");
  ok(ids.indexOf(firstBefore) === h.feed.omitted, "the earlier entries are placed before the preview");
  ok(await page.locator('[data-older="feed"]').count() === 0, "button goes away when nothing older remains");
  // journal
  const jb = page.locator('[data-older="journal"]');
  ok(await jb.count() === 1, "journal offers earlier entries");
  ok(new RegExp("^\\s*" + h.journal.observations + " observed").test(await page.locator(".panel", { hasText: "Discoveries" }).last().locator(".note").innerText()), "discoveries count comes from the full record, not the preview");
  for (let i = 0; i < 20 && await jb.count(); i++) { await jb.click(); await page.waitForTimeout(80); }
  ok(await page.locator("#journalEntries ul.plain > li").count() === h.journal.total, "journal shows the full record after loading");
  // a page written ahead of the snapshot never shows entries newer than the published revision
  await page.evaluate(() => { const s = window.__store; s["view/feed-0001"].entries.push({ who: "gm", event_id: "evt_9999", time: "later", text: "NOT YET PUBLISHED" }); });
  await page.reload(); await page.locator("summary", { hasText: "Previous Turns" }).click(); await page.waitForSelector('[data-older="feed"]'); await page.click('[data-older="feed"]'); await page.waitForTimeout(300);
  ok(!/NOT YET PUBLISHED/.test(await page.locator("#colRight .previous-history").innerText()), "entries beyond the published revision stay hidden");
  // resolution and publication are separate
  await page.evaluate(cid => { window.__store["actions/a1"] = { status: "resolved", text: "I wait.", campaign_id: cid, created_ms: Date.now(), commit: "c3a2054abc", publication: { status: "pending", last_error: "view/state write refused" } }; window.__notify(); }, state.campaign_id);
  await page.waitForTimeout(200);
  const act = await page.locator(".act").first().innerText();
  ok(/Resolved · Publication pending/i.test(act) && !/Failed/.test(act), "resolved turn shows publication pending, not failed", act);
  ok(/Retry/.test(act) && /nothing is rolled again/i.test(act) && /view\/state write refused/.test(act), "retry offered with the reason");
  ok(await page.locator("#submitTurn").count() === 0 || await page.locator("#submitTurn").isDisabled(), "no new turn can be submitted while publication is pending");
  // an older snapshot without a manifest still renders (page and data roll out independently)
  await page.evaluate(() => { const s = window.__store["view/state"]; delete s.history; window.__notify(); });
  await page.waitForTimeout(200);
  ok(await page.locator("#colRight .previous-history > div").count() > 0 && await page.locator("[data-older]").count() === 0, "a snapshot without history still renders");
  ok(errors.length === 0, "no page errors", errors.join(" | "));
  await browser.close();
  console.log(failures ? "FAILED " + failures : "all ok");
  process.exit(failures ? 1 : 0);
})();
