# Combat rules inventory and dice reconciliation audit — 2026-11-24

**Branch:** `dev/cc005-server-verify`, audited at `e2127f8`.
**Kind of work:** read-only. No mechanics, UI, dice behaviour, tests or campaign data were changed. Hask Meadow, `shared-0002` and Oracle were not touched. The Crucible branch was read through a temporary detached worktree, which was removed afterwards; it was not merged.

**Evidence conventions**
- Paths are repository-relative.
- `engine.js`, `catalog.json`, `scenarios.json` and the other unqualified file names are in `development/combat_slice/`.
- "Sheet" means `api_bridge/gm/aero_character_runtime.yml`.
- "Live turn contract" means `campaigns/starwars_litrpg/creator/TURN_CONTRACT.md` (turn-contract/3).

---

## 0. Summary

1. **What Aero can do.** Aero has **32 profiles** in the combat slice:
   - **20 sheet profiles**, from `scenarios.json` → `aero.grants.sheet`;
   - **11 sandbox proposals**, from `aero.grants.sandbox_proposal`;
   - **1 campaign grant:** `minor_telekinesis`, through `campaign_overlay.js`, only when the session campaign is `starwars_litrpg`.

   Nine more profiles are NPC fixtures.

2. **Three different rule layers are in play, and they are not the same thing:**

   | Layer | What it is | Rule authority? |
   |---|---|---|
   | Live turn contract | One action, one bonus, one reaction, movement, one free object interaction. **No Secondary.** | Yes: live campaign rules |
   | Sandbox ruleset `cc-sandbox-0.5` (`catalog.json` → `ruleset`) | Adds the SA-001 Secondary budget and several proposals. These are **on by default in the sandbox**. | No |
   | Thin client (`player_api.js` and the page) | Display of the server's view | No |

3. **The d20 combat dice are fully server-authoritative and replayable.** The engine never invents a die. The Atomic service draws every value from a secret seed and records the roller's identity. Every roll has a receipt, and the player sees a projection of it.

4. **Narrative Consequences d6 is a different system from the combat slice.** It lives in the Python experimental resolver (`development/experimental_resolution/`) and was **owner-adopted for `hask_meadow_r2` on 2026-11-15** for the player's own eligible d20 rolls.
   - **Implemented:** rolling the d6 and mapping it to Threat or Advantage points.
   - **Not implemented:** anything that **spends or applies** those points (`causal.committed_effects` is always `[]`).
   - **Not connected** to the JS combat engine or the Atomic service.

5. **Crucible dice (d6 and d8) are design candidates only.**
   - Both test files pass.
   - Every published probability matches my independent enumeration, including the d6 Variant A gate figures, which have no test.
   - Nothing on that branch is active, and nothing was merged.

6. **Discrepancies:** section 6 lists 14. The most important:
   - The **Feint advantage does not expire at the end of the turn** (D-3).
   - Minor Telekinesis repositioning is a sandbox adaptation beyond the ruling (D-1).
   - The SA-001 source document is not in the repository (D-9).

---

## 1. Inventory of Aero's actions

**Cost keys** come from `catalog.json` `profiles.<id>.cost`. The budget per turn is `catalog.json` `ruleset.budget`: Main 1, Bonus 1, Secondary 1, Reaction 1, Movement 30 ft, Object 1.

**Category** is server-assigned by `player_api.js` `categoryOf()` (CC-006 B).

**Status codes** (as defined in the brief):

| Code | Meaning |
|---|---|
| **1** | Source-backed and implemented |
| **2** | Explicitly approved campaign ruling |
| **3** | Approved provisional rule or campaign grant |
| **4** | Sandbox-only proposal or adaptation |
| **5** | Partially implemented |
| **6** | Unresolved or awaiting the owner |

### 1.1 Sheet profiles (`aero.grants.sheet`)

