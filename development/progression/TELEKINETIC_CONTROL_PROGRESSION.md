# Telekinetic Control mastery: level 0–20 proposal (CC-007 §5) — SANDBOX PROPOSAL

**Base:** the Jedi Fundamentals Minor Telekinesis grant (`jedi_fundamentals.json`, `approved_provisional`, 2026-11-11). The grant is **unchanged**, and nothing is written to `aero_character_runtime.yml`.

**Owner direction (2026-11-25):**
- Every legitimate use, in combat or exploration, earns XP.
- Ordinary out-of-combat use is at-will, with no roll unless the outcome is uncertain.
- The combat action cost stays.
- Range and weight limits are real.
- Every 5 levels brings a significant training milestone.
- The curve gets steeper.

**Numbers:** the owner's proposed baseline, used for simulation only.

## Curve and table

- **Curve:** XP(L→L+1) = **10 + 5L + L²**.
- **Range:** 30 ft + 5 ft per level.
- **Weight:** 10 lb + 1 lb per level, plus another 5 lb at levels 5, 10 and 15.
- **Objects at once:** always 1.

| Level | XP to next | Cumulative XP | Range (ft) | Max weight (lb) | Milestone (eligibility only) |
|---:|---:|---:|---:|---:|---|
| 0 | 10 | 0 | 30 | 10 | — |
| 1 | 16 | 10 | 35 | 11 | — |
| 2 | 24 | 26 | 40 | 12 | — |
| 3 | 34 | 50 | 45 | 13 | — |
| 4 | 46 | 84 | 50 | 14 | — |
| **5** | 60 | **130** | 55 | **20** | **`tk_m5_fine_manipulation`**: training opportunity |
| 6 | 76 | 190 | 60 | 21 | — |
| 7 | 94 | 266 | 65 | 22 | — |
| 8 | 114 | 360 | 70 | 23 | — |
| 9 | 136 | 474 | 75 | 24 | — |
| **10** | 160 | **610** | 80 | **30** | **`tk_m10_sustained_hold`**: training opportunity |
| 11 | 186 | 770 | 85 | 31 | — |
| 12 | 214 | 956 | 90 | 32 | — |
| 13 | 244 | 1170 | 95 | 33 | — |
| 14 | 276 | 1414 | 100 | 34 | — |
| **15** | 310 | **1690** | 105 | **40** | **`tk_m15_force_power_prerequisite`**: prerequisite |
| 16 | 346 | 2000 | 110 | 41 | — |
| 17 | 384 | 2346 | 115 | 42 | — |
| 18 | 424 | 2730 | 120 | 43 | — |
| 19 | 466 | 3154 | 125 | 44 | — |
| 20 | — | 3620 | 130 | 45 | — |

## Milestones

Each milestone offers eligibility only. A grant needs a recorded approval, and none of them ever grants Force Pull, Force Push, creature manipulation, damage, disarming or attended objects.

| Level | Milestone | What it offers | Reasoning |
|---|---|---|---|
| 5 | **Fine manipulation** | Operate simple unattended mechanisms (latches, switches, levers) within range, still one object | Stays inside the ruling's "manipulate". Fixed objects are refused until this grant is recorded (tested). |
| 10 | **Sustained hold** | Keep one object aloft while doing other light tasks | Would resolve Jedi Fundamentals open item 3 for this character only, if the owner approves |
| 15 | **Force-power prerequisite** | Eligibility to **begin training** a learned telekinetic power (drafts `power_force_pull` / `power_force_push`, unpromoted) | Learning the power still needs a teacher or story event, owner approval and the `powers_known` rules |

## XP classification

XP is classified only from the facts of the committed event:

| Rule | XP | Basis | Status |
|---|---:|---|---|
| Any legitimate committed use | 1 (minimum) | Owner direction | baseline |
| Load ≥ 75% of current capacity | +1 | Event fact `weight_lb` | candidate |
| Reach ≥ 75% of current range | +1 | Event fact `distance_ft` | candidate |
| First use on a new object kind | +2 | Event fact `object_kind`, per character | candidate |
| Used in an encounter | +1 | Event fact `in_encounter` | candidate, **off** |

## Simulation (`sim_telekinesis.cjs`; results in `sim_telekinesis_results.json`)

**Pacing: sessions needed to reach each level**

| Player | L5 | L10 | L15 | L20 |
|---|---:|---:|---:|---:|
| Light (5 uses per session) | 20 | 98 | 276 | >400 |
| Typical (10 uses) | 10 | 48 | 132 | 281 |
| Heavy (20 uses) | 5 | 23 | 62 | 132 |
| Typical, with a routine-XP cap of 3 per scene *(candidate rule)* | 16 | 76 | 218 | >400 |
| Heavy, with a routine-XP cap of 3 per scene *(candidate rule)* | 8 | 40 | 109 | 234 |

**Farming.** Pure farming (one trivial lift, repeated) reaches L5 / L10 / L15 / L20 after **128 / 608 / 1688 / 3618** uses.
- The steep curve already makes high levels slow.
- But L5 is roughly 128 submitted no-stakes turns. If "legitimate" doesn't require a purpose, an automated or patient player can get there.

**Environment** (the 8 fixture objects, of which 5 are movable: visible, unattended, not fixed)

| Level | Range / weight | Movable objects in reach | What it adds |
|---|---|---|---|
| 0 | 30 ft / 10 lb | 2 of 5 | — |
| 4 | 50 ft / 14 lb | 4 of 5 | The crate and the power cell |
| 20 | 130 ft / 45 lb | 4 of 5 | The 60 lb locker is still out of reach |

The fixed lever needs the L5 grant. Attended and unseen objects are always refused.

**Combat and action economy:**
- Combat use still costs **Main**, and mastery doesn't change that.
- In the current slice the only loose objects are dropped weapons (3 lb) within 30 ft, so mastery changes nothing in combat **until scenes carry object data**.
- Higher range would let D-1 repositioning reach further, so **D-1 must be resolved first**.

## Findings and decisions for the owner

1. **"Legitimate use" needs a definition before live use.** Should purposeless repetition count? Options:
   - a per-scene routine-XP cap (simulated above);
   - "requires a declared purpose or stake";
   - unlimited.
2. **Range growth** reaches 130 ft at L20, about 4× the base. Weight grows to 4.5×. Range may outpace the setting's sense of "minor" telekinesis; a range cap or a slower per-level range gain are options.
3. The **demanding and novel bonuses** are candidates. The **in-encounter bonus** is off.
4. The **uncertain-use roll** (Jedi Fundamentals open item 1) is unset, so uncertain uses are refused.
5. The **milestone content** (levels 5, 10, 15) is a proposal: eligibility and prerequisites only.
6. **Where mastery state lives** in live play (gateway ledger vs character runtime) is GPT's integration lane, and needs owner approval.
