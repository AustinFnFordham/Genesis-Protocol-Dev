/* WHISPER start-of-turn context (TB4-WHISPER-001 §2.4, §3.2), switchable and removable.
 * On only when view.features.whisper_context === true. Remove this file, its line in build_datapad.py and the
 * `WH.` hooks in composer.js to take it out.
 *
 * Player-authored only. Blank means *unspecified* — never calm, numb or none-felt. Nothing here costs an action, rolls,
 * changes morality or becomes an act. "What if…?" thoughts are static, zero-cost prompts: opening, reading or dismissing
 * one records nothing; only the player's explicit "Use as my reflection" copies the words into the private reflection.
 */
var GenesisWhisper = (function () {
  var FEELINGS = ["fear", "anger", "grief", "guilt", "shame", "disgust", "hope", "resolve", "relief", "love", "joy", "doubt"];
  var EXPRESSIONS = [["", "Not stated"], ["open", "Shows it openly"], ["controlled", "Keeps it controlled"], ["masked", "Hides it behind a different face"]];
  // Static creative prompts (authored, cached in the page): contrasting, never presented as Aero's real thought.
  var WHAT_IF = {
    combat: ["What if I let it come to me and stop protecting Wick?", "What if I make it hurt, so the others think twice?",
             "What if I just run and let the drill end without me?", "What if I put the saber away and try to calm it?"],
    scene: ["What if I lie to Wick about what I saw?", "What if I take what I need and leave them to it?",
            "What if I tell Wick everything, even what scares me?", "What if I stop and listen before I decide anything?"]
  };
  function enabled(v) { return !!(v && v.features && v.features.whisper_context === true); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function ensure(sel) { sel.whisper = sel.whisper || { felt: [], feltOther: "", expression: "", expressionText: "", motive: "", reflection: "" }; return sel.whisper; }
  function context(sel) {   // null when the player stated nothing (unspecified)
    var w = ensure(sel), felt = w.felt.slice(); if (String(w.feltOther || "").trim()) felt.push(String(w.feltOther).trim());
    var out = { schema: "genesis-whisper-context/1", source: "player_explicit", visibility: "pc_private",
                felt_emotion: felt.length ? felt : "unspecified",
                expression: w.expression ? { style: w.expression, text: String(w.expressionText || "").trim() || null } : "unspecified",
                motive: String(w.motive || "").trim() || "unspecified", reflection: String(w.reflection || "").trim() || null };
    return felt.length || w.expression || out.motive !== "unspecified" || out.reflection ? out : null;
  }
  function apply(d, sel) { var c = context(sel); if (c) d.whisper = c; return d; }
  function restore(d, sel) {
    var w = ensure(sel), x = d && d.whisper; if (!x) return;
    var felt = Array.isArray(x.felt_emotion) ? x.felt_emotion : [];
    w.felt = felt.filter(function (f) { return FEELINGS.indexOf(f) >= 0; }); w.feltOther = felt.filter(function (f) { return FEELINGS.indexOf(f) < 0; }).join(", ");
    w.expression = x.expression && x.expression.style || ""; w.expressionText = x.expression && x.expression.text || "";
    w.motive = x.motive && x.motive !== "unspecified" ? x.motive : ""; w.reflection = x.reflection || "";
  }
  function panel(c, sel) {
    var w = ensure(sel), mode = c && c.mode === "combat" ? "combat" : "scene", filled = !!context(sel);
    return '<details class="grp whisper" id="whisperPanel"' + (filled ? " open" : "") + '><summary><b>WHISPER</b> · how Aero feels and why (optional, private)</summary>' +
      '<div class="note">Only you write this. Leaving it blank means “not stated”, not calm or cold. It costs nothing, rolls nothing and never changes Aero’s morality by itself. NPCs only see what Aero shows.</div>' +
      '<div class="row" style="flex-wrap:wrap;gap:6px;margin:6px 0">' + FEELINGS.map(function (f) {
        return '<button type="button" class="chip mini" data-whfeel="' + f + '" aria-pressed="' + (w.felt.indexOf(f) >= 0) + '">' + f + "</button>"; }).join("") + "</div>" +
      '<label><small>Other feeling, in your words</small><input class="txt" id="w_wh_other" data-wh="feltOther" value="' + esc(w.feltOther) + '"></label>' +
      '<label><small>What Aero lets show</small><select class="txt" id="w_wh_expr" data-wh="expression">' + EXPRESSIONS.map(function (e) { return '<option value="' + e[0] + '"' + (w.expression === e[0] ? " selected" : "") + ">" + e[1] + "</option>"; }).join("") + "</select></label>" +
      (w.expression ? '<label><small>How it shows (what others can see or hear)</small><input class="txt" id="w_wh_exprtext" data-wh="expressionText" value="' + esc(w.expressionText) + '"></label>' : "") +
      '<label><small>Why: Aero’s intention or motive</small><input class="txt" id="w_wh_motive" data-wh="motive" placeholder="e.g. protect Wick, not prove anything" value="' + esc(w.motive) + '"></label>' +
      '<label><small>Private reflection (only you and the GM)</small><textarea id="w_wh_reflection" data-wh="reflection" rows="2">' + esc(w.reflection) + "</textarea></label>" +
      '<details class="whatif" id="whatIf"><summary>What if…? (thought experiments, not Aero’s thoughts)</summary><div class="note">Reading these records nothing. Use one only if you want it as your own reflection; doing something is a separate choice in your turn.</div><ul>' +
      WHAT_IF[mode].map(function (t, i) { return '<li>' + esc(t) + ' <button type="button" class="chip mini" data-whadopt="' + mode + ":" + i + '">Use as my reflection</button></li>'; }).join("") + "</ul></details>" +
      (filled ? '<button type="button" class="chip mini" id="whClear">Clear (back to not stated)</button>' : "") + "</details>";
  }
  // Post-turn review (switch whisper_review; owner decisions 1-2). Suggestions only; the player answers.
  function reviewOn(v) { return !!(v && v.features && v.features.whisper_review === true && v.whisper && v.whisper.pending); }
  function reviewCard(v, sel, busy) {
    var p = v.whisper.pending, ed = sel.whEdit = sel.whEdit || {};
    var KIND = { temporary: "for now", long_term: "lasting — becomes part of who he is", prompt: "your words" };
    return '<div class="check" id="whisperReview" style="margin-top:8px"><b>WHISPER · after that turn</b><div class="note">' + esc(p.note || "") + '</div>' +
      p.candidates.map(function (c) {
        var id = esc(c.candidate_id);
        return '<div class="whcand" style="border-top:1px solid var(--line);padding-top:6px;margin-top:6px"><div><small class="tag">' + esc(KIND[c.kind] || c.kind) + "</small> " +
          (c.proposed ? "<b>" + esc(c.proposed) + "</b>" : "<b>How does Aero feel about it?</b>") + '</div><div class="note">' + esc(c.explanation) + ' <small>(from ' + esc(c.evidence.join(", ")) + ")</small></div>" +
          '<textarea id="w_whed_' + id + '" data-whedit="' + id + '" rows="2" placeholder="' + (c.proposed ? "Edit it into your own words" : "In your own words") + '">' + esc(ed[c.candidate_id] || "") + "</textarea>" +
          '<div class="row" style="flex-wrap:wrap;gap:6px">' + (c.proposed ? '<button type="button" class="chip mini" data-whresp="' + id + '|accept"' + (busy ? " disabled" : "") + ">Accept</button>" : "") +
          '<button type="button" class="chip mini" data-whresp="' + id + '|edit"' + (busy ? " disabled" : "") + ">" + (c.proposed ? "Use my edit" : "Save my words") + "</button>" +
          '<button type="button" class="chip mini" data-whresp="' + id + '|reject"' + (busy ? " disabled" : "") + ">Reject</button>" +
          '<button type="button" class="chip mini" data-whresp="' + id + '|defer"' + (busy ? " disabled" : "") + ">Later</button></div></div>";
      }).join("") +
      '<div style="border-top:1px solid var(--line);padding-top:6px;margin-top:6px"><label><small>Or something else entirely, in your words</small><textarea id="w_whcustom" data-whedit="__custom" rows="2">' + esc(ed.__custom || "") + "</textarea></label>" +
      '<button type="button" class="chip mini" data-whresp="__custom|custom"' + (busy ? " disabled" : "") + ">Save my own response</button></div>" +
      '<div class="note">Nothing here changes Aero unless you choose it. Mechanical conditions still follow the rules.</div><span class="note" id="whMsg"></span></div>';
  }
  function bindReview(root, v, sel, hooks) {
    var ed = sel.whEdit = sel.whEdit || {};
    Array.prototype.forEach.call(root.querySelectorAll("[data-whedit]"), function (el) {
      el.addEventListener("input", function () { ed[el.getAttribute("data-whedit")] = el.value; });
    });
    Array.prototype.forEach.call(root.querySelectorAll("[data-whresp]"), function (b) {
      b.addEventListener("click", function () {
        var p = b.getAttribute("data-whresp").split("|"), cid = p[0] === "__custom" ? null : p[0], choice = p[1];
        var text = String(ed[p[0]] || "").trim();
        if ((choice === "edit" || choice === "custom") && !text) { var m = root.querySelector("#whMsg"); if (m) m.textContent = "Write your words first."; return; }
        hooks.respond({ review_id: v.whisper.pending.review_id, candidate_id: cid, choice: choice, text: choice === "edit" || choice === "custom" ? text : null });
        delete ed[p[0]];
      });
    });
  }
  function summary(sel) {
    var c = context(sel); if (!c) return "";
    return "WHISPER (private): " + [Array.isArray(c.felt_emotion) ? "feels " + c.felt_emotion.join(", ") : "", typeof c.expression === "object" ? "shows: " + c.expression.style + (c.expression.text ? " (" + c.expression.text + ")" : "") : "", c.motive !== "unspecified" ? "why: " + c.motive : ""].filter(Boolean).join("; ");
  }
  function bind(root, sel, hooks) {
    var w = ensure(sel);
    Array.prototype.forEach.call(root.querySelectorAll("[data-whfeel]"), function (b) { b.addEventListener("click", function () {
      var f = b.getAttribute("data-whfeel"), i = w.felt.indexOf(f); if (i >= 0) w.felt.splice(i, 1); else w.felt.push(f); hooks.changed(); }); });
    Array.prototype.forEach.call(root.querySelectorAll("[data-wh]"), function (el) {
      var k = el.getAttribute("data-wh");
      if (el.tagName === "SELECT") el.addEventListener("change", function () { w[k] = el.value; hooks.changed(); });
      else el.addEventListener("input", hooks.soft(function (v) { w[k] = v; }));
    });
    Array.prototype.forEach.call(root.querySelectorAll("[data-whadopt]"), function (b) { b.addEventListener("click", function () {
      var p = b.getAttribute("data-whadopt").split(":"); w.reflection = (w.reflection ? w.reflection + "\n" : "") + WHAT_IF[p[0]][+p[1]]; hooks.changed(); }); });
    var cl = root.querySelector("#whClear"); if (cl) cl.addEventListener("click", function () { sel.whisper = null; ensure(sel); hooks.changed(); });
  }
  return { FEELINGS: FEELINGS, WHAT_IF: WHAT_IF, reviewOn: reviewOn, reviewCard: reviewCard, bindReview: bindReview, enabled: enabled, context: context, apply: apply, restore: restore, panel: panel, summary: summary, bind: bind };
})();
if (typeof module !== "undefined") module.exports = GenesisWhisper;