| Profile id · name | Category · cost | Requirements and targeting (`requires`) | Roll and opposition (`resolution`) | Effect | Source | Status | Test evidence |
|---|---|---|---|---|---|---|---|
| `saber_strike` · Lightsaber Strike | attack · Main 1 | lightsaber held and lit; enemy within 5 ft | `1d20+5` vs AC; hit: `1d8+3` energy | Damage. Can carry Force augmentation (+1d4, 1 FP). Sets `melee_attacked`, which unlocks `flow_strike`. | Sheet weapons, Taron-forged lightsaber (+5, 1d8+3) | **1** | test_engine, test_cc003, test_cc004, test_cc005b, test_cc005_server, test_atomic_flow, test_play_ui |
| `saber_strike_2h` · two-handed | attack · Main 1 | as above, plus `offhand_free` (no blaster in hand, not grappling) | `1d20+5`; `1d10+3` energy | Damage | Sheet: versatile, two-handed 1d10+3 | **1** | test_cc004, test_playtest_ui |
| `unarmed_strike` · Echani Strike | attack · Main 1 | enemy within 5 ft; no empty hand needed (GEP C5) | `1d20+5`; `1d4+3` kinetic | Damage; `melee_attacked` | Sheet: unarmed strike, "does not require an empty hand" | **1** | test_engine, test_cc004, test_cc005_server, … |
| `blaster_shot` · Blaster Pistol Shot | attack · Main 1 | sidearm held, ammo ≥ 1, enemy ≤ 160 ft | `1d20+5`; `1d6+3` energy; disadvantage beyond 40 ft (`rangeMods`). With the **opt-in** switch, also disadvantage with a hostile within 5 ft. | Uses one shot | Sheet: Standard Blaster Pistol +5, 1d6+3, 40/160, capacity 12 | **1** (switch: **4**) | test_cc004, test_cc005b |
| `dodge_action` · Dodge Action | maneuver · Main 1 | self | — | `effect.sets: dodging`: attacks against Aero have disadvantage; cleared at Aero's next `startTurn` | "SRD core action (turn-contract/3 core actions)" | **1** | **No test references this profile** |
| `battle_insight` · Battle Insight | maneuver (Setup) · Main 1 | visible enemy within 30 ft | — | Sets `insight` on the target; Aero has advantage on his next attack against it; consumed by that attack (`attack()`) | Sheet powers: Battle Insight (level 0, action, 0 FP, concentration 1 min, "adopted duration override; source duration is 1 round") | **5**: concentration and the 1-minute expiry are not implemented; it lasts until consumed | test_engine, test_cc004 |
| `taunt` · Taunt | maneuver (Provoke) · Bonus 1 | visible enemy within 30 ft that understands speech | contest: Intimidation (+4) vs Insight; **ties go to the target** | `taunted`: disadvantage on its attacks against anyone but Aero until Aero's next turn | `catalog.json` cites "Owner ruling 2026-11-17 (switch tb4_taunt)" and `ui/tb4_rules.py` | **2** | test_engine |
| `calm_beast` · Calm the Animal (untrained) | main · Main 1 | beast within 30 ft | contest: Animal Handling +2 vs its Wisdom | `wary`: disadvantage on its next attack | Sheet: no Animal Handling proficiency | **1** | **No test references this profile** |
| `move` · Move | movement · `movement_ft` | not grappled; "close" needs a visible target | — | Close: costs (distance − 5) ft and ends at 5 ft. Withdraw: 15 ft. Leaving reach provokes an opportunity attack (`doMove`). Grappling releases the hold. | SRD movement | **5**: the distance model is pairwise and abstract (close or withdraw only; no grid or positions) | test_engine, test_cc004, test_cc005b, test_cc005_server, test_cc005b_server, test_play_ui |
| `speak` · Speak | free · none | — | — | Logged speech; no debuff | Live turn contract: "ordinary speech is free" | **1** | test_engine |
| `recover_weapon` · Recover Weapon | movement · Object 1 + 10 ft | own weapon dropped | — | Picks up the dropped weapon; **a lightsaber comes back unlit**. If the weapon was flung by telekinesis, the cost is 30 ft (`availability`). | SRD object interaction plus movement | **1** (the 10 ft drop distance and the unlit return are fixture or sandbox choices: **4**) | test_engine, test_atomic_flow, test_cc005_server, test_cc005b, test_play_ui |
| `toggle_blade` · Ignite / Deactivate | object · Object 1 | holding the lightsaber | — | Toggles `ignited` | Live turn contract: objects | **1** | test_engine, test_cc004, test_cc005b |
| `draw_sidearm` · Draw Blaster | object · Object 1 | sidearm holstered | — | Sidearm held; the off hand is then occupied | Sheet: carry, right hip, left-hand draw | **1** | test_cc004, test_cc005_server |
| `holster_sidearm` · Holster Blaster | object · Object 1 | sidearm held | — | Frees the off hand | core object interaction | **1** | test_cc004 |
| `reload_sidearm` · Reload Blaster | main · Main 1 | held, not full, reserve ≥ 1 | — | Refills to 12 from reserve | Sheet: "reload: action", capacity 12 | **1** | test_cc004 |
| `burst` · Burst | main (Force power) · Main 1 | — | each other creature within 5 ft rolls a DEX save vs DC 12 (`areaSave`); fail: `1d4` force damage and prone | Allies are hit too; Aero is excluded | Sheet power Burst: "save, self-exclusion, success result and prone rider are **adopted table rulings**" | **2** (level, cost and damage **1**) | test_cc004 |
| `grapple` · Echani Grapple | attack (Grapple) · Main 1 | enemy within 5 ft, `offhand_free`, not already grappled by Aero | contest: martial check +5 (`actor_bonus`) vs the target's better of Athletics or Acrobatics; ties go to the target | `grappled`: speed 0; ended when Aero moves | Sheet: Echani Grappling Training ("special melee attack", +5, free hand) | **5**: no size limit, no contested escape, no drag at half speed; costs Main (the sheet says "special melee attack") | test_cc004 |
| `lightsaber_deflect` · Lightsaber Deflect (Tier 1) | reaction · Reaction 1 · trigger `ranged_energy_hit_on_me` | lightsaber held and lit | reduction `1d10+2`; at 0, redirect `1d20+5` vs the chosen target's AC | Damage reduction. The redirect target is **chosen by the player** from visible creatures within 30 ft, or declined. A redirect hit deals the original rolled damage. | Sheet: Lightsaber Deflect - Tier 1 (corrected in CC-005, GEP C6) | **1** | test_cc004, test_cc005_server |
| `force_connection` · Force Connection (focused) | main (Force sense) · Main 1 | enemy within 30 ft | — | Sets `focused_read`. **No mechanical effect in combat:** no combat roll uses Insight. | Sheet: Force Connection, focused | **1** (inert here) | test_cc004 |
| `sentinel_balance` · Sentinel Balance | reaction · trigger `failed_dex_or_cha_save` | — | `save_bonus 1d4` | `inert_note`: no encounter forces Aero to save, so it never triggers | Sheet: 2 uses per long rest | **5**: the per-rest counter is not implemented, and the trigger is never reached | **No test references this profile** |

### 1.2 Sandbox proposals (`aero.grants.sandbox_proposal`)

| Profile id · name | Category · cost | Requirements · roll | Effect | Source | Status | Tests |
|---|---|---|---|---|---|---|
| `feint` · Weapon Feint | maneuver · **Secondary 1** | enemy within 5 ft; SA-001 switch · contest Deception (+2) vs Insight; ties go to the target | `feinted`: advantage on Aero's next melee attack on it "this turn" | CC-002 §2 (rework of draft `power_feinting_attack`) | **4** (see D-3: the expiry is wrong) | test_engine, test_cc003, test_cc004, test_atomic_flow, test_play_ui |
| `flow_strike` · Echani Flow Strike | maneuver (Follow-up) · Bonus 1 | after a melee attack this turn; enemy within 5 ft · `1d20+5`, `1d4` | Damage | CC-002 §2 (new Bonus profile) | **4** | wide |
| `parry` · Parry | reaction · trigger `melee_hit_on_me` | lightsaber held and lit · `ac_bonus +2` | Can turn a would-hit into a miss. **Not offered against a critical hit** (`attack()` checks `hit && !crit`). | CC-002 (draft parry reworked; no superiority dice) | **4** | test_engine, test_cc003 |
| `riposte` · Riposte | reaction · trigger `melee_miss_on_me` | lightsaber lit, within 5 ft · `1d20+5`, `1d8+3` | Counterattack. Fenced: a counter can never trigger a counter, and `trigger_depth_max = 1` | Draft `power_riposte` | **4** | test_engine |
| `readied_dodge` · Readied Dodge | maneuver (Dodge) · Secondary 1 | SA-001 | Sets `dodge_ready` until Aero's next turn | CC-002 §2 | **4** | test_engine |
| `dodge_reaction` · Dodge (readied) | reaction · trigger `attack_declared_on_me` | needs `dodge_ready` | The attack has disadvantage | pairs with Readied Dodge | **4** | test_engine, test_cc005_server |
| `blade_bind` · Blade Bind & Strip | maneuver (Disarm) · Main 1 | lit blade, enemy within 5 ft holding a weapon · contest Acrobatics vs the better of Athletics or Acrobatics | `disarmed`: the weapon lands 10 ft away; no damage | CC-002 §4 (rework of `power_disarming_blow`) | **4** | test_engine |
| `controlled_takedown` · Blade Bind & Takedown | maneuver · **compound: Main 1 + Secondary 1** | as Blade Bind, plus SA-001 · one contest | Disarmed **and** prone; a loss spends both actions | CC-003 proposal | **4** | test_cc003 |
| `tactical_glance` · Tactical Glance | secondary (Search) · Secondary 1 | SA-001 · `1d20+4` Perception vs a hidden actor's `stealth_dc` (default 10, engine-side) | Reveals hidden enemies | CC-002 §2 | **4** | test_engine, test_atomic_flow, test_cc005_server, test_cc005b_server |
| `battle_insight_bonus` · Battle Insight (quick) | maneuver · Bonus 1 | switch `battle_insight_bonus`, **off by default** | As Battle Insight | CC-002 §2 proposed conversion | **4** (off) | test_engine |
| `force_augment` · Force-Guided Strike | (step modifier) · FP 1 | switch `force_augmentation`, **on by default in the sandbox**; only on `saber_strike` or `riposte`; once per turn (`cap:augment`) | +1d4 to that attack roll (`extra` die in `rollDice`) | CC-002 §1.7 | **4** | test_engine and test_cc003 (via `augment`) |

