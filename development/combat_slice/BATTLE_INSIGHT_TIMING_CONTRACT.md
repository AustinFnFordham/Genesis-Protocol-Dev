# Battle Insight: duration and concentration — what's missing (CC-007 E)

**Status:** this is a statement of the missing contract, not a mechanic. The engine's behaviour is unchanged (owner R-4: "retain existing behaviour where a detail is still unresolved"). This is open decision D-13.

## 1. The source

`api_bridge/gm/aero_character_runtime.yml` → powers → Battle Insight:
- action, 30 ft, **concentration, up to 1 minute**;
- "advantage on his next attack against it";
- it ends:
  - after that attack;
  - if concentration breaks;
  - if the target becomes invalid;
  - after 1 minute;
- `rules_status`: "adopted duration override; source duration is 1 round".

## 2. What the engine does today (pinned by `test_cc007.cjs` E)

| Behaviour | Where in the engine |
|---|---|
| The effect is the condition `insight = {by}` on the **target** | `execStep` |
| Advantage applies only to the caster's attack **against that target** | `attack()`, line `bi.by === attacker` |
| The effect is removed by that attack, hit or miss | `delete D.conds.insight` |
| It is **not** removed by a contest (Feint, Bind) or by other actors' attacks | — |
| It **persists across rounds** until it is used | — |
| There is no duration, and no concentration state on the caster | — |
| Two Battle Insights on two different targets can be active at once | — |

## 3. Why it can't be implemented yet

| Needed | Present? |
|---|---|
| A round-to-time mapping (1 minute = N rounds) | **No.** `s.round` counts rounds, but no source in the repo states how long a round lasts. `ENCOUNTER_RULING.md` defines turn order only. |
| A concentration state per caster (at most one effect) | **No.** No power or profile in the catalog tracks concentration. |
| Concentration-break triggers: damage (with a save?), incapacitation or going down, casting another concentration power | **Partly.** `down` exists. There are no Constitution saves, no concentration save rule, and no other concentration powers. |
| A definition of an "invalid target" (down? hidden? beyond 30 ft? out of sight?) | **No** authoritative definition. |

## 4. The contract that's needed (proposal for owner review)

1. **`ruleset.round_seconds`:** the source and the value, for example 6. Without it, "1 minute" can't become rounds.
2. **`actor.concentration = {pid, target, started_round, expires_round}`:** at most one at a time. Starting a second one ends the first.
3. **Break rules:**
   - the caster goes down or is incapacitated: ends;
   - the caster takes damage: a save needs a sourced DC and ability, or the owner decides damage never breaks it at this tier;
   - the caster casts another concentration power: ends.
4. **Target validity:** owner choice from down, hidden (lost sight), or beyond 30 ft at the start of the caster's turn.
5. **Expiry check** at `startTurn` of the caster, against `expires_round`, with an event `concentration_ended {why}`.
6. **Projection:** the player sees their own concentration and the rounds left. Enemies see only its effects.

## 5. Until then

The current behaviour stays: the effect lasts until used. The tests pin it, so any later change is deliberate and visible.
