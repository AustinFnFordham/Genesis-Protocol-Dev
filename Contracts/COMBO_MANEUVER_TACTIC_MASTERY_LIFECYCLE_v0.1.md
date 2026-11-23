# Genesis Protocol — Combo, Maneuver, Tactic and Team Mastery Contract
**ID:** CMT-001 | **Version:** 0.1 | **Date:** 2026-11-22 | **Status:** owner-approved design direction; quantitative mechanics sandbox proposals, not live rules.
**Starting commit:** CC-005c 16b4750445ed34b31093b879983e1555204d5983. This branch documents decisions ONLY. No changes to Oracle, Hask Meadow, shared-0002, existing abilities or live dice.

**Outcome-system continuation:** [SSRR-001](GENESIS_SPARK_STRAIN_RESOLVE_RUIN_OUTCOME_CONTRACT_v0.1.md) adopts the owner's Spark/Strain (minor immediate) and Resolve/Ruin (major banked) terminology and specifies two-axis outcomes, WHISPER authority and candidate spend policy. All numerical rolls/spends remain proposals until separately adopted.

**Crucible integration (proposal only):** [GCD-001](GENESIS_CRUCIBLE_DICE_AND_PRESSURE_DESIGN_v0.1.md) defines candidate Agency/Entropy symbol checks and how per-component learned Maneuver bonuses may interact with Spark/Strain/Resolve/Ruin. Mastery advancement remains open-ended and may not be capped by a mobile dice-display limit. No particular die pool grants a new Maneuver without purchase and valid prerequisites.

## 0. Authority and correction
This document corrects proposed terminology in CC-002 (Cinematic Combat v0.2), GEP-001 and previous assistant handoffs where they conflict with the owner's updated definitions. Existing canonical rules, actual character grants and pinned campaigns retain their authority until a later versioned, explicitly approved implementation. The older CC-002 used Maneuver to mean a tactical objective such as Feint, Disarm or Riposte. **New Genesis definition: a purchasable Maneuver is a specialized, prerequisite-gated composition of abilities with a distinct mechanical payoff.** Older one-action candidate entries must be reconciled as atomic abilities, techniques or composite Maneuvers, without silent migrations.

The statement "bonuses don't stack indefinitely" was overbroad and is RETRACTED as a progression rule. **Long-term mastery may continue to advance and unlock additional authored tiers/branches as a character grows.** Separate per-roll combination rules still prevent duplicate advantage, unauthorized extra dice, infinite reactions or unbounded recursive triggering. Finite action budgets and balanced individual effects are not a categorical cap on character development.

## 1. Distinct systems
- **Ability / Skill / Trait:** source-backed actor-owned entitlement or learned competence (Dodge Action, Taunt, Riposte, Lightsaber Strike, item use); has activation profiles and separate grant, target, action and resource information.
- **Combo:** free player-authored/discovered ordered or conditional sequence of otherwise legal action profiles in the existing Turn Creator. Predicted synergy and exact seeded whole-turn probability are shown by the existing Combo Judge. A named/saved Combo grants NO new mechanical effect merely because it is named. It may include two of the same action category only when the actor genuinely has enough budget or authorized alternates. The player can rename or reuse it.
- **Maneuver:** one purchased, authored specialized *composition* that requires ownership/training of its constituent abilities and a validated advancement expenditure. It grants a measurable effect BEYOND executing the ordinary Combo (e.g. advantage on explicit eligible rolls, cost conversion, added control, new target relationship, conditional next-turn benefit). It still consumes a legitimate execution-cost vector. Visual style alone is not sufficient to justify its purchase.
- **Tactic:** reusable conditional strategy that EMERGES from meaningful repeated uses and refinements of free Combos, purchased Maneuvers, mixed sequences or ordinary actions. Does NOT require purchasing a Maneuver. Evolving Tactic mastery is separate from an unlockable Maneuver's ownership.
- **Team Combo, Team Maneuver, Team Tactic:** coordinated version using legal actions by distinct PCs and/or allied NPCs. A purchased Team Maneuver has authored prerequisites and effect; a Team Tactic may emerge from repeated coordinated action. Every participating PC controls their character; allied NPC motivations, consent and observed knowledge remain valid. No actor shares action-budget slots or hidden knowledge without a grant.

