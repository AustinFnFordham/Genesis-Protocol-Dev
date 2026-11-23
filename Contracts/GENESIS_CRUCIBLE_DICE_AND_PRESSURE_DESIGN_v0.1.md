# Genesis Protocol — Crucible Dice, Outcome Economy & Character Pressure
**Contract:** GCD-001 | **Version:** 0.1 owner-proposed design / simulation baseline | **Date:** 2026-11-22
**NOT CANONICAL GAMEPLAY:** This is a candidate replacement or overlay for particular resolution scopes. No SW5e/d20 campaign roll, Hask Meadow, GM provider, accepted receipt, or staging cursor is modified by documenting it. Sources: owner-provided face map and spends, SSRR-001, CMT-001, ACP-001, TB4-WHISPER-001, existing `development/whisper` implementation.

## 0. Scope and structural decisions

- **Atomic:** authentic dice faces, success arithmetic, net symbols, action and resource costs, immutable receipts, transaction/recovery and version.
- **Chaos:** source-backed immediate benefits/complications and major-bank earn/spend proposals under approved eligibility and visibility. Spark/Strain cancellation is mathematical, but Chaos does not improvise permission to change already committed facts.
- **Soul:** describes only accepted results, character styles and consequences; its prose cannot generate symbols, pool balances, dice or mastery perks.
- **WHISPER:** private player-authored felt state, perception/appraisal, evidence history and prospectively approved mechanical fatigue/pressure projections. It does NOT, in the present code, already have a universal numeric mental-pressure counter or authority to seize PC choices.
- **Combo/Maneuver/Tactic:** preserve free ordinary Combos and the existing Combo Judge. Purchasable Maneuvers gain an authored measurable boon over their free comparable Combo and grow with *each* independently mastered prerequisite. Learned Tactics emerge from validated repeated ordinary Combos, purchased Maneuvers or both. Team equivalents require each PC/ally's own permission, costs and evidence.
- **Universal, setting-agnostic vocabulary:** Spark and Strain = immediate net minor effects; Resolve (player) and Ruin (GM/scene) = eligible major event-earned resources. A separate source-approved physical-fatigue and psychological-pressure effect may result from Strain; Strain itself is NOT a mental diagnosis/meter. Ruin cannot force a PC's free-willed choice.
- **Versioned rules mode:** `genesis-crucible/0.1-candidate`; only opt-in isolated synthetic fixtures. Keep `cc-sandbox-0.5` d20 rolls unchanged. Later choose (i) full alternate Crucible core, (ii) narrative-symbol sidecar to existing d20, or (iii) parallel setting-specific resolver. Never implicitly hybridize two independent successes, dice tapes or receipts.

## 1. Two opposed dice pools — owner-proposed face map

Suggested product name: **Crucible Dice** (not Fate Dice/Genesys proprietary terms). On screen **Agency Dice** (player/active actor) and **Entropy Dice** (resistance, stakes and hazard). These names are not moral sides; an NPC can roll Agency dice, a PC can encounter Entropy dice. A distinct **Conscience Die** is a *possible*, optional dilemma-specific die whose actual face map remains UNDEFINED.

### Standard d6 (symbol ideas illustrative)

| Face | Agency die (active actor) | Entropy die (hazard/opposition) |
|---|---|---|
| 1 | Blank | Blank |
| 2 | 1 Success | 1 Cancel Success |
| 3 | 1 Success | 1 Cancel Success |
| 4 | 1 Spark | 1 Strain |
| 5 | 1 Success + 1 Spark | 1 Cancel Success + 1 Strain |
| 6 | 1 Resolve symbol **and** 1 Success contribution | 1 Ruin symbol **and** 1 Cancel Success contribution |

For this **particular draft**, positive objective symbols occur on **4/6 Agency faces** (2, 3, 5, 6), opposing cancel-success symbols on **4/6 Entropy faces** (2, 3, 5, 6), Spark on **2/6 Agency faces** (4, 5), Strain on **2/6 Entropy faces** (4, 5), and each major symbol on **1/6** of its respective color.

