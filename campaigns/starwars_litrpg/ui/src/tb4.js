/* Turn Builder 4 (TB4-WHISPER-001 §2), switchable and removable.
 * On only when the published state says view.features.tb4_builder === true. Remove this file, its line in
 * build_datapad.py and the `TB4.` hooks in composer.js to take it out; nothing else depends on it.
 *
 * - Custom box in every combat category: literal player words, kept as written in declaration.tb4.custom and passed
 *   to the GM as unmapped text (the existing validator and GM adjudicate cost; the UI label never sets a cost).
 * - Secondary Activity: a grouping of supporting conduct, never an extra slot (its cost is ruled like any other text).
 * - Suggestions: pure, deterministic, zero model calls; ranked from player-visible options only, ≤4 per category,
 *   each marked known_legal / needs_adjudication / blocked, and Custom is always offered.
 */
var GenesisTB4 = (function () {
  var CATS = [
    { id: "action", label: "Primary action", group: "action", hint: "Your own action, in your words: what, how, at whom" },
    { id: "bonus_action", label: "Bonus action", group: "bonus", hint: "Only if a feature gives you one; the GM checks it" },
    { id: "secondary", label: "Secondary activity", group: null, hint: "Supporting words or gestures alongside your turn. Not an extra action: the GM rules its real cost" },
    { id: "movement", label: "Movement", group: "movement", hint: "Exact path or destination" },
    { id: "object", label: "Object interaction", group: "objects", hint: "Which object, which hand, how" },
    { id: "reaction", label: "Reaction", group: "reactions", hint: "If <trigger>, then <response>" }
  ];
  // Explicit player style only (chosen on screen, never inferred). Keyword tags on GM-published option ids/labels.
  var STYLES = { cautious: /dodge|disengage|hide|hold|back|cover|retreat|guard|wait|watch/i,
                 bold: /attack|strike|burst|charge|slash|shoot|swing|rush|close|ignite/i,
                 social: /ask|talk|say|call|taunt|warn|help|calm|persuad|intimidat|order/i,
                 tactical: /ready|search|listen|look|insight|read|aim|study|scan|battle/i };
  var STYLE_LABEL = { "": "No preference", cautious: "Cautious", bold: "Bold", social: "Social", tactical: "Tactical" };

  function enabled(v) { return !!(v && v.features && v.features.tb4_builder === true); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function ensure(sel) { sel.tb4custom = sel.tb4custom || {}; sel.style = sel.style || ""; return sel; }

  function candidates(c, cat) {
    if (cat === "action") return (c.options || []).filter(function (o) { return o.slot === "action"; }).map(function (o) { return { key: "action:" + o.id, group: "action", id: o.id, label: o.label }; });
    if (cat === "bonus_action") return (c.options || []).filter(function (o) { return o.slot === "bonus_action"; }).map(function (o) { return { key: "bonus_action:" + o.id, group: "bonus", id: o.id, label: o.label }; });
    if (cat === "movement") return (c.movement || []).map(function (m) { return { key: "move:" + m.id, group: "movement", id: m.id, label: m.label }; });
    if (cat === "object") return (c.objects || []).filter(function (o) { return !o.gear; }).map(function (o) { return { key: "object:" + o.id, group: "objects", id: o.id, label: o.label }; });
    if (cat === "reaction") return (c.reactions || []).map(function (o) { return { key: "reaction:" + o.id, group: "reactions", id: o.id, label: o.label }; });
    return [];
  }
  // avail: map "type:option" -> {status, reasons} from the shared validator (turn_contract availability). Pure.
  function suggest(c, cat, style, avail) {
    var re = STYLES[style || ""] || null, out = [];
    candidates(c, cat).forEach(function (k, i) {
      var a = (avail || {})[k.key], st = !a ? "known_legal" : /not_here/.test(a.status) ? "blocked" : /needs_step|needs_choice/.test(a.status) ? "needs_adjudication" : "known_legal";
      var score = (st === "known_legal" ? 20 : st === "needs_adjudication" ? 10 : 0) + (re && re.test(k.id + " " + k.label) ? 5 : 0) - (k.id === "hold" ? 3 : 0);
      out.push({ id: k.id, group: k.group, label: k.label, status: st, reason: a && a.reasons && a.reasons[0] || "", score: score, order: i });
    });
    out.sort(function (x, y) { return y.score - x.score || x.order - y.order || (x.id < y.id ? -1 : 1); });
    return out.filter(function (x) { return x.status !== "blocked"; }).slice(0, 4).concat(out.filter(function (x) { return x.status === "blocked"; }).slice(0, 1));
  }

  function styleBar(sel) {
    ensure(sel);
    return '<fieldset class="grp tb4style"><legend>How Aero tends to play (optional)</legend><div class="note" style="margin:0 0 6px">Only changes which suggestions come first. Nothing is learned from your play.</div><div class="row" style="flex-wrap:wrap;gap:6px">' +
      Object.keys(STYLE_LABEL).map(function (k) { return '<button type="button" class="chip mini" data-tb4style="' + k + '" aria-pressed="' + (sel.style === k) + '">' + STYLE_LABEL[k] + "</button>"; }).join("") + "</div></fieldset>";
  }
  var STLABEL = { known_legal: "fits the rules", needs_adjudication: "GM checks", blocked: "not now" };
  function extras(cat, c, sel, avail) {
    ensure(sel);
    var meta = CATS.filter(function (x) { return x.id === cat; })[0]; if (!meta) return "";
    var sg = meta.group ? suggest(c, cat, sel.style, avail) : [], h = "";
    if (sg.length) h += '<div class="tb4sugg" data-tb4cat-sugg="' + cat + '"><span class="note" style="margin:0">Suggested:</span> ' + sg.map(function (x) {
      return '<button type="button" class="chip mini' + (x.status === "blocked" ? " off" : "") + '" data-tb4pick="' + esc(x.group + "|" + x.id) + '"' + (x.status === "blocked" ? " disabled" : "") +
        ' title="' + esc(x.reason) + '">' + esc(x.label) + ' <small class="tag">' + STLABEL[x.status] + "</small></button>"; }).join(" ") + "</div>";
    h += '<label class="tb4custom" style="display:block;margin-top:6px"><small>Custom ' + esc(meta.label.toLowerCase()) + " · " + esc(meta.hint) + '</small><input class="txt" id="w_tb4_' + cat + '" data-tb4cat="' + cat + '" placeholder="Your own words" value="' + esc(sel.tb4custom[cat] || "") + '"></label>';
    return h;
  }
  function secondaryFieldset(c, sel, avail) {
    return '<fieldset class="grp"><legend>Secondary activity</legend>' + extras("secondary", c, sel, avail) + "</fieldset>";
  }
  function customList(sel) {
    ensure(sel);
    return CATS.map(function (k) { var t = String(sel.tb4custom[k.id] || ""); return t.trim() ? { category: k.id, text: t.trim() } : null; }).filter(Boolean);
  }
  function hasCustom(sel) { return customList(sel).length > 0; }
  // Adds the customs to a combat declaration. Literal text is kept as written; unmapped carries it to the GM.
  function apply(d, sel) {
    var list = customList(sel);
    if (!list.length) return d;
    d.tb4 = { schema: "genesis-turn-builder/4", custom: list };
    d.unmapped = (d.unmapped || []).slice();
    list.forEach(function (x) { if (d.unmapped.indexOf(x.text) < 0) d.unmapped.push(x.text); });
    d.freeform = [d.freeform || ""].concat(list.map(function (x) { return x.text; })).filter(Boolean).join(" ");
    return d;
  }
  function summary(sel) {
    return customList(sel).map(function (x) { var k = CATS.filter(function (y) { return y.id === x.category; })[0]; return k.label + " (custom): " + x.text; }).join("; ");
  }
  function restore(d, sel) {
    ensure(sel); var used = [];
    ((d.tb4 && d.tb4.custom) || []).forEach(function (x) { if (CATS.some(function (k) { return k.id === x.category; })) { sel.tb4custom[x.category] = x.text; used.push(x.text); } });
    return used;   // texts that belong to custom boxes, so the caller can keep them out of its general note
  }
  // Event wiring; hooks: onSoft(fn) for typing, onChanged() for a re-render.
  function bind(root, sel, hooks) {
    ensure(sel);
    Array.prototype.forEach.call(root.querySelectorAll("[data-tb4cat]"), function (el) {
      el.addEventListener("input", hooks.soft(function (v) { sel.tb4custom[el.getAttribute("data-tb4cat")] = v; }));
    });
    Array.prototype.forEach.call(root.querySelectorAll("[data-tb4style]"), function (b) {
      b.addEventListener("click", function () { sel.style = b.getAttribute("data-tb4style"); hooks.changed(); });
    });
    Array.prototype.forEach.call(root.querySelectorAll("[data-tb4pick]"), function (b) {
      b.addEventListener("click", function () {
        var p = b.getAttribute("data-tb4pick").split("|"), inp = root.querySelector('input[data-g="' + p[0] + '"][value="' + (window.CSS && CSS.escape ? CSS.escape(p[1]) : p[1]) + '"]');
        if (inp && !inp.disabled) { if (inp.type === "checkbox") inp.checked = !inp.checked; else inp.checked = true; inp.dispatchEvent(new Event("change", { bubbles: true })); }
      });
    });
  }
  return { CATS: CATS, enabled: enabled, suggest: suggest, styleBar: styleBar, extras: extras, secondaryFieldset: secondaryFieldset,
           apply: apply, hasCustom: hasCustom, summary: summary, restore: restore, bind: bind, customList: customList };
})();
if (typeof module !== "undefined") module.exports = GenesisTB4;
