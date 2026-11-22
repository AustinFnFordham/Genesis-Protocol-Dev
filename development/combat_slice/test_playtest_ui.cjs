// CC-004 Combat v0.4 in a real browser. Offline file (practice dice) + the preview server (Atomic dice, reconnect).
// node test_playtest_ui.cjs
const { chromium, devices } = require("playwright");
const path = require("path"), fs = require("fs"), os = require("os");
const { execFileSync, spawn } = require("child_process");
const page = execFileSync("python3", ["-B", path.join(__dirname, "build_playtest.py")]).toString().trim();
const fileUrl = "file://" + page;
const P = require("./predict.js"), D = require("./turn_driver.js");
let failures = 0;
const ok = (c, n, x) => { if (c) console.log("ok", n); else { failures++; console.log("FAIL", n, x == null ? "" : JSON.stringify(x).slice(0, 300)); } };
const G = (p, fn) => p.evaluate(fn);
async function center(loc, fy) { const b = await loc.boundingBox(); return { x: b.x + b.width / 2, y: b.y + b.height * (fy == null ? 0.5 : fy) }; }
async function mouseDrag(p, from, to, fy) { await from.scrollIntoViewIfNeeded(); const a = await center(from); await p.mouse.move(a.x, a.y); await p.mouse.down(); let b; for (let i = 1; i <= 14; i++) { b = await center(to, fy); await p.mouse.move(a.x + (b.x - a.x) * i / 14, a.y + (b.y - a.y) * i / 14); } await p.mouse.up(); await p.waitForTimeout(60); }
async function aboveDock(p, loc) { await loc.scrollIntoViewIfNeeded(); const b = await loc.boundingBox(), d = await p.locator("#dock").boundingBox(); if (d && d.y > 50 && b.y + b.height > d.y - 8) await p.evaluate((dy) => window.scrollBy(0, dy), b.y + b.height - d.y + 16); await p.waitForTimeout(50); }
async function touchDrag(p, cdp, from, to, fy) { await aboveDock(p, from); const a = await center(from); let b;
  await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: a.x, y: a.y }] });
  for (let i = 1; i <= 14; i++) { b = await center(to, fy); await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: a.x + (b.x - a.x) * i / 14, y: a.y + (b.y - a.y) * i / 14 }] }); await p.waitForTimeout(16); }
  await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); await p.waitForTimeout(80); }
const plan = (p) => G(p, () => window.__genesisCombat.plan().map((s) => s.pid));
async function ready(p) { await p.waitForFunction(() => window.__genesisCombat && window.__genesisCombat.authority() && !window.__genesisCombat.busy() && document.querySelector("[data-card]"), null, { timeout: 15000 }); }
async function closeIn(p) { await G(p, () => { const s = window.__genesisCombat.state(); Object.keys(s.dist).forEach((k) => s.dist[k] = 5); }); await p.locator("#clear").click(); }
// Drive whatever the page is waiting for: reactions, Aero's Roll button; until not busy.
async function drive(p, react) { for (let i = 0; i < 200; i++) { if (await p.locator("#react[open]").count()) { const pos = p.locator("#reactBody [data-react]:not([data-react=''])"); if (react !== "none" && await pos.count()) await pos.first().click(); else await p.locator("#reactBody [data-react='']").click(); }
    const rb = p.locator("[data-roll]:not([disabled])"); if (await rb.count()) await rb.first().click();
    if (!(await G(p, () => window.__genesisCombat.busy())) && !(await p.locator("#react[open]").count())) return; await p.waitForTimeout(60); } }
async function playOut(p) { for (let t = 0; t < 30; t++) { await drive(p); if (await G(p, () => !!window.__genesisCombat.state().over)) return true; await p.locator("#clear").click();
    for (const c of ["recover_weapon", "move", "saber_strike", "unarmed_strike", "blaster_shot", "flow_strike"]) { const el = p.locator(`[data-card="${c}"][data-off="false"]`); if (await el.count()) { await el.click(); if (await p.locator("#pick[open]").count()) await p.locator("#pickBody button").first().click(); } }
    if (await p.locator("#resolve").isDisabled()) { const any = p.locator(`[data-card][data-off="false"]`); if (await any.count()) await any.first().click(); if (await p.locator("#pick[open]").count()) await p.locator("#pickBody button").first().click(); }
    if (!(await p.locator("#resolve").isDisabled())) { await p.locator("#resolve").click(); if (await p.locator("#confirm[open]").count()) await p.locator("#confirmYes").click(); } }
  return G(p, () => !!window.__genesisCombat.state().over); }

