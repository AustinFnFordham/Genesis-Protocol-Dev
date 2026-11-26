# SA-001 Secondary Activity: proposed contract and balance study (CC-007 §3)

**Status:** PROPOSAL, sandbox only. **Not** adopted, and not promoted into live campaign authority. The live turn contract (`campaigns/starwars_litrpg/creator/TURN_CONTRACT.md`, turn-contract/3) is unchanged: it has an action, a bonus action, a reaction, movement and one object interaction, and no Secondary.

**Source gap (audit D-9):** the original SA-001 document is not in this repository. This contract is reconstructed from:
- its implementation (`catalog.json` → `ruleset.switches.secondary_action`, `budget.secondary`);
- GEP-001 C7 ("a distinct prospective budget, not a universal extra Main");
- the profile data.

If the original exists elsewhere, it should replace this reconstruction.

## 1. Definition (proposed)

A **Secondary Activity** is a brief, non-damaging tactical act woven into the turn: a feint, a readied defensive posture, a quick scan. It changes the *conditions* of the turn's attacks or defence, but it is never an attack, a power, or a source of damage.

| Budget | What it is | Examples here |
|---|---|---|
| **Main** | The turn's main deed: one attack, a power, a major action | `saber_strike`, `burst`, `battle_insight`, `grapple`, `minor_telekinesis` |
| **Bonus** | A specific extra deed **granted by a feature or profile** (it isn't generic) | `taunt` (sheet ruling), `flow_strike` (proposal, after a melee attack) |
| **Secondary** (SA-001) | A generic, non-damaging tactical act: at most one per turn | `feint`, `readied_dodge`, `tactical_glance` |
| **Free** | Trivial, with no tactical effect | `speak`, `release_grapple` |
| **Object** | One object interaction | `toggle_blade`, `draw_sidearm`, `holster_sidearm` |

## 2. Rules (proposed)

1. **At most one** Secondary Activity per turn. It doesn't carry over and can't be converted into another budget.
2. A Secondary Activity **must not** do any of the following:
   - make an attack roll or deal damage;
   - cast a Force power or spend Force Points;
   - move a creature;
   - grant an extra attack;
   - repeat a Main-action effect.
3. A profile qualifies only if its catalog `cost` is `{secondary: 1}` **and** it has no `damage`, no attack `resolution` and no `fp` cost. The engine already refuses Secondary profiles when the switch is off (`SA001_DISABLED`).
4. **Compound maneuvers** spend every budget they name, as a single declaration. `controlled_takedown` spends Main + Secondary on one contest, and **a loss spends both**. It is shown as "compound" in preflight (`player_api.preflight` → `compound`).
5. **Who gets it** is an owner choice. The sandbox gives it to **every combatant**, NPCs included: Ilsa feints about 1.6 times per fight with A. The alternative is to grant it only through progression, as a trained capability.

**Aero profiles that qualify today:**
- `feint`
- `readied_dodge`
- `tactical_glance`
- `controlled_takedown`, through its Secondary half

All of them are sandbox proposals.

## 3. Study (`audit/sa001_sim.cjs`; results in `audit/sa001_results_2000.json`)

**Method**
- 2,000 seeded fights per cell, with the **same seeds** across rules.
- The real engine and validator, with the policies of a reasonable tactical player and the NPCs.
- **Rules compared:**
  - **A:** SA-001 on (the current sandbox).
  - **B:** SA-001 off (the live economy).
  - **C:** no Secondary budget; the same activities **cost a Bonus action** instead, so they compete with Flow Strike. Under C the NPC duelist gets the same Bonus-cost feint, for fairness.

| Encounter : rule | Win % | Rounds | Aero dmg per turn | Dmg taken per fight | Secondary used | Feint success | Flow Strike used | Plan variety (bits / distinct plans) |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| duelist : A | 32.5 | 2.25 | 5.95 | 11.35 | 100% | 43.7% | 100% | 2.11 / 7 |
| duelist : B | 30.6 | 2.35 | 5.32 | 11.51 | 0% | — | 100% | 1.61 / 4 |
| duelist : C | 34.3 | 2.85 | 4.76 | 11.22 | 100% (as Bonus) | 44.1% | **0%** | 2.36 / 7 |
| predator : A | 62.0 | 2.25 | 8.04 | 8.79 | 50.4% (Readied Dodge) | — | 100% | 1.00 / 2 |
| predator : B | 58.8 | 2.13 | 8.90 | 9.16 | 0% | — | 100% | 0.00 / 1 |
| predator : C | 57.5 | 2.39 | 7.23 | 9.07 | 53% | — | 47% | 1.00 / 2 |
| relay_droid : A | 99.8 | 1.34 | 7.31 | 0.75 | 2.3% | — | 100% | 0.93 / 3 |
| relay_droid : B | 99.8 | 1.34 | 7.33 | 0.75 | 0% | — | 100% | 0.82 / 2 |
| relay_droid : C | 99.7 | 1.35 | 7.29 | 0.76 | 2.7% | — | 97.3% | 0.95 / 3 |

**Findings**
- **Power:**
  - A raises Aero's damage per turn against the duelist by about **12%** over B, with a +1.9-point win rate. The NPC uses the same rule, which mostly offsets it.
  - With A, Readied Dodge adds about +3 points of win rate against the predator.
  - A creates no extra attacks; the gain comes entirely from Feint advantage.
- **Duration:** A and B are nearly equal (2.25 vs 2.35 rounds against the duelist). C lengthens fights by about 0.6 rounds, because a Feint now costs Flow Strike.
- **Variety:** both A and C add tactical variety over B (about +0.5 to +0.75 bits; 7 distinct plans vs 4). A is "always use Secondary", 100% of the time. With **C**, every turn involves a **real choice**: open with a Feint or follow up with Flow Strike.
- **Opportunity cost:** A has none (the Secondary is free value every turn). Under C, 100% of duelist Feint turns give up Flow Strike, and 53% of predator turns give it up for Readied Dodge.
- **Relay droid:** none of the rules matters, because the fight is decided by attacks alone.

## 4. Recommendation (a recommendation, not a decision)

**The simplest balanced rule is C:** no new budget type, with tactical activities costing the existing **Bonus** action.
- It matches the live turn contract (no Secondary) and needs no migration.
- It turns "free value every turn" into a decision.
- It stays within ±4 points of win rate of both alternatives.

**Keep A as an opt-in sandbox ruleset** if the owner wants Secondary as a *progression-granted* budget. For example, a trained "combat flow" milestone could unlock a dedicated Secondary, which would then fit the mastery substrate (`progression/`).

**Caveats**
- Flow Strike is itself a proposal. On Aero's actual sheet, Bonus is used only by Taunt, so under the pure sheet C costs even less.
- The policies are scripted. The results compare rules, not optimal play.