**UI rule:** The current combat palette shows only categories in which the actor actually owns eligible actions/Maneuvers; it never displays unearned categories or unlocked-content teasers. A separate opt-in progression browser can explain what might be unlocked. Owned conditional actions may display clear unavailable reasons within an otherwise present category.

## 2. Three paths, never forced into one tree
(A) **Ordinary actions → valid Combo → generated/player name → saved Combo → meaningful repeat + adaptation → emerging Tactic → evidence-based Tactic mastery.**
(B) **Acquired prerequisite abilities → individual mastery training → advancement expenditure → purchased Maneuver → application of independently earned component mastery nodes → additional composite mastery branches → maybe a Tactic.**
(C) **Coordinated allied actions → Team Combo → evidence-grown Team Tactic or purchased Team Maneuver → refined coordinated strategy.**
All three coexist. A Tactic can exist without any Maneuver. A Maneuver may be played without having a named Tactic. A Combo can remain purely a Combo.

**Two costs** must never be conflated: purchase cost (permanent entitlement; currency and timing still open) and activation cost (Main, Secondary, Bonus, Reaction, movement, Object Interaction, Free, Force Point and other per-use costs). Player-proposed standard budget: Main 1, Secondary 1, Bonus 1, Reaction 1, movement 1 allocation, Free contextual/unmetered within fiction, object interactions context-dependent. Version-gate any changes to legacy campaigns.

## 3. Constituent ability mastery drives Maneuver upgrades
Maneuver outcomes are dynamically composed from **actually owned and independently mastered ability nodes**, along with maneuver-specific training, circumstances and optional team evidence. Never treat all abilities as mastered simply because one is. Do not replace all components with one generic overall mastery level.

Case: Mocking Crane = Dodge Action + Taunt + conditional Riposte. Suppose the purchased base version grants authored Flourish on eligible Taunt and eligible triggered Riposte, bounded to a chosen target. Progression:
- **No component mastery:** purchased base benefit, if preconditions and unlock hold.
- **Dodge mastery ONLY:** apply the explicitly authored Dodge-derived evasion, movement/control or response-window upgrade. Taunt and Riposte remain at baseline.
- **Taunt mastery ONLY:** apply the explicitly authored Taunt-derived vocal/gesture, provocation, perception or pressure upgrade. Dodge and Riposte stay at baseline.
- **Riposte mastery ONLY:** apply the specifically authored Riposte-derived counter accuracy, control or other trained effect; Dodge and Taunt stay baseline.
- **Dodge + Taunt mastered:** apply their two validated effects, not an unearned Riposte effect.
- **All three mastered:** each individual contribution applies per its policy. An additional authored **composite milestone** may unlock next-turn advantage on a qualifying action, an earned Inspiration-like die/resource, a positioning/control flourish or a novel defensive follow-up. Neither an automatic grant nor an unlimited free reroll.
- **Later progression:** higher-than-initial-master tiers and alternate mastery branches remain possible. Characters may keep growing as new, source-backed nodes are earned. No arbitrary global cap on number of mastery nodes or total Maneuver sophistication.

**Inspiration-like resource**: proposal only. Must specify earning trigger, actor ownership, validated die size, spend window, max held, refresh/expiry, per-event anti-farming and stacking with existing dice. A limit on simultaneous held resources is a balance policy, NOT a cap on player mastery progression. Same for per-roll advantage: if ordinary d20 advantage does not stack, additional mastered nodes should grant new qualitative/conditional effects rather than pretend to roll infinite advantage dice.

A fully mastered Maneuver can be extraordinarily cinematic and efficient. Incomplete mastery is not punished: only the skills actually mastered contribute enhanced mechanics. A character cannot 'master Taunt' merely by saying something funny; source proficiency and advancement provenance matter.