### 1.3 Campaign grant: Minor Telekinesis

| Profile id | Category · cost | Implementation | Status |
|---|---|---|---|
| `minor_telekinesis` · Minor Telekinesis (Jedi Fundamentals) | main · Main 1 (0 FP) | `campaign_overlay.js` `fromJediFundamentals`, `engine.js` `newState` (overlay), `tkObject`, `execStep`, `applyProjection` | **3**, with the sandbox adaptations listed in §2 |

Tests: test_cc004, test_cc005b, test_cc005b_server, test_playtest_ui; also `ui/test_campaign_features.py` (campaign side).

### 1.4 NPC fixture profiles (not Aero's; listed for completeness)

`npc_blade`, `npc_parry`, `npc_riposte`, `npc_bind`, `npc_blaster`, `npc_slam`, `bite`, `pounce`. All are `sandbox_proposal` fixtures. Per owner decision D5, the relay droid's HP 7 / AC 13 are fixture values only.
- **No tests:** `npc_parry`, `npc_riposte`, `npc_slam`.
- **Tested:** the others appear in test_engine, test_cc003, test_cc004 or test_cc005_server.

### 1.5 Rules that cut across all actions (`engine.js`)

- **Budget and turn start (`startTurn`):**
  - The acting actor's budget is restored.
  - `dodging`, `dodge_ready` and `taunted` expire when their `until` actor's turn starts.
  - A prone actor stands up and loses 15 ft of movement.
- **Plan validation:** `validatePlan` walks the plan step by step against a projection (`project` / `applyProjection` / `spend`). Each step is judged at the distances, weapon state and budget left by the earlier steps. `availability()` holds the refusal codes (`OUT_OF_REACH`, `NO_MAIN`, `SA001_DISABLED`, `HAND_OCCUPIED`, `WEAPON_FAR`, and so on).
- **Revalidation:** `execStep` re-runs `availability` against the real state before each step and refuses rather than shrinking the step.
- **Advantage and disadvantage (`hasAdv`, `rangeMods`):**

  | Gives advantage | Gives disadvantage |
  |---|---|
  | `resolution.advantage` (ambush) | attacker prone |
  | attacker hidden | target `dodging` |
  | prone target (melee only) | readied dodge |
  | feint (melee, by the same attacker) | taunted (vs anyone but the taunter) |
  | Battle Insight | `wary` |
  | | long range |
  | | ranged-in-melee (switch) |

  Advantage and disadvantage together cancel to a normal roll.
- **Critical hits and fumbles (`attack()` / `rollDice`):**
  - A natural 1 always misses; a natural 20 always hits and is a critical.
  - **A critical doubles the damage dice count** (`n * (opts.crit ? 2 : 1)`), and Parry is not offered against it.
  - **Source:** none is cited in `catalog.json` or on the sheet. This is an engine convention (D-12).
- **Contests (`contest()`):** `win = a.total > t.total`, so **every contest tie goes to the defender**. The source states this only for Taunt (D-11).
- **Reactions:** one per round (`reaction_left`). Reaction windows inside `attack()` come in this order:
  1. `attack_declared_on_me` (readied dodge);
  2. `melee_hit_on_me` (parry);
  3. `ranged_energy_hit_on_me` (deflect);
  4. `melee_miss_on_me` (riposte).

  `opportunity_attack` is a separate window in `doMove`. Player reactions pause the turn (`decide` → `Pause`), and NPC reactions follow the policy (`npcReaction`).
- **Synergies:** `catalog.json` `synergies`, with the predicted ones computed by `E.synergies`. They are only predictions; they never grant a bonus. Confirmed combos come from **resolved events** (`confirmedCombos`).
  - With a feint step: `echani_flow_line`, `opening_cut`, `opening_strike`.
  - Without a feint: `blade_and_body`, `unarmed_flow`, `read_and_strike`, and the rest of the list.
- **Compound cost:** `player_api.preflight` flags any step whose profile is `compound` or costs more than one of Main, Secondary, Bonus and Reaction. Today that is `controlled_takedown`.

---

## 2. Provenance and authority: the points the brief called out

### 2.1 Minor Telekinesis, detail by detail

**Sources:** `campaigns/starwars_litrpg/creator/JEDI_FUNDAMENTALS.md` and `jedi_fundamentals.json` (rule `jedi_fundamentals_minor_telekinesis` v1, `approved_provisional`, owner ruling 2026-11-11). Owner decision D1 of 2026-11-22 (`CC005B_DECISIONS.md`) approved the overlay mechanism.

