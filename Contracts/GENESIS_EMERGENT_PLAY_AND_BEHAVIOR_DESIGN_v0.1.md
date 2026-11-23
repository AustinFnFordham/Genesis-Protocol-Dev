# Genesis Protocol — Emergent Play, Behavioral Consequence, Tactics & Scene Direction
**ID:** GEP-001 · **Version:** 0.1 · **Date:** 2026-11-22  
**Status:** OWNER DESIGN DIRECTION CAPTURED; NONCANONICAL implementation proposal and acceptance contract. No gameplay rule, numeric modifier, schema migration, character grant, deployment or live-campaign change is authorized by this document.

**CMT-001 supersession (2026-11-22):** For the definitive proposed distinction among free Combos, purchased Maneuvers, evidence-grown Tactics, Team variants, independently accumulated component mastery and open-ended progression, see [Combo, Maneuver, Tactic and Team Mastery v0.1](COMBO_MANEUVER_TACTIC_MASTERY_LIFECYCLE_v0.1.md) and its [JSON example](examples/combo_maneuver_mastery_example_v0.1.json). CMT-001 corrects incompatible *proposal-level* terminology in this document but does not change live rules or grant character abilities.

## 0. Purpose and source boundaries

Capture the owner's late-November 2026 playtest discoveries as durable, reviewable design input for the existing Genesis Protocol. The objective is to make actual play expressive, tactically deep, psychologically consequential, narratively continuous, and responsive without undermining deterministic adjudication. This is an ADDITION to existing architecture, not a mandate to rebuild the combat prototype or forge new parallel engines.

