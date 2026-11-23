# Genesis Protocol — WHISPER × Crucible Pressure, Fatigue and Adaptation
**Contract:** WCP-001 | **Version:** 0.1 proposal | **Date:** 2026-11-22
**Authority:** This does not supersede the existing TB4-WHISPER-001 player-private emotional narrative and consent contract; it proposes additional prospective, event-backed mechanical rules. Live Hask Meadow and shared-0002 unchanged.

## 1. Actually implemented today
- `development/whisper/whisper.py`: player-explicit private beginning-of-turn feelings/motive/reflection, outward-expression-only observer projection, no inferred diagnoses or automatic alignment deltas.
- `development/whisper/post_turn.py`: candidate private emotional history after consequential accepted events; long-term candidate from repeated *player-confirmed* related history; accept/edit/reject/defer/custom choices.
- `Contracts/TB4_WHISPER_001_v0.1.md`: independently evaluates moral, psychological and social appraisals with provenance and privacy, no model seizure of player intent.
- **NOT currently implemented:** generic numeric mental fatigue, automatic hardening/conviction mechanics, Conscience Die, Ruin/Resolve pools, or a Ruin-driven character breakdown.
These are VERSIONED, OPT-IN additional mechanics, not statements about existing authoritative functionality.

## 2. Reuse one outcome substrate, not one identical condition
The owner wants physical exhaustion, mental fatigue, environmental overload, moral stress and interpersonal tension to *share* Spark/Strain and Resolve/Ruin semantics instead of separate bespoke dice engines. Reuse a common typed consequence interface and event-source ledger. But each domain has its own **cause, track owner, recovery, immunities, manifestation and source predicates**:
- `fatigue.physical`: cold, running, hunger, injury, oxygen shortage, burnout of a pilot, etc. Requires physical event and domain-specific recovery.
- `pressure.psychological`: situational fear, grief, horror, emotional overload, loss of composure. Requiring evidence does not reveal a PC's private stated felt emotions to NPCs.
- `pressure.social`: relationship exposure, leverage, scrutiny, embarrassment, reputational pressure; not an automatic psychological injury.
- `load.system`: hardware/ship/tech heat or material strain; does not directly cause character mental damage.
- `pressure.moral_dilemma`: optional high-stakes decision context, tracked separately from a binary good/evil alignment.
A Strain symbol MAY be translated into an approved condition in its matching domain when causal predicates and player/GM rules allow; never automatically adds `pressure.psychological` on every Strain. Resolve/Ruin accrue under separate major-eligibility rules rather than from all die faces.