| Detail | Ruling says | Engine does | Status |
|---|---|---|---|
| Who | Explicit `granted_to` entry plus completed Jedi training. Aero qualifies through the sheet (`current_rank: Newly Knighted Jedi`, council ruling). | The overlay grants it only when the session campaign is `starwars_litrpg` **and** the character is named. Client-supplied overlays are ignored. | **3** (approved) |
| Why it isn't a Force power | It is a feature by recorded exception. It does not count against `powers_known` (2: Battle Insight and Burst) and is not Force Pull or Force Push. The drafts `power_force_pull` and `power_force_push` stay unpromoted. | It is not on the sheet and not in `grants`. `not_on_sheet` explains it, and no Pull or Push profile exists. | **3** |
| Cost | "In combat: it takes the character's **action**", with **0 Force Points** | `cost: {main: 1}`; `limits.force_point_cost: 0` | **3**. Mapping "action" to Main is an interpretation: the live contract's "action" is the sandbox's Main. |
| Target | One visible, **unattended** object (not held, worn, carried or fixed) | Only **dropped weapons** count in this slice. Held weapons are refused (`ATTENDED_OBJECT`). Visibility is not checked separately (dropped weapons are assumed visible). | **3**, scope narrowed by the fixture |
| Weight | ≤ 10 lb | Checks `weight_lb`, but **no fixture weapon has a weight**, so the engine defaults to 3 lb (`dw.weight_lb \|\| 3`) | **4** (fixture assumption) |
| Range | Within 30 ft, and the object **stays within 30 ft while moved** | Retrieve: refused if the weapon is `far`. Reposition: refused if (distance to the owner + 10) > 30. **There is no check that the object's end position stays within 30 ft of Aero** (the distance model has no object positions). | **5** |
| Retrieve own weapon | Allowed ("retrieve … bring it to hand") | Returns the weapon to hand; **a lightsaber comes back unlit** | Retrieval is **3**. The unlit return is a **4** sandbox choice, not stated in the ruling (D-2). |
| Reposition another creature's dropped weapon | "Reposition" is allowed. It must never disarm, take attended objects, or move or restrain a creature. | Allowed only for a weapon already **dropped**, so it cannot disarm. It sends the weapon "30 ft away" (`O.dropped.far = true`). | Repositioning an unattended object is **3**. The specific *30 ft further* displacement is **4**. |
| 30-ft recovery consequence | Not in the ruling. The ruling only says "consequences stay real". | The owner must spend **30 ft of movement** instead of 10 to recover the weapon (`WEAPON_FAR`), and the NPC policy respects it. | **4, awaiting the owner (D-1). Not promoted.** Labelled pending owner review in `COMBAT_V05B.md` §1 and in the profile's `rules` text. |
| Roll | Out of combat: no roll unless uncertain. Default roll (open item 1): d20 + forcecasting modifier + PB (+4) vs a hidden DC, **not owner-set** | No roll in combat (it simply is the action) | **6**: the open-item default is not implemented here |
| Hands | Open item 2; default: no free hand needed | No hand requirement | **6** (follows the default) |
| Holding an object aloft | Open item 3; default: takes the action each round | Not modelled | **6** |

### 2.2 Ranged-in-melee disadvantage

The switch `ranged_in_melee_disadvantage` defaults to **off**.
- Its provenance is recorded in `catalog.json`: "common d20 convention; NOT on Aero's runtime sheet". Owner decision D4 of 2026-11-22: opt-in sandbox only.
- Exceptions are implemented in `rangeMods` and tested in `test_cc005b.cjs`.
- **Status: 4.**

### 2.3 Action economy: Secondary is not Bonus

| Layer | Budget |
|---|---|
| **Live turn contract** (`TURN_CONTRACT.md`) | `action`, `bonus_action`, `reaction`, `movement_ft`, `object_interaction`. **There is no Secondary.** |
| **Sandbox** (`ruleset.budget`) | Main, **Secondary**, Bonus, Reaction, Movement 30 ft, Object |

- **Secondary** is **SA-001**, a distinct prospective budget (GEP-001 §1 and C7). It is **not** a renamed Bonus.
  - The `secondary_action` switch defaults to **on** in the sandbox. Turning it off sets Secondary to 0 and refuses Secondary profiles (`SA001_DISABLED`).
  - **The SA-001 contract itself is not in this repository.** It is referenced, but no file defines it (D-9).
- **Bonus** profiles that exist in the source or the sandbox: `taunt` (sheet / ruling), `flow_strike` (proposal) and `battle_insight_bonus` (proposal, off).
- **Secondary** profiles (all proposals): `feint`, `readied_dodge`, `tactical_glance`, and half of `controlled_takedown`.

### 2.4 Reactions, compound maneuvers and Force augmentation

- **Reactions:** one per round, with a trigger fence and `trigger_depth_max: 1`. The source reactions are `lightsaber_deflect` and `sentinel_balance`. The proposals are `parry`, `riposte` and `dodge_reaction`.
- **Compound:** `controlled_takedown` (Main + Secondary, one contest, both spent on a loss). It is a proposal and depends on SA-001.
- **Force augmentation:** a sandbox proposal. It is on by default in the sandbox and costs 1 FP for +1d4 to `saber_strike` or `riposte`, once per turn.
  - It is **not** available on `saber_strike_2h`. The proposal's `augments` list omits that profile.
  - It is not a Resolve or Crucible resource (GCD-001 §2 keeps them separate).

---

## 3. Dice audit

### 3.A The d20 combat dice that run today

**How one roll travels, from declaration to narration (bound session, player token only):**

1. **Declaration.** The client sends `/atomic/preflight {plan}`. `player_api.preflight` calls `E.validatePlan`, `E.knowledge` and `P.analyzePlan`, and returns legality, costs, odds *ranges* and synergies. Nothing is rolled.
2. **Commit.** The client sends `/atomic/commit {turn_key, actor, plan}`.
   - `atomic_service.commit` checks the token, the turn and the plan lock.
   - The worker (`atomic_engine_worker.cjs`) rebuilds the state from the journal and validates the plan again in the server's own state (`ILLEGAL_PLAN`, `NOT_YOUR_TURN`, `GM_PLAN_MISMATCH`).
3. **Dice request.**
   - `resolveTurn` runs until `rollDice` → `drawDice` finds no value at the next `seq`.
   - `drawDice` then throws `NeedDice {from, dice:[{seq, sides}], step, rules, target, actor, purpose, formula, mode, crit, extra}`.
   - The worker reports it as the pending `need`, including the roller's identity (player or GM).
4. **Roll.** The client sends `/atomic/roll`. `atomic_service.roll` refuses:
   - dice that aren't needed (`NOT_NEEDED`, so no rolling ahead to peek);
   - the wrong roller (`ROLLER_MISMATCH`);
   - a wrong role (`FORBIDDEN_ROLE`).

   Values come from `die_value(seed, seq, sides)`, a mulberry32 port matching `engine.js` `localDie`, using the **server's secret seed**. They are journalled with `roll_id`, roller, turn and rules version.
   - **Idempotency:** the same `seq` returns the stored values. `acceptDice` treats the same seq with the same value as a no-op and refuses anything else.