Evidence reviewed:
- development/combat_slice/COMBAT_V04.md at dev/cc004-combat-v04, commit 2455ab713ac0a829e1d57e4753ced5cef683243e (implemented noncanonical Combat v0.4; report claims 66 suites / 0 failures, not independently rerun in this documentation commit).
- development/combat_slice/{catalog.json,scenarios.json,engine.js,atomic_service.py,turn_driver.js}, same branch: existing capabilities, noncanonical proposals, event/receipt boundaries.
- api_bridge/gm/aero_character_runtime.yml on that branch: Aero's real current abilities, forcecasting, equipment and status.
- Contracts/CINEMATIC_COMBAT_AND_MANEUVER_CONTRACT_v0.2.md; Contracts/CHARACTER_CAPABILITY_AND_MASTERY_CONTRACT_v0.1.md; Contracts/SECONDARY_ACTION_AND_CAPABILITY_ACTIVATION_CONTRACT_v0.1.md on docs/cinematic-combat-capability-v0.2-20261121 (design reference branch; not all files are present on CC-004's branch).
- development/gm_provider/GM_GUIDE.md (currently forbids GM from spontaneously acting for player; a future owner-approved loss-of-control rule would require an explicit, versioned, mechanically adjudicated exception).
- Owner's discussion and actual Aero/Ilsa/Wick playtest feedback from 2026-11-22. Example names and dialogue below are illustrative and not committed campaign history.

Authority boundaries:
1. Atomic owns legal actions, costs, contested checks, deterministic dice, applied facts, approved state transitions, receipts, replay, and event commits; the browser and models cannot grant themselves mechanical authority.
2. Soul owns expression, character voice, imagery, dynamic combo naming, narration and dialogue proposal, bounded by accepted events.
3. Chaos owns grounded causal relationships, interactions, consequences, NPC reactions and candidate synergies; it proposes, it does not bypass Atomic.
4. WHISPER/psychology supplies versioned character-state evidence, dispositions, thresholds and candidate triggers to the authoritative adjudicator. It is neither a free-floating mood-to-bonus calculator nor a license for model whim.
5. Registry holds resolvable capabilities, tactics, mastery candidates and typed relationships; candidate similarity never silently grants a mechanic or creates a ghost relationship.
6. GM/Scene Director choose and propose plausible NPC/scene developments from established motive and state; persistent changes pass the existing accepted event/ledger protocol. Neither creates objective facts by prose alone.
7. No live Hask Meadow edits, no shared-0002 claims, no rerolls or retroactive rewrites, no Oracle deployment, no silent promotion to canonical rules.

### Decision status vocabulary
- **Design direction agreed:** Owner explicitly wants the experience/architecture. This is not equivalent to approving numbers or adopting a campaign rule.
- **Existing implementation:** Observed in CC-004 sources/report; not an assertion of production readiness.
- **Mechanics proposal:** Hypothesis needing balance review, source validation, tests and owner approval.
- **Open decision:** Must remain disabled or sandbox-only until resolved.

## 1. Combat: complete, honest capability coverage and action economy

The Main, Secondary, Bonus, Reaction, Movement, Object Interaction, Free/Speech interface must be mechanically legible, not arbitrarily numerically balanced. Main, Secondary and Bonus receive equivalent visual prominence, but not artificial parity in quantity or power.

**Attack** is an action-category selector, not a hardcoded lightsaber attack. Its available execution profiles must include every CURRENTLY authorized possibility given Aero's sheet and state: 1H/2H lightsaber; Echani unarmed strike (fist, elbow, knee, kick with no false empty-hand requirement); blaster pistol shot subject to actual ready/held/ammunition/range constraints; existing grappling; and conditionally available other real profiles. Plans may mix these only where the resource budget allows. Display unavailable profiles with specific explainable reasons and source status (sheet, campaign ruling, sandbox proposal, not learned).

Review *every* current grant and proposed secondary/bonus alternative, including Taunt, Battle Insight, Burst, Echani Flow Strike, Feint, Tactical Glance, Readied Dodge, Force Connection, Deflect, Sentinel Balance, equipment, reload, draw/holster, brief speech and optional Force augmentation. Do not equate a generic Force concept with a learned Force power. On the currently reviewed Aero runtime sheet, his two level-0 powers are **Battle Insight and Burst**; Telekinesis/Minor Telekinesis is NOT on that sheet. Older CC-002 documents describe an explicit *campaign-scoped* Minor Telekinesis exception; reconcile its provenance and campaign applicability before any new grant. No globally free Telekinesis.

Secondary Action is the **SA-001 prospective distinct budget**, not the earlier semantic Secondary Activity and not a universal extra Main/Bonus/attack. Alternate activation profiles do not add capacity, duplicate item grants do not double use caps, and literal zero cannot fall back to a default allowance. Preserve current campaign versions unless adopted under feature/ruleset gate.

Acceptance:
- Exhaustive sheet-to-UI coverage table with source path, profile, mode, cost, eligibility and disabled reason; full visual/touch QA.
- Hand/weapon/position/ammunition changes immediately update available cards and synergy prediction. Explicit conditional offers for player reaction and chosen redirect target.
- Tests for spent budgets, conditional Bonus/Secondary, range, concurrent effects, used reactions, per-rest counters, item loss, illegal/unknown power, and legacy Secondary-disabled behavior.
- The UI may not make a provisional maneuver look like a canonical class grant.

## 2. Roll Theater, sticky planning, and decoupled narration

The player should decide WHEN to trigger their pending authorized character dice; GM-controlled NPC dice execute under the GM's separate authority. Neither player nor GM chooses the result. Atomic is the only authoritative RNG source. The moment the plan is committed and a roll requested, use a stable identity binding campaign/session, actor, turn, plan, step, purpose, sequence, rules version and target where applicable. Duplicate requests return the SAME receipt; interruptions/reconnects resume. Hidden GM-only rolls and unrevealed facts must not leak through public roll labels.

Every visible roll should unambiguously show PLAYER — AERO versus GM — <NPC>, the acting entity, roll purpose, die formula, each die, numeric modifiers and their sources, target/DC where player-visible, whether it hit/missed/saved, derived effect and authoritative receipt. Avoid showing a secret AC/DC just because the model knows it. Animate only the already-authorized result; animations never affect odds.

The timeline/composer and currently pending Roll Theater/result remain sticky as ability cards scroll. Desktop uses an anchored sidebar; iPad/phone use an accessible, expandable bottom dock with safe touch targets, drop zone and state summary; no hunting for the drop target. Build → Roll → Resolve is one coherent workspace, not disconnected floating panels.

Mechanics resolve first. After an accepted, mechanically complete segment, Soul receives frozen facts and creates fresh optional cinematic text; the game is not blocked for 5–9 minutes by a narration model. If a player decision, reaction, eligible next roll, or actual adjudication gap remains, pause at THAT checkpoint rather than inventing an auto-choice. Speech remains ordered: a taunt/sentence before a strike occurs before it even if the enemy dies; speech after a defeat follows the committed ordering. Original player words and equipment truth must be preserved; not every insult is a mechanical Taunt.

**Current CC-004 limitation:** sandbox Atomic supplies and journals authoritative dice, but the client still computes combat results. v0.5 should make the SERVER independently replay and verify the full turn/outcome, use server-owned authoritative state/hashes, reject client alterations, and prevent encounter/session seed-shopping before real campaign integration. A mere client-supplied hash is not proof. Verified label only follows actual server verification.

## 3. Nonlethal intent, controlled force and accidental overforce

The desired story outcome is richer than a binary 'kill' / 'spare' switch. A character may DECLARE a nonlethal strike and MEAN IT, yet due to serious psychological stress, injury, technique, weapon, circumstance, and a genuinely failed control resolution, apply excessive force and accidentally kill or seriously injure the target. That tragedy must be mechanical, physically intelligible and causally earned — never a model improvisation or generic punishment for high attack rolls.

Illustrative physical sequence: after an opponent kills an ally and surrenders, Aero aims a measured Echani strike to incapacitate; his body fails to control the impact/follow-through, striking a vulnerable location with damaging force. The result can diverge from his intent without rewriting what he declared. Do not write incoherent prose such as 'anger moves faster than thought' while a weapon merely lowers, with no explained physical act.

**Two distinct dimensions**:
- Hit/connection quality follows its ordinary attack/check semantics: a higher ordinary d20 attack total is generally BETTER, not secretly transformed into a lethal failure.
- Force-control/intensity (or a bounded control/complication check, exact model TBD) determines whether the struck target is merely subdued, is seriously hurt, or suffers accidental potentially fatal overforce. Emotional strain may shrink the SAFE upper control window or increase the risk of exceeding it. The owner's phrase 'DC for nonlethal gets lower' refers to the **upper safe-force ceiling**, not a universal decrease in attack DC or a reason to punish nat-20 accuracy.

Target state, weapon lethality, environment, protective equipment, training, focus and plausible control maneuvers should influence this risk; a firearm or lightsaber is not automatically equivalent to a fist or restraint. Not every overshoot is fatal, and not every emotional episode causes a control failure. Proposed effect categories: no incapacitation; safe subdual (unconscious and stable where rules allow); uncontrolled injury with follow-up complications; potentially fatal overforce; otherwise apply current adopted death/injury rules. Exact bands/probabilities remain OPEN.

Consequences persist: surrender, mercy, accidental death, guilt, witness perception, bounty viability, lawful custody, rescue, interrogation and escape all form later scenes. Knockout is not mind control and doesn't compel answers. Capture requires restraints, time, security and relevant resolution. Any rule affecting a live or canonical campaign must be enabled before the encounter, not retrofitted after seeing dice.

Acceptance:
- A high ordinary d20 attack result does NOT create a spontaneous fatality.
- An explicitly declared nonlethal attempt under severe pressure can result in a physically grounded accident if approved control mechanics fail, with immutable evidence/receipts.
- Low-stress/trained controlled incapacitation remains viable; outcomes vary by actor disposition/weapon/target/terrain.
- An incapacitated opponent can survive and later become a social, legal or nemesis arc without guaranteed compliance.
- No retroactive reclassification of Ilsa's prior sandbox victory.

## 4. WHISPER: emotional pressure, involuntary cascades and earned tragedy

Health percentage may create pressure; it must NEVER map universally to fear. Full health could mean readiness or arrogance. <50% or <25% HP are interesting PROPOSED trigger bands, not canonical boons, saving thresholds, or universal debuffs. Same low-HP situation can evoke fearful withdrawal, berserker escalation, cool resolve, protective martyrdom, dissociation or panic depending on character, training, traits, history, bonds, active events, resources and culture. A concept such as 'Mark of a Martyr' (extra precision when badly hurt) requires a defined feature, exact math, bounded cost, prerequisites, versioned grant and explicit approval, not an improvised +25% from the narrator.

Crucial owner correction: Genesis is NOT required to protect a character from all involuntary behaviors. Rare dramatic 'WHAT HAVE I DONE?' events are intended when passion, fear, rage, trauma and stakes truly converge. A player may choose mercy but an approved, active loss-of-control mechanic may cause an involuntary harmful act or accident. The difference from arbitrary agency hijacking is **prospective rule authorization and auditable causal resolution**, not a last-second consent questionnaire each time drama emerges.

Contract:
1. Create a versioned psychological state projection and evidence records with source event IDs, character traits/values, current emotions/strain, perceived threats, relationship triggers, protections and decay; use observation vs objective knowledge boundaries.
2. A proposed cascade identifies explicit eligibility and prior committed trigger facts; Atomic validates probability/check and a bounded consequence envelope under a campaign rules/consent boundary enabled in advance. Never have Soul decide retroactively that a player 'must lose control' just because the prose would be dramatic.
3. Involuntary actions consume legitimate action/reaction/scene resources or have explicit exception rules; they cannot fabricate extra attacks, bypass a pending dice gate, or rewrite predeclared speech or choices. If prior GM guidance prohibits choosing PC actions, adopting this mechanic requires an explicit versioned exception in GM/rules contract, not silent contradiction.
4. Events record intent, divergence, physical mechanism, dice receipt (if any), resulting state and relationship/psychological effects. Both failures and successful composure must be possible, and the severity distribution must be balanced for rarity and foreseeable stakes.
5. The psychological state may be hidden or partially visible according to player perception; a 'mental bar' must not imply perfect insight or linear emotions. Internal motivation and observable behavior are distinct.
6. The owner can set campaign tone/content boundaries up front (including whether involuntary violence and accidental killing are allowed); no mid-roll surprise policy change.

Playtest two actors at same HP with different dispositions, plus one disciplined character in a rare extreme-pressure cascade. Confirm no model-invented behavior; capture why the mechanic was eligible.

## 5. Meaningful combos → emergent player-authored Tactics

Differentiate:
- **Maneuver:** one validated execution/capability.
- **Combo:** compatible sequence of actual actions, with predicted before and confirmed after based on what REALLY occurred.
- **Tactic:** a reusable, player-developed conditional plan with objective, sequence, target/environment preconditions, branch alternatives, provenance and signature identity. It may contain maneuvers, movement, defensive reactions, speech and conditional decisions; a Tactic does NOT create extra slots, learned powers or automatic bonuses.

Examples: an unarmed strike followed by an Echani follow-up CANNOT be called 'Blade and Body' if no blade participated. A legitimate Attack + Dodge + Counter chain might earn a flavor name proposed by the GM, but only after the actual resolved chain exists. Dynamic naming should match equipment/body movement, terrain, timing, objective and tone; allow player rename/retirement. Keep romance/social motifs in their appropriate context rather than confusing named albums with literal combat moves. Name is presentation metadata until an explicit Registry authoring/validation gate, never a source of mechanics.

Passive discovery is a requirement: the system quietly learns meaningful player preferences from **accepted, relevant causal sequences**, without repeatedly asking the player to save things. It can show a subtle 'emerging pattern' cue; player naming and mastery selection should be optional and never obstruct ordinary play.

Proposed evidence algorithm (not fixed rule):
- Normalize a sequence to typed Registry capability/profile references plus roles (setup, probe, defense, counter, control), outcomes, equipment, environmental context, timing and target; do not compare only card labels or free-text embeddings.
- Derive semantic/graph candidate neighborhoods and compatible variant patterns through the Forge Analogical Discovery Engine. Similarity SUGGESTS a candidate, never grants a tactic or bypasses entity resolution.
- Gather idempotent, accepted observations of deliberate, meaningfully distinct use; include wins, failures, adaptations and near misses when evidence policy permits; filter duplicated clicks, retry/replay, trivial farming, correlated same-outcome events and renamed copies.
- An illustrative heuristic is around 3 meaningful uses across 2 encounters for 'emerging', with diversity/novelty and player-intent confidence; owner must tune threshold per complexity and source evidence. A truly distinctive single situation may earn a provisional highlight without granting a mechanical Tactic.
- Promote to a reusable Tactic identity only after resolving prerequisites/conditional branches, source provenance and validation, preserving stable actor/scoped IDs. Reuse ONE Registry and existing combo definitions, not a new disconnected taxonomy.
- Develop candidate Mastery Graph branches from actual tactic purpose and evidence: reliability of setup, safer contingency, target adaptability, efficiency *only when approved*, and opponent counterplay. Evidence threshold opening a choice NEVER auto-awards bonus, level, proficiency, or learned capability.
- The Tactics tab selects a plan TEMPLATE. Revalidate live distance, hand state, object availability, action budget, enemy apparent stance, and known triggers; allow a conditional fallback rather than executing an invalid follow-up. Never reveal hidden enemy data as a predictive 'certainty'.

### Adaptive rivals / Nemesis
An NPC can learn what it reasonably perceived of Aero's actual tactic history, train or choose a legitimate counter, and adapt across encounters. It must not receive omniscient access to the hidden registry, be rewarded for unobserved moves, or teleport into perfect knowledge. A rival might learn Aero's usual feint pattern but have an outdated tactical model when Aero deliberately changes style — the Maul/Obi-Wan lesson. Enemy counters also use the same Atomic action economy and capability validator. This relationship is explicit and persistently versioned (observed tactic → inferred pattern → trained response → encounter consequence).

### Decision support
If a known opponent has previously countered a feint, the composer may provide an honest confidence-calibrated advisory: 'Your opponent has seen this setup; Dodge may be safer.' Odds estimates must use visible/known state, the exact rules and conditional uncertainty (movement-projected range included), not private AC or an LLM-guessed percentage. The warning is optional; the player may choose the risky move.

## 6. Generalize to noncombat: Approaches and Methods

**Objective:** the desired outcome (get Wick safely out of the barn).
**Method:** the procedural HOW or plan (exit by the rear door, scout courtyard first, secure a lantern, use distractions).
**Approach:** the attitude, presentation and relational HOW of engaging the situation or person (calmly reassuring, gently humorous, cocky, assertive, cautious, empathetic).
**Execution:** actual ordered declarations/checks, using the same capability and state authorities, with context-dependent time and resource costs.
**Interpretation/consequence:** NPC-specific observations, emotional filters, and causal updates based on accepted events.

These are not interchangeable. Two identical Methods may use distinct Approaches. Two similarly warm Approaches may hide very different intended Methods. The language layer recognizes player intent but doesn't presume identical outward reception.

A cross-domain behavior learner may notice recurring social humor, stealth habits, investigation strategies, merciful captures or improvised use of objects, building evidence-backed *Approach/Method* candidates and character signature style. Do not create a second action validator or second psychological truth. Exploration, conversation, romance and combat share source identities and committed event authority but use domain-appropriate availability and mastery policies. A social signature grants no automatic +5 Trust or Persuasion without approved capability.

## 7. Emotion-first dialogue, personalization and perception

Preferred interactive conversation experience: typically **4 or 5 authored response choices plus a real custom/free-text way out**, not a strict always-five button limit. Use KOTOR/Mass Effect/Dragon Age/BG3-style tonal variety and sometimes an explicit morally consequential good/bad/compromise choice **when earned by the actual scene**, not as obligatory axis buttons. Include more humor, flirtation, silence, uncertainty, defiance, warmth, vulnerability and character-specific phrasing. Let the GM dynamically tailor choices to how THIS Aero actually speaks (he can be playfully cocky and supportive); never force the protagonist to utter text he didn't select except under a separately adopted loss-of-control mechanic.

The owner-corrected causal chain is deliberately:
**Speaker intent → expression/tone → NPC emotional state (PRE-EXISTING FILTER) → NPC perception/interpretation → NPC emotional response/state change → relationship consequence and subsequent choices.**

Important temporal distinction: NPC emotional state immediately BEFORE the incoming statement affects perception; the emotional response AFTER interpretation is a separate update. NPC has limited knowledge, goals, history, trust, fear, self-image, cultural norms, recent trauma, and current situation. Example: Wick is afraid and quiet; Aero's joke may comfort him or feel dismissive, depending on preexisting fear and how the joke lands. Aero observed Wick withdrawing and became especially nice and supportive; don't label that automatically manipulative or effective. Allow sincerely intended reassurance to be misinterpreted without declaring a hidden relationship adjustment as guaranteed.

Response preview can label proposed **tone** (Cocky, Calm, Empathetic, Humorous, Assertive, Deceptive) but cannot promise how the listener will take it. Allow nuanced mixed intent, deliberate sarcasm, moral conflict, social risks and interpretive uncertainty. NPC-only hidden assessments stay private; observable cues may be shown, no mindreading. In-world characters retain consent and agency, including romantic rejections and changed boundaries.

Adult romance tone: support affectionate, emotionally intimate, flirtatious, suggestive, non-graphic and fade-to-black scenes without blanket sanitization, within explicit campaign boundaries and character consent. Never force affection/sexual access via a high persuasion roll. Couple/romance combinations are social relationship content, not confused with attack mechanics.

Tests: same spoken line to frightened versus relaxed Wick, same Wick state with compassionate versus smug tone, prior trust changes interpretation, humor candidate matches Aero's established voice, NPC declines/changes topic, no leaked private score, no free mechanically guaranteed moral alignment.

## 8. Scene Director: momentum without forced plot

The Meridian Reach lesson is not that the GM needs to invent more random twists; it needs to recognize a scene becoming repetitive, emotionally productive, unresolved, ready to move, or at a justified transition.

Introduce a scene-level planner/director ABOVE individual dialogue exchanges and combat beats, but BELOW authoritative world facts. It reads current objective, unresolved stakes, NPC goals, accepted events, scene phase, previous turns' novelty, tension, emotional trajectories, elapsed fictional time and the player's expressed plans.

Possible outputs: hold meaningful silence; surface an earned cue; allow NPC to make a motive-consistent decision; introduce a pre-established consequence at its plausible time; shift spatial focus; prompt a genuine choice; or close/transition a scene and resume open threads elsewhere. It MUST NOT solve a locked mystery, auto-compel a character to speak, fabricate an NPC confession, move the player or end a crucial encounter simply to satisfy pacing metrics.

Pacing proposals go through deterministic continuity/position/time/resource gates before becoming events; otherwise remain narration or explicit options. Track scene-progress evidence over time and preserve world-state continuity across GM providers. The Director should stop cycling six dialogue replies that make no change, but can intentionally maintain silence if it advances tension/interpretation. No arbitrary fixed number of exchanges triggers a mandatory plot twist.

Acceptance: prove Wick can remain afraid and quiet while Aero tries to reassure him; prove stalled circular dialogue can reach a causal exit or meaningful decision without new lore; prove mid-scene provider handoff retains intention, NPC knowledge and unresolved stakes.

## 9. Forge, Registry and runtime contracts

No duplicate authority:
- Reuse the existing capability Registry, execution-profile schema and typed relationship vocabulary. The Tactic is a validated, Registry-backed composite plan/template with provenance and conditional steps; analogical suggestions remain candidates.
- Reuse existing accepted event records and Atomic dice receipt authority for combat, social checks, damage, emotional state changes, tactic observations and scene updates. Domain-specific event types must be versioned rather than appended as opaque story text.
- The read-only Soul facts copy can drive proposed prose. Actual state changes (injuries, emotions, recognized tactics, relationship updates, mastery evidence, scene state) must be committed via authorized gateway/ledger pathways, not by a UI callback or model text.
- Psychological state projection and NPC observation history require privacy boundaries and causal source links; false precision in emotion gauges is discouraged.
- Preserve ruleset/campaign version pinning, RFC6902-style validated state mutations where applicable, append-only decisions, replay protection and provider neutrality. Don't assume that the sandbox Atomic journal is identical to the live gateway's combat, roll or storage APIs.
- Separate **mechanical capability recognition** from **semantic similarity** and from **cinematic name suggestion**. Names/labels and repeated model requests are not mechanic grants.
- Canonical promotion requires data schema review, source conflict reconciliation, owner-approved balance and boundary choices, regression/interrupt/recovery tests, then explicit versioned campaign migration with a documented rollback strategy.

## 10. Implementation sequence and release gates

| Milestone | Deliverable | Minimum gate |
|---|---|---|
| CC-004 (existing) | Sticky composer, player/GM Roll Theater, full Aero sheet coverage, equipment-aware combo confirmation, sandbox Atomic seed/journal | Already implemented on dev/cc004-combat-v04; reported test pass, independently inspect before promotion |
| CC-005 (next) | Server-replayed, server-verified turn results; anti-tampering and anti-session-shopping; Fix Deflect target choice and current ranged-in-melee decision as separately adopted | Match every accepted turn to authoritative server reconstruction, refuse forged client state, recover without reroll, no campaign writes |
| GEP-002 | Nonlethal control/overforce sandbox + WHISPER evidence state and validated pressure/cascade hooks | Prospective policy, rarity/balance simulations, ordinary high attack roll always beneficial, physically coherent narrative, immutable receipts |
| GEP-003 | Passive semantic tactic discovery, Tactics tab, authored names, candidate mastery, measured Nemesis learning | Meaningful-use deduplication, eligibility, conditional branch validation, anti-farming, no free new powers, knowledge boundaries |
| GEP-004 | Approaches/Methods and dynamic 4–5-option dialogue incl. humor, custom text, emotional-state-first interpretation | Persistent character voice, NPC-specific response, source-bound relationships, consent and no unearned scores |
| GEP-005 | Scene Director, provider-neutral continuity and narrative pacing | Deterministic scene transitions, no fabricated lore, preserves unresolved stakes and world state |

Every milestone: isolated branch; inspect existing implementations; tests at engine/API/browser/mobile; performance, replay, interruption and privacy checks; user playtest; written known gaps; explicit acceptance before merging into live Hask Meadow/Oracle. Do not block CC-005 on open WHISPER numeric details. Do not rebuild a second combat resolver.

## 11. Open owner decisions (DO NOT infer defaults as canon)

1. Nonlethal: exact attack/force-control composition, safe window, effect/severity bands, lethal equipment restrictions, critical damage handling, player-visible risk warning, accident rarity.
2. WHISPER: mood/strain vector, trigger policy, protections and decay, involuntary-action severity, advanced character consent/boundaries and relation to current 'no player agency hijack' rule.
3. Force augmentation: eligibility, whether it is attack/defense/control/damage, duration, 1 FP per use, stacking, once-per-turn and current character grant. The existing CC-004 Force-Guided Strike +1d4 attack is explicitly a sandbox proposal, not a general Force power.
4. Tactic recognition: normalization, meaningful repetition threshold, candidate-to-saved transition, mastery evidence rubric, naming conventions, tutorial/notification cadence, rival learning and forgetting.
5. Capabilities: exact Secondary/Bonus catalog, alternative profile authorization, unknown power vs campaign-specific exception; no unearned Minor Telekinesis on Aero's current sheet.
6. NPC dialogue: how much tone information and emotional state may be revealed; controls for player-specific humor vs spoilers; romance boundaries.
7. Scene Director: state schema, 'progress' evidence, scene transition authorization, pacing safeguards, privacy and provider handoff.
8. Any proposed ranged-in-melee rule or fixture balance changes need explicit owner approval before canonical use, even if applicable source rules are familiar. Deflect redirect follows Aero's current sheet's player-chosen 30-ft visible target.
9. Who may execute a player-control exception and how loss-of-control gates coexist with prior GM guidance, action economy and campaign boundary agreements.

## 12. Traceable acceptance stories

- **Ilsa and disarm:** If Aero loses the lightsaber and attacks unarmed, the accepted sequence cannot confirm or name a 'Blade and Body' maneuver; it may receive an original unarmed-flavored name with zero automatic bonus.
- **Aero roll:** Player presses Roll; Atomic returns receipt. Network drops; replay yields identical dice/HP/steps with no duplicate roll; GM's dice are clearly labeled and separate.
- **Psychological mercy:** Aero intends nonlethal subdual after an acute loss. A prospectively approved control failure may cause physically coherent excess force; a normal high attack roll by itself never causes that tragedy.
- **Surrender consequence:** A spared opponent can be questioned later but may refuse or lie, escape custody or become a nemesis; no automatic interrogation success.
- **Rival adaptation:** Rival watches repeated feint/counter tactics, has legitimate knowledge and training, then counters one; Aero can change technique and the rival's stale expectation can fail.
- **Wick and intent:** Aero proposes rear exit Method while using a gentle humor Approach. Wick's PRE-existing fear conditions whether the same joke comforts or unsettles him; subsequent relationship change is not assumed from player's intent.
- **Dialogue individuality:** Four or five choices reflect established Aero tone incl. humor and an optional custom line, with occasional meaningful moral choice; the same menu is not blindly recycled each encounter.
- **Scene pacing:** Wick goes quiet. Director preserves emotionally meaningful silence or chooses a justified transition, not an invented confession or mandatory plot twist.

---

**Document change control:** This document preserves the owner's design intent and unresolved mechanics. It must be reviewed and explicitly adopted through future source/ruleset gates before being treated as canonical gameplay law.
