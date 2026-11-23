# Genesis Protocol — Spark, Strain, Resolve & Ruin: Outcome and Resource Contract
**ID:** SSRR-001 | **Version:** 0.1 | **Date:** 2026-11-22
**Status:** Owner selected terminology and design direction; mechanic examples PROPOSED, not activated or balanced.
**Scope:** Oracle/Hask Meadow/shared-0002 are protected; no adopted dice rule, advancement grant, campaign migration or live resource pool is created by this document.

**Crucible and WHISPER extensions (proposal, not adopted):** See [GCD-001](GENESIS_CRUCIBLE_DICE_AND_PRESSURE_DESIGN_v0.1.md) for the owner's exact Agency/Entropy d6 symbols, Spark/Strain cancellation, major resource economics and mathematical benchmarks; see [WCP-001](GENESIS_WHISPER_CRUCIBLE_PRESSURE_AND_ADAPTATION_v0.1.md) for psychological privacy, fatigue and conscience/adaptation boundaries. These extend this contract without changing existing d20 rules.

## 0. Relationship to CMT-001, ACP-001 and WHISPER
This contract reconciles two otherwise incompatible draft definitions:
- ACP-001 currently calls ANY legal sequence of action steps a "Maneuver"; the owner has since clarified that this is an ordinary **Combo** or generic composition.
- CMT-001 correctly calls a **Maneuver** a **purchased, prerequisite-driven specialized composition with a distinct mechanical effect**. Use CMT-001's owner-approved definition for future implementation. Preserve ACP-001's otherwise valuable profile/hand/throw/augment/Team safety contracts and its tested schema; a later migration must change affected words/schema in a backward-compatible way, not silently redefine saved ids.
- **Tactic** can emerge from meaningful practice of ordinary Combos, purchased Maneuvers or a mixture. Team Combos, Team Maneuvers and Team Tactics are multi-actor analogs, with separate actor consent/knowledge/turn costs.
- The Combo Creator, step-by-step legality, existing seeded Combo Judge with objective odds and opponent reaction risk are NONNEGOTIABLE. Purchased Maneuver value must be shown as a measured difference from the ordinary Combo, not merely a fancy name.
- WHISPER presently provides private player-authored emotional context and evidence-gated, player-confirmed post-turn appraisals (TB4-WHISPER-001 v0.1, development/whisper/whisper.py and post_turn.py). It does **NOT** yet implement a numeric Mental Fatigue/Composure meter or permission for model-decided involuntary PC actions. Such gameplay rules require separate scoped contracts. The shared design pattern is persistent evidence, triggers, bounded effects, and player perception versus objective world truth.

## 1. Exactly two orthogonal outcome axes, plus a magnitude and economy
**Axis A — Objective:** Did the actor accomplish the declared objective? Success / Failure, with source-supported graded outcomes. A composite objective does NOT mechanically equal the conjunction of all step rolls.
**Axis B — Consequence:** Did the event yield a favorable opening, no side effect, an adverse complication, or separately grounded positive and negative effects? This is resolved from eligible stakes, context and authoritative mechanics, not chosen retroactively for narrative flavor.
**Magnitude — Minor or Major:** Side-effect magnitude and resource eligibility are distinct from whether Axis A succeeded. A major effect is NOT generated merely because a d20 was high.
**Flourish — Purchased mastery expression:** A learned Maneuver's authored mechanical and cinematic benefit, separate from Axis B. A visually extraordinary failed maneuver is still a failure.

Owner-selected labels:
- **Spark:** a MINOR positive consequence, resolved now. Do not bank Spark by default.
- **Strain:** a MINOR adverse consequence, resolved now. Do not bank Strain as a GM currency.
- **Resolve:** a MAJOR positive player/party resource, banked for approved later use.
- **Ruin:** a MAJOR adverse GM/scene resource, banked for approved later use.

A single event might be Success+Spark, Success+Strain, Failure+Spark, Failure+Strain, neutral, or a valid major reward/escalation. The combination is not hardcoded as "success always creates Spark" or "failure always creates Ruin". Minor outcome and major-pool accrual are distinct eligibility rules. Spark and Strain refer to event consequences. In particular **Strain the minor outcome** is NOT automatically identical to WHISPER psychological stress, and **Resolve the spendable pool** is not an exact readout of subjective emotional resolve.

