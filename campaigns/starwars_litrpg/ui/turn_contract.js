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
 *     unmapped: [ "text the parser could not map" ],
 *     steps: [ { type: "speech"|"action"|"bonus_action"|"move"|"object"|"free", option, target, trigger, text,
 *                condition: { text } | absent, pending: true | absent, authorized: true | absent } ] }
 * `steps` (turn-contract/2, optional) is the player's order; the other fields are derived from it.
 *
 * Optional turn-context fields read by contract 2 (published by the GM from committed events only):
 *   hands: { right: {item, label} | null, left: {...} | null }       hand occupancy, when an event states it
 *   objects[].frees_hand ("left"|"right"), objects[]/options[].needs_hands (n, momentary use),
 *   objects[]/options[].takes_hands (n, the item is then held), .at (visible id where it is used),
 *   .reach_ft (default 5 for `at`), pending_steps: [steps] left from a halted sequence.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.GenesisTurn = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  var VERSION = "turn-contract/2";  // reads turn-contract/1 declarations unchanged (no `steps`)

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

  /* ---------- free-text parsing (deterministic, alias-driven, order-preserving) ----------
   * The GM publishes aliases with every option. The text is cut into clauses in the player's order
   * (sentences, ";", "then", "and then", "after that"); quoted speech keeps its place. Every match
   * becomes a step, so conflicts surface in validation instead of being silently resolved. A clause
   * that matches nothing is kept as a free step (and in `unmapped`), never dropped. A clause with
   * "if", "unless", "depending on"... marks its steps as conditional: the GM stops before them unless
   * what the character already knows settles the condition. The GM processor re-reads the text with
   * judgment, but must run the same validator on its reading. */
  var MOTION = /\b(go|goes|walk|walks|head|heads|move|moves|run|runs|return|returns|back to|cross|crosses|step|steps|climb|climbs|come back)\b/i;
  var COND = /\b(if|unless|only if|depending on|in case|provided that|as long as|whether)\b/i;
  var ITEM = /\b(take|takes|grab|grabs|pick up|picks up|carry|carries|bring|brings|pocket|stow|loot|put (?:it|them) in)\b/i;
  var POWER = /\b(force (?:push|pull|choke|lightning|jump|speed|wave|throw|grip|crush|heal|persuade|stasis|barrier|sense)|mind trick|use the force)\b/i;
  function classify(text) {
    var t = String(text || "");
    return COND.test(t) ? "condition" : POWER.test(t) ? "power" : ITEM.test(t) ? "item" : "other";
  }
  function kindsOf(text) {  // every kind a piece of unmapped text carries (a note can be conditional AND name an item)
    var t = String(text || ""), k = [];
    if (COND.test(t)) k.push("condition"); if (POWER.test(t)) k.push("power"); if (ITEM.test(t)) k.push("item");
    return k.length ? k : ["other"];
  }
  function norm(t) { return " " + lc(t).replace(/[^a-z0-9' ]+/g, " ") + " "; }
  function matchesIn(text, list, kind) {
    var t = norm(text), out = [];
    (list || []).forEach(function (o) {
      var al = (o.aliases || []).concat([o.label || ""]);
      for (var i = 0; i < al.length; i++) {
        var a = lc(al[i]).replace(/[^a-z0-9' ]+/g, " ").trim(), k = a ? t.indexOf(" " + a + " ") : -1;
        if (k >= 0) { out.push({ id: o.id, kind: kind, pos: k, end: k + a.length + 1, len: a.length }); break; }
      }
    });
    return out;
  }
  function findAliases(text, list) {  // kept for callers that only need ids in order
    return matchesIn(text, list, "x").sort(function (x, y) { return x.pos - y.pos; }).map(function (h) { return h.id; });
  }
  function resolveOverlaps(ms, clause) {
    var prefMove = MOTION.test(clause), kept = [];
    ms.slice().sort(function (a, b) { return b.len - a.len || ((a.kind === "move") === prefMove ? -1 : 1); }).forEach(function (m) {
      if (!kept.some(function (k) { return m.pos < k.end && k.pos < m.end; })) kept.push(m);
    });
    return kept.sort(function (a, b) { return a.pos - b.pos; });
  }
  function clauses(text) {  // [{type:"speech"|"text", text, pos}] in order
    var out = [], re = /["“]([^"”]+)["”]/g, last = 0, m;
    function pushText(chunk, base) {
      var sep = /(?:[.;!?]+\s+|[.;!?]+$|,?\s+(?:and\s+)?then\s+|\s+after that,?\s+)/gi, i = 0, x;
      while ((x = sep.exec(chunk))) { out.push({ type: "text", text: chunk.slice(i, x.index), pos: base + i }); i = x.index + x[0].length; }
      out.push({ type: "text", text: chunk.slice(i), pos: base + i });
    }
    while ((m = re.exec(text))) { pushText(text.slice(last, m.index), last); out.push({ type: "speech", text: m[1], pos: m.index }); last = m.index + m[0].length; }
    pushText(text.slice(last), last);
    return out.filter(function (c) { return c.type === "speech" || /[a-z0-9]/i.test(c.text.replace(/^\s*(and|also|but|so)\s*$/i, "")); });
  }

  function parseFreeform(text, ctx) {
    var d = emptyDecl(ctx); d.source = "freeform"; d.freeform = String(text || "");
    var opts = ctx.options || [], steps = [];
    clauses(d.freeform).forEach(function (c) {
      if (c.type === "speech") { steps.push({ type: "speech", text: c.text }); return; }
      var ms = resolveOverlaps([].concat(
        matchesIn(c.text, opts.filter(function (o) { return o.slot === "action"; }), "action"),
        matchesIn(c.text, opts.filter(function (o) { return o.slot === "bonus_action"; }), "bonus_action"),
        matchesIn(c.text, (ctx.movement || []).filter(function (m) { return m.id !== "hold"; }), "move"),
        matchesIn(c.text, ctx.objects, "object"),
        matchesIn(c.text, ctx.reactions, "reaction")), c.text);
      var cond = COND.test(c.text) ? { text: c.text.trim() } : null;
      if (!ms.length) { steps.push({ type: "free", text: c.text.trim(), kind: classify(c.text) }); return; }
      ms.forEach(function (h) {
        if (h.kind === "reaction") { d.reactions.push(h.id); return; }
        var st = { type: h.kind, option: h.id };
        var o = byId(opts, h.id);
        if (h.kind === "action" || h.kind === "bonus_action") {
          st.target = null; st.trigger = null;
          if (o && o.needs_trigger) { var tm = c.text.match(/(?:against|at|when|if)\s+([^,.;]+)/i); st.trigger = tm ? tm[0].trim() : (o.default_trigger || null); }
          if (o && o.needs_target) { var tg = findAliases(c.text, ctx.visible); if (!tg.length) tg = findAliases(d.freeform, ctx.visible); st.target = tg[0] || null; }
        }
        if (cond && !(o && o.needs_trigger)) st.condition = cond;
        steps.push(st);
      });
    });
    // "ready" swallows the attack it readies: "ready a strike" is one action, not two.
    var ready = steps.some(function (s) { var o = s.type === "action" && byId(opts, s.option); return o && o.needs_trigger; });
    if (ready) steps = steps.filter(function (s) { var o = s.type === "action" && byId(opts, s.option); return !(o && o.readiable && !o.needs_trigger); });
    d.steps = steps;
    return normalize(d, ctx);
  }

  /* ---------- steps <-> legacy fields ----------
   * `steps` (turn-contract/2) is the player's ordered sequence. The legacy fields (speech, actions,
   * bonus_actions, movement, objects, unmapped) are always derived from it, so turn-contract/1
   * readers keep working. A declaration without steps gets them from the legacy fields in the
   * contract-1 order (speech, objects, a move toward an action's place, actions, bonus, move). */
  function legacySteps(d, ctx) {
    var st = [], opts = ctx.options || [];
    if (d.speech && d.speech.text) st.push({ type: "speech", text: d.speech.text, option: d.speech.option || null, approach: d.speech.approach, extended: !!d.speech.extended });
    (d.objects || []).forEach(function (oid) { st.push({ type: "object", option: oid }); });
    var mv = d.movement && d.movement.option !== "hold" ? byId(ctx.movement, d.movement.option) : null;
    var moveFirst = mv && (d.actions || []).concat(d.bonus_actions || []).some(function (a) {
      var o = byId(opts, a.option), place = a.target || (o && o.at), da = mv.distance_after || {};
      if (!place || da[place] == null) return false;
      var v = byId(ctx.visible, place);
      return a.target ? true : (v ? da[place] < v.distance_ft : true);
    });
    if (mv && moveFirst) st.push({ type: "move", option: mv.id });
    (d.actions || []).forEach(function (a) { st.push({ type: "action", option: a.option, target: a.target || null, trigger: a.trigger || null }); });
    (d.bonus_actions || []).forEach(function (a) { st.push({ type: "bonus_action", option: a.option, target: a.target || null }); });
    if (mv && !moveFirst) st.push({ type: "move", option: mv.id });
    return st;
  }
  function normalize(decl, ctx) {
    var d = clone(decl);
    d.unmapped = (d.unmapped || []).slice(); d.reactions = (d.reactions || []).slice();
    if (!d.steps || !d.steps.length) { d.steps = legacySteps(d, ctx); return d; }
    var sp = d.steps.filter(function (s) { return s.type === "speech" && s.text; });
    if (sp.length) d.speech = { option: sp.length === 1 ? (sp[0].option || null) : null, text: sp.map(function (s) { return s.text; }).join(" "),
                                approach: sp.length === 1 ? (sp[0].approach || "freeform") : "freeform", extended: sp.some(function (s) { return !!s.extended; }) };
    else d.speech = null;
    d.actions = d.steps.filter(function (s) { return s.type === "action"; }).map(function (s) { return { option: s.option, target: s.target || null, trigger: s.trigger || null }; });
    d.bonus_actions = d.steps.filter(function (s) { return s.type === "bonus_action"; }).map(function (s) { return { option: s.option, target: s.target || null }; });
    var mvs = d.steps.filter(function (s) { return s.type === "move"; });
    d.movement = mvs.length ? { option: mvs[0].option } : (d.movement && d.movement.option === "hold" ? d.movement : null);
    d.objects = d.steps.filter(function (s) { return s.type === "object"; }).map(function (s) { return s.option; });
    d.steps.filter(function (s) { return s.type === "free" && s.text; }).forEach(function (s) { if (d.unmapped.indexOf(s.text) < 0) d.unmapped.push(s.text); });
    return d;
  }

  /* ---------- halting a sequence (GM side) ----------
   * The GM resolves steps in order and stops at the first one that needs the player: a material
   * choice, a condition not settled by committed events, an unforeseen event, or initiative.
   * Steps before the halt that do not depend on it may be resolved; the rest come back as
   * pending steps. Pending steps never run until the player submits them again explicitly. */
  function haltAt(decl, ctx, index, reason) {
    var d = normalize(decl, ctx), i = Math.max(0, Math.min(index, d.steps.length));
    return { resolved: d.steps.slice(0, i), reason: String(reason || ""),
             pending: d.steps.slice(i).map(function (s) { var x = clone(s); x.pending = true; delete x.authorized; return x; }) };
  }

  /* ---------- preflight validation ---------- */
  function validate(declIn, ctx) {
    var errors = [], warnings = [], info = [], preview = [];
    var b = ctx.budget || {}, opts = ctx.options || [];
    var combat = ctx.mode === "combat";  // outside combat there is no action economy: steps happen in sequence
    var decl = normalize(declIn, ctx), steps = decl.steps;
    function err(code, msg, extra) { var e = { code: code, message: msg }; for (var k in extra || {}) e[k] = extra[k]; errors.push(e); }
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
    steps.filter(function (s) { return s.type === "move"; }).forEach(function (s) { if (!byId(ctx.movement, s.option)) err("UNKNOWN_MOVE", "That movement is not available here."); });

    // pending steps (left over from a halted sequence) run only when the player authorizes them again
    var unauth = steps.filter(function (s) { return s.pending && !s.authorized; });
    if (unauth.length) err("PENDING_UNAUTHORIZED", unauth.length + " step" + (unauth.length > 1 ? "s were" : " was") + " left over from an interrupted sequence. Choose \"Continue these steps\" (or rewrite them) to authorize them again.");

    // speech: brief speech is free; extended or check-based social actions use the action
    var speechAction = decl.speech && decl.speech.extended && combat;
    var actionCount = actions.length + (speechAction ? 1 : 0);
    var actLabels = actions.map(function (a) { var o = byId(opts, a.option); return o ? o.label : a.option; });
    if (speechAction) actLabels.push("an extended social action");

    // 3. action economy (combat only)
    var extraObjects = Math.max(0, objs.length - (b.object_interaction == null ? 1 : b.object_interaction));
    if (extraObjects && combat) { actionCount += extraObjects; actLabels.push("a second object interaction"); }
    var stepCount = steps.filter(function (s) { return s.type !== "speech"; }).length;
    if (!combat && stepCount > 1) info.push({ code: "SEQUENCE", message: "Outside combat these happen one after another, in this order; the GM resolves the time they take and stops if something needs your decision." });
    if (combat && actionCount > (b.action == null ? 1 : b.action))
      err("ACTION_CONFLICT", joinAnd(actLabels) + (actionCount === 2 ? " both require" : " all require") + " your primary action, so you cannot use " + (actionCount === 2 ? "both" : "them all") +
        " this turn unless another feature grants you an additional action.");
    if (combat && bonus.length > (b.bonus_action == null ? 1 : b.bonus_action)) err("BONUS_CONFLICT", "You have one bonus action this turn.");
    bonus.forEach(function (a) { var o = byId(opts, a.option); if (o && o.slot !== "bonus_action") err("NOT_BONUS", o.label + " is not a bonus action."); });
    actions.forEach(function (a) { var o = byId(opts, a.option); if (o && o.slot !== "action") err("NOT_ACTION", o.label + " is not a primary action."); });

    // 4-5. requirements, range, target, area
    actions.concat(bonus).forEach(function (a) {
      var o = byId(opts, a.option); if (!o) return;
      (o.requires || []).forEach(function (r) { if (flags.indexOf(r) < 0) err("REQUIRES", o.label + " needs " + (ctx.flag_labels && ctx.flag_labels[r] || r) + " first."); });
      if (o.needs_target) {
        var t = byId(ctx.visible, a.target);
        // movement may be split around the action, so the closest point of the declared moves counts
        var dist = t ? t.distance_ft : null;
        if (t) steps.forEach(function (s) { var m = s.type === "move" && byId(ctx.movement, s.option); if (m && m.distance_after && m.distance_after[t.id] != null) dist = Math.min(dist, m.distance_after[t.id]); });
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
    var moves = steps.filter(function (s) { return s.type === "move"; }).map(function (s) { return byId(ctx.movement, s.option); }).filter(Boolean);
    var mv = decl.movement ? byId(ctx.movement, decl.movement.option) : null;
    if (decl.movement && !mv && !moves.length) err("UNKNOWN_MOVE", "That movement is not available here.");
    var feet = moves.reduce(function (t, m) { return t + (m.feet || 0); }, 0);
    if (combat && feet > (b.movement_ft == null ? ctx.speed_ft : b.movement_ft) * (dash ? 2 : 1))
      err("DISTANCE", (moves.length === 1 ? moves[0].label + " is about " : "Those moves add up to about ") + feet + " ft; you can move " + (b.movement_ft * (dash ? 2 : 1)) + " ft this turn" + (dash ? "" : " (Dash would double it)") + ".");
    if (!combat && moves.length > 1) info.push({ code: "MOVE_SEQUENCE", message: "Distances after the first move are measured by the GM from where that move ends." });
    moves.forEach(function (m) { if (m.blocked_by && m.blocked_by.length) warn("PATH", m.label + ": the way passes " + joinAnd(names(ctx, m.blocked_by)) + "; you may have to go around or stop short."); });

    // 6b. physical feasibility along the sequence (all modes): hands and position, when the GM has
    // published them. A missing step is told apart from something that cannot be done here.
    var hands = ctx.hands && typeof ctx.hands === "object" ? clone(ctx.hands) : null;
    var here = {}; (ctx.visible || []).forEach(function (v) { here[v.id] = v.distance_ft; });
    function heldText() { return ["right", "left"].map(function (h) { return hands[h] ? "your " + h + " hand holds " + (hands[h].label || hands[h].item || hands[h]) : "your " + h + " hand is free"; }).join(" and "); }
    function freeCount() { return ["right", "left"].filter(function (h) { return !hands[h]; }).length; }
    function freers(from) {
      return (ctx.objects || []).filter(function (o) { return o.frees_hand && hands[o.frees_hand]; })
        .filter(function (o) { return !steps.slice(0, from).some(function (s) { return s.type === "object" && s.option === o.id; }); }).map(function (o) { return o.id; });
    }
    steps.forEach(function (s, i) {
      var o = s.type === "object" ? byId(ctx.objects, s.option) : (s.type === "action" || s.type === "bonus_action") ? byId(opts, s.option) : null;
      if (s.type === "move") { var m = byId(ctx.movement, s.option); if (m && m.distance_after) for (var k in here) here[k] = m.distance_after[k] != null ? m.distance_after[k] : null; return; }
      if (!o) return;
      if (o.at && here[o.at] != null && here[o.at] > (o.reach_ft != null ? o.reach_ft : 5)) {
        var reach = (ctx.movement || []).filter(function (m) { return m.distance_after && m.distance_after[o.at] != null && m.distance_after[o.at] <= (o.reach_ft != null ? o.reach_ft : 5); }).map(function (m) { return m.id; });
        err("POSITION", o.label + ": " + names(ctx, [o.at])[0] + " is about " + here[o.at] + " ft away at that point. " + (reach.length ? "Add a move there first." : "There is no listed way to reach it from here."),
            { step: i, resolution: reach.length ? "add_step" : "not_possible_here", suggest: reach });
      }
      if (!hands) return;
      var need = (o.needs_hands || 0) + (o.takes_hands || 0);
      if (need > freeCount()) {
        var f = freers(i);
        err("HANDS", o.label + " needs " + need + " free hand" + (need > 1 ? "s" : "") + "; at that point " + heldText() + "." +
            (f.length && f.length + freeCount() >= need ? " Free one first (for example: " + joinAnd(f.map(function (id) { return byId(ctx.objects, id).label.toLowerCase(); }), "or") + "), or say how Aero carries it." : " Nothing listed frees enough hands; say how Aero carries it or leave something behind."),
            { step: i, resolution: f.length && f.length + freeCount() >= need ? "add_step" : "needs_choice", suggest: f });
      } else if (o.takes_hands) {
        var n = o.takes_hands; ["right", "left"].forEach(function (h) { if (n > 0 && !hands[h]) { hands[h] = { item: o.item || o.id, label: o.item_label || (o.item ? "the " + String(o.item).replace(/_/g, " ") : o.label) }; n--; } });
      }
      if (o.frees_hand && hands[o.frees_hand]) hands[o.frees_hand] = null;
    });

    // 8. visible reaction and opportunity-attack risk (no hidden capability is consulted)
    if (combat && !disengage) {
      var leaving = uniq([].concat.apply([], moves.map(function (m) { return m.leaves_reach_of || []; }))).filter(function (id) { var v = byId(ctx.visible, id); return v && v.hostile; });
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

    // conditions and unlisted things: the GM decides them, never the validator; say so plainly
    var halts = [];
    steps.forEach(function (s, i) { if (s.condition && s.condition.text) halts.push(i); });
    if (halts.length) info.push({ code: "CONDITIONAL", message: "Step " + (halts[0] + 1) + " depends on “" + steps[halts[0]].condition.text + "”. The GM resolves the steps before it and stops there unless what Aero already knows settles it; then you decide." });
    var kinds = {};
    (decl.unmapped || []).forEach(function (u) { kindsOf(u).forEach(function (k) { kinds[k] = (kinds[k] || []).concat([u]); }); });
    if (kinds.condition) info.push({ code: "CONDITIONAL", message: "Part of this depends on something not yet known (“" + kinds.condition[0].trim().slice(0, 120) + "”). The GM will not decide that for Aero: it stops and asks." });
    if (kinds.item) info.push({ code: "UNLISTED_ITEM", message: "“" + kinds.item[0].trim().slice(0, 120) + "” names an item or use that is not listed here. The GM checks that it is established, that Aero has a hand free and how it is carried, before anything is rolled." });
    if (kinds.power) info.push({ code: "UNLISTED_POWER", message: "“" + kinds.power[0].trim().slice(0, 120) + "” names a power that is not listed here. The GM checks Aero's sheet; a power he does not have is refused, not substituted." });
    if (kinds.other) info.push({ code: "UNMAPPED", message: "Part of this could not be matched to a listed option. The GM will interpret it and check it against these same rules before any roll." });

    // 10. ordered preview: the player's order
    var objSeen = 0;
    steps.forEach(function (s) {
      var pre = s.condition && s.condition.text ? "Only if " + s.condition.text.replace(/^\s*(only\s+)?if\s+/i, "") + ": " : "";
      if (s.type === "speech" && s.text) preview.push({ step: "speech", text: pre + "Say: “" + s.text + "”" + (speechAction ? " (extended, uses your action)" : " (free)") });
      else if (s.type === "object") { var o = byId(ctx.objects, s.option); if (o) { preview.push({ step: "object", text: pre + o.label + (combat ? (objSeen === 0 ? " (free object interaction)" : " (uses your action)") : "") }); objSeen++; } }
      else if (s.type === "move") { var m = byId(ctx.movement, s.option); if (m) preview.push({ step: "movement", text: pre + m.label + (m.feet && !/\d\s*(ft|m)\b/.test(m.label) ? " (~" + m.feet + " ft)" : "") }); }
      else if (s.type === "action") { var a = byId(opts, s.option); if (a) preview.push({ step: "action", text: pre + a.label + (s.target ? " → " + names(ctx, [s.target])[0] : "") + (s.trigger ? " (trigger: " + s.trigger + ")" : "") }); }
      else if (s.type === "bonus_action") { var x = byId(opts, s.option); if (x) preview.push({ step: "bonus_action", text: pre + x.label }); }
      else if (s.type === "free" && s.text) preview.push({ step: "free", text: "Also: " + s.text });
    });
    if (mv && mv.id === "hold" && !moves.length && steps.length) preview.push({ step: "movement", text: mv.label });
    (decl.reactions || []).forEach(function (r) { var x = byId(ctx.reactions, r); if (x) preview.push({ step: "reaction", text: "If " + x.trigger + ": " + x.label }); });

    var used = { action: Math.min(actionCount, 9), bonus_action: bonus.length, movement_ft: feet, object_interaction: Math.min(objs.length, 1), reaction: reservesReaction ? 1 : 0 };
    var alternatives = errors.some(function (e) { return e.code === "ACTION_CONFLICT"; }) ? alternativesFor(decl, ctx) : [];
    return { contract: VERSION, legal: errors.length === 0, needs_confirmation: errors.length === 0 && warnings.length > 0,
             errors: errors, warnings: warnings, info: info, preview: preview, used: used, alternatives: alternatives, steps: steps, halts: halts };
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
    decl = clone(decl); delete decl.steps;  // alternatives are composer (legacy-slot) declarations
    decl.actions.forEach(function (a) {
      var d = clone(decl); d.actions = [a]; d.source = "composer";
      if (d.objects.length > 1) d.objects = d.objects.slice(0, 1);
      var v = validate(d, ctx);
      if (v.legal) out.push({ label: describe(d, ctx), declaration: d, warnings: v.warnings.map(function (w) { return w.message; }) });
    });
    if (decl.movement && byId(ctx.options, "disengage")) {
      var d2 = clone(decl); delete d2.steps; d2.actions = [{ option: "disengage", target: null, trigger: null }]; d2.source = "composer";
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

  return { VERSION: VERSION, emptyDecl: emptyDecl, parseFreeform: parseFreeform, normalize: normalize, validate: validate, summary: summary, haltAt: haltAt, classify: classify };
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
  } else if (argv[0] === "halt") {  // node turn_contract.js halt <decl|-> <ctx> <step index> "<reason>"
    var dh = JSON.parse(argv[1] === "-" ? fs.readFileSync(0, "utf8") : fs.readFileSync(argv[1], "utf8"));
    process.stdout.write(JSON.stringify(T.haltAt(dh, ctx, +argv[3], argv[4] || ""), null, 1) + "\n");
  } else { process.stderr.write("usage: parse <text> <ctx> | validate <decl|-> <ctx> | halt <decl|-> <ctx> <index> <reason>\n"); process.exit(2); }
}