**Important clarification:** Resolve/Ruin major *symbols* are uncancelable, but each contributes a **normal** 1 Success / 1 Cancel Success to the separate OBJECTIVE sum, and that numerical contribution CAN be offset by opposing success/cancel symbols. The major symbol's eligibility for banking remains separate from objective cancellation. Otherwise the statement "counts toward success" contradicts "majors never cancel." Do not equate a Ruin symbol to automatic failure; it is one success cancellation, not an independent forced failed roll.

#### Proposed resolution algorithm
1. Draw only actual, explicitly authorized dice according to the actor's attributes/training and the specific difficulty/hazard. Do not trust a client-supplied dice list or model text.
2. Count `success`, `cancel_success`, `spark`, `strain`, `resolve_symbols`, `ruin_symbols` on RAW dice.
3. Compute `net_success = max(0, success - cancel_success)` for reporting; retain signed `success_margin = success - cancel_success` for possible graded outcomes. Candidate base task succeeds on `success_margin >= 1`, unless a source-defined difficulty threshold demands more. Do NOT silently reuse d20 AC/DC as Entropy dice.
4. Minor positive/negative symbols cancel **one-to-one**, `net_spark = max(0, spark-strain)`, `net_strain = max(0, strain-spark)`. At most one type remains from a single canceled pool, unless different source-valid events generate secondary effects.
5. **Never cancel major symbols:** `resolve_symbols` and `ruin_symbols` both remain visible; whether each becomes an actual banked point is governed by the chosen earning policy (unknown), per-event caps, pool balances and eligibility. Full auto-bank face 6 is a balance candidate, not approved fact.
6. Candidate optional conversion AFTER minor cancellation and BEFORE immediate spends: `3 net Spark -> 1 Resolve` and `3 net Strain -> 1 Ruin`; consumed symbols cannot also fund immediate minor effects. Conversion consumes a *net* group of three; per-roll limits, automatic vs chosen timing, actor/GM consent and pool caps require a decision. Do not create new resources from already-spent Sparks.
7. Mutate no world facts until Atomic validates the final interpretation and records idempotent receipts. In the journal store raw faces, counts, cancellation, margin, owner, objective, stakes, minor effects, major earn/spend, version and evidence.

### Exact mathematical sanity check (enumerable; NOT user-approved odds)
See `Contracts/tests/test_crucible_dice.cjs`, which enumerates the independent d6 face distributions using binomial probabilities. With the above **exact map** and success iff at least one net success:
- 3 Agency vs 2 Entropy → **56.79%** objective success, **64.61%** have a nonzero net Spark or Strain, **1.65%** yield 3+ net Spark, **0%** yield 3+ net Strain (only two Entropy dice), **59.81%** yield at least one major symbol. The owner-supplied rough "65% success" and "10–15% 3-Spark conversion" are NOT true at 3v2 for these faces.
- 4 Agency vs 2 Entropy → **76.82%** success, **70.37%** nonzero minor, **5.49%** 3+ net Spark and **66.51%** at least one major.
- 5 Agency vs 2 Entropy → **88.61%** success, **75.86%** nonzero minor, **11.39%** 3+ net Spark and **72.09%** at least one major.
- Resolve/Ruin symbols under unmodified 3v2 occur often: `1-(5/6)^5=59.81%` of rolls have **at least one** of either. This conflicts with "rare major outcomes" if **every** face-6 symbol immediately banks a full major point. Solve through separate major earn eligibility, rarer specialized faces/dice, delayed spend conditions, reduced pool refresh or other simulation-tested policy—not unproven marketing odds.

Never describe Sparks and Strains as canceling the major resource symbols. Signed net minor counts can be zero, resulting in no minor twist. Mixed Success+Strain and Failure+Spark are valid without forcing them on every roll.

