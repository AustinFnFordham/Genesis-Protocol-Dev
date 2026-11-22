// Genesis CC-003 Soul narration seam (noncanonical sandbox).
// Soul only DESCRIBES outcomes the engine has already accepted. It receives a frozen list of facts copied from the
// accepted log, never the state, never the dice function. Output is display text; nothing it returns is read back
// by the engine. A future AI narrator plugs in as `provider(facts) -> string | Promise<string>`; its text is shown
// only if `guard` finds no number, name or outcome that is absent from the facts. Deterministic fallback otherwise.
(function (root, factory) { if (typeof module === "object" && module.exports) module.exports = factory(); else root.GenesisSoul = factory(); })(this, function () {
  "use strict";
  function deepFreeze(o) { if (o && typeof o === "object" && !Object.isFrozen(o)) { Object.freeze(o); Object.keys(o).forEach(function (k) { deepFreeze(o[k]); }); } return o; }
  var KEEP = ["ev", "attacker", "defender", "target", "actor", "pid", "total", "nat", "crit", "adv", "dis", "counter", "augment", "amount", "hp", "hp_max", "win", "turned", "receipt", "text", "speech"];
  // facts(turnLog, names) -> frozen array of plain facts (a copy; the log itself is never handed out)
  function facts(turnLog, names) {
    return deepFreeze(turnLog.filter(function (l) { return l.ev || l.speech; }).map(function (l, i) {
      var f = { i: i }; KEEP.forEach(function (k) { if (l[k] !== undefined) f[k] = JSON.parse(JSON.stringify(l[k])); });
      ["attacker", "defender", "target", "actor"].forEach(function (k) { if (f[k]) f[k + "_name"] = names[f[k]] || f[k]; });
      return f;
    }));
  }
  function pick(list, key) { var h = 0; for (var i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) | 0; return list[Math.abs(h) % list.length]; }
  var MOVE = { saber_strike: ["the indigo blade snaps through a tight arc", "a clean cut of indigo light", "the saber hums into a short, honest line"],
               unarmed_strike: ["a palm strike drives in", "an Echani heel-strike lands"], flow_strike: ["the body follows the blade — an Echani kick rides the same motion", "his weight rolls through into a flowing Echani strike"],
               npc_blade: ["the vibroblade darts in low", "a Makashi thrust, precise as a needle"], npc_riposte: ["the vibroblade answers before the parry has even finished"], riposte: ["the blade comes back on the rebound"],
               bite: ["jaws snap shut", "the stalker lunges, teeth first"], pounce: ["the stalker explodes out of cover"] };
  function verb(pid, key) { return pick(MOVE[pid] || ["the strike comes in"], key); }
  function hpWord(f) { var r = f.hp / f.hp_max; return f.hp === 0 ? "and it ends there" : r <= 0.25 ? "barely on their feet now" : r <= 0.5 ? "badly hurt" : "still standing"; }

  // Deterministic fallback narration: one short paragraph per meaningful beat, each tagged with the fact indices it used.
  function fallback(F) {
    var out = [], i = 0;
    while (i < F.length) {
      var f = F[i], key = String(f.receipt || f.i);
      if (f.ev === "contest" && f.pid === "feint") {
        out.push({ from: [i], text: f.win ? f.actor_name + " sells the false line — " + f.target_name + " commits to it, and the opening is real." : f.target_name + " reads the feint and refuses to bite." }); i++; continue;
      }
      if (f.ev === "contest") { out.push({ from: [i], text: f.win ? f.actor_name + " wins the bind." : f.target_name + " holds firm against " + f.actor_name + "." }); i++; continue; }
      if (f.ev === "disarm") { out.push({ from: [i], text: f.actor_name + " binds the blade and twists — " + f.target_name + "'s weapon spins away." }); i++; continue; }
      if (f.ev === "takedown") { out.push({ from: [i], text: f.actor_name + " binds, strips and sweeps; " + f.target_name + " hits the ground without a weapon." }); i++; continue; }
      if (f.ev === "attack") {
        var used = [i], j = i + 1, parts = [];
        var lead = (f.counter ? "Instantly, " : "") + verb(f.pid, key) + (f.adv && f.adv.length ? " into the opening (" + f.adv.join(", ") + ")" : "") + (f.dis && f.dis.length ? ", but awkwardly (" + f.dis.join(", ") + ")" : "");
        while (j < F.length && (F[j].ev === "parry" || F[j].ev === "damage" || F[j].ev === "miss" || F[j].ev === "down" || F[j].ev === "dodge")) {
          var g = F[j]; used.push(j);
          if (g.ev === "parry") parts.push(g.turned ? g.actor_name + "'s parry turns it aside" : g.actor_name + " parries, but too late");
          if (g.ev === "damage") parts.push((g.crit ? "a perfect strike — " : "") + g.target_name + " takes it (" + g.amount + "), " + hpWord(g));
          if (g.ev === "miss" && !parts.length) parts.push("it finds only air");
          if (g.ev === "down") parts.push(g.actor_name + " goes down");
          j++;
        }
        out.push({ from: used, text: cap(lead) + (parts.length ? "; " + parts.join("; ") : "") + "." }); i = j; continue;
      }
      if (f.ev === "riposte") { i++; continue; }   // folded into the counter attack's line
      if (f.ev === "close") { out.push({ from: [i], text: f.actor_name + " closes the distance." }); i++; continue; }
      if (f.ev === "revealed") { out.push({ from: [i], text: "Something moves — " + f.actor_name + " is there." }); i++; continue; }
      if (f.ev === "stand") { out.push({ from: [i], text: f.actor_name + " scrambles back up." }); i++; continue; }
      if (f.ev === "down") { out.push({ from: [i], text: f.actor_name + " is down." }); i++; continue; }
      if (f.speech) { out.push({ from: [i], text: f.text }); i++; continue; }
      i++;
    }
    return out;
  }
  function cap(t) { return t.charAt(0).toUpperCase() + t.slice(1); }

  // guard: reject provider text that states numbers or names not present in the facts (it may not invent outcomes).
  function guard(text, F) {
    var nums = {}, names = {};
    F.forEach(function (f) { ["total", "amount", "hp", "hp_max", "nat"].forEach(function (k) { if (f[k] != null) nums[f[k]] = 1; }); ["attacker_name", "defender_name", "target_name", "actor_name"].forEach(function (k) { if (f[k]) names[f[k].split(" ")[0]] = 1; }); });
    var bad = (String(text).match(/\d+/g) || []).filter(function (n) { return !nums[n]; });
    return { ok: bad.length === 0, problems: bad.length ? ["numbers not in the accepted facts: " + bad.join(", ")] : [] };
  }

  // narrate(turnLog, names, {provider}) -> {source, beats, facts}. Synchronous fallback; async when a provider is given.
  function narrate(turnLog, names, opts) {
    opts = opts || {}; var F = facts(turnLog, names || {}), beats = fallback(F);
    var res = { source: "deterministic fallback", beats: beats, facts: F };
    if (!opts.provider) return res;
    return Promise.resolve().then(function () { return opts.provider(F); }).then(function (txt) {
      var g = guard(txt, F); return g.ok ? { source: "provider", beats: [{ from: F.map(function (f) { return f.i; }), text: String(txt) }], facts: F } : Object.assign(res, { provider_rejected: g.problems });
    }, function () { return Object.assign(res, { provider_rejected: ["provider failed"] }); });
  }
  return { narrate: narrate, facts: facts, fallback: fallback, guard: guard };
});
