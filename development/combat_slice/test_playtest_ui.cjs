// CC-003 Tactical Composer in a real browser (desktop, iPad touch, phone touch). node test_playtest_ui.cjs
const { chromium, devices } = require("playwright");
const path = require("path");
const { execFileSync } = require("child_process");
const page = execFileSync("python3", ["-B", path.join(__dirname, "build_playtest.py")]).toString().trim();
const url = "file://" + page;
const P = require("./predict.js"), E = require("./engine.js");
let failures = 0;
const ok = (c, n, x) => { if (c) console.log("ok", n); else { failures++; console.log("FAIL", n, x || ""); } };
async function answerReactions(p, choice) { for (let i = 0; i < 8; i++) { if (!(await p.locator("#react[open]").count())) return; const pos = p.locator("#reactBody [data-react]:not([data-react=''])"); if (choice === "first" && await pos.count()) await pos.first().click(); else await p.locator("#reactBody [data-react='']").click(); await p.waitForTimeout(100); } }
async function idle(p) { await p.waitForFunction(() => !window.__genesisCombat.playing()); }
async function center(loc, fy) { const b = await loc.boundingBox(); return { x: b.x + b.width / 2, y: b.y + b.height * (fy == null ? 0.5 : fy) }; }
async function mouseDrag(p, from, to) { const a = await center(from), b = await center(to); await p.mouse.move(a.x, a.y); await p.mouse.down(); for (let i = 1; i <= 12; i++) await p.mouse.move(a.x + (b.x - a.x) * i / 12, a.y + (b.y - a.y) * i / 12); await p.mouse.up(); await p.waitForTimeout(60); }
async function touchDrag(p, cdp, from, to, fy) { await from.scrollIntoViewIfNeeded(); const a = await center(from); let b = await center(to);
  await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: a.x, y: a.y }] });
  for (let i = 1; i <= 14; i++) { b = await center(to, fy); await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: a.x + (b.x - a.x) * i / 14, y: a.y + (b.y - a.y) * i / 14 }] }); await p.waitForTimeout(16); }
  await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); await p.waitForTimeout(80); }
const plan = (p) => p.evaluate(() => window.__genesisCombat.plan().map((s) => s.pid));
async function setClose(p) { await p.evaluate(() => { const s = window.__genesisCombat.state(); s.dist["aero|ilsa"] = 5; }); await p.locator("#clear").click(); }