## 2. Dice scaling, gear and mastery (noncanonical choices)
- **Attributes/skill ranks:** source-granted values may define Agency dice quantity (owner candidate `attribute 1–3 + skill 0–3` with most tests ~2–5 dice). This must be a **new, source-mapped stat conversion**; it does not automatically convert existing SW5e 8/16 stat scores or d20 bonuses into pool size. Low stats and training still get clear rules for empty/negative pools.
- **Difficulty:** author mapping of true stakes/opposition to Entropy dice (owner candidate 1–4). Opposed actor skill may legitimately affect Entropy, but private opposition numbers should NOT be disclosed through player-visible odds or raw GM dice.
- **Gear:** basic equipment may grant permission; masterwork or specialized gear may upgrade selected Agency dice to approved **d8 Mastery Dice**. A d8 has no specified faces yet, so **do not roll/use it** until source-linked exact faces, probabilities and stacking are authored. Improvised/damaged gear might add Entropy dice or require an alternative profile, never a free universal penalty.
- **Force augmentation:** independently offered to many source-eligible actions, but every option needs a granted augmentation profile, Force Point debit, exact affected component and legal scope. Do not conflate Force Point, Resolve, or mastery resources.
- **Maneuver upgrades:** an unlocked Maneuver's base boon exists at purchase and further effects can accrue via its component mastery nodes individually. Never impose blanket permanent progression ceiling. One-roll additive dice/advantage rules are a distinct authored limit.
- **UI pool display:** "3–8 dice shown, perhaps 1 center die" is an ergonomic hint, NOT a global mechanical dice cap. More mastery dice can be collapsed, paged, displayed in summary, or animated in batches without depriving high-level characters of earned dice. Avoid conflating rendering and gameplay mathematics.
- **Conscience Die:** no existing authoritative face map or predicate. It must NOT be rolled simply because the GM *thinks* an event is morally significant; use legitimate source facts, player-declared intent and stakes, and prospective opt-in.

## 3. Spend menus — proposed authority, NOT guaranteed automatic effects

### Player-facing positive menu
| Name | Currency | Example proposed effect | Required guard |
|---|---|---|---|
| Pass the Spark | Spark (minor, now) | Give ally +1 eligible Agency die next connected action | ally can perceive/support and has authorized action; no free new attack |
| Flash of Insight | Spark | One truthful bounded perception question | no unrestricted private NPC thoughts or hidden secret bypass; GM must cite accepted observations |
| Grounding Moment | Spark | Reduce 1 source-defined psychological pressure / help ally | only if actual mechanical pressure exists and player/ally eligible; don't rewrite subjective emotions |
| Quick Shift | Spark | Limited permitted cover/movement or draw/stow | needs exact distance and timing; cannot bypass held hand/object constraints or free infinite interactions |
| Second Wind | Spark | Reduce 1 eligible physical fatigue or minor penalty | exact recovery rate and condition type needed |
| Read the Room | Spark | Observe real emotional cues or improve situational social position | no reading internal intent telepathically or forcibly warming NPC disposition |
| Push Past Limits | Resolve (banked spend) | source-approved reroll/recovery or cost-bearing success | before commit or explicit Atomic alternate with an idempotent receipt; no retroactive rewriting of locked die |
| Defy the Odds | Resolve | defend against eligible condition/attack or shield ally | a legit reaction window/feature; no automatically negating fatality without approved power |
| Steel Your Mind | Resolve | ignore narrowly specified psych penalty for a defined window | cannot erase private WHISPER history or all psychological effects in every setting |
| Anchor an Ally | Resolve | offer stabilization assistance for an eligible ally | ally consent/agency, resistance/relationship constraints |
| Stand Your Ground | Resolve | improved resistance to coercion/intimidation | cannot force a different NPC's behavior or become blanket immunity to all mind control |
| Catharsis | Resolve (downtime) | reduce an authored pressure condition after safe roleplay and recovery | no automatic deletion of trauma, moral memory, lasting convictions or private player narrative |

**Owner excluded** Fuel Signature Move and Declare Story Fact from the final example table; do NOT silently reinsert as defaults. Any special Maneuver or narrative fact spend must be a separate future decision.