5. **Resolution.**
   - The replay consumes the tape and produces a **receipt** per roll: `receipt`, `seq`, `first_seq`, `authority: "atomic"`, `vs`, `kind`, `actor`, `purpose`, `formula`, `mode`, `rolls`, `kept`, `extra`, `total`.
   - It also produces committed log events such as `ev: attack | damage | parry | deflect | redirect | contest | save | down …`.
   - Player reactions pause the turn (`decide` → `/atomic/decide`).
6. **Verification.** `gm_step` and `complete` compare the server's reconstruction with the client and record `verify ok:true|false`.
7. **Projection.** `engine.playerProjection` and `player_api.playerView` strip enemy HP and AC, replace other sides' `pid` values, and rewrite damage text. Learned AC bounds come from the player's side's own resolved attacks.
8. **Narration.** Soul (`soul.js`) narrates **only the visible, accepted events** on the server, using `story` in the view. Soul can't change a result; a miss is never narrated as a hit.

**d20 variants that exist today**

| Variant | Formula and mechanics | Who rolls | Where |
|---|---|---|---|
| Attack | `1d20+bonus` vs AC. Advantage or disadvantage selects one of a pair; extra dice add (Force-guided d4). Natural 1 misses, natural 20 hits and crits. | Attacker's controller | `attack()` |
| Damage | profile `damage`; crit doubles the dice count | Attacker | `attack()` |
| Contest | `1d20+skill` against the defender's `1d20+skill`; ties go to the defender; skill advantage via `advantage_on` (Aero: Insight) | Each side rolls its own die | `contest()` |
| Save | `1d20+ability` vs DC (Burst DC 12) | The saving creature | `areaSave()` |
| Deflect reduction | `1d10+2` | Defender | `attack()` |
| Deflect redirect | `1d20+5` vs the chosen target's AC | Defender | `attack()` |
| Search | `1d20+4` vs a hidden actor's `stealth_dc` (the DC stays engine-side) | Searcher | `execStep` (Tactical Glance) |

**Ownership.** Every die records `actor`. The Atomic service maps it to `roller: player | gm`, and a player can never roll GM dice. The player client shows the purpose of pending GM dice only as "waiting on GM".

### 3.B Narrative Consequences d6

**Verdict:** implemented and executable for **rolling and mapping**, but **only partially implemented** as a gameplay system. It is **not connected** to the combat slice.

**Sources**
- `development/experimental_resolution/README.md`
- `policy.py`: `narrative()`, `resolve()`, `public_resolution()`, `assess_causal()`
- `engine.py`: `narrative_face`, lines 184–189
- `campaigns/starwars_litrpg/runs/hask_meadow_r2/experimental_resolution.json`: `canonical: true`, `owner_adopted: 2026-11-15`, `controlled_actors: ["aero"]`, commit `eacb14d`
- `development/gm_provider/gateway.py:272` refuses settings that aren't the default (`UNSUPPORTED_SETTINGS`) unless that marker is active
- `campaigns/starwars_litrpg/CAMPAIGN_CHARTER.md:64` (player party only)

**Trigger**
- The player turns it On per submitted action: `action.resolution_settings.narrative_consequences`. The default is Off, and it is independent of the Regular, Heroic or Legendary temperature setting.
- Eligibility: a **player-controlled** check, attack or save with exactly one positive d20. NPC, hidden and damage rolls are never eligible.

**Outcome rule** (`policy.narrative`)

| d6 face | Result |
|---|---|
| 1 | 2 Threat |
| 2 | 1 Threat |
| 3, 4 | Neutral |
| 5 | 1 Advantage |
| 6 | 2 Advantage |

**Randomness.** A domain-separated mulberry32 stream, seeded from SHA-256 of the domain (`genesis:narrative:v1`), the private campaign seed, the turn, the action id and the roll key. It consumes **zero** ordinary draws and can be replayed from the private record.

**Spending rules: none are implemented.**
- `assess_causal` only *filters* externally supplied candidates. A candidate needs cited `event_ids`, `rule_source`, an `axis`, and a cost of at most the points on that axis, and a domain `validate` callback must accept it.
- It never generates a candidate, spends a point or mutates state, and `committed_effects` is always `[]`.
- "The wider 0–5+ budget model and SID Q15/Q16 remain provisional."

**Relationship to the d20.** It is an independent second axis. It never changes the d20's success, its degree (a margin band) or a critical.

**Missing integration work (not done in this audit)**
1. A spend and effect contract: a catalogue of Advantage and Threat effects, their costs, who chooses, and timing.
2. A candidate source with causal predicates.
3. Atomic commit events for applied effects.
4. Projection of points and effects into the player view.
5. Wiring the combat slice (JS engine and Atomic service) to the setting.
6. A decision on whether it applies to slice combat at all (D-5).

**Do not confuse it with Crucible dice.** Narrative Consequences produces "Advantage/Threat" points from a d6. Crucible's "Spark/Strain/Resolve/Ruin" come from opposed Agency and Entropy pools. They are different systems with different vocabulary.

### 3.C Genesis Crucible dice (design candidates only)

**Branch:** `docs/crucible-dice-whisper-design-v01-20261122` at `f32afce`. It was read in a temporary detached worktree, which has since been removed. **Not merged, not activated.**

**Status of each file**

| File | Status |
|---|---|
| `Contracts/GENESIS_CRUCIBLE_DICE_AND_PRESSURE_DESIGN_v0.1.md` (GCD-001) | "NOT CANONICAL GAMEPLAY"; `genesis-crucible/0.1-candidate` |
| `Contracts/GENESIS_CRUCIBLE_DICE_D8_ALTERNATIVE_v0.1.md` (GCD-001-A) | candidate variants A, B and C |
| `Contracts/GENESIS_SPARK_STRAIN_RESOLVE_RUIN_OUTCOME_CONTRACT_v0.1.md` (SSRR-001) | names and tiers chosen by the owner; mechanics proposed |
| `Contracts/GENESIS_WHISPER_CRUCIBLE_PRESSURE_AND_ADAPTATION_v0.1.md` (WCP-001) | proposal; states what WHISPER does *not* implement |
| `Contracts/examples/crucible_d8_variant_v0.1.json` | `noncanonical_fixture` |
| `Contracts/tests/test_crucible_d8_variant.cjs` | PASS: 5 fixtures, 3 exact rows |
| `Contracts/tests/test_crucible_dice.cjs` (d6) | PASS: 3 exact rows plus guardrail asserts |

**The distinctions the brief asked for**
- **Agency vs Entropy:**
  - Agency dice are the active actor's pool; Entropy dice are resistance, stakes or hazard.
  - These are **not moral sides**: an NPC can roll Agency.
  - Difficulty must not silently reuse d20 AC or DC (GCD-001 §1 step 3).
