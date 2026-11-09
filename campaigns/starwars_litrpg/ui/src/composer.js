  /* ===================== Turn composer (turn-contract/3) =====================
     Combat: slot builder with the full action economy (unavailable choices disabled with their reason).
     Scene: a cinematic plan. Visual sequences of ordered steps, a visible palette whose availability
     follows the planned order (GenesisTurn.availability, the same validator the GM runs), committed
     state shown apart from planned state. The Datapad never adjudicates: it only checks structure. */
  var T = window.GenesisTurn, mcpNs = null, phase = "", notifyState = {}, usage = [];
  function byId(list, id) { for (var i = 0; i < (list || []).length; i++) if (list[i].id === id) return list[i]; return null; }
  function freshUi(ctxId, keepWrite) {
    return { ctxId: ctxId, mode: "build", write: keepWrite || "", note: "", confirmed: false, draftId: "", carried: false,
             sel: { dialogue: "silent", own: "", action: "", target: {}, trigger: "", bonus: "", movement: "hold", objects: [], reactions: [], steps: [],
                    nseq: 1, labels: [""], active: { seq: 0 }, nextId: 1, sayDraft: "", actDraft: "" } };
  }
  function upgradeSel(s) {  // drafts saved by older versions keep working
    s.steps = s.steps || []; s.nseq = s.nseq || 1; s.labels = s.labels || [""]; s.active = s.active || { seq: 0 };
    s.nextId = s.nextId || 1; s.sayDraft = s.sayDraft || ""; s.actDraft = s.actDraft || "";
    s.steps = s.steps.map(function (x) {
      if (x.type === "say") x = s.dialogue === "own" ? { type: "speech", text: s.own || "" } : { type: "speech", option: s.dialogue };
      if (!x.id) x.id = "s" + (s.nextId++); if (x.seq == null) x.seq = 0; return x;
    }).filter(function (x) { return x.type !== "speech" || x.option || (x.text && x.text.trim()); });
    var mx = s.steps.reduce(function (m, x) { return Math.max(m, x.seq || 0); }, 0); if (s.nseq <= mx) s.nseq = mx + 1;
    while (s.labels.length < s.nseq) s.labels.push("");
    return s;
  }
  var ui = (function () { try { var x = JSON.parse(ls("datapad.ui") || "null"); if (x && x.sel) { upgradeSel(x.sel); return x; } } catch (e) {} return freshUi(null, ls("datapad.draft")); })();
  function saveUi() { ls("datapad.ui", JSON.stringify(ui)); }
  var eqCache = { src: null, out: null };
  function ctxOf(v) {  // gear interactions (take out / put away / set down) are derived from the record's equipment
    var c = v && v.turn_context ? v.turn_context : null;
    if (!c) return null;
    if (eqCache.src !== c) { eqCache.src = c; try { eqCache.out = T.withEquipment(c); } catch (e) { eqCache.out = c; } }
    return eqCache.out;
  }
  /* A new turn context never throws away a plan in progress: the steps are kept and re-checked against
     what Aero sees now (steps that no longer fit are marked). Left-over steps of the old context are dropped:
     the GM republishes them when they still apply. */
  function syncCtx() {
    var c = ctxOf(view), id = c ? c.context_id : null;
    if (ui.ctxId === id) return;
    var keep = ui.sel, mode = ui.mode, wasScene = ui.ctxId !== null;
    ui = freshUi(id, ui.write);
    if (wasScene && keep && (keep.steps || []).some(function (x) { return !x.pending; }) && sceneMode(c)) {
      keep.steps = keep.steps.filter(function (x) { return !x.pending; }); ui.sel = upgradeSel(keep); ui.mode = mode; ui.carried = true;
    }
    saveUi();
  }
  var localPending = null;  // a turn this device just saved, until the store's listener reports it
  function activeAction() {
    var real = actions.filter(function (a) { return a.status === "submitted" || a.status === "processing"; })[0];
    if (real) return real;
    if (localPending && Date.now() - localPending.at < 20000 && !actions.some(function (a) { return a._id === localPending.id; }))
      return { _id: localPending.id, status: "submitted", text: localPending.text };
    return null;
  }
  function pendingAction() { return activeAction(); }

  /* The validator never blocks the player when it fails: the GM runs the same checks before any roll. */
  function safeValidate(d, c) {
    try { return T.validate(d, c); } catch (e) {
      try { console.error("live check failed", e); } catch (x) {}
      return { contract: T.VERSION, legal: true, needs_confirmation: false, crashed: true, errors: [], warnings: [], alternatives: [], halts: [], trace: [], steps: (d && d.steps) || [],
               info: [{ code: "CHECK_UNAVAILABLE", message: "Live check unavailable right now. You can still submit; the GM checks this turn against the same rules before any roll." }],
               preview: ((d && d.steps) || []).map(function (s) { return { step: s.type, text: stepLabel(c, s) }; }), used: { action: 0, bonus_action: 0, movement_ft: 0, object_interaction: 0, reaction: 0 } };
    }
  }
  function safeStatus(r) { try { return r.crashed ? {} : T.stepStatus(r); } catch (e) { return {}; } }
  function safeAvail(d, c, w) {
    try { return T.availability(d, c, w); } catch (e) {
      return ((c.options || []).map(function (o) { return { type: o.slot === "bonus_action" ? "bonus_action" : "action", option: o.id }; })
        .concat((c.movement || []).filter(function (m) { return m.id !== "hold"; }).map(function (m) { return { type: "move", option: m.id }; }), (c.objects || []).map(function (o) { return { type: "object", option: o.id }; })))
        .map(function (a) { a.status = "unknown"; a.reasons = ["The GM checks this."]; a.suggest = []; return a; });
    }
  }

  function sceneMode(c) { return c && c.mode !== "combat"; }
  function stepLabel(c, st) {
    if (st.type === "say") return "Say the line chosen above";
    if (st.type === "speech") { var dl = st.option && byId(c.dialogue, st.option); return "Say: “" + (st.text || (dl ? dl.text : "")) + "”"; }
    if (st.type === "free") return "Try: " + (st.text || "");
    if (st.type === "branch") return "Decision: if / else if / otherwise";
    var o = st.type === "move" ? byId(c.movement, st.option) : st.type === "object" ? byId(c.objects, st.option) : byId(c.options, st.option);
    return o ? o.label : st.option + " (no longer available here)";
  }
  function cleanStep(x) {
    var st = { id: x.id, seq: x.seq || 0, type: x.type };
    if (x.option) st.option = x.option;
    if (x.text != null) st.text = x.text;
    if (x.kind) st.kind = x.kind;
    ["method", "hands", "reach_ft"].forEach(function (k) { if (x[k] != null && x[k] !== "") st[k] = x[k]; });
    ["uses", "targets", "equipment_changes"].forEach(function (k) { if (x[k] && x[k].length) st[k] = x[k].slice(); });
    if (x.creates && x.creates.label) st.creates = { label: x.creates.label, state: x.creates.state || "placed" };
    if (x.type === "action" || x.type === "bonus_action") { st.target = x.target || null; st.trigger = x.trigger || null; }
    if (x.condition && x.condition.text && x.condition.text.trim()) st.condition = { text: x.condition.text.trim() };
    if (x.pending) { st.pending = true; if (x.status) st.status = x.status; if (x.authorized) { st.authorized = true; if (typeof x.authorized_ctx === "string") st.authorized_ctx = x.authorized_ctx; } }
    if (x.type === "branch") {
      st.cases = (x.cases || []).map(function (k) { return { when: String(k.when || "").trim(), after: k.after === "stop" ? "stop" : "continue", steps: (k.steps || []).map(cleanStep) }; });
      st.otherwise = x.otherwise === "continue" ? "continue" : "stop";
    }
    return st;
  }
  function declaration(c) {
    if (ui.mode === "write") return T.parseFreeform(ui.write, c);
    var d = T.emptyDecl(c), s = ui.sel;
    if (sceneMode(c)) {  // scene: ordered steps in visual sequences; speech lines are steps of their own
      d.steps = s.steps.map(cleanStep);
      d.sequences = s.labels.slice(0, s.nseq).map(function (l) { return { label: l || "" }; });
      if (!d.steps.some(function (x) { return x.type === "move"; }) && byId(c.movement, "hold")) d.movement = { option: "hold" };
      d.reactions = s.reactions.filter(function (o) { return byId(c.reactions, o); });
      return T.normalize(d, c);
    }
    if (s.dialogue === "own" && s.own.trim()) d.speech = { option: null, text: s.own.trim(), approach: "freeform", extended: false };
    else { var dl = byId(c.dialogue, s.dialogue); if (dl) d.speech = { option: dl.id, text: dl.text, approach: dl.approach, extended: !!dl.extended }; }
    if (s.action) {
      var op = byId(c.options, s.action);
      d.actions = [{ option: s.action, target: op && op.needs_target ? (s.target[s.action] || null) : null,
                     trigger: op && op.needs_trigger ? (s.trigger.trim() || op.default_trigger || null) : null }];
    }
    if (s.bonus) d.bonus_actions = [{ option: s.bonus, target: null }];
    if (s.movement && byId(c.movement, s.movement)) d.movement = { option: s.movement };
    d.objects = s.objects.filter(function (o) { return byId(c.objects, o); });
    d.reactions = s.reactions.filter(function (o) { return byId(c.reactions, o); });
    if (ui.note.trim()) { d.freeform = ui.note.trim(); d.unmapped = [ui.note.trim()]; }
    return d;
  }
  function newId() { return "s" + (ui.sel.nextId++); }
  function fromDecl(st, seqMap, authorize) {
    var x = { id: newId(), seq: seqMap(st.seq || 0), type: st.type };
    if (st.status) x.status = st.status;
    ["option", "text", "kind", "target", "trigger", "method", "hands", "uses", "targets", "equipment_changes", "creates"].forEach(function (k) { if (st[k] != null) x[k] = JSON.parse(JSON.stringify(st[k])); });
    if (st.type === "speech" && st.option) delete x.text;
    if (st.condition) x.condition = { text: st.condition.text };
    if (st.pending) { x.pending = true; if (authorize) { x.authorized = true; x.authorized_ctx = authorize; } }
    if (st.type === "branch") { x.otherwise = st.otherwise; x.cases = (st.cases || []).map(function (k) { return { when: k.when || "", after: k.after || "continue", steps: (k.steps || []).map(function (y) { return fromDecl(y, function () { return x.seq; }, authorize); }) }; }); }
    return x;
  }
  function loadDeclaration(d, c, authorize) {
    var s = freshUi(c.context_id).sel;
    if (sceneMode(c)) {
      ui.sel = s;
      var n = T.normalize(d, c), seqs = [];
      n.steps.forEach(function (st) { if (seqs.indexOf(st.seq || 0) < 0) seqs.push(st.seq || 0); });
      seqs.sort(function (a, b) { return a - b; });
      var map = function (q) { return Math.max(0, seqs.indexOf(q)); };
      n.steps.filter(function (st) { return !st.status || T.CONTINUABLE.indexOf(st.status) >= 0; }).forEach(function (st) { s.steps.push(fromDecl(st, map, authorize ? c.context_id || true : false)); });
      if (n.steps.some(function (st) { return st.type === "free" && st.text && !st.kind; })) s.steps.forEach(function (x) { if (x.type === "free" && !x.kind) x.kind = "custom"; });
      s.nseq = Math.max(1, seqs.length); s.labels = []; for (var i = 0; i < s.nseq; i++) s.labels.push((d.sequences && d.sequences[seqs[i]] && d.sequences[seqs[i]].label) || "");
      s.reactions = (d.reactions || []).slice(); s.active = { seq: s.nseq - 1 };
      ui.mode = "build"; ui.confirmed = false; ui.note = ""; saveUi();
      return;
    }
    if (d.speech) { if (d.speech.option && byId(c.dialogue, d.speech.option)) s.dialogue = d.speech.option; else { s.dialogue = "own"; s.own = d.speech.text || ""; } }
    if (d.actions && d.actions[0]) { s.action = d.actions[0].option; if (d.actions[0].target) s.target[s.action] = d.actions[0].target; s.trigger = d.actions[0].trigger || ""; }
    if (d.bonus_actions && d.bonus_actions[0]) s.bonus = d.bonus_actions[0].option;
    s.movement = d.movement ? d.movement.option : "hold";
    s.objects = (d.objects || []).slice(); s.reactions = (d.reactions || []).slice();
    ui.sel = s; ui.mode = "build"; ui.confirmed = false; ui.note = (d.unmapped || []).join(" "); saveUi();
  }
  function turnText(d, r) {
    if (ui.mode === "write") return ui.write.trim();
    if (sceneMode(ctxOf(view))) {
      var by = {}; (r.preview || []).forEach(function (p) { if (p.id && !by[p.id]) by[p.id] = []; if (p.id) by[p.id].push(p.text); });
      var out = [];
      for (var q = 0; q < ui.sel.nseq; q++) {
        var rows = d.steps.filter(function (x) { return (x.seq || 0) === q; }), t = [];
        rows.forEach(function (x) { (by[x.id] || []).forEach(function (p) { t.push(p); }); });
        if (t.length) out.push("Sequence " + (q + 1) + (ui.sel.labels[q] ? " (" + ui.sel.labels[q] + ")" : "") + ": " + t.join("; "));
      }
      return out.join("\n");
    }
    return r.preview.map(function (p) { return p.text; }).join("; ") + (ui.note.trim() ? ". Also: " + ui.note.trim() : "");
  }

  function radio(group, value, checked, label, small, tag, disabled, why) {
    return '<label class="opt' + (disabled ? " off" : "") + '"><input type="radio" name="' + group + '" value="' + esc(value) + '" data-g="' + group + '"' + (checked ? " checked" : "") + (disabled && !checked ? " disabled" : "") + '><span class="lbl">' + esc(label) +
      (tag ? ' <span class="tag">' + esc(tag) + "</span>" : "") + (small ? "<small>" + esc(small) + "</small>" : "") + (why ? '<small class="why">' + esc(why) + "</small>" : "") + "</span></label>";
  }
  function check(group, value, checked, label, small) {
    return '<label class="opt"><input type="checkbox" value="' + esc(value) + '" data-c="' + group + '"' + (checked ? " checked" : "") + '><span class="lbl">' + esc(label) + (small ? "<small>" + esc(small) + "</small>" : "") + "</span></label>";
  }
  function budget(c, r) {
    if (c.mode !== "combat") return '<div class="note">Scene: no initiative and no action economy. Group what Aero intends into sequences, in order. The GM plays the whole plan in one pass and stops only when the world interrupts or something needs your decision. Hands, gear, distance and time still apply.</div>';
    var b = c.budget || {}, u = r.used;
    function p(name, used, txt) { return '<span class="pill ' + (used ? "used" : "ok") + '">' + name + ": " + txt + "</span>"; }
    return '<div class="budget">' + p("Action", u.action >= (b.action || 1), u.action >= (b.action || 1) ? "Used" : "Available") +
      p("Movement", u.movement_ft > 0, (b.movement_ft - u.movement_ft) + "/" + b.movement_ft + " ft") +
      p("Bonus", u.bonus_action >= (b.bonus_action || 1), u.bonus_action ? "Used" : ((c.options || []).some(function (o) { return o.slot === "bonus_action"; }) ? "Available" : "None eligible")) +
      p("Reaction", u.reaction > 0, u.reaction ? "Reserved" : "Available") +
      p("Object", u.object_interaction > 0, u.object_interaction ? "Used" : "Available") + "</div>";
  }
  function checkPanel(r) {
    var cls = r.legal ? (r.needs_confirmation ? "warn" : "") : "bad";
    var head = r.crashed ? "Live check unavailable" : r.legal ? (r.needs_confirmation ? "Legal, with known risks" : r.warnings.length ? "Legal turn (with visible risks)" : "Legal turn") : "Not legal yet";
    var h = '<div class="check ' + cls + '" aria-live="polite"><b>' + head + "</b>";
    r.errors.forEach(function (e) { h += '<div class="msg-err">' + esc(e.message) + "</div>"; });
    r.warnings.forEach(function (w) { h += '<div class="msg-warn">' + esc(w.message) + "</div>"; });
    r.info.forEach(function (i) { h += '<div class="note">' + esc(i.message) + "</div>"; });
    if (r.preview.length) h += "<ol>" + r.preview.map(function (p) { return "<li>" + esc(p.text) + "</li>"; }).join("") + "</ol>";
    if (r.alternatives.length) h += '<div class="note">Legal alternatives:</div><div class="sugg">' + r.alternatives.map(function (a, i) { return '<button class="chip" data-alt="' + i + '">' + esc(a.label) + "</button>"; }).join("") + "</div>";
    if (r.legal && r.needs_confirmation) h += '<label class="opt"><input type="checkbox" id="confirmRisk"' + (ui.confirmed ? " checked" : "") + '><span class="lbl">I understand these risks. Submit anyway.</span></label>';
    h += '<div class="note">Preflight checks what is structurally possible and the risks Aero can see. It never predicts the dice; the world can still interrupt any step.</div>';
    return h + "</div>";
  }

  /* ---------- scene plan ---------- */
  var ICON = { ok: "✓", risky: "⚠", fix: "✕", waits: "⏸", gm: "✎", "case": "↳", branch: "⑂", invalidated: "⊘" };
  var STXT = { ok: "can be attempted", risky: "possible, with a risk", fix: "needs fixing", waits: "waits for your decision", gm: "the GM adjudicates", "case": "only in this case", branch: "decision point", invalidated: "cancelled" };
  var PICO = { ok: "+", risky: "⚠", needs_step: "↪", needs_choice: "?", not_here: "⊘", unknown: "+" };
  var PTXT = { ok: "", risky: "possible, with a risk", needs_step: "needs a step first", needs_choice: "needs your choice", not_here: "not possible here", unknown: "the GM checks" };
  function itemName(h) { return h ? String(h.item || h.label || "something").replace(/_/g, " ") : "free"; }
  function flagName(c, f) { return (c.flag_labels || {})[f] || f.replace(/_/g, " "); }
  function renderNow(c) {
    var parts = [];
    parts.push(c.hands ? "right: " + (c.hands.right ? (c.hands.right.label || itemName(c.hands.right)) : "free") + " · left: " + (c.hands.left ? (c.hands.left.label || itemName(c.hands.left)) : "free") : "hands: the GM checks");
    if (c.position_label) parts.push(c.position_label);
    var fl = (c.state_flags || []).map(function (f) { return flagName(c, f); }); if (fl.length) parts.push(fl.join(", "));
    if ((c.equipment || []).length) {
      var g = c.equipment.filter(function (e) { return !e.fixed && (["holstered", "attached", "transported", "placed", "dropped"].indexOf(e.state) >= 0 || (e.state === "worn" && e.improvised)); }).map(function (e) { return e.label + " (" + (STATEWORD[e.state] || e.state) + (e.where ? ", " + e.where : "") + (e.uncertain ? ", unconfirmed" : "") + ")"; });
      var packed = c.equipment.filter(function (e) { return e.state === "stored"; }).length;
      parts.push("gear: " + (g.length ? g.join("; ") : "nothing loose") + (packed ? "; " + packed + " items packed" : ""));
    }
    var lint = []; try { lint = T.contextLint(c).filter(function (f) { return f.level === "warn"; }); } catch (e) {}
    return '<div class="now" role="status"><span class="pill ok">Now · committed</span> <span>' + esc(parts.join(" · ")) + "</span></div>" +
      (lint.length ? '<div class="note deferred">Some checks are left to the GM for this moment: ' + esc(lint.map(function (f) { return f.code === "NO_HANDS" ? "what Aero holds" : f.code === "NO_AT" ? "where some actions can be done" : "a detail of the scene"; }).filter(function (v, i, a) { return a.indexOf(v) === i; }).join(", ")) + ". The Datapad will not guess them.</div>" : "");
  }
  function eqLabel(c, id) {
    var e = byId(c.equipment, id); if (e) return e.label;
    if (/^made_/.test(id)) { var f = locate(id.slice(5)); var x = f && f.list[f.index]; if (x && x.creates && x.creates.label) return x.creates.label; }
    return String(id).replace(/_/g, " ");
  }
  var STATEWORD = { held: "in hand", holstered: "holstered", worn: "worn", stored: "packed", attached: "attached", transported: "carried along", placed: "set down", dropped: "dropped" };
  function customMeta(c, x) {
    var parts = [];
    if (x.method) parts.push("how: " + x.method);
    if ((x.uses || []).length) parts.push("using " + x.uses.map(function (id) { return eqLabel(c, id); }).join(", "));
    if ((x.targets || []).length) parts.push("on " + x.targets.map(function (id) { var v = byId(c.visible, id); return v ? (v.short || v.label) : id; }).join(", "));
    if (x.hands != null && x.hands !== "") parts.push(x.hands + " hand" + (+x.hands === 1 ? "" : "s"));
    (x.equipment_changes || []).forEach(function (ch) { parts.push(eqLabel(c, ch.item) + " → " + (ch.in ? "into " + eqLabel(c, ch.in) : (STATEWORD[ch.to] || ch.to))); });
    if (x.creates && x.creates.label) parts.push("makes " + x.creates.label + " (" + (STATEWORD[x.creates.state] || x.creates.state) + ", if it works)");
    return parts.length ? '<div class="note meta">' + esc(parts.join(" · ")) + "</div>" : "";
  }
  function plannedLine(c, x, prev, cur) {
    if (!cur) return "";
    var parts = [];
    if (cur.hands && prev.hands && (itemName(cur.hands.right) !== itemName(prev.hands.right) || itemName(cur.hands.left) !== itemName(prev.hands.left)))
      parts.push("right: " + itemName(cur.hands.right) + " · left: " + itemName(cur.hands.left));
    if (cur.position && cur.position !== prev.position) parts.push(cur.position);
    var add = cur.flags.filter(function (f) { return (prev.flags || []).indexOf(f) < 0; }), rem = (prev.flags || []).filter(function (f) { return cur.flags.indexOf(f) < 0; });
    var attempt = x.type === "action" || x.type === "bonus_action";
    if (add.length) parts.push(add.map(function (f) { return flagName(c, f); }).join(", ") + (attempt ? " (if it works)" : ""));
    if (rem.length) parts.push("no longer " + rem.map(function (f) { return flagName(c, f); }).join(", "));
    if (cur.equipment) {
      var pe = prev.equipment || {}; if (!prev.equipment) (c.equipment || []).forEach(function (e) { pe[e.id] = e.state; });
      Object.keys(cur.equipment).forEach(function (k) {
        if (pe[k] === cur.equipment[k]) return;
        var st = cur.equipment[k], planned = /\*$/.test(st); st = st.replace(/\*$/, "");
        if (/^eq_|^(right|left)$/.test(k)) return;
        if (cur.hands && st === "held" && pe[k] !== undefined) return;  // already shown as a hand change
        parts.push(eqLabel(c, k) + ": " + (STATEWORD[st] || st) + (planned ? " (if it works)" : ""));
      });
    }
    if (cur.load != null && prev.load !== cur.load && c.carry && cur.load > c.carry.capacity) parts.push("load " + cur.load + "/" + c.carry.capacity);
    return parts.length ? '<div class="planned">Planned: ' + esc(parts.join(" · ")) + "</div>" : "";
  }
  function locate(id, list, parent, k) {
    list = list || ui.sel.steps;
    for (var i = 0; i < list.length; i++) {
      if (list[i].id === id) return { list: list, index: i, parent: parent || null, caseIdx: k };
      if (list[i].type === "branch") for (var j = 0; j < (list[i].cases || []).length; j++) { var f = locate(id, list[i].cases[j].steps || [], list[i], j); if (f) return f; }
    }
    return null;
  }
  function stepRow(c, s, x, stat, tr, nested) {
    var st = stat[x.id] || { status: "ok", messages: [] }, p = tr.prev[x.id] || tr.now, cur = tr.at[x.id];
    var open = ui.openStep === x.id;
    var h = '<li class="step st-' + st.status + (open ? " open" : "") + '" data-sid="' + esc(x.id) + '"><div class="srow" data-open="' + esc(x.id) + '" role="button" tabindex="0" aria-expanded="' + open + '" aria-label="' + esc(stepLabel(c, x)) + ': show controls"><span class="ico" title="' + STXT[st.status] + '" aria-label="' + STXT[st.status] + '">' + ICON[st.status] + '</span><span class="lbl' + (x.type === "speech" || x.type === "free" ? " verb" : "") + '">' + esc(stepLabel(c, x)) +
      (x.pending ? ' <span class="tag">' + (x.authorized ? "continued" : "left over") + "</span>" : "") + (x.condition ? ' <span class="tag">only if</span>' : "") + '</span><span class="more" aria-hidden="true">' + (open ? "▴" : "▾") + "</span></div>";
    if (x.type === "free") h += customMeta(c, x);
    if (x.type !== "branch") h += plannedLine(c, x, p, cur);
    if (st.messages.length && st.status !== "ok") h += st.messages.map(function (m) { return '<div class="' + (st.status === "fix" ? "msg-err" : st.status === "risky" ? "msg-warn" : "note") + '">' + esc(m) + "</div>"; }).join("");
    if (st.status === "fix" && (st.suggest_steps || []).length) {
      var seen = {};
      h += '<div class="row">' + st.suggest_steps.filter(function (g) { var k = g.type + ":" + g.option; if (seen[k]) return false; seen[k] = 1; return true; }).slice(0, 3).map(function (g) {
        var src = g.type === "move" ? byId(c.movement, g.option) : g.type === "object" ? byId(c.objects, g.option) : byId(c.options, g.option);
        return '<button class="btn mini pre" data-fix="' + esc(x.id) + "|" + g.type + ":" + esc(g.option) + '">Add “' + esc(src ? src.label : g.option) + '” before this</button>';
      }).join("") + "</div>";
    }
    if (st.status === "fix" && st.resolution === "needs_choice") h += '<div class="row"><button class="btn mini pre" data-how="' + esc(stepLabel(c, x)) + '">Say how (custom action)</button></div>';
    if (x.condition && !open && x.condition.text) h += '<div class="note cond">Only if ' + esc(x.condition.text) + "</div>";
    if (x.condition) h += '<input class="txt cond-in" id="w_cond_' + esc(x.id) + '" placeholder="Only if… (the GM stops here and asks unless Aero already knows)" value="' + esc(x.condition.text || "") + '">';
    var o = (x.type === "action" || x.type === "bonus_action") && byId(c.options, x.option);
    if (o && o.needs_target) h += '<select class="txt" id="w_tgt_' + esc(x.id) + '" aria-label="Target"><option value="">Choose a target</option>' + (c.visible || []).map(function (t) { return '<option value="' + esc(t.id) + '"' + (x.target === t.id ? " selected" : "") + ">" + esc(t.label) + " (~" + t.distance_ft + " ft)</option>"; }).join("") + "</select>";
    if (x.type === "branch") h += branchBody(c, s, x, stat, tr);
    h += '<div class="ctl"><button class="btn mini" data-up="' + esc(x.id) + '" aria-label="Move earlier">↑</button><button class="btn mini" data-down="' + esc(x.id) + '" aria-label="Move later">↓</button>' +
      (!nested && x.type !== "branch" ? '<button class="btn mini" data-cond="' + esc(x.id) + '" aria-pressed="' + !!x.condition + '" aria-label="Only if">if…</button>' : "") +
      '<button class="btn mini" data-del="' + esc(x.id) + '" aria-label="Remove this step">✕</button></div>';
    return h + "</li>";
  }
  function branchBody(c, s, x, stat, tr) {
    var h = '<div class="branch">';
    (x.cases || []).forEach(function (k, j) {
      var on = s.active.branch === x.id && s.active["case"] === j;
      h += '<div class="case' + (on ? " active" : "") + '"><label class="note" for="w_when_' + esc(x.id) + "_" + j + '">' + (j ? "Else if" : "If") + '</label><textarea class="when" rows="1" id="w_when_' + esc(x.id) + "_" + j + '" placeholder="What Aero must hear or see, e.g. Wick confirms something is trapped inside">' + esc(k.when || "") + "</textarea>" +
        '<ol class="steps">' + (k.steps || []).map(function (y) { return stepRow(c, s, y, stat, tr, true); }).join("") + "</ol>" + ((k.steps || []).length ? "" : '<div class="note">No steps: do none of this.</div>') +
        '<div class="row"><button class="btn mini" data-act-case="' + esc(x.id) + ":" + j + '" aria-pressed="' + on + '">' + (on ? "Adding here" : "Add steps here") + "</button>" +
        '<button class="btn mini" data-after="' + esc(x.id) + ":" + j + '" aria-pressed="' + (k.after === "stop") + '">' + (k.after === "stop" ? "Then: stop and ask me" : "Then: continue the plan") + "</button>" +
        ((x.cases || []).length > 1 ? '<button class="btn mini" data-del-case="' + esc(x.id) + ":" + j + '" aria-label="Remove this case">✕</button>' : "") + "</div></div>";
    });
    h += '<button class="btn mini" data-add-case="' + esc(x.id) + '">+ Else if</button>' +
      '<div class="row otherwise"><span class="note">Otherwise:</span><button class="btn mini" data-other="' + esc(x.id) + ':stop" aria-pressed="' + (x.otherwise !== "continue") + '">Stop and ask me</button><button class="btn mini" data-other="' + esc(x.id) + ':continue" aria-pressed="' + (x.otherwise === "continue") + '">Skip it and continue</button></div>' +
      '<div class="note">Missing information never counts as a yes. The GM takes a case only when Aero has seen or heard enough to settle it.</div>';
    return h + "</div>";
  }
  function traceMaps(c, r) {
    var now = { hands: c.hands || null, position: c.position_label || null, flags: c.state_flags || [] }, at = {}, prev = {}, last = now;
    (r.trace || []).forEach(function (t) { at[t.step_id] = t; prev[t.step_id] = last; last = t; });
    return { now: now, at: at, prev: prev };
  }
  function renderPlan(c, s, r, stat) {
    var tr = traceMaps(c, r), haltId = (r.halts || []).length && r.steps[r.halts[0]] ? r.steps[r.halts[0]].id : null;
    var h = '<div class="plan" id="planTop" aria-label="Your plan">';
    if (ui.carried) h += '<div class="check warn"><b>The scene changed while you were planning.</b><div>Your steps are kept and re-checked against what Aero sees now. Steps that no longer fit are marked.</div></div>';
    for (var q = 0; q < s.nseq; q++) {
      var on = !s.active.branch && s.active.seq === q, rows = s.steps.filter(function (x) { return (x.seq || 0) === q; });
      h += '<section class="seqcard' + (on ? " active" : "") + '" aria-label="Sequence ' + (q + 1) + '"><div class="seqhead"><b>Sequence ' + (q + 1) + "</b>" +
        '<input class="txt seqlbl" id="w_lbl_' + q + '" aria-label="Name of sequence ' + (q + 1) + '" placeholder="Name (optional)" value="' + esc(s.labels[q] || "") + '">' +
        '<button class="btn mini" data-act-seq="' + q + '" aria-pressed="' + on + '">' + (on ? "Adding here" : "Add here") + "</button>" +
        (s.nseq > 1 ? '<button class="btn mini" data-del-seq="' + q + '"' + (rows.length ? ' disabled title="Move or remove its steps first"' : "") + ' aria-label="Remove empty sequence ' + (q + 1) + '">✕</button>' : "") + "</div>";
      if (!rows.length) h += '<div class="note">Empty. ' + (on ? "Choose from the palette below." : "Tap “Add here”, then choose from the palette.") + "</div>";
      h += '<ol class="steps">' + rows.map(function (x) {
        return (x.id === haltId ? '<li class="halt" role="note">⏸ The GM stops here and asks you, unless what Aero already knows settles it. Nothing after this runs until you decide.</li>' : "") + stepRow(c, s, x, stat, tr, false);
      }).join("") + "</ol></section>";
    }
    return h + '<button class="btn" id="addSeq">+ Sequence</button><div class="note">A new sequence is only a visual group: the GM keeps going through it in the same pass. Every step can be interrupted by the world.</div></div>';
  }
  function activeWhere(s) {
    if (s.active && s.active.branch) { var f = locate(s.active.branch); if (f && f.list[f.index].cases && f.list[f.index].cases[s.active["case"]]) return { branch: s.active.branch, "case": s.active["case"] }; }
    return { seq: Math.max(0, Math.min(s.active && s.active.seq != null ? s.active.seq : 0, s.nseq - 1)) };
  }
  function palBtn(key, label, small, a, count) {
    var stt = a ? a.status : "ok", dis = stt === "needs_step" || stt === "needs_choice" || stt === "not_here";
    var h = '<div class="pal st-' + stt + '"><button class="palbtn" data-pal="' + esc(key) + '"' + (dis ? " disabled" : "") + '><span class="ico" aria-hidden="true">' + PICO[stt] + '</span><span class="lbl">' + esc(label) +
      (count ? ' <span class="tag">added ×' + count + "</span>" : "") + (small ? "<small>" + esc(small) + "</small>" : "") +
      (PTXT[stt] ? '<small class="why">' + esc(PTXT[stt] + (a.reasons && a.reasons[0] ? ": " + a.reasons[0] : "")) + "</small>" : "") + "</span></button>";
    if (stt === "needs_step") h += (a.suggest || []).map(function (g) { return '<button class="btn mini pre" data-pre="' + esc(g.type + ":" + g.option) + '">Add “' + esc(g.label) + '” first</button>'; }).join("");
    if (stt === "needs_choice") h += '<button class="btn mini pre" data-how="' + esc(label) + '">Say how (custom action)</button>';
    return h + "</div>";
  }
  function customEditor(c, s) {
    var d = s.actX || {}, gear = (c.equipment || []).filter(function (e) { return !e.fixed; });
    var h = '<div class="ed" id="pg_custom"><label for="w_act">Custom action (anything the list does not cover; your exact words go to the GM)</label><textarea id="w_act" rows="2" placeholder="e.g. Tie the syntherope into a harness so the torch and bottles ride on my back">' + esc(s.actDraft) + "</textarea>" +
      '<details class="howto"' + (d.open ? " open" : "") + ' id="actHow"><summary>Method, tools and result (optional)</summary>' +
      '<label for="w_how">How Aero does it</label><textarea id="w_how" rows="1" placeholder="e.g. a sling over both shoulders, bottles lashed back to back">' + esc(d.method || "") + "</textarea>";
    if (gear.length) h += '<div class="note">Using (only what Aero has):</div><div class="usegrid">' + gear.map(function (e) {
      var on = (d.uses || []).indexOf(e.id) >= 0;
      return '<label class="opt"><input type="checkbox" data-use="' + esc(e.id) + '"' + (on ? " checked" : "") + '><span class="lbl">' + esc(e.label) + "<small>" + esc((STATEWORD[e.state] || e.state) + (e.where ? ", " + e.where : "")) + "</small></span></label>" +
        (on ? '<select class="txt" data-after-use="' + esc(e.id) + '" aria-label="Afterwards, ' + esc(e.label) + '"><option value="">afterwards: no change</option>' + ["held", "worn", "attached", "stored", "placed", "transported"].map(function (st) { return '<option value="' + st + '"' + (d.after && d.after[e.id] === st ? " selected" : "") + ">afterwards: " + STATEWORD[st] + "</option>"; }).join("") +
          gear.filter(function (b) { return b.capacity && b.id !== e.id; }).map(function (b) { var v = "in:" + b.id; return '<option value="' + esc(v) + '"' + (d.after && d.after[e.id] === v ? " selected" : "") + ">afterwards: into " + esc(b.label) + "</option>"; }).join("") + "</select>" : "");
    }).join("") + "</div>";
    h += '<label for="w_on">On / at</label><select class="txt" id="w_on"><option value="">(nothing in particular)</option>' + (c.visible || []).map(function (v) { return '<option value="' + esc(v.id) + '"' + (d.target === v.id ? " selected" : "") + ">" + esc(v.label) + "</option>"; }).join("") + "</select>" +
      '<label for="w_hands">Hands it needs</label><select class="txt" id="w_hands"><option value="">let the builder work it out</option>' + [0, 1, 2].map(function (n) { return '<option value="' + n + '"' + (String(d.hands) === String(n) ? " selected" : "") + ">" + n + "</option>"; }).join("") + "</select>" +
      '<label for="w_makes">Makes, if it works</label><input class="txt" id="w_makes" placeholder="e.g. a rope harness" value="' + esc(d.makes || "") + '">' +
      '<select class="txt" id="w_makes_state" aria-label="Where the result ends up">' + ["worn", "attached", "held", "placed", "transported"].map(function (st) { return '<option value="' + st + '"' + ((d.makes_state || "worn") === st ? " selected" : "") + ">it ends up " + STATEWORD[st] + "</option>"; }).join("") + "</select>" +
      '<div class="note">The GM decides whether the method works, how long it takes and whether the result holds. Nothing is assumed.</div></details>' +
      '<button class="btn" id="addAct">Add action</button></div>';
    return h;
  }
  function gearGroup(c, by) {  // Aero's own gear, at this point of the plan: only what can actually be done with it
    var items = (c.objects || []).filter(function (o) { var a = by["object:" + o.id]; return o.gear && (!a || a.status !== "not_here"); });
    if (!items.length) return "";
    return '<details class="palgrp" id="pg_gear"' + (ui.gearOpen ? " open" : "") + '><summary><h3 style="display:inline">Gear (' + items.length + ')</h3></summary><div class="palgrid">' + items.map(function (o) { return palBtn("object:" + o.id, o.label, o.detail, by["object:" + o.id]); }).join("") + "</div></details>";
  }
  function renderPalette(c, s, d) {
    var w = activeWhere(s), av = safeAvail(d, c, w), by = {};
    av.forEach(function (a) { by[a.type + ":" + a.option] = a; });
    var where = w.branch ? (function () { var f = locate(w.branch), k = f.list[f.index].cases[w["case"]]; return (w["case"] ? "Else if " : "If ") + (k.when || "…") + " (Sequence " + ((f.list[f.index].seq || 0) + 1) + ")"; })()
      : "Sequence " + (w.seq + 1) + (s.labels[w.seq] ? " · " + s.labels[w.seq] : "");
    function used(id) { var n = 0; T.flat(s.steps).forEach(function (x) { if (x.type === "speech" && x.option === id) n++; }); return n; }
    function grp(title, items, id) { return items.length ? '<div class="palgrp"' + (id ? ' id="' + id + '"' : "") + "><h3>" + title + '</h3><div class="palgrid">' + items.join("") + "</div></div>" : ""; }
    var acts = (c.options || []).filter(function (o) { return o.slot === "action"; }), bon = (c.options || []).filter(function (o) { return o.slot === "bonus_action"; });
    var nav = '<nav class="palnav" aria-label="Palette sections">' + [["↑ Plan", "planTop"], ["Say", "pg_say"], ["Do", "pg_do"], ["Go", "pg_go"], ["Handle", "pg_handle"], ["Gear", "pg_gear"], ["Custom", "pg_custom"]].map(function (x) { return '<a class="chip mini" href="#' + x[1] + '">' + x[0] + "</a>"; }).join("") + "</nav>";
    var h = '<fieldset class="grp palette" id="palette"><legend>Add to: ' + esc(where) + "</legend>" + nav +
      '<div class="note added" id="lastAdded" role="status" aria-live="polite">' + esc(ui.lastAdded || "") + "</div>" +
      '<div class="note">Everything Aero could try right now. Greyed-out choices say what is missing at that point in your plan; nothing is added unless you tap it.</div>' +
      grp("Say", (c.dialogue || []).map(function (dl) { return palBtn("speech:" + dl.id, "“" + dl.text + "”", dl.approach + (dl.extended ? " · extended" : ""), { status: "ok" }, used(dl.id)); }), "pg_say") +
      '<div class="ed"><label for="w_say">Your own line (line breaks are kept)</label><textarea id="w_say" rows="2" placeholder="What Aero says">' + esc(s.sayDraft) + '</textarea><button class="btn" id="addSay">Add line</button></div>' +
      grp("Do", acts.map(function (o) { return palBtn("action:" + o.id, o.label, o.detail, by["action:" + o.id]); }), "pg_do") +
      grp("Quick (bonus)", bon.map(function (o) { return palBtn("bonus_action:" + o.id, o.label, o.detail, by["bonus_action:" + o.id]); })) +
      grp("Go", (c.movement || []).filter(function (m) { return m.id !== "hold"; }).map(function (m) { return palBtn("move:" + m.id, m.label, m.feet ? "~" + m.feet + " ft" : "", by["move:" + m.id]); }), "pg_go") +
      grp("Handle", (c.objects || []).filter(function (o) { return !o.gear; }).map(function (o) { return palBtn("object:" + o.id, o.label, o.detail, by["object:" + o.id]); }), "pg_handle") +
      gearGroup(c, by) +
      customEditor(c, s) +
      (w.branch ? "" : '<button class="btn" id="addBranch">Add a decision (if / else if / otherwise)</button>');
    return h + "</fieldset>";
  }
  var STOPTXT = { combat: "Interrupted: initiative has begun", consequential: "Stopped: something needs your decision", mechanical: "Stopped by what happened",
                  prerequisite: "Stopped: a step did not work out", condition: "Paused: waiting on your decision", complete: "Plan complete" };
  /* What happened to the plan, in the player's terms. Statuses come from planProgress (GM side):
     interrupted · paused · unattempted · suspended can be continued (after a new, explicit authorization);
     blocked · cancelled cannot. */
  var GROUPS = [["interrupted", "Interrupted while it was happening", true], ["paused", "Paused: waiting on your decision", true], ["unattempted", "Not attempted yet", true],
                ["pending", "Not done yet", true], ["suspended", "Set aside until the fight is over", true], ["blocked", "Blocked: what it needed did not happen", false], ["cancelled", "Cancelled by what happened", false], ["invalidated", "Cancelled by what happened", false]];
  function continuable(c, x) { var st = x.status || "pending"; return T.CONTINUABLE.indexOf(st) >= 0 && !(st === "suspended" && !sceneMode(c)); }
  function renderPending(c) {
    var ps = c.pending_steps || [], pr = c.plan_result || null;
    if (!ps.length && !(pr && pr.stop_kind && pr.stop_kind !== "complete")) return "";
    function lbl(x) { return (x.condition && x.condition.text ? "Only if " + x.condition.text.replace(/^\s*(only\s+)?if\s+/i, "") + ": " : "") + (x.type === "speech" && x.text ? "Say: “" + x.text + "”" : x.type === "free" ? "Try: " + x.text : stepLabel(c, x)); }
    var h = '<div class="check warn interrupt" style="margin-top:8px"><b>' + esc(pr ? (STOPTXT[pr.stop_kind] || "Not done yet") : "Not done yet") + "</b>" + (c.pending_reason || (pr && pr.reason) ? "<div>" + esc(c.pending_reason || pr.reason) + "</div>" : "");
    if (pr && pr.completed) h += '<div class="note">' + (pr.completed > 1 ? pr.completed + " steps of your plan happened and are" : "1 step of your plan happened and is") + " in the story.</div>";
    GROUPS.forEach(function (g) {
      var xs = ps.filter(function (x) { return (x.status || "pending") === g[0]; });
      if (!xs.length) return;
      h += '<div class="note grp-' + g[0] + '"><b>' + g[1] + "</b>" + (g[2] ? "" : " (these cannot be continued)") + '</div><ol class="' + (g[2] ? "live" : "dead") + '">' + xs.map(function (x) { return "<li>" + esc(lbl(x)) + "</li>"; }).join("") + "</ol>";
    });
    var can = ps.filter(function (x) { return continuable(c, x); });
    if (can.length) h += sceneMode(c) ? '<button class="btn" id="continuePending">Continue these steps</button><div class="note">Nothing resumes on its own. Continue puts them back in your plan, checked against what Aero sees now; they run only if you submit again.</div>'
                                      : '<div class="note">Initiative has started. Choose your combat turn; set-aside steps can be continued once the fight is over.</div>';
    return h + "</div>";
  }
  function combatAvail(c) {  // per option, with the current action/move taken out (a radio replaces it)
    var d = declaration(c), base = JSON.parse(JSON.stringify(d)); base.actions = []; base.movement = null; delete base.steps;
    var out = {}; safeAvail(base, c, null).forEach(function (a) { out[a.type + ":" + a.option] = a; });
    return out;
  }

  function renderTurn(v) {
    var c = ctxOf(v), busy = activeAction();
    if (!c) return renderLegacy(v, busy);
    var d = declaration(c), r = safeValidate(d, c), s = ui.sel, scene = sceneMode(c), stat = safeStatus(r);
    window.__lastValidation = r;
    var dis = busy ? " disabled" : "";
    var h = '<div class="panel composer"><div class="row" style="justify-content:space-between"><h2 style="margin:0">' + esc(c.actor_name || "Aero") + "’s turn" + (c.mode === "combat" ? " · round " + esc(c.round) : "") + "</h2>" +
      '<div class="seg" role="group" aria-label="Compose mode"><button data-mode="build" aria-pressed="' + (ui.mode === "build") + '">Build</button><button data-mode="write" aria-pressed="' + (ui.mode === "write") + '">Write</button></div></div>' +
      budget(c, r) + renderPending(c) + ((c.notes || []).length ? '<div class="check warn" style="margin-top:8px"><b>What you notice</b>' + c.notes.map(function (n) { return "<div>" + esc(n) + "</div>"; }).join("") + "</div>" : "") +
      (scene ? renderNow(c) : "") + "<fieldset" + dis + ' style="border:0;margin:0;padding:0;min-width:0">';
    if (ui.mode === "write") {
      h += '<textarea id="w_write" placeholder="Describe the whole plan in your own words, in order. Put speech in quotes." style="margin-top:10px">' + esc(ui.write) + "</textarea>" +
        '<div class="note" id="readAs">Read as: ' + esc(r.preview.map(function (p) { return p.text; }).join(" → ") || "nothing matched yet") + "</div>" + readAsSteps(c, r, stat) +
        (scene && ui.write.trim() ? '<button class="btn" id="editAsSteps">Edit as steps</button>' : "");
    } else if (scene) {
      h += renderPlan(c, s, r, stat) + renderPalette(c, s, d);
      if ((c.reactions || []).length) h += '<fieldset class="grp"><legend>Reactions (if triggered)</legend>' + c.reactions.map(function (o) { return check("reactions", o.id, s.reactions.indexOf(o.id) >= 0, o.label, "if " + o.trigger); }).join("") + "</fieldset>";
    } else {
      var ca = combatAvail(c);
      function why(k) { var a = ca[k]; return a && /needs_step|needs_choice|not_here/.test(a.status) ? [true, (PTXT[a.status] + (a.reasons[0] ? ": " + a.reasons[0] : ""))] : [false, ""]; }
      h += '<fieldset class="grp"><legend>Dialogue</legend>' + (c.dialogue || []).map(function (o) { return radio("dialogue", o.id, s.dialogue === o.id, "“" + o.text + "”", o.approach + (o.extended ? " · extended, uses your action" : "")); }).join("") +
        radio("dialogue", "silent", s.dialogue === "silent", "Remain silent") + radio("dialogue", "own", s.dialogue === "own", "Write my own line") +
        (s.dialogue === "own" ? '<input class="txt" id="w_own" placeholder="What Aero says" value="' + esc(s.own) + '">' : "") + "</fieldset>";
      h += '<fieldset class="grp"><legend>Primary action</legend>' + radio("action", "", !s.action, "No action") +
        (c.options || []).filter(function (o) { return o.slot === "action"; }).map(function (o) {
          var tag = (o.requires || []).length ? "needs " + o.requires.map(function (q) { return (c.flag_labels || {})[q] || q; }).join(", ") : "", w = why("action:" + o.id);
          var x = radio("action", o.id, s.action === o.id, o.label, o.detail || (o.area_ft ? o.area_ft + "-ft radius" : o.reach_ft ? "reach " + o.reach_ft + " ft" : ""), tag, w[0], w[1]);
          if (s.action === o.id && o.needs_target) x += '<select class="txt" id="w_target" aria-label="Target"><option value="">Choose a target</option>' + (c.visible || []).map(function (t) { return '<option value="' + esc(t.id) + '"' + (s.target[o.id] === t.id ? " selected" : "") + ">" + esc(t.label) + " (~" + t.distance_ft + " ft)</option>"; }).join("") + "</select>";
          if (s.action === o.id && o.needs_trigger) x += '<input class="txt" id="w_trigger" placeholder="Trigger: ' + esc(o.default_trigger || "") + '" value="' + esc(s.trigger) + '">';
          return x;
        }).join("") + "</fieldset>";
      var bon = (c.options || []).filter(function (o) { return o.slot === "bonus_action"; });
      if (bon.length) h += '<fieldset class="grp"><legend>Bonus action</legend>' + radio("bonus", "", !s.bonus, "None") + bon.map(function (o) { return radio("bonus", o.id, s.bonus === o.id, o.label, o.detail); }).join("") + "</fieldset>";
      h += '<fieldset class="grp"><legend>Movement</legend>' + (c.movement || []).map(function (m) {
        var risk = c.mode === "combat" && (m.leaves_reach_of || []).length ? "opportunity attack risk" : "", w = m.id === "hold" ? [false, ""] : why("move:" + m.id);
        return radio("movement", m.id, s.movement === m.id, m.label, m.feet && !/\d\s*(ft|m)\b/.test(m.label) ? "~" + m.feet + " ft" : "", risk, w[0], w[1]);
      }).join("") + "</fieldset>";
      if ((c.objects || []).length) h += '<fieldset class="grp"><legend>Object interaction</legend>' + c.objects.map(function (o) { return check("objects", o.id, s.objects.indexOf(o.id) >= 0, o.label, "first one each turn is free"); }).join("") + "</fieldset>";
      if ((c.reactions || []).length) h += '<fieldset class="grp"><legend>Reactions (if triggered)</legend>' + c.reactions.map(function (o) { return check("reactions", o.id, s.reactions.indexOf(o.id) >= 0, o.label, "if " + o.trigger); }).join("") + "</fieldset>";
      h += '<textarea id="w_note" placeholder="Anything else Aero does (optional). The GM checks it against the same rules." style="margin-top:10px;min-height:60px">' + esc(ui.note) + "</textarea>";
    }
    h += "</fieldset>" + '<div id="liveCheck">' + checkPanel(r) + "</div>";
    h += '<div class="submitbar' + (scene ? " sticky" : "") + '" id="submitBar">' + submitBar(r, stat, busy) + "</div>" +
      (busy ? '<div class="note">One turn at a time: the current one is with the GM.</div>' : "") + renderActions() + "</div>";
    return h;
  }
  function canSubmitNow(r, busy) {
    return !busy && status === "live" && r.legal && (!r.needs_confirmation || ui.confirmed) && (r.preview.length || (ui.mode === "write" && ui.write.trim()) || ui.note.trim());
  }
  function fixCount(r, stat) {
    var n = r.errors.filter(function (e) { return !e.step_id; }).length;
    Object.keys(stat).forEach(function (k) { if (stat[k].status === "fix") n++; });
    return n;
  }
  function submitBar(r, stat, busy) {
    var n = fixCount(r, stat), ok = canSubmitNow(r, busy) && !phase;
    var scene = sceneMode(ctxOf(view)) && ui.mode !== "write";
    return (n ? '<button class="btn" id="jumpFix">' + n + " to fix ↑</button>" : "") + (scene ? '<a class="btn only-phone" href="#palette" id="jumpAdd">+ Add</a>' : "") +
      '<button class="btn primary" id="submitTurn"' + (ok ? "" : " disabled") + ">" + (phase === "validating" ? "Submitting…" : sceneMode(ctxOf(view)) ? "Submit plan" : "Submit turn") + "</button>" +
      '<button class="btn" id="clearTurn"' + (busy ? " disabled" : "") + '>Clear</button><span class="note" id="msg"></span>';
  }
  function readAsSteps(c, r, stat) { return '<div id="readAsSteps">' + readAsInner(c, r, stat) + "</div>"; }
  function readAsInner(c, r, stat) {
    if (!r.steps || !r.steps.length) return "";
    return '<ol class="steps readas">' + T.flat(r.steps).filter(function (x) { return x.type !== "branch"; }).map(function (x) {
      var st = stat[x.id] || { status: "ok", messages: [] };
      return '<li class="step st-' + st.status + '"><div class="srow"><span class="ico" aria-label="' + STXT[st.status] + '">' + ICON[st.status] + '</span><span class="lbl">' + esc(stepLabel(c, x)) + "</span></div>" +
        (st.status !== "ok" ? st.messages.map(function (m) { return '<div class="' + (st.status === "fix" ? "msg-err" : "note") + '">' + esc(m) + "</div>"; }).join("") : "") + "</li>";
    }).join("") + "</ol>";
  }

  function renderLegacy(v, busy) {
    return '<div class="panel composer"><h2>Your action</h2>' +
      '<textarea id="w_write" placeholder="What does Aero do or say? Anything is allowed." ' + (busy ? "disabled" : "") + ">" + esc(ui.write) + "</textarea>" +
      '<div class="row" style="margin-top:8px"><button class="btn primary" id="submitTurn" ' + (busy || !ui.write.trim() || status !== "live" || phase ? "disabled" : "") + ">Submit turn</button>" +
      '<span class="note" id="msg"></span></div><div class="note" style="margin-top:6px">No turn options are published for this moment; the GM reads your text directly.</div>' + renderActions() + "</div>";
  }

  function ago(ms) { var s = Math.max(0, Math.round((Date.now() - ms) / 1000)); return s < 90 ? s + " s" : Math.round(s / 60) + " min"; }
  function notifyLine(a) {
    var n = notifyState[a._id];
    if (!n) return "";
    if (n.state === "sending") return '<div class="note">Starting the GM…</div>';
    if (n.ok) return '<div class="note">GM started ' + ago(n.at) + " ago. The result appears here by itself.</div>";
    var why = { approval_required: "The Datapad needs your permission to start the GM. Tap Start GM and choose Allow.", not_in_manifest: "Starting the GM is not allowed for this page. Allow Claude Code Remote in the page permissions.",
      server_not_connected: "Claude Code Remote is not available to this page.", mcp_unavailable: "This view cannot start the GM automatically.", no_processor: "This campaign has no automatic GM." }[n.code] || ("Could not start the GM (" + n.code + ").");
    return '<div class="note msg-warn">' + esc(why) + " Your turn is saved either way; sending any message in the chat also works.</div>";
  }
  function renderActions() {
    if (!actions.length) return "";
    return actions.slice(0, 3).map(function (a) {
      var pills = { submitted: '<span class="pill pend">Submitted</span>', processing: '<span class="pill pend">Processing</span>', committed: '<span class="pill ok">Committed' + (a.event_id ? " · " + esc(a.event_id) : "") + "</span>",
        needs_revision: '<span class="pill" style="color:var(--bad);border-color:var(--bad)">Needs revision</span>', failed: '<span class="pill" style="color:var(--bad);border-color:var(--bad)">Failed</span>', clarify: '<span class="pill pend">Needs revision</span>' };
      var h = '<div class="act"><div class="row">' + (pills[a.status] || '<span class="pill">' + esc(a.status) + "</span>");
      if (a.status === "submitted") h += ' <button class="btn" data-wd="' + esc(a._id) + '" style="min-height:32px;padding:2px 10px">Withdraw</button> <button class="btn" data-nudge="' + esc(a._id) + '" style="min-height:32px;padding:2px 10px">Start GM</button>';
      var stuck = a.status === "processing" && a.processing && Date.now() - a.processing.started_ms > 15 * 60000;
      if (stuck || a.status === "failed") h += ' <button class="btn" data-nudge="' + esc(a._id) + '" style="min-height:32px;padding:2px 10px">Retry</button>';
      h += "</div><q>" + esc(a.text) + "</q>";
      if (a.status === "submitted") h += notifyLine(a);
      if (a.status === "processing") h += '<div class="note">' + (stuck ? "Taking longer than expected. Retry is safe: the GM never resolves a turn twice." : "The GM is resolving this turn" + (a.processing ? " (" + ago(a.processing.started_ms) + ")" : "") + ". Nothing is part of the story until it is committed.") + "</div>";
      if (a.status === "needs_revision" && a.review) {
        h += '<div class="note msg-err">' + esc(a.review.summary || "") + "</div>";
        var rmsg = function (x) { return typeof x === "string" ? x : (x && x.message) || ""; };
        (a.review.errors || []).forEach(function (x) { h += '<div class="msg-err">' + esc(rmsg(x)) + "</div>"; });
        (a.review.warnings || []).forEach(function (x) { h += '<div class="msg-warn">' + esc(rmsg(x)) + "</div>"; });
        if ((a.review.alternatives || []).length) h += '<div class="sugg">' + a.review.alternatives.map(function (x, i) { return '<button class="chip" data-ralt="' + esc(a._id) + ":" + i + '">' + esc(x.label) + "</button>"; }).join("") + "</div>";
        h += '<div class="note">No dice were rolled. Revise and submit again.</div>';
      }
      if (a.status === "failed") h += '<div class="note msg-err">' + esc(a.error || "Processing failed. Nothing was narrated.") + "</div>";
      return h + "</div>";
    }).join("");
  }

  function renderUsage(v) {
    var mine = usage.filter(function (u) { return u.campaign_id === v.campaign_id; });
    if (!mine.length) return "";
    var mins = mine.reduce(function (t, u) { return t + Math.max(0, (u.finished_ms || u.started_ms) - u.started_ms); }, 0) / 60000;
    var by = {}; mine.forEach(function (u) { by[u.outcome] = (by[u.outcome] || 0) + 1; });
    return '<div class="panel"><h2>Cloud GM usage</h2><div class="kv"><span>Sessions (latest 50)</span><span>' + mine.length + '</span></div><div class="kv"><span>Total run time</span><span>' + mins.toFixed(1) + ' min</span></div>' +
      '<div class="note" style="margin-top:6px">' + Object.keys(by).map(function (k) { return esc(k.replace("_", " ")) + " " + by[k]; }).join(" · ") + "</div>" + renderPerf(mine) + "</div>";
  }
  /* Read-only performance view from the processor's own usage records (measured marks; nothing is
     written and no model is called). Not authoritative: marks are taken at the next shell call. */
  var PHASES = [["1_submit_to_worker_start_ms", "Submit → GM start"], ["2_session_init_ms", "Session start"], ["4a_lock_and_claim_ms", "Lock + claim"],
    ["3_context_loading_ms", "Reading + thinking"], ["4_preflight_and_rules_ms", "Preflight + rules"], ["5_dice_ms", "Dice"], ["6_ledger_ms", "Ledger"],
    ["7_narration_ms", "Narration"], ["9_git_sync_ms", "Git push"], ["8_projection_ms", "Datapad update"], ["submit_to_visible_ms", "Submit → visible"]];
  function renderPerf(mine) {
    var done = mine.filter(function (u) { return u.outcome === "committed" && u.timings; }).sort(function (a, b) { return b.started_ms - a.started_ms; }).slice(0, 10);
    if (!done.length) return "";
    function sec(ms) { return ms == null ? "—" : (ms / 1000).toFixed(ms < 10000 ? 1 : 0) + " s"; }
    function med(k) { var v = done.map(function (u) { return u.timings[k]; }).filter(function (x) { return typeof x === "number"; }).sort(function (a, b) { return a - b; });
      return v.length ? (v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2) : null; }
    var last = done[0].timings;
    return '<details class="perf" style="margin-top:8px"><summary>Turn timing · last ' + sec(last.submit_to_visible_ms) + " · median " + sec(med("submit_to_visible_ms")) + "</summary>" +
      '<table class="kvt"><thead><tr><th>Phase</th><th>Last</th><th>Median (' + done.length + ")</th></tr></thead><tbody>" +
      PHASES.map(function (p) { return "<tr><td>" + esc(p[1]) + "</td><td>" + sec(last[p[0]]) + "</td><td>" + sec(med(p[0])) + "</td></tr>"; }).join("") + "</tbody></table>" +
      '<div class="note">' + (typeof last.model_ms === "number" ? "Last turn: model " + sec(last.model_ms) + ", tools " + sec(last.tool_ms) + ", " + (last.model_calls || 0) + " model calls, " + (last.tool_calls || 0) + " tool calls, " + Math.round((last.output_tokens || 0) / 1000) + "K output tokens. " : "") +
      "Measured by the GM worker; phases absorb the thinking before each mark. Read-only, not part of the story.</div></details>";
  }
  function renderDice(v) {
    if (!v.rolls || !v.rolls.length) return "";
    return '<div class="panel"><h2>Dice · last turn</h2><ul class="plain dice">' + v.rolls.map(function (r) { return "<li><div>" + esc(r.purpose) + '</div><div class="kv"><span class="note">' + esc(r.by === "gm" ? "GM" : "You") + "</span><span>" + esc(r.summary) + "</span></div></li>"; }).join("") + "</ul></div>";
  }

  function renderCenter(v) {
    var s = v.scene;
    var feed = v.feed.map(function (f) {
      return '<div class="' + (f.who === "player" ? "you" : "gm") + '"><div class="meta">' + (f.who === "player" ? "Aero · " : "Narrator · ") + esc(f.time) + "</div>" + paras(f.text) + "</div>";
    }).join("");
    return '<div class="panel hdr"><div class="mirror"><span class="pill">Ledger mirror · read only</span><span>rev ' + v.revision + " · " + esc(v.ledger_head) + " · turn " + v.turn_no + "</span></div>" +
      '<h1 style="margin-top:8px">' + esc(s.title) + '</h1><div class="sub"><span>' + esc(s.location) + "</span><span>" + esc(s.time) + "</span></div>" +
      '<div class="tags">' + s.atmosphere.map(function (a) { return "<span>" + esc(a) + "</span>"; }).join("") + "</div></div>" +
      '<div class="panel"><h2>Narrative</h2><div class="feed">' + (feed || '<div class="empty">The scene has not been narrated.</div>') + "</div></div>" +
      renderDice(v) + renderTurn(v);
  }

  function render() {
    var ae = document.activeElement, keep = ae && ae.id && /^w_/.test(ae.id) ? { id: ae.id, s: ae.selectionStart, e: ae.selectionEnd } : null;
    if (!view) {
      $("colCenter").innerHTML = '<div class="panel"><h2>Genesis Datapad</h2><div class="empty">' + (status === "unavailable" ? "The campaign store is not reachable from this view. Open the page while signed in to Claude." : status === "error" ? esc(err) : "Connecting to the campaign ledger…") + "</div></div>";
      return;
    }
    syncCtx();
    $("colLeft").innerHTML = renderLeft(view.character, view);
    $("colGear").innerHTML = renderGear(view.character, view);
    $("colRight").innerHTML = renderRecord(view);
    $("colCenter").innerHTML = renderCenter(view);
    Array.prototype.forEach.call(document.querySelectorAll(".member-sel"), function (el) {
      el.addEventListener("change", function () { selId = el.value; ls("datapad.member", selId); render(); });
    });
    bindCenter();
    if (keep && $(keep.id)) { var el = $(keep.id); try { el.focus({ preventScroll: true }); } catch (x) { el.focus(); } try { el.setSelectionRange(keep.s, keep.e); } catch (x) {} }
    watchNewest();
  }

  /* ---------- interaction ---------- */
  function setMsg(t) { var m = $("msg"); if (m) m.textContent = t; }
  function changed() { ui.confirmed = false; ui.draftId = ""; ui.carried = false; saveUi(); render(); ui.lastAdded = ""; }
  function sortSeq() {
    var L = ui.sel.steps.map(function (x, i) { return [x, i]; });
    L.sort(function (a, b) { return (a[0].seq || 0) - (b[0].seq || 0) || a[1] - b[1]; });
    ui.sel.steps = L.map(function (p) { return p[0]; });
  }
  function moveStep(id, dir) {
    var f = locate(id); if (!f) return;
    var L = f.list, i = f.index, x = L[i], j = i + dir;
    if (f.parent) { if (j < 0 || j >= L.length) return; L.splice(j, 0, L.splice(i, 1)[0]); return; }
    var nb = L[j];
    if (nb && (nb.seq || 0) === (x.seq || 0)) { L[i] = nb; L[j] = x; return; }
    var ns = (x.seq || 0) + dir; if (ns < 0 || ns >= ui.sel.nseq) return;  // across a sequence boundary
    x.seq = ns; sortSeq();
  }
  function makeStep(key) {
    var k = key.indexOf(":"), t = key.slice(0, k), id = key.slice(k + 1), st = { id: newId(), type: t, option: id };
    if (t === "action" || t === "bonus_action") { st.target = null; st.trigger = null; }
    return st;
  }
  function addAtActive(st) {
    var w = activeWhere(ui.sel), out = T.insertStep(ui.sel.steps, w, st);
    ui.sel.steps = out;
    var c = ctxOf(view), where = w.branch ? "this decision" : "Sequence " + (w.seq + 1);
    ui.lastAdded = "Added to " + where + ": " + (c ? stepLabel(c, st) : st.type) + ".";
  }
  function bindCenter() {
    function on(id, ev, fn) { var el = $(id); if (el) el.addEventListener(ev, fn); }
    function each(sel, fn) { Array.prototype.forEach.call(document.querySelectorAll(sel), fn); }
    function click(attr, fn) { each("[" + attr + "]", function (b) { b.addEventListener("click", function () { fn(b.getAttribute(attr), b); }); }); }
    var deb = null;
    function soft(fn) { return function (e) { fn(e.target.value); ui.confirmed = false; ui.draftId = ""; autoGrow(e.target); clearTimeout(deb); deb = setTimeout(function () { saveUi(); refreshLive(); }, 250); }; }
    each("[data-mode]", function (b) { b.addEventListener("click", function () { ui.mode = b.getAttribute("data-mode"); changed(); }); });
    each("input[data-g]", function (el) { el.addEventListener("change", function () { ui.sel[el.getAttribute("data-g")] = el.value; changed(); }); });
    each("input[data-c]", function (el) {
      el.addEventListener("change", function () {
        var g = el.getAttribute("data-c"), list = ui.sel[g].filter(function (x) { return x !== el.value; });
        if (el.checked) list.push(el.value); ui.sel[g] = list; changed();
      });
    });
    on("w_target", "change", function () { ui.sel.target[ui.sel.action] = $("w_target").value; changed(); });

    /* scene plan: every change is the player's explicit tap; nothing is added, removed or reordered otherwise */
    click("data-pal", function (key) {
      if (key.indexOf("speech:") === 0) addAtActive({ id: newId(), type: "speech", option: key.slice(7) });
      else addAtActive(makeStep(key));
      changed();
    });
    click("data-pre", function (key) { addAtActive(makeStep(key)); changed(); });
    click("data-fix", function (v) {
      var p = v.split("|"), f = locate(p[0]); if (!f) return;
      var st = makeStep(p[1]); st.seq = f.list[f.index].seq; f.list.splice(f.index, 0, st); changed();
    });
    click("data-how", function (label) {
      ui.sel.actDraft = (ui.sel.actDraft ? ui.sel.actDraft + "\n" : "") + "How Aero does it (" + label + "): ";
      saveUi(); render(); var t = $("w_act"); if (t) { t.focus(); try { t.setSelectionRange(t.value.length, t.value.length); } catch (x) {} t.scrollIntoView({ block: "center" }); }
    });
    on("addSay", "click", function () { var t = $("w_say") ? $("w_say").value : ""; if (!t.trim()) return; addAtActive({ id: newId(), type: "speech", text: t.replace(/\s+$/, "") }); ui.sel.sayDraft = ""; changed(); });
    on("addAct", "click", function () {
      var t = $("w_act") ? $("w_act").value : ""; if (!t.trim()) return;
      var d = ui.sel.actX || {}, st = { id: newId(), type: "free", text: t.replace(/\s+$/, ""), kind: "custom" };
      if (d.method && d.method.trim()) st.method = d.method.replace(/\s+$/, "");
      if ((d.uses || []).length) st.uses = d.uses.slice();
      if (d.target) st.targets = [d.target];
      if (d.hands !== undefined && d.hands !== "") st.hands = +d.hands;
      var ch = Object.keys(d.after || {}).filter(function (k) { return d.after[k] && (d.uses || []).indexOf(k) >= 0; }).map(function (k) {
        var v = d.after[k]; return /^in:/.test(v) ? { item: k, to: "attached", in: v.slice(3) } : { item: k, to: v }; });
      if (ch.length) st.equipment_changes = ch;
      if (d.makes && d.makes.trim()) st.creates = { label: d.makes.trim(), state: d.makes_state || "worn" };
      addAtActive(st); ui.sel.actDraft = ""; ui.sel.actX = {}; changed();
    });
    function actx() { ui.sel.actX = ui.sel.actX || {}; return ui.sel.actX; }
    on("actHow", "toggle", function (e) { actx().open = e.target.open; saveUi(); });
    on("pg_gear", "toggle", function (e) { ui.gearOpen = e.target.open; saveUi(); });
    on("w_how", "input", function (e) { actx().method = e.target.value; autoGrow(e.target); saveUi(); });
    on("w_makes", "input", function (e) { actx().makes = e.target.value; saveUi(); });
    on("w_makes_state", "change", function (e) { actx().makes_state = e.target.value; saveUi(); });
    on("w_on", "change", function (e) { actx().target = e.target.value; saveUi(); });
    on("w_hands", "change", function (e) { actx().hands = e.target.value; saveUi(); });
    each("[data-use]", function (el) { el.addEventListener("change", function () { var x = actx(), id = el.getAttribute("data-use"); x.uses = (x.uses || []).filter(function (u) { return u !== id; }); if (el.checked) x.uses.push(id); x.open = true; saveUi(); render(); }); });
    each("[data-after-use]", function (el) { el.addEventListener("change", function () { var x = actx(); x.after = x.after || {}; x.after[el.getAttribute("data-after-use")] = el.value; saveUi(); }); });
    on("addBranch", "click", function () {
      var b = { id: newId(), type: "branch", otherwise: "stop", cases: [{ when: "", after: "continue", steps: [] }] };
      addAtActive(b); ui.sel.active = { branch: b.id, "case": 0 }; changed();
      var t = $("w_when_" + b.id + "_0"); if (t) t.focus();
    });
    on("addSeq", "click", function () { ui.sel.nseq++; ui.sel.labels.push(""); ui.sel.active = { seq: ui.sel.nseq - 1 }; changed(); });
    click("data-act-seq", function (q) { ui.sel.active = { seq: +q }; saveUi(); render(); var p = $("palette"); if (p && window.innerWidth < 961) p.scrollIntoView({ block: "start" }); });
    click("data-act-case", function (v) { var p = v.split(":"); ui.sel.active = { branch: p[0], "case": +p[1] }; saveUi(); render(); });
    click("data-del-seq", function (q) {
      q = +q; if (ui.sel.steps.some(function (x) { return (x.seq || 0) === q; }) || ui.sel.nseq < 2) return;
      ui.sel.steps.forEach(function (x) { if ((x.seq || 0) > q) x.seq--; });
      ui.sel.labels.splice(q, 1); ui.sel.nseq--; ui.sel.active = { seq: Math.min(q, ui.sel.nseq - 1) }; changed();
    });
    each("[data-open]", function (el) {
      function tog() { var id = el.getAttribute("data-open"); ui.openStep = ui.openStep === id ? null : id; saveUi(); render(); }
      el.addEventListener("click", tog); el.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); tog(); } });
    });
    click("data-up", function (id) { ui.openStep = id; moveStep(id, -1); changed(); var el = document.querySelector('[data-sid="' + id + '"]'); if (el) el.scrollIntoView({ block: "center" }); });
    click("data-down", function (id) { ui.openStep = id; moveStep(id, 1); changed(); var el = document.querySelector('[data-sid="' + id + '"]'); if (el) el.scrollIntoView({ block: "center" }); });
    click("data-del", function (id) {
      var f = locate(id); if (!f) return; var x = f.list.splice(f.index, 1)[0];
      if (ui.sel.active.branch === id) ui.sel.active = { seq: x.seq || 0 }; changed();
    });
    click("data-cond", function (id) { var f = locate(id); if (!f) return; var x = f.list[f.index]; if (x.condition) delete x.condition; else x.condition = { text: "" }; changed(); });
    click("data-after", function (v) { var p = v.split(":"), f = locate(p[0]); if (!f) return; var k = f.list[f.index].cases[+p[1]]; k.after = k.after === "stop" ? "continue" : "stop"; changed(); });
    click("data-add-case", function (id) { var f = locate(id); if (!f) return; var b = f.list[f.index]; b.cases.push({ when: "", after: "continue", steps: [] }); ui.sel.active = { branch: id, "case": b.cases.length - 1 }; changed(); });
    click("data-del-case", function (v) { var p = v.split(":"), f = locate(p[0]); if (!f) return; f.list[f.index].cases.splice(+p[1], 1); ui.sel.active = { seq: f.list[f.index].seq || 0 }; changed(); });
    click("data-other", function (v) { var p = v.split(":"), f = locate(p[0]); if (!f) return; f.list[f.index].otherwise = p[1] === "continue" ? "continue" : "stop"; changed(); });
    T.flat(ui.sel.steps || []).forEach(function (x) {
      on("w_cond_" + x.id, "input", soft(function (v) { x.condition = { text: v }; }));
      on("w_cond_" + x.id, "change", function () { saveUi(); render(); });
      on("w_tgt_" + x.id, "change", function (e) { x.target = e.target.value || null; changed(); });
      (x.cases || []).forEach(function (k, j) {
        on("w_when_" + x.id + "_" + j, "input", soft(function (v) { k.when = v; }));
        on("w_when_" + x.id + "_" + j, "change", function () { saveUi(); render(); });
      });
    });
    for (var q = 0; q < (ui.sel.nseq || 1); q++) (function (q) { on("w_lbl_" + q, "input", soft(function (v) { ui.sel.labels[q] = v; })); })(q);
    on("w_say", "input", function (e) { ui.sel.sayDraft = e.target.value; autoGrow(e.target); saveUi(); });
    on("w_act", "input", function (e) { ui.sel.actDraft = e.target.value; autoGrow(e.target); saveUi(); });
    on("continuePending", "click", function () { var c = ctxOf(view); if (c) { loadDeclaration({ actor: c.actor, steps: (c.pending_steps || []).filter(function (x) { return continuable(c, x); }) }, c, true); render(); } });
    on("editAsSteps", "click", function () { var c = ctxOf(view); if (c) { loadDeclaration(T.parseFreeform(ui.write, c), c, false); render(); } });
    on("w_own", "input", soft(function (x) { ui.sel.own = x; }));
    on("w_trigger", "input", soft(function (x) { ui.sel.trigger = x; }));
    on("w_note", "input", soft(function (x) { ui.note = x; }));
    on("w_write", "input", soft(function (x) { ui.write = x; ls("datapad.draft", x); }));
    bindLive();
    each(".composer textarea", autoGrow);
    Array.prototype.forEach.call(document.querySelectorAll("[data-ralt]"), function (b) {
      b.addEventListener("click", function () {
        var p = b.getAttribute("data-ralt").split(":"), a = actions.filter(function (x) { return x._id === p[0]; })[0];
        var alt = a && a.review && a.review.alternatives[+p[1]]; if (alt && ctxOf(view)) { loadDeclaration(alt.declaration, ctxOf(view)); render(); }
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-wd]"), function (b) {
      b.addEventListener("click", function () {
        var id = b.getAttribute("data-wd"), a = actions.filter(function (x) { return x._id === id; })[0];
        if (!a || a.status !== "submitted") { setMsg("Already picked up by the GM."); return; }
        dbRef.doc("actions/" + id).delete().catch(function (e) { setMsg("Could not withdraw: " + (e && e.code || "error")); });
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-nudge]"), function (b) { b.addEventListener("click", function () { notifyGM(b.getAttribute("data-nudge")); }); });
  }

  /* Live preflight while typing: update only the check panel, the "Read as" line and the submit bar,
     so a text box is never rebuilt under the player's keyboard. */
  function bindLive() {
    var cr = $("confirmRisk"); if (cr) cr.addEventListener("change", function () { ui.confirmed = cr.checked; saveUi(); refreshLive(); });
    Array.prototype.forEach.call(document.querySelectorAll("[data-alt]"), function (b) {
      b.addEventListener("click", function () { var r = window.__lastValidation; var a = r && r.alternatives[+b.getAttribute("data-alt")]; if (a) { loadDeclaration(a.declaration, ctxOf(view)); render(); } });
    });
    var sb = $("submitTurn"); if (sb && !sb.__bound) { sb.__bound = true; sb.addEventListener("click", submitTurn); }
    var cl = $("clearTurn"); if (cl && !cl.__bound) { cl.__bound = true; cl.addEventListener("click", function () { ui = freshUi(ui.ctxId); saveUi(); render(); }); }
    var jf = $("jumpFix"); if (jf && !jf.__bound) { jf.__bound = true; jf.addEventListener("click", function () { var el = document.querySelector(".step.st-fix") || $("liveCheck"); if (el) el.scrollIntoView({ block: "center" }); }); }
  }
  function refreshLive() {
    var c = ctxOf(view), lc = $("liveCheck");
    if (!c || !lc) { if (!c && $("submitTurn")) $("submitTurn").disabled = !!(activeAction() || !ui.write.trim() || status !== "live" || phase); return; }
    var busy = activeAction(), d = declaration(c), r = safeValidate(d, c), stat = safeStatus(r);
    window.__lastValidation = r;
    lc.innerHTML = checkPanel(r);
    var ra = $("readAs"); if (ra) ra.textContent = "Read as: " + (r.preview.map(function (p) { return p.text; }).join(" → ") || "nothing matched yet");
    var rs = $("readAsSteps"); if (rs) rs.innerHTML = readAsInner(c, r, stat);
    var bar = $("submitBar"); if (bar) bar.innerHTML = submitBar(r, stat, busy);
    bindLive();
  }
  function autoGrow(el) {
    if (!el || el.tagName !== "TEXTAREA") return;
    var col = el.closest(".col"), y = col ? col.scrollTop : 0, wy = window.scrollY;
    el.style.height = "auto"; el.style.height = (el.scrollHeight + 2) + "px";
    el.style.overflowY = el.scrollHeight + 2 > el.clientHeight + 1 ? "auto" : "hidden";
    if (col) col.scrollTop = y; window.scrollTo(window.scrollX, wy);
  }

  /* "Newest" button: jumps to the latest story entry; hidden while that entry is on screen. */
  var jumpObs = null;
  function watchNewest() {
    var btn = $("jumpNew"), items = document.querySelectorAll("#colCenter .feed > div");
    if (!btn) return;
    var last = items[items.length - 1];
    if (jumpObs) jumpObs.disconnect();
    if (!last) { btn.hidden = true; return; }
    if (!("IntersectionObserver" in window)) { btn.hidden = false; return; }
    // hidden while the newest entry is on screen, and while the turn builder is (it would cover palette buttons)
    var seen = { last: false, comp: false }, comp = document.querySelector(".composer");
    jumpObs = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.target === last) seen.last = e.isIntersecting; else seen.comp = e.isIntersecting; });
      btn.hidden = seen.last || seen.comp;
    });
    jumpObs.observe(last); if (comp) jumpObs.observe(comp);
  }
  (function () {
    var btn = $("jumpNew"); if (!btn) return;
    btn.addEventListener("click", function () {
      var items = document.querySelectorAll("#colCenter .feed > div"), last = items[items.length - 1];
      if (!last) return;
      var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      last.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    });
  })();

  function submitTurn() {
    var c = ctxOf(view), busy = activeAction();
    if (busy || !dbRef || phase) return;
    var d = c ? declaration(c) : null, r = c ? safeValidate(d, c) : null;
    if (c && (!r.legal || (r.needs_confirmation && !ui.confirmed))) return;
    var text = c ? turnText(d, r) : ui.write.trim();
    if (!text) return;
    phase = "validating"; render();
    var seenRev = view.revision, seenHead = view.ledger_head;
    // The store may have moved on since this plan was checked: re-read it first and never submit against an old scene.
    dbRef.doc("view/state").get().then(function (vs) {
      var cur = vs && vs.exists ? vs.data() : null;
      if (cur && (cur.revision !== seenRev || cur.ledger_head !== seenHead)) {
        view = cur; phase = ""; render();
        setMsg("The scene moved on (revision " + seenRev + " → " + cur.revision + "). Your plan is kept and re-checked; review it and submit again.");
        return;
      }
      saveAction(c, d, r, text);
    }, function () { saveAction(c, d, r, text); });
  }
  function saveAction(c, d, r, text) {
    if (!ui.draftId) { ui.draftId = "a" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8); saveUi(); }
    var id = ui.draftId, ref = dbRef.doc("actions/" + id);
    var doc = { text: text, declaration: d, source: c ? (ui.mode === "write" ? "freeform" : "composer") : "freeform", actor: view.active_actor || "aero",
      campaign_id: view.campaign_id || "starwars_litrpg", based_on_revision: view.revision, ledger_head: view.ledger_head, context_id: c ? c.context_id : null,
      contract: T.VERSION, confirmed_warnings: !!(r && r.needs_confirmation), warnings: r ? r.warnings.map(function (w) { return w.message; }) : [],
      preflight: r ? { legal: r.legal, crashed: !!r.crashed, codes: r.errors.map(function (e) { return e.code; }).concat(r.warnings.map(function (w) { return w.code; })) } : null,
      status: "submitted", created_ms: Date.now() };
    // Idempotent create: the id is minted once per draft; if a retry finds the document, it is never overwritten.
    ref.get().then(function (snap) { return snap.exists ? null : ref.set(doc); }).then(function () {
      localPending = { id: id, at: Date.now(), text: text };
      ui = freshUi(c ? c.context_id : null); ls("datapad.draft", ""); saveUi(); phase = ""; render(); notifyGM(id);
    }, function (e) { phase = ""; render(); setMsg("Not saved (" + (e && e.code || "error") + "). Your turn is still here; try again."); });
  }

  function notifyGM(id) {
    if (!view.processor) { notifyState[id] = { ok: false, code: "no_processor" }; render(); return; }
    if (!mcpNs) { notifyState[id] = { ok: false, code: "mcp_unavailable" }; render(); return; }
    notifyState[id] = { state: "sending" }; render();
    mcpNs.callTool(view.processor.server, "fire_trigger", { trigger_id: view.processor.trigger_id, text: JSON.stringify({ campaign_id: view.campaign_id, action_id: id }) })
      .then(function () { notifyState[id] = { ok: true, at: Date.now() }; render(); },
            function (e) { notifyState[id] = { ok: false, code: (e && e.code) || "error" }; render(); });
  }

  Array.prototype.forEach.call(document.querySelectorAll("#tabbar button"), function (b) {
    b.addEventListener("click", function () {
      $("app").setAttribute("data-tab", b.getAttribute("data-t"));
      Array.prototype.forEach.call(document.querySelectorAll("#tabbar button"), function (x) { x.setAttribute("aria-selected", String(x === b)); });
      window.scrollTo(0, 0);
    });
  });

  /* ---------- data: subscribe once ---------- */
  var timer = setTimeout(function () { if (!view) { status = "error"; err = "The campaign store has not answered yet. It may be offline."; render(); } }, 10000);
  setInterval(function () { if (activeAction()) render(); }, 30000);  // refresh "processing for N min" labels only while a turn is out
  function start(db) {
    dbRef = db; status = "live";
    db.doc("view/state").onSnapshot(function (snap) {
      if (snap.exists) { view = snap.data(); clearTimeout(timer); }
      render();
    }, function (e) { status = "error"; err = "Store error: " + (e && e.code); render(); });
    db.collection("usage").orderBy("started_ms", "desc").limit(50).onSnapshot(function (q) {
      usage = q.docs.map(function (d) { return d.data(); }); render();
    }, function () {});
    db.collection("actions").orderBy("created_ms", "desc").limit(10).onSnapshot(function (q) {
      actions = q.docs.map(function (d) { var x = Object.assign({}, d.data()); x._id = d.id; return x; })
        .filter(function (a) { return !view || !view.campaign_id || (a.campaign_id || "starwars_litrpg") === view.campaign_id; });
      render();
    }, function () {});
  }
  render();
  if (window.claude && window.claude.use) {
    window.claude.use("db").then(function (db) { if (db) start(db); else { status = "unavailable"; clearTimeout(timer); render(); } }, function () { status = "unavailable"; render(); });
    window.claude.use("mcp").then(function (m) { mcpNs = m; render(); }, function () { mcpNs = null; });
  } else { status = "unavailable"; render(); }
})();
</script>
