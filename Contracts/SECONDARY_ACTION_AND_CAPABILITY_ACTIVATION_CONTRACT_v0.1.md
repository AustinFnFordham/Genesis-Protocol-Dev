# Genesis Protocol — Secondary Action and Capability Activation Contract
**ID:** SA-001 | **Version:** 0.1 draft | **Scope:** prospective game rule, not deployed | **Decision date:** 2026-11-18

## 0. Authority and change control
This captures the owner's design decision: **Secondary Action** (not the earlier "Secondary Activity") is a distinct, limited, rules-governed action resource. Every character ordinarily has **one Secondary Action per turn**, unless a validated grant modifies the allowance. Only explicitly eligible capabilities may consume it. This document describes future implementation and must **not** change live Hask Meadow, ongoing play, dice, or feature switches.

This intentionally supersedes the *design classification* of Secondary Activity in `Contracts/TB4_WHISPER_001_v0.1.md` §2.1–2.2, which previously described Secondary Activity as non-slot semantic annotation. It does **not** authorize silently changing current deployed `turn-contract/3` behavior or upgrading old records. An implementation milestone must reconcile these rules behind an explicit version/feature gate and regression tests.

References: `schema/Feature.schema.json` (activation), `schema/Action.schema.json` (action cost), `schema/Class.schema.json` (fluid progression), `schema/Power.schema.json` (power upgrades), `campaigns/starwars_litrpg/creator/DESIGN_DECISIONS.md` (2026-10-29 cross-tree/affinity), and `Contracts/02_Progression_Tree_System.md`.

## 1. Action budget
For an ordinary combat turn, the *proposed Genesis extension* to a D&D/SW5e-shaped economy is:

| Resource | Baseline | Important boundary |
|---|---|---|
| Primary Action | 1 | Major actions and abilities unless an explicit alternative activation is granted |
| Bonus Action | 1 | A capability must explicitly permit a Bonus Action; not any ordinary action |
| **Secondary Action** | **1** | Only Secondary-eligible capabilities; independent tracked budget |
| Movement | Existing ruleset speed/remaining movement | Moving into cover is not the same as becoming Hidden |
| Reaction | Existing ruleset allowance and timing | Trigger- and eligibility-bound, often outside turn |
| Free/incidental conduct | Contextual, existing rules | Physical gestures/speech and obvious perception are not automatic free mechanical benefits |
| Object interaction | Existing ruleset allowance | Does not turn extra object interactions into free Secondary Actions |

Reset, turn-end, interruption, migration, and scenario-specific action budgets are owned by the encounter controller/ruleset. The Secondary Action is **not** a universal extra attack, spell, check, Help, Hide, or Dodge.

## 2. Eligibility: one canonical capability, alternative execution profiles
A capability record should identify:
- Canonical Registry entity and applicable ruleset; target(s), effect, conditions, known grants.
- Default execution profile(s): resource cost(s), target requirements, trigger, timing, duration, and any feature prerequisites.
- Explicit alternative profiles unlocked through approved **class, species, skill mastery, power upgrade, item/gear, faction, or other domain-owned source**.
- Usage limits independent of action budget (per turn, encounter, rest, charge, and shared capability limits); effect stacking/overwrite rules; resource costs such as Force Points.
- Source identity, entitlement, provenance, expiration/equip state, and immutable rules version.

A Secondary Action label alone does not establish a mechanical effect. The validator must distinguish an incidental crouch, a movement to cover, an attempt to hide, and a rules-level Hidden status. Costs attach to the requested *effect* and authorized execution profile, not merely the natural-language verb.

## 3. Source grants versus resources
Three distinct grant types **must not be conflated**:
1. **Capability grant:** while eligibility holds (e.g. item equipped), the actor may invoke an otherwise unknown skill/effect.
2. **Execution-profile grant:** the actor may activate a particular capability through an alternative slot, e.g. Bonus Action instead of Secondary Action.
3. **Capacity grant:** the actor gains an additional unit of an action budget, e.g. +1 Secondary Action this turn.

An execution-profile grant **does not itself** add to the actor's Secondary or Bonus Action budget. Two grants of the same activation profile do not create two slots or double an effect. Equipment-derived entitlements cease when their equip/attunement/charge conditions are no longer met, subject to the accepted event record.

## 4. Legendary item example — alternate activation and a second use
*Proposed illustrative skill and item; neither is a canonical Registry entity or live reward.*

