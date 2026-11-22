# Genesis Protocol — Cinematic Combat, Maneuver & Character Integration
**ID:** CC-002 · **Version:** 0.2 proposed · **Date:** 2026-11-21 · **Status:** Design contract / implementation handoff, NOT deployed

**Authoritative references:** [Character Capability & Mastery v0.1](CHARACTER_CAPABILITY_AND_MASTERY_CONTRACT_v0.1.md); [Secondary Action and Capability Activation SA-001 v0.1](SECONDARY_ACTION_AND_CAPABILITY_ACTIVATION_CONTRACT_v0.1.md); `campaigns/starwars_litrpg/creator/{DESIGN_DECISIONS,TURN_CONTRACT,ACTION_ECONOMY_RULING,JEDI_FUNDAMENTALS}.md`; character runtime `api_bridge/gm/aero_character_runtime.yml`; existing Registry/Forge maneuver candidates. Read current implementation before editing.

## 0. Status, authority and owner intent
This companion contract consolidates design discussion into a versioned, implementation-ready **proposal**, not a retrospective declaration that numeric values and exceptions are canon. Owner wants a **playable, complete, noncanonical Level-1 Aero combat prototype**, not another partial design exercise; wants all sourced lightsaber forms and comparable differentiated firearm/melee styles; wants a card-based cinematic Turn Builder and the **same Atomic action adjudication for player and NPC actors**.

**Claude is lead Genesis engineer and owns the gameplay implementation, content reconciliation, tests and dedicated feature branch. GPT/ChatGPT Work owns the independent three-provider interoperability lane:** Codespace hosting/access, MCP/GM tools, Git-backed gateway persistence, `storage_recovery_required` diagnosis and Claude↔GPT↔Gemini routed-turn acceptance. GPT may independently test the gameplay branch, but must not create a competing combat engine. No implementation task is authorized merely by this document; use explicit owner prompts for execution.

Do not touch live `runs/hask_meadow_r2` or any canonical character sheet/ledger; do not change shared `staging/provider-shared` / `staging/shared-1`; do not alter accepted dice, implement a rule across campaigns by default, merge, deploy or start a paid API/hosting path without owner approval. For sandbox rules use version opt-in; preserve current turn-contract/3 behavior.

## 1. One mechanical language across actors
Proposed action budget in combat: Main 1, Bonus 1, Secondary 1 (future SA-001 ruleset), Reaction 1, movement, one ordinary object interaction, contextual free conduct; capacity only changes through explicit grant. The current production Turn Builder does **not** yet implement a Secondary budget. Every actor—player, NPC, adversary—presents declarations to the **same** authoritative resolver and shares reaction timing, capability checks, geometry, resource debits, dice receipts, interrupt handling and ledger rules. Model-generated enemy plans cannot conjure extra actions. Legitimate adversary exceptions must be explicit and validated. NPC perception and knowledge constrain NPC decisions; hidden data must not appear in public cards or combo previews.

Distinguish:
1. **Skill/proficiency**: learned competence or check expertise; not necessarily an activatable ability.
2. **Maneuver**: tactical objective such as Feint, Parry, Riposte, Disarm, Called Shot, Control, Takedown.
3. **Technique**: specific means of fulfilling a maneuver, including Blade Bind & Strip or Precision Shot; can grant execution profiles.
4. **Fighting Form / Style**: broader training path or stance family, e.g. Makashi, Soresu, Echani Flow, pistol CQB; grant specific documented proficiencies/techniques, never blanket free modifiers.
5. **Weapon configuration**: one saber, saberstaff, paired sabers, shoto, crossguard, blaster pistol, rifle, repeater, sniper etc; determines compatibility, occupancy, reach, reload, equip state and legal technique subset.
6. **Execution profile**: versioned ruleset-backed, prerequisite-validated trigger, exact costs (including compound), resolution, target/geometry, available effect and usage cap.
7. **Augmentation**: optional, explicitly granted expenditure of Force Points or other resource to change a named execution profile; cannot invent unlearned Force powers.