### 1.1 Suggested minimal authority pipeline (new mechanics require approval)
1. Player or NPC declares intent, target, exact steps and relevant scope/consent; game validates prereqs, timing, weapon/hand state and legal action resources.
2. Atomic records locked plan and resolves objective checks with server-authoritative dice receipts; no model chooses die faces.
3. Atomic/Chaos evaluates pre-eligible consequence candidates, range/magnitude and optional separate Chaos check, then produces immutable, source-backed opportunity/complication receipts. An independent Chaos die is ONE proposed implementation; exact faces, rates and independence/correlation with objective success are OPEN decisions, not assumed.
4. A **minor** chosen/validated consequence applies immediately to positioning, relevant next roll, short clock, consumable or perception (Spark/Strain). A validated **major** event may earn or spend Resolve/Ruin through explicit actor/scene pool events. If a major consequence must occur immediately, that effect is an authored rule, not a reason to turn every minor die into a pool gain.
5. Resolve/Ruin spending requires ownership, balance, available window, bounded authorized menu, causal predicates and stable idempotency keys. Locked dice, committed history and private facts cannot be rewritten. The GM can propose only approved, source-grounded consequences.
6. Soul receives the accepted player-visible events and renders scene-appropriate prose and audiovisual Flourish; it cannot turn a miss into a hit, invent relationships or "spend" Ruin in narration.

## 2. Owner's example spend families (proposal until exact rule/roll policies approved)
| Currency / effect | Proposed core spends | Validation restriction |
|---|---|---|
| Spark, immediate | Pass an opening to an ally; brief truthful situation clue; short reposition/cover; brief recovery | One relevant accepted event; legal movement/reaction/object timing; a clue requires a source and perception; no free extra Main |
| Strain, immediate | Exposed stance; ammo/gear cost; advance a risk clock; next-action instability | Consequence must be physically/causally possible, visible to relevant actors, time-limited or source-defined; no arbitrary permanent injury |
| Resolve, banked player/party | Push a result under an approved pre/post-roll rule; activate signature Maneuver; resist an authorized penalty; propose a plausible story detail | No reroll of committed dice without an explicit Atomic alternate receipt; no auto-override of NPC autonomy, sealed canon, private facts, or other players' choices |
| Ruin, banked GM/scene | Trigger an established environmental hazard; use an enemy's granted boss feature; increase predeclared risk; offer meaningful cost/benefit bargain | Only existing causal predicates/authorable world decisions; no hindsight DC change after plan lock, no extra boss turn without feature, no invalidated player declaration |

Specific suggested but **not yet approved** costs from owner brainstorm: 1 Resolve to push/declare a compatible fact; 1-2 Resolve for signature actions or ally defense; 1-2 Ruin for boss/hazard scenes. These are playtest candidates, not executable universal amounts. Increases to attack/dodge die count must define whether "+1d" means an additive die, advantage, or another authored expression; never guess.

**Narrative fact governance:** "I know the guard" or "I brought a grappling hook" is a request to establish a plausible new detail through a properly gated scene/world authoring action. It cannot retroactively create established NPC relationships, hidden clues, resources or sovereign facts for one Resolve without checking continuity, inventory and consent. "I automatically resist charm" cannot bypass a source-backed condition immunity check unless that Resolve power is actually granted.

## 3. Social and investigative mapping
Spark examples: observe outward emotion/cues based on a real perception channel; improve a forthcoming ally's social setup; de-escalate an authorized tangent. Do NOT equate "read a hidden insecurity" with omniscient access to private NPC psychology.
Strain examples: spoken slip, unwanted witnesses, awkwardness, reduced time horizon, conditional next-check pressure—each must be based on an observed statement/clock/relationship state.
Resolve examples: stand ground, invoke validated favor/contact, empower a speech. The NPC can still refuse; no roll or resource compels friendship, love, confession or support.
Ruin examples: an existing rival arrives at an earned moment, public misinterpretation, a previously grounded leverage reveal, a new time or resource cost. GM cannot manufacture non-existent damning evidence, force a PC into a legally binding oath/choice, or globally alter faction relationships without visibility and causality.
Speaker intent → tone/expression → NPC PRE-existing emotional filter → NPC interpretation → emotion response → validated relationship consequence remains the prior GEP-001 contract. Ruin and Spark modify scene opportunities, not mind-control.