- **Success vs Cancel Success:**
  - `success_margin = Σ Agency.success − Σ Entropy.cancel_success`.
  - The candidate succeeds when the margin is at least 1, or above a higher domain threshold.
- **Spark vs Strain:**
  - Minor, immediate consequences, positive and negative. They cancel **one-to-one**, so at most one type survives.
  - SSRR-001 says they are **not banked by default**.
  - Strain is **not** a psychological meter (WCP-001 §2).
- **Resolve vs Ruin:**
  - Major, **banked** pools: Resolve belongs to the player or party, Ruin to the GM or scene.
  - **Ruin can never force a player character's free choice.**
- **Minor-symbol cancellation:** `net_spark = max(0, spark − strain)` and `net_strain = max(0, strain − spark)`.
- **Major symbol vs banked point:**
  - Major symbols are uncancellable, but a face-8 (d8) or face-6 (d6) major still adds an ordinary Success or Cancel Success that *can* be cancelled.
  - A symbol appearing is **not** the same as banking a point. Banking needs an earning policy, which is **pending**: the fixture has `bank_policy.auto_bank_major_symbols: false` and `qualification: "pending"`.
- **Optional 3-to-1 conversion:**
  - Only after cancellation, and only from **net** leftovers: 3 net Spark → 1 Resolve, 3 net Strain → 1 Ruin.
  - Converted symbols can't also pay for immediate effects.
  - It is opt-in, and the per-roll caps are pending.

**d6 candidate vs custom d8.** The d8 faces below are copied exactly from the d8 fixture JSON.

| Face | d6 Agency | d6 Entropy | d8 Agency | d8 Entropy |
|---|---|---|---|---|
| 1 | Blank | Blank | Blank | Blank |
| 2 | Success | Cancel | Success | Cancel |
| 3 | Success | Cancel | Success | Cancel |
| 4 | Spark | Strain | Spark | Strain |
| 5 | Success + Spark | Cancel + Strain | Success + Spark | Cancel + Strain |
| 6 | Resolve symbol + Success | Ruin symbol + Cancel | Success + Spark | Cancel + Strain |
| 7 | — | — | **Double Spark** (`spark: 2`) | **Double Strain** (`strain: 2`) |
| 8 | — | — | **Resolve symbol + 1 Success** | **Ruin symbol + 1 Cancel Success** |

**Probabilities.** These figures were recomputed independently by full enumeration for this audit, and all match the documents:

| Pool | Success | Nonzero minor | 3+ net Spark | 3+ net Strain | Any Resolve symbol | Any Ruin symbol | Either major |
|---|---:|---:|---:|---:|---:|---:|---:|
| d6 3v2 | 56.790% | 64.609% | 1.646% | **0%** | 42.130% | 30.556% | 59.812% |
| d8 3v2 | 54.901% | 76.303% | 11.353% | 1.807% | 33.008% | 23.438% | 48.709% |
| d8 4v2 | 73.818% | 81.604% | 22.924% | 0.977% | 41.382% | 23.438% | 55.120% |
| d8 3v3 | 33.749% | 76.894% | 6.938% | 6.938% | 33.008% | 33.008% | 55.120% |

**Variant A gate figures** (d6, 3v2). These are the earning predicates from GCD-001-A, and the published figures **have no test**:

| Outcome | Figure |
|---|---:|
| Qualified Resolve | 22.749% |
| Qualified Ruin | 18.647% |
| Both | 3.344% |

My enumeration reproduces all three exactly.

For reference only, and **not in any source document**: the same predicates applied to d8 3v2 give qualified Resolve 20.242%, Ruin 15.298% and both 2.795%.

**Test-quality findings (read-only; no test was changed)**
- **The d8 test asserts a key that doesn't exist.** `test_crucible_d8_variant.cjs` asserts `!model.banking?.major_face_auto_banked`, but the d8 fixture has no `banking` key; it uses `bank_policy.auto_bank_major_symbols`. The assertion therefore always passes. Fix suggestion: assert `model.bank_policy.auto_bank_major_symbols === false`.
- The d8 test does not check the "either major" column (48.709%, 55.120%); it was verified here.
- No test covers the Variant A gate figures; they were verified here.

---

## 4. Architecture gaps for the alternative dice systems

| Question | What exists and can be reused | What's missing |
|---|---|---|
| **Data structures** | The Atomic tape: `seq`, `sides`, `value`, `roll_id`, `roller`, turn, plan hash, rules version. `NeedDice` / `need`; receipts; journal; `verify` records; `decide` / `Pause`; projection layer; `knowledge()`. The tape takes any number of sides, so d6 or d8 draws work unchanged. | A **symbol-interpreting receipt** (faces → symbol counts → margin, net minor, majors). The d20 receipt has `kept` and `total`; a pool receipt needs `agency[]`, `entropy[]`, `counts`, `success_margin`, `net_spark`, `net_strain`, `majors` and `bank_events`. |
| **Versioned contracts** | `rules_version` in every roll identity (`cc-sandbox-0.5`); `genesis-experimental-resolution/1`; `genesis-crucible-d8-candidate/0.1` (fixture only) | A resolution-mode field that says, per session, which resolver owns a check: `d20` / `crucible-d6` / `crucible-d8` / `sidecar`. GCD-001 forbids mixing tapes implicitly. Also missing: pool account events (`resolve_earned`, `resolve_spent`, `ruin_earned`, `ruin_spent`) with idempotency keys, and a schema for spend menu entries. |
| **Presenting consequence choices** | The `decide` / `Pause` → `/atomic/decide` flow already offers server-built options to the player and journals the choice | Option builders for Spark spends (player) and Strain applications (GM, with causal predicates), and a deadline or ordering for when several are pending |
| **Who selects and spends** (per SSRR-001 and GCD-001 §3) | Roller identity and role tokens; `FORBIDDEN_ROLE` | Spark is spent by the **player**. Strain is applied by the GM or Chaos but must be causally valid. Resolve is a player or party pool with consent. Ruin is a GM or scene pool, bounded, and **never forces a player character's choice**. Enforcement routes and per-role tests are still needed. |
| **Player agency** | The engine never acts for the player character: player reactions always pause | A test like "a Ruin spend never produces a player character's action" before any `rule:whisper`, and versioned gating of that exception (GEP-002 prep) |
| **Hidden GM information** | Player projection; learned bounds; "waiting on GM" for NPC dice; the leak tests (`FORBIDDEN`) | Entropy pool size can reveal difficulty, and the Ruin pool balance is GM-private. The player view needs a rule for each, plus leak tests. |
| **Deterministic, auditable, idempotent, replayable** | Server seed; `die_value`; same seq returns the same values; full replay from the journal; Narrative Consequences' separate deterministic stream that consumes **zero** ordinary draws | Replay must include **spend decisions** as journalled `decide`-style entries. Conversion (3:1) must be a recorded choice event, not something derived silently. |
| **Soul and Chaos** | Soul narrates only visible accepted events; `assess_causal` (Narrative Consequences) shows the "Chaos proposes, Atomic commits" pattern | Typed Spark/Strain/Resolve/Ruin events for Soul to read, and a Chaos candidate generator with source citations. Prose must never create pool deltas (SSRR-001 §7.7). |
| **Thin-client dice rendering** | Roll Theater lanes built from projected receipts; the client never resolves (CC-005c) | Face glyphs (blank, success, cancel, spark ×1/×2, majors), batching for large pools (GCD-001 §6.8), and a "symbol occurred" vs "point banked" display. All of it can be driven from the server receipt. |
| **Coordination with Codex's Oracle GM authorization** | No Oracle, OAuth or gateway code was touched | **Interface proposal:** pool spends and GM dice must carry the authorized gateway actor (GM role) on every Ruin or Strain write, which needs the same authenticated actor binding listed as a gap in `COMBAT_V05B.md` §6. Sandbox role tokens are **not** identity. |

