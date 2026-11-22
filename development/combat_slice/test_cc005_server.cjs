// CC-005: server-side verification, anti-tampering, anti-session-shopping, roll identity, Deflect target choice.
// Runs against the REAL preview server with its engine worker. node test_cc005_server.cjs
const { spawn } = require("child_process"); const path = require("path"), fs = require("fs"), os = require("os");
const E = require("./engine.js"), D = require("./turn_driver.js"), C = require("./catalog.json"), S = require("./scenarios.json");
let fails = 0; const ok = (c, n, x) => { console.log((c ? "ok " : "FAIL ") + n + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 300))); if (!c) fails++; };
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "cc005-")), port = 20000 + Math.floor(Math.random() * 2000);
const srv = spawn("python3", ["-B", path.join(__dirname, "../preview/serve_preview.py"), "--port", String(port)], { env: Object.assign({}, process.env, { GENESIS_ATOMIC_DIR: dir }), stdio: "ignore" });
const base = "http://127.0.0.1:" + port, at = D.HttpAtomic(base);
async function post(p, b) { const r = await fetch(base + p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) }); return { status: r.status, body: await r.json() }; }
const code = async (pr) => { try { await pr; return null; } catch (e) { return e.code; } };
function legal(s, plan) { const out = []; for (const st of plan) if (E.validatePlan(s, "aero", out.concat([st])).legal) out.push(st); return out; }
function aeroPlan(s) { const foes = Object.keys(s.actors).filter((k) => s.actors[k].side === "enemy" && !s.actors[k].down && !s.actors[k].conds.hidden); if (!foes.length) return [{ pid: "tactical_glance" }]; const t = foes[0];
  return legal(s, [{ pid: "recover_weapon" }, { pid: "move", dest: "close", target: t }, { pid: "saber_strike", target: t }, { pid: "unarmed_strike", target: t }, { pid: "flow_strike", target: t }]); }
