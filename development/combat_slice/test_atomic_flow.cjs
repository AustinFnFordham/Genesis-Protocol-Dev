// CC-004: whole fights through the REAL preview server's Atomic routes. node test_atomic_flow.cjs
const { spawn } = require("child_process"); const path = require("path"); const fs = require("fs"); const os = require("os");
const E = require("./engine.js"), D = require("./turn_driver.js"), C = require("./catalog.json"), S = require("./scenarios.json");
let fails = 0; const ok = (c, n, x) => { console.log((c ? "ok " : "FAIL ") + n + (c ? "" : " " + (x || ""))); if (!c) fails++; };
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "atomic-")), port = 18000 + Math.floor(Math.random() * 2000);
const srv = spawn("python3", ["-B", path.join(__dirname, "../preview/serve_preview.py"), "--port", String(port)], { env: Object.assign({}, process.env, { GENESIS_ATOMIC_DIR: dir }), stdio: ["ignore", "pipe", "pipe"] });
const base = "http://127.0.0.1:" + port;
function legal(s, actor, plan) { const out = []; for (const st of plan) if (E.validatePlan(s, actor, out.concat([st])).legal) out.push(st); return out; }
function aeroPlan(s) { const foes = Object.keys(s.actors).filter((k) => s.actors[k].side === "enemy" && !s.actors[k].down && !s.actors[k].conds.hidden); if (!foes.length) return [{ pid: "tactical_glance" }]; const t = foes[0];
  return legal(s, "aero", [{ pid: "recover_weapon" }, { pid: "move", dest: "close", target: t }, { pid: "feint", target: t }, { pid: "saber_strike", target: t }, { pid: "unarmed_strike", target: t }, { pid: "flow_strike", target: t }]); }
async function fight(scenario, atomic, opts) {
  opts = opts || {}; const o = await atomic.open({ scenario, switches: {} }); const ctx = { atomic, session: o.session };
  let s = E.newState(C, S, scenario, { atomic: true }), playerRolls = 0, gmRolls = 0, turns = 0;
  const hooks = { playerRoll: async () => { playerRolls++; }, gmRoll: async () => { gmRolls++; }, decide: async (p) => p.options[0] };
  while (!s.over && turns < 40) { const a = E.current(s); const plan = a === "aero" ? aeroPlan(s) : E.npcPlan(s, a); const r = await D.runTurn(ctx, s, a, plan, hooks); if (r.refused) throw new Error("refused " + JSON.stringify(r.refused.steps)); s = r.state; turns++; if (opts.stopAfter && turns >= opts.stopAfter) break; }
  return { s, ctx, playerRolls, gmRolls };
}
(async () => {
  for (let i = 0; i < 80; i++) { try { await fetch(base + "/healthz"); break; } catch (e) { await new Promise((r) => setTimeout(r, 150)); } }
  try {
    const at = D.HttpAtomic(base);
    // 1. a whole duel; every die came from Atomic; receipts say so
    const f = await fight("duelist", at);
    ok(!!f.s.over, "a full duel finishes with every die from the Atomic service");
    ok(f.s.receipts.length > 0 && f.s.receipts.every((r) => r.authority === "atomic"), "every receipt is marked authority=atomic");
    ok(f.playerRolls > 0 && f.gmRolls > 0, "player dice waited for the player; GM dice were rolled by the GM side", f.playerRolls + "/" + f.gmRolls);
    const aeroOwn = f.s.receipts.filter((r) => r.actor === "aero").length; ok(aeroOwn > 0, "Aero's own rolls exist in the receipts");
    // 2. reconnect: rebuild from the journal → identical state (no reroll)
    const j = await at.journal(f.ctx.session); const rb = D.replay(C, S, j);
    ok(D.stateHash(rb.state) === D.stateHash(f.s) && !rb.pending, "reconnect: replaying the journal rebuilds the identical state");
    // 3. lost responses: the server processes the roll but the client never sees the answer; retry gets the same die
    let drop = 2; const flaky = D.HttpAtomic(base, async (u, init) => { const r = await fetch(u, init); if (/\/atomic\/roll$/.test(u) && drop-- > 0) throw new TypeError("network lost after server processed"); return r; });
    const g = await fight("predator", flaky); const jg = await flaky.journal(g.ctx.session);
    ok(!!g.s.over && D.stateHash(D.replay(C, S, jg).state) === D.stateHash(g.s), "lost roll responses are retried idempotently (same dice, same state)");
    ok(new Set(jg.tape.map((d) => d.seq)).size === jg.tape.length && jg.tape.every((d, i) => d.seq === i), "no duplicate or skipped dice in the journal after retries");
    // 4. interrupted mid-turn: commit + some dice, then the page dies; a new client resumes exactly there
    const o = await at.open({ scenario: "duelist", switches: {} }); const ctx = { atomic: at, session: o.session };
    let s = E.newState(C, S, "duelist", { atomic: true }); s.dist["aero|ilsa"] = 5;   // (fixture distance is part of the state; set it the same way on both sides)
    const plan = [{ pid: "move", dest: "close", target: "ilsa" }, { pid: "feint", target: "ilsa" }, { pid: "saber_strike", target: "ilsa" }];
    let calls = 0; const crash = D.runTurn(ctx, E.newState(C, S, "duelist", { atomic: true }), "aero", plan, { playerRoll: async () => { if (++calls === 2) throw new Error("tab closed"); } });
    await crash.catch(() => {});
    const j2 = await at.journal(o.session); const rp = D.replay(C, S, j2);
    ok(rp.pending && rp.pending.turn_key === "R1.T0.aero" && j2.tape.length > 0, "after a crash mid-turn the journal shows the turn pending with its dice kept", JSON.stringify(rp.pending && rp.pending.turn_key));
    const before = j2.tape.map((d) => d.value);
    const resumed = await D.runTurn(ctx, rp.state, "aero", rp.pending.plan, { choices: rp.pending.choices, decide: async (p) => p.options[0] });
    const j3 = await at.journal(o.session);
    ok(!resumed.refused && JSON.stringify(j3.tape.slice(0, before.length).map((d) => d.value)) === JSON.stringify(before), "resuming reuses the already-drawn dice (no reroll) and finishes the turn");
    ok(D.stateHash(D.replay(C, S, j3).state) === D.stateHash(resumed.state), "resumed turn equals a clean replay");
    // 5. the client cannot change the plan once dice are drawn
    let code = null; try { await at.commit(o.session, "R1.T0.aero", "aero", [{ pid: "saber_strike", target: "ilsa" }]); } catch (e) { code = e.code; } ok(code === "PLAN_LOCKED" || code === "TURN_ORDER", "re-planning a turn after its dice is refused", code);
    // cross-site form posts (text/plain) are refused
    const xs = await fetch(base + "/atomic/open", { method: "POST", headers: { "Content-Type": "text/plain" }, body: "{}" }); ok(xs.status === 415, "non-JSON (cross-site form) posts to /atomic are refused", xs.status);
    // 6. relay droid: ranged enemy, blaster, deflect reaction, all through Atomic
    const d = await fight("relay_droid", at);
    ok(!!d.s.over, "relay droid fight (ranged enemy) finishes through Atomic");
  } catch (e) { fails++; console.log("FAIL exception", e.stack); }
  finally { srv.kill(); }
  console.log(fails ? fails + " FAILED" : "all passed"); process.exit(fails ? 1 : 0);
})();
