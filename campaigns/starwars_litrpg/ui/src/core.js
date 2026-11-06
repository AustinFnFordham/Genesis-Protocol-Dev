(function () {
  "use strict";
  var view = null, actions = [], dbRef = null, status = "connecting", err = "";
  var $ = function (id) { return document.getElementById(id); };
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function ls(k, v) { try { if (v === undefined) return localStorage.getItem(k) || ""; localStorage.setItem(k, v); } catch (e) { return ""; } return ""; }
  var selId = ls("datapad.member") || "aero";
  function roster(v) { return v.roster && v.roster.length ? v.roster : [{ id: "aero", name: v.character.name, line: v.character.line, role: "You", status: "Active", mechanics: "authoritative" }]; }
  function selected(v) { var r = roster(v); return r.filter(function (m) { return m.id === selId; })[0] || r[0]; }
  function isActor(v, m) { return m.id === (v.active_actor || "aero"); }
  /* Viewing a character never changes who acts: the composer always acts as the active actor. */
  function selector(v) {
    var r = roster(v), m = selected(v);
    var opts = r.map(function (x) { return '<option value="' + esc(x.id) + '"' + (x.id === m.id ? " selected" : "") + ">" + esc(x.name) + (x.role ? " (" + esc(x.role) + ")" : "") + "</option>"; }).join("");
    return '<div class="panel"><h2>Party</h2><select class="member-sel" aria-label="Party member" style="width:100%;min-height:44px;font:inherit;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:4px;padding:0 10px">' + opts + "</select>" +
      (isActor(v, m) ? "" : '<div class="note" style="margin-top:8px">Viewing only. You still act as ' + esc(r[0].name) + ". You cannot control this character.</div>") + "</div>";
  }
  function pendingSheet(m) {
    return '<div class="panel"><h1 style="font-size:18px;margin:0">' + esc(m.name) + '</h1><div class="note">' + esc(m.line) + "</div>" +
      (m.note ? "<p>" + esc(m.note) + "</p>" : "") + "</div>" +
      '<div class="panel"><h2>Mechanical sheet</h2><div class="empty">Pending validation. Stats, powers and equipment are not shown until the build is validated and linked into the record.</div></div>';
  }

  /* ---------- rendering (pure function of `view` + `actions`) ---------- */
  function bar(cls, cur, max) { return '<div class="bar ' + cls + '"><i style="width:' + Math.max(0, Math.min(100, max ? cur / max * 100 : 0)) + '%"></i></div>'; }
  function paras(text) {
    return String(text).split(/\n{2,}/).map(function (p) {
      var say = /^["“]/.test(p.trim());
      return "<p" + (say ? ' class="say"' : "") + ">" + esc(p.trim()).replace(/\*(.+?)\*/g, "<em>$1</em>") + "</p>";
    }).join("");
  }

  function renderLeft(c, v) {
    var m = selected(v);
    if (m.mechanics !== "authoritative") return selector(v) + pendingSheet(m);
    c = v.character;
    var f = c.force, pips = "";
    for (var i = 0; i < f[1]; i++) pips += '<i class="' + (i < f[0] ? "on" : "") + '"></i>';
    var sc = Object.keys(c.scores).map(function (k) { var v = c.scores[k]; return "<div><small>" + k + "</small><b>" + v[0] + "</b><em>" + (v[1] >= 0 ? "+" : "") + v[1] + "</em></div>"; }).join("");
    return selector(v) + '<div class="panel"><div class="portrait"><b>AD</b><small>Portrait pending</small></div>' +
      '<h1 style="font-size:18px;margin:10px 0 0">' + esc(c.name) + '</h1><div class="note">' + esc(c.line) + " · Level " + esc(c.level) + "</div></div>" +
      '<div class="panel"><h2>Status</h2>' +
      '<div class="stat"><span>HP</span>' + bar("hp", c.hp[0], c.hp[1]) + "<b>" + c.hp[0] + "/" + c.hp[1] + "</b></div>" +
      '<div class="stat"><span>Strain</span>' + bar("st", c.strain[0], c.strain[1]) + "<b>" + c.strain[0] + "/" + c.strain[1] + "</b></div>" +
      '<div class="stat"><span>Force</span><div class="pips">' + pips + "</div><b>" + f[0] + "/" + f[1] + "</b></div>" +
      '<div class="kv"><span>Armor class</span><span>' + c.ac + '</span></div><div class="kv"><span>Speed</span><span>' + esc(c.speed) + '</span></div>' +
      '<div class="kv"><span>Initiative</span><span>+' + c.initiative + '</span></div>' +
      '<div class="kv"><span>Passive Perception / Insight</span><span>' + c.passive.perception + " / " + c.passive.insight + "</span></div>" +
      '<div class="kv"><span>Conditions</span><span>' + (c.conditions.length ? esc(c.conditions.join(", ")) : "none") + "</span></div>" +
      (v.continuity ? '<div class="kv"><span>Protagonist Continuity</span><span>' + esc(v.continuity.status === "active" ? "protected" : v.continuity.status) + (v.continuity.marks ? " · " + v.continuity.marks + " mark" + (v.continuity.marks > 1 ? "s" : "") : "") + "</span></div>" +
        (v.continuity.status === "expiring" ? '<div class="note msg-warn">Protection ends at the end of your next long rest. After that, death is permanent.</div>' : "") : "") +
      '<div class="scores">' + sc + "</div></div>" +
      '<div class="panel"><h2>Skills</h2><div class="tags">' + c.skills.map(function (s) { return '<span style="font-style:normal;font-family:var(--f-data);font-size:12px">' + esc(s.name) + " " + (s.mod >= 0 ? "+" : "") + s.mod + "</span>"; }).join("") + "</div>" +
      '<div class="note" style="margin-top:8px">Languages: ' + esc(c.languages.join(", ")) + "</div></div>" +
      '<div class="panel"><h2>Powers</h2><ul class="plain">' + c.powers.map(function (p) { return "<li><details><summary>" + esc(p.name) + ' <span class="pill">' + esc(p.cost) + "</span></summary><p>" + esc(p.effect) + "</p></details></li>"; }).join("") + "</ul></div>" +
      '<div class="panel"><h2>Features</h2><ul class="plain">' + c.features.map(function (p) { return "<li><details><summary>" + esc(p.name) + ' <span class="pill">' + esc(p.kind) + "</span></summary><p>" + esc(p.effect) + "</p></details></li>"; }).join("") + "</ul></div>";
  }

  function renderGear(c, v) {
    var m = selected(v);
    if (m.mechanics !== "authoritative") return selector(v) + '<div class="panel"><h2>Equipment</h2><div class="empty">Pending validation for ' + esc(m.name) + ".</div></div>";
    c = v.character;
    return selector(v) + '<div class="panel"><h2>Weapons</h2><ul class="plain">' + c.weapons.map(function (w) { return '<li><div class="kv"><span>' + esc(w.name) + "</span><span>+" + w.attack + "</span></div><div class='note'>" + esc(w.damage) + "</div></li>"; }).join("") + "</ul></div>" +
      '<div class="panel"><h2>Worn</h2><div class="kv"><span>' + esc(c.armor.name) + "</span><span>AC " + c.armor.ac + "</span></div></div>" +
      '<div class="panel"><h2>Inventory</h2><ul class="plain">' + c.inventory.map(function (i) { return '<li class="kv"><span>' + esc(i.item) + "</span><span>×" + i.qty + "</span></li>"; }).join("") + '</ul><div class="kv" style="margin-top:8px"><span>Credits</span><span>' + c.credits + "</span></div></div>";
  }

  function renderRecord(v) {
    var m = selected(v), own = isActor(v, m);
    var jrn = own ? v.journal : ((v.member_journals || {})[m.id] || []);
    var disc = jrn.filter(function (j) { return j.kind === "observation"; });
    var jr = jrn.slice().reverse().map(function (j) {
      return '<li><div class="row" style="justify-content:space-between"><span class="pill ' + esc(j.knowledge) + '">' + esc(j.knowledge) + '</span><span class="note">' + esc(j.time) + "</span></div><div style='margin-top:4px'>" + esc(j.text) + "</div></li>";
    }).join("");
    return selector(v) + '<div class="panel"><h2>Journal' + (own ? "" : " · " + esc(m.name)) + '</h2><ul class="plain">' + (jr || '<li class="empty">Nothing recorded about ' + esc(m.name) + " yet.</li>") + "</ul></div>" +
      '<div class="panel"><h2>Discoveries</h2><div class="note">' + disc.length + " observed so far. Marked <b>report</b> means what Aero perceived, not confirmed truth.</div></div>" +
      '<div class="panel"><h2>Objectives</h2>' + (v.objectives.length ? "<ul class='plain'>" + v.objectives.map(function (o) { return "<li>" + esc(o) + "</li>"; }).join("") + "</ul>" : '<div class="empty">None established. The GM has not set one, and you are free to choose your own.</div>') + "</div>" +
      '<div class="panel"><h2>Party</h2><ul class="plain">' + roster(v).map(function (p) { return '<li class="kv"><span>' + esc(p.name) + "</span><span>" + esc(p.role) + (p.mechanics === "pending" ? " · sheet pending" : "") + "</span></li>"; }).join("") + '</ul><div class="note" style="margin-top:8px">Companions join through play.</div></div>' + renderUsage(v);
  }
