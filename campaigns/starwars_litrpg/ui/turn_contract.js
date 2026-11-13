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
 *   contract 3: objects[].frees_item (frees whichever hand holds that item), options/objects/moves .grants/.removes
 *   (planned flags, applied in step order), .unless [flags that make it pointless], .at_free (no place needed), .risk (visible risk text), movement[].ends_at, position_label,
 *   plan_result {stop_kind, reason, completed, pending, invalidated}, pending_steps[].status.
 *   adjudication repair (ruling 2026-11-13, creator/ACTION_ECONOMY_RULING.md), all optional and GM-published:
 *   objects[].cost "none": no object interaction is spent (letting go of or dropping something, taking a hand
 *   off something, shifting a thing already held, receiving what another character puts into a free hand).
 *   objects[].by (an actor id other than the acting character): that character performs it, at no cost to the
 *   acting character; whether they do it is theirs to decide (info NPC_COOPERATION). Hand effects written on
 *   such an object (takes_hands, needs_hands) still describe the acting character's hands (the receiver).
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.GenesisTurn = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  var VERSION = "turn-contract/3";  // reads turn-contract/1 (no `steps`) and /2 (no ids, seq or branches) unchanged

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
  var ITEM = /\b(take|takes|grab|grabs|pick up|picks up|carry|carries|bring|brings|pocket|stow|loot|put (?:it|them) in|throw|throws|use|uses|using|with my|tie|ties|lash|lashes|weld|welds)\b/i;
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
      if (!ms.length) {
        var fs = { type: "free", text: c.text.trim(), kind: classify(c.text) };
        // free text naming Aero's own gear: link it so its whereabouts are checked; the GM still reads the method
        var gear = findAliases(c.text, ctx.equipment || []);
        if (gear.length) { fs.uses = gear; fs.parsed = true; fs.kind = "custom"; }
        if (cond) fs.condition = cond;
        steps.push(fs); return;
      }
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
  /* contract 3: every step has a stable `id` and a `seq` (the visual sequence it belongs to);
     a `branch` step holds cases [{when, steps, after: "continue"|"stop"}] and `otherwise` ("stop"|"continue").
     Ids are assigned once when missing (k0, k1, … and k3c0_0 inside a case) and never renumbered here. */
  function flat(steps) { var o = []; (steps || []).forEach(function (s) { o.push(s); if (s.type === "branch") (s.cases || []).forEach(function (c) { o = o.concat(flat(c.steps || [])); }); }); return o; }
  function assignIds(steps, prefix, used, seq) {
    var cur = seq || 0;
    steps.forEach(function (s, i) {
      if (!s.id || used[s.id]) { var k = prefix + i; while (used[k]) k += "_"; s.id = k; }
      used[s.id] = 1;
      if (s.seq == null) s.seq = cur; else cur = s.seq;
      if (s.type === "branch") { s.cases = s.cases || []; s.otherwise = s.otherwise === "continue" ? "continue" : "stop";
        s.cases.forEach(function (c, k) { c.steps = c.steps || []; c.when = String(c.when || ""); assignIds(c.steps, s.id + "c" + k + "_", used, s.seq); }); }
    });
  }
  function speechText(s, ctx) { if (s.text) return s.text; var dl = s.option && byId(ctx.dialogue, s.option); return dl ? dl.text : ""; }
  function normalize(decl, ctx) {
    var d = clone(decl);
    d.unmapped = (d.unmapped || []).slice(); d.reactions = (d.reactions || []).slice();
    if (!d.steps || !d.steps.length) { d.steps = legacySteps(d, ctx); assignIds(d.steps, "k", {}); return d; }
    assignIds(d.steps, "k", {});
    flat(d.steps).forEach(function (s) { if (s.type === "speech" && !s.text) { s.text = speechText(s, ctx); var dl = s.option && byId(ctx.dialogue, s.option); if (dl) { s.approach = s.approach || dl.approach; s.extended = s.extended || !!dl.extended; } } });
    var all = flat(d.steps).filter(function (s) { return s.type !== "branch"; });
    var sp = all.filter(function (s) { return s.type === "speech" && s.text; });
    if (sp.length) d.speech = { option: sp.length === 1 ? (sp[0].option || null) : null, text: sp.map(function (s) { return s.text; }).join(" "),
                                approach: sp.length === 1 ? (sp[0].approach || "freeform") : "freeform", extended: sp.some(function (s) { return !!s.extended; }) };
    else d.speech = null;
    d.actions = all.filter(function (s) { return s.type === "action"; }).map(function (s) { return { option: s.option, target: s.target || null, trigger: s.trigger || null }; });
    d.bonus_actions = all.filter(function (s) { return s.type === "bonus_action"; }).map(function (s) { return { option: s.option, target: s.target || null }; });
    var mvs = all.filter(function (s) { return s.type === "move"; });
    d.movement = mvs.length ? { option: mvs[0].option } : (d.movement && d.movement.option === "hold" ? d.movement : null);
    d.objects = all.filter(function (s) { return s.type === "object"; }).map(function (s) { return s.option; });
    all.filter(function (s) { return s.type === "free" && s.text; }).forEach(function (s) { if (d.unmapped.indexOf(s.text) < 0) d.unmapped.push(s.text); });
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

  /* ---------- preflight validation ----------
   * validateLinear checks ONE ordered path of steps. validate() expands branch steps into paths
   * (one per case, plus "otherwise"), validates each path with the same rules and merges the
   * verdicts: a step that fails on every path that reaches it is an error; one that fails only on
   * some paths is an advisory BRANCH_DEPENDENT warning (the GM stops there in that case).
   * State is tracked in step order: hands, position, flags (grants/removes of objects, moves and
   * actions; an action's grants are its INTENDED result, so later steps that depend on it are only
   * planned, never promised). Nothing here reads hidden state or predicts a roll. */
  var CARRIED0 = ["held", "holstered", "worn", "stored", "attached"];
  var STOP_ERRORS = ["CAPACITY", "TIME", "UNKNOWN_OPTION", "UNKNOWN_OBJECT", "UNKNOWN_MOVE", "RESOURCE", "ACTION_CONFLICT", "BONUS_CONFLICT", "DISTANCE", "NOT_BONUS", "NOT_ACTION", "INCAPACITATED", "ACTOR", "NOT_CONTINUABLE", "SUSPENDED", "PENDING_STALE"];
  function shortLabel(t) { return String(t || "").split(/\s*[:(;,]\s*|\s+—\s+/)[0].trim(); }
  function placeOf(m, ctx) {
    if (m.ends_at) return m.ends_at;
    var da = m.distance_after || {}, hit = null;
    Object.keys(da).forEach(function (k) { if (!hit && da[k] === 0) { var v = byId(ctx.visible, k); if (v) hit = v.short || shortLabel(v.label); } });
    return hit ? "at " + hit.charAt(0).toLowerCase() + hit.slice(1) : null;
  }

  // An object step spends the acting character's object interaction unless the GM published it as costless
  // (release / contact / held-item repositioning / receiving) or as another character's act.
  function objCostly(ctx, id) { var o = byId((ctx && ctx.objects) || [], id); return !(o && (o.cost === "none" || (o.by && o.by !== ctx.actor))); }
  function objBudget(ctx) { var b = (ctx && ctx.budget) || {}; return b.object_interaction == null ? 1 : b.object_interaction; }

  function previewSteps(steps, ctx, combat, speechAction, state) {
    var out = [], opts = ctx.options || [];
    state = state || { objSeen: 0 };
    steps.forEach(function (s) {
      var pre = s.condition && s.condition.text ? "Only if " + s.condition.text.replace(/^\s*(only\s+)?if\s+/i, "") + ": " : "";
      if (s.type === "speech" && s.text) out.push({ step: "speech", id: s.id, text: pre + "Say: “" + s.text + "”" + (speechAction ? " (extended, uses your action)" : " (free)") });
      else if (s.type === "object") { var o = byId(ctx.objects, s.option); if (o) { var costly = objCostly(ctx, s.option), other = o.by && o.by !== ctx.actor; out.push({ step: "object", id: s.id, text: pre + o.label + (combat ? (other ? " (theirs to do, no cost to you)" : !costly ? " (no action)" : state.objSeen < objBudget(ctx) ? " (free object interaction)" : " (uses your action)") : "") }); if (costly) state.objSeen++; } }
      else if (s.type === "move") { var m = byId(ctx.movement, s.option); if (m) out.push({ step: "movement", id: s.id, text: pre + m.label + (m.feet && !/\d\s*(ft|m)\b/.test(m.label) ? " (~" + m.feet + " ft)" : "") }); }
      else if (s.type === "action") { var a = byId(opts, s.option); if (a) out.push({ step: "action", id: s.id, text: pre + a.label + (s.target ? " → " + names(ctx, [s.target])[0] : "") + (s.trigger ? " (trigger: " + s.trigger + ")" : "") }); }
      else if (s.type === "bonus_action") { var x = byId(opts, s.option); if (x) out.push({ step: "bonus_action", id: s.id, text: pre + x.label }); }
      else if (s.type === "free" && s.text) out.push({ step: "free", id: s.id, text: pre + (s.kind === "custom" || s.custom ? "Try: " : "Also: ") + s.text });
      else if (s.type === "branch") {
        (s.cases || []).forEach(function (c, k) {
          var inner = previewSteps(c.steps || [], ctx, combat, speechAction, state).map(function (p) { return p.text; });
          out.push({ step: "branch", id: s.id, text: (k ? "Else if " : "If ") + (c.when || "…") + ": " + (inner.length ? inner.join("; ") : "do none of this") + (c.after === "stop" ? ", then stop and ask me" : "") });
        });
        out.push({ step: "branch", id: s.id, text: s.otherwise === "continue" ? "Otherwise: skip this and continue" : "Otherwise: stop and ask me" });
      }
    });
    return out;
  }

  function validateLinear(decl, ctx) {
    var errors = [], warnings = [], info = [], trace = [];
    var b = ctx.budget || {}, opts = ctx.options || [];
    var combat = ctx.mode === "combat";  // outside combat there is no action economy: steps happen in sequence
    var steps = decl.steps;
    function err(code, msg, extra) { var e = { code: code, message: msg }; for (var k in extra || {}) e[k] = extra[k]; errors.push(e); }
    function warn(code, msg, extra) { var w = { code: code, message: msg }; for (var k in extra || {}) w[k] = extra[k]; warnings.push(w); }

    // 1-2. acting character
    if (decl.actor !== ctx.actor) err("ACTOR", "Only " + (ctx.actor_name || ctx.actor) + " can act this turn. Viewing another party member never grants control of them.");
    if (ctx.actor_conditions && ctx.actor_conditions.some(function (c) { return /unconscious|dead|incapacitated/.test(c); }))
      err("INCAPACITATED", (ctx.actor_name || ctx.actor) + " cannot act (" + ctx.actor_conditions.join(", ") + ").");

    var actions = decl.actions || [], bonus = decl.bonus_actions || [], objs = decl.objects || [];

    // 4. capabilities exist
    steps.forEach(function (s, i) {
      var ex = { step: i, step_id: s.id };
      if ((s.type === "action" || s.type === "bonus_action") && !byId(opts, s.option)) err("UNKNOWN_OPTION", "\"" + s.option + "\" is not something " + (ctx.actor_name || ctx.actor) + " can do right now.", ex);
      if (s.type === "object" && !byId(ctx.objects, s.option)) err("UNKNOWN_OBJECT", "\"" + s.option + "\" is not an available object interaction.", ex);
      if (s.type === "move" && !byId(ctx.movement, s.option)) err("UNKNOWN_MOVE", "That movement is not available here.", ex);
      if (s.pending && s.status && CONTINUABLE.indexOf(s.status) < 0) err("NOT_CONTINUABLE", "This step was " + s.status + " by what happened" + (s.reason ? " (" + s.reason + ")" : "") + ". It cannot be continued; choose again from what Aero sees now.", ex);
      if (s.pending && s.status === "suspended" && combat) err("SUSPENDED", "This step is set aside until the fight is over.", ex);
      if (s.pending && s.authorized && ctx.context_id && s.authorized_ctx && s.authorized_ctx !== ctx.context_id)
        err("PENDING_STALE", "This step was authorized against an earlier moment. The scene has moved on: choose \"Continue these steps\" again so it is checked against what Aero sees now.", ex);
    });

    // pending steps (left over from a halted sequence) run only when the player authorizes them again
    var unauth = steps.filter(function (s) { return s.pending && !s.authorized && (!s.status || CONTINUABLE.indexOf(s.status) >= 0); });
    if (unauth.length) err("PENDING_UNAUTHORIZED", unauth.length + " step" + (unauth.length > 1 ? "s were" : " was") + " left over from an interrupted sequence. Choose \"Continue these steps\" (or rewrite them) to authorize them again.");

    // speech: brief speech is free; extended or check-based social actions use the action
    var speechAction = decl.speech && decl.speech.extended && combat;
    var actionCount = actions.length + (speechAction ? 1 : 0);
    var actLabels = actions.map(function (a) { var o = byId(opts, a.option); return o ? o.label : a.option; });
    if (speechAction) actLabels.push("an extended social action");
    var customs = steps.filter(function (s) { return s.type === "free" && (s.kind === "custom" || s.method || (s.uses || []).length); });
    if (combat && customs.length) { actionCount += customs.length; customs.forEach(function () { actLabels.push("a custom action"); }); }

    // 3. action economy (combat only)
    var costlyObjs = objs.filter(function (id) { return objCostly(ctx, id); });
    var extraObjects = Math.max(0, costlyObjs.length - (b.object_interaction == null ? 1 : b.object_interaction));
    var askedOf = {}; objs.forEach(function (id) { var o = byId(ctx.objects, id); if (o && o.by && o.by !== ctx.actor) askedOf[o.by] = 1; });
    Object.keys(askedOf).forEach(function (who) { info.push({ code: "NPC_COOPERATION", message: "Part of this is " + ((byId(ctx.visible || [], who) || {}).short || who) + "'s to do, not Aero's. It costs Aero nothing; whether they do it is theirs to decide, and the GM resolves it from what they know and want." }); });
    if (extraObjects && combat) { actionCount += extraObjects; actLabels.push("a second object interaction"); }
    var stepCount = steps.filter(function (s) { return s.type !== "speech"; }).length;
    if (!combat && stepCount > 1) info.push({ code: "SEQUENCE", message: "Outside combat these happen one after another, in this order; the GM resolves the time they take and stops if something needs your decision." });
    if (combat && actionCount > (b.action == null ? 1 : b.action))
      err("ACTION_CONFLICT", joinAnd(actLabels) + (actionCount === 2 ? " both require" : " all require") + " your primary action, so you cannot use " + (actionCount === 2 ? "both" : "them all") +
        " this turn unless another feature grants you an additional action.");
    if (combat && bonus.length > (b.bonus_action == null ? 1 : b.bonus_action)) err("BONUS_CONFLICT", "You have one bonus action this turn.");
    bonus.forEach(function (a) { var o = byId(opts, a.option); if (o && o.slot !== "bonus_action") err("NOT_BONUS", o.label + " is not a bonus action."); });
    actions.forEach(function (a) { var o = byId(opts, a.option); if (o && o.slot !== "action") err("NOT_ACTION", o.label + " is not a primary action."); });

    // 6. movement totals
    var dash = actions.some(function (a) { var o = byId(opts, a.option); return o && o.doubles_movement; });
    var disengage = actions.some(function (a) { var o = byId(opts, a.option); return o && o.suppresses_opportunity_attacks; });
    var moves = steps.filter(function (s) { return s.type === "move"; }).map(function (s) { return byId(ctx.movement, s.option); }).filter(Boolean);
    var mv = decl.movement ? byId(ctx.movement, decl.movement.option) : null;
    if (decl.movement && !mv && !moves.length) err("UNKNOWN_MOVE", "That movement is not available here.");
    var feet = moves.reduce(function (t, m) { return t + (m.feet || 0); }, 0);
    // worn or carried loads with a stated speed effect (e.g. a harness of gas bottles) slow Aero; only what the record states
    var slow = (ctx.equipment || []).filter(function (e) { return CARRIED0.indexOf(e.state) >= 0 && e.effects && e.effects.speed_ft; });
    var speedMod = slow.reduce(function (t, e) { return t + e.effects.speed_ft; }, 0);
    var baseMove = (b.movement_ft == null ? ctx.speed_ft : b.movement_ft) + speedMod;
    if (combat && feet > baseMove * (dash ? 2 : 1))
      err("DISTANCE", (moves.length === 1 ? moves[0].label + " is about " : "Those moves add up to about ") + feet + " ft; you can move " + (baseMove * (dash ? 2 : 1)) + " ft this turn" + (speedMod ? " (" + slow.map(function (e) { return e.label; }).join(", ") + ": " + speedMod + " ft)" : "") + (dash ? "" : " (Dash would double it)") + ".");
    if (!combat && slow.length && moves.length) info.push({ code: "SLOWED", message: joinAnd(slow.map(function (e) { return e.label; })) + " slows Aero (" + speedMod + " ft of speed)" + (slow.some(function (e) { return e.effects.noisy; }) ? " and is noisy" : "") + ". The GM accounts for the time and the noise." });
    if (!combat && moves.length > 1) info.push({ code: "MOVE_SEQUENCE", message: "Distances after the first move are measured by the GM from where that move ends." });
    steps.forEach(function (s, i) { var m = s.type === "move" && byId(ctx.movement, s.option); if (m && m.blocked_by && m.blocked_by.length) warn("PATH", m.label + ": the way passes " + joinAnd(names(ctx, m.blocked_by)) + "; you may have to go around or stop short.", { step: i, step_id: s.id }); });

    // 4-8 along the sequence: requirements, target/range, resources, position, hands, flags.
    // A missing step is told apart from something that cannot be done here.
    var flags = (ctx.state_flags || []).slice();
    var hands = ctx.hands && typeof ctx.hands === "object" ? clone(ctx.hands) : null;
    var here = {}; (ctx.visible || []).forEach(function (v) { here[v.id] = v.distance_ft; });
    var pos = ctx.position_label || null;
    // equipment (contract 3): where each established item is, step by step. Only items in ctx.equipment exist;
    // nothing is ever granted. Held / holstered / worn / stored / attached / transported / placed / dropped.
    var eq = {}; (ctx.equipment || []).forEach(function (e) { eq[e.id] = clone(e); });
    var CARRIED = ["held", "holstered", "worn", "stored", "attached"];
    function eqName(id) { var e = eq[id]; return e ? (e.label || id.replace(/_/g, " ")) : id.replace(/_/g, " "); }
    function flagName(f) { return ctx.flag_labels && ctx.flag_labels[f] || f.replace(/_/g, " "); }
    function eqSnap() { var o = {}; Object.keys(eq).forEach(function (k) { o[k] = eq[k].state + (eq[k].planned ? "*" : ""); }); return o; }
    function heldText() { return ["right", "left"].map(function (h) { return hands[h] ? "your " + h + " hand holds " + (hands[h].label || hands[h].item || hands[h]) : "your " + h + " hand is free"; }).join(" and "); }
    function freeCount() { return ["right", "left"].filter(function (h) { return !hands[h]; }).length; }
    function freers(from) {
      return (ctx.objects || []).filter(function (o) { return ((o.frees_hand && hands[o.frees_hand]) || (o.frees_item && holding(o.frees_item))) && !(o.unless_active && flags.indexOf(o.unless_active) >= 0) && !(o.gear && o.to_state === "placed" && (ctx.objects || []).some(function (x) { return x.id === "eq_stow:" + o.frees_item; })); })
        .filter(function (o) { return !steps.slice(0, from).some(function (s) { return s.type === "object" && s.option === o.id; }); }).map(function (o) { return o.id; });
    }
    function holding(item) { return ['right', 'left'].filter(function (h) { return hands[h] && hands[h].item === item; })[0] || null; }
    function providers(flag) {
      var out = [];
      (ctx.objects || []).forEach(function (o) { if ((o.grants || []).indexOf(flag) >= 0) out.push({ type: "object", option: o.id }); });
      opts.forEach(function (o) { if ((o.grants || []).indexOf(flag) >= 0) out.push({ type: o.slot, option: o.id }); });
      (ctx.movement || []).forEach(function (o) { if ((o.grants || []).indexOf(flag) >= 0) out.push({ type: "move", option: o.id }); });
      return out;
    }
    function applyFlags(o) {
      (o.grants || []).forEach(function (f) { if (flags.indexOf(f) < 0) flags.push(f); });
      (o.removes || []).forEach(function (f) { flags = flags.filter(function (x) { return x !== f; }); });
    }
    function snap(s) {
      var load = null;
      if (ctx.carry && ctx.carry.capacity != null) {
        load = Object.keys(eq).reduce(function (t, k) { var e = eq[k]; return t + (CARRIED.indexOf(e.state) >= 0 && e.bulk != null ? e.bulk * (e.quantity || 1) : 0); }, 0);
        if (load > ctx.carry.capacity && !s.__enc) warn("ENCUMBERED", "At that point Aero would carry about " + load + " of " + ctx.carry.capacity + " " + (ctx.carry.unit || "bulk") + ". Moving that loaded can be slow or unsafe; the GM adjudicates.", { step: steps.indexOf(s), step_id: s.id, advisory: true });
      }
      trace.push({ step_id: s.id, hands: hands ? clone(hands) : null, position: pos, flags: flags.slice(), equipment: (ctx.equipment ? eqSnap() : null), load: load });
    }
    function takeHand(item, label, n) { ["right", "left"].forEach(function (h) { if (n > 0 && !hands[h]) { hands[h] = { item: item, label: label }; n--; } }); }
    /* Improvised / custom steps with a declared method, tools (uses), targets, equipment changes or a result (creates).
       The builder constrains what is impossible (an item Aero does not have), asks about what is underspecified (no free
       hand and no method, a tool still in the pack, a target out of reach) and leaves the uncertain to the GM: whether the
       method works, how long it takes, whether the result holds. A created item exists only as "planned" until the GM
       commits it; later steps that use it depend on that. */
    function customStep(s, i) {
      var ex = { step: i, step_id: s.id }, how = !!String(s.method || "").trim() || !!s.parsed;
      function ask(code, msg, extra) { if (how) warn("GM_" + code, msg + " The GM adjudicates the method you described.", { step: i, step_id: s.id, advisory: true }); else err(code, msg, Object.assign({ step: i, step_id: s.id }, extra || {})); }
      (s.uses || []).forEach(function (id) {
        var e = eq[id];
        if (!e) { err("UNKNOWN_ITEM", "“" + String(id).replace(/_/g, " ") + "” is not part of Aero's established equipment. The GM never adds gear that is not in the record.", { step: i, step_id: s.id, resolution: "not_possible_here" }); return; }
        if (e.planned) warn("GM_DEPENDS", eqName(id) + " exists only if an earlier step works; the GM resolves that first.", { step: i, step_id: s.id, advisory: true });
        var movesIt = (s.equipment_changes || []).some(function (ch) { return ch.item === id; });
        if (["holstered", "stored", "worn", "attached"].indexOf(e.state) >= 0 && !e.usable_in_place && !e.planned && !movesIt) {
          var take = byId(ctx.objects, "eq_take:" + id);
          ask("ACCESS", eqName(id) + " is " + e.state + (e.where ? " (" + e.where + ")" : "") + " at that point. Take it out first, or say how Aero uses it where it is.",
              { resolution: take ? "add_step" : "needs_choice", suggest: take ? [take.id] : [], suggest_steps: take ? [{ type: "object", option: take.id }] : [] });
        }
        if ((e.state === "placed" || e.state === "dropped") && e.at && here[e.at] != null && here[e.at] > 5) ask("POSITION", eqName(id) + " lies " + (e.where || "") + " about " + here[e.at] + " ft away at that point.");
        if (e.state === "transported" && e.at && here[e.at] != null && here[e.at] > 5) ask("POSITION", eqName(id) + " is on " + names(ctx, [e.at])[0] + ", about " + here[e.at] + " ft away at that point.");
        if (e.active_when && flags.indexOf(e.active_when) < 0) {
          var pv = providers(e.active_when);
          ask("REQUIRES", eqName(id) + " needs " + flagName(e.active_when) + " for that.", { resolution: pv.length ? "add_step" : "needs_choice", suggest: pv.map(function (p) { return p.option; }), suggest_steps: pv });
        }
      });
      (s.targets || []).forEach(function (vid) {
        var v = byId(ctx.visible, vid), reach = s.reach_ft != null ? s.reach_ft : 5;
        if (!v) { err("TARGET", "“" + vid + "” is not something Aero can see right now.", { step: i, step_id: s.id, resolution: "not_possible_here" }); return; }
        if (here[vid] != null && here[vid] > reach) {
          var mv2 = (ctx.movement || []).filter(function (m) { return m.distance_after && m.distance_after[vid] != null && m.distance_after[vid] <= reach; }).map(function (m) { return m.id; });
          ask("POSITION", v.label + " is about " + here[vid] + " ft away at that point.", { resolution: mv2.length ? "add_step" : "needs_choice", suggest: mv2, suggest_steps: mv2.map(function (id) { return { type: "move", option: id }; }) });
        }
      });
      if (hands) {
        var need = s.hands != null ? +s.hands : ((s.uses || []).length || (s.equipment_changes || []).length ? 1 : 0);
        var usable = freeCount() + ["right", "left"].filter(function (h) { return hands[h] && (s.uses || []).indexOf(hands[h].item) >= 0; }).length;
        if (need > usable) {
          var f = freers(i).filter(function (oid) { var ob = byId(ctx.objects, oid); return !(ob && (s.uses || []).indexOf(ob.frees_item) >= 0); });
          ask("HANDS", "This needs " + need + " hand" + (need > 1 ? "s" : "") + "; at that point " + heldText() + ".",
              { resolution: f.length ? "add_step" : "needs_choice", suggest: f, suggest_steps: f.map(function (id) { return { type: "object", option: id }; }) });
        }
      }
      (s.equipment_changes || []).forEach(function (ch) {
        var e = eq[ch.item];
        if (!e) { err("UNKNOWN_ITEM", "“" + String(ch.item).replace(/_/g, " ") + "” is not part of Aero's established equipment.", { step: i, step_id: s.id, resolution: "not_possible_here" }); return; }
        if (hands && e.state === "held" && ch.to !== "held") { var h0 = holding(ch.item); if (h0) hands[h0] = null; }
        if (ch.in) {  // putting it into a container: never beyond what the record says it holds
          var box = eq[ch.in];
          if (!box) { err("UNKNOWN_ITEM", "“" + String(ch.in).replace(/_/g, " ") + "” is not part of Aero's equipment.", { step: i, step_id: s.id, resolution: "not_possible_here" }); return; }
          var inside = Object.keys(eq).filter(function (k) { return eq[k].in === ch.in && k !== ch.item; }).map(function (k) { return eq[k]; });
          var cap = box.capacity || {};
          if (cap.slots == null && cap.max_bulk == null) err("CAPACITY", eqName(ch.in) + " has no stated room for more; the GM has to rule what it can hold before anything is added.", { step: i, step_id: s.id, resolution: "needs_choice" });
          else if (cap.slots != null && inside.length + 1 > cap.slots) err("CAPACITY", eqName(ch.in) + " is full at that point (" + inside.length + " of " + cap.slots + " places used): " + inside.map(function (x) { return x.label; }).join(", ") + ".", { step: i, step_id: s.id, resolution: "not_possible_here" });
          else if (cap.max_bulk != null && inside.reduce(function (t, x) { return t + (x.bulk || 0); }, 0) + (e.bulk || 0) > cap.max_bulk) err("CAPACITY", eqName(ch.in) + " cannot take " + eqName(ch.item) + ": that would be more than it can carry.", { step: i, step_id: s.id, resolution: "not_possible_here" });
          e.in = ch.in; e.where = box.label;
        } else if (e.in && ch.to !== "attached") { delete e.in; }
        if (hands && ch.to === "held" && e.state !== "held") takeHand(ch.item, "the " + eqName(ch.item), e.hands == null ? 1 : e.hands);
        e.state = ch.to; if (ch.where) e.where = ch.where; if (ch.at) e.at = ch.at;
      });
      if (s.creates && String(s.creates.label || "").trim()) {
        var nid = s.creates.id || ("made_" + s.id);
        eq[nid] = { id: nid, label: s.creates.label, state: s.creates.state || "placed", where: s.creates.where || "", planned: true, from_step: s.id };
        info.push({ code: "IMPROVISED", message: "“" + s.creates.label + "” would exist only if the GM rules the method works. Whether it can be made, how long it takes, and whether it holds are separate questions; nothing is assumed durable." });
      }
    }
    steps.forEach(function (s, i) {
      var ex = { step: i, step_id: s.id };
      if (s.type === "move") {
        var m = byId(ctx.movement, s.option);
        if (m) { if (m.distance_after) for (var k in here) here[k] = m.distance_after[k] != null ? m.distance_after[k] : null; pos = placeOf(m, ctx) || pos; applyFlags(m); }
        snap(s); return;
      }
      if (s.type === "free" && (s.method || (s.uses || []).length || (s.targets || []).length || (s.equipment_changes || []).length || s.creates)) {
        customStep(s, i); snap(s); return;
      }
      if (s.type === "free") {  // custom steps: the GM adjudicates; report what is visible at that point
        var t = String(s.text || ""), kinds = kindsOf(t);
        if (kinds.indexOf("item") >= 0 || s.kind === "item") {
          if (hands && freeCount() === 0) warn("GM_HANDS", "“" + t.slice(0, 80) + "”: at that point " + heldText() + ". The GM will ask how Aero does it.", { step: i, step_id: s.id, advisory: true });
          findAliases(t, ctx.visible).forEach(function (vid) {
            if (here[vid] != null && here[vid] > 5) warn("GM_POSITION", "“" + t.slice(0, 80) + "”: " + names(ctx, [vid])[0] + " is about " + here[vid] + " ft away at that point. The GM stops there unless a move comes first.", { step: i, step_id: s.id, advisory: true });
          });
        }
        snap(s); return;
      }
      var isAct = s.type === "action" || s.type === "bonus_action";
      var o = s.type === "object" ? byId(ctx.objects, s.option) : isAct ? byId(opts, s.option) : null;
      if (!o) { snap(s); return; }
      (o.requires || []).forEach(function (r) {
        if (flags.indexOf(r) >= 0) return;
        if ((o.removes || []).indexOf(r) >= 0) {  // undoing something that is not there (holstering a holstered blaster)
          err("ALREADY", o.label + ": at that point Aero does not have " + (ctx.flag_labels && ctx.flag_labels[r] || r.replace(/_/g, " ")) + ".", { step: i, step_id: s.id, resolution: "not_possible_here" });
          return;
        }
        var pv = providers(r);
        err("REQUIRES", o.label + " needs " + (ctx.flag_labels && ctx.flag_labels[r] || r.replace(/_/g, " ")) + " first.",
            { step: i, step_id: s.id, resolution: pv.length ? "add_step" : "not_possible_here", suggest: pv.map(function (p) { return p.option; }), suggest_steps: pv });
      });
      (o.unless || []).forEach(function (r) {
        if (flags.indexOf(r) >= 0) err("ALREADY", o.label + ": at that point Aero already has " + (ctx.flag_labels && ctx.flag_labels[r] || r.replace(/_/g, " ")) + ".", { step: i, step_id: s.id, resolution: "not_possible_here" });
      });
      if (isAct) {
        if (o.needs_target) {
          var tg = byId(ctx.visible, s.target), dist = tg ? (here[tg.id] != null ? here[tg.id] : tg.distance_ft) : null;
          // in combat movement may be split around the action, so the closest point of the declared moves counts
          if (tg && combat) steps.forEach(function (x) { var mm = x.type === "move" && byId(ctx.movement, x.option); if (mm && mm.distance_after && mm.distance_after[tg.id] != null) dist = Math.min(dist, mm.distance_after[tg.id]); });
          if (!tg) err("TARGET", o.label + " needs a visible target.", ex);
          else if (o.reach_ft != null && dist > o.reach_ft) err("RANGE", tg.label + " is about " + dist + " ft away, beyond " + o.label + "'s reach of " + o.reach_ft + " ft.", ex);
        }
        if (o.needs_trigger && !s.trigger) err("TRIGGER", o.label + " needs a trigger (for example, \"" + (o.default_trigger || "when a hostile moves into reach") + "\").", ex);
        if (o.area_ft != null) {
          var inside = (ctx.visible || []).filter(function (v) { return v.distance_ft <= o.area_ft; }).map(function (v) { return v.label; });
          var outside = (ctx.visible || []).filter(function (v) { return v.distance_ft > o.area_ft; }).map(function (v) { return v.label + " (~" + v.distance_ft + " ft)"; });
          info.push({ code: "AREA", message: o.label + " (" + o.area_ft + "-ft radius) would reach: " + (inside.length ? joinAnd(inside) : "no one visible") + "." + (outside.length ? " Out of reach: " + joinAnd(outside) + "." : "") });
        }
        if (o.cost && o.cost.force_points && (ctx.resources || {}).force_points < o.cost.force_points) err("RESOURCE", o.label + " costs " + o.cost.force_points + " Force Points; you have " + ctx.resources.force_points + ".", ex);
        if (o.uses_left === 0) err("RESOURCE", o.label + " has no uses left.", ex);
      }
      if (o.risk) warn("RISK", o.label + ": " + o.risk, { step: i, step_id: s.id, advisory: !combat });
      if (o.at && here[o.at] != null && here[o.at] > (o.reach_ft != null ? o.reach_ft : 5)) {
        var reach = (ctx.movement || []).filter(function (m) { return m.distance_after && m.distance_after[o.at] != null && m.distance_after[o.at] <= (o.reach_ft != null ? o.reach_ft : 5); }).map(function (m) { return m.id; });
        err("POSITION", o.label + ": " + names(ctx, [o.at])[0] + " is about " + here[o.at] + " ft away at that point. " + (reach.length ? "Add a move there first." : "There is no listed way to reach it from here."),
            { step: i, step_id: s.id, resolution: reach.length ? "add_step" : "not_possible_here", suggest: reach, suggest_steps: reach.map(function (id) { return { type: "move", option: id }; }) });
      }
      if (o.from_container && o.access_rounds > 1) {
        if (combat) err("TIME", o.label + " takes about " + o.access_rounds + " rounds (" + (eq[o.item] && eq[o.item].access || "unstrapping") + "); it cannot be done within one turn.", { step: i, step_id: s.id, resolution: "not_possible_here" });
        else info.push({ code: "TAKES_TIME", message: o.label + ": " + (eq[o.item] && eq[o.item].access || "takes a while") + ". The world keeps moving while Aero works." });
      }
      if (o.item && eq[o.item] && o.to_state === "held") {
        var ei = eq[o.item];
        if (ei.state === "held") err("ALREADY", o.label + ": at that point it is already in Aero's hand.", { step: i, step_id: s.id, resolution: "not_possible_here" });
        else if ((ei.state === "placed" || ei.state === "dropped") && !o.at) err("ACCESS", o.label + ": at that point it is " + ei.state + (ei.where ? " " + ei.where : "") + ", not on Aero.", { step: i, step_id: s.id, resolution: "not_possible_here" });
      }
      if (o.unless_active && flags.indexOf(o.unless_active) >= 0) {
        var offs = (ctx.objects || []).filter(function (x) { return (x.removes || []).indexOf(o.unless_active) >= 0; }).map(function (x) { return x.id; });
        err("REQUIRES", o.label + ": it is still active at that point (" + flagName(o.unless_active) + "). Switch it off first.", { step: i, step_id: s.id, resolution: offs.length ? "add_step" : "not_possible_here", suggest: offs, suggest_steps: offs.map(function (id) { return { type: "object", option: id }; }) });
      }
      if (o.frees_item && eq[o.frees_item] && eq[o.frees_item].state !== "held")
        err("ALREADY", o.label + ": at that point " + eqName(o.frees_item) + " is not in Aero's hand.", { step: i, step_id: s.id, resolution: "not_possible_here" });
      if (hands) {
        var need = (o.needs_hands || 0) + (o.takes_hands || 0);
        if (need > freeCount()) {
          var f = freers(i), canFree = f.length && f.length + freeCount() >= need;
          err("HANDS", o.label + " needs " + need + " free hand" + (need > 1 ? "s" : "") + "; at that point " + heldText() + "." +
              (canFree ? " Free one first (for example: " + joinAnd(f.map(function (id) { return byId(ctx.objects, id).label.toLowerCase(); }), "or") + "), or say how Aero carries it." : " Nothing listed frees enough hands; say how Aero carries it or leave something behind."),
              { step: i, step_id: s.id, resolution: canFree ? "add_step" : "needs_choice", suggest: f, suggest_steps: canFree ? f.map(function (id) { return { type: "object", option: id }; }) : [] });
        } else if (o.takes_hands) {
          var n = o.takes_hands; ["right", "left"].forEach(function (h) { if (n > 0 && !hands[h]) { hands[h] = { item: o.item || o.id, label: o.item_label || (o.item ? "the " + String(o.item).replace(/_/g, " ") : o.label) }; n--; } });
        }
        if (o.frees_hand && hands[o.frees_hand]) { var fi = hands[o.frees_hand].item; if (eq[fi]) { eq[fi].state = o.to_state || eq[fi].home_state || "holstered"; } hands[o.frees_hand] = null; }
        if (o.frees_item && holding(o.frees_item)) hands[holding(o.frees_item)] = null;
      }
      if (o.item && eq[o.item] && o.to_state) { eq[o.item].state = o.to_state; if (o.to_state === "held") delete eq[o.item].in; }
      if (o.frees_item && eq[o.frees_item]) { eq[o.frees_item].state = o.to_state || "placed"; if (o.to_state === "placed") eq[o.frees_item].where = pos || "here"; }
      applyFlags(o);
      snap(s);
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
    // a reaction prompt (the GM stopped at a trigger during someone else's moment): only a reaction, or declining, is possible
    if (ctx.reaction_prompt) {
      var rp = ctx.reaction_prompt;
      if (steps.some(function (s) { return s.type !== "speech" || (s.text && s.text.length > 80); }))
        err("REACTION_ONLY", "It is not your turn: " + (rp.trigger || "something is happening") + ". You can only choose a reaction now (or none).");
      (decl.reactions || []).forEach(function (r) { if ((rp.options || []).indexOf(r) < 0) err("REACTION_NOT_OFFERED", "That reaction does not fit what is happening right now."); });
      if ((decl.reactions || []).length > 1) err("ONE_REACTION", "You have one reaction.");
      if (!(decl.reactions || []).length && !decl.reaction_decline) err("REACTION_CHOICE", "Choose a reaction or decline it.");
      if (b.reaction === 0 && (decl.reactions || []).length) err("REACTION_USED", "Your reaction is already spent this round.");
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

    var used = { action: Math.min(actionCount, 9), bonus_action: bonus.length, movement_ft: feet, object_interaction: Math.min(costlyObjs.length, Math.max(1, b.object_interaction == null ? 1 : b.object_interaction)), reaction: reservesReaction ? 1 : 0 };
    return { errors: errors, warnings: warnings, info: info, used: used, trace: trace, halts: halts, speechAction: speechAction };
  }

  /* one path per branch case (plus "otherwise"); a path that stops at a branch ends there */
  function paths(steps) {
    var out = [{ steps: [], label: [], stopped: null, choice: {} }], nested = false;
    for (var i = 0; i < steps.length; i++) {
      var s = steps[i];
      if (s.type !== "branch") { out.forEach(function (p) { if (!p.stopped) p.steps.push(s); }); continue; }
      var next = [];
      out.forEach(function (p) {
        if (p.stopped) { next.push(p); return; }
        (s.cases || []).forEach(function (c, k) {
          if ((c.steps || []).some(function (x) { return x.type === "branch"; })) nested = true;
          var ch = clone(p.choice); ch[s.id] = k;
          next.push({ steps: p.steps.concat(c.steps || []), label: p.label.concat(["if " + (c.when || "…")]), stopped: c.after === "stop" ? s.id : null, choice: ch });
        });
        var co = clone(p.choice); co[s.id] = "otherwise";
        next.push({ steps: p.steps.slice(), label: p.label.concat(["otherwise"]), stopped: s.otherwise === "continue" ? null : s.id, choice: co });
      });
      out = next;
      if (out.length > 16) return { error: "TOO_MANY_BRANCHES" };
    }
    return nested ? { error: "NESTED_BRANCH" } : out;
  }
  function halting(steps) { var h = []; steps.forEach(function (s, i) { if ((s.condition && s.condition.text) || s.type === "branch") h.push(i); }); return h; }

  /* Equipment interactions are derived from ctx.equipment (the record), so the palette always offers taking an item
     out, putting it away or setting it down, without the GM listing each one. Objects the GM published for an item win. */
  function withEquipment(ctx) {
    if (!ctx || !Array.isArray(ctx.equipment) || ctx.__eq) return ctx;
    var c = clone(ctx); c.__eq = true; c.objects = (c.objects || []).slice();
    var covered = {}; c.objects.forEach(function (o) { [o.item, o.frees_item, o.equipment].forEach(function (x) { if (x) covered[x] = 1; }); });
    c.equipment.forEach(function (e) {
      if (covered[e.id] || e.fixed) return;
      var nm = e.label || e.id.replace(/_/g, " "), hands = e.hands == null ? 1 : e.hands;
      var cont = e.in && byId(c.equipment, e.in);
      if (e.state !== "transported") c.objects.push({ id: "eq_take:" + e.id, label: cont ? "Take " + nm + " off " + cont.label : (e.state === "holstered" ? "Draw " : "Take out ") + nm, takes_hands: hands, item: e.id, item_label: nm, to_state: "held", generated: true, gear: true,
        detail: (e.where ? "from " + e.where : "") + (e.access ? " · " + e.access : ""), at: (e.state === "placed" || e.state === "dropped") ? e.at : undefined, access_rounds: e.access_rounds, from_container: e.in });
      c.objects.push({ id: "eq_stow:" + e.id, label: "Put away " + nm, frees_item: e.id, to_state: e.home_state || "stored", generated: true, gear: true, detail: e.home ? "to " + e.home : "", unless_active: e.active_when });
      c.objects.push({ id: "eq_place:" + e.id, label: "Set " + nm + " down here", frees_item: e.id, to_state: "placed", generated: true, gear: true, unless_active: e.active_when });
    });
    return c;
  }
  function validate(declIn, ctx) {
    ctx = withEquipment(ctx);
    var decl = normalize(declIn, ctx), combat = ctx.mode === "combat";
    var ps = paths(decl.steps), errors = [], warnings = [], info = [], trace = {}, used = null, speechAction = false;
    if (ps.error) {
      errors.push({ code: ps.error, message: ps.error === "NESTED_BRANCH" ? "A branch cannot sit inside another branch. Put the second choice in its own step after it." : "Too many branches in one plan (more than 16 outcomes). Split it, or submit part of it." });
      ps = [{ steps: decl.steps.filter(function (s) { return s.type !== "branch"; }), label: [], choice: {} }];
    }
    var containing = {}, results = ps.map(function (p) {
      var d = normalize(Object.assign({}, decl, { steps: p.steps }), ctx);
      p.steps.forEach(function (s) { containing[s.id] = (containing[s.id] || 0) + 1; });
      return { p: p, r: validateLinear(d, ctx) };
    });
    var seenE = {}, seenW = {}, seenI = {};
    results.forEach(function (x) {
      x.r.trace.forEach(function (t) { if (!trace[t.step_id]) trace[t.step_id] = t; });
      x.r.info.forEach(function (i) { if (!seenI[i.message]) { seenI[i.message] = 1; info.push(i); } });
      x.r.warnings.forEach(function (w) { var k = w.code + "|" + (w.step_id || "") + "|" + w.message; if (!seenW[k]) { seenW[k] = 1; warnings.push(w); } });
      if (!used) used = clone(x.r.used); else for (var k in used) used[k] = Math.max(used[k], x.r.used[k]);
      speechAction = speechAction || x.r.speechAction;
    });
    var groups = {}, order = [];
    results.forEach(function (x) {
      var mine = {};
      x.r.errors.forEach(function (e) {
        var k = e.code + "|" + (e.step_id || "");
        if (mine[k]) return; mine[k] = 1;
        if (!groups[k]) { groups[k] = { e: e, n: 0, labels: [] }; order.push(k); }
        groups[k].n++; groups[k].labels.push(x.p.label.join(", "));
      });
    });
    order.forEach(function (k) {
      var g = groups[k];
      if (!g.e.step_id || ps.length === 1 || g.n >= (containing[g.e.step_id] || 1)) errors.push(g.e);
      else warnings.push({ code: "BRANCH_DEPENDENT", message: "In the case “" + g.labels[0] + "”: " + g.e.message + " The GM stops there in that case.", step: g.e.step, step_id: g.e.step_id, advisory: true, cause: g.e.code });
    });
    flat(decl.steps).forEach(function (s, i) {
      if (s.type !== "branch") return;
      if (!(s.cases || []).length) errors.push({ code: "BRANCH_EMPTY", message: "A decision needs at least one “if”.", step_id: s.id });
      (s.cases || []).forEach(function (c, k) { if (!String(c.when || "").trim()) errors.push({ code: "BRANCH_WHEN", message: "Say what Aero must hear or see for " + (k ? "“else if” " + k : "the “if”") + " of this decision.", step_id: s.id }); });
      if (decl.steps.indexOf(s) < 0) errors.push({ code: "NESTED_BRANCH", message: "A decision cannot sit inside another decision.", step_id: s.id });
    });
    var halts = halting(decl.steps);
    if (decl.steps.some(function (s) { return s.type === "branch"; }))
      info.push({ code: "BRANCH", message: "At a branch the GM takes a case only when what Aero has seen or heard settles it. Missing information never counts as a yes; otherwise it does what you chose for “otherwise”." });
    var preview = previewSteps(decl.steps, ctx, combat, speechAction);
    var mv = decl.movement ? byId(ctx.movement, decl.movement.option) : null;
    if (mv && mv.id === "hold" && !decl.steps.some(function (s) { return s.type === "move"; }) && decl.steps.length) preview.push({ step: "movement", text: mv.label });
    (decl.reactions || []).forEach(function (r) { var x = byId(ctx.reactions, r); if (x) preview.push({ step: "reaction", text: (ctx.reaction_prompt ? "Now: " : "If " + x.trigger + ": ") + x.label }); });
    if (ctx.reaction_prompt && decl.reaction_decline) preview.push({ step: "reaction", text: "Do not react" });
    var confirm = warnings.filter(function (w) { return !w.advisory; });
    var alternatives = errors.some(function (e) { return e.code === "ACTION_CONFLICT"; }) ? alternativesFor(decl, ctx) : [];
    return { contract: VERSION, legal: errors.length === 0, needs_confirmation: errors.length === 0 && confirm.length > 0,
             errors: errors, warnings: warnings, info: info, preview: preview, used: used, alternatives: alternatives,
             steps: decl.steps, halts: halts, trace: decl.steps.length ? flat(decl.steps).map(function (s) { return trace[s.id]; }).filter(Boolean) : [], paths: ps.length };
  }

  /* ---------- per-step status for the builder (from a validate() result; never a prediction) ---------- */
  function stepStatus(v) {
    var out = {}, top = v.steps || [], firstHalt = (v.halts || []).length ? v.halts[0] : -1;
    function set(id, st) { out[id] = st; }
    flat(top).forEach(function (s) { set(s.id, { status: s.type === "free" ? "gm" : "ok", messages: [] }); });
    top.forEach(function (s, i) {
      if (s.type === "branch") (s.cases || []).forEach(function (c) { (c.steps || []).forEach(function (x) { if (out[x.id].status === "ok") out[x.id].status = "case"; }); });
      if (firstHalt >= 0 && i > firstHalt) flat([s]).forEach(function (x) { out[x.id].status = "waits"; });
      if (i === firstHalt) out[s.id].status = s.type === "branch" ? "branch" : "waits";
      if (s.pending && s.status && CONTINUABLE.indexOf(s.status) < 0) out[s.id].status = "invalidated";
    });
    v.warnings.forEach(function (w) { var o = w.step_id && out[w.step_id]; if (!o) return; o.messages.push(w.message); if (o.status === "ok" || o.status === "case") o.status = /^GM_/.test(w.code) ? "gm" : "risky"; });
    v.errors.forEach(function (e) {
      var o = e.step_id && out[e.step_id]; if (!o) return;
      if (o.status !== "fix") { o.status = "fix"; o.messages = []; }
      o.messages.push(e.message);
      if (!o.resolution || e.resolution === "not_possible_here" || (e.resolution === "needs_choice" && o.resolution === "add_step")) { o.resolution = e.resolution || "not_possible_here"; }
      o.suggest_steps = (o.suggest_steps || []).concat(e.suggest_steps || []);
    });
    return out;
  }

  /* ---------- palette availability: validate the plan with each candidate inserted ---------- */
  function insertStep(steps, where, step) {
    steps = clone(steps || []);
    if (where && where.branch) {
      var b = byId(steps, where.branch);
      if (b && b.type === "branch" && b.cases && b.cases[where.case]) { step.seq = b.seq; b.cases[where.case].steps = (b.cases[where.case].steps || []).concat([step]); return steps; }
    }
    var seq = where && where.seq != null ? where.seq : (steps.length ? steps[steps.length - 1].seq || 0 : 0), idx = 0;
    step.seq = seq;
    for (var i = steps.length - 1; i >= 0; i--) if ((steps[i].seq || 0) <= seq) { idx = i + 1; break; }
    if (where && where.index != null) idx = Math.max(0, Math.min(where.index, steps.length));
    steps.splice(idx, 0, step);
    return steps;
  }
  function candidates(ctx) {
    return [].concat((ctx.options || []).map(function (o) { return { type: o.slot === "bonus_action" ? "bonus_action" : "action", option: o.id, label: o.label }; }),
      (ctx.movement || []).filter(function (m) { return m.id !== "hold"; }).map(function (m) { return { type: "move", option: m.id, label: m.label }; }),
      (ctx.objects || []).map(function (o) { return { type: "object", option: o.id, label: o.label }; }));
  }
  function availability(declIn, ctx, where) {
    ctx = withEquipment(ctx);
    var base = normalize(declIn, ctx), rb = validate(base, ctx);
    var baseGlobal = rb.errors.filter(function (e) { return !e.step_id; }).map(function (e) { return e.code; });
    return candidates(ctx).map(function (c) {
      var st = { id: "__cand", type: c.type, option: c.option };
      if (c.type === "action" || c.type === "bonus_action") { st.target = null; st.trigger = null; }
      var d = clone(base); d.steps = insertStep(base.steps, where, st);
      var r = validate(d, ctx);
      var errs = r.errors.filter(function (e) { return (e.step_id === "__cand" || (!e.step_id && baseGlobal.indexOf(e.code) < 0)) && e.code !== "TARGET" && e.code !== "TRIGGER"; });
      var warns = r.warnings.filter(function (w) { return w.step_id === "__cand"; });
      var status = "ok";
      if (errs.some(function (e) { return STOP_ERRORS.indexOf(e.code) >= 0 || e.resolution === "not_possible_here" || !e.resolution; })) status = "not_here";
      else if (errs.some(function (e) { return e.resolution === "needs_choice"; })) status = "needs_choice";
      else if (errs.length) status = "needs_step";
      else if (warns.length) status = "risky";
      var sugg = [], seen = {};
      errs.forEach(function (e) { (e.suggest_steps || []).slice(0, 1).forEach(function (x) { var k = x.type + ":" + x.option; if (!seen[k]) { seen[k] = 1; var src = x.type === "move" ? byId(ctx.movement, x.option) : x.type === "object" ? byId(ctx.objects, x.option) : byId(ctx.options, x.option); sugg.push({ type: x.type, option: x.option, label: src ? src.label : x.option }); } }); });
      return { type: c.type, option: c.option, label: c.label, status: status, codes: errs.map(function (e) { return e.code; }).concat(warns.map(function (w) { return w.code; })),
               reasons: errs.map(function (e) { return e.message; }).concat(warns.map(function (w) { return w.message; })), suggest: status === "needs_step" ? sugg : [] };
    });
  }

  /* ---------- plan progress (GM side): the one shape for a partially executed plan ----------
   * outcome = { completed: [step ids, in order], interrupted: id|null, stop_kind, reason,
   *             branches: {branch id: case index|"otherwise"},
   *             blocked: [ids]    steps that cannot happen because something they needed did not happen (a failed cut),
   *             cancelled: [ids]  steps the changed circumstances make pointless (named by the GM, with the reason),
   *             suspended: [ids]  combat only: intentions set aside until the fight ends (the rest are cancelled) }
   * Step statuses: completed · interrupted (in progress when it happened) · paused (the decision point it stopped at)
   * · unattempted (not reached) · blocked · cancelled · suspended · skipped (an untaken branch case).
   * Only interrupted, paused, unattempted and (outside combat) suspended steps can be continued, and only when the
   * player authorizes them again against the latest turn context. A consequential stop leaves the rest unattempted
   * unless the GM names steps the new circumstances cancel. */
  var STOP_KINDS = ["consequential", "mechanical", "prerequisite", "condition", "combat", "complete"];
  var CONTINUABLE = ["interrupted", "paused", "unattempted", "suspended", "pending"];
  function planProgress(declIn, ctx, outcome) {
    ctx = withEquipment(ctx);
    var decl = normalize(declIn, ctx), o = outcome || {}, kind = o.stop_kind, problems = [];
    if (kind === "incidental") problems.push("An incidental event is not a stop: log it and continue the plan.");
    else if (STOP_KINDS.indexOf(kind) < 0) problems.push("Unknown stop_kind " + JSON.stringify(kind) + ".");
    var br = o.branches || {}, path = [], skipped = [], haltAt = null;
    for (var i = 0; i < decl.steps.length && haltAt === null; i++) {
      var s = decl.steps[i];
      if (s.type !== "branch") { path.push(s); continue; }
      var ch = br[s.id];
      (s.cases || []).forEach(function (c, k) { if (ch !== k) skipped = skipped.concat(flat(c.steps || []).map(function (x) { return x.id; })); });
      if (ch === undefined) { haltAt = { step: s, index: i }; break; }
      if (ch === "otherwise") { if (s.otherwise !== "continue") haltAt = { step: s, index: i, settled: true }; continue; }
      var c = (s.cases || [])[ch];
      if (!c) { problems.push("Branch " + s.id + " has no case " + ch + "."); haltAt = { step: s, index: i }; break; }
      path = path.concat(c.steps || []);
      if (c.after === "stop") haltAt = { step: s, index: i, after: true };
    }
    var ids = path.map(function (s) { return s.id; }), done = o.completed || [];
    for (var j = 0; j < done.length; j++) if (ids[j] !== done[j]) { problems.push("completed must be the first " + done.length + " steps of the executed path, in order (step " + (j + 1) + " is " + ids[j] + ", got " + done[j] + ")."); break; }
    var restSteps = path.slice(done.length), interrupted = o.interrupted || null;
    if (interrupted && (!restSteps.length || restSteps[0].id !== interrupted)) problems.push("interrupted must be the step right after the completed ones.");
    var reachedHalt = haltAt && done.length === path.length;
    if (kind === "complete" && (restSteps.length || (haltAt && !haltAt.after && !haltAt.settled))) problems.push("stop_kind \"complete\" but steps remain (or a decision is unsettled).");
    if (reachedHalt && !haltAt.after && !haltAt.settled && ["condition", "combat", "consequential", "mechanical"].indexOf(kind) < 0) problems.push("The plan reached an unsettled decision; stop_kind must be \"condition\" (missing information is never a yes).");
    var remaining = restSteps.slice();
    if (haltAt) remaining = remaining.concat(decl.steps.slice(haltAt.after ? haltAt.index + 1 : haltAt.index));
    var remIds = remaining.map(function (s) { return s.id; });
    var blocked = (o.blocked || []).concat(o.invalidated || []), cancelled = o.cancelled || [], suspended = o.suspended || [];
    blocked.concat(cancelled, suspended).forEach(function (id) { if (remIds.indexOf(id) < 0) problems.push("Step " + id + " is not among the steps that did not happen."); });
    if (suspended.length && kind !== "combat") problems.push("Only a combat stop suspends steps.");
    if (kind === "complete" && (blocked.length || cancelled.length)) problems.push("A complete plan has nothing blocked or cancelled.");
    if (problems.length) return { ok: false, problems: problems };
    var out = { interrupted: [], paused: [], unattempted: [], blocked: [], cancelled: [], suspended: [] }, steps = [];
    remaining.forEach(function (s, k) {
      var x = clone(s), st;
      delete x.authorized; delete x.authorized_ctx; x.pending = true;
      if (s.id === interrupted) x.interrupted = true;
      if (blocked.indexOf(s.id) >= 0) { st = "blocked"; x.reason = o.reason ? "it needed something that did not happen" : ""; }
      else if (kind === "combat") { st = suspended.indexOf(s.id) >= 0 ? "suspended" : "cancelled"; x.reason = "initiative began"; }
      else if (cancelled.indexOf(s.id) >= 0) { st = "cancelled"; x.reason = "the situation changed"; }
      else if (s.id === interrupted) st = "interrupted";
      else if (k === 0 && kind === "condition" && !interrupted) st = "paused";
      else if (haltAt && !haltAt.after && s === haltAt.step) st = "paused";
      else st = "unattempted";
      x.status = st; out[st].push(s.id); steps.push(x);
    });
    var counts = { completed: done.length }; Object.keys(out).forEach(function (k) { counts[k] = out[k].length; });
    return { ok: true,
      plan_progress: { action_id: o.action_id || null, completed: done.slice(), interrupted_step: interrupted, interrupted: out.interrupted, paused: out.paused, unattempted: out.unattempted,
                       blocked: out.blocked, cancelled: out.cancelled, suspended: out.suspended, skipped: skipped, branches: br, stop_kind: kind, reason: String(o.reason || "") },
      pending_steps: steps, plan_result: Object.assign({ stop_kind: kind, reason: String(o.reason || "") }, counts) };
  }

  /* ---------- context lint (GM side, before publishing a turn context) ----------
   * Warns when the player-visible context is too thin for reliable checks, so the GM publishes it or the
   * builder defers that check to the GM ("the GM checks"); flags fields that look like hidden numbers. */
  function contextLint(ctx) {
    var out = [], acts = (ctx.options || []).concat(ctx.objects || []);
    function w(code, level, msg) { out.push({ code: code, level: level, message: msg }); }
    if (!ctx.hands && acts.some(function (o) { return o.takes_hands || o.needs_hands || o.frees_hand || o.frees_item; }))
      w("NO_HANDS", "warn", "Hand occupancy is not published; hand checks are deferred to the GM.");
    if (!ctx.hands) w("HANDS_UNKNOWN", "info", "No hands published: the Datapad shows \u201cthe GM checks\u201d.");
    if (!ctx.position_label) w("NO_POSITION", "info", "No position_label: the committed strip omits Aero's position.");
    var vis = ctx.visible || [];
    acts.forEach(function (o) {
      if (o.at && !byId(vis, o.at)) w("UNKNOWN_AT", "warn", o.label + ": `at` names " + o.at + ", which is not visible.");
      if (o.at || o.at_free) return;  // at_free: the GM states it can be done from where Aero is (looking, a held item)
      var named = findAliases((o.label || "") + " " + (o.aliases || []).join(" "), vis).filter(function (id) { var v = byId(vis, id); return v && v.distance_ft > 5; });
      if (named.length) w("NO_AT", "warn", o.label + " names " + names(ctx, named)[0] + " (~" + byId(vis, named[0]).distance_ft + " ft) but has no `at`; its position check is deferred to the GM.");
    });
    var bad = /^(dc|ac|hp|hp_max|hit_points|armor_class|stealth|save_dc|hidden|gm_.*|secret.*)$/i;
    (function scan(x, at) {
      if (Array.isArray(x)) x.forEach(function (y, i) { scan(y, at + "[" + i + "]"); });
      else if (x && typeof x === "object") Object.keys(x).forEach(function (k) { if (bad.test(k) && at.indexOf("resources") < 0) w("LEAK_SUSPECT", "error", at + "." + k + " looks like a hidden number; the turn context must stay player-visible."); scan(x[k], at + "." + k); });
    })(ctx, "turn_context");
    return out;
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

  return { VERSION: VERSION, emptyDecl: emptyDecl, parseFreeform: parseFreeform, normalize: normalize, validate: validate, summary: summary, haltAt: haltAt, classify: classify,
           flat: flat, withEquipment: withEquipment, stepStatus: stepStatus, availability: availability, insertStep: insertStep, planProgress: planProgress, contextLint: contextLint, STOP_KINDS: STOP_KINDS, CONTINUABLE: CONTINUABLE };
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
  } else if (argv[0] === "availability") {  // node turn_contract.js availability <decl|-> <ctx> [<where json>]
    var da = JSON.parse(argv[1] === "-" ? fs.readFileSync(0, "utf8") : fs.readFileSync(argv[1], "utf8"));
    process.stdout.write(JSON.stringify(T.availability(da, ctx, argv[3] ? JSON.parse(argv[3]) : null), null, 1) + "\n");
  } else if (argv[0] === "status") {  // per-step status of a declaration
    var ds = JSON.parse(argv[1] === "-" ? fs.readFileSync(0, "utf8") : fs.readFileSync(argv[1], "utf8")), vs = T.validate(ds, ctx);
    process.stdout.write(JSON.stringify({ validation: vs, status: T.stepStatus(vs) }, null, 1) + "\n");
  } else if (argv[0] === "lintctx") {  // node turn_contract.js lintctx - <ctx>
    var lw = T.contextLint(ctx);
    process.stdout.write(JSON.stringify({ ok: !lw.some(function (x) { return x.level === "error"; }), findings: lw }, null, 1) + "\n");
    process.exit(lw.some(function (x) { return x.level === "error"; }) ? 3 : 0);
  } else if (argv[0] === "progress") {  // node turn_contract.js progress <decl|-> <ctx> <outcome.json>
    var dp = JSON.parse(argv[1] === "-" ? fs.readFileSync(0, "utf8") : fs.readFileSync(argv[1], "utf8"));
    var pr = T.planProgress(dp, ctx, JSON.parse(fs.readFileSync(argv[3], "utf8")));
    process.stdout.write(JSON.stringify(pr, null, 1) + "\n");
    process.exit(pr.ok ? 0 : 3);
  } else { process.stderr.write("usage: parse <text> <ctx> | validate <decl|-> <ctx> | halt <decl|-> <ctx> <index> <reason> | availability <decl|-> <ctx> [where] | status <decl|-> <ctx> | progress <decl|-> <ctx> <outcome>\n"); process.exit(2); }
}
