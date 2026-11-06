/* Genesis composite-turn contract: parse + preflight validation.
 *
 * ONE implementation, two hosts: the Datapad inlines this file (build_datapad.py) for the live
 * preview, and the GM turn processor runs it under node (`node turn_contract.js validate ...`)
 * before any die is rolled. Same input, same verdict.
 *
 * Inputs are PLAYER-VISIBLE only. `ctx` (the turn context) is published by the GM in view/state
 * and never contains hidden stats, DCs, enemy HP or hidden capabilities. The validator therefore
 * cannot leak them, and it never predicts dice.
 *
 * Declaration shape (the same for composer selections and parsed free text):
 *   { actor, source: "composer"|"freeform", freeform: "...",
 *     speech:  { option: "d1"|null, text: "...", approach: "...", extended: false } | null,
 *     actions: [ { option: "burst", target: "dog_a"|null, trigger: "..."|null } ],   // primary actions
 *     bonus_actions: [ { option: "...", target: null } ],
 *     movement: { option: "to_ramp" } | null,
 *     objects: [ "ignite_saber" ],                        // object interactions
 *     reactions: [ "sentinel_balance" ],                  // declared reaction intents (conditional)
 *     unmapped: [ "text the parser could not map" ] }
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.GenesisTurn = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  var VERSION = "turn-contract/1";

  function byId(list, id) { for (var i = 0; i < (list || []).length; i++) if (list[i].id === id) return list[i]; return null; }
  function lc(s) { return String(s || "").toLowerCase(); }
  function uniq(a) { var o = []; a.forEach(function (x) { if (o.indexOf(x) < 0) o.push(x); }); return o; }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function names(ctx, ids) { return ids.map(function (id) { var v = byId(ctx.visible, id); return v ? v.label : id; }); }
  function joinAnd(a, w) { return a.length <= 1 ? (a[0] || "") : a.slice(0, -1).join(", ") + " " + (w || "and") + " " + a[a.length - 1]; }

  function emptyDecl(ctx) {
    return { actor: ctx.actor, source: "composer", freeform: "", speech: null, actions: [], bonus_actions: [],
             movement: null, objects: [], reactions: [], unmapped: [] };
  }

  /* ---------- free-text parsing (deterministic, alias-driven) ----------
   * The GM publishes aliases with every option. The parser finds every option whose alias occurs in
   * the text and records ALL of them, so conflicts surface in validation instead of being silently
   * resolved. The GM processor re-reads the text with judgment, but must run the same validator. */
  function findAliases(text, list) {
    var t = " " + lc(text).replace(/[^a-z0-9' ]+/g, " ") + " ", hits = [];
    (list || []).forEach(function (o) {
      var al = (o.aliases || []).concat([o.label || ""]);
      for (var i = 0; i < al.length; i++) {
        var a = lc(al[i]).replace(/[^a-z0-9' ]+/g, " ").trim();
        if (a && t.indexOf(" " + a + " ") >= 0) { hits.push({ id: o.id, pos: t.indexOf(" " + a + " ") }); break; }
      }
    });
    return hits.sort(function (x, y) { return x.pos - y.pos; }).map(function (h) { return h.id; });
  }

  function parseFreeform(text, ctx) {
    var d = emptyDecl(ctx); d.source = "freeform"; d.freeform = String(text || "");
    var quotes = d.freeform.match(/["“]([^"”]+)["”]/g);
    var bare = d.freeform.replace(/["“][^"”]*["”]/g, " ");
    if (quotes) d.speech = { option: null, text: quotes.map(function (q) { return q.replace(/^["“]|["”]$/g, ""); }).join(" "), approach: "freeform", extended: false };
    var opts = (ctx.options || []);
    // "ready" swallows the attack it readies: "ready a strike" is one action, not two.
    var acts = findAliases(bare, opts.filter(function (o) { return o.slot === "action"; }));
    var ready = acts.filter(function (id) { var o = byId(opts, id); return o && o.needs_trigger; });
    if (ready.length) acts = acts.filter(function (id) { var o = byId(opts, id); return ready.indexOf(id) >= 0 || !(o && o.readiable); });
    d.actions = acts.map(function (id) {
      var o = byId(opts, id), a = { option: id, target: null, trigger: null };
      if (o && o.needs_trigger) { var m = bare.match(/(?:against|at|when|if)\s+([^,.;]+)/i); a.trigger = m ? m[0].trim() : (o.default_trigger || null); }
      if (o && o.needs_target) { var tg = findAliases(bare, ctx.visible); a.target = tg[0] || null; }
      return a;
    });
    d.bonus_actions = findAliases(bare, opts.filter(function (o) { return o.slot === "bonus_action"; })).map(function (id) { return { option: id, target: null }; });
    var mv = findAliases(bare, (ctx.movement || []).filter(function (m) { return m.id !== "hold"; }));
    d.movement = mv.length ? { option: mv[0] } : null;
    d.objects = findAliases(bare, ctx.objects);
    d.reactions = findAliases(bare, ctx.reactions);
    if (!d.actions.length && !d.movement && !d.objects.length && !d.speech) d.unmapped.push(d.freeform);
    return d;
  }

  /* ---------- preflight validation ---------- */
  function validate(decl, ctx) {
    var errors = [], warnings = [], info = [], preview = [];
    var b = ctx.budget || {}, opts = ctx.options || [];
    function err(code, msg) { errors.push({ code: code, message: msg }); }
    function warn(code, msg) { warnings.push({ code: code, message: msg }); }

    // 1-2. acting character
    if (decl.actor !== ctx.actor) err("ACTOR", "Only " + (ctx.actor_name || ctx.actor) + " can act this turn. Viewing another party member never grants control of them.");
    if (ctx.actor_conditions && ctx.actor_conditions.some(function (c) { return /unconscious|dead|incapacitated/.test(c); }))
      err("INCAPACITATED", (ctx.actor_name || ctx.actor) + " cannot act (" + ctx.actor_conditions.join(", ") + ").");

    var actions = decl.actions || [], bonus = decl.bonus_actions || [], objs = decl.objects || [];
    var flags = (ctx.state_flags || []).slice();
    objs.forEach(function (oid) { var o = byId(ctx.objects, oid); if (o) flags = flags.concat(o.grants || []); });

    // 4. capabilities exist
    actions.concat(bonus).forEach(function (a) { if (!byId(opts, a.option)) err("UNKNOWN_OPTION", "\"" + a.option + "\" is not something " + (ctx.actor_name || ctx.actor) + " can do right now."); });
    objs.forEach(function (oid) { if (!byId(ctx.objects, oid)) err("UNKNOWN_OBJECT", "\"" + oid + "\" is not an available object interaction."); });

    // speech: brief speech is free; extended or check-based social actions use the action
    var speechAction = decl.speech && decl.speech.extended && ctx.mode === "combat";
    var actionCount = actions.length + (speechAction ? 1 : 0);
    var actLabels = actions.map(function (a) { var o = byId(opts, a.option); return o ? o.label : a.option; });
    if (speechAction) actLabels.push("an extended social action");

    // 3. action economy
    var extraObjects = Math.max(0, objs.length - (b.object_interaction == null ? 1 : b.object_interaction));
    if (extraObjects) { actionCount += extraObjects; actLabels.push("a second object interaction"); }
    if (actionCount > (b.action == null ? 1 : b.action))
      err("ACTION_CONFLICT", joinAnd(actLabels) + (actionCount === 2 ? " both require" : " all require") + " your primary action, so you cannot use " + (actionCount === 2 ? "both" : "them all") +
        " this turn unless another feature grants you an additional action.");
    if (bonus.length > (b.bonus_action == null ? 1 : b.bonus_action)) err("BONUS_CONFLICT", "You have one bonus action this turn.");
    bonus.forEach(function (a) { var o = byId(opts, a.option); if (o && o.slot !== "bonus_action") err("NOT_BONUS", o.label + " is not a bonus action."); });
    actions.forEach(function (a) { var o = byId(opts, a.option); if (o && o.slot !== "action") err("NOT_ACTION", o.label + " is not a primary action."); });

    // 4-5. requirements, range, target, area
    actions.concat(bonus).forEach(function (a) {
      var o = byId(opts, a.option); if (!o) return;
      (o.requires || []).forEach(function (r) { if (flags.indexOf(r) < 0) err("REQUIRES", o.label + " needs " + (ctx.flag_labels && ctx.flag_labels[r] || r) + " first."); });
      if (o.needs_target) {
        var t = byId(ctx.visible, a.target);
        // movement may be split around the action, so the closest point of the declared move counts
        var mvA = decl.movement ? byId(ctx.movement, decl.movement.option) : null;
        var dist = t ? Math.min(t.distance_ft, mvA && mvA.distance_after && mvA.distance_after[t.id] != null ? mvA.distance_after[t.id] : t.distance_ft) : null;
        if (!t) err("TARGET", o.label + " needs a visible target.");
        else if (o.reach_ft != null && dist > o.reach_ft) err("RANGE", t.label + " is about " + dist + " ft away, beyond " + o.label + "'s reach of " + o.reach_ft + " ft.");
      }
      if (o.needs_trigger && !a.trigger) err("TRIGGER", o.label + " needs a trigger (for example, \"" + (o.default_trigger || "when a hostile moves into reach") + "\").");
      if (o.area_ft != null) {
        var inside = (ctx.visible || []).filter(function (v) { return v.distance_ft <= o.area_ft; }).map(function (v) { return v.label; });
        var outside = (ctx.visible || []).filter(function (v) { return v.distance_ft > o.area_ft; }).map(function (v) { return v.label + " (~" + v.distance_ft + " ft)"; });
        info.push({ code: "AREA", message: o.label + " (" + o.area_ft + "-ft radius) would reach: " + (inside.length ? joinAnd(inside) : "no one visible") + "." + (outside.length ? " Out of reach: " + joinAnd(outside) + "." : "") });
      }
      if (o.cost && o.cost.force_points && (ctx.resources || {}).force_points < o.cost.force_points) err("RESOURCE", o.label + " costs " + o.cost.force_points + " Force Points; you have " + ctx.resources.force_points + ".");
      if (o.uses_left === 0) err("RESOURCE", o.label + " has no uses left.");
    });

    // 6. movement and geometry
    var dash = actions.some(function (a) { var o = byId(opts, a.option); return o && o.doubles_movement; });
    var disengage = actions.some(function (a) { var o = byId(opts, a.option); return o && o.suppresses_opportunity_attacks; });
    var mv = decl.movement ? byId(ctx.movement, decl.movement.option) : null;
    if (decl.movement && !mv) err("UNKNOWN_MOVE", "That movement is not available here.");
    if (mv && mv.feet > (b.movement_ft == null ? ctx.speed_ft : b.movement_ft) * (dash ? 2 : 1))
      err("DISTANCE", mv.label + " is about " + mv.feet + " ft; you can move " + (b.movement_ft * (dash ? 2 : 1)) + " ft this turn" + (dash ? "" : " (Dash would double it)") + ".");
    if (mv && mv.blocked_by && mv.blocked_by.length) warn("PATH", mv.label + ": the way passes " + joinAnd(names(ctx, mv.blocked_by)) + "; you may have to go around or stop short.");

    // 8. visible reaction and opportunity-attack risk (no hidden capability is consulted)
    if (mv && ctx.mode === "combat" && !disengage) {
      var leaving = (mv.leaves_reach_of || []).filter(function (id) { var v = byId(ctx.visible, id); return v && v.hostile; });
      if (leaving.length) {
        var prone = leaving.filter(function (id) { var v = byId(ctx.visible, id); return (v.conditions || []).indexOf("prone") >= 0; });
        warn("OPPORTUNITY_ATTACK", "Moving away from " + joinAnd(names(ctx, leaving)) + " may provoke opportunity attacks." +
          (prone.length ? " " + (prone.length === 1 ? "One of them is" : "Some are") + " currently prone, but prone does not automatically prevent an opportunity attack." : "") +
          (byId(opts, "disengage") ? " Disengage would prevent them, but uses your action." : ""));
      }
    }
    // reactions: one per round; Ready reserves it
    var reservesReaction = actions.some(function (a) { var o = byId(opts, a.option); return o && o.uses_reaction_when_triggered; });
    (decl.reactions || []).forEach(function (r) { if (!byId(ctx.reactions, r)) err("UNKNOWN_REACTION", "\"" + r + "\" is not an available reaction."); });
    if (reservesReaction && (decl.reactions || []).length) warn("REACTION_SHARED", "A readied action spends your reaction when it triggers; " + joinAnd((decl.reactions || []).map(function (r) { var x = byId(ctx.reactions, r); return x ? x.label : r; })) + " would then be unavailable until your next turn.");
    if ((decl.unmapped || []).length) info.push({ code: "UNMAPPED", message: "Part of this could not be matched to a listed option. The GM will interpret it and check it against these same rules before any roll." });

    // 10. ordered preview
    if (decl.speech && decl.speech.text) preview.push({ step: "speech", text: "Say: “" + decl.speech.text + "”" + (speechAction ? " (extended, uses your action)" : " (free)") });
    objs.forEach(function (oid, i) { var o = byId(ctx.objects, oid); if (o) preview.push({ step: "object", text: o.label + (i === 0 ? " (free object interaction)" : " (uses your action)") }); });
    var moveFirst = mv && mv.distance_after && actions.some(function (a) { return a.target && mv.distance_after[a.target] != null; });
    if (mv && moveFirst) preview.push({ step: "movement", text: mv.label + (mv.feet ? " (~" + mv.feet + " ft)" : "") });
    actions.forEach(function (a) { var o = byId(opts, a.option); if (o) preview.push({ step: "action", text: o.label + (a.target ? " → " + names(ctx, [a.target])[0] : "") + (a.trigger ? " (trigger: " + a.trigger + ")" : "") }); });
    bonus.forEach(function (a) { var o = byId(opts, a.option); if (o) preview.push({ step: "bonus_action", text: o.label }); });
    if (mv && !moveFirst) preview.push({ step: "movement", text: mv.label + (mv.feet ? " (~" + mv.feet + " ft)" : "") });
    (decl.reactions || []).forEach(function (r) { var x = byId(ctx.reactions, r); if (x) preview.push({ step: "reaction", text: "If " + x.trigger + ": " + x.label }); });

    var used = { action: Math.min(actionCount, 9), bonus_action: bonus.length, movement_ft: mv ? mv.feet : 0, object_interaction: Math.min(objs.length, 1), reaction: reservesReaction ? 1 : 0 };
    var alternatives = errors.some(function (e) { return e.code === "ACTION_CONFLICT"; }) ? alternativesFor(decl, ctx) : [];
    return { contract: VERSION, legal: errors.length === 0, needs_confirmation: errors.length === 0 && warnings.length > 0,
             errors: errors, warnings: warnings, info: info, preview: preview, used: used, alternatives: alternatives };
  }

  function describe(decl, ctx) {
    var parts = [];
    decl.actions.forEach(function (a) { var o = byId(ctx.options, a.option); if (o) parts.push(o.label); });
    var mv = decl.movement && byId(ctx.movement, decl.movement.option);
    if (mv && mv.feet) parts.push(mv.label.charAt(0).toLowerCase() + mv.label.slice(1));
    else parts.push("hold position");
    if (decl.objects.length) parts.unshift(byId(ctx.objects, decl.objects[0]).label.toLowerCase());
    return parts.join(" + ");
  }

  function alternativesFor(decl, ctx) {
    var out = [];
    decl.actions.forEach(function (a) {
      var d = clone(decl); d.actions = [a]; d.source = "composer";
      if (d.objects.length > 1) d.objects = d.objects.slice(0, 1);
      var v = validate(d, ctx);
      if (v.legal) out.push({ label: describe(d, ctx), declaration: d, warnings: v.warnings.map(function (w) { return w.message; }) });
    });
    if (decl.movement && byId(ctx.options, "disengage")) {
      var d2 = clone(decl); d2.actions = [{ option: "disengage", target: null, trigger: null }]; d2.source = "composer";
      if (d2.objects.length > 1) d2.objects = d2.objects.slice(0, 1);
      if (validate(d2, ctx).legal) out.push({ label: describe(d2, ctx), declaration: d2, warnings: [] });
    }
    return out.slice(0, 4);
  }

  function summary(v) {
    if (!v.legal) return v.errors.map(function (e) { return e.message; }).concat(v.warnings.map(function (w) { return w.message; })).join(" ") +
      (v.alternatives.length ? " You may choose " + joinAnd(v.alternatives.map(function (a) { return a.label; }), "or") + ", subject to the active rules." : "");
    return v.warnings.map(function (w) { return w.message; }).join(" ");
  }

  return { VERSION: VERSION, emptyDecl: emptyDecl, parseFreeform: parseFreeform, validate: validate, summary: summary };
});

/* node CLI: node turn_contract.js validate <decl.json|-> <ctx.json>   |   parse "<text>" <ctx.json> */
if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
  var fs = require("fs"), T = module.exports, argv = process.argv.slice(2);
  var ctx = JSON.parse(fs.readFileSync(argv[2], "utf8"));
  if (argv[0] === "parse") {
    var d = T.parseFreeform(argv[1], ctx), v = T.validate(d, ctx);
    process.stdout.write(JSON.stringify({ declaration: d, validation: v, summary: T.summary(v) }, null, 1) + "\n");
  } else if (argv[0] === "validate") {
    var decl = JSON.parse(argv[1] === "-" ? fs.readFileSync(0, "utf8") : fs.readFileSync(argv[1], "utf8"));
    var r = T.validate(decl, ctx);
    process.stdout.write(JSON.stringify({ validation: r, summary: T.summary(r) }, null, 1) + "\n");
    process.exit(r.legal ? 0 : 3);
  } else { process.stderr.write("usage: parse <text> <ctx> | validate <decl|-> <ctx>\n"); process.exit(2); }
}