(async () => {
  const browser = await chromium.launch();
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "atomic-ui-")), port = 18000 + Math.floor(Math.random() * 2000);
  const srv = spawn("python3", ["-B", path.join(__dirname, "../preview/serve_preview.py"), "--port", String(port)], { env: Object.assign({}, process.env, { GENESIS_ATOMIC_DIR: dir }), stdio: "ignore" });
  try {
    // ================= desktop, offline file =================
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 950 } });
    const p = await ctx.newPage(); const errors = []; p.on("pageerror", (e) => errors.push(e.message));
    await p.goto(fileUrl); await ready(p);
    ok((await G(p, () => window.__genesisCombat.authority())) === "offline-practice" && /NOT authoritative/.test(await p.locator("#theaterAuth").innerText()), "standalone file: dice are labelled offline practice, NOT authoritative");
    const groups = await p.$$eval("details.grp", (d) => d.map((x) => x.dataset.grp));
    ok(JSON.stringify(groups) === JSON.stringify(["maneuvers", "attacks", "main", "secondary", "bonus", "reactions", "movement", "object", "free", "absent"]), "groups: Maneuvers, Attack, Main, Secondary, Bonus, Reactions, Movement, Object, Free, Not-on-sheet", groups);
    const attacks = await p.$$eval("details[data-grp=attacks] [data-card]", (d) => d.map((x) => x.dataset.card).sort());
    ok(JSON.stringify(attacks) === JSON.stringify(["blaster_shot", "grapple", "saber_strike", "saber_strike_2h", "unarmed_strike"]), "Attack selector lists every execution: saber 1H/2H, unarmed, blaster, grapple", attacks);
    ok(/Draw your blaster pistol first/.test(await p.locator('[data-card="blaster_shot"]').innerText()), "unavailable blaster says why (draw it first)");
    await p.locator("details[data-grp=absent] > summary").click();
    ok(/Telekinesis/.test(await p.locator("details[data-grp=absent]").innerText()) && /Not on Aero's sheet/.test(await p.locator("details[data-grp=absent]").innerText()), "telekinesis appears as not on the sheet, with the reason");
    ok(/never triggers here/.test(await p.locator("[data-reaction=sentinel_balance]").innerText()), "inert sheet reaction (Sentinel Balance) says why it never triggers");
    // D1: campaign-grant overlay
    await p.locator("#campaignOverlay").check(); await ready(p);
    ok(/Campaign ruling/i.test(await p.locator('[data-card="minor_telekinesis"]').innerText()) && !/Minor Telekinesis/.test(await p.locator("details[data-grp=absent]").innerText()), "overlay on: Minor Telekinesis appears as a Campaign ruling card (not on the sheet)");
    ok(/unattended|Nothing of yours/i.test(await p.locator('[data-card="minor_telekinesis"]').innerText()), "with nothing loose, Telekinesis explains why it is unavailable");
    await G(p, () => { const s = window.__genesisCombat.state(); const a = s.actors.aero; a.dropped = JSON.parse(JSON.stringify(a.weapon)); a.weapon.held = false; a.weapon.ignited = false; }); await p.locator("#clear").click();
    await p.locator('[data-card="minor_telekinesis"]').click(); await p.locator("#pickBody [data-obj='own_weapon']").click();
    ok(JSON.stringify(await plan(p)) === '["minor_telekinesis"]' && /Main/.test(await p.locator("#timeline .step").first().innerText()), "Telekinesis picks a loose object and costs the Main action");
    await p.locator("#campaignOverlay").uncheck(); await ready(p);
    ok(await p.locator('[data-card="minor_telekinesis"]').count() === 0, "overlay off: no Telekinesis card");
    // sticky composer: scroll the library; the timeline stays on screen
    await p.locator("details[data-grp=object]").scrollIntoViewIfNeeded(); await p.mouse.wheel(0, 900); await p.waitForTimeout(150);
    const tb = await p.locator("#timeline").boundingBox(); ok(tb && tb.y >= -2 && tb.y < 950, "sticky composer: the timeline stays visible while scrolling the library", tb);
    // drag and drop with the timeline sticky
    await closeIn(p);
    await mouseDrag(p, p.locator('details[data-grp=attacks] [data-card="saber_strike"]'), p.locator("#timeline"));
    await p.mouse.wheel(0, 1200); await p.waitForTimeout(100);
    await mouseDrag(p, p.locator('[data-card="flow_strike"]'), p.locator("#timeline"), 0.95);
    ok(JSON.stringify(await plan(p)) === '["saber_strike","flow_strike"]', "mouse drag from far down the library into the sticky timeline", await plan(p));
    ok(await p.locator('[data-combo="blade_and_body"]').count() === 1 && /predicted synergy/.test(await p.locator(".comboBanner").innerText()), "Blade and Body shown as a PREDICTED synergy with the lit saber");
    // disarmed: the same cards must not show Blade and Body
    await G(p, () => { const a = window.__genesisCombat.state().actors.aero; a.dropped = JSON.parse(JSON.stringify(a.weapon)); a.weapon.held = false; a.weapon.ignited = false; });
    await p.locator("#clear").click(); await p.locator('[data-card="unarmed_strike"]').click(); await p.locator('[data-card="flow_strike"]').click();
    ok(await p.locator('[data-combo="blade_and_body"]').count() === 0 && await p.locator('[data-combo="unarmed_flow"]').count() === 1, "disarmed + unarmed: no Blade and Body (Unarmed Flow instead)");
    ok(/Needs your lightsaber in hand/.test(await p.locator('[data-card="saber_strike"]').innerText()), "lightsaber card explains it needs the blade in hand");
    await G(p, () => { const a = window.__genesisCombat.state().actors.aero; a.weapon.held = true; a.weapon.ignited = true; a.dropped = null; }); await p.locator("#clear").click();
    // object vs main accounting: draw (object) + blaster shot (main)
    await p.locator('[data-card="draw_sidearm"]').click(); ok(/Not enough object/i.test(await p.locator('[data-card="holster_sidearm"]').innerText()) || (await p.locator('[data-card="holster_sidearm"]').getAttribute("data-off")) === "true", "one object interaction per turn");
    await p.locator('[data-card="blaster_shot"]').click(); ok(JSON.stringify(await plan(p)) === '["draw_sidearm","blaster_shot"]', "draw then shoot is a legal plan");
    ok(/HAND|off hand/i.test(await p.locator('[data-card="saber_strike_2h"]').innerText()), "two-handed grip refused while the blaster is in the off hand");
    await p.locator("#clear").click();
    // compound confirmation; then rolls are the PLAYER's: nothing resolves until Roll is pressed
    await p.locator('[data-card="controlled_takedown"]').click(); await p.locator("#resolve").click();
    ok(/consumes 1 Main \+ 1 Secondary\. Continue\?/.test(await p.locator("#confirm").innerText()), "compound cost confirmation");
    await p.locator("#confirmYes").click(); await p.waitForSelector("[data-roll]:not([disabled])");
    const logBefore = await G(p, () => window.__genesisCombat.state().log.length); await p.waitForTimeout(600);
    ok((await G(p, () => window.__genesisCombat.waitingRoll())) && (await G(p, () => window.__genesisCombat.state().log.length)) === logBefore, "the turn waits for the player's Roll button (no auto-roll for Aero)");
    const card = await p.locator(".tcard.mine").last().innerText(); ok(/PLAYER — AERO/.test(await p.locator(".lane-tag.player").innerText()) && /martial|acrobatics/i.test(card) && /opposed by/.test(card), "player roll card shows purpose, dice and what it is opposed by", card);
    await p.locator("[data-roll]:not([disabled])").first().dblclick().catch(() => {});
    await drive(p);
    const gmTitle = await p.locator("#laneGTitle").innerText(); ok(/^GM — ILSA VOHR/.test(gmTitle), "GM lane names the NPC", gmTitle);
    ok(await p.locator(".tcard.gm").count() > 0, "the GM rolled Ilsa's dice in the GM lane");
    const tape = await G(p, () => window.__genesisCombat.state().tape); ok(tape.every((d, i) => d.seq === i), "double-clicking Roll did not create extra dice (contiguous tape)");
    ok(/receipt r\d+/.test(await p.locator(".tcard.mine .tc-res").first().innerText()), "rolls show their receipt");
    // narration after mechanics
    ok((await p.locator("#story .beat").count()) > 0, "Soul narration appears after the mechanics");
    await p.locator("#txWrap > summary").click(); ok(/\[r\d+ 1d20/.test(await p.locator("#log").innerText()), "expandable mechanical transcript");
    ok(await playOut(p), "a whole fight can be played through the UI (offline dice)");
    ok(errors.length === 0, "no page errors (desktop offline)", errors);
    await ctx.close();

    // ================= touch: iPad and phone (offline file) =================
    for (const [label, dev] of [["iPad", devices["iPad (gen 7)"]], ["phone", devices["Pixel 5"]]]) {
      const c2 = await browser.newContext({ ...dev }); const q = await c2.newPage(); const errs = []; q.on("pageerror", (e) => errs.push(e.message));
      await q.goto(fileUrl); await ready(q); const cdp = await c2.newCDPSession(q); await closeIn(q);
      const vh = (await q.viewportSize()).height;
      const dockBox = await q.locator("#dock").boundingBox();
      if (label === "phone") ok(dockBox && dockBox.y + dockBox.height <= vh + 1 && dockBox.y > vh * 0.3, "phone: the composer is a bottom dock, always on screen", dockBox);
      await q.locator('details[data-grp=object]').scrollIntoViewIfNeeded();
      await touchDrag(q, cdp, q.locator('details[data-grp=attacks] [data-card="saber_strike"] .grip'), q.locator("#timeline"));
      ok(JSON.stringify(await plan(q)) === '["saber_strike"]', label + ": touch drag into the timeline without chasing it", await plan(q));
      await aboveDock(q, q.locator('[data-card="flow_strike"]')); await q.locator('[data-card="flow_strike"]').tap(); ok((await plan(q)).length === 2, label + ": tap adds a card");
      await q.locator("#resolve").tap(); await q.waitForSelector("[data-roll]:not([disabled])"); const rb = await q.locator("[data-roll]:not([disabled])").first().boundingBox();
      ok(rb && rb.y >= 0 && rb.y + rb.height <= vh + 1 && rb.height >= 44, label + ": the Roll button is on screen and thumb-sized", rb);
      await drive(q);
      const wide = await G(q, () => document.documentElement.scrollWidth - window.innerWidth); ok(wide <= 1, label + ": no horizontal page scroll", wide);
      const small = await q.$$eval("button:not([hidden]), .grip", (els) => els.filter((e) => { const r = e.getBoundingClientRect(); return r.width && r.height && getComputedStyle(e).visibility !== "hidden" && (r.height < 43.5 || r.width < 43.5); }).map((e) => e.outerHTML.slice(0, 70)));
      ok(small.length === 0, label + ": tap targets at least 44 px", small.slice(0, 4));
      ok(errs.length === 0, label + ": no page errors", errs);
      await c2.close();
    }

    // ================= preview server: Atomic dice, reconnect, no rerolls =================
    const base = "http://127.0.0.1:" + port;
    for (let i = 0; i < 80; i++) { try { await fetch(base + "/healthz"); break; } catch (e) { await new Promise((r) => setTimeout(r, 150)); } }
    const c3 = await browser.newContext({ viewport: { width: 1300, height: 950 } }); const h = await c3.newPage(); const herr = []; h.on("pageerror", (e) => herr.push(e.message));
    await h.goto(base + "/combat.html"); await ready(h);
    ok((await G(h, () => window.__genesisCombat.authority())) === "atomic-sandbox" && /Atomic \(sandbox service\)/.test(await h.locator("#theaterAuth").innerText()), "preview server: dice come from the Atomic service");
    // a plan that is only legal because the page's own state was edited is refused by the server
    await closeIn(h); for (const c of ["saber_strike", "flow_strike"]) await h.locator(`[data-card="${c}"]`).click(); await h.locator("#resolve").click(); await drive(h);
    ok(/ILLEGAL_PLAN/.test(await h.locator("#errMsg").innerText()), "server refuses a plan built on an edited page state (ILLEGAL_PLAN)", await h.locator("#errMsg").innerText());
    await h.reload(); await ready(h);
    await h.locator('[data-card="move"]').click(); if (await h.locator("#pick[open]").count()) await h.locator("#pickBody button").first().click();
    for (const c of ["saber_strike", "flow_strike"]) await h.locator(`[data-card="${c}"]`).click(); await h.locator("#resolve").click(); await drive(h);
    ok(await h.locator(".lane-turn .auth.ok").count() >= 1, "honest turns show the server-verified badge");
    // D3: player view renders enemy facts only from the server projection
    await h.locator("#playerView").check(); await h.waitForTimeout(400);
    const plateTxt = await h.locator("[data-plate=ilsa]").innerText();
    ok(!/HP \d+ \/ \d+/.test(plateTxt) && !/AC 15\b/.test(plateTxt) && /learned from your attacks/.test(plateTxt), "player view: no enemy HP numbers or true AC; AC shown as learned bounds", plateTxt);
    await h.locator("#playerView").uncheck();
    ok(await G(h, () => window.__genesisCombat.state().receipts.every((r) => r.authority === "atomic")), "every receipt is authority=atomic");
    const sid = await G(h, () => window.__genesisCombat.session()); const hash1 = await G(h, () => JSON.stringify([window.__genesisCombat.state().log.length, window.__genesisCombat.state().tape, window.__genesisCombat.state().actors.aero.hp, window.__genesisCombat.state().actors.ilsa.hp]));
    // NOTE: closeIn() changed distance in the page only, so the server replay differs from the page in where Aero stands; use a clean fight for the reconnect proof.
    await h.locator("#reset").click(); await ready(h);
    const sid2 = await G(h, () => window.__genesisCombat.session()); ok(sid2 && sid2 !== sid, "New fight opens a new Atomic session");
    await h.locator('[data-card="move"]').click(); if (await h.locator("#pick[open]").count()) await h.locator("#pickBody button").first().click();
    await h.locator('[data-card="saber_strike"]').click(); await h.locator("#resolve").click();
    await h.waitForSelector("[data-roll]:not([disabled])"); await h.locator("[data-roll]:not([disabled])").first().click();
    // wait for the next player die, or the end of the round; then reload mid-fight
    for (let i = 0; i < 60 && !(await G(h, () => window.__genesisCombat.waitingRoll())) && (await G(h, () => window.__genesisCombat.busy())); i++) { if (await h.locator("#react[open]").count()) await h.locator("#reactBody [data-react='']").click(); await h.waitForTimeout(80); }
    const tapeBefore = await G(h, () => window.__genesisCombat.state().tape.map((d) => d.value));
    await h.reload(); await h.waitForFunction(() => window.__genesisCombat && window.__genesisCombat.session(), null, { timeout: 15000 });
    ok((await G(h, () => window.__genesisCombat.session())) === sid2, "reload: the page reconnects to the same Atomic session");
    ok(/Reconnected/.test(await h.locator("#connMsg").innerText()), "reload: says it rebuilt from the journal");
    await drive(h);
    const tapeAfter = await G(h, () => window.__genesisCombat.state().tape.map((d) => d.value));
    ok(JSON.stringify(tapeAfter.slice(0, tapeBefore.length)) === JSON.stringify(tapeBefore), "reload: every die already drawn is reused (no reroll after reconnect)", [tapeBefore, tapeAfter]);
    const toks = await G(h, () => window.__genesisCombat.tokens());
    const j = await (await fetch(base + "/atomic/journal", { method: "POST", body: JSON.stringify({ session: sid2, tokens: toks }), headers: { "Content-Type": "application/json" } })).json();
    const C = require("./catalog.json"), S = require("./scenarios.json"); const rb = D.replay(C, S, j);
    const pageState = await G(h, () => JSON.parse(JSON.stringify(window.__genesisCombat.state())));
    ok(!rb.pending && D.stateHash(rb.state) === D.stateHash(pageState), "the page's state equals a clean replay of the server journal (presentation wrote nothing into game state)");
    ok(herr.length === 0, "no page errors (Atomic mode)", herr);
    await c3.close();
  } finally { srv.kill(); await browser.close(); }
  console.log(failures ? failures + " FAILED" : "all UI checks passed"); process.exit(failures ? 1 : 0);
})();
