// CC-005b on the real preview server: role tokens, server-run GM, viewer-specific projections, campaign overlay.
const { spawn } = require("child_process"); const path = require("path"), fs = require("fs"), os = require("os");
const E = require("./engine.js"), D = require("./turn_driver.js"), C = require("./catalog.json"), S = require("./scenarios.json");
let fails = 0; const ok = (c, n, x) => { console.log((c ? "ok " : "FAIL ") + n + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 300))); if (!c) fails++; };
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "cc005b-")), port = 22000 + Math.floor(Math.random() * 2000);
const srv = spawn("python3", ["-B", path.join(__dirname, "../preview/serve_preview.py"), "--port", String(port)], { env: Object.assign({}, process.env, { GENESIS_ATOMIC_DIR: dir }), stdio: "ignore" });
const base = "http://127.0.0.1:" + port;
async function post(p, b) { const r = await fetch(base + p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) }); return { status: r.status, body: await r.json() }; }
function legal(s, plan) { const out = []; for (const st of plan) if (E.validatePlan(s, "aero", out.concat([st])).legal) out.push(st); return out; }
(async () => {
  for (let i = 0; i < 100; i++) { try { await fetch(base + "/healthz"); break; } catch (e) { await new Promise((r) => setTimeout(r, 150)); } }
  try {
    // ---- roles ----
    const pr = await post("/atomic/open", { scenario: "predator" }); const sid = pr.body.session, P = pr.body.player_token, G = pr.body.gm_token;
    ok(P && G, "practice: player and GM tokens issued");
    const j0 = await post("/atomic/journal", { session: sid, token: P }); ok(!JSON.stringify(j0.body).includes("_tokens") && !JSON.stringify(j0.body).includes(P), "journals never expose tokens or their hashes");
    ok((await post("/atomic/journal", { session: sid })).status === 401 && (await post("/atomic/journal", { session: sid, token: "forged" })).status === 401, "no token or a forged token: 401");
    const s0 = E.newState(C, S, "predator", { atomic: true }), gp = E.npcPlan(s0, "stalker");
    ok((await post("/atomic/commit", { session: sid, token: P, turn_key: "R1.T0.stalker", actor: "stalker", plan: gp })).body.error === "FORBIDDEN_ROLE", "a player token cannot commit the NPC's turn");
    const cm = await post("/atomic/commit", { session: sid, token: G, turn_key: "R1.T0.stalker", actor: "stalker", plan: gp }); ok(cm.status === 200, "the GM token can");
    ok((await post("/atomic/roll", { session: sid, token: P, turn_key: "R1.T0.stalker", plan_hash: cm.body.plan_hash, dice: [{ seq: 0, sides: 20 }, { seq: 1, sides: 20 }], roller: "gm", actor: "stalker" })).body.error === "FORBIDDEN_ROLE", "a player token cannot roll GM dice");
    ok((await post("/atomic/state", { session: sid, token: P })).status === 403, "full state needs the GM (debug) token");
    // ---- a bound encounter played with ONLY the player token; the server is the GM ----
    const b = await post("/atomic/open", { scenario: "duelist", mode: "bound", encounter_id: "cc005b.duel." + Date.now() }); const bs = b.body.session, BP = b.body.player_token;
    ok(BP && !b.body.gm_token, "bound: player token only");
    let s = E.newState(C, S, "duelist", { atomic: true }), steps = 0, playerRolls = 0, over = null;
    const call = (p, x) => post(p, Object.assign({ session: bs, token: BP }, x));
    for (let k = 0; k < 400 && !over; k++) {
      const g = (await call("/atomic/gm_step", {})).body;
      if (g.stopped === "over") { over = g.over; break; }
      if (g.stopped === "player_turn") {
        const j = (await call("/atomic/journal", {})).body; s = D.replay(C, S, j).state;
        const foe = "ilsa", plan = legal(s, [{ pid: "recover_weapon" }, { pid: "move", dest: "close", target: foe }, { pid: "saber_strike", target: foe }, { pid: "unarmed_strike", target: foe }, { pid: "flow_strike", target: foe }]);
        const c = await call("/atomic/commit", { turn_key: g.turn_key, actor: "aero", plan: plan.length ? plan : [{ pid: "tactical_glance" }] }); if (c.status !== 200) throw new Error("commit " + JSON.stringify(c.body));
        steps++; continue;
      }
      if (g.stopped === "player_roll") { playerRolls++; const r = await call("/atomic/roll", { turn_key: g.turn_key, plan_hash: g.plan_hash, dice: g.need.dice, roller: "player", actor: g.need.actor }); if (r.status !== 200) throw new Error("roll " + JSON.stringify(r.body)); continue; }
      if (g.stopped === "player_decision") { await call("/atomic/decide", { turn_key: g.turn_key, key: g.paused.key, choice: g.paused.options[0] }); continue; }
      throw new Error("gm_step " + JSON.stringify(g));
    }
    ok(!!over && steps > 0 && playerRolls > 0, "a whole bound duel played with only the player token (server ran Ilsa)", [over, steps, playerRolls]);
    const jb = (await call("/atomic/journal", {})).body;
    ok(jb.tape.filter((d) => d.roller === "gm").length > 0 && jb.tape.filter((d) => d.roller === "player").length === jb.tape.filter((d) => d.roller === "player").length, "GM dice were rolled by the server-side GM");
    ok((await call("/atomic/state", {})).status === 403 && (await call("/atomic/view", { as: "gm" })).body.view.projection === "player", "bound: no debug view for the player (state refused; view is the player projection)");
    // ---- projection contents ----
    const v = (await call("/atomic/view", {})).body.view, txt = JSON.stringify(v), real = D.replay(C, S, jb).state;
    ok(v.actors.aero.hp === real.actors.aero.hp && v.actors.aero.ac === 13, "own sheet visible in full");
    const I = v.actors.ilsa; ok(!I || (I.hp === null && I.ac === null && I.hp_max === null), "enemy HP and AC are not in the player projection", I);
    ok(!JSON.stringify(v).match(/"type":"ac","target":"ilsa","value":\d/) && !/\/20\)/.test(txt), "no enemy AC value or HP fraction anywhere (receipts and log text included)");
    if (I && I.ac_known) { const k = I.ac_known; ok((k.ac_min == null || k.ac_min <= 15) && (k.ac_max == null || k.ac_max >= 15), "learned AC bounds are consistent with the truth (" + JSON.stringify(k) + ")"); }
    // practice: GM may ask for the debug view, or the player projection explicitly
    const pv = (await post("/atomic/view", { session: sid, tokens: { player: P, gm: G } })).body, pv2 = (await post("/atomic/view", { session: sid, tokens: { player: P, gm: G }, as: "player" })).body;
    ok(pv.view.actors.stalker && pv.view.actors.stalker.ac === 13 && pv2.view.projection === "player" && pv2.hash === null, "practice: full debug view for the GM token; player projection on request");
    ok(!pv2.view.actors.stalker || pv2.view.actors.stalker.ac == null, "a hidden predator does not appear in the player projection");
    // ---- campaign overlay over the server ----
    const co = await post("/atomic/open", { scenario: "duelist", campaign: "starwars_litrpg" }); const cst = (await post("/atomic/state", { session: co.body.session, token: co.body.gm_token })).body.state;
    ok(cst.actors.aero.profiles.includes("minor_telekinesis") && cst.campaign === "starwars_litrpg", "campaign overlay applied server-side from the repo's rule file");
    ok((await post("/atomic/open", { scenario: "duelist", campaign: "some_other_campaign" })).body.error === "BAD_CAMPAIGN", "unknown campaign refused");
    const np = await post("/atomic/open", { scenario: "duelist", overlays: [{ campaign: null, profile: "minor_telekinesis", granted_to: [{ character: "aero" }] }] }); const nst = (await post("/atomic/state", { session: np.body.session, token: np.body.gm_token })).body.state;
    ok(!nst.actors.aero.profiles.includes("minor_telekinesis"), "a client-supplied overlay is ignored (grants come only from the server's rule files)");
  } catch (e) { fails++; console.log("FAIL exception", e.stack); }
  finally { srv.kill(); }
  console.log(fails ? fails + " FAILED" : "all passed"); process.exit(fails ? 1 : 0);
})();
