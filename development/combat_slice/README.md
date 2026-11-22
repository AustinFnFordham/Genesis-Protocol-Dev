# CC-002 sandbox combat slice — Aero, Level 1 (noncanonical)

Implements the playable slice of `Contracts/CINEMATIC_COMBAT_AND_MANEUVER_CONTRACT_v0.2.md` (CC-002) and the
execution-profile parts of `Contracts/CHARACTER_CAPABILITY_AND_MASTERY_CONTRACT_v0.1.md`, both on
`docs/cinematic-combat-capability-v0.2-20261121`. Branch: `dev/cc002-combat-slice`. **Nothing here is canonical**: no
campaign, sheet, ledger, gateway, staging environment or turn-contract/3 behaviour is changed.

## Play it
- **Local / Codespaces:** `python3 -B development/preview/serve_preview.py` → `http://127.0.0.1:8080/combat.html`
  (in a Codespace: Ports → 8080, keep it private, add `/combat.html`). Linked from the preview banner.
- **Standalone file:** `python3 development/combat_slice/build_playtest.py` → `development/combat_slice/out/combat.html`
  (open in any browser; no network).
- Scenarios: **Aero vs a skilled duelist** (Ilsa Vohr, Makashi vibroblade: Feint, Parry, Riposte, Bind) and **Aero vs
  an unfamiliar predator** (hidden vrask stalker: pounce, uncertain perception, no free Animal Handling).
- Tap cards to build an ordered turn; ▲▼ reorder; ⓘ inspects a card (rules, source, approval status). Every step is
  checked live by the engine. Reactions (Parry, Riposte, readied Dodge, opportunity attacks) are offered when they
  trigger — the game pauses and asks; nothing is chosen for Aero. Sandbox switches and a seed are at the top.

## What is built
| Piece | File | Notes |
|---|---|---|
| Shared resolver | `engine.js` | One `validatePlan` / `resolveTurn` for every actor (player and NPC). Pure state in, state out. Seeded dice with receipts; a paused turn resumes by replaying from the same snapshot, so earlier rolls are identical (no rerolls are possible). |
| Execution profiles | `catalog.json` | Cost (compound allowed), trigger, requirements (weapon, ignition, reach/range, target kind, visibility, understanding, prior melee attack, conditions), resolution (attack / contest / AC bonus / disadvantage / perception), effect, usage cap, status, source. |
| Fixtures | `scenarios.json` | Aero (numbers from `api_bridge/gm/aero_character_runtime.yml`), Ilsa Vohr, vrask stalker. |
| Card Turn Builder | `playtest_src.html` → `build_playtest.py` | Touch-first, keyboard-accessible, 44 px targets, theme-aware; quick view (cost, availability reason, range, budget); Combo Judge (Atomic facts only) + optional cinematic note (no mechanics). |
| NPC policies | `engine.js npcPlan / npcReaction` | Decide *what* to try; the same validator decides whether it is legal. |
| Tests | `test_engine.cjs` (27), `test_playtest_ui.cjs` (30) | In `development/run_all_checks.sh`. |
| Inventory | `inventory.py` | Read-only table below. |

