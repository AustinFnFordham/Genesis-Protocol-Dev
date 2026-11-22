// CC-005 server-side engine worker. The Atomic service (Python) runs this as a long-lived child process and asks it
// to rebuild a session from the JOURNAL ONLY (its own record of commits, accepted dice and decisions). Its answers are
// the authority: what the next turn is, whose it is, the GM's plan for an NPC, whether a plan is legal, which dice the
// engine needs next and for whom, which decision is pending, and the state hash after each completed turn.
// Protocol: one JSON request per line on stdin -> one JSON response per line on stdout.
const E = require("./engine.js"), D = require("./turn_driver.js");
const C = require("./catalog.json"), S = require("./scenarios.json");
const readline = require("readline");
function clone(x) { return JSON.parse(JSON.stringify(x)); }
function inspect(journal, candidate) {
  if (!S.scenarios[(journal.meta || {}).scenario]) return { error: "UNKNOWN_SCENARIO" };
  const rb = D.replay(clone(C), S, journal), s = rb.state, out = { hash: D.stateHash(s), over: s.over || null, round: s.round };
  if (rb.pending) {
    const p = rb.pending; out.pending = { turn_key: p.turn_key, actor: p.actor };
    if (p.need_dice) { const n = p.need_dice; out.pending.need = { dice: n.dice.filter((d) => !s.tape[d.seq]), actor: n.actor, controller: s.actors[n.actor].controller, purpose: n.purpose, step: n.step, rules: n.rules, target: n.target, kind: n.kind }; }
    if (p.paused) out.pending.paused = { key: p.paused.key, actor: p.paused.actor, controller: s.actors[p.paused.actor].controller, kind: p.paused.kind, options: p.paused.options };
  } else if (!s.over) {
    const a = E.current(s); out.next = { turn_key: D.turnKey(s), actor: a, controller: s.actors[a].controller };
    if (s.actors[a].controller === "npc") out.next.npc_plan = E.npcPlan(s, a);
  }
  if (candidate && candidate.actor && s.actors[candidate.actor]) { const v = E.validatePlan(s, candidate.actor, candidate.plan || []); out.validation = { legal: v.legal, reasons: (v.steps || []).filter((x) => !x.ok).map((x) => ({ step: x.i, pid: x.pid, codes: x.reasons.map((r) => r.code) })).concat((v.errors || []).map((e) => ({ codes: [e.code] }))) }; }
  if (candidate && candidate.want_state) out.state = s;
  return out;
}
const rl = readline.createInterface({ input: process.stdin });
rl.on("line", (line) => {
  let req; try { req = JSON.parse(line); } catch (e) { process.stdout.write(JSON.stringify({ error: "BAD_JSON" }) + "\n"); return; }
  let res; try { res = req.op === "inspect" ? inspect(req.journal, req.candidate) : { error: "NO_OP" }; } catch (e) { res = { error: "ENGINE_ERROR", text: String(e.message).slice(0, 300) }; }
  process.stdout.write(JSON.stringify(Object.assign({ id: req.id }, res)) + "\n");
});