- **Tactical Assessment**, learned by the actor: can activate with **1 Secondary Action**.
- **The Strategist's Eye**, a legendary equipped item: grants Tactical Assessment **as a Bonus Action**, even if the actor has not learned the base skill.
- If the actor has both sources, they have **two eligible execution profiles** and could attempt two activations in one turn: one Secondary + one Bonus.
- This is valid **only if** the ability's shared usage cap permits two uses, the item permits repeated activation, all targets/effects remain legal, and stacking rules do not prohibit or multiply the results.
- If Tactical Assessment is once-per-turn, both sources still share that cap unless the item **explicitly grants an additional use**. "Can use as Bonus" is **not** equivalent to "can use twice."
- Multiple uses may target different things where allowed; duplicate numerical buffs do not stack unless explicitly authorized.

No permanent learned-skill acquisition is implied by equipping an item. Legacy design says caches do not directly grant learned abilities; a conditional item-bound capability is a separate, reversible grant.

## 5. Skill mastery and character progression
Skill trees may include owner-approved, player-chosen milestones that:
- Add an execution profile (Primary → Bonus, Secondary → Bonus, etc.).
- Grant a limited secondary variant of a stronger action.
- Increase Secondary Action capacity for a defined trigger or duration.
- Improve range, reliability, targets, effects, or usage cap **instead of** action efficiency.

These are **not** automatic level thresholds. They are nodes evaluated through the existing fluid progression rules: prerequisites, tag affinity from accepted events, level/XP requirements when present, cross-tree constraints, choice-group exclusivity, and confirmed player choice. Ruleset and source entitlements must remain distinguishable.

A passive is an automatically evaluated rule with a defined trigger/condition, not an unbounded action that the player can repeat freely. "Free" likewise requires explicit event/turn limits where effects could be exploited.

## 6. Validation and transaction behavior
The future Atomic capability resolver shall, in order:
1. Resolve the actor, currently accepted character profile, Registry capability, ruleset and rules version.
2. Enumerate active grants from class, skill trees, species, faction, items, statuses, etc., with sources and effective dates.
3. Resolve legal execution profiles (including Secondary), eligibility, line-of-sight, range, equipment, hands, status, and prerequisites.
4. Check **remaining** budget (respecting literal zero), usage ceilings, stacking, known costs, and action sequencing. Never fall back from zero to one.
5. Produce a player-visible, spoiler-safe preflight showing costs and limits; await player authorization.
6. Commit via existing ledger/gateway authority; record source and execution profile; project updated budgets to the Turn Builder and character sheet.
7. On interruption, replay/recovery, or provider handoff, preserve the same action identity, cost accounting, dice receipts, and accepted history.

Chaos may discover candidate cross-domain relationships; it may not bypass Atomic validation, change legal action costs, or create phantom sources.

## 7. Migration / compatibility / test gates
- **Do not** repurpose existing `secondary_activity` free-form records as spent Secondary Actions without an explicit migration contract.
- Introduce a separately versioned declaration/budget field, feature-gated; old campaigns stay on old behavior until owner-approved adoption.
- Update `Feature.schema.json`, `Action.schema.json`, capability and turn schemas consistently only in an approved implementation milestone.
- Regression cases: baseline one Secondary; second without grant rejected; extra Secondary capacity honored; Bonus item grant without learned skill; learned+item two profiles with shared once/turn cap; item lost mid-round; duplicate items; rest-charge limits; incompatible stacking; zero Primary remaining while Secondary remains; reaction timing; noncombat and turn-end; replay after crash; disabled feature/legacy mode.
- No new resource or mechanical entitlement may be invented by a GM model, a suggestion chip, or narrative prose.

## 8. Open balance/authoring decisions (not invented here)
- The **complete eligible Secondary Action catalog**, per system/ruleset.
- Whether Secondary can be exchanged for Primary or Bonus, if ever.
- Whether Secondary variants of Hide, Search, Help, Battle Insight, etc. have reduced effects or special prerequisites.
- Numerical mastery thresholds, grant cadence, and additional Secondary Action stacking caps.
- Encounter balance adjustments and migration behavior for existing characters.
- Item-bound activation use ceilings, equipment qualification, and effect nonstacking.
These need independent design, test fixtures, and explicit owner ratification **before deployment**.

## 9. Handoff
This contract belongs on the **docs-only branch**. Work may continue UI improvements and private playtests on its own implementation branch in parallel. Do not merge, enable, or present Secondary Action as live until the eligibility catalog, mechanics, schema updates and Atomic tests are approved.
