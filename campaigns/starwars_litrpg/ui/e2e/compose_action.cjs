// Sandbox E2E helper: drive the REAL built Datapad (mock store) with a list of taps and print the action
// document the page itself writes on Submit. The GM processor then receives exactly what a player's
// Datapad would send. Usage: node compose_action.cjs <page.html> <view_state.json> <ops.json> [--allow-disabled]
// ops: ["pal:object:holster_blaster", "say:<text>", "act:<text>", "seq", "activeseq:<n>", "branch", "when:<case>:<text>",
//       "after:<case>", "addcase", "activecase:<case>", "other:stop|continue", "continue", "del:<step index>",
//       "up:<step index>", "down:<step index>", "cond:<step index>:<text>", "radio:<group>:<value>", "select:<id>:<value>"]
const { chromium } = require("playwright"); const fs = require("fs"), path = require("path");
const [pageFile, stateFile, opsFile] = process.argv.slice(2);
const MOCK = fs.readFileSync(path.join(__dirname, "..", "test_datapad_ui.cjs"), "utf8").match(/const MOCK = `([\s\S]*?)`;/)[1];
(async () => {
  const b = await chromium.launch(); const p = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
  const errs = []; p.on("pageerror", e => errs.push(e.message));
  await p.addInitScript(({ mock, st }) => { window.__store = { "view/state": st }; eval(mock); }, { mock: MOCK, st: JSON.parse(fs.readFileSync(stateFile)) });
  await p.goto("file://" + path.resolve(pageFile)); await p.waitForSelector("#submitTurn");
  const sid = i => p.evaluate(i => document.querySelectorAll(".plan li.step")[i].getAttribute("data-sid"), i);
  const bid = () => p.evaluate(() => { const x = document.querySelectorAll("[data-add-case]"); return x[x.length - 1].getAttribute("data-add-case"); });
  for (const op of JSON.parse(fs.readFileSync(opsFile))) {
    const [k, ...r] = op.split(":"), a = r.join(":");
    if (k === "pal") await p.click(`[data-pal="${a}"]`);
    else if (k === "say") { await p.fill("#w_say", a.replace(/\\n/g, "\n")); await p.click("#addSay"); }
    else if (k === "act") { await p.fill("#w_act", a.replace(/\\n/g, "\n")); await p.click("#addAct"); }
    else if (k === "seq") await p.click("#addSeq");
    else if (k === "activeseq") await p.click(`[data-act-seq="${a}"]`);
    else if (k === "branch") await p.click("#addBranch");
    else if (k === "when") { const [c, ...t] = r; const id = await bid(); await p.fill(`#w_when_${id}_${c}`, t.join(":")); await p.locator(`#w_when_${id}_${c}`).blur(); }
    else if (k === "after") await p.click(`[data-after="${await bid()}:${a}"]`);
    else if (k === "addcase") await p.click(`[data-add-case="${await bid()}"]`);
    else if (k === "activecase") await p.click(`[data-act-case="${await bid()}:${a}"]`);
    else if (k === "other") await p.click(`[data-other="${await bid()}:${a}"]`);
    else if (k === "continue") await p.click("#continuePending");
    else if (k === "radio") { const [g, v] = r; await p.check(`input[data-g="${g}"][value="${v}"]`); }
    else if (k === "select") { const [id, v] = r; await p.selectOption("#" + id, v); }
    else if (k === "del") { const id = await sid(+a); await p.click(`[data-open="${id}"]`); await p.click(`[data-del="${id}"]`); }
    else if (k === "up") { const id = await sid(+a); await p.click(`[data-open="${id}"]`); await p.click(`[data-up="${id}"]`); }
    else if (k === "down") { const id = await sid(+a); await p.click(`[data-open="${id}"]`); await p.click(`[data-down="${id}"]`); }
    else if (k === "cond") { const [i, ...t] = r; const id = await sid(+i); await p.click(`[data-open="${id}"]`); await p.click(`[data-cond="${id}"]`); await p.fill(`#w_cond_${id}`, t.join(":")); await p.locator(`#w_cond_${id}`).blur(); }
    await p.waitForTimeout(60);
  }
  const live = await p.locator("#liveCheck").innerText();
  const disabled = await p.locator("#submitTurn").isDisabled();
  if (disabled) { console.log(JSON.stringify({ submitted: false, live, plan: await p.locator(".plan").innerText(), errs })); await b.close(); return; }
  await p.click("#submitTurn"); await p.waitForTimeout(400);
  const doc = await p.evaluate(() => { const k = Object.keys(window.__store).find(k => k.startsWith("actions/")); return k ? Object.assign({ _id: k.slice(8) }, window.__store[k]) : null; });
  console.log(JSON.stringify({ submitted: !!doc, doc, live, errs }));
  await b.close();
})();
