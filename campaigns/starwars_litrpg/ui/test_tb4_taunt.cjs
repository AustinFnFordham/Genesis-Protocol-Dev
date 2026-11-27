// Taunt behind tb4_taunt and action-economy guards (TB4-03, -04, -05, -06, -08). Validator + browser.
// node test_tb4_taunt.cjs <page.html> <state_round1.json>
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const T = require("./turn_contract.js");
const [pageFile, stateFile] = process.argv.slice(2);
let failures = 0;
const ok = (c, n, x) => { if (c) console.log("ok", n); else { failures++; console.log("FAIL", n, x || ""); } };
const st = JSON.parse(fs.readFileSync(stateFile));
const c0 = st.turn_context;
const on = JSON.parse(execFileSync("python3", ["-B", "-c",
  "import json,sys;sys.path.insert(0,sys.argv[1]);import tb4_rules as R;print(json.dumps(R.apply_switches(json.load(open(sys.argv[2]))['turn_context'],{'tb4_taunt':True})))",
  __dirname, path.resolve(stateFile)]).toString());
const foe = on.visible.find((v) => v.hostile).id;
const act = on.options.find((o) => o.slot === "action" && !o.needs_target) || on.options.find((o) => o.slot === "action");
const D = (c, f) => { const d = T.emptyDecl(c); f(d); return T.validate(d, c); };

let r = D(on, (d) => { d.bonus_actions = [{ option: "taunt", target: foe }]; d.actions = [{ option: act.id, target: act.needs_target ? foe : null }]; });
ok(r.legal && r.used && r.used.bonus_action === 1 && r.used.action === 1, "TB4-03 granted Taunt uses exactly one bonus action and leaves the action for the primary", JSON.stringify(r.used));
r = D(on, (d) => { d.bonus_actions = [{ option: "taunt", target: foe }]; });
ok(r.legal && r.used.action === 0, "Taunt alone never spends the primary action", JSON.stringify(r.used));
r = D(on, (d) => { d.bonus_actions = [{ option: "taunt", target: foe }, { option: "taunt", target: foe }]; });
ok(!r.legal && r.errors.some((e) => e.code === "BONUS_CONFLICT"), "a second bonus action is refused");
r = D(c0, (d) => { d.bonus_actions = [{ option: "taunt", target: foe }]; });
ok(!r.legal && r.errors.some((e) => e.code === "UNKNOWN_OPTION"), "TB4-04 without the switch, Taunt is not a granted mechanic");
r = D(on, (d) => { d.bonus_actions = [{ option: "taunt", target: null }]; });
ok(!r.legal && r.errors.some((e) => e.code === "TARGET"), "Taunt needs a target");
r = D(c0, (d) => { d.speech = { option: null, text: "Come on, you mangy sim-dog!", approach: "freeform" }; d.actions = [{ option: act.id, target: act.needs_target ? foe : null }]; });
ok(r.legal && r.used.bonus_action === 0, "TB4-05 a brief insult is free speech: no bonus action, no Taunt effect", JSON.stringify(r.used));
r = D(c0, (d) => { d.actions = [{ option: act.id, target: act.needs_target ? foe : null }]; d.unmapped = ["Wave Wick back toward the crates"]; d.tb4 = { custom: [{ category: "secondary", text: "Wave Wick back toward the crates" }] }; });
ok(r.legal && r.used.action === 1 && r.used.bonus_action === 0, "TB4-06 Secondary activity spends nothing on its own; the GM rules its cost", JSON.stringify(r.used));
const wick = on.objects && on.objects.find((o) => o.by === "wick");
r = D(c0, (d) => { d.actions = [{ option: act.id, target: act.needs_target ? foe : null }, { option: act.id, target: act.needs_target ? foe : null }]; });
ok(!r.legal, "TB4-08 (partial) Aero never gets a second primary action, borrowed or otherwise; NPC cooperation itself is covered by test_action_economy.py");

const { chromium } = require("playwright");
const MOCK = fs.readFileSync(path.join(__dirname, "test_datapad_ui.cjs"), "utf8").match(/const MOCK = `([\s\S]*?)`;/)[1];
(async () => {
  const browser = await chromium.launch();
  try {
    const page = await (await browser.newContext({ viewport: { width: 820, height: 1180 } })).newPage();
    const errors = []; page.on("pageerror", (e) => errors.push(e.message));
    const state = JSON.parse(JSON.stringify(st)); state.features = { tb4_builder: true, tb4_taunt: true }; state.turn_context = on; state.processor = null;
    await page.addInitScript(({ mock, st }) => { window.__store = { "view/state": st }; eval(mock); }, { mock: MOCK, st: state });
    await page.goto(require(require("path").join(__dirname, "hosted_url.cjs")).hostedUrl(pageFile)); await page.waitForSelector("#submitTurn");
    await page.locator("#mechanicsCatalog > summary").click();
    await page.locator('input[data-g="bonus"][value="taunt"]').check(); await page.waitForTimeout(200);
    ok(await page.locator("#w_tb4_taunt_words").count() === 1 && /Wisdom \(Insight\)/.test(await page.locator(".tb4taunt").innerText()), "choosing Taunt asks for target, check and exact words, and states the ruling");
    await page.selectOption("#w_tb4_taunt_target", foe);
    await page.selectOption("#w_tb4_taunt_skill", "deception");
    const words = "I tap the saber hilt twice against my thigh and whistle, like calling a pet.";
    await page.fill("#w_tb4_taunt_words", words); await page.waitForTimeout(500);
    ok(!(await page.locator("#submitTurn").isDisabled()), "a Taunt turn can be submitted");
    await page.locator("#submitTurn").click(); await page.waitForTimeout(500);
    const row = await page.evaluate(() => { const k = Object.keys(window.__store).find((x) => x.startsWith("actions/")); return k && window.__store[k]; });
    ok(row && row.declaration.bonus_actions[0].option === "taunt" && row.declaration.bonus_actions[0].target === foe, "the action carries the Taunt bonus action and its target");
    ok(row && row.declaration.tb4.taunt.words === words && row.declaration.tb4.taunt.skill === "deception", "the player's exact words and chosen check are kept");
    ok(row && /Taunt \(deception\)/.test(row.text) && row.text.includes(words), "the turn text gives the GM the words verbatim");
    ok(errors.length === 0, "no page errors", errors.join("|"));
  } finally { await browser.close(); }
  console.log(failures ? failures + " FAILED" : "all passed");
  process.exit(failures ? 1 : 0);
})();