const hooks = (pick) => ({ playerRoll: async () => {}, gmRoll: async () => {}, decide: async (p) => pick ? pick(p) : p.options[0] });
(async () => {
  for (let i = 0; i < 100; i++) { try { await fetch(base + "/healthz"); break; } catch (e) { await new Promise((r) => setTimeout(r, 150)); } }
  try {
    // 1. honest fight: every turn verified by the server's own reconstruction
    let o = await at.open({ scenario: "duelist", switches: {} }), ctx = { atomic: at, session: o.session }, s = E.newState(C, S, "duelist", { atomic: true }), verified = 0, turns = 0;
    while (!s.over && turns < 40) { const a = E.current(s); const r = await D.runTurn(ctx, s, a, a === "aero" ? aeroPlan(s) : E.npcPlan(s, a), hooks()); s = r.state; turns++; if (r.verification && r.verification.verified) verified++; }
    ok(s.over && verified === turns, "honest duel: every turn verified by the server (" + verified + "/" + turns + ")", [verified, turns]);
    const st = await at.state(o.session); ok(st.hash === D.stateHash(s), "server's authoritative state equals the client's (hash " + st.hash + ")");
    // 2. tampered outcome: the client quietly sets Ilsa to 1 HP before computing its turn
    o = await at.open({ scenario: "duelist", switches: {} }); ctx = { atomic: at, session: o.session }; s = E.newState(C, S, "duelist", { atomic: true });
    const forged = JSON.parse(JSON.stringify(s)); forged.actors.ilsa.hp = 1;
    const r2 = await D.runTurn(ctx, forged, "aero", [{ pid: "move", dest: "close", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }], hooks(() => null));
    ok(r2.verification && r2.verification.tamper === true, "tampered client state is detected (STATE_MISMATCH)", r2.verification);
    ok(r2.state.actors.ilsa.hp > 1 || r2.state.actors.ilsa.hp === S.scenarios.duelist.actors.ilsa.hp, "the server's result stands: Ilsa's real HP, not the forged 1", r2.state.actors.ilsa.hp);
    const j2 = await at.journal(o.session); ok(D.stateHash(D.replay(C, S, j2).state) === D.stateHash(r2.state), "client adopted the server reconstruction");
    // 3. forged hash on an honest turn is also refused
    o = await at.open({ scenario: "duelist", switches: {} }); ctx = { atomic: at, session: o.session }; s = E.newState(C, S, "duelist", { atomic: true });
    const fakeAt = Object.assign({}, at, { complete: (sid, tk) => at.complete(sid, tk, "deadbeef") });
    const r3 = await D.runTurn({ atomic: fakeAt, session: o.session }, s, "aero", [{ pid: "move", dest: "close", target: "ilsa" }], hooks());
    ok(r3.verification && r3.verification.tamper, "a forged state hash is refused; verification follows the server only");
    // 4. illegal plan built on a client-side distance edit
    o = await at.open({ scenario: "duelist", switches: {} });
    ok((await code(at.commit(o.session, "R1.T0.aero", "aero", [{ pid: "saber_strike", target: "ilsa" }]))) === "ILLEGAL_PLAN", "a plan that is only legal in a doctored client state is refused (ILLEGAL_PLAN)");
    ok((await code(at.commit(o.session, "R1.T0.ilsa", "ilsa", []))) === "NOT_YOUR_TURN", "the server decides whose turn it is");
    // 5. forged NPC plan
    const op = await at.open({ scenario: "predator", switches: {} }); const sp = E.newState(C, S, "predator", { atomic: true });
    ok((await code(at.commit(op.session, "R1.T0.stalker", "stalker", [{ pid: "bite", target: "aero" }]))) === "GM_PLAN_MISMATCH", "a client cannot write the NPC's plan (GM_PLAN_MISMATCH)");
    const gp = E.npcPlan(sp, "stalker"); const cm = await at.commit(op.session, "R1.T0.stalker", "stalker", gp); ok(!!cm.plan_hash, "the GM policy's own plan is accepted");
    // 6. dice ownership and dice the engine does not need
    ok((await code(at.roll(op.session, "R1.T0.stalker", cm.plan_hash, [{ seq: 0, sides: 20 }, { seq: 1, sides: 20 }], "player", "stalker"))) === "ROLLER_MISMATCH", "the player cannot roll the NPC's dice (ROLLER_MISMATCH)");
    ok((await code(at.roll(op.session, "R1.T0.stalker", cm.plan_hash, [{ seq: 0, sides: 6 }], "gm", "stalker"))) === "NOT_NEEDED", "dice the engine did not ask for are refused (NOT_NEEDED)");
    ok((await code(at.roll(op.session, "R1.T0.stalker", cm.plan_hash, [{ seq: 0, sides: 20 }, { seq: 1, sides: 20 }, { seq: 2, sides: 20 }], "gm", "stalker"))) === "NOT_NEEDED", "no rolling ahead to peek (NOT_NEEDED)");
    ok((await code(at.decide(op.session, "R1.T0.stalker", "t1", "dodge_reaction"))) === "DECISION_NOT_PENDING", "a decision that is not pending is refused");
    // 7. roll identity recorded server-side
    const okRoll = await at.roll(op.session, "R1.T0.stalker", cm.plan_hash, [{ seq: 0, sides: 20 }, { seq: 1, sides: 20 }], "gm", "stalker", "x");
    const lines = fs.readFileSync(path.join(dir, op.session + ".jsonl"), "utf8").trim().split("\n").map((l) => JSON.parse(l)).filter((l) => l.op === "dice");
    const d0 = lines[0].dice[0]; ok(d0.step === 0 && d0.rules === "cc-sandbox-0.5" && d0.target === "aero" && d0.actor === "stalker" && d0.turn_key === "R1.T0.stalker" && /Pounce/.test(d0.purpose), "every accepted die records turn, actor, step, purpose, target and rules version", d0);
    ok(!JSON.stringify(await at.journal(op.session)).includes('"seed"'), "the journal a client reads still never contains the seed");
    // 8. session shopping
    const b1 = await post("/atomic/open", { scenario: "duelist", mode: "bound", encounter_id: "sandbox.duel.encounter-7" });
    const b2 = await post("/atomic/open", { scenario: "duelist", mode: "bound", encounter_id: "sandbox.duel.encounter-7" });
    ok(b1.body.session === b2.body.session && b2.body.resumed, "bound encounter: opening again returns the SAME session (no new seed)", [b1.body, b2.body]);
    const ab = await post("/atomic/abandon", { session: b1.body.session }); ok(ab.body.forfeit === true, "abandoning a bound encounter is a recorded forfeit");
    const b3 = await post("/atomic/open", { scenario: "duelist", mode: "bound", encounter_id: "sandbox.duel.encounter-7" });
    ok(b3.body.session === b1.body.session && b3.body.closed === true, "after a forfeit the encounter stays closed; no fresh seed is issued", b3.body);
    ok((await post("/atomic/commit", { session: b1.body.session, turn_key: "R1.T0.aero", actor: "aero", plan: [] })).body.error === "SESSION_CLOSED", "a forfeited encounter accepts nothing");
    ok((await post("/atomic/open", { scenario: "duelist", mode: "bound" })).body.error === "NEED_ENCOUNTER", "bound sessions need an encounter id from the campaign authority");
    const p1 = await post("/atomic/open", { scenario: "duelist" }), p2 = await post("/atomic/open", { scenario: "duelist" });
    ok(p1.body.session !== p2.body.session && p1.body.mode === "practice" && p1.body.eligible_for_campaign_authority === false, "practice sessions get fresh seeds and are labelled ineligible for campaign authority");
    // 9. Deflect: player-chosen redirect target, through the server
    let saw = null;
    for (let k = 0; k < 40 && !saw; k++) {
      const od = await at.open({ scenario: "relay_droid", switches: {} }); let sd = E.newState(C, S, "relay_droid", { atomic: true });
      const c1 = { atomic: at, session: od.session };
      sd = (await D.runTurn(c1, sd, "aero", [{ pid: "draw_sidearm" }], hooks())).state;   // Aero holds at 30 ft; the droid shoots next
      if (sd.over) continue;
      const rr = await D.runTurn(c1, sd, "droid", E.npcPlan(sd, "droid"), hooks((p) => { if (p.kind === "deflect_redirect") { saw = p; return p.options[0]; } return p.kind === "ranged_energy_hit_on_me" ? "lightsaber_deflect" : null; }));
      if (saw) ok(rr.verification.verified && rr.log.some((l) => l.ev === "redirect" && l.target === saw.options[0]), "Deflect redirect: the player picked the target; the server verified the turn", rr.verification);
    }
    if (!saw) ok(false, "no full-stop deflect found in 40 sessions (statistically unlikely)");
  } catch (e) { fails++; console.log("FAIL exception", e.code, e.status, e.stack); }
  finally { srv.kill(); }
  console.log(fails ? fails + " FAILED" : "all passed"); process.exit(fails ? 1 : 0);
})();
