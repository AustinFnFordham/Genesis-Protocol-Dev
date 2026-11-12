// Browser test: "Needs revision" GM options load into the composer and can be submitted (owner report 2026-11-12).
// Usage: node test_datapad_review_options.cjs genesis_datapad.html fixtures/needs_revision/state.json fixtures/needs_revision/actions
const { chromium } = require("playwright"); const fs = require("fs"); const path = require("path");
const [page_file, state_file, act_dir, shot] = process.argv.slice(2);
const MOCK = fs.readFileSync(path.join(__dirname, "test_datapad_ui.cjs"), "utf8").match(/const MOCK = `([\s\S]*?)`;/)[1];
const st = JSON.parse(fs.readFileSync(state_file, "utf8"));
const store = { "view/state": st };
for (const f of fs.readdirSync(act_dir)) { const d = JSON.parse(fs.readFileSync(path.join(act_dir, f), "utf8")); store["actions/" + f.replace(".json", "")] = d.data || d; }
let fails = 0; const ok = (c, n, x) => { if (c) console.log("ok", n); else { fails++; console.log("FAIL", n, x === undefined ? "" : JSON.stringify(x).slice(0, 600)); } };
(async () => {
  const b = await chromium.launch(); const p = await (await b.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true })).newPage();
  const errs = []; p.on("pageerror", e => errs.push(e.message));
  await p.addInitScript(({ mock, s }) => { window.__store = s; eval(mock); }, { mock: MOCK, s: store });
  await p.goto("file://" + path.resolve(page_file)); await p.waitForSelector("#submitTurn");
  const chips = p.locator("[data-ralt]");
  ok(await chips.count() === 5, "review options render", await chips.count());
  ok(await p.locator('[data-ralt^="amwdr79h8h0afs5"]:not([disabled])').count() === 2 && await p.locator('[data-ralt^="amwdo3arg2zkpts"]:not([disabled])').count() === 3, "options for the current scene are enabled");
  // option 1: "end your turn" (adds nothing visible) is now selectable and submittable
  await p.locator('[data-ralt="amwdr79h8h0afs5:0"]').click(); await p.waitForTimeout(500);
  ok(/GM option loaded[\s\S]*End your turn here/.test(await p.locator("#altBanner").innerText()), "tapping an option shows what was loaded");
  const box = await p.locator("#altBanner").boundingBox();
  ok(box && box.y >= -5 && box.y < 500, "the page scrolls to the loaded option", box);
  ok(!(await p.locator("#submitAlt").isDisabled()), "the loaded option can be submitted");
  if (shot) await p.screenshot({ path: shot });
  await p.click("#submitAlt"); await p.waitForTimeout(500);
  const made = await p.evaluate(() => Object.keys(window.__store).filter(k => k.startsWith("actions/a")).map(k => window.__store[k]).filter(x => x.status === "submitted"));
  ok(made.length === 1 && /^GM option chosen: End your turn here/.test(made[0].text) && made[0].gm_alternative.of_action === "amwdr79h8h0afs5" && made[0].gm_alternative.index === 0, "submitting records the chosen GM option", made.map(m => [m.text, m.gm_alternative]));
  ok(made[0].based_on_revision === st.revision && made[0].declaration.movement.option === "hold" && made[0].declaration.actions.length === 0, "the action carries the option's declaration, pinned to the revision");
  ok(await p.locator("#altBanner").count() === 0, "the banner clears after submitting");
  // option with an object interaction, then discard
  await p.evaluate(() => { Object.keys(window.__store).filter(k => k.startsWith("actions/a") && window.__store[k].status === "submitted").forEach(k => delete window.__store[k]); window.__notify(); });
  await p.reload(); await p.waitForSelector("#submitTurn"); await p.waitForTimeout(300);
  await p.locator('[data-ralt="amwdo3arg2zkpts:2"]').click(); await p.waitForTimeout(400);
  const chk = await p.locator("#liveCheck").innerText();
  ok(/Draw the blade back|withdraw/i.test(chk) && /step back|10 ft/i.test(chk), "an option with an object interaction and a move fills the composer", chk.slice(0, 300));
  await p.click("#discardAlt"); await p.waitForTimeout(200);
  ok(await p.locator("#altBanner").count() === 0 && await p.locator("#submitTurn").isDisabled(), "Discard empties the composer again");
  // options written for an earlier scene are shown but not selectable
  await p.evaluate(() => { const v = window.__store["view/state"]; v.turn_context = Object.assign({}, v.turn_context, { context_id: "evt_9999" }); v.revision += 1; window.__notify(); });
  await p.waitForTimeout(300);
  ok(await p.locator("[data-ralt]:not([disabled])").count() === 0 && /earlier moment in the scene/.test(await p.locator(".act").first().innerText()), "options from an earlier scene are disabled with an explanation");
  ok(errs.length === 0, "no page errors", errs);
  await b.close(); console.log(fails ? fails + " FAILED" : "all passed"); process.exit(fails ? 1 : 0);
})();