All mechanical references resolve to Registry entities with valid authority, provenance, character entitlement and revision. A draft labeled `power_type: Maneuver` is **not automatically a legal Power**. Existing draft feint/parry/disarm and 27-entry quarantined maneuver catalog are source candidates; review, repair, split and promote through normal gates only on approved implementation scope. Do not blindly import cross-system superiority dice or class synergies.

## 2. Candidate action economy / maneuvers
Proposals below are **not canonical grants**. Claude should verify source-specific rules, produce test fixture parameters and enumerate balance decisions rather than assert inferred numbers as owner-approved.

| Maneuver / skill | Candidate execution | Special behavior / constraint |
|---|---|---|
| Weapon Feint | Secondary setup; follow-up strike consumes its own Main/Attack | Contested read/deception vs relevant defense; bait accepted, ignored or spotted. A defender need not spend Reaction to be deceived; Feint does not auto-hit. No unlimited Feint spam. |
| Parry | Reaction, grant-conditioned; passive training may change eligibility | Weapon or guarded-limb redirect of eligible melee strike; default source draft reduces damage by superiority die + Dex **only where actor has that actual resource**. A passive defense trait cannot roll free on every incoming attack unless an authored, bounded profile expressly allows it. |
| Riposte | Reaction on eligible opponent miss / successful redirect, per learned trigger | Consumes Reaction unless explicit alternative/counterpackage; cannot create recursive unbounded counter chains. Source draft is reaction after opponent misses melee attack. |
| Readied Dodge | Secondary preparation + Reaction at eligible trigger (if both required by profile) | Trained scope and risk-profile advancement; one ordinary Reaction remains unless capacity explicitly granted. |
| Reflex Cascade | Master Dodge future node | Extraordinary explicitly limited reaction exceptions, possible counter and perception/resistance-gated Fear after a successful landed counterattack. Dodge probabilities 50%, 66.7%, 83.3%, 98% are hypotheses and need roll model and stress tests; **no automatic universal Fear**. Flavor may use short phrase "Be water, my friend" subject to attributed-source/copyright treatment by publisher. |
| Disarm | Main attack/maneuver; optional Secondary setup | Separate techniques for blade bind, weapon-hand control, blaster precision shot; successful hit is not automatically disarm—author target resistance, saves, effect and weapon landing/possession. |
| Called Shot / Disable | Main attack; modifier or additional costs by technique | Target leg, hand, held weapon, mechanism; explicit penalties/thresholds and nonlethal outcome rules. A declared intent to capture doesn't guarantee survival or limb preservation. |
| Controlled Takedown | Compound Main + Secondary candidate | Leveraged grapple, trip or control; opposing checks, creature size, target state, reach and positional consequences. |
| Echani Flow Strike | Main unarmed attack **or** optional Bonus follow-up after eligible melee Attack Action | Existing main unarmed +5, 1d4+3; proposed follow-up +5 to hit, **1d4 damage without Dex bonus**, 5-ft reach, one per eligible Bonus, no free hand required for kick/knee/elbow. Bonus profile is **new**, subject to approval/tests. |
| Quick Throw / Improvised Throw | Main attack for hostile damaging throws; supportive variants possible | A Bonus or Secondary version requires explicit training/profile and equipment interaction limits; don't assume BG3's class-dependent Enraged Throw applies to all. |
| Force Connection — Focused | Existing Main; proposed Secondary tactical reading variant | Source-authorized Force-sense boundaries; do not double-stack advantage with existing Echani Combat Discipline/Communication. |
| Minor Telekinesis | Existing Main in combat; proposed Secondary or Bonus for approved limited object manipulation | Campaign provisional scope is one visible unattended object ≤10 lb within 30 ft, zero Force Points, no damage/creatures/disarm/projectile interception. Incidental flourish is free only if it changes no mechanical state. Complex/sustained handling remains Main unless new profile approved. |
| Battle Insight | Existing Main, Level-0 Force power; **proposed** Bonus conversion | Level 0 is not itself a Bonus authorization. Preserve 0 Force Points, one target ≤30 ft, advantage on next attack, adopted concentration; test same-turn setup/attack and interaction with Feint; advantage does not stack. |
| Tactical Glance / Search | Passive sense baseline; bounded free glance, Secondary focused scan, Main investigation candidates | A free check may resolve uncertain perception but cannot be rerolled repeatedly; distinguish Perception proficiency (+4) from untrained Investigation (+1) and avoid leaking hidden DC/actors. |
| Taunt | Existing switch-gated Bonus | Free speech/insults are allowed without automatic debuff; ability-granted contested Taunt retains Bonus unless separately approved free activation. |

