// CC-005c thin PLAYER client: no private data in the page or on the wire; a full fight with only the player token.
const { chromium, devices } = require("playwright");
const { spawn } = require("child_process"); const path = require("path"), fs = require("fs"), os = require("os");
let fails = 0; const ok = (c, n, x) => { console.log((c ? "ok " : "FAIL ") + n + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 300))); if (!c) fails++; };
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "play-")), port = 24000 + Math.floor(Math.random() * 2000);
const srv = spawn("python3", ["-B", path.join(__dirname, "../preview/serve_preview.py"), "--port", String(port)], { env: Object.assign({}, process.env, { GENESIS_ATOMIC_DIR: dir }), stdio: "ignore" });
const base = "http://127.0.0.1:" + port;
// Strings that would prove private enemy data or authority code reached the browser.
const FORBIDDEN = [/"ac":15\b/, /"hp_max":20\b/, /"hp":20\b/, /stealth_dc/, /"skills"/, /"grants"/, /"profiles"/, /npc_plan/, /"seed"/, /gm_token/, /"deception":/, /"insight":3/, /"form":/, /resolveTurn/, /GenesisCombat/, /npc_blade/, /npc_parry/, /npc_riposte/];
const G = (p, fn) => p.evaluate(fn);
async function ready(p) { await p.waitForFunction(() => window.__genesisPlay && window.__genesisPlay.view() && !window.__genesisPlay.busy(), null, { timeout: 20000 }); }
async function show(p, pid) {   // open the card's category on the rail (cards of other categories are hidden)
  const c = p.locator(`[data-pid="${pid}"]`); if (!(await c.count()) || (await c.isVisible())) return;
  const t = p.locator('.tabs [data-tab="actions"]'); if (await t.isVisible()) await t.click();
  const cat = await c.getAttribute("data-cat"); if (cat && !(await c.isVisible())) await p.locator(`[data-rail="${cat}"]`).click();
}
async function drive(p) {   // answer every player checkpoint until it is our planning turn or the fight ends
  for (let i = 0; i < 300; i++) {
    await ready(p); const k = await G(p, () => window.__genesisPlay.view().checkpoint.kind);
    if (k === "plan" || k === "over") return k;
    if (k === "roll") { await p.locator("#rollBtn").click(); await p.waitForTimeout(80); continue; }
    if (k === "decision") { await p.locator("#checkpoint [data-opt]").first().click(); await p.waitForTimeout(80); continue; }
    await p.waitForTimeout(150);
  }
}
(async () => {
  for (let i = 0; i < 100; i++) { try { await fetch(base + "/healthz"); break; } catch (e) { await new Promise((r) => setTimeout(r, 150)); } }
  const browser = await chromium.launch();
  try {
    const html = await (await fetch(base + "/play.html")).text();
    const hit = FORBIDDEN.filter((re) => re.test(html)).map(String); ok(hit.length === 0, "the page source contains no engine, rules, scenario or enemy data", hit);
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } }); const p = await ctx.newPage();
    const wire = []; p.on("response", async (r) => { if (r.url().includes("/atomic/")) { try { wire.push(await r.text()); } catch (e) {} } });
    const errs = []; p.on("pageerror", (e) => errs.push(e.message));
    await p.goto(base + "/play.html"); await ready(p);
    ok((await G(p, () => window.__genesisPlay.view().checkpoint.kind)) === "plan", "a fresh duel starts at Aero's planning checkpoint");
    ok(/Out of reach/.test(await p.locator('[data-pid="saber_strike"]').innerText()), "server-computed reasons on cards");
    // category rail: categories come from the server's card data; one category shown at a time; disabled cards stay inspectable
    const cats = await G(p, () => window.__genesisPlay.view().cards.map((c) => [c.pid, c.category]));
    ok(cats.every((x) => typeof x[1] === "string" && x[1]) && new Set(cats.map((x) => x[1])).size >= 4, "every card carries a server-assigned category", cats);
    ok(await G(p, () => [...document.querySelectorAll("[data-rail]")].every((r) => window.__genesisPlay.view().cards.some((c) => c.category === r.dataset.rail) || r.dataset.rail === "off")), "the rail lists only categories present in the server's cards");
    ok(await G(p, () => { const sel = document.querySelector("[data-rail][aria-selected=true]").dataset.rail; return [...document.querySelectorAll(".card[data-pid]")].every((c) => (c.dataset.cat === sel) === !c.hidden); }), "only the selected category's cards are shown");
    ok(await G(p, () => { const r = window.__genesisPlay.view().cards.filter((c) => c.reaction); return r.every((c) => c.category === "reaction"); }), "reactions stay their own category (not merged with look-alikes)");
    await show(p, "saber_strike"); await p.locator('[data-pid="saber_strike"]').click({ force: true });   /* aria-disabled: Playwright would refuse; a finger does not */ await p.waitForSelector("#drawer[open]");
    ok(/Can't use now:.*Out of reach/s.test(await p.locator("#drawerBody").innerText()) && (await G(p, () => window.__genesisPlay.plan().length)) === 0, "tapping a disabled card explains why (and adds nothing)");
    await p.locator("#drawerClose").click();
    ok(!(await G(p, () => localStorage.getItem("genesis.play.token") === null)) && !(await G(p, () => JSON.stringify(localStorage).includes("gm"))), "only the player token is kept; no GM token in the client");
    // build a turn by tapping; preflight is server-side
    const tap = async (pid) => { await ready(p); await show(p, pid); await p.locator(`[data-pid="${pid}"]`).click(); if (await p.locator("#dlg[open]").count()) await p.locator("#dlgBody [data-o]").first().click(); await ready(p); };
    for (const c of ["move", "feint", "saber_strike", "flow_strike"]) await tap(c);
    await p.waitForFunction(() => document.querySelector("[data-combo]"));
    ok(/Echani Flow Line/.test(await p.locator("#combo").innerText()), "server-predicted synergy shown");
    ok(/\d+%–\d+% hit\*/.test(await p.locator("#plan").innerText()), "odds are ranges from learned AC (not exact enemy numbers)", await p.locator("#plan").innerText());
    await p.locator("#plan [data-up='2']").click(); await ready(p); await p.locator("#plan [data-dn='1']").click(); await ready(p);
    ok(JSON.stringify(await G(p, () => window.__genesisPlay.plan().map((s) => s.pid))) === '["move","feint","saber_strike","flow_strike"]', "reorder up/down works");
    await p.locator("#commit").click(); await ready(p);
    const kk = await G(p, () => [window.__genesisPlay.view().checkpoint.kind, document.getElementById("err").textContent, window.__genesisPlay.plan().length]);
    await p.waitForFunction(() => window.__genesisPlay.view().checkpoint.kind === "roll" && !window.__genesisPlay.busy(), null, { timeout: 15000 }).catch(() => {});
    ok((await G(p, () => window.__genesisPlay.view().checkpoint.kind)) === "roll" && /PLAYER — AERO/.test(await p.locator("#checkpoint").innerText()), "the turn waits for the player's Roll button");
    const cpText = await p.locator("#checkpoint").innerText(); ok(!/AC 15/.test(cpText), "the roll prompt does not reveal the enemy's AC", cpText);
    // reconnect mid-roll: same session, same pending roll, nothing rolled
    const sid = await G(p, () => window.__genesisPlay.session()); await p.reload(); await ready(p);
    ok((await G(p, () => window.__genesisPlay.session())) === sid && (await G(p, () => window.__genesisPlay.view().checkpoint.kind)) === "roll", "reload mid-roll: same session, still waiting on the player's roll");
    // play the fight out
    let result = null;
    for (let t = 0; t < 40 && !result; t++) {
      const k = await drive(p); if (k === "over") { result = await G(p, () => window.__genesisPlay.view().over); break; }
      for (const c of ["recover_weapon", "move", "saber_strike", "unarmed_strike", "flow_strike"]) { await ready(p); const b = p.locator(`[data-pid="${c}"][aria-disabled="false"]`); if (await b.count()) { await show(p, c); await b.click(); if (await p.locator("#dlg[open]").count()) await p.locator("#dlgBody [data-o]").first().click(); await ready(p); } }
      await ready(p);
      if (await p.locator("#commit").isDisabled()) { const any = p.locator('[data-pid][aria-disabled="false"]').first(); if (await any.count()) { await show(p, await any.getAttribute("data-pid")); await any.click(); if (await p.locator("#dlg[open]").count()) await p.locator("#dlgBody [data-o]").first().click(); await ready(p); } }
      if (!(await p.locator("#commit").isDisabled())) { await p.locator("#commit").click(); if (await p.locator("#cYes").count()) await p.locator("#cYes").click(); }
    }
    ok(!!result, "a whole duel played in the thin client (" + result + ")");
    ok(await p.locator("#laneG .roll").count() > 0 && await p.locator("#laneG button").count() === 0, "GM rolls appear in the GM lane with no player button");
    ok(await p.locator("#story .beat").count() > 0, "server-side Soul narration is shown");
    const leaks = []; wire.forEach((t, i) => FORBIDDEN.forEach((re) => { if (re.test(t)) leaks.push(String(re) + " in response " + i); }));
    ok(leaks.length === 0, "no enemy-private data or authority code in any of " + wire.length + " server responses", leaks.slice(0, 5));
    ok(errs.length === 0, "no page errors", errs);
    await ctx.close();
    // phone
    const c2 = await browser.newContext({ ...devices["Pixel 5"] }); const q = await c2.newPage(); await q.goto(base + "/play.html"); await ready(q);
    ok((await G(q, () => document.documentElement.scrollWidth - window.innerWidth)) <= 1, "phone: no horizontal scroll");
    const small = await q.$$eval("button", (els) => els.filter((e) => { const r = e.getBoundingClientRect(); return r.width && r.height && (r.height < 43.5 || r.width < 43.5); }).map((e) => e.outerHTML.slice(0, 60)));
    ok(small.length === 0, "phone: tap targets ≥ 44 px", small.slice(0, 3));
    await c2.close();
  } catch (e) { fails++; console.log("FAIL exception", e.stack); }
  finally { srv.kill(); await browser.close(); }
  console.log(fails ? fails + " FAILED" : "all passed"); process.exit(fails ? 1 : 0);
})();