(async () => {
  const browser = await chromium.launch();
  try {
    // ---------------- desktop ----------------
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 1000 } });
    const p = await ctx.newPage(); const errors = []; p.on("pageerror", (e) => errors.push(e.message));
    await p.goto(url); await p.waitForSelector("[data-card]");
    const banner = await p.locator("#devBanner").innerText();
    ok(/Test Environment/.test(banner) && /noncanonical/.test(banner), "banner: test environment, noncanonical");
    const groups = await p.$$eval("details.grp", (d) => d.map((x) => x.dataset.grp));
    ok(JSON.stringify(groups) === JSON.stringify(["maneuvers", "main", "secondary", "bonus", "reactions", "moveobj", "free"]), "cards grouped by action economy, Maneuvers first", groups);
    ok(await p.locator("details.grp[data-grp=maneuvers] [data-card=controlled_takedown] .c-main").count() && await p.locator("details.grp[data-grp=maneuvers] [data-card=controlled_takedown] .c-secondary").count(), "a maneuver shows every action type it consumes (Main + Secondary)");
    ok(await p.locator("details.grp[data-grp=reactions] [data-reaction=parry]").count() && /Triggers when/.test(await p.locator("[data-reaction=parry]").innerText()) && /1\/1 this round/.test(await p.locator("[data-reaction=parry]").innerText()), "reactions show trigger, readiness and capacity (not turn steps)");
    await p.locator("[data-filter=bonus]").click(); ok((await p.$$eval("details.grp", (d) => d.length)) === 1, "filter shows one group"); await p.locator("[data-filter=all]").click();
    await p.locator("details.grp[data-grp=main] > summary").click(); ok(!(await p.locator("details.grp[data-grp=main]").evaluate((d) => d.open)), "groups collapse"); await p.locator("details.grp[data-grp=main] > summary").click();
    ok(/HP 20 \/ 20/.test(await p.locator("[data-plate=ilsa]").innerText()) && /HP 11 \/ 11/.test(await p.locator("[data-plate=aero]").innerText()), "HP bars visible for Aero and the enemy");
    ok(/Out of reach/.test(await p.locator('[data-card="saber_strike"]').innerText()), "unavailable card explains why");
    await p.locator('[data-info="controlled_takedown"]').click(); ok(/compound: 1 Main \+ 1 Secondary/.test(await p.locator("#inspectBody").innerText()), "inspect shows compound cost"); await p.locator("#inspectClose").click();

    // drag & drop with the mouse
    await setClose(p);
    await mouseDrag(p, p.locator('[data-card="saber_strike"]'), p.locator("#timeline"));
    ok(JSON.stringify(await plan(p)) === '["saber_strike"]', "mouse: drag a card into the timeline");
    await mouseDrag(p, p.locator('[data-card="feint"]'), p.locator("#timeline .step").first());
    ok(JSON.stringify(await plan(p)) === '["feint","saber_strike"]', "mouse: drop position decides order (dropped above)", await plan(p));
    await p.locator('[data-card="flow_strike"]').focus(); await p.keyboard.press("Enter");
    ok(JSON.stringify(await plan(p)) === '["feint","saber_strike","flow_strike"]', "keyboard: Enter adds a focused card");
    ok(await p.locator('[data-combo="echani_flow_line"]').count() === 1 && await p.locator(".step.combo").count() === 3, "combo recognized: Echani Flow Line, linked steps highlighted");
    const combo = await p.locator(".comboBanner").innerText();
    ok(/Legal sequence/i.test(combo) && /Synergy/i.test(combo) && /Predicted/i.test(combo) && /Cinematic/i.test(combo) && /Conditional/.test(combo), "combo separates legal / synergy / predicted / cinematic and says it is conditional");
    // prediction numbers equal the module's exact math for the same state
    const expected = await p.evaluate(() => JSON.stringify(window.__genesisCombat.state()));
    const s0 = JSON.parse(expected), an = P.analyzePlan(s0, "aero", [{ pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }, { pid: "flow_strike", target: "ilsa" }]);
    const predTxt = await p.locator("#pred").innerText(); const pc = (x) => Math.round(x * 100) + "%";
    ok(predTxt.includes(pc(an.steps[0].success)) && predTxt.includes(pc(an.steps[1].hit)) && predTxt.includes(pc(an.steps[2].hit)), "prediction shows the exact engine-based percentages", [pc(an.steps[0].success), pc(an.steps[1].hit), predTxt.slice(0, 200)]);
    await p.waitForSelector("[data-sim]"); ok(/400 seeded runs/.test(await p.locator("[data-sim]").innerText()) && /95%/.test(await p.locator("[data-sim]").innerText()), "simulation labeled with sample count and interval");
    ok((await p.evaluate(() => JSON.stringify(window.__genesisCombat.state()))) === expected, "prediction did not touch authoritative dice or state");
    ok(/read/i.test(predTxt) && /Mechanical/i.test(predTxt), "mechanical numbers and narrative read are labeled separately");
    // reorder by keyboard and by drag; remove
    await p.locator("#timeline .step").nth(2).focus(); await p.keyboard.press("Alt+ArrowUp");
    ok(JSON.stringify(await plan(p)) === '["feint","flow_strike","saber_strike"]', "keyboard: Alt+Up reorders");
    await mouseDrag(p, p.locator("#timeline .step").nth(1).locator(".ttl"), p.locator("#timeline .step").nth(2).locator(".sub"));
    await mouseDrag(p, p.locator("#timeline .step").nth(2).locator(".ttl"), p.locator("#timeline .step").nth(1).locator(".ttl"));
    const pl = await plan(p); ok(pl.length === 3 && pl[0] === "feint", "mouse: steps can be dragged to reorder", pl);
    await p.locator("#timeline [data-rm]").first().click(); ok((await plan(p)).length === 2, "remove a step");
    await p.locator("#clear").click();
    // compound confirmation, only for compound
    await p.locator('[data-card="controlled_takedown"]').click(); await p.locator("#resolve").click();
    ok(/Blade Bind & Takedown consumes 1 Main \+ 1 Secondary\. Continue\?/.test(await p.locator("#confirm").innerText()), "compound cost confirmation before commit");
    await p.locator("#confirmNo").click(); ok((await plan(p)).length === 1 && !(await p.locator("#confirm[open]").count()), "Revise keeps the plan uncommitted");
    await p.locator("#clear").click(); await p.locator('[data-card="saber_strike"]').click(); await p.locator("#resolve").click();
    ok(!(await p.locator("#confirm[open]").count()), "ordinary action commits without a confirmation");
    await answerReactions(p, "first"); await idle(p);
    ok(await p.locator("#dice .roll").count() > 0 && /receipt r\d/.test(await p.locator("#dice").innerText()), "dice tray shows rolls with receipts");
    ok(/= \d+/.test(await p.locator("#dice .calc").first().innerText()), "dice breakdown shows the calculation");
    ok((await p.locator("#story .beat").count()) > 0, "Soul narration appears");
    await p.locator("#txWrap > summary").click(); ok(/\[r\d+ 1d20/.test(await p.locator("#log").innerText()), "expandable mechanical transcript with receipts");
    await p.locator("#fullMech").check(); ok(/budget/.test(await p.locator("[data-plate=ilsa]").innerText()), "full-mechanics debug view toggles");
    // play a whole fight through the UI
    for (let t = 0; t < 30; t++) { await idle(p); if (await p.evaluate(() => !!window.__genesisCombat.state().over)) break; await answerReactions(p, "first"); await idle(p);
      if (await p.locator("#resolve").isDisabled()) { await p.locator("#clear").click(); for (const c of ["move", "saber_strike", "flow_strike"]) { const el = p.locator(`[data-card="${c}"][data-off="false"]`); if (await el.count()) { await el.click(); if (await p.locator("#pick[open]").count()) await p.locator("#pickBody button").first().click(); } } }
      if (!(await p.locator("#resolve").isDisabled())) await p.locator("#resolve").click(); }
    ok(await p.evaluate(() => !!window.__genesisCombat.state().over), "a full fight finishes through the UI");
    ok(errors.length === 0, "no page errors on desktop", errors);

    // ---------------- touch: iPad and phone ----------------
    for (const [label, dev] of [["iPad", devices["iPad (gen 7)"]], ["phone", devices["Pixel 5"]]]) {
      const c2 = await browser.newContext({ ...dev }); const q = await c2.newPage(); const errs = []; q.on("pageerror", (e) => errs.push(e.message));
      await q.goto(url); await q.waitForSelector("[data-card]"); const cdp = await c2.newCDPSession(q);
      await q.evaluate(() => { const s = window.__genesisCombat.state(); s.dist["aero|ilsa"] = 5; }); await q.locator("#clear").click();
      await touchDrag(q, cdp, q.locator('[data-card="saber_strike"] .grip'), q.locator("#timeline"));
      ok(JSON.stringify(await plan(q)) === '["saber_strike"]', label + ": touch drag (grip) into the timeline", await plan(q));
      await touchDrag(q, cdp, q.locator('[data-card="feint"] .grip'), q.locator("#timeline .step").first(), 0.15);
      ok(JSON.stringify(await plan(q)) === '["feint","saber_strike"]', label + ": touch drop position orders steps", await plan(q));
      await q.locator('[data-card="flow_strike"]').tap(); ok((await plan(q)).length === 3, label + ": tap adds a card (accessible alternative)");
      const sy = await q.evaluate(() => window.scrollY); await touchDrag(q, cdp, q.locator('[data-card="taunt"] .nm'), q.locator('[data-card="taunt"] .nm'));
      ok((await plan(q)).length === 3, label + ": an ordinary short touch on a card body does not start a drag");
      const wide = await q.evaluate(() => document.documentElement.scrollWidth - window.innerWidth); ok(wide <= 1, label + ": no horizontal page scroll", wide);
      const small = await q.$$eval("button:not([hidden]), .grip", (els) => els.filter((e) => { const r = e.getBoundingClientRect(); return r.width && r.height && (r.height < 43.5 || r.width < 43.5); }).map((e) => e.outerHTML.slice(0, 60)));
      ok(small.length === 0, label + ": tap targets at least 44 px", small.slice(0, 4));
      ok(errs.length === 0, label + ": no page errors", errs);
      await c2.close();
    }
  } finally { await browser.close(); }
  console.log(failures ? failures + " FAILED" : "all UI checks passed"); process.exit(failures ? 1 : 0);
})();
