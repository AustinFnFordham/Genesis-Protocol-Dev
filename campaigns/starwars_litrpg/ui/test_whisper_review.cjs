// WHISPER post-turn review card (switch whisper_review; owner decisions 1-2). node test_whisper_review.cjs <page> <state>
const fs = require("fs"), path = require("path");
const { chromium } = require("playwright");
const [pageFile, stateFile] = process.argv.slice(2);
const st = JSON.parse(fs.readFileSync(stateFile));
const MOCK = fs.readFileSync(path.join(__dirname, "test_datapad_ui.cjs"), "utf8").match(/const MOCK = `([\s\S]*?)`;/)[1];
const PENDING = { review_id: "evt_0900", action_id: "a1", note: "Suggestions only. Nothing changes for Aero unless you accept, edit or write your own.",
  candidates: [{ candidate_id: "wc_aaaa", theme: "loss_after_trying", kind: "temporary", proposed: "Grief, or blaming himself for not reaching them in time.", explanation: "He tried to help and it failed; he did it to save Wick.", evidence: ["evt_0202"] },
               { candidate_id: "wc_bbbb", theme: "weight_of_the_strike", kind: "prompt", proposed: null, explanation: "How does Aero feel about it — if anything? Your words only.", evidence: ["evt_0203"] }] };
let failures = 0;
const ok = (c, n, x) => { if (c) console.log("ok", n); else { failures++; console.log("FAIL", n, x || ""); } };
(async () => {
  const browser = await chromium.launch();
  try {
    async function open(features, vp) {
      const page = await (await browser.newContext({ viewport: vp || { width: 820, height: 1180 } })).newPage();
      const errors = []; page.on("pageerror", (e) => errors.push(e.message));
      const s = JSON.parse(JSON.stringify(st)); delete s.features; if (features) s.features = features; s.whisper = { pending: PENDING, history: [] };
      s.processor = { server: "Claude Code Remote", trigger_id: "trig_test" };
      await page.addInitScript(({ mock, st }) => { window.__store = { "view/state": st }; eval(mock); }, { mock: MOCK, st: s });
      await page.goto(require(require("path").join(__dirname, "hosted_url.cjs")).hostedUrl(pageFile)); await page.waitForSelector("#submitTurn");
      return { page, errors };
    }
    { const { page } = await open(null); ok(await page.locator("#whisperReview").count() === 0, "switch off: no review card"); }
    const { page, errors } = await open({ whisper_review: true });
    ok(await page.locator("#whisperReview").count() === 1, "switch on: review card shown");
    const txt = await page.locator("#whisperReview").innerText();
    ok(/Grief, or blaming himself/.test(txt) && /evt_0202/.test(txt) && /Nothing here changes Aero unless you choose it/.test(txt), "each suggestion shows its reason and evidence");
    ok(await page.locator('[data-whresp="wc_bbbb|accept"]').count() === 0, "a prompt has no Accept: only the player's words");
    await page.locator('[data-whresp="wc_bbbb|edit"]').click(); await page.waitForTimeout(200);
    ok(/Write your words first/.test(await page.locator("#whMsg").innerText()), "saving words needs words");
    ok(await page.evaluate(() => Object.keys(window.__store).filter((k) => k.startsWith("actions/")).length) === 0, "nothing was sent");
    await page.locator('[data-whresp="wc_aaaa|accept"]').click(); await page.waitForTimeout(400);
    const rows = await page.evaluate(() => Object.keys(window.__store).filter((k) => k.startsWith("actions/")).map((k) => window.__store[k]));
    ok(rows.length === 1 && rows[0].kind === "whisper_response" && rows[0].whisper.choice === "accept" && rows[0].whisper.candidate_id === "wc_aaaa" && rows[0].whisper.review_id === "evt_0900", "Accept sends exactly that answer", JSON.stringify(rows));
    ok(!rows[0].declaration, "an answer is not a turn: no declaration");
    const calls = await page.evaluate(() => window.__mcpCalls);
    ok(calls.length === 1 && JSON.parse(calls[0].i.text).action_id && calls[0].t === "fire_trigger", "the GM worker is started to record it");
    const { page: p2 } = await open({ whisper_review: true });
    await p2.fill("#w_whcustom", "Numb. He keeps moving."); await p2.locator('[data-whresp="__custom|custom"]').click(); await p2.waitForTimeout(400);
    const r2 = await p2.evaluate(() => { const k = Object.keys(window.__store).find((x) => x.startsWith("actions/")); return window.__store[k]; });
    ok(r2.whisper.choice === "custom" && r2.whisper.candidate_id === null && r2.whisper.text === "Numb. He keeps moving.", "a fully custom response is kept verbatim");
    const { page: ph } = await open({ whisper_review: true }, { width: 390, height: 844 });
    ok(await ph.evaluate(() => document.documentElement.scrollWidth - innerWidth) <= 0, "no horizontal scroll at phone width");
    const small = await ph.evaluate(() => [...document.querySelectorAll("#whisperReview button")].filter((b) => b.getBoundingClientRect().height < 44).length);
    ok(small === 0, "review buttons meet the 44px touch target", small);
    if (process.argv[4]) { await ph.locator("#whisperReview").scrollIntoViewIfNeeded(); await ph.screenshot({ path: process.argv[4] }); }
    ok(errors.length === 0, "no page errors", errors.join("|"));
  } finally { await browser.close(); }
  console.log(failures ? failures + " FAILED" : "all passed"); process.exit(failures ? 1 : 0);
})();