## 4. Example 1 — Mocking Crane
**Free Combo:** Dodge (Main) + Taunt (Bonus, including player-selected exact speech/gesture) + conditional Riposte (Reaction when its real trigger fires). A perfectly valid plan if all individual grants, resources and trigger requirements hold. No purchased Maneuver needed.

**Purchased Maneuver:** prerequisite Dodge, Taunt, Riposte grants, extra training/unlock, and advancement cost (amount/currency pending); same Main + Bonus and reserved conditional Reaction cost as free Combo. It MUST confer a measurable mechanical difference from that Combo. Sandbox candidate 'Baited Counter' applies advantage to its eligible Taunt contest and, if the chosen opponent attacks, misses and triggers the legal counter, advantage to Riposte; individual mastery edges grow these effects. One preauthorized auto-reaction is not an extra Reaction; reserving it prevents other reactions, and it is only spent when the trigger happens under the agreed policy.

The Maneuver might fail when Taunt is ignored, when the opponent changes plans, when the opponent hits or when the reaction cannot trigger. Enemy learning and telegraphing are additional real risks, not automatic GM punishment. A failed Taunt need not doom the overall objective if the enemy independently attacks and the Riposte works. On full success + qualifying component mastery, a later tier MAY grant temporary next-turn advantage or a special Inspiration-like resource, with separate approval/testing. If only Dodge is mastered, the riposte does NOT inherit the master's bonuses.

**Comparison is mandatory**: cost, target and trigger, each check chance, joint composite objective probability, opponent counter exposure, expected damage/control, negative/positive consequences, mastered components and marginal improvement purchased vs free. Seeded simulator must never consume real accepted dice.

## 5. Example 2 — Serpent's Passage
**Free attempted Combo:** Main Dodge + Main Lightsaber Strike = two Main costs; normally illegal with a single Main unless some entirely separate grant provides a second Main.
**Purchased Maneuver:** require both grants, trained composite technique and advancement expenditure. Its expressly authored activation may convert the execution cost to **Main 1 + Secondary 1**, leaving Bonus 1, Reaction 1, and unused movement as otherwise permitted. It authorizes a distinct guarded strike, not two full unmodified Main actions plus unlimited extras. Its measurable payoff is already the legal action-cost conversion; trained Flourish may later add an approved effect. Dodge mastery changes only the defensive component; lightsaber mastery only the offensive component; later both-tier milestone may add a new conditional effect. Threat exposure, limited ability to use another Secondary setup and opponent counters remain risks.

## 6. Two independent outcomes + Flourish
Axis **A: primary objective** (success, failure, or source-supported graded bands). It is NOT always the AND of all component rolls: a failed setup might still precede successful counter; a successful preliminary attack might not fulfill the intended disable objective.
Axis **B: Chaos consequence** (positive opportunity, neutral, negative complication, possibly separately authored multiple effects). Both axes must be resolved by grounded, validated consequences and immutable source facts, with clear probability/provenance. A success can include a complication. A failure can produce an opportunity. Positive and negative effects can both be present if separately justified. No automatic 'narrative tradeoff' added solely to create drama.

**Flourish** is an earned Maneuver/skill performance dimension (style and specific mechanic), NOT the consequence die, not an automatic success and not the entirety of its mechanical reward. Soul's animation/voice must correspond to accepted outcomes: a spectacular failure remains a failure; high mastery may justify more impressive presentation without changing the dice.

