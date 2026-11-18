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
    var re = STYLES[style || ""] || null, out = [], seen = {};
    candidates(c, cat).forEach(function (k, i) {
      var a = (avail || {})[k.key], st = !a ? "known_legal" : /not_here/.test(a.status) ? "blocked" : /needs_step|needs_choice|unknown|risky/.test(a.status) ? "needs_adjudication" : "known_legal";
      var score = (st === "known_legal" ? 20 : st === "needs_adjudication" ? 10 : 0) + (re && re.test(k.id + " " + k.label) ? 5 : 0) - (k.id === "hold" ? 3 : 0);
      out.push({ id: k.id, group: k.group, label: k.label, status: st, reason: a && a.reasons && a.reasons[0] || "", score: score, order: i });
    });
    out.sort(function (x, y) { return y.score - x.score || x.order - y.order || (x.id < y.id ? -1 : 1); });
    out = out.filter(function (x) { var key = String(x.label).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
      if (seen[key]) return false; seen[key] = true; return true; });
    return out.filter(function (x) { return x.status !== "blocked"; }).slice(0, 4).concat(out.filter(function (x) { return x.status === "blocked"; }).slice(0, 1));
  }

  // M11: plans are derived only from public, published capabilities. They are proposals,
  // never grants or adjudication. The existing availability/validator owns costs and reach.
  function plans(c, sel, avail) {
    var seen = {}, out = [], foes = (c.visible || []).filter(function (v) { return v.hostile; });
    ["action", "bonus_action", "movement", "object"].forEach(function (cat) {
      suggest(c, cat, sel.style, avail).forEach(function (x) {
        var key = String(x.label).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
        if (x.status === "blocked" || x.id === "hold" || seen[key]) return;
        var slot = cat === "action" ? "action" : cat === "bonus_action" ? "bonus_action" : cat === "movement" ? "movement_ft" : "object_interaction";
        if (c.mode === "combat" && c.budget && c.budget[slot] === 0) return;
        seen[key] = true;
        var defensive = /dodge|disengage|cover|retreat|guard/i.test(x.id + " " + x.label);
        var reason = x.reason || (cat === "movement" ? "Published route; reach and opportunity risks are checked." : "Available capability in this scene; edit before submitting.");
        if (foes.length && defensive) { x.score += 4; reason = "Known threat: " + foes.map(function (v) { return v.label; }).join(", ") + ". " + reason; }
        var support = null, label = x.label;
        // A defensive activity plus a published retreat/cover route is a real composite
        // plan only when the shared validator accepts the whole proposed combination.
        // This never moves an NPC, invents a destination, or silently selects a target.
        var T = typeof GenesisTurn !== "undefined" ? GenesisTurn : (typeof require === "function" ? require("../turn_contract.js") : null);
        if (cat === "action" && defensive && foes.length && T) {
          (c.movement || []).some(function (m) {
            if (m.id === "hold" || !/back|retreat|cover/i.test(m.id + " " + m.label)) return false;
            var d = T.emptyDecl(c); d.actions = [{option:x.id}]; d.movement = {option:m.id};
            try { if (!T.validate(d, c).legal) return false; } catch (e) { return false; }
            support = {group:"movement", id:m.id}; label += "; " + m.label; return true;
          });
        }
        var source = (c.options || []).filter(function (o) { return o.id === x.id; })[0];
        if (source && (source.needs_target || source.needs_trigger)) {
          x = Object.assign({}, x, {status:"needs_adjudication"});
          reason += source.needs_target ? " Choose your target." : " Specify your trigger.";
        }
        out.push(Object.assign({}, x, { label:label, category: cat, reason: reason, support:support }));
      });
    });
    return out.sort(function (a, b) { return b.score - a.score || a.order - b.order; }).slice(0, 4);
  }
  function intentPanel(c, sel, avail) {
    var ps = plans(c, sel, avail), selected = (c.options || []).filter(function (o) { return o.id === sel.action; })[0];
    var h = '<section class="grp" id="intentPlans"><h3 style="margin:0">What do you want to achieve?</h3><p class="note">Choose a starting plan or write your intention. Edit it and combine supporting activities below. Nothing executes until you submit; custom costs need GM review.</p>';
    h += '<div data-tb4cat-sugg="action">' + ps.map(function (x) {
      return '<button type="button" class="btn" style="display:block;width:100%;text-align:left;white-space:normal;margin:6px 0" data-tb4pick="' + esc(x.group + "|" + x.id) + '"' + (x.support ? ' data-tb4support="' + esc(x.support.group + "|" + x.support.id) + '"' : "") + '><b>' + esc(x.label) + '</b><small style="display:block">' + esc(x.reason) + ' · ' + STLABEL[x.status] + '</small></button>';
    }).join("") + '</div>';
    h += '<div class="note">Current plan: ' + esc(selected ? selected.label : "No primary action selected") + (sel.movement && sel.movement !== "hold" ? " · " + esc(((c.movement || []).filter(function (m) { return m.id === sel.movement; })[0] || {}).label || sel.movement) : "") + '</div>';
    if (selected) h += '<button type="button" class="btn" data-tb4pick="action|">Clear primary action</button>';
    h += extras("action", c, sel, avail);
    return h + '</section>';
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
    var h = "";
    if (cat === "bonus_action" && sel.bonus === "taunt" && (c.options || []).some(function (o) { return o.id === "taunt"; })) h += tauntFields(c, sel);
    h += '<label class="tb4custom" style="display:block;margin-top:6px"><small>Custom ' + esc(meta.label.toLowerCase()) + " · " + esc(meta.hint) + '</small><input class="txt" id="w_tb4_' + cat + '" data-tb4cat="' + cat + '" placeholder="Your own words" value="' + esc(sel.tb4custom[cat] || "") + '"></label>';
    return h;
  }
  // Taunt (switch tb4_taunt; owner ruling 2026-11-17). Only shown when the published context grants the option.
  function tauntFields(c, sel) {
    var t = sel.taunt = sel.taunt || { target: "", words: "", skill: "intimidation" };
    var foes = (c.visible || []).filter(function (v) { return v.hostile; });
    return '<div class="tb4taunt" style="margin:6px 0 0 4px"><label><small>Taunt whom</small><select class="txt" id="w_tb4_taunt_target" data-tb4taunt="target"><option value="">Choose a target</option>' +
      foes.map(function (v) { return '<option value="' + esc(v.id) + '"' + (t.target === v.id ? " selected" : "") + ">" + esc(v.label) + (v.distance_ft != null ? " (~" + v.distance_ft + " ft)" : "") + "</option>"; }).join("") + "</select></label>" +
      '<label><small>How (your check)</small><select class="txt" id="w_tb4_taunt_skill" data-tb4taunt="skill"><option value="intimidation"' + (t.skill !== "deception" ? " selected" : "") + '>Intimidation</option><option value="deception"' + (t.skill === "deception" ? " selected" : "") + ">Deception</option></select></label>" +
      '<label><small>Your exact words or gesture</small><input class="txt" id="w_tb4_taunt_words" data-tb4taunt="words" placeholder="What Aero says or does to draw it" value="' + esc(t.words) + '"></label>' +
      '<div class="note" style="margin:2px 0 0">Contested: your Charisma vs its Wisdom (Insight). If you win, it has disadvantage on attacks against anyone but you until your next turn. It still decides what it does.</div></div>';
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
    var list = customList(sel), b = (d.bonus_actions || [])[0];
    if (b && b.option === "taunt") {
      var t = sel.taunt || {};
      b.target = t.target || null;
      d.tb4 = d.tb4 || { schema: "genesis-turn-builder/4", custom: [] };
      d.tb4.taunt = { target: t.target || null, skill: t.skill === "deception" ? "deception" : "intimidation", words: String(t.words || "").trim() };
    }
    if (!list.length) return d;
    d.tb4 = d.tb4 || { schema: "genesis-turn-builder/4" }; d.tb4.custom = list;
    d.unmapped = (d.unmapped || []).slice();
    list.forEach(function (x) { if (d.unmapped.indexOf(x.text) < 0) d.unmapped.push(x.text); });
    d.freeform = [d.freeform || ""].concat(list.map(function (x) { return x.text; })).filter(Boolean).join(" ");
    return d;
  }
  function summary(sel) {
    var t = sel.bonus === "taunt" && sel.taunt && sel.taunt.words ? ["Taunt (" + (sel.taunt.skill || "intimidation") + "): “" + String(sel.taunt.words).trim() + "”"] : [];
    return t.concat(customList(sel).map(function (x) { var k = CATS.filter(function (y) { return y.id === x.category; })[0]; return k.label + " (custom): " + x.text; })).join("; ");
  }
  function restore(d, sel) {
    ensure(sel); var used = [];
    if (d.tb4 && d.tb4.taunt) sel.taunt = { target: d.tb4.taunt.target || "", skill: d.tb4.taunt.skill || "intimidation", words: d.tb4.taunt.words || "" };
    ((d.tb4 && d.tb4.custom) || []).forEach(function (x) { if (CATS.some(function (k) { return k.id === x.category; })) { sel.tb4custom[x.category] = x.text; used.push(x.text); } });
    return used;   // texts that belong to custom boxes, so the caller can keep them out of its general note
  }
  // Event wiring; hooks: onSoft(fn) for typing, onChanged() for a re-render.
  function bind(root, sel, hooks) {
    ensure(sel);
    var catalogue = root.querySelector("#mechanicsCatalog");
    if (catalogue) catalogue.addEventListener("toggle", function () { sel.catalogOpen = catalogue.open; if (hooks.persist) hooks.persist(); });
    Array.prototype.forEach.call(root.querySelectorAll("[data-tb4cat]"), function (el) {
      el.addEventListener("input", hooks.soft(function (v) { sel.tb4custom[el.getAttribute("data-tb4cat")] = v; }));
    });
    Array.prototype.forEach.call(root.querySelectorAll("[data-tb4taunt]"), function (el) {
      var k = el.getAttribute("data-tb4taunt"), set = function (v) { sel.taunt = sel.taunt || {}; sel.taunt[k] = v; };
      if (el.tagName === "SELECT") el.addEventListener("change", function () { set(el.value); hooks.changed(); });
      else el.addEventListener("input", hooks.soft(set));
    });
    Array.prototype.forEach.call(root.querySelectorAll("[data-tb4style]"), function (b) {
      b.addEventListener("click", function () { sel.style = b.getAttribute("data-tb4style"); hooks.changed(); });
    });
    Array.prototype.forEach.call(root.querySelectorAll("[data-tb4pick]"), function (b) {
      b.addEventListener("click", function () {
        var p = b.getAttribute("data-tb4pick").split("|"), inp = root.querySelector('input[' + (/objects|reactions/.test(p[0]) ? "data-c" : "data-g") + '="' + p[0] + '"][value="' + (window.CSS && CSS.escape ? CSS.escape(p[1]) : p[1]) + '"]');
        if (inp && !inp.disabled) { if (inp.type === "checkbox") inp.checked = !inp.checked; else inp.checked = true; inp.dispatchEvent(new Event("change", { bubbles: true })); }
        var support = b.getAttribute("data-tb4support");
        if (support) { var q = support.split("|"), move = root.querySelector('input[data-g="' + q[0] + '"][value="' + q[1] + '"]');
          if (move && !move.disabled) { move.checked = true; move.dispatchEvent(new Event("change", {bubbles:true})); } }
      });
    });
  }
  return { plans: plans, intentPanel: intentPanel, CATS: CATS, enabled: enabled, suggest: suggest, styleBar: styleBar, extras: extras, secondaryFieldset: secondaryFieldset,
           apply: apply, hasCustom: hasCustom, summary: summary, restore: restore, bind: bind, customList: customList };
})();
if (typeof module !== "undefined") module.exports = GenesisTB4;