### GM-side negative menu
| Name | Currency | Example proposed effect | Required guard |
|---|---|---|---|
| Frayed Nerves | Strain | +1 psychological pressure or a short shaken condition | only if mental evidence/physical cause and approved psych-pressure rule, not whenever Strain occurs |
| Overextended | Strain | +1 physical fatigue or bounded next-action penalty | source-specific activity and finite time window |
| Costly Effort | Strain | debit existing ammo, battery, gear condition | item exists; physically caused; cannot invent failure of unrelated gear |
| Exposed | Strain | defensible flank/position opening for a qualifying next attack | no omniscient enemy advantage |
| Ticking Clock | Strain | advance real scene danger clock if risk was established | clock must preexist or be created by authorized scene rules, not silently fabricate imminent catastrophe |
| Slip of the Tongue | Strain | unwanted disclosure in actual spoken words or externally observed tell | **cannot force unspoken PC dialogue/secret revelation**; proposed external observation/cost or player consent needed |
| Escalation | Ruin | activate grounded hazard or enter authorized reinforcement | provenance, spatial constraints and budget |
| Hard Bargain | Ruin | offer success with resource/moral/tactical cost | **player chooses accept/decline**; GM does not choose PC moral compromise |
| Spiral/Panic | Ruin | source-backed acute condition when approved psych-pressure threshold met | requires prospective campaign boundary, specific evidence, verified Atomic conditions; Ruin alone never forces PCs to flee/fire |
| Unleash Threat | Ruin | enemy's granted interrupt/boss profile | the enemy needs a real authorizing feature and actual cost/interrupt timing |
| Burn a Bridge | Ruin | evidence-based relationship hit when actually observed | cannot invent a public oath or force long-term faction hatred without causal chain |
| Catastrophe | Ruin | rare major material/scene injury or loss | prospective stakes, severity table and defensible evidence, no forced arbitrary permanent trauma/death |

Each menu entry is a CANDIDATE execution/Chaos consequence profile, not immediate permission. Decide which entries survive balancing and make their own source, cost, timing, actor authorization, immunity and scene prerequisites explicit. No generator may automatically choose any psychological or moral effect simply because it sounds dramatic.

## 4. Potential Conscience Die and long-term moral adaptation (independent of Resolve/Ruin pools)
The owner proposes an optional third (center) die for **high-stakes moral tension**, tentatively called **Conscience Die**; it has no face list, odds or resolved eligibility in this design. Two thematic result groups can be **Sacrifice** (accept personal cost to protect someone/values) and **Survival** (prioritize immediate self/party safety), but these are NOT synonyms for Good/Evil, Light/Dark, success/failure or guilt. An altruistic survival choice and an abusive sacrifice demand are possible. Moral appraisal MUST inspect intent, alternatives, information, proportionality, coercion and actual result from TB4-WHISPER-001.

**Two time horizons:**
1. **Session:** temporary Resolve/Ruin balances with exact earned/spent receipts and scoped ownership; owner proposes a possible pool cap of five, or GM cap based on party size, as a BALANCE candidate. Reset/decay rules TBD.
2. **Long-term:** actor-specific history of confirmed choices, observations and consequences; possible actor traits/conditions like Hardening/Desensitization and Conviction/Anchoring, but no automatic hidden diagnosis or moral label assigned from a single roll.

**Hardening candidate (NOT an automatic personality verdict):** repeated, meaningfully comparable, player-authored or source-observable survival-first decisions may create a *reviewable* adaptation: reduced acute shock from specific witnessed horrors, while certain relationship repair/reassurance attempts require more effort. It must specify scope (particular stressor), exposure, repetition evidence, what the player actually did and knew, nonjudgmental wording, reversal/recovery and subjective self-appraisal confirmation. Not blanket immunity to guilt/panic, not inability to love, and not "becomes evil." Other PCs/NPCs may react only to acts they saw/learned through admissible channels.

**Conviction candidate:** repeated informed choices to bear a cost for others can produce a reviewable, earned trait: greater resilience/Resolve opportunities when defending a declared principle, with actual sacrifice costs. Not universal emotional fragility and not moral alignment score.

**Conscience Die cannot author a PC's decision.** Player chooses their deed; die can determine external consequences of a choice and eligible mechanical stress only under a specific authored rule. An involuntary response remains limited to a prospectively approved `rule:whisper` exception, normally requiring max strain plus independent causal criteria. WHISPER's existing player-confirmed private emotional interpretation is respected.