Additional source candidate maneuvers to reconcile: Trip Attack, Guarded Stance, Evasive Footwork, Reposition, Commander's Strike, Rally, Analyze Weakness, and non-starship vs starship distinctions. No automatic promotion of quarantined records. Source mechanics and Genesis adaptations must be visibly distinct.

## 3. Reaction ordering, combos and compound costs
Atomic must simulate ordered declarations with provisional resource escrow and conditional branches; do not precommit later steps that become invalid after interruption. For example:
**Secondary Feint → Main lightsaber attack → defender eligible Parry/other Reaction → attacker conditional Bonus Flow Strike → Free speech**. A reaction can trigger in between any relevant subevents. A defender who spent its only ordinary Reaction on the first attack cannot Parry the follow-up absent explicit grant. A counterattack triggered from a defense is an actual attack with proper target, roll and resource rules, not an animation-only hit. A new Reaction may be unavailable even if the actor has an unused Secondary Action.

Permit compound cost `{main:1,secondary:1}`; explicit optional overcommit of another resource can grant bounded authored benefit, but mere ownership of extra action capacity doesn't grant bonus damage. Validate once per actor per step, shared usage caps, hand/weapon state, target location, stacking, interruptions, revalidation and idempotent resumptions. Add recursion depth/trigger-id fencing and prevent reactive loops. The GM never chooses undeclared PC responses or retroactively reorders steps.