## 3. Accepted event → mechanical and narrative appraisals
Example: a character knowingly leaves injured civilians to evacuate others during a ship rupture. This is a player-authored choice; the GM cannot decide that choosing survival is evil or that the PC regrets it. Proposed event fields include declared intent, feasible alternatives known at that moment, coercion, actor resources, witnessed outcome, objective causal effect and provenance.
- **Atomic** resolves what physically happens, under rules and receipts. Might apply physical fatigue from lifting wreckage or environmental harm.
- **Chaos** tests whether an authored Spark/Strain or gated major consequence is causally eligible (ally's observed reaction, pursuit clock, system heat), without invented facts.
- **WHISPER moral appraisal** evaluates *candidate* interpretation based on actor's information/agency/alternatives, separately from success and consequence; no forced alignment slide from a symbol.
- **WHISPER psychological appraisal** may propose a long-term inner reflection, but the player must accept/edit/reject it under the existing contract. Source-defined fear/exhaustion mechanical conditions can be real without dictating subjective inner feelings.
- **Social appraisal** records only NPC observations/claims/interpretations and scene/ruleset-tied relationships; no mind-reading.
- **Soul** narrates accepted outward effects and adopted subjective context according to visibility, not as proof a player feels guilt.

## 4. Proposed pressure triggers and safety
- Psychological pressure can accrue on events already tied to threats/conditions: trauma triggers, exhaustion, ally loss, repeated surrender situations, established character fear, sensory overload, dangerous setting. No blanket +1 from every story complication.
- Spark's `Grounding Moment` may decrease an eligible **mechanical** pressure effect, including supporting an ally if source allows. It never deletes private WHISPER history.
- Resolve's `Steel Your Mind` may suspend explicit mechanical penalties for an authored interval; does not necessarily cure the condition, change beliefs, or render the character universally immune.
- Resolve's `Anchor an Ally` needs real proximity/communication and that ally's independent character agency. A PC can't decide how another PC responds; NPC reactions are based on their state and choice.
- `Catharsis` at downtime may enable a mechanically defined decrease after a source-approved process and time, not automatically rewrite a character trait or erase an event from memory.
- A **Ruin** spend can offer a consequential *choice* or trigger a **legally granted** hazard/boss ability/pressure consequence; it cannot by itself force flight, attack, confession, accidental murder or long-term trauma.
- A catastrophic involuntary overforce cascade is legal ONLY if a campaign opted in prospectively to narrow `rule:whisper`, accepted relevant facts satisfy the actor-specific cause/threshold, maxed strain is present, Atomic resolves a bounded physical mechanism and severity and the action still matches its preauthorized exception. Max strain alone is not enough. No live use now.

## 5. Conscience Die and adaptation WITHOUT hidden moral determinism
Proposed optional **Conscience Die** is a dilemma-specific source-backed extra resolution channel; exact faces, cancellation, critical symbols, eligibility, cost and interaction with Agency/Entropy dice remain UNDEFINED. Do not implement or silently start rolling it.

The owner suggests two longer-term adaptation families:
- **Hardening / Desensitization candidate:** repeated *comparable accepted events* may make an actor less vulnerable to a specific previously shocking stressor, possibly at a cost to certain relationship-repair or grounding opportunities. No single survival choice proves emotional coldness. A player may intentionally remain compassionate, and an NPC may react differently. Mechanical acclimation to a horror is NOT the same as private moral failure.
- **Conviction / Anchoring candidate:** repeated deliberate, informed acceptance of a real personal cost for a principle may qualify for a resilience/Resolve-related feat or complication under separate proficiency/evidence rules. Sacrifice is not always virtuous; survival not always selfish.
- These adaptations require distinct accepted events, similarity/context evidence, owner-selected character response where subjective, reversible/contested changes, source-specific expiry/erosion and NPC knowledge constraints.
- Never secretly label a PC "calloused", "evil", "traumatized" or "good" solely from a Conscience symbol. A model's guess is a candidate, not character truth. Hidden mechanical meters (if approved) still have player-accessible audit/provenance and opt-in.
- Adaptation is **orthogonal** to mastery: a purchased Mocking Crane benefits from actual Dodge/Taunt/Riposte mastery nodes, not from a generic psychological hardening multiplier. WHISPER may affect situation-specific performance through accepted conditions, with explicit mechanics.

## 6. Cross-domain example table
| Context | Valid minor positive | Valid minor negative | Invalid shortcut |
|---|---|---|---|
| Combat | Spark: ally gains legal opening | Strain: established exposed stance | No free off-hand attack or new main action |
| Social | Spark: observed cue, useful question | Strain: visible hesitation/clock | No omniscient NPC motives or forced PC speech |
| Physical survival | Spark: brief footing/rest | Strain: fatigue when physically plausible | No automatic mental illness |
| Piloting | Spark: positioning or revealed safe channel | Strain: equipment thermal load | No unsupported equipment explosion |
| Horror | Spark: grounding if pressure event source | Strain: temporary fear penalty when eligible | No permanent trauma from one die |
| Moral dilemma | Spark: reasonable new option observed | Strain: environmental/personal cost | No "Survival = Evil" meter progression |

## 7. Acceptance and implementation order
A. Preserve TB4-WHISPER-001 compatibility, player-private vs observer views, post-turn confirmation and repeat evidence; test older appraisals unaffected.
B. Implement source-specific physical and psychological pressure metrics *if adopted*, with separate causal receipts and decay rules. Verify one Strain doesn't indiscriminately add mental/physical/social fatigue.
C. Add safe Spark grounding/Resolve resistance/GM Ruin hazard candidate menus in sandbox; test legal prerequisites, no secret exposure and deny forced PC dialogue.
D. Only then test hardening/conviction proposals using contrasting scenarios (similar event but different player motive; player who does not confirm a personality change; ally observing vs not observing; culturally distinct NPC interpretations).
E. Separate versioned high-stakes opted-in Conscience Die experiments after its face map and authority are defined; no live campaign activation.
F. Gate all major spends by resource owner, time, idempotent receipt, visibility, available source fact, causality, approved rule version and player consent where choice is required.
G. Keep actual GM provider authentication separate: neither WHISPER nor Ruin grants a write-capable OAuth scope.

**Open questions:** exact fatigue meters and thresholds, all numeric spend values, recovery pacing, psych-pressure visibility, Conscience faces and die size, eligible moral triggers, whether long-term stress adaptations alter mechanics, and campaign opt-in boundaries. Nothing here grants those rules today.
