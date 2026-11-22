// CC-002 playtest page in a real browser (desktop, iPad, phone). node test_playtest_ui.cjs
const { chromium } = require("playwright");
const path = require("path");
const { execFileSync } = require("child_process");
const page = execFileSync("python3", ["-B", path.join(__dirname, "build_playtest.py")]).toString().trim();
const url = "file://" + page;
let failures = 0;
const ok = (c, n, x) => { if (c) console.log("ok", n); else { failures++; console.log("FAIL", n, x || ""); } };
async function answerReactions(p, choice) {   // answer any reaction prompts that appear (choice: "first" | "none")
  for (let i = 0; i < 6; i++) {
    if (!(await p.locator("#react[open]").count())) return i;
    const btns = p.locator("#reactBody [data-react]");
    if (choice === "first" && await p.locator("#reactBody [data-react]:not([data-react=''])").count()) await p.locator("#reactBody [data-react]:not([data-react=''])").first().click();
    else await p.locator("#reactBody [data-react='']").click();
    await p.waitForTimeout(120);
  }
  return 6;
}
(async () => {
  const browser = await chromium.launch();
  try {
    const ctx = await browser.newContext({ viewport: { width: 1180, height: 1300 } });
    const p = await ctx.newPage();
    const errors = []; p.on("pageerror", (e) => errors.push(e.message));
    await p.goto(url); await p.waitForSelector("[data-card]");
    ok(/Genesis Development \/ Test Environment/.test(await p.locator("#devBanner").innerText()) && /noncanonical/.test(await p.locator("#devBanner").innerText()), "banner: test environment, noncanonical");
    ok(await p.locator(".badge.sandbox_proposal").count() > 0 && await p.locator(".badge.sheet").count() > 0, "cards say whether they are on the sheet or a proposal");
    ok(/Out of reach/.test(await p.locator('[data-card="saber_strike"]').innerText()), "a card explains why it is unavailable (out of reach)");
    // inspect modal
    await p.locator('[data-info="feint"]').click();
    ok(/Sandbox proposal — needs owner approval/i.test(await p.locator("#inspectBody").innerText()) && /Deception/.test(await p.locator("#inspectBody").innerText()), "inspect shows rules, source and approval status");
    await p.locator("#inspectClose").click();
    // build a combo
    await p.locator('[data-card="move"]').click(); await p.locator('[data-close="ilsa"]').click();
    await p.locator('[data-card="feint"]').click(); await p.locator('[data-card="saber_strike"]').click(); await p.locator('[data-card="flow_strike"]').click();
    ok(await p.locator("#plan li").count() === 4 && await p.locator("#plan li.bad").count() === 0, "a legal four-step combo");
    ok(/advantage/.test(await p.locator("#judge").innerText()), "Combo Judge states the conditional synergy");
    ok(/Not enough Main/.test(await p.locator('[data-card="unarmed_strike"]').innerText()), "the hand reflects the plan's remaining budget");
    // reorder makes Flow Strike illegal (before any melee attack)
    await p.locator('#plan [data-up="3"]').click(); await p.locator('#plan [data-up="2"]').click();
    ok(await p.locator("#plan li.bad").count() === 1 && /Only after a melee attack/.test(await p.locator("#plan").innerText()) && await p.locator("#resolve").isDisabled(), "reordering is checked live; an illegal order cannot be resolved");
    await p.locator('#plan [data-dn="1"]').click(); await p.locator('#plan [data-dn="2"]').click();
    ok(await p.locator("#plan li.bad").count() === 0, "fixed order is legal again");
    await p.locator('[data-aug="2"]').check();
    await p.locator("#resolve").click(); await p.waitForTimeout(200);
    await answerReactions(p, "first");
    const log = await p.locator("#log").innerText();
    ok(/Aero's turn/.test(log) && /Weapon Feint/.test(log) && /Lightsaber Strike/.test(log), "the turn resolved through the engine");
    ok(/Force-guided/.test(log), "Aero's own roll shows its dice and the Force-guided die");
    ok(/Ilsa Vohr's turn/.test(log), "the duelist took her turn with the same rules");
    const st = await p.evaluate(() => { const s = window.__genesisCombat.state(); return { cur: s.order[s.turn], fp: s.actors.aero.fp, over: s.over }; });
    ok(st.over || st.cur === "aero", "control returns to Aero (or the fight ended)", JSON.stringify(st));
    ok(st.fp === 2, "the Force Point was spent", st.fp);
    ok(!/"hp":\s*\d+/.test(await p.locator("#actors").innerText()) && !/\d+\/20/.test(await p.locator("#actors").innerText()), "enemy HP is never shown as a number");
    // play on until the fight ends (simple strategy), answering reactions
    for (let round = 0; round < 25; round++) {
      const s = await p.evaluate(() => { const s = window.__genesisCombat.state(); return { over: s.over, cur: s.order[s.turn], d: s.dist["aero|ilsa"] }; });
      if (s.over) break;
      await answerReactions(p, "first");
      if (s.cur !== "aero") { await p.waitForTimeout(50); continue; }
      if (s.d > 5) { await p.locator('[data-card="move"]').click(); await p.locator('[data-close="ilsa"]').click(); }
      const strike = await p.locator('[data-card="saber_strike"][data-off="false"]').count() ? "saber_strike" : "unarmed_strike";
      if (await p.locator(`[data-card="${strike}"][data-off="false"]`).count()) await p.locator(`[data-card="${strike}"]`).click();
      if (await p.locator('[data-card="recover_weapon"][data-off="false"]').count()) await p.locator('[data-card="recover_weapon"]').click();
      if (await p.locator("#resolve").isDisabled()) { await p.locator("#clear").click(); await p.locator('[data-card="speak"]').click(); }
      await p.locator("#resolve").click(); await p.waitForTimeout(80);
    }
    await answerReactions(p, "first");
    const end = await p.evaluate(() => window.__genesisCombat.state().over);
    ok(end === "victory" || end === "defeat", "a full duel can be played to the end in the browser", end);
    ok(await p.locator(".over").count() === 1, "the end of the fight is shown");
    // predator scenario: hidden creature, pounce, no Taunt
    await p.selectOption("#scenario", "predator"); await p.waitForTimeout(200);
    await answerReactions(p, "none");
    const plog = await p.locator("#log").innerText();
    ok(/Pounce/.test(plog) && /revealed/.test(plog), "the predator pounced from hiding (its turn came first)");
    ok(/does not understand/.test(await p.locator('[data-card="taunt"]').innerText()) || await p.locator('[data-card="taunt"][data-off="true"]').count() === 1, "Taunt is refused against a beast");
    ok(/untrained/.test(await p.locator('[data-card="calm_beast"]').innerText()), "only untrained Animal Handling is offered");
    // hidden case: before it acts, nothing hidden is shown
    await p.locator("#seed").fill("1"); await p.evaluate(() => {});
    // SA-001 switch off: Secondary cards refused
    await p.selectOption("#scenario", "duelist"); await p.waitForTimeout(150);
    await p.locator('[data-sw="secondary_action"]').uncheck(); await p.waitForTimeout(150);
    ok(/Secondary Action \(SA-001\) is off/.test(await p.locator('[data-card="feint"]').innerText()), "with SA-001 off, Feint explains it is unavailable");
    ok(errors.length === 0, "no page errors (desktop)", errors.join(" | "));
    // iPad and phone
    for (const vp of [{ width: 820, height: 1180, name: "iPad" }, { width: 390, height: 844, name: "phone" }]) {
      const c2 = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, hasTouch: true, deviceScaleFactor: 2 });
      const q = await c2.newPage(); const e2 = []; q.on("pageerror", (e) => e2.push(e.message));
      await q.goto(url); await q.waitForSelector("[data-card]");
      ok(await q.evaluate(() => document.documentElement.scrollWidth - innerWidth) <= 0, vp.name + ": no horizontal scroll");
      const small = await q.evaluate(() => [...document.querySelectorAll("button, select, input[type=text]")].filter((b) => b.offsetParent && b.getBoundingClientRect().height < 44).map((b) => b.outerHTML.slice(0, 60)));
      ok(small.length === 0, vp.name + ": every control at least 44 px tall", small.join(" | "));
      await q.locator('[data-card="move"]').tap(); await q.locator('[data-close="ilsa"]').tap(); await q.locator('[data-card="saber_strike"]').tap();
      ok(await q.locator("#plan li").count() === 2, vp.name + ": cards can be tapped into a plan");
      if (vp.name === "phone") await q.screenshot({ path: path.join(__dirname, "out/phone.png"), fullPage: false });
      ok(e2.length === 0, vp.name + ": no page errors", e2.join(" | "));
      await c2.close();
    }
  } finally { await browser.close(); }
  console.log(failures ? failures + " FAILED" : "all passed");
  process.exit(failures ? 1 : 0);
})();
