// CC-009 read-only audit: replay every committed Hask Meadow r2 combat declaration through the CURRENT turn contract,
// using the exact turn context the GM published before it, and compare with what the record then did.
// Reads campaigns/starwars_litrpg/runs/hask_meadow_r2/records/events.jsonl only. Writes nothing to the campaign.
"use strict";
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const REPO = path.join(__dirname, "../.."), EV = path.join(REPO, "campaigns/starwars_litrpg/runs/hask_meadow_r2/records/events.jsonl");
const T = require(path.join(REPO, "campaigns/starwars_litrpg/ui/turn_contract.js"));
function audit() {
  const raw = fs.readFileSync(EV), ev = raw.toString("utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
  const rows = []; let ctx = null;
  ev.forEach((e, i) => {
    if (e.kind === "turn_context") ctx = e.details;
    if (e.kind !== "player_declaration" || !ctx || ctx.mode !== "combat" || ctx.reaction_prompt) return;
    const decl = e.details.declaration, v = T.validate(decl, ctx);
    const after = ev.slice(i + 1); const nextDecl = after.findIndex((x) => x.kind === "player_declaration");
    const window = nextDecl < 0 ? after : after.slice(0, nextDecl);
    const ended = window.some((x) => x.kind === "combat_round" && /ends his round-\d+ turn/.test(x.summary));
    const pp = window.filter((x) => x.kind === "plan_progress").pop();
    const left = ["action", "bonus_action", "object_interaction"].filter((k) => ((ctx.budget || {})[k] == null ? 1 : ctx.budget[k]) - (v.used[k] || 0) > 0);
    const mvLeft = ((ctx.budget || {}).movement_ft || 0) - (v.used.movement_ft || 0);
    rows.push({ event: e.event_id, action_id: e.details.action_id, round: ctx.round, budget_before: ctx.budget, hands_before: ctx.hands || null,
      declared_end_turn: decl.end_turn === true, steps: (decl.steps || []).length, current_validator: { legal: v.legal, ends_turn: v.ends_turn, errors: v.errors.map((x) => x.code), info: v.info.map((x) => x.code) },
      unspent_after_plan: { slots: left, movement_ft: mvLeft }, record_ended_turn: ended, record_stop: pp ? (pp.details || {}).stop_kind || null : null,
      finding: ended && !v.ends_turn ? "RECORD_ENDED_TURN_THAT_CURRENT_CONTRACT_CONTINUES" : !ended && v.ends_turn ? "RECORD_CONTINUED_TURN_CURRENT_CONTRACT_ENDS" : null });
  });
  return { schema: "genesis-cc009-hask-replay/0.1", canonical: false, source: { path: path.relative(REPO, EV), sha256: crypto.createHash("sha256").update(raw).digest("hex"), events: ev.length },
           contract: T.VERSION, rows, summary: { declarations: rows.length, findings: rows.filter((r) => r.finding).map((r) => ({ event: r.event, round: r.round, finding: r.finding, unspent: r.unspent_after_plan })) } };
}
module.exports = { audit };
if (require.main === module) { const r = audit(); const out = path.join(__dirname, "evidence/hask_replay.json"); fs.mkdirSync(path.dirname(out), { recursive: true }); fs.writeFileSync(out, JSON.stringify(r, null, 1) + "\n"); console.log(JSON.stringify(r.summary, null, 1)); }
