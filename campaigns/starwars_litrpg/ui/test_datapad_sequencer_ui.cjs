// Browser tests for the cinematic scene sequencer (turn-contract/3): visible palette with availability,
// sequences, multi-select dialogue, multiline custom lines and actions, explicit prerequisites, reordering
// across sequences, branches, committed vs planned state, stale-revision guard, validator-crash fallback,
// the S3 interruption panel (combat invalidates, consequential leaves pending), no hidden information, phone layout.
// Usage: node test_datapad_sequencer_ui.cjs <page.html> <state.json> [shotDir]
// The state's turn_context is replaced by the NON-canonical fixture fixtures/hask_r2_sequencer.json.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const T = require("./turn_contract.js");
const [page_file, state_file, shotDir] = process.argv.slice(2);
const url = "file://" + path.resolve(page_file);
const fx = p => JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", p), "utf8"));
const CTX = fx("hask_r2_sequencer.json"), GM = fx("hask_r2_sequencer_gm_only.json"), S1F = fx("s1_four_sequences_fixed.json");
const state = JSON.parse(fs.readFileSync(state_file, "utf8"));
state.turn_context = CTX;
const MOCK = fs.readFileSync(path.join(__dirname, "test_datapad_ui.cjs"), "utf8").match(/const MOCK = `([\s\S]*?)`;/)[1];

let fails = 0;
function ok(c, name, extra) { if (c) console.log("ok", name); else { fails++; console.log("FAIL", name, extra === undefined ? "" : JSON.stringify(extra).slice(0, 900)); } }