## 4. Full combat form and weapon-style catalog
Author a reference-backed catalog separating (a) lore traditions, (b) source-authored rules, (c) Genesis proposals. Include classical lightsaber I Shii-Cho, II Makashi, III Soresu, IV Ataru, V Shien/Djem So, VI Niman, VII Juyo/Vaapad and relevant documented auxiliary traditions (Jar'Kai, Sokan, Tràkata, others with evidence). Don't treat these as ten interchangeable level-one bonuses. Validate form availability and prerequisite training. Permit dynamic form or technique choice **per eligible maneuver/profile**, with defined stances, transitions and opportunity costs; do not stack incompatible styles for free simply because the UI allows a form card.

Build mechanical compatibility by form × weapon configuration × technique, distinguishing standard and curved-hilt sabers, saberstaff/double-bladed, dual-wield, shoto, crossguard and future split-hilt. Incompatible combinations must be refused or have separately authored variants; no automatic approval via a form name.

Author comparable *meaningful* style branches for vibroweapons, Echani unarmed, pistol/CQB, rifle/carbine, sniper/marksman, repeaters/suppression, improvised and thrown weapons. Equality means depth of viable choices, **not an arbitrary equal number of named forms**. Use source provenance and style-specific grants; don't silently retrofit proprietary Star Wars mechanics into Genesis-wide canon.

### Blade Bind
A **blade bind** is sustained weapon contact/pressure during a clash. It can be used as the physical setup for a technique that rotates, redirects, or strips a weapon out of the opponent's grip. It is a **fictional combat position / technique opportunity**, not inherently a free successful disarm. Needs valid held weapons, contact, leverage, target resistance and timing.

## 5. Aero Level-1 representative build
Character authority: `api_bridge/gm/aero_character_runtime.yml` defines Echani Sentinel 1, newly knighted; Vael Taron formerly Shadow and later Jedi Temple Weapons Master. Already recorded: DEX16, WIS14, CHA14, 11 HP, AC13, 3 Force Points, proficiency Insight +4, Perception +4, Persuasion +4, Intimidation +4, Technology +3; simple weapons, lightsabers, blaster pistols and unarmed strikes; existing Combat Discipline, Combat Communication, Martial Arts Training, Echani Grappling Training, Lightsaber Deflect Tier 1, Sentinel Balance, Force Connection; learned Battle Insight and Burst; explicit campaign-scoped Minor Telekinesis.

Propose **Weapons-Master Apprentice** as a noncanonical loadout with signature mastery in lightsaber, Echani close combat and combat reading, and source-justified Riposte/Parry/Feint training. Distinguish what sheet already grants vs historically plausible but ungranted vs newly proposed vs future tier. Do not equate current weapon proficiency to Advanced mastery; don't pregrant Sentry subclass. Examine Acrobatics, Investigation, Stealth, Search, animal handling and alternative encounter competencies without turning a specialist into an all-rounder. Animal Handling is **not** granted by dueling training. Baseline skill/stat bonuses remain until explicit approved corrections. Use isolated fixture; owner reviews exact new sheet grants and mechanical consequences before any canonical import.

## 6. Cinematic Momentum and player-authored Spotlights
Introduce an **optional sandbox** Cinematic Judge that recognizes validated creativity, meaningful risk, combinations, character expression, rescue, restraint, diplomacy and consequential decisions. **No automatic extra mechanics from narrative sentiment, more actions, or greater damage.** Earning logic needs an auditable rubric, bounded intervals, anti-farming, explainability, no provider-dependent subjectivity or hidden bias. Cinematic Momentum is not necessarily existing character XP or Inspiration; distinguish pools and evaluate coexistence.

- **Director's Cut:** a earned, opt-in player narration privilege **after** Atomic has accepted a success, rescue, defeat or other secured outcome. Player can dramatically describe the authorized result but not change causal truths, wound legality, location, ownership, damage, new powers or future canon outside that result. Soul may assist; player chooses final words and style within contract.
- **Legendary Moment (separate proposal):** extraordinary cinematic consequences *beyond* the mechanically established outcome require a separately validated, scarce exceptional-effect grant with explicit cost, scope, prerequisites, continuity implications, no roll rewriting, and owner approval. Do **not** implement as a hidden excuse to invent unlearned Starship Telekinesis at level one.
- Narrative arcs and social triumphs are eligible for equivalent cinematic opportunities. A character may decline a Spotlight. No button forces player narration or rewrites previous turn.

A ship with 1 HP remaining and a *confirmed* finishing hit may receive glorious narration. If the portrayal introduces physically impossible Force control, either keep it as nonliteral expression, require a specifically permitted Legendary Moment, or offer a legal alternative; the game should not claim that Force ability was learned.

## 7. Card composer, in-place playability, and testing
Preserve existing `ui/src/composer.js`, action sequencing, free text, pause/Continue, reaction prompting, and deterministic preflight. Prototype a touch-first/keyboard-accessible hand of ability cards, tap or drag-to-sequence, ordered conditional chain with interruption status, and full-modal card inspection (flavor + precise rules + source + mastery + constraints + image when available). Compact Atomic quick view displays action cost, availability reason, known range, resources, target eligibility and *conditional* combo outcomes, never hidden DCs/enemy AC/unknown powers. "Combo Judge" has:
1. **Atomic** legality, budget, known conditional synergies, approved modifiers and consequences; no fantasy score.
2. **Cinematic** optional descriptive feedback or momentum rubric; no effect unless approved by a defined mechanic.

Model real same-resolution gameplay for NPCs using common validator; NPC UI can be different but actions may not bypass validation. Cards must remain presentation—never authoritative rules source. Animation follows accepted outcome; quick-time inputs must not be required for legality or make slower devices weaker. Mobile touch and accessibility are first-class.

### Minimum playable slice
Use an isolated fixture for Aero vs skilled duelist (Feint, Riposte, Parry, Dodge, Flow Strike, control/disarm, resource exhaustion, attack timing) and Aero vs unfamiliar animal/predator (species-specific tactics, uncertain perception, no free Animal Handling). Test Force augmentation, off-turn counter ordering, double counter loop prevention, free speech vs Taunt, setup after target moves, loss of weapon mid-chain, concealment, all resource budgets at literal zero, exact valid roll/receipt replay, disabled SA-001 legacy behavior, and NPC/PC result parity. Show exact run instructions and one-click preview where possible; no assertion of production readiness without interactive device evidence.

## 8. Relationship to gateway interoperability and ownership
**Claude's development lane**: audit existing code, develop sandbox implementation, use current validators, verify tests, provide independent feature branch and commit(s), and deliver operator-readable playable artifact. Do not edit GM provider connector credentials, authentication, cross-provider staging, hosted recovery flags, or production deployment as part of combat work.

**GPT's integration lane**: retain ownership of tri-provider Codespace/MCP session workflow, authenticated GM mutation capabilities, storage recovery diagnosis, Git write/push boundary at gateway, provider identities `claude-session`, `gpt-session`, `gemini-session`, and routed handoff acceptance. Reuse existing `development/gm_provider/{gateway,store,service,gmctl}.py`; no duplicate gateway and no invented availability/credentials. Cross-provider acceptance is separate from combat balance tests. A separate explicit integration stage may connect the **accepted** combat runtime only after compatibility review.

**Owner**: approves new canonical grants, mastery probabilities, reaction exceptions, expanded telekinesis, combat ruleset opt-in, progression, cinematic resource semantics, paid infrastructure and deployment. Keep each role in separate branches and provide handoff dependencies rather than concurrent edits of common files.

## 9. Required engineering artifacts and gates
**Claude outputs:** existing-code/Registry inventory; source status table for every existing maneuver draft; canonical mapping and error list (including `Power.power_type` mismatch); form/configuration compatibility table; Aero original-vs-candidate grant diff; documented execution-profile schema; playable isolated fixture and card UI; deterministic shared PC/NPC resolver; comprehensive tests; commit SHA and clear owner choices. Prefer end-to-end functionality over an unintegrated dossier.

**GPT outputs (independent):** root-cause/evidence report for `storage_recovery_required`, authenticated write-capable GM tool exposure without giving model sessions raw Git credentials, protected branch/Git CAS tests, real routed GPT→Gemini→Claude acceptance with immutable state and actual model/session attestation, Codespace/mobile browser verification. Never claim a successful handoff before the ledger demonstrates it.

**Protected truths:** No new canonical abilities from a narrative; no silent retroactive migration; no unsafe toggling of a recovery flag; no fictitious rolls; no concurrent independent commits for the same action; no unauthorized PC reaction choice; no spoiler leaks; no automatic skill farming, bonus stacking, infinite counter chains or universal Fear. Changed action costs (Battle Insight, Minor Telekinesis) and provisional Dodge percentages require explicit approval before enabled play.

## 10. Unresolved owner-balanced questions
- Feint check formulation vs guard/Insight, reward when opponent ignores, and available tactical cues.
- Parry baseline resolution vs AC, Dodge risk die coexistence, Riposte trigger ordering and reaction overhead.
- Proficient/Advanced/Master tier thresholds, reactive capacity and Fear radius/resistance.
- Level-1 grants justified by Taron/Echani training without advancing full level.
- Technique/form switching costs and compatibility exceptions by saber/blaster platform.
- Force Point augmentation catalog, cost budget and effects.
- Called Shot wound/disarm/nonlethal rules, creature/anatomy/armor differences.
- Cinematic Momentum evidence rubric, noncombat parity, caps and Spotlight timing.
- SA-001 migration, adoption scope and backward compatibility with canonical run 2.

**Design intent:** Make each turn a legal, expressive, cinematic sequence assembled from real capability; success is earned by character training, sound tactics and accepted resolution—not by a model's persuasive prose.