## 4. WHISPER psychological integration without agency hijack
Current source fact: WHISPER's private felt emotion is **player-authored**; its post-turn emotional-history proposals remain optional and owner-confirmed. Mechanical status/conditions (fear, exhaustion, panic) are a SEPARATE rules domain.

To implement the proposed numeric mental-pressure subsystem, author a new versioned, prospectively enabled *psych-pressure* projection backed by accepted objective events. Define:
- stress/pressure metric, baseline, max, increments, recovery, traits, state-specific triggers, provenance and appropriate player/GM visibility;
- whether a particular minor **Strain** consequence could cause a *specific, typed* fatigue increase, physical overload or social pressure (rather than automatically marking one Mental Fatigue every time);
- how Spark can offer a **source-backed** brief grounding/recovery effect, and Resolve can pay for an authorized steadying action with real cost;
- threshold envelopes for psychological conditions, including which rolls are invoked and how narrative context modifies the risk;
- **max mental strain as necessary but insufficient** to allow a catastrophic involuntary cascade. Also require a prospectively opted-in campaign boundary, high-stakes event, actor-specific trait/history/physical mechanism, independently validated severity and an Atomic receipt.
- **rule:whisper** is a future narrow, versioned exception to GM_GUIDE's "never act for player" rule. The GM may not spend Ruin to force player speech, murder, flight or breakdown simply because enough pool was accumulated. Without that authorized exception, any flight/freeze/outburst is a prompt or mechanical condition with player-controlled response, never an automatic PC action.
- Time off or one Resolve can mitigate a source-defined mechanical condition; it MUST NOT forcibly rewrite a character's private psychological narrative, permanently erase trauma, diagnose a player, or delete previously accepted WHISPER history. Long-term character outlook remains player-confirmed.

**Example:** after an ally's death, Aero tries a nonlethal finishing blow. When baseline calm and no qualifying pressure rule applies, the valid nonlethal attack subdues normally, irrespective of very high damage (when source rules permit). Under a proven extreme-pressure trigger, a separate inverted **Control Under Pressure** check may be requested; exceeding the safe ceiling can create Strain, while catastrophic overforce also requires maxed psychological strain, valid situation, authorized death/injury severity and the campaign's pre-approved exception. A high ordinary d20 attack never directly produces accidental killing.

## 5. Purchased Maneuvers, incremental mastery and currencies
The Mocking Crane (free legal Combo) = Main Dodge + Bonus Taunt + preauthorized conditional Reaction Riposte. The free sequence is not a purchased Maneuver and may become a Tactic by actual play. **Buying the specialized Mocking Crane MUST give a measurable added effect at BASE purchase**, such as advantage on its eligible Taunt contest and (only if triggered and legally available) Riposte attack, subject to source, balance, counterplay and stacking tests. The player's own speech/gesture is selected; an automatic Reaction must be preauthorized, reserved and consumed only on trigger. No opponent compulsion.
- Dodge mastery ONLY adds an authored Dodge-derived improvement.
- Taunt mastery ONLY adds an authored Taunt-derived improvement.
- Riposte mastery ONLY adds an authored Riposte-derived improvement.
- Full component mastery can earn extra composite payoff such as next-turn conditional advantage or a 1-use Resolve earning opportunity if the exact owner rule is later approved; it does NOT automatically grant points/dice just because three skills are mastered.
- Higher future mastery nodes/branches are OPEN-ENDED as new content is authored and earned. There is no blanket progression cap. Per-roll stacking, resource holding and per-trigger idempotency are independent safeguards.
- A paid upgrade may alter the *kind* of bonus (control/mobility/options/recovery/counterplay), not merely grow raw number bonuses infinitely.
- The **Combo Judge remains primary:** compare free versus purchased at the same known state, show actual conditional success/counter risk, expected damage, chance of Spark/Strain/Resolve/Ruin as statistically justified, and specific source of mastery edges. Monte Carlo simulation cannot read hidden enemy stats for player-visible certainty.