---

## 5. Test coverage summary (read-only runs, 2026-11-24)

| Suite | Result |
|---|---|
| `test_engine.cjs` | 27/27 |
| `test_cc003.cjs` | 21/21 |
| `test_cc004.cjs` | 20/20 |
| `test_cc005b.cjs` | 16/16 |
| `test_atomic_flow.cjs` | pass |
| `test_cc005_server.cjs` | pass |
| `test_cc005b_server.cjs` | pass |
| `test_atomic_service.py` | pass |
| `development/experimental_resolution/test_resolution.py` | OK |
| Crucible `test_crucible_d8_variant.cjs` | PASS |
| Crucible `test_crucible_dice.cjs` | PASS |
| Crucible `test_action_execution_patterns.cjs` | PASS |
| Last full `run_all_checks.sh` | at `e2127f8`: 71 suites, 0 failed |

**Profiles that no test references by id:**
- Aero's sheet: `dodge_action`, `calm_beast`, `sentinel_balance`.
- NPC fixtures: `npc_parry`, `npc_riposte`, `npc_slam`.

**Mechanics with no dedicated test:**
- critical-hit dice doubling;
- Parry not offered against a critical;
- contest tie rules other than Taunt;
- Feint expiry at the end of the turn. This one would fail; see D-3.

---

## 6. Discrepancies: source vs engine

| # | Where | Source says | Engine does | Kind |
|---|---|---|---|---|
| X-1 | `feint` | "advantage on your next melee attack against that target **this turn**" (`effect.note`, `rules`) | `feinted` is removed only when consumed or when the distance goes over 5 ft. `startTurn` never clears it, so an unused feint **carries into later turns**. | **Bug** (D-3). **Reproduced** with `E.newState(duelist, seed 1)`: Aero closes and feints, then `endTurn`; Ilsa takes an empty turn, then `endTurn`. At round 2, Aero's turn, `ilsa.conds.feinted = {by: "aero"}` is still present. |
| X-2 | `battle_insight` | Concentration, ends after 1 minute or if the target becomes invalid (sheet, with an adopted duration override) | Lasts until consumed; no concentration or duration | Partial |
| X-3 | `grapple` | One size larger at most; contested escape; drag at half speed | None of these | Partial |
| X-4 | `sentinel_balance` | 2 uses per long rest | No counter; trigger never reached | Partial and inert |
| X-5 | Contests | Ties go to the target (Taunt ruling only) | Ties go to the defender for **all** contests | Generalisation (D-11) |
| X-6 | Critical hits | No cited source | Natural 20 doubles damage dice; Parry not offered | Unsourced convention (D-12) |
| X-7 | `minor_telekinesis` reposition | Object stays within 30 ft while moved | Displacement relative to the owner; no end-position check | Partial (D-1) |
| X-8 | `minor_telekinesis` / `recover_weapon` | — | A lightsaber comes back **unlit** | Sandbox choice (D-2) |
| X-9 | Object weight | ≤ 10 lb | Fixture weapons have no weight; defaults to 3 lb | Fixture assumption |
| X-10 | Action economy | Live turn contract has no Secondary | Sandbox Secondary is **on** by default; the SA-001 document isn't in the repo | Provenance gap (D-9) |
| X-11 | Sandbox defaults | — | `force_augmentation` and `secondary_action` default to **on**; `cinematic_judge` is on but descriptive only | Sandbox-only (D-10) |
| X-12 | `taunt` | Rules text cites "switch tb4_taunt" | No such switch in `ruleset`; Taunt is always available | Label mismatch |
| X-13 | `move` | SRD movement | Close (to 5 ft) or withdraw (15 ft) only | Abstraction |
| X-14 | Crucible d8 test | Fixture key `bank_policy.auto_bank_major_symbols` | The test asserts `banking?.major_face_auto_banked`, which always passes | Weak test (on the Crucible branch) |

---

## 7. Owner decisions blocking implementation

Every "Recommendation" below is **a recommendation, not a decision**. Nothing here has been resolved on the owner's behalf.

### D-1 · Minor Telekinesis: repositioning consequence
- **Current:** another creature's dropped weapon is sent "30 ft away", and its owner needs 30 ft of movement to recover it (`execStep`, `availability` → `WEAPON_FAR`).
- **Evidence:** the ruling allows "reposition" of an unattended object within 30 ft that "stays within 30 ft while moved". The 30-ft recovery cost is not in the ruling. It is labelled "pending owner review" in `COMBAT_V05B.md` §1.
- **Choice and alternatives:**
  - (a) Adopt it as is.
  - (b) Allow repositioning only within 30 ft of Aero, with the recovery cost equal to the new distance from the owner (needs object positions).
  - (c) Allow repositioning, but with no tactical displacement benefit.
  - (d) Disallow repositioning of other creatures' gear in combat.
- **Implications:** (a) is a strong tempo tool for a Main action at 0 FP. (b) needs a position model the slice doesn't have. (c) and (d) are the narrowest readings.
- **Recommendation:** (b) as the target, with (a) kept as a labelled sandbox fixture until positions exist.