### Turn rules the engine enforces
Budget per turn: Main 1, Bonus 1, Secondary 1 (SA-001 switch; off = 0 and Secondary profiles refused `SA001_DISABLED`),
Reaction 1 per round (refreshes at the start of the actor's own turn), 30 ft movement, 1 object interaction, free speech.
Literal zero stays zero. Reactions cannot be declared as turn steps (`REACTION_ONLY`). Steps are walked in order on a
projection at preflight and revalidated against real state at execution (a step that became impossible is refused and
logged). Reaction windows inside an attack: declared (readied Dodge) → would hit (Parry) → missed (Riposte). A Riposte
can never trigger a Riposte (counter fence + `trigger_depth_max: 1`); a spent Reaction stays spent. Leaving an enemy's
reach provokes an opportunity attack for either side. Advantage does not stack. Hidden creatures are not targetable and
never appear in the public view (no name, id or DC); a Tactical Glance can find them. Enemy HP is shown as a condition word.

## Contract §7 test matrix (all automated)
Feint (contest, advantage, no auto-hit, no spam) · Riposte · Parry · readied Dodge (and declining keeps the Reaction) ·
Flow Strike (only after a melee attack; once) · disarm by bind (no damage) and recovery · resource exhaustion and
literal zero for every budget · off-turn counter ordering · double-counter loop prevention · free speech vs Taunt ·
setup after the target moves (feint opening closes) · loss of weapon mid-chain (preflight and execution; disarmed
defender gets no saber reactions) · concealment · Force augmentation (1 FP, +1d4, once, learned strikes only) · exact
receipt replay and pause/resume equality · SA-001 disabled legacy · NPC/PC parity (same refusal codes, same costs, an NPC
cannot use a profile it lacks) · the GM never picks a player reaction · predator: pounce with advantage, Taunt refused
(`CANNOT_UNDERSTAND`), only untrained Animal Handling · full duel played to the end, every dice line cites a receipt.
Browser: combo building, live reorder legality, inspect modal, reactions answered in-page, full duel to the end on
desktop, predator turn first, SA-001 off, iPad/phone no horizontal scroll and every control ≥ 44 px.

## Aero: original vs candidate grants
| Capability | On the sheet today | In this sandbox | Status |
|---|---|---|---|
| Lightsaber strike +5, 1d8+3 | yes | same | sheet |
| Echani unarmed +5, 1d4+3 | yes | same | sheet |
| Battle Insight (Main, 0 FP, 30 ft) | yes | same; **Bonus version behind a switch, off** | sheet / proposal |
| Taunt (Bonus contest) | owner ruling 11-17 | same | sheet |
| Dodge action | core action | same | sheet |
| Animal Handling | **not trained** (WIS +2) | untrained only | sheet |
| Deception | not trained (CHA +2) | used untrained for Feint | sheet value |
| Acrobatics | not trained (DEX +3) | used untrained for Blade Bind | sheet value |
| Echani Flow Strike (Bonus, +5, 1d4, after a melee attack) | no | new Bonus profile | **proposal** |
| Weapon Feint (Secondary contest → advantage) | no | Weapons-Master Apprentice | **proposal** |
| Parry (Reaction, +2 AC vs a melee hit, blade lit) | no | replaces the draft's superiority die + Dex | **proposal** |
| Riposte (Reaction on a missed melee attack) | no | one strike, fenced | **proposal** |
| Readied Dodge (Secondary + Reaction: disadvantage) | no | Novice tier | **proposal** |
| Blade Bind & Strip (Main contest → disarm, no damage) | no | technique | **proposal** |
| Tactical Glance (Secondary Perception, once/turn) | no | | **proposal** |
| Force-Guided Strike (1 FP → +1d4 attack) | no | augmentation | **proposal** |
Not granted, deliberately: Sentry subclass, Advanced/Master tiers, any Dodge percentage, Reflex Cascade, Fear, Starship
Telekinesis, Minor Telekinesis cost change, Animal Handling, Investigation training.

## Form × weapon configuration
Lore only in this slice — no form grants a numeric bonus. A technique is usable only if the actor holds a compatible
configuration *and* has the technique granted; forms list which techniques they would teach.

| Form | Compatible configurations | Techniques it would teach (slice) | Gate |
|---|---|---|---|
| I Shii-Cho | single, two-handed, crossguard, saberstaff, dual | — | |
| II Makashi | single, curved hilt, crossguard | feint, riposte, blade bind, parry | |
| III Soresu | single, two-handed, shoto | parry | |
| IV Ataru | single, two-handed, shoto | — | |
| V Shien / Djem So | single, two-handed, reverse grip | riposte | |
| VI Niman | single, dual, saberstaff | — | |
| VII Juyo / Vaapad | single, two-handed | — | advanced training only |
| Jar'Kai | dual | — | |
| Sokan | single, two-handed | — | |
| Tràkata | single, dual | — | blade-deactivation timing not authored |
| Echani Flow | unarmed, single | flow strike, readied dodge | |
| Pistol CQB | blaster pistol | — | ranged profiles not authored here |
Vibroweapon, rifle, sniper, repeater, improvised and thrown styles: not authored in this slice (see blockers).

## Execution profile schema (as implemented)
```
{ name, maneuver, technique?, status: sheet | sandbox_proposal, source, rules,
  cost: { main?, bonus?, secondary?, reaction?, movement_ft?: n | "distance", object?, fp? },
  trigger?: attack_declared_on_me | melee_hit_on_me | melee_miss_on_me,      // reactions only
  requires: { weapon_kind?, held?, ignited?, reach_ft?, range_ft?, target?: enemy|beast|self, visible?, understands?,
              target_holds_weapon?, after_melee_attack_this_turn?, condition?, secondary_action?, switch?, weapon_dropped? },
  resolution?: { type: attack|contest|ac_bonus|disadvantage|perception, bonus?, damage?, damage_type?, melee?, counter?,
                 advantage?, actor_skill?, target_skill? },
  effect?: { on_success? | sets? | on_use?, note },  cap?: { group, per: turn, max } }
```

## Existing maneuver drafts (generated by `inventory.py`)
Power.schema.json power_type enum: ['Force', 'Tech']

| Draft | power_type | Casting time | Needs superiority dice | Starship-scale | Validation errors | Used in slice |
|---|---|---|---|---|---|---|
| `power_analyze_weakness` | Maneuver | 1 Action |  |  | 0 |  |
| `power_angle_deflector_shields` | Maneuver | 1 Maneuver |  | yes | 0 |  |
| `power_boost_shields` | Maneuver | 1 Action |  | yes | 0 |  |
| `power_calculated_strike` | Maneuver | 1 Bonus_Action |  |  | 0 |  |
| `power_commanders_strike` | Maneuver | 1 Action |  |  | 0 |  |
| `power_damage_control` | Maneuver | 1 Action |  | yes | 0 |  |
| `power_disarming_blow` | Maneuver | 1 Action | yes |  | 0 | reworked → blade_bind (contest; no damage) |
| `power_emergency_shield` | Maneuver | 1 Reaction |  | yes | 0 |  |
| `power_evasive_footwork` | Maneuver | 1 Maneuver | yes |  | 0 |  |
| `power_evasive_maneuvers` | Maneuver | 1 Action |  | yes | 0 |  |
| `power_feinting_attack` | Maneuver | 1 Bonus_Action | yes |  | 0 | reworked → feint (contest, no superiority die) |
| `power_fire_weapon` | Maneuver | 1 Action |  | yes | 0 |  |
| `power_flyby` | Maneuver | 1 Action |  | yes | 0 |  |
| `power_full_speed` | Maneuver | 1 Action |  | yes | 0 |  |
| `power_guarded_stance` | Maneuver | 1 Action |  |  | 0 |  |
| `power_parry` | Maneuver | 1 Reaction | yes |  | 0 | reworked → parry (+2 AC, no superiority die) |
| `power_reposition` | Maneuver | 1 Action | yes | yes | 0 |  |
| `power_riposte` | Maneuver | 1 Reaction | yes |  | 0 | reworked → riposte (Reaction on a missed melee attack) |
| `power_spot_the_weakness` | Maneuver | 1 Action | yes |  | 0 |  |
| `power_squadron_command` | Maneuver | 1 Action | yes | yes | 0 |  |
| `power_target_priority` | Maneuver | 1 Bonus Action | yes |  | 0 |  |
| `power_trip_attack` | Maneuver | Special (part of attack) | yes |  | 0 |  |
| `power_wait_for_opening` | Maneuver | 1 Action |  |  | 0 |  |

Quarantined catalog `maneuvers_comprehensive`: errors ['no stable id/urid']

Mapping errors found: all 23 drafts use `power_type: "Maneuver"`, which is not in `Power.schema.json` (`Force`, `Tech`),
yet their candidate validation reports 0 errors (the candidate validator does not check that enum). Casting times are
inconsistent (`1 Maneuver`, `1 Bonus_Action`, `1 Bonus Action`, `Special (part of attack)`). 13 depend on superiority
dice that no Genesis character has. 10 are starship-scale and belong in a separate catalog. The 27-entry quarantined
catalog has no stable id/urid. Nothing was promoted; four drafts were *reworked* into sandbox profiles above.

## Decisions that need the owner
1. Adopt or change each **sandbox proposal** above (cost, numbers, trigger): Flow Strike, Feint, Parry (+2 AC),
   Riposte, Readied Dodge, Blade Bind, Tactical Glance, Force-Guided Strike (1 FP → +1d4), Battle Insight as Bonus.
2. **SA-001 Secondary action**: enable for a sandbox ruleset only, or never; migration for run 2.
3. **Feint formulation**: Deception vs Insight contest (as built) vs a fixed DC or passive Insight; reward when ignored.
4. **Parry** model: +2 AC (built) vs damage reduction; Dodge risk die (not built) and the 50/66.7/83.3/98% hypotheses.
5. Aero's **Level-1 grants** justified by Taron / Echani training (the "Weapons-Master Apprentice" list).
6. **Force augmentation** catalogue and cost budget (only one augmentation exists here).
7. Called Shot / wound / nonlethal rules (not built), creature anatomy differences.
8. Cinematic Momentum, Director's Cut and Legendary Moment (not built beyond a descriptive note).
9. The two fixture opponents' stat lines (sandbox numbers).

## Blockers and limits (honest)
- Ranged, firearm, vibroweapon-style, thrown and starship profiles are not authored; Lightsaber Deflect (ranged) is on
  the sheet but no ranged attacker exists in these fixtures.
- Geometry is a simple distance map (close / withdraw), not a grid; no cover or terrain.
- Burst and Minor Telekinesis are not cards here (Minor Telekinesis cost changes need approval; Burst is AoE).
- No Mastery Graph, evidence accumulation or advancement (contract §3–4 of the capability contract): out of scope here.
- Not connected to the gateway, ledger or Datapad; integrating the accepted runtime is a separate, owner-approved step.
- Interactive verification is headless Chromium (desktop, iPad and phone viewports); not yet tried on a physical device.