**External systems as comparative evidence, not copied rules:** The official Cosmere RPG describes its d20 and Plot Die Opportunity/Complication axes (https://www.cosmererpg.com/system); Daggerheart's public SRD describes independent success vs Hope/Fear and cooperative Tag Team rolls (https://daggerheartsrd.com/rules/making-moves-and-taking-action/). Genesys/FFG narrative dice, Modiphius 2d20, Fate, Ironsworn, Forged in the Dark and Cortex Prime offer additional design comparisons; verify individual official sources and avoid copying proprietary labels/actual system implementations. No unverified cross-game engine claim enters canon.

## 7. WHISPER relation
WHISPER provides a proven **pattern** of stateful character evidence, triggers, thresholds, decay and authoritatively validated consequences. Apply the same evidence/Registry/Atomic→Chaos→Soul architecture across mastery, tactics, diplomacy, piloting and group dynamics. Do NOT reduce all domains to the WHISPER mental-strain meter: psychology is one domain; skills, equipment, training and teamwork have independent causal substrates. Psychological strain may affect eligibility or failure consequence of a practiced maneuver, but never grants unlearned techniques.

## 8. Source-grounded implementation and anti-abuse
- Proposed schema example: Contracts/examples/combo_maneuver_mastery_example_v0.1.json. Example IDs are illustrative, not global registry grants. Adapt fields to canonical Registry rather than duplicating truth.
- Prerequisite ownership, node level, advancement receipt, grants, action cost vectors, target/position/weapon state, reaction timing, release of unused reserves and ruleset version are checked by Atomic.
- Per-skill mastery edges independently resolve only when real actor source nodes are present; composite all-mastered effects are separate checks. Do not double-count same die modifier, retry, or tactic observation.
- Emerging Tactics require unique accepted event IDs, meaningful evidence, novelty/context, deduplication and non-farming. A Combo name does not grant stats. Team Tactics require actor-specific authorizations and shared timing; an NPC ally can decline.
- Optional Force Point augmentation may enhance MOST eligible actions for actors with explicit Force ability/grants, but each variant requires a specific FP cost, effect, legal range and resource limit; no universal unexplained Force powers.
- Off-hand blaster/dual blade, Echani strike follow-up, held-lantern Throw, Jump and Jump+Attack deserve authorable source-backed execution profiles and maneuvers. Missing implementations are coverage gaps, not evidence they are impossible.
- Only possessed and eligible categories appear in the live ability rail, with no teased ungranted categories. Optional progression browser is separate from combat.
- Preserve Roll Theater, Combo Judge with 400-seed-style predictive simulation, plan locks, server-owned player projections and real receipts; no secret enemy stats in player bundle.

## 9. Acceptance stories
1. Free Mocking Crane Combo works with three source-backed grants but no maneuver unlock; no free Flourish modifier.
2. Purchased Mocking Crane same resource budget, additional statistically testable benefit and authorized conditional reaction; no retroactive GM-chosen PC response.
3. Three independent single-skill mastery fixtures each activate ONLY their respective mastered component; full triple-mastery fixture activates each plus separately granted composite milestone.
4. An actor can continue evolving a previously fully mastered maneuver via later authored tier nodes; finite per-roll checks and action budgets still apply.
5. Serpent's Passage free two-Main sequence fails with one Main; purchased Main+Secondary profile succeeds if prereqs and conditions hold, with no implicit extra full Main action.
6. Repeated ordinary Combo becomes a named Tactic without any Maneuver purchase, using deduplicated accepted events; no farming.
7. Team Combo/Tactic combines distinct PC and NPC resources without forced PC actions, omniscient information or free enemy reactions.
8. Mixed-component success+complication and failure+opportunity both possible through independent validated consequence rules, not invented by Soul.
9. Prediction side-by-side shows exact marginal odds, damage, counter exposure, granted mastery benefits and proposed outcome distributions; simulation never consumes campaign RNG.
10. Hask Meadow, shared-0002 and live GM rules are unchanged until a separately approved promotion/migration.

## 10. Open decisions
Exact advancement currency and pricing, training/proficiency thresholds, purchased Maneuver effects and scaling at each node, real source IDs, Inspiration-like die earn/spend/caps, future tiers and progression evidence, stacking policy within single die rolls, objective-success bands, second-axis mechanics, team participation windows and the effect of Force augmentation are not yet canonical.

**Owner's directive:** no unrequested ceiling on mastery growth; NO implementation handoff to Claude until this contract and its concrete example are available and inspected in Git.
