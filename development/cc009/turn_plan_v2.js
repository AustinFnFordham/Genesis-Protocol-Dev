/* Genesis Combat Turn Builder v2 — structured turn plan (CC-009 prototype, NONCANONICAL).
 *
 * A thin layer OVER the existing live contract (campaigns/starwars_litrpg/ui/turn_contract.js, turn-contract/3). It adds no
 * second validator and no rules: every legality, cost, hand and budget verdict comes from GenesisTurn.validate(). What v2 adds:
 *   - one explicit ordered activity list with slot, capability-or-custom intent, typed target, speech, flair, conditions and
 *     dependencies (`after`), editable before submission;
 *   - three separate layers per activity: INTENTION (what the player wrote), AUTHORIZATION (the validator's verdict on
 *     the capability), OUTCOME (only ever filled from committed GM/Atomic events, never predicted here);
 *   - plan-level gates the live contract does not express: staleness against the published context, ruleset gating of the
 *     Secondary Action (absent unless the active ruleset enables it), dependency order, explicit end-of-turn.
 * It never rolls dice, never writes a ledger, never edits history. Output for live use is a turn-contract/3 declaration.
 */
(function (root, factory) {
  var api = factory(typeof require === "function" ? require("../../campaigns/starwars_litrpg/ui/turn_contract.js") : root.GenesisTurn);
  if (typeof module === "object" && module.exports) module.exports = api; else root.GenesisTurnPlanV2 = api;
})(typeof self !== "undefined" ? self : this, function (T) {
  "use strict";
  var SCHEMA = "genesis-turn-plan/2.0-candidate";
  var SLOTS = ["main", "bonus", "reaction", "movement", "object", "free", "speech", "secondary"];
  var TO_STEP = { main: "action", bonus: "bonus_action", movement: "move", object: "object", free: "free", speech: "speech" };
  var TARGET_KINDS = ["enemy", "ally", "self", "object", "location"];
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function err(code, message, id) { return { code: code, message: message, activity: id || null }; }

  function newPlan(ctx, extra) {
    return Object.assign({ schema: SCHEMA, actor: ctx.actor, based_on: { context_id: ctx.context_id || null }, activities: [], end_turn: false }, extra || {});
  }
  // ---- editing before submission (pure; each returns a new plan) ----
  var seq = 0;
  function add(plan, a, index) { var p = clone(plan), x = clone(a); x.id = x.id || "a" + (++seq) + "_" + p.activities.length; if (index == null) p.activities.push(x); else p.activities.splice(index, 0, x); return p; }
  function remove(plan, id) { var p = clone(plan); p.activities = p.activities.filter(function (a) { return a.id !== id; });
    p.activities.forEach(function (a) { if (a.after) a.after = a.after.filter(function (d) { return d !== id; }); }); return p; }
  function move(plan, id, toIndex) { var p = clone(plan), i = p.activities.findIndex(function (a) { return a.id === id; }); if (i < 0) return p;
    var x = p.activities.splice(i, 1)[0]; p.activities.splice(Math.max(0, Math.min(toIndex, p.activities.length)), 0, x); return p; }
  function update(plan, id, patch) { var p = clone(plan); p.activities = p.activities.map(function (a) { return a.id === id ? Object.assign({}, a, clone(patch)) : a; }); return p; }

  function rulesetAllowsSecondary(ctx) { return !!(ctx && ctx.ruleset && ctx.ruleset.secondary_action === true); }

  // ---- v2 → turn-contract/3 declaration (order preserved; reactions stay declared intents, not steps) ----
  function toDeclaration(plan, ctx) {
    var steps = [], reactions = [];
    plan.activities.forEach(function (a) {
      if (a.slot === "reaction") { if (a.capability && a.capability.option) reactions.push(a.capability.option); return; }
      if (a.slot === "secondary") return;   // gated out in evaluate(); never sent to the live contract
      var s = { id: a.id, type: TO_STEP[a.slot] };
      if (a.slot === "speech") { s.text = (a.speech && a.speech.text) || ""; s.extended = !!(a.speech && a.speech.extended); if (a.target) s.target = a.target.id; }
      else if (a.capability && a.capability.option) { s.option = a.capability.option; if (a.target && a.target.id) s.target = a.target.id; if (a.trigger) s.trigger = a.trigger; }
      else { s.type = "free"; s.kind = "custom"; s.text = (a.intent && a.intent.text) || ""; if (a.target && a.target.id) s.targets = [a.target.id]; }
      if (a.condition && a.condition.text) s.condition = { text: a.condition.text };
      if (a.flair) s.flair = a.flair;              // descriptive only; the contract ignores it, the GM may narrate it
      if (a.pending) { s.pending = true; if (a.status) s.status = a.status; }
      steps.push(s);
    });
    var d = { actor: plan.actor, source: "composer", freeform: "", speech: null, actions: [], bonus_actions: [], movement: null, objects: [], reactions: reactions, unmapped: [], steps: steps };
    if (plan.end_turn === true) d.end_turn = true;
    if (plan.whisper !== undefined) d.whisper = clone(plan.whisper);   // WHISPER stays governed by its own contract; carried untouched
    return d;
  }

  function evaluate(plan, ctx) {
    var errors = [], warnings = [], ids = {};
    if (plan.schema !== SCHEMA) errors.push(err("PLAN_SCHEMA", "Unknown plan schema."));
    if (plan.actor !== ctx.actor) errors.push(err("PLAN_ACTOR", "This plan belongs to another character."));
    if (!plan.based_on || plan.based_on.context_id !== (ctx.context_id || null))
      errors.push(err("STALE_PLAN", "The scene changed after this plan was written. Review the latest turn and resubmit; nothing was resolved."));
    plan.activities.forEach(function (a, i) {
      if (ids[a.id]) errors.push(err("DUPLICATE_ACTIVITY", "Two activities share an id.", a.id)); ids[a.id] = i;
      if (SLOTS.indexOf(a.slot) < 0) errors.push(err("UNKNOWN_SLOT", "Unknown kind of activity.", a.id));
      if (a.slot === "secondary" && !rulesetAllowsSecondary(ctx)) errors.push(err("SECONDARY_NOT_ENABLED", "Secondary Actions are not part of this campaign's rules.", a.id));
      if (a.target && TARGET_KINDS.indexOf(a.target.kind) < 0) errors.push(err("TARGET_KIND", "A target must be an enemy, ally, self, object or location.", a.id));
      if (a.slot !== "speech" && a.slot !== "reaction" && !(a.capability && a.capability.option) && !(a.intent && String(a.intent.text || "").trim()))
        errors.push(err("EMPTY_ACTIVITY", "Pick a capability or describe what you try.", a.id));
      if (a.slot === "reaction" && !(a.trigger || (a.capability && a.capability.option)))
        errors.push(err("REACTION_NEEDS_TRIGGER", "A reaction needs the event that would trigger it.", a.id));
      (a.after || []).forEach(function (d) {
        if (!(d in ids)) errors.push(err(plan.activities.some(function (b) { return b.id === d; }) ? "DEPENDENCY_ORDER" : "DEPENDENCY_UNKNOWN",
          "This activity depends on one that is not before it. Move it after what it needs.", a.id));
      });
    });
    var decl = toDeclaration(plan, ctx), v = T.validate(decl, ctx), st = T.stepStatus(v);
    var layers = plan.activities.map(function (a) {
      var s = st[a.id], gate = errors.filter(function (e) { return e.activity === a.id; });
      var auth = gate.length ? "blocked" : a.slot === "reaction" ? (ctx.reaction_prompt ? "offered_now" : "declared_intent")
        : !s ? "not_sent" : s.status === "fix" ? "blocked" : s.status === "gm" ? "needs_adjudication" : s.status === "waits" || s.status === "branch" ? "waits_on_condition" : "known_legal";
      return { id: a.id, slot: a.slot,
               intention: { text: a.intent ? a.intent.text : null, speech: a.speech ? a.speech.text : null, flair: a.flair || null, capability: a.capability ? a.capability.option : null, target: a.target || null },
               authorization: { verdict: auth, messages: gate.map(function (e) { return e.message; }).concat(s ? s.messages : []),
                                cost_known: !(a.slot === "free" || (!a.capability && a.slot !== "speech")), speech_effect: a.slot === "speech" ? "words only; any effect on others is adjudicated" : undefined },
               outcome: null };   // filled only from committed events by the GM/Atomic, never here
    });
    var legal = errors.length === 0 && v.legal;
    return { schema: SCHEMA, legal: legal, submittable: legal, errors: errors.concat(v.errors.map(function (e) { return err(e.code, e.message, e.step_id); })),
             warnings: warnings.concat(v.warnings), info: v.info, used: v.used, ends_turn: legal && v.ends_turn, partial_ok: true, layers: layers, declaration: decl, contract: v };
  }
  // the narrative channel: speech and description are always offered, whatever the budget (their mechanical effects are not)
  function narrativeAvailable() { return true; }
  return { SCHEMA: SCHEMA, SLOTS: SLOTS, TARGET_KINDS: TARGET_KINDS, newPlan: newPlan, add: add, remove: remove, move: move, update: update,
           toDeclaration: toDeclaration, evaluate: evaluate, rulesetAllowsSecondary: rulesetAllowsSecondary, narrativeAvailable: narrativeAvailable };
});
