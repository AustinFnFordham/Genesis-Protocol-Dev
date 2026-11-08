// iPhone comfort pass for the scene sequencer (emulated iPhone 13 in Chromium: viewport, touch, DPR, mobile UA;
// the WebKit engine itself is not installed here, so Safari-specific rendering is NOT covered).
// Measures what a thumb has to do: palette reach, adding sequences, reordering across groups, multiline editing,
// branches, and editing an earlier step without losing later work (also across a reload).
// Usage: node test_datapad_iphone.cjs <page.html> <state.json> [shotDir]
const { chromium, devices } = require("playwright");
const fs = require("fs"), path = require("path");
const [page_file, state_file, shotDir] = process.argv.slice(2);
// Published artifacts are wrapped in a skeleton with a device-width viewport; a phone renders that, so test the same.
const wrapped = path.join(require("os").tmpdir(), "datapad_iphone_wrapped.html");
fs.writeFileSync(wrapped, '<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>' + fs.readFileSync(page_file, "utf8") + "</body></html>");
const url = "file://" + wrapped;
const state = JSON.parse(fs.readFileSync(state_file, "utf8"));
state.turn_context = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "hask_r2_sequencer.json"), "utf8"));
const MOCK = fs.readFileSync(path.join(__dirname, "test_datapad_ui.cjs"), "utf8").match(/const MOCK = `([\s\S]*?)`;/)[1];
let fails = 0; const report = {};
function ok(c, name, extra) { if (c) console.log("ok", name); else { fails++; console.log("FAIL", name, extra === undefined ? "" : JSON.stringify(extra).slice(0, 600)); } }

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ ...devices["iPhone 13"] });
  const page = await context.newPage();
  const errors = []; page.on("pageerror", e => errors.push(e.message));
  await page.addInitScript(({ mock, st }) => { if (!window.__store) window.__store = { "view/state": st }; eval(mock); }, { mock: MOCK, st: state });
  await page.goto(url); await page.waitForSelector("#submitTurn");
  let taps = 0;
  const tap = async sel => { await page.locator(sel).first().scrollIntoViewIfNeeded(); await page.tap(sel); taps++; await page.waitForTimeout(50); };
  const vh = page.viewportSize().height;

  // palette reach: how far below the top of the composer the first choice sits, and section chips
  const comp = await page.locator(".composer").boundingBox(), first = await page.locator(".palbtn").first().boundingBox();
  report.palette_offset_px = Math.round(first.y - comp.y);
  ok(await page.locator(".palnav a").count() === 6, "palette has section chips (Plan / Say / Do / Go / Handle / Custom)");
  await page.locator('.palnav a[href="#pg_go"]').scrollIntoViewIfNeeded(); await page.tap('.palnav a[href="#pg_go"]'); await page.waitForTimeout(300);
  const go = await page.locator("#pg_go").boundingBox();
  ok(go.y >= -2 && go.y < vh / 2, "section chip jumps to that part of the palette", go.y);

  // build the owner's plan (S1) by thumb
  for (const k of ["object:holster_blaster", "speech:d1", "move:to_cart", "action:inspect_cart"]) await tap(`[data-pal="${k}"]`);
  await page.locator("#w_act").scrollIntoViewIfNeeded(); await page.tap("#w_act");
  await page.keyboard.type("Load the torch and both gas bottles onto the handcart"); await page.keyboard.press("Enter"); await page.keyboard.type("and strap them down tight.");
  const grow = await page.locator("#w_act").evaluate(e => [e.clientHeight, e.scrollHeight]);
  ok(grow[0] >= grow[1] - 2, "custom action box grows with its text (no inner scrolling)", grow);
  await tap("#addAct"); await tap('[data-pal="action:push_cart"]');
  ok(/Added to Sequence 1: Push the handcart/.test(await page.locator("#lastAdded").innerText()), "each add is confirmed next to the palette (no need to scroll up)");
  await tap("#addSeq");
  ok(/Add to: Sequence 2/i.test(await page.locator("#palette legend").innerText()), "a new sequence becomes the target at once");
  for (const k of ["move:to_shed_door", "speech:d2"]) await tap(`[data-pal="${k}"]`);
  await tap("#addSeq");
  await page.locator("#w_say").scrollIntoViewIfNeeded(); await page.tap("#w_say");
  await page.keyboard.type("Wick, get the lantern ready."); await page.keyboard.press("Enter"); await page.keyboard.type("When the door opens, shine it inside, low and steady.");
  await tap("#addSay"); await tap('[data-pal="action:cut_chain"]');
  await tap('.pal:has([data-pal="action:open_door"]) [data-pre]'); await tap('[data-pal="action:open_door"]'); await tap('[data-pal="object:draw_blaster"]');
  await tap("#addSeq");
  for (const k of ["action:signal_wick", "action:force_sense", "action:prepare_enter"]) await tap(`[data-pal="${k}"]`);
  report.taps_to_build_S1 = taps;
  const n = await page.locator(".plan li.step").count();
  ok(n === 16 && await page.locator("li.st-fix").count() === 0, "S1 built on the phone: 16 steps in 4 sequences, nothing to fix", n);
  if (shotDir) await page.screenshot({ path: shotDir + "/iphone_s1_built.png" });

  // inputs never trigger iOS zoom (font-size >= 16px)
  const small = await page.evaluate(() => [...document.querySelectorAll(".composer input, .composer textarea, .composer select")].filter(e => e.offsetParent && parseFloat(getComputedStyle(e).fontSize) < 16).map(e => e.id || e.className));
  ok(small.length === 0, "every text field is at least 16px (iOS does not zoom on focus)", small);
  // the plan stays compact and both ends are one tap apart
  ok(await page.locator("#jumpAdd").isVisible(), "the sticky bar has “+ Add”, which jumps to the palette");
  ok(await page.locator("#jumpNew").isHidden(), "the floating “Newest” button does not cover the builder");
  const navH = (await page.locator(".palnav").boundingBox()).height;
  ok(navH <= 56, "palette section chips take one row", navH);
  // tap targets and horizontal scroll
  const tiny = await page.evaluate(() => [...document.querySelectorAll(".composer button, .composer a.chip, .composer select, .composer input.txt")].filter(e => e.offsetParent && !e.disabled && e.getBoundingClientRect().height < 44).map(e => e.textContent.trim().slice(0, 20) || e.id));
  ok(tiny.length === 0, "all enabled controls are at least 44px tall", tiny);
  ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), "no horizontal scrolling");

  // reorder across groups by thumb: the first step of Sequence 2 goes up into Sequence 1
  const ids = await page.evaluate(() => [...document.querySelectorAll(".plan li.step")].map(li => li.getAttribute("data-sid")));
  await tap(`[data-open="${ids[6]}"]`);
  ok(await page.locator(`[data-up="${ids[6]}"]`).isVisible() && !(await page.locator(`[data-up="${ids[5]}"]`).isVisible()), "a tapped step shows its controls; the others stay compact");
  await tap(`[data-up="${ids[6]}"]`);
  const per = await page.evaluate(() => [...document.querySelectorAll(".seqcard")].map(s => s.querySelectorAll("li.step").length));
  ok(JSON.stringify(per) === "[7,1,5,3]", "↑ on the first step of a sequence moves it to the end of the previous one", per);
  await tap(`[data-down="${ids[6]}"]`);
  ok(JSON.stringify(await page.evaluate(() => [...document.querySelectorAll(".seqcard")].map(s => s.querySelectorAll("li.step").length))) === "[6,2,5,3]", "and ↓ moves it back");

  // branch on the phone
  await tap('[data-act-seq="1"]'); await tap("#addBranch");
  const bid = await page.evaluate(() => document.querySelector("[data-add-case]").getAttribute("data-add-case"));
  await page.locator(`#w_when_${bid}_0`).scrollIntoViewIfNeeded(); await page.tap(`#w_when_${bid}_0`);
  await page.keyboard.type("Wick says something is shut inside"); await page.locator(`#w_when_${bid}_0`).blur(); await page.waitForTimeout(80);
  await tap(`[data-after="${bid}:0"]`);
  ok(/If Wick says something is shut inside: do none of this, then stop and ask me/.test(await page.locator("#liveCheck").innerText()), "branch built with thumbs");

  // editing an earlier step keeps every later step and its text
  const before = await page.evaluate(() => [...document.querySelectorAll(".plan li.step")].map(li => li.getAttribute("data-sid") + "|" + li.querySelector(".lbl").textContent));
  await tap(`[data-open="${ids[1]}"]`); await tap(`[data-cond="${ids[1]}"]`); await page.tap(`#w_cond_${ids[1]}`); await page.keyboard.type("Wick is calm enough to answer"); await page.locator(`#w_cond_${ids[1]}`).blur(); await page.waitForTimeout(80);
  await page.fill("#w_lbl_0", "Preparation"); await page.waitForTimeout(300);
  const after = await page.evaluate(() => [...document.querySelectorAll(".plan li.step")].map(li => li.getAttribute("data-sid") + "|" + li.querySelector(".lbl").textContent));
  ok(after.length === before.length && after.slice(2).join() === before.slice(2).join(), "editing step 2 leaves every later step untouched", { before: before.length, after: after.length });
  ok(/Wick, get the lantern ready\.\nWhen the door opens/.test(after.join("\n")), "multiline line keeps its line break");
  // a reload (app switch, tab discarded) keeps the whole plan and the drafts
  await page.locator("#w_say").scrollIntoViewIfNeeded(); await page.tap("#w_say"); await page.keyboard.type("Unsent draft line");
  await page.reload(); await page.waitForSelector("#submitTurn"); await page.waitForTimeout(150);
  const reloaded = await page.evaluate(() => [...document.querySelectorAll(".plan li.step")].map(li => li.getAttribute("data-sid") + "|" + li.querySelector(".lbl").textContent));
  ok(reloaded.join() === after.join() && await page.inputValue("#w_say") === "Unsent draft line" && await page.inputValue("#w_lbl_0") === "Preparation", "reload keeps the plan, names and unsent drafts", reloaded.length);
  // the sticky submit bar never hides the field being edited
  await page.locator("#w_act").scrollIntoViewIfNeeded(); await page.tap("#w_act");
  const fb = await page.locator("#w_act").boundingBox(), sb = await page.locator("#submitBar").boundingBox();
  ok(fb.y + fb.height <= sb.y + 1 || fb.y >= sb.y + sb.height, "the focused field is not under the sticky submit bar", { field: fb, bar: sb });
  report.plan_height_px = Math.round((await page.locator(".plan").boundingBox()).height);
  report.palette_height_px = Math.round((await page.locator("#palette").boundingBox()).height);
  if (shotDir) { await page.locator(".plan").screenshot({ path: shotDir + "/iphone_plan.png" }); await page.locator("#palette").screenshot({ path: shotDir + "/iphone_palette.png" }); }
  ok(errors.length === 0, "no page errors", errors);
  console.log("REPORT " + JSON.stringify(report));
  await browser.close();
  console.log(fails ? fails + " failed" : "all passed");
  process.exit(fails ? 1 : 0);
})();