## 5. Choice examples / cross-domain acceptance
- **Combat:** Aero's purchased Mocking Crane can make the Taunt/Riposte odds materially better than free Combo, but a miss may generate Spark if an actual opponent overextends; enemy may learn based on witnessed evidence, not omniscience.
- **Social:** an unsuccessful negotiation may create an authentic Spark (learn a *perceived* public motive); a successful bluff can generate Strain (documentable tell or overheard remark). Resolve cannot compel NPC affection or invent a previously unmentioned friendship as established canon.
- **Exploration:** a failed search with Spark might reveal a new route but not the quest item; success with Strain might activate an already tracked patrol clock.
- **Piloting:** damaged fighter succeeds in maneuvering with Strain physical systems risk; Resolve might permit a separately granted emergency action, not rewriting a locked hit.
- **Horror/survival:** Spark may aid grounding, but Strain should map to cold/fatigue vs psychic panic only when the event's source says so. Ruin cannot force PC self-endangering speech.
- **Team:** each actor's linked outcome and Spark support has own evidence and consent; optional shared Resolve pool must have explicit bank owner and participation rules.
- **Farming:** players can't repeatedly make trivial checks to print Resolve/Ruin. Require material stakes, distinct accepted source events, anti-retry receipts, scene-level earn gates, conversion caps and an audit trail.
- **Privacy:** NPCs see expressions, claims, perception and valid observation; not hidden private PC emotion, WHISPER reflections or unrevealed goal.

## 6. Acceptance gate before gameplay implementation
1. Actual d6 face-schema validators, one-to-one success & minor cancellation, major symbols retained even when numerical success contributions cancel, clear success threshold and no misleading probabilities.
2. Deterministic independent test distribution across 3v2, 4v2, 5v2, plus 3:1 conversions (only net leftover and not both immediate effect and bank).
3. Benchmarks for economy tempo: earning Resolve/Ruin per relevant meaningful scene and per roll, difficulty, pool count, heroic vs villain balance; assess whether 1/6 face-6 majors are too common.
4. Rarity and fairness: GM never invents pressure, evidence or moral failure; negative minors can be zero. Conscience eligibility based on meaningful choices and no label bias.
5. Independent actor auth, private information, no retroactive dice spending, no unlimited extra actions.
6. Per-domain physical/social/psych projections and proper mapping of Strain to environmental fatigue; WHISPER current private choices untouched.
7. Side-by-side d20 vs Crucible sandbox fixture outcomes with comparable difficulty and reward pacing. Adoption must explicitly choose alternate mode or approved hybrid; **do not replace the live d20 engine** by merging this document.
8. Mobile theater can show up to ~8 dice prominently while preserving **ALL** mechanically required dice via scrolling/batching; do not impose gameplay cap from pixel density.
9. Only after tests and owner sign-off: source-backed ability/Maneuver augment profiles, proper case-specific spend menus, new event schema and accepted replay receipts in an isolated sandbox.

## 7. Open decisions that MUST NOT be inferred
- Alternative full Crucible vs d20 narrative sidecar vs independent setting rulesets.
- Actual character stat-to-dice mapping; thresholds and opponent/difficulty pool.
- Major earn eligibility (uncancelable symbols versus guaranteed points), bank caps, expiry and spend windows, conversion 3:1 on/off and per-event cap.
- Exact d8 Mastery faces; extra center Conscience faces, polarity, necessary trigger and opt-in.
- Exact numeric effects/costs (including +1 die, advantage, fatigue marks, penalty turns).
- Whether social “Read the Room” finds information or disposition and which NPC disclosure channels apply.
- How psych-pressure increments, coping/decay, tier boundaries, physical symptoms, and versioned player-control exception are authorized.
- Distinct Resolve pool owner (individual vs party), Ruin pool owner (GM/scene), and anti-hoarding.
- Source names/IDs and implementation interoperability with TB4-WHISPER-001, SSRR-001, ACP-001, CMT-001, existing SW5e rules and live campaign projections.

**This contract is a candidate system, not permission for an LLM to change morality, damage, rolls, character history or live game state.**
