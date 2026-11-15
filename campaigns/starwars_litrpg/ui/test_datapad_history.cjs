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
  // Any number of pages per kind. The expected record is the manifest's pages in order, capped at the published revision.
  const seq = id => parseInt(String(id).split("_")[1], 10);
  const expected = kind => h[kind].pages.flatMap(m => store["view/" + m.id].entries.map(e => e.event_id));
  const pageGets = async kind => (await page.evaluate(() => window.__gets)).filter(p => p.startsWith("view/" + kind + "-"));
  const shown = sel => page.locator(sel).evaluateAll(els => els.map(e => e.getAttribute("data-eid")));
  const wantFeed = expected("feed");
  ok(wantFeed.length === h.feed.total && new Set(wantFeed).size === wantFeed.length, "fixture: the feed pages hold the whole record once (" + h.feed.pages.length + " page(s))", wantFeed.length + " of " + h.feed.total);
  let clicks = 0, growth = [], last = state.feed.length;
  while (clicks < 200 && await btn.count()) {
    await btn.click(); await page.waitForTimeout(80); clicks++;
    const now = (await shown("#colRight .previous-history > div")).length; growth.push(now - last); last = now;
  }
  const ids = await shown("#colRight .previous-history > div");
  ok(ids.length === h.feed.total && new Set(ids).size === ids.length, "after loading, every entry appears exactly once", ids.length + " of " + h.feed.total);
  ok(ids.join() === wantFeed.join(), "completeness and order: the loaded narrative is exactly the pages' record, in page order");
  ok(ids.every((id, i) => i === 0 || seq(ids[i - 1]) < seq(id)) && ids[ids.length - 1] === state.feed[state.feed.length - 1].event_id, "entries stay in story order, newest last");
  ok(ids.indexOf(firstBefore) === h.feed.omitted, "the earlier entries are placed before the preview");
  const feedGets = await pageGets("feed");
  ok(new Set(feedGets).size === feedGets.length, "pagination: no feed page is fetched twice", feedGets.join());
  // A tap loads the next older page; if that page holds nothing new (it is already in the preview) the same tap goes on to the one before.
  ok(feedGets.length <= h.feed.pages.length && feedGets.length >= clicks && clicks >= 1, "pagination: a page at a time, never more pages than exist", clicks + " taps, " + feedGets.length + " fetches, " + h.feed.pages.length + " pages");
  ok(feedGets.join() === feedGets.slice().sort().reverse().join(), "pagination: pages load newest first, working back", feedGets.join());
  ok(growth.every(g => g > 0) && growth.reduce((a, b) => a + b, 0) === h.feed.omitted, "every tap adds entries, and only ones that were not shown yet", growth.join());
  ok(await page.locator('[data-older="feed"]').count() === 0, "button goes away when nothing older remains");
  // Duplicate prevention: a refresh of the same snapshot, and a page that repeats entries already shown, add nothing.
  await page.evaluate(() => window.__notify()); await page.waitForTimeout(150);
  const again = await shown("#colRight .previous-history > div");
  ok(again.join() === ids.join() && (await pageGets("feed")).length === feedGets.length, "a snapshot refresh neither duplicates entries nor refetches pages");
  // journal
  const jb = page.locator('[data-older="journal"]');
  ok(await jb.count() === 1, "journal offers earlier entries");
  ok(new RegExp("^\\s*" + h.journal.observations + " observed").test(await page.locator(".panel", { hasText: "Discoveries" }).last().locator(".note").innerText()), "discoveries count comes from the full record, not the preview");
  let jclicks = 0;
  while (jclicks < 200 && await jb.count()) { await jb.click(); await page.waitForTimeout(80); jclicks++; }
  ok(await page.locator("#journalEntries ul.plain > li").count() === h.journal.total, "journal shows the full record after loading", (await page.locator("#journalEntries ul.plain > li").count()) + " of " + h.journal.total);
  const journalGets = await pageGets("journal"), wantJournal = expected("journal");
  ok(wantJournal.length === h.journal.total && new Set(journalGets).size === journalGets.length && journalGets.length >= jclicks && journalGets.length <= h.journal.pages.length &&
     journalGets.join() === journalGets.slice().sort().reverse().join(),
     "journal pagination: " + h.journal.pages.length + " page(s), a page at a time, newest first, none twice", jclicks + " taps, " + journalGets.join());
  const jids = (await shown("#journalEntries ul.plain > li")).filter(Boolean);
  if (jids.length) ok(jids.join() === wantJournal.join(), "journal entries are complete, unique and in record order");
  ok(await page.locator('[data-older="journal"]').count() === 0, "journal button goes away when nothing older remains");
  // a page written ahead of the snapshot never shows entries newer than the published revision
  // ... on whichever page is the newest, and with an entry repeated across two pages shown once
  const newest = h.feed.pages[h.feed.pages.length - 1].id, oldest = h.feed.pages[0].id;
  await page.evaluate(({ newest, oldest, multi }) => { const s = window.__store;
    s["view/" + newest].entries.push({ who: "gm", event_id: "evt_99999", time: "later", text: "NOT YET PUBLISHED" });
    if (multi) s["view/" + newest].entries.unshift(JSON.parse(JSON.stringify(s["view/" + oldest].entries[s["view/" + oldest].entries.length - 1]))); },
    { newest, oldest, multi: h.feed.pages.length > 1 });
  await page.reload(); await page.locator("summary", { hasText: "Previous Turns" }).click(); await page.waitForSelector('[data-older="feed"]');
  for (let i = 0; i < 200 && await page.locator('[data-older="feed"]').count(); i++) { await page.click('[data-older="feed"]'); await page.waitForTimeout(80); }
  ok(!/NOT YET PUBLISHED/.test(await page.locator("#colRight .previous-history").innerText()), "entries beyond the published revision stay hidden");
  const deduped = await shown("#colRight .previous-history > div");
  ok(new Set(deduped).size === deduped.length && deduped.length === h.feed.total, "an entry repeated on two pages is shown once", deduped.length + " shown, " + new Set(deduped).size + " unique, " + h.feed.total + " expected");
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