### D-2 · Minor Telekinesis: lightsaber returns unlit
- **Current:** a retrieved lightsaber comes back unlit, as with `recover_weapon`.
- **Evidence:** the ruling is silent.
- **Alternatives:** unlit (re-igniting costs an Object interaction), or as dropped (a dropped lightsaber is unlit by construction).
- **Recommendation:** keep unlit, since a dropped lightsaber is deactivated. Confirm it.

### D-3 · Feint expiry (bug fix approval)
- **Current:** feint advantage can persist beyond the turn.
- **Evidence:** the profile text says "this turn"; `startTurn` doesn't clear `feinted`.
- **Alternatives:** expire at the end of the feinter's turn (as written), or until the start of the feinter's next turn.
- **Implications:** the current behaviour inflates feint value and skews the simulation numbers in `audit/BALANCE_REPORT.md`.
- **Recommendation:** fix it to end of turn, as written, in its own commit with a regression test.

### D-4 · Crucible dice: which core mode
- **Current:** three committed candidates exist, none adopted:
  - Variant A: the d6 with qualified banking.
  - Variant B: the d8 with doubled symbols.
  - Variant C: majors on special dice only.
- **Evidence:** GCD-001-A; the fixtures. The odds were reproduced in §3.C.
- **Alternatives and implications:**
  - **d6:** 3+ net Strain is impossible with two Entropy dice, so Ruin conversion is effectively one-sided.
  - **d8:** fixes that, and roughly doubles the 3+ Spark rate. Majors still appear on 48.7% of 3v2 rolls.
  - **C:** makes majors rarer but ties them to gear.
- **Recommendation:** run d8 with **qualified** banking (Variant A's predicates applied to d8: 20.2% and 15.3% qualified at 3v2, by my computation) in an isolated simulator before choosing.

### D-5 · Crucible: full core, d20 sidecar, or parallel resolver
- **Current:** undecided (GCD-001 §0 and §7).
- **Implications:** a sidecar keeps every d20 rule and test intact. A full core needs a new stat-to-pool mapping (GCD-001 §2) and a re-derivation of every attack and contest.
- **Recommendation:** a sidecar first, in the sandbox only, gated by `rules_version`.

### D-6 · Resolve and Ruin earning gates, pool caps and decay
- **Current:** `auto_bank_major_symbols: false`, `qualification: pending`. GCD-001 §4 suggests a session cap of 5 as a balance candidate.
- **Alternatives:** auto-bank; predicate-gated (Variant A); scene-level earn caps; specific dice only (Variant C).
- **Recommendation:** predicate-gated, with a per-scene cap and anti-farming on stakes. Simulate before setting numbers.

### D-7 · Minor-symbol 3:1 conversion
- **Current:** optional, after cancellation, net only, exclusive of immediate spends. Caps are pending.
- **Alternatives:** off; on with a per-roll cap of 1; on with a choice at spend time.
- **Recommendation:** on, capped at 1 per roll, as an explicit journalled player (Spark) or GM (Strain) choice.

### D-8 · Narrative Consequences d6 activation and spending
- **Current:** live-adopted for rolling and mapping only (`hask_meadow_r2`). No spend or effect is implemented, and it is not wired into the combat slice.
- **Evidence:** §3.B.
- **Alternatives:**
  - (a) Leave it as a display-only axis.
  - (b) Define an Advantage/Threat effect catalogue plus Atomic commits.
  - (c) Retire it in favour of Crucible Spark/Strain.
  - (d) Bring it into the combat slice as is.
- **Implications:** two overlapping "consequence" vocabularies (Advantage/Threat and Spark/Strain) would confuse players and agents.
- **Recommendation:** decide D-4 and D-5 first. If Crucible becomes a sidecar, map Narrative Consequences onto Spark/Strain rather than running both.

### D-9 · SA-001 Secondary action
- **Current:** a sandbox budget, on by default. Not in the live turn contract. The SA-001 document is missing from the repository.
- **Alternatives:** adopt it for the sandbox only; adopt it for run 2 with a migration; drop it.
- **Recommendation:** commit the SA-001 source document first, then decide. Until then, Feint, Readied Dodge, Tactical Glance and Takedown remain proposals.

### D-10 · Sandbox defaults
- **Current:** Force augmentation and SA-001 are on by default in the sandbox.
- **Recommendation:** keep them on in the sandbox only. Confirm that no campaign inherits these defaults.

### D-11 · Contest ties
- **Current:** ties go to the defender in every contest (Feint, Blade Bind, Grapple, Calm, Takedown).
- **Alternatives:** keep that rule universally; re-roll ties; or adjudicate per profile.
- **Recommendation:** adopt "ties go to the defender" universally and record it as a ruleset rule.

### D-12 · Critical-hit rule
- **Current:** a natural 20 doubles damage dice and blocks Parry. No source is cited.
- **Evidence:** the experimental resolver also treats an original 20 as a crit; the sheet is silent.
- **Recommendation:** record the rule with its source (SW5e or another d20 base) in `ruleset`.

### D-13 · Battle Insight duration and concentration
- **Current:** lasts until used.
- **Evidence:** the sheet says "concentration, up to 1 minute", which is itself an adopted override of the source's 1 round.
- **Recommendation:** implement the end conditions once a concentration model exists (it was already listed as open in v0.4).

### D-14 · Grapple escape, drag and size
- **Current:** not modelled.
- **Recommendation:** implement the escape contest (the target's action) before relying on Grapple in balance runs.

### D-15 · Per-rest resources (Sentinel Balance)
- **Current:** untracked.
- **Recommendation:** add rest counters together with any save-forcing enemy.

### D-16 · Minor Telekinesis open items 1–3
- **Current:** the defaults are in use: a +4 roll vs a hidden DC only when uncertain; no hand needed; the action each round to hold an object aloft. None of them has been ruled by the owner.
- **Recommendation:** rule on them before using the feature outside combat.

### D-17 · Undefined Crucible elements
- **Current:** these are undefined, and nothing should be rolled for them:
  - the Conscience Die faces and trigger;
  - the Mastery d8 faces;
  - the stat-to-pool mapping;
  - the difficulty-to-Entropy mapping;
  - the numbers in the spend menus;
  - who owns the Resolve pool (individual or party);
  - Ruin's per-scene budget.
- **Recommendation:** treat them as one design packet for a GEP after D-4 and D-5.

---

## 8. What this audit did not do

- **Did not change:** any mechanic, test, UI or dice behaviour; any live campaign file.
- **Did not merge:** the Crucible branch.
- **Did not touch:** Oracle, OAuth or the gateway.
- **Did not activate:** Narrative Consequences or Crucible in the slice.
- **The X-1 Feint bug is reported, not fixed**, pending D-3.
