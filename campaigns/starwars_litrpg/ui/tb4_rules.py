"""TB4 campaign grants behind owner switches (removable: delete this file and its call in export_state.build).

tb4_taunt (owner ruling 2026-11-17, development/TB4_WHISPER_PROGRESS.md):
  Taunt costs 1 bonus action; the player's exact words or gesture are kept. Contested check: the taunter's Charisma
  (Intimidation or Deception, the player's choice) against the target's Wisdom (Insight). On a success the target has
  disadvantage on attack rolls against anyone other than the taunter until the start of the taunter's next turn.
  No forced attack, no mind control: the target still acts from its own motives. Ties go to the target.
"""
TAUNT_ID = "taunt"
TAUNT_OPTION = {
    "id": TAUNT_ID, "slot": "bonus_action", "label": "Taunt",
    "detail": "Bonus action, your own words. Your Charisma (Intimidation or Deception) vs its Wisdom (Insight). "
              "If you win, it has disadvantage on attacks against anyone but you until your next turn. It still chooses what it does.",
    "needs_target": True, "requires": [], "cost": "bonus_action", "aliases": ["taunt", "provoke", "goad", "jeer at"],
    "granted_by": "campaign switch tb4_taunt (owner ruling 2026-11-17)",
}


def apply_switches(turn_context, switches):
    """Return a copy of the public turn context with switched-on grants added. Never removes or changes GM options."""
    if not turn_context or not switches:
        return turn_context
    tc = dict(turn_context)
    if switches.get("tb4_taunt") is True and tc.get("mode") == "combat":
        options = list(tc.get("options") or [])
        if not any(o.get("id") == TAUNT_ID for o in options) and any(v.get("hostile") for v in tc.get("visible") or []):
            options.append(dict(TAUNT_OPTION))
        tc["options"] = options
    return tc


def resolve_taunt(taunter_total, target_total):
    """Contested check. Returns the ruled effect for the GM to commit (as condition_change on the target)."""
    if not isinstance(taunter_total, int) or not isinstance(target_total, int):
        raise ValueError("both totals must be accepted roll totals (ints)")
    success = taunter_total > target_total
    return {"success": success,
            "effect": ({"condition": "taunted", "by": "taunter", "until": "start of the taunter's next turn",
                        "mechanic": "disadvantage on attack rolls against anyone other than the taunter",
                        "compels": False} if success else None),
            "ties": "target"}
