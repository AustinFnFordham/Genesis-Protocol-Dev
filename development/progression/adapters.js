// Authority-side adapters that turn VALIDATED, COMMITTED facts into skill-use events for the mastery ledger (CC-007 §4/§5).
// Sandbox only. The client never calls these; a narrated or asserted use produces nothing.
"use strict";
const crypto = require("crypto"), M = require("./mastery.js");
const sha = (s) => crypto.createHash("sha256").update(s).digest("hex");

// Combat: telekinesis events in an engine turn that the SERVER has verified (CC-005 'verify ok:true').
function combatEvents(def, sessionId, turnKey, state, fromLogIndex, verified, character) {
  if (verified !== true) return { ok: false, code: "TURN_NOT_VERIFIED", events: [] };
  const out = [];
  state.log.forEach((l, i) => { if (i < fromLogIndex || l.ev !== "telekinesis" || l.actor !== character) return;
    out.push({ event_id: "evt_" + sha([sessionId, turnKey, i, "telekinesis"].join("|")).slice(0, 24), authority: "atomic", committed: true, validated: true,
               type: "telekinesis_use", skill: def.id, actor: l.actor, source: { session: sessionId, turn_key: turnKey, log_index: i, mode: l.mode },
               facts: { weight_lb: l.weight_lb, distance_ft: l.distance_ft, object_kind: l.object_kind, in_encounter: true } }); });
  return { ok: true, events: out };
}

// Exploration: the authority validates one declared out-of-combat use against SCENE OBJECT DATA (not the player's words).
// At-will, no roll — unless the authority marks the outcome uncertain (Jedi Fundamentals open item 1: roll not owner-set → refused here).
function explorationUse(def, mastery, scene, use, grants) {
  const st = mastery.skills[def.id] || { level: 0 }, cap = M.capability(def, st.level).values, o = scene.objects.find((x) => x.id === use.object);
  const refuse = (code, text) => ({ ok: false, code, text });
  if (!o) return refuse("NO_SUCH_OBJECT", "Not in this scene.");
  if (!o.visible) return refuse("NOT_VISIBLE", "Minor Telekinesis needs a visible object.");
  if (o.attended) return refuse("ATTENDED_OBJECT", "Held, worn or carried by someone: never.");
  const fine = (grants || []).some((g) => g.milestone === "tk_m5_fine_manipulation");
  if (o.fixed && !fine) return refuse("FIXED_OBJECT", "Fixed in place (operating mechanisms is the level-5 training opportunity, not granted).");
  if (o.weight_lb > cap.max_weight_lb) return refuse("TOO_HEAVY", o.weight_lb + " lb is over your " + cap.max_weight_lb + " lb.");
  if (o.distance_ft > cap.range_ft) return refuse("OUT_OF_RANGE", o.distance_ft + " ft is beyond your " + cap.range_ft + " ft.");
  if (use.uncertain) return refuse("ROLL_RULE_UNSET", "An uncertain use needs the owner's roll rule (Jedi Fundamentals open item 1).");
  return { ok: true, event: { event_id: "evt_" + sha([scene.scene, use.use_id].join("|")).slice(0, 24), authority: "atomic_exploration", committed: true, validated: true,
           type: "telekinesis_use", skill: def.id, actor: mastery.character, source: { scene: scene.scene, use_id: use.use_id, object: o.id },
           facts: { weight_lb: o.weight_lb, distance_ft: o.distance_ft, object_kind: o.kind, in_encounter: false } } };
}
// The engine-side limits a session would use for this character's current mastery (session overlay only).
function tkLimits(def, mastery) { const st = mastery.skills[def.id] || { level: 0 }, c = M.capability(def, st.level);
  return { range_ft: c.values.range_ft, max_weight_lb: c.values.max_weight_lb, objects_at_once: c.values.objects_at_once, source: def.id + "@" + def.version + " level " + st.level + " (sandbox overlay)" }; }
module.exports = { combatEvents, explorationUse, tkLimits };
