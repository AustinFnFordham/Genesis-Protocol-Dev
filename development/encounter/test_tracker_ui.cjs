// Browser check: the initiative tracker renders from turn_context.encounter and shows nothing it was not given.
// Usage: node development/encounter/test_tracker_ui.cjs <page.html> <state.json>
const fs = require("fs"), path = require("path"), assert = require("assert/strict");
const { chromium } = require("playwright");
(async () => {
  const [html, stateFile] = process.argv.slice(2);
  const root = path.resolve(__dirname, "../..");
  const mock = fs.readFileSync(path.join(root, "campaigns/starwars_litrpg/ui/test_datapad_ui.cjs"), "utf8").match(/const MOCK = `([\s\S]*?)`;/)[1];
  const state = JSON.parse(fs.readFileSync(stateFile, "utf8"));
  const pill = (a, b, r, o, m) => ({ action: a, bonus_action: b, reaction: r, object_interaction: o, movement_ft: m, speed_ft: 30 });
  state.turn_context.encounter = { mode: "combat", round: 3, current: "Aero", next: "Wick", mode_since: "evt_0001", mode_reason: "encounter began",
    decision: { kind: "player", actor_id: "aero", control: "player" },
    order: [{ actor_id: "aero", label: "Aero", side: "party", initiative: 21, control: "player", conditions: [], budget: pill(1, null, 1, 0, 20), ready: null, unseen: false, status: "acting" },
            { actor_id: "wick", label: "Wick", side: "party", initiative: 12, control: "undecided", conditions: [], budget: pill(0, null, 0, 0, 0), ready: { trigger: "you say fire", does: "one shot" }, unseen: false, status: "waiting" },
            { slot: "hidden:pack:7", label: "Others you cannot see", side: "pack", initiative: 7, unseen: true, status: "waiting" }] };
  const browser = await chromium.launch(process.env.GENESIS_TEST_CHROMIUM ? { executablePath: process.env.GENESIS_TEST_CHROMIUM } : {});
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const errors = []; page.on("pageerror", e => errors.push(e.message));
    await page.addInitScript(({ mock, st }) => { window.__store = { "view/state": st }; eval(mock); }, { mock, st: state });
    await page.goto("file://" + path.resolve(html));
    await page.waitForSelector("#encounterTracker");
    const text = await page.locator("#encounterTracker").textContent();
    assert.match(text, /Combat · round 3 · now: Aero · next: Wick/);
    assert.match(text, /Others you cannot see/);
    assert.match(text, /control undecided/);
    assert.match(text, /readied: one shot when you say fire/);
    assert.match(text, /Move: 20\/30 ft/);
    assert.equal(/Bonus/.test(text), false, "no bonus pill for an actor with no eligible bonus action");
    assert.equal((text.match(/Action:/g) || []).length, 2, "no budget is shown for the unseen slot");
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1), false, "no horizontal scroll on a phone");
    const core = await page.locator("body").textContent();
    for (const name of ["Dash", "Dodge", "Disengage", "Help", "Ready an action"]) assert.ok(core.includes(name), name + " is offered in combat");
    state.turn_context.encounter.mode = "standoff"; state.turn_context.encounter.round = null; state.turn_context.encounter.mode_reason = "every way in is shut";
    const second = await browser.newPage({ viewport: { width: 390, height: 844 } });
    second.on("pageerror", e => errors.push(e.message));
    await second.addInitScript(({ mock, st }) => { window.__store = { "view/state": st }; eval(mock); }, { mock, st: state });
    await second.goto("file://" + path.resolve(html)); await second.waitForSelector("#encounterTracker");
    const calm = await second.locator("#encounterTracker").textContent();
    assert.match(calm, /^Standoff/); assert.match(calm, /every way in is shut/); assert.equal(/Action:/.test(calm), false);
    assert.deepEqual(errors, []);
    console.log("PASS encounter tracker: order, budgets, unseen slot, readied action, core actions, standoff, phone width");
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
