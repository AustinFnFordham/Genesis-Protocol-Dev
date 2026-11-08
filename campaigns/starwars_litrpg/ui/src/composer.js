  /* ===================== Turn composer (turn-contract/1) ===================== */
  var T = window.GenesisTurn, mcpNs = null, phase = "", notifyState = {}, usage = [];
  function byId(list, id) { for (var i = 0; i < (list || []).length; i++) if (list[i].id === id) return list[i]; return null; }
  function freshUi(ctxId, keepWrite) {
    return { ctxId: ctxId, mode: "build", write: keepWrite || "", note: "", confirmed: false, draftId: "",
             sel: { dialogue: "silent", own: "", action: "", target: {}, trigger: "", bonus: "", movement: "hold", objects: [], reactions: [] } };
  }
  var ui = (function () { try { var x = JSON.parse(ls("datapad.ui") || "null"); if (x && x.sel) return x; } catch (e) {} return freshUi(null, ls("datapad.draft")); })();
  function saveUi() { ls("datapad.ui", JSON.stringify(ui)); }
  function ctxOf(v) { return v && v.turn_context ? v.turn_context : null; }
  function syncCtx() {
    var c = ctxOf(view), id = c ? c.context_id : null;
    if (ui.ctxId !== id) { ui = freshUi(id, ui.write); saveUi(); }
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

  function declaration(c) {
    if (ui.mode === "write") return T.parseFreeform(ui.write, c);
    var d = T.emptyDecl(c), s = ui.sel;
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
  function loadDeclaration(d, c) {
    var s = freshUi(c.context_id).sel;
    if (d.speech) { if (d.speech.option && byId(c.dialogue, d.speech.option)) s.dialogue = d.speech.option; else { s.dialogue = "own"; s.own = d.speech.text || ""; } }
    if (d.actions && d.actions[0]) { s.action = d.actions[0].option; if (d.actions[0].target) s.target[s.action] = d.actions[0].target; s.trigger = d.actions[0].trigger || ""; }
    if (d.bonus_actions && d.bonus_actions[0]) s.bonus = d.bonus_actions[0].option;
    s.movement = d.movement ? d.movement.option : "hold";
    s.objects = (d.objects || []).slice(); s.reactions = (d.reactions || []).slice();
    ui.sel = s; ui.mode = "build"; ui.confirmed = false; ui.note = (d.unmapped || []).join(" "); saveUi();
  }
  function turnText(d, r) {
    if (ui.mode === "write") return ui.write.trim();
    return r.preview.map(function (p) { return p.text; }).join("; ") + (ui.note.trim() ? ". Also: " + ui.note.trim() : "");
  }

  function radio(group, value, checked, label, small, tag) {
    return '<label class="opt"><input type="radio" name="' + group + '" value="' + esc(value) + '" data-g="' + group + '"' + (checked ? " checked" : "") + '><span class="lbl">' + esc(label) +
      (tag ? ' <span class="tag">' + esc(tag) + "</span>" : "") + (small ? "<small>" + esc(small) + "</small>" : "") + "</span></label>";
  }
  function check(group, value, checked, label, small) {
    return '<label class="opt"><input type="checkbox" value="' + esc(value) + '" data-c="' + group + '"' + (checked ? " checked" : "") + '><span class="lbl">' + esc(label) + (small ? "<small>" + esc(small) + "</small>" : "") + "</span></label>";
  }
  function budget(c, r) {
    if (c.mode !== "combat") return '<div class="note">Scene: no initiative. Say and do what you like; the GM applies the rules where they matter.</div>';
    var b = c.budget || {}, u = r.used;
    function p(name, used, txt) { return '<span class="pill ' + (used ? "used" : "ok") + '">' + name + ": " + txt + "</span>"; }
    return '<div class="budget">' + p("Action", u.action >= (b.action || 1), u.action >= (b.action || 1) ? "Used" : "Available") +
      p("Movement", u.movement_ft > 0, (b.movement_ft - u.movement_ft) + "/" + b.movement_ft + " ft") +
      p("Bonus", u.bonus_action >= (b.bonus_action || 1), u.bonus_action ? "Used" : ((c.options || []).some(function (o) { return o.slot === "bonus_action"; }) ? "Available" : "None eligible")) +
      p("Reaction", u.reaction > 0, u.reaction ? "Reserved" : "Available") +
      p("Object", u.object_interaction > 0, u.object_interaction ? "Used" : "Available") + "</div>";
  }
  function checkPanel(r) {
    var cls = r.legal ? (r.warnings.length ? "warn" : "") : "bad";
    var head = r.legal ? (r.warnings.length ? "Legal, with known risks" : "Legal turn") : "Not legal yet";
    var h = '<div class="check ' + cls + '" aria-live="polite"><b>' + head + "</b>";
    r.errors.forEach(function (e) { h += '<div class="msg-err">' + esc(e.message) + "</div>"; });
    r.warnings.forEach(function (w) { h += '<div class="msg-warn">' + esc(w.message) + "</div>"; });
    r.info.forEach(function (i) { h += '<div class="note">' + esc(i.message) + "</div>"; });
    if (r.preview.length) h += "<ol>" + r.preview.map(function (p) { return "<li>" + esc(p.text) + "</li>"; }).join("") + "</ol>";
    if (r.alternatives.length) h += '<div class="note">Legal alternatives:</div><div class="sugg">' + r.alternatives.map(function (a, i) { return '<button class="chip" data-alt="' + i + '">' + esc(a.label) + "</button>"; }).join("") + "</div>";
    if (r.legal && r.warnings.length) h += '<label class="opt"><input type="checkbox" id="confirmRisk"' + (ui.confirmed ? " checked" : "") + '><span class="lbl">I understand these risks. Submit anyway.</span></label>';
    h += '<div class="note">Preflight checks legality and visible risks only. It never predicts the dice.</div>';
    return h + "</div>";
  }

  function renderTurn(v) {
    var c = ctxOf(v), busy = activeAction();
    if (!c) return renderLegacy(v, busy);
    var d = declaration(c), r = T.validate(d, c), s = ui.sel;
    window.__lastValidation = r;
    var dis = busy ? " disabled" : "";
    var h = '<div class="panel composer"><div class="row" style="justify-content:space-between"><h2 style="margin:0">' + esc(c.actor_name || "Aero") + "’s turn" + (c.mode === "combat" ? " · round " + esc(c.round) : "") + "</h2>" +
      '<div class="seg" role="group" aria-label="Compose mode"><button data-mode="build" aria-pressed="' + (ui.mode === "build") + '">Build</button><button data-mode="write" aria-pressed="' + (ui.mode === "write") + '">Write</button></div></div>' +
      budget(c, r) + ((c.notes || []).length ? '<div class="check warn" style="margin-top:8px"><b>What you notice</b>' + c.notes.map(function (n) { return "<div>" + esc(n) + "</div>"; }).join("") + "</div>" : "") +
      "<fieldset" + dis + ' style="border:0;margin:0;padding:0;min-width:0">';
    if (ui.mode === "write") {
      h += '<textarea id="w_write" placeholder="Describe the whole turn in your own words. Put speech in quotes." style="margin-top:10px">' + esc(ui.write) + "</textarea>" +
        '<div class="note" id="readAs">Read as: ' + esc(r.preview.map(function (p) { return p.text; }).join(" → ") || "nothing matched yet") + "</div>";
    } else {
      h += '<fieldset class="grp"><legend>Dialogue</legend>' + (c.dialogue || []).map(function (o) { return radio("dialogue", o.id, s.dialogue === o.id, "“" + o.text + "”", o.approach + (o.extended ? " · extended, uses your action" : "")); }).join("") +
        radio("dialogue", "silent", s.dialogue === "silent", "Remain silent") + radio("dialogue", "own", s.dialogue === "own", "Write my own line") +
        (s.dialogue === "own" ? '<input class="txt" id="w_own" placeholder="What Aero says" value="' + esc(s.own) + '">' : "") + "</fieldset>";
      h += '<fieldset class="grp"><legend>Primary action</legend>' + radio("action", "", !s.action, "No action") +
        (c.options || []).filter(function (o) { return o.slot === "action"; }).map(function (o) {
          var tag = (o.requires || []).length ? "needs " + o.requires.map(function (q) { return (c.flag_labels || {})[q] || q; }).join(", ") : "";
          var x = radio("action", o.id, s.action === o.id, o.label, o.detail || (o.area_ft ? o.area_ft + "-ft radius" : o.reach_ft ? "reach " + o.reach_ft + " ft" : ""), tag);
          if (s.action === o.id && o.needs_target) x += '<select class="txt" id="w_target" aria-label="Target"><option value="">Choose a target</option>' + (c.visible || []).map(function (t) { return '<option value="' + esc(t.id) + '"' + (s.target[o.id] === t.id ? " selected" : "") + ">" + esc(t.label) + " (~" + t.distance_ft + " ft)</option>"; }).join("") + "</select>";
          if (s.action === o.id && o.needs_trigger) x += '<input class="txt" id="w_trigger" placeholder="Trigger: ' + esc(o.default_trigger || "") + '" value="' + esc(s.trigger) + '">';
          return x;
        }).join("") + "</fieldset>";
      var bon = (c.options || []).filter(function (o) { return o.slot === "bonus_action"; });
      if (bon.length) h += '<fieldset class="grp"><legend>Bonus action</legend>' + radio("bonus", "", !s.bonus, "None") + bon.map(function (o) { return radio("bonus", o.id, s.bonus === o.id, o.label, o.detail); }).join("") + "</fieldset>";
      h += '<fieldset class="grp"><legend>Movement</legend>' + (c.movement || []).map(function (m) {
        var risk = c.mode === "combat" && (m.leaves_reach_of || []).length ? "opportunity attack risk" : "";
        return radio("movement", m.id, s.movement === m.id, m.label, m.feet && !/\d\s*(ft|m)\b/.test(m.label) ? "~" + m.feet + " ft" : "", risk);
      }).join("") + "</fieldset>";
      if ((c.objects || []).length) h += '<fieldset class="grp"><legend>Object interaction</legend>' + c.objects.map(function (o) { return check("objects", o.id, s.objects.indexOf(o.id) >= 0, o.label, "first one each turn is free"); }).join("") + "</fieldset>";
      if ((c.reactions || []).length) h += '<fieldset class="grp"><legend>Reactions (if triggered)</legend>' + c.reactions.map(function (o) { return check("reactions", o.id, s.reactions.indexOf(o.id) >= 0, o.label, "if " + o.trigger); }).join("") + "</fieldset>";
      h += '<textarea id="w_note" placeholder="Anything else Aero does (optional). The GM checks it against the same rules." style="margin-top:10px;min-height:60px">' + esc(ui.note) + "</textarea>";
    }
    h += "</fieldset>" + '<div id="liveCheck">' + checkPanel(r) + "</div>";
    var canSubmit = !busy && status === "live" && r.legal && (!r.warnings.length || ui.confirmed) && (r.preview.length || (ui.mode === "write" && ui.write.trim()) || ui.note.trim());
    h += '<div class="row" style="margin-top:10px"><button class="btn primary" id="submitTurn"' + (canSubmit && !phase ? "" : " disabled") + ">" + (phase === "validating" ? "Submitting…" : "Submit turn") + "</button>" +
      '<button class="btn" id="clearTurn"' + dis + '>Clear</button><span class="note" id="msg"></span></div>' +
      (busy ? '<div class="note">One turn at a time: the current one is with the GM.</div>' : "") + renderActions() + "</div>";
    return h;
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
      '<div class="note" style="margin-top:6px">' + Object.keys(by).map(function (k) { return esc(k.replace("_", " ")) + " " + by[k]; }).join(" · ") + "</div></div>";
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
  function changed() { ui.confirmed = false; ui.draftId = ""; saveUi(); render(); }
  function bindCenter() {
    function on(id, ev, fn) { var el = $(id); if (el) el.addEventListener(ev, fn); }
    Array.prototype.forEach.call(document.querySelectorAll("[data-mode]"), function (b) { b.addEventListener("click", function () { ui.mode = b.getAttribute("data-mode"); changed(); }); });
    Array.prototype.forEach.call(document.querySelectorAll("input[data-g]"), function (el) {
      el.addEventListener("change", function () { ui.sel[el.getAttribute("data-g")] = el.value; changed(); });
    });
    Array.prototype.forEach.call(document.querySelectorAll("input[data-c]"), function (el) {
      el.addEventListener("change", function () {
        var g = el.getAttribute("data-c"), list = ui.sel[g].filter(function (x) { return x !== el.value; });
        if (el.checked) list.push(el.value); ui.sel[g] = list; changed();
      });
    });
    on("w_target", "change", function () { ui.sel.target[ui.sel.action] = $("w_target").value; changed(); });
    var deb = null;
    function typed(set) { return function (e) { set(e.target.value); ui.confirmed = false; ui.draftId = ""; autoGrow(e.target); clearTimeout(deb); deb = setTimeout(function () { saveUi(); refreshLive(); }, 250); }; }
    on("w_own", "input", typed(function (x) { ui.sel.own = x; }));
    on("w_trigger", "input", typed(function (x) { ui.sel.trigger = x; }));
    on("w_note", "input", typed(function (x) { ui.note = x; }));
    on("w_write", "input", typed(function (x) { ui.write = x; ls("datapad.draft", x); }));
    bindLive();
    Array.prototype.forEach.call(document.querySelectorAll(".composer textarea"), autoGrow);
    on("clearTurn", "click", function () { ui = freshUi(ui.ctxId); saveUi(); render(); });
    on("submitTurn", "click", submitTurn);
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

  /* Live preflight while typing: update only the check panel, the "Read as" line and the Submit
     button, so the text box is never rebuilt under the player's keyboard. */
  function bindLive() {
    var cr = $("confirmRisk"); if (cr) cr.addEventListener("change", function () { ui.confirmed = cr.checked; saveUi(); refreshLive(); });
    Array.prototype.forEach.call(document.querySelectorAll("[data-alt]"), function (b) {
      b.addEventListener("click", function () { var r = window.__lastValidation; var a = r && r.alternatives[+b.getAttribute("data-alt")]; if (a) { loadDeclaration(a.declaration, ctxOf(view)); render(); } });
    });
  }
  function refreshLive() {
    var c = ctxOf(view), lc = $("liveCheck");
    if (!c || !lc) { if (!c && $("submitTurn")) $("submitTurn").disabled = !!(activeAction() || !ui.write.trim() || status !== "live" || phase); return; }
    var busy = activeAction(), d = declaration(c), r = T.validate(d, c);
    window.__lastValidation = r;
    lc.innerHTML = checkPanel(r);
    var ra = $("readAs"); if (ra) ra.textContent = "Read as: " + (r.preview.map(function (p) { return p.text; }).join(" \u2192 ") || "nothing matched yet");
    var canSubmit = !busy && status === "live" && r.legal && (!r.warnings.length || ui.confirmed) && (r.preview.length || (ui.mode === "write" && ui.write.trim()) || ui.note.trim());
    var sb = $("submitTurn"); if (sb) sb.disabled = !(canSubmit && !phase);
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
    jumpObs = new IntersectionObserver(function (es) { btn.hidden = es[es.length - 1].isIntersecting; });
    jumpObs.observe(last);
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
    var d = c ? declaration(c) : null, r = c ? T.validate(d, c) : null;
    if (c && (!r.legal || (r.warnings.length && !ui.confirmed))) return;
    var text = c ? turnText(d, r) : ui.write.trim();
    if (!text) return;
    phase = "validating"; render();
    if (!ui.draftId) { ui.draftId = "a" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8); saveUi(); }
    var id = ui.draftId, ref = dbRef.doc("actions/" + id);
    var doc = { text: text, declaration: d, source: c ? (ui.mode === "write" ? "freeform" : "composer") : "freeform", actor: view.active_actor || "aero",
      campaign_id: view.campaign_id || "starwars_litrpg", based_on_revision: view.revision, ledger_head: view.ledger_head, context_id: c ? c.context_id : null,
      contract: T.VERSION, confirmed_warnings: !!(r && r.warnings.length), warnings: r ? r.warnings.map(function (w) { return w.message; }) : [],
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