**Serpent's Passage** purchases an authored conversion of otherwise illegal Main Dodge + Main Lightsaber Strike (2 Main) into an execution costing **1 Main + 1 Secondary**. It must specify what portion of Dodge's defense is actually retained. Mastery of Dodge affects Dodge-derived parts, not lightsaber precision; mastery of saber affects only its relevant part.

## 6. Team pattern application
Team Combo/Maneuver/Tactic tracks action and consequence axis separately per actor and for the declared shared objective. Team Spark may help an ally through valid shared perception and communication; Team Resolve pool is OPTIONAL and requires defined ownership/contribution, distribution, expiration and no forced spending of a teammate's resource. Ruin may advance grounded shared scene stakes but cannot silently spend a teammate's reaction or violate NPC autonomy. Allied NPCs need motivation/participation decisions, and no PC can authorize another PC without controlling that actor under the applicable control policy.

## 7. Implementation contract, fixture tests and precedence
1. **Reconcile vocabulary/data:** ACP-001 general composed 'Maneuver' records become generic Composition/Combo templates. CMT-001 specialized purchased 'Maneuver' records add purchase, prerequisites, unique benefits and mastery edges. Preserve existing IDs and migrations; do not relabel current combat catalog without a tested adapter.
2. **Author owner-approved schema:** primary_result, independent_chance_result, magnitude, immediate_event, earn/spend pool, source_event_ids, resolved_receipts, visibility, target(s), stage, actor and rule_version. Either a dedicated Atomic Chaos die or a pre-existing accepted outcome table can resolve side-effect polarity; verify independence experimentally if claimed.
3. **Separate account ledgers:** player-scoped Resolve (optional party pool) versus GM/scene-scoped Ruin; Spark/Strain are immediate consequences, not balances. Event-sourced with idempotency and replay, no client-owned counters.
4. **Maneuver ROI:** implement and simulator-test free Combo vs purchased Maneuver in isolated fixtures, including component mastery matrix and two-axis mixed outcomes, before granting it in an actual game.
5. **WHISPER gate:** implement versioned numerical pressure only if adopted, maintain player-private emotional self-report separation; no new psychological controller/LLM lane.
6. **UI:** render eligible categories only, show Primary Outcome + Spark/Strain/Resolve/Ruin separately in the verified transcript, allow player's choice of eligible spend; show GM expenditures only to extent observable; distinguish proposal, estimated and authoritative.
7. **Provider security:** same phase-scoped GM contract, authoritative receipts and server-side visibility; Gemini/GPT/local may propose candidates but cannot create pool deltas in prose. Resolve/Ruin spending must produce authorized gateway events.
8. **Staging:** no Hask Meadow or shared-0002 writes until explicit owner approval, a specific ruleset migration and separate test acceptance.

Mandatory tests: all 5 basic primary/consequence combinations; major earn/spend idempotency; unauthorized GM spend refusal; predeclared vs post-lock spend; no fabricated hidden fact; owner-selected Taunt speech; varying Dodge/Taunt/Riposte mastery; single-source Strain vs WHISPER pressure; catastrophic-gate denial when strain not maxed; no forced PC action by Ruin; source-backed NPC consequences; stable provider handoff and recovery.

## 8. Open numerical decisions
The owner selected **names and tier purposes**, not fixed mechanics: exact Chaos die and odds, Spark effects, Strain severity, how/when major Resolve and Ruin are earned, pool caps/decay, spend timing, resource die size, boss ability costs, what constitutes full vs partial success, Team pool ownership, and versioned psych-pressure settings remain unadopted. Mark options PROPOSED, not executable. Present comparative Monte Carlo fixture results before rule promotion.

**Supersession directive:** This contract joins ACP-001's exhaustiveness/authorization with CMT-001's purchased and growing Maneuver lifecycle. It corrects ACP-001's overbroad Maneuver noun only prospectively. No new action, pool, psychological condition or GM right is silently enabled.
