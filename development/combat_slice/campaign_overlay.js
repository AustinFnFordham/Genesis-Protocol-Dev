// Campaign-grant overlays (CC-005b). Turns an owner campaign ruling file (e.g. creator/jedi_fundamentals.json) into the
// data newState(opts.overlays) applies. Nothing here edits a character sheet or powers_known.
(function (root, factory) { if (typeof module === "object" && module.exports) module.exports = factory(); else root.GenesisOverlay = factory(); })(this, function () {
  "use strict";
  function fromJediFundamentals(rule) {
    var m = /campaign:\s*([a-z0-9_]+)/.exec(rule.scope || "");
    return { rule: rule.rule, version: rule.version, status: rule.status, approved: rule.approved, campaign: m ? m[1] : null, doc: "campaigns/starwars_litrpg/" + rule.doc,
             profile: "minor_telekinesis", granted_to: (rule.granted_to || []).map(function (g) { return { character: g.character, granted_by: g.granted_by }; }) };
  }
  return { fromJediFundamentals: fromJediFundamentals };
});