(async () => {
  const browser = await chromium.launch();
  async function open(viewport, st) {
    const ctx = await browser.newContext({ viewport, hasTouch: viewport.width < 500 });
    const page = await ctx.newPage();
    page.errors = []; page.on("pageerror", e => page.errors.push(e.message));
    await page.addInitScript(({ mock, st }) => { window.__store = { "view/state": st }; eval(mock); }, { mock: MOCK, st: st || state });
    await page.goto(url); await page.waitForSelector("#submitTurn");
    return page;
  }
  const page = await open({ width: 390, height: 844 });
  const steps = () => page.locator(".plan li.step").count();
  const tap = async sel => { await page.click(sel); await page.waitForTimeout(40); };
  const pal = key => page.locator(`[data-pal="${key}"]`);

  // ----- committed state and the visible palette -----
  const now = await page.locator(".now").innerText();
  ok(/Now · committed/i.test(now) && /left: the blaster pistol/.test(now) && /at the shed door/.test(now), "committed strip shows hands and position from the ledger", now);
  ok(await page.locator("select#w_addstep").count() === 0 && await page.locator(".palette .palbtn").count() >= 15, "contextual choices are visible buttons, not a dropdown");
  ok(await pal("action:inspect_cart").isDisabled(), "inspecting the cart 35 ft away is disabled");
  const why = await pal("action:inspect_cart").innerText();
  ok(/needs a step first/.test(why) && /35 ft/.test(why), "disabled choice says what is missing", why);
  ok(await pal("object:draw_blaster").isDisabled() && /already has a drawn blaster/.test(await pal("object:draw_blaster").innerText()), "drawing a drawn blaster is not possible here");
  ok(/possible, with a risk/.test(await pal("action:cut_chain").innerText()) && !(await pal("action:cut_chain").isDisabled()), "risky choice stays selectable with its risk");

  // ----- S1, sequence 1: holster, ask (d1), move, inspect, custom action, push the cart -----
  await tap('[data-pal="object:holster_blaster"]'); await tap('[data-pal="speech:d1"]'); await tap('[data-pal="move:to_cart"]');
  ok(!(await pal("action:inspect_cart").isDisabled()), "after the planned move the inspection becomes available");
  await tap('[data-pal="action:inspect_cart"]');
  const custom = "Load the torch and both gas bottles onto the handcart\nand strap them down tight.";
  await page.fill("#w_act", custom); await tap("#addAct");
  await tap('[data-pal="action:push_cart"]');
  ok(await steps() === 6, "six taps, six steps (nothing added on its own)", await steps());
  const planText = await page.locator(".plan").innerText();
  ok(/Planned: right: lightsaber · left: free/.test(planText) && /Planned: at the welding cart/.test(planText), "planned state shown per step", planText.slice(0, 600));
  ok(/✎\s*Try: Load the torch/.test(planText), "custom action kept and marked for the GM", planText);

  // ----- sequence 2: walk back, ask (d2); multi-select dialogue -----
  await tap("#addSeq"); await tap('[data-pal="move:to_shed_door"]'); await tap('[data-pal="speech:d2"]');
  ok(/added ×1/.test(await pal("speech:d1").innerText()), "selected dialogue lines stay selectable and show their count");

  // ----- sequence 3: multiline line, cut, explicit prerequisite, open, draw -----
  await tap("#addSeq");
  const line = "Wick, get the lantern ready.\nWhen the door opens, shine it inside, low and steady.";
  await page.fill("#w_say", line); await tap("#addSay");
  await tap('[data-pal="action:cut_chain"]');
  ok(await pal("action:open_door").isDisabled() && /left hand holds the handcart/.test(await pal("action:open_door").innerText()), "opening the door with both hands full is disabled, with the reason");
  const before = await steps();
  const pre = page.locator('.pal:has([data-pal="action:open_door"]) [data-pre]');
  ok(/Let go of the handcart/.test(await pre.first().innerText()), "the missing step is offered explicitly", await pre.allInnerTexts());
  await pre.first().click(); await page.waitForTimeout(60);
  ok(await steps() === before + 1, "the prerequisite button adds exactly one step");
  ok(!(await pal("action:open_door").isDisabled()), "the door becomes available once the cut and the free hand are planned");
  await tap('[data-pal="action:open_door"]'); await tap('[data-pal="object:draw_blaster"]');

  // ----- sequence 4 -----
  await tap("#addSeq"); await tap('[data-pal="action:signal_wick"]'); await tap('[data-pal="action:force_sense"]'); await tap('[data-pal="action:prepare_enter"]');
  await page.fill("#w_lbl_0", "Preparation and investigation"); await page.waitForTimeout(350);
  ok(await steps() === 16 && await page.locator(".seqcard").count() === 4, "four sequences, sixteen steps", await steps());
  ok(await page.locator("li.st-fix").count() === 0 && !(await page.locator("#submitTurn").isDisabled()), "the whole plan is structurally possible and can be submitted");
  if (shotDir) await page.screenshot({ path: shotDir + "/s1_plan_phone.png", fullPage: true });
  await tap("#submitTurn"); await page.waitForTimeout(300);
  const key = await page.evaluate(() => Object.keys(window.__store).filter(k => k.startsWith("actions/"))[0]);
  const doc = key ? await page.evaluate(k => window.__store[k], key) : null;
  const ds = doc ? doc.declaration.steps : [];
  ok(doc && doc.contract === "turn-contract/3" && ds.length === 16 && JSON.stringify([...new Set(ds.map(s => s.seq))]) === "[0,1,2,3]", "submitted plan carries ordered steps in four sequences", doc && ds.map(s => [s.seq, s.type]));
  ok(ds.some(s => s.type === "speech" && s.text === line) && ds.some(s => s.type === "free" && s.text === custom), "multiline line and custom action are submitted verbatim");
  ok(ds.filter(s => s.type === "speech").length === 3 && doc.declaration.sequences[0].label === "Preparation and investigation" && doc.preflight.legal, "three speech steps, labels and preflight recorded", doc && doc.declaration.sequences);
  ok(/Sequence 1 \(Preparation and investigation\): Holster/.test(doc.text) && /\nSequence 4: Signal Wick/.test(doc.text), "the turn text reads as sequences", doc && doc.text);

  // ----- reordering across sequences, with an explicit fix -----
  const p2 = await open({ width: 390, height: 844 });
  const t2 = async sel => { await p2.click(sel); await p2.waitForTimeout(40); };
  await t2('[data-pal="object:holster_blaster"]'); await t2('[data-pal="move:to_cart"]'); await t2("#addSeq"); await t2('[data-pal="action:inspect_cart"]');
  const ids = await p2.evaluate(() => [...document.querySelectorAll(".plan li.step")].map(li => li.getAttribute("data-sid")));
  await t2(`[data-open="${ids[1]}"]`); await t2(`[data-down="${ids[1]}"]`);  // the move crosses into sequence 2, after nothing: it becomes its first step
  let seqs = await p2.evaluate(() => [...document.querySelectorAll(".seqcard")].map(s => s.querySelectorAll("li.step").length));
  ok(JSON.stringify(seqs) === "[1,2]", "↓ on the last step of a sequence moves it to the next one", seqs);
  await t2(`[data-down="${ids[1]}"]`);  // now after the inspection: the inspection loses its move
  ok(await p2.locator("li.st-fix").count() === 1 && /Add “Over to the welding cart/.test(await p2.locator("li.st-fix").innerText()), "the broken step explains itself and offers the move", await p2.locator(".plan").innerText());
  const n0 = await p2.locator(".plan li.step").count();
  await t2("li.st-fix [data-fix]");
  ok(await p2.locator(".plan li.step").count() === n0 + 1 && await p2.locator("li.st-fix").count() === 0, "fix inserts exactly one step before the broken one");
  ok(await p2.locator(`[data-del-seq="1"]`).isDisabled() && await p2.locator(".seqcard").count() === 2, "a sequence with steps cannot be removed");
  await t2("#addSeq"); await t2(`[data-del-seq="2"]`);
  ok(await p2.locator(".seqcard").count() === 2, "an empty sequence can be removed");

  // ----- branches -----
  const p3 = await open({ width: 1280, height: 900 });
  const t3 = async sel => { await p3.click(sel); await p3.waitForTimeout(40); };
  await t3('[data-pal="object:holster_blaster"]');
  await p3.fill("#w_say", "Wick. Is something shut in there?"); await t3("#addSay");
  await t3("#addBranch");
  ok(await p3.locator("#submitTurn").isDisabled() && /Say what Aero must hear or see/.test(await p3.locator("#liveCheck").innerText()), "an empty “if” blocks submission with a reason");
  const bid = await p3.evaluate(() => document.querySelector("[data-add-case]").getAttribute("data-add-case"));
  await p3.fill(`#w_when_${bid}_0`, "Wick confirms something is trapped inside"); await p3.locator(`#w_when_${bid}_0`).blur(); await p3.waitForTimeout(80);
  await t3(`[data-after="${bid}:0"]`);
  await t3(`[data-add-case="${bid}"]`);
  await p3.fill(`#w_when_${bid}_1`, "Wick gives credible information supporting opening the shed"); await p3.locator(`#w_when_${bid}_1`).blur(); await p3.waitForTimeout(80);
  await t3('[data-pal="action:cut_chain"]');  // the active container is the else-if case
  await t3('[data-act-seq="0"]'); await t3('[data-pal="action:open_door"]');
  const lc = await p3.locator("#liveCheck").innerText();
  ok(/If Wick confirms something is trapped inside: do none of this, then stop and ask me/.test(lc) && /Else if Wick gives credible information[^\n]*: Cut the shed/.test(lc) && /Otherwise: stop and ask me/.test(lc), "branch preview reads as if / else if / otherwise", lc);
  ok(await p3.locator("li.halt").count() === 1 && /stops here and asks you/.test(await p3.locator("li.halt").innerText()), "decision divider shown");
  ok(/Missing information never counts as a yes/.test(await p3.locator(".branch").innerText()), "branch states the no-assumption rule");
  ok(!(await p3.locator("#submitTurn").isDisabled()), "branch plan can be submitted");
  await t3(`[data-other="${bid}:continue"]`);
  ok(/In the case “otherwise”: Open the shed door needs the chain cut first/.test(await p3.locator("#liveCheck").innerText()), "otherwise-continue flags the path where the door cannot open");
  if (shotDir) await p3.screenshot({ path: shotDir + "/s2_branch_desktop.png", fullPage: true });
  await t3("#submitTurn"); await p3.waitForTimeout(300);
  const bdoc = await p3.evaluate(() => { const k = Object.keys(window.__store).find(k => k.startsWith("actions/")); return k && window.__store[k]; });
  const br = bdoc && bdoc.declaration.steps.find(s => s.type === "branch");
  ok(br && br.cases.length === 2 && br.cases[0].after === "stop" && br.cases[1].steps[0].option === "cut_chain" && br.otherwise === "continue", "branch submitted with its cases", br);

  // ----- stale revision guard -----
  const p4 = await open({ width: 390, height: 844 });
  await p4.click('[data-pal="action:signal_wick"]'); await p4.waitForTimeout(40);
  await p4.evaluate(() => { window.__store["view/state"].revision += 3; });  // the store moved on; the listener has not fired yet
  await p4.click("#submitTurn"); await p4.waitForTimeout(250);
  const written = await p4.evaluate(() => Object.keys(window.__store).filter(k => k.startsWith("actions/")).length);
  ok(written === 0 && /scene moved on/.test(await p4.locator("#msg").innerText()) && await p4.locator(".plan li.step").count() === 1, "never submits against an old scene; the plan is kept");

  // ----- validator crash: never locks the player out -----
  await p4.evaluate(() => { window.GenesisTurn.validate = () => { throw new Error("boom"); }; window.GenesisTurn.availability = () => { throw new Error("boom"); }; });
  await p4.click('[data-pal="action:force_sense"]'); await p4.waitForTimeout(80);
  ok(/Live check unavailable/.test(await p4.locator("#liveCheck").innerText()) && !(await p4.locator("#submitTurn").isDisabled()), "a crashed check says so and still allows submit");
  ok(/the GM checks/.test(await p4.locator(".palette").innerText()), "palette falls back to 'the GM checks'");

  // ----- S3: the hidden Mastiff interruption, then a consequential stop -----
  const done = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s10b", "s11"];
  const pr = T.planProgress(S1F, CTX, { completed: done, interrupted: "s12", stop_kind: "combat", reason: "Something burst out of the dark behind you and lunged. It went past you, through the open door." });
  const combatCtx = Object.assign({}, CTX, { context_id: "fx_after_s3", mode: "combat", round: 1, pending_steps: pr.pending_steps, plan_result: pr.plan_result, pending_reason: null,
    hands: { right: CTX.hands.right, left: null }, state_flags: ["saber_ignited", "chain_cut", "door_open"] });
  const st5 = JSON.parse(JSON.stringify(state)); st5.turn_context = combatCtx; st5.revision += 5;
  const p5 = await open({ width: 390, height: 844 }, st5);
  const box = await p5.locator(".interrupt").innerText();
  ok(/Interrupted: initiative has begun/.test(box) && /12 steps of your plan happened/.test(box) && /Cancelled by what happened[\s\S]*Draw the blaster[\s\S]*Prepare to step inside/.test(box), "interruption panel: what happened, what was cancelled", box);
  ok(await p5.locator("#continuePending").count() === 0 && await p5.locator(".budget").count() === 1, "combat: no Continue, the combat action economy applies");
  const all5 = await p5.locator("body").innerText();
  ok(!GM.leak_markers.some(m => all5.includes(m)), "no hidden simulation detail reaches the page", GM.leak_markers.filter(m => all5.includes(m)));
  if (shotDir) await p5.screenshot({ path: shotDir + "/s3_interrupted_phone.png", fullPage: true });
  const pr2 = T.planProgress(S1F, CTX, { completed: ["s1", "s2", "s3"], interrupted: "s4", stop_kind: "consequential", reason: "Wick grabs your sleeve: a lamp is coming up the lane." });
  const st6 = JSON.parse(JSON.stringify(state)); st6.turn_context = Object.assign(JSON.parse(JSON.stringify(CTX)), { context_id: "fx_after_cons", pending_steps: pr2.pending_steps, plan_result: pr2.plan_result,
    // committed after s1-s3: blaster holstered, Aero at the cart
    hands: { right: CTX.hands.right, left: null }, state_flags: ["saber_ignited"], position_label: "at the welding cart" });
  st6.turn_context.visible.forEach(v => { const d = { wick: 5, shed_door: 35, welding_cart: 0, middle_silo: 10, grange: 300 }; if (d[v.id] != null) v.distance_ft = d[v.id]; }); st6.revision += 6;
  const p6 = await open({ width: 390, height: 844 }, st6);
  ok(/Stopped: something needs your decision/.test(await p6.locator(".interrupt").innerText()) && await p6.locator(".plan li.step").count() === 0, "pending steps are shown, never loaded on their own");
  await p6.click("#continuePending"); await p6.waitForTimeout(100);
  const n6 = await p6.locator(".plan li.step").count(), seq6 = await p6.locator(".seqcard").count();
  ok(n6 === pr2.pending_steps.length && /continued/i.test(await p6.locator(".plan").innerText()) && seq6 === 4, "Continue loads them as authorized steps in their sequences", [n6, seq6]);

  // Continue is an explicit authorization bound to the current context; a newer context drops it
  await p6.click("#submitTurn"); await p6.waitForTimeout(300);
  const cdoc = await p6.evaluate(() => { const k = Object.keys(window.__store).find(k => k.startsWith("actions/")); return k && window.__store[k]; });
  const cs = cdoc ? cdoc.declaration.steps : [];
  ok(cs.length === 13 && cs.every(x => x.pending && x.authorized && x.authorized_ctx === "fx_after_cons") && cs[0].status === "interrupted", "continued steps are submitted authorized against the current context", cs.slice(0, 2));
  const p8 = await open({ width: 390, height: 844 }, st6);
  await p8.click("#continuePending"); await p8.waitForTimeout(80);
  await p8.click('[data-pal="action:search_dark"]'); await p8.waitForTimeout(60);
  await p8.evaluate(() => { const v = window.__store["view/state"]; v.revision += 1; v.turn_context = Object.assign({}, v.turn_context, { context_id: "fx_newer", pending_steps: [], plan_result: null }); window.__notify(); });
  await p8.waitForTimeout(200);
  const t8 = await p8.locator(".plan").innerText();
  ok(/scene changed while you were planning/.test(t8) && await p8.locator(".plan li.step").count() === 1 && /Search around/.test(t8), "a newer context drops the old authorization but keeps the player's own new steps", t8.slice(0, 300));

  // status vocabulary: paused, not attempted, blocked, cancelled are told apart
  const S2 = { actor: "aero", steps: [{ id: "a1", seq: 0, type: "object", option: "holster_blaster" }, { id: "a2", seq: 0, type: "speech", text: "Is something shut in there?" },
    { id: "b1", seq: 0, type: "branch", otherwise: "stop", cases: [{ when: "Wick confirms something is trapped inside", steps: [], after: "stop" }] }, { id: "a3", seq: 1, type: "action", option: "cut_chain" }] };
  const pc = T.planProgress(S2, CTX, { completed: ["a1", "a2"], stop_kind: "condition", reason: "Wick doesn't know." });
  const pb = T.planProgress(S1F, CTX, { completed: ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"], stop_kind: "prerequisite", reason: "The chain held.", blocked: ["s11", "s15"], cancelled: ["s12"] });
  const st9 = JSON.parse(JSON.stringify(state)); st9.turn_context = Object.assign({}, CTX, { context_id: "fx_blocked", pending_steps: pb.pending_steps, plan_result: pb.plan_result }); st9.revision += 9;
  const p9 = await open({ width: 390, height: 844 }, st9);
  const t9 = await p9.locator(".interrupt").innerText();
  ok(/Stopped: a step did not work out/.test(t9) && /Not attempted yet[\s\S]*Let go of the handcart/.test(t9) && /Blocked: what it needed did not happen[\s\S]*Open the shed door/.test(t9) && /Cancelled by what happened[\s\S]*Draw the blaster/.test(t9), "blocked, cancelled and not-attempted are shown apart", t9);
  await p9.click("#continuePending"); await p9.waitForTimeout(80);
  const t9b = await p9.locator(".plan").innerText();
  ok(!/Open the shed door/.test(t9b) && !/Draw the blaster/.test(t9b) && /Let go of the handcart/.test(t9b), "Continue offers only steps that can still happen", t9b.slice(0, 400));
  const st10 = JSON.parse(JSON.stringify(state)); st10.turn_context = Object.assign({}, CTX, { context_id: "fx_paused", pending_steps: pc.pending_steps, plan_result: pc.plan_result }); st10.revision += 10;
  const p10 = await open({ width: 390, height: 844 }, st10);
  ok(/Paused: waiting on your decision[\s\S]*Decision/.test(await p10.locator(".interrupt").innerText()) && /Not attempted yet[\s\S]*Cut the shed/.test(await p10.locator(".interrupt").innerText()), "a paused decision is shown apart from steps not reached");
  // no guarantee language anywhere in the builder
  const words = (await page.locator(".composer").innerText()) + (await p9.locator(".composer").innerText());
  ok(!/\b(will succeed|guaranteed|certain to|sure to|will work|chance|likely|\d+\s*%)\b/i.test(words), "legal choices never read as guaranteed outcomes");

  // ----- improvised equipment: gear from the record, custom method / tools / result (S4 harness) -----
  const p11 = await open({ width: 390, height: 844 });
  const t11 = async sel => { await p11.click(sel); await p11.waitForTimeout(50); };
  ok(/gear: .*compact Jedi glowrod \(attached, belt clip\).*items packed/i.test(await p11.locator(".now").innerText()), "committed strip shows where Aero's gear is", await p11.locator(".now").innerText());
  await t11("#pg_gear summary");
  const rope = p11.locator('[data-pal="object:eq_take:syntherope"]');
  ok(await rope.isDisabled() && /needs a step first/.test(await rope.innerText()), "taking out the rope with both hands full asks for a step first", await rope.innerText());
  await t11('.pal:has([data-pal="object:eq_take:syntherope"]) [data-pre]');
  ok(!(await rope.isDisabled()), "after holstering, the rope can be taken out");
  await t11('[data-pal="move:to_cart"]'); await t11('[data-pal="object:eq_take:syntherope"]');
  await p11.fill("#w_act", "Tie the syntherope into a harness and lash the torch and both gas bottles to my back");
  await t11("#actHow summary");
  await p11.fill("#w_how", "bottles back to back, rope crossed over both shoulders and knotted at the waist");
  await p11.check('[data-use="syntherope"]'); await p11.waitForTimeout(80);
  await p11.selectOption('[data-after-use="syntherope"]', "attached");
  await p11.selectOption("#w_on", "welding_cart"); await p11.selectOption("#w_hands", "2");
  await p11.fill("#w_makes", "rope harness carrying the torch and two gas bottles"); await p11.selectOption("#w_makes_state", "worn");
  await t11("#addAct");
  const plan11 = await p11.locator(".plan").innerText();
  ok(/✎\s*Try: Tie the syntherope/.test(plan11) && /how: bottles back to back/.test(plan11) && /using syntherope/.test(plan11) && /makes rope harness carrying the torch and two gas bottles \(worn, if it works\)/.test(plan11), "custom step shows method, tools and intended result", plan11);
  ok(/syntherope: in hand|left: syntherope/.test(plan11) && /rope harness carrying the torch and two gas bottles: worn \(if it works\)/.test(plan11), "planned gear changes are shown, the result only as planned", plan11);
  ok(!(await p11.locator("#submitTurn").isDisabled()), "the improvised plan can be submitted for the GM to adjudicate");
  await t11("#submitTurn"); await p11.waitForTimeout(300);
  const hdoc = await p11.evaluate(() => { const k = Object.keys(window.__store).find(k => k.startsWith("actions/")); return k && window.__store[k]; });
  const hs = hdoc && hdoc.declaration.steps.find(x => x.type === "free");
  ok(hs && hs.method && hs.uses[0] === "syntherope" && hs.targets[0] === "welding_cart" && hs.hands === 2 && hs.equipment_changes[0].to === "attached" && hs.creates.state === "worn" &&
     hs.text === "Tie the syntherope into a harness and lash the torch and both gas bottles to my back", "submitted step keeps the exact words, method, tools, changes and intended result", hs);

  // ----- phone layout -----
  const sw = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  ok(sw <= 0, "no horizontal scroll on phone", sw);
  const p7 = await open({ width: 390, height: 844 });
  await p7.click('[data-pal="object:holster_blaster"]'); await p7.waitForTimeout(40);
  const small = await p7.evaluate(() => [...document.querySelectorAll(".plan .btn.mini, .palbtn, #addSeq, #submitTurn")].filter(e => e.offsetParent && e.getBoundingClientRect().height < 44).map(e => e.textContent));
  ok(small.length === 0, "tap targets are at least 44 px tall", small);
  const sticky = await p7.evaluate(() => getComputedStyle(document.getElementById("submitBar")).position);
  ok(sticky === "sticky", "submit bar stays reachable on phone", sticky);

  for (const p of [page, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11]) ok(p.errors.length === 0, "no page errors", p.errors);
  await browser.close();
  console.log(fails ? fails + " failed" : "all passed");
  process.exit(fails ? 1 : 0);
})();
