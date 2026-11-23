# Genesis Protocol — Action Composition, Maneuvers, Tactics, and Team Patterns

**ID:** ACP-001  
**Version:** 0.1 owner-direction amendment  
**Date:** 2026-11-22  
**Status:** OWNER INTENT CAPTURED; DATA-CONTRACT PROPOSAL; NOT ADOPTED GAMEPLAY  
**Scope:** docs and noncanonical fixtures only. This amendment grants no action, proficiency, Force effect, budget, learned pattern, or live-campaign authority.

## 0. Why this amendment exists

The current documents and CC-005 sandbox contain useful pieces but do not yet encode the owner's distinctions consistently. In particular:

- `GENESIS_EMERGENT_PLAY_AND_BEHAVIOR_DESIGN_v0.1.md` §5 calls one validated execution/capability a **Maneuver**. The owner instead defines a Maneuver as a composed legal sequence across the action economy.
- `development/combat_slice/catalog.json` uses `maneuver` as a label on individual execution profiles (`Attack`, `Dodge`, `Object`, and similar). That field is taxonomy, not proof that a composed Maneuver exists.
- the current catalog has no legal off-hand blaster attack, off-hand saber attack, generic carried-object Throw, or dual-weapon simultaneous execution profile;
- the only modeled Force augmentation targets `saber_strike` and `riposte`; it does not establish the owner's broader targetable-augmentation design;
- the current catalog and owner-directed categories differ for several capabilities; and
- the earlier UI direction to show blocked/unavailable options can expose categories the actor does not actually have.

This document is additive. It preserves existing rules until a separately approved implementation adopts specific profiles behind a ruleset/campaign gate. Claude's combat branch remains the implementation lane; this docs branch does not edit its resolver, catalog, UI, fixtures, or tests.

## 1. Normative vocabulary

These nouns are different records and MUST NOT be collapsed into one `type`, `maneuver`, or card-category field.

1. **Taxonomy** describes what something is for discovery and grouping: attack, defense, movement, object use, Force, social, setup, and so on. Taxonomy has no cost or entitlement by itself.
2. **Action category** is the budget consumed by one execution profile: Main, Secondary, Bonus, Reaction, Movement, Object Interaction, or Free/Speech. A category does not grant a slot or capability.
3. **Capability** is the stable Registry identity for a learned, innate, item-bound, campaign-scoped, or otherwise authored ability.
4. **Execution profile** is one exact way to execute a capability: costs, timing, targets, prerequisites, hand/equipment state, resource debits, proficiency rule, resolution, usage cap, source, ruleset, and approval.
5. **Grant** answers whether this actor has the capability or execution profile and why. A capability grant, an alternative-profile grant, and a capacity grant remain distinct under SA-001.
6. **Prerequisite/eligibility** answers whether a granted profile can be used now. Held state, ammunition, object presence, range, target, trigger, and remaining budget are not grants.
7. **Maneuver** is a player-authored or authored-template composition of two or more legal execution steps across the action economy, with order/timing, targets, branches, interruption points, and exact combined accounting. It grants no extra capacity.
8. **Tactic** is a reusable conditional pattern that matures from repeated or deliberately combined Maneuver evidence. Promotion creates a learned plan/template identity, not an automatic modifier, proficiency, slot, or new capability.
9. **Team Maneuver** is a coordinated composition whose declared steps belong to two or more independently authorized player characters. Aero, Varon, Rissa, and the Togruta may contribute when each actor is controlled/authorized and each step is legal for that actor. No participant lends a slot, proficiency, resource, or secret knowledge to another.
10. **Team Tactic** is a reusable conditional team pattern promoted from evidence of coordinated Team Maneuvers. It preserves participants/roles, substitutions, consent, timing, observations, communication requirements, contingencies, and per-actor accounting.
11. **Augmentation profile** is an optional, expressly granted resource expenditure targeting named execution profiles and named effect components. Possessing Force Points alone grants no augmentation.
12. **Mastery** is evidence-backed progression or increased competence governed by its own approved graph. Learning a Tactic and mastering a capability are related but not interchangeable.

### Pattern progression

```text
granted capability
  -> legal execution profile(s)
  -> composed Maneuver
  -> repeated/combined conditional evidence
  -> reviewed Tactic candidate
  -> approved learned Tactic

multiple authorized PCs + legal per-actor profiles
  -> Team Maneuver
  -> repeated coordinated evidence
  -> reviewed Team Tactic candidate
  -> approved learned Team Tactic
```

No arrow is automatic. Each promotion records evidence, scope, approval, and the rules version that evaluated it.

## 2. UI availability: do not tease unavailable categories

The category rail MUST be a player-specific projection, never a static enumeration.

- Render a category only when at least one profile in it is granted to the actor and is currently executable or conditionally executable from player-visible state.
- Never render an ungranted capability/profile merely to advertise future content.
- A temporarily blocked but granted profile MAY appear inside an already-visible category when its blocker is actionable and spoiler-safe (for example, reload or draw), with a precise reason.
- A blocked profile MUST NOT keep an otherwise empty category visible.
- Hidden enemy state, unlearned powers, candidate Registry entities, GM-only branches, and profiles from unadopted rulesets do not count toward category availability.
- Direct character-sheet/progression inspection may explain locked future content in that separate context; combat action selection may not.

This narrows the earlier `GENESIS_EMERGENT...` instruction to display unavailable profiles. The newer owner direction controls category projection while retaining honest reasons for owned, temporarily blocked profiles.

## 3. Owner-directed category reconciliation

The table distinguishes observed CC-005 behavior from owner direction. **Owner direction is not implementation authorization.** Every changed category needs an adopted execution profile, grant policy, balance decision, and tests; until then the current profile remains current.

| Capability/profile | Observed CC-005 catalog | Owner-directed category | Reconciliation status |
|---|---|---|---|
| Dodge Action | Main | Main | aligned |
| Battle Insight | Main; Bonus variant behind off-by-default proposal switch | Secondary | missing Secondary profile/source approval |
| Blade Bind & Strip | one Main profile labeled `maneuver: Disarm` | Maneuver | taxonomy conflict; needs composed-step definition |
| Lightsaber Strike (1H) | Main | Main | aligned |
| Echani Strike | Main | Main | aligned; separate off-hand/follow-up profile remains possible |
| Lightsaber Strike (2H) | Main, off hand free | Main | aligned |
| Blaster Pistol Shot | Main | Main | aligned; off-hand follow-up is missing |
| Echani Grapple | Main | Secondary | owner-directed alternative not authored/adopted |
| Calm the Animal (untrained) | Main | Secondary | owner-directed alternative not authored/adopted |
| Reload Blaster | Main | Secondary | owner-directed alternative conflicts with sheet `reload: action`; source/ruleset decision required |
| Burst | Main | Secondary | owner-directed alternative not authored/adopted |
| Force Connection (focused) | Main | Secondary | owner-directed alternative not authored/adopted |
| Minor Telekinesis (Jedi Fundamentals) | Main, campaign-scoped provisional grant | Bonus | owner-directed alternative not authored/adopted; never globalize grant |
| Blade Bind & Takedown | compound Main + Secondary | Maneuver | structurally aligned, but should be stored as a Maneuver template over steps |
| Weapon Feint | Secondary | Secondary | aligned as execution profile; may be a Maneuver step |
| Readied Dodge | Secondary setup + Reaction trigger | Secondary | aligned cost description; composition/trigger must remain explicit |

`Action category` values in data remain Main/Secondary/Bonus/etc. `Maneuver` is a composition record, not another budget category.

## 4. Required execution-profile families

The owner has directed that the model support these possibilities. The exemplar data records them as proposals and explicit source gaps; it does not declare them legal.

### 4.1 Off-hand and dual-weapon attacks

Author distinct profiles for:

- off-hand blaster follow-up after an eligible attack;
- off-hand saber follow-up while wielding two eligible sabers;
- Echani/unarmed follow-up using fist, elbow, knee, or kick as the profile permits; and
- declared saber + blaster or saber + saber dual-weapon sequences.

Each profile MUST state:

- which action category it consumes (the owner proposes Bonus for off-hand attacks);
- whether an earlier Main/Attack step is a trigger;
- which hand/limb and weapon configuration is used;
- separate attack rolls, targets, ammunition, damage rules, and per-hit effects;
- whether ability modifiers apply to off-hand damage;
- exact proficiency predicates and the source that defines them;
- what happens when the actor lacks the required proficiency; and
- interaction with draw/holster, two-handed grip, grapple, reload, reactions, Force augmentation, advantage/disadvantage, and usage limits.

The owner's current penalty proposal is **disadvantage when the actor lacks the appropriate proficiency**. Record it as a candidate rule until the relevant proficiency identities and ruleset approval are resolved. Do not silently infer that weapon proficiency, dual-wield training, off-hand training, or a fighting style are the same predicate.

"Simultaneous" is presentation/timing, not free accounting. A simultaneous dual-weapon declaration still names every consumed slot/resource, creates separate attack/effect records unless an adopted source says otherwise, and is interruptible/revalidated at defined boundaries. It cannot compress Main + Bonus into one free Main.

### 4.2 Carried-object Throw

Throw MUST resolve the actual carried/held object instance (for example a lantern), hand, weight/size, target, range, purpose, fragility, recoverability, and environment. Separate:

- ordinary transfer/drop with no hostile effect;
- improvised hostile/damaging Throw;
- distraction/utility Throw;
- trained Quick Throw or other alternative activation; and
- telekinetic movement, which is not ordinary Throw.

The current CC-005 catalog has no generic carried-object Throw. CC-002 text proposes Main for hostile damaging throws and requires an explicit profile for Bonus/Secondary variants. Appropriate improvised/thrown proficiency and the owner's candidate disadvantage rule remain source gaps.

### 4.3 Force Point augmentation

Many abilities MAY be designed with Force Point augmentation, but none gains it merely because the actor has Force Points. Every augmentation record MUST include:

- stable augmentation ID and source/approval;
- exact target execution-profile IDs, not a broad string/category match;
- exact target component (attack roll, damage, range, targets, duration, control, defense, or another authored field);
- timing and whether selection happens before/after a roll;
- cost, pool, minimum balance, cap, recharge, and shared usage limit;
- stacking/replacement rules and interaction with advantage/disadvantage;
- actor grant/prerequisites and campaign/ruleset scope; and
- public explanation without revealing hidden state.

The current `force_augment` sandbox proposal is evidence for one narrow profile: 1 FP, once per turn, +1d4 to the attack roll of `saber_strike` or `riposte`. It does not authorize any other ability. Broader targets must be separately authored and approved.

## 5. Maneuver and Tactic records

A Maneuver stores ordered step references rather than copying capability rules. At preflight and again at every interrupt boundary, Atomic resolves the current version of each referenced execution profile, verifies the actor's grant, prerequisites, target, costs, and remaining resources, and escrows/commits according to the existing turn transaction rules.

Required Maneuver fields include:

- stable ID/version, scope/status/source/approval;
- ordered steps with actor, execution profile, target binding, timing group, and condition;
- aggregate budget/resource forecast partitioned by actor;
- interruption/revalidation/fallback rules;
- declared objective and optional player-authored name/signature; and
- no embedded unapproved modifier.

A Tactic additionally stores conditional branches, evidence references, promotion decision, learned/granted actors, substitutions, counter-observation boundaries, and a new live-state validation result for every use. Repetition can nominate a candidate; it never bypasses review.

## 6. Team pattern safeguards

- Each PC declaration requires the controlling player's authorization; one player's template cannot silently spend another PC's turn.
- Team patterns are schedules over independent turns/reactions, not a pooled super-turn.
- Every participant keeps separate grants, budgets, Force Points, ammunition, reactions, status, and receipts.
- Communication/visibility/range/timing requirements are explicit. A team member cannot act on private information they did not perceive or receive.
- A participant becoming unavailable triggers an authored fallback or pauses/refuses the remaining plan; it does not transfer their step to another PC.
- Team Tactic learning may bind named participants (Aero, Varon, Rissa, the Togruta) or approved role slots. A role substitution needs compatibility rules and consent.
- NPC observation/counter-learning is limited to what the NPC actually perceived, consistent with `GENESIS_EMERGENT...`.

## 7. Source gaps and decisions still required

These are not resolved by existing documentation:

1. Exact source/ruleset for off-hand Bonus attacks, dual-wield prerequisites, ability-modifier damage, and nonproficiency disadvantage.
2. Exact ordinary/improvised Throw rules for object size, range, damage, proficiency, breakage, and object interaction.
3. Whether the owner-directed Secondary/Bonus alternatives replace or supplement current Main profiles, and under which ruleset/campaign gate.
4. Whether Blade Bind & Strip is decomposed into existing/legal steps or remains one contest wrapped by a Maneuver template.
5. Evidence thresholds, diversity requirements, naming/approval, forgetting/respec, and mechanical benefits (if any) for Tactic/Team Tactic promotion.
6. Team control/consent model when one human controls multiple PCs versus multiple human players.
7. Which additional abilities receive Force augmentation, which components may change, and their exact cost/caps.
8. How current `catalog.json`'s overloaded `maneuver` field migrates without breaking CC-005 readers.

Until resolved, data MUST say `proposed`/`source_gap`; UI MUST not present it as granted or legal.

## 8. Data artifacts and compatibility

- Schema: `Contracts/schemas/action-execution-pattern.schema.json`
- Noncanonical owner-intent/source-gap exemplars: `Contracts/examples/action-execution-patterns.v0.1.json`
- Coverage checks: `Contracts/tests/test_action_execution_patterns.cjs`

The schema is an additive authoring contract. It is not a migration of `development/combat_slice/catalog.json`. Existing CC-005 behavior and receipts keep their pinned rules version. A future implementation may add a projection adapter after owner approval; it must not rename current fields in place or infer adoption from these examples.

## 9. Adoption gates

Before any profile or pattern becomes gameplay:

1. resolve source and Registry IDs;
2. record owner/rules authority approval and campaign/ruleset scope;
3. decide exact proficiency, cost, timing, resolution, caps, and stacking;
4. add Atomic validation and deterministic receipt/replay tests;
5. add negative tests for missing grant, missing proficiency, spent slot, wrong hand state, no object/ammo/FP, interruption, duplicate trigger, unconsented teammate, and hidden data;
6. verify UI hides ungranted/empty categories and does not retain a category solely for blocked profiles;
7. verify PC/NPC parity where the same profile is actually granted;
8. run isolated playtests and balance review; and
9. obtain a separate adoption decision. No docs merge alone enables gameplay.

## 10. Audited refs

Audit refreshed from GitHub remote `dev` on 2026-11-22. Evidence reviewed:

- `docs/gep002-owner-design-20261122` at `662cae3` (this branch's base; contains CC-005/CC-005b ancestry and GEP-002 amendments);
- `dev/cc005-server-verify` at `16b4750` (newer thin-client/server verification; no catalog changes relative to the docs base);
- `dev/cc004-combat-v04` at `2455ab7`, `dev/cc003-tactical-composer` at `01f9061`, and `dev/cc002-combat-slice` at `f514617`;
- `docs/emergent-play-design-v01-20261122` at `4749ae0` and its integrated counterpart `31c332e`;
- `docs/cinematic-combat-capability-v0.2-20261121` at `329f05a`, including CC-002 v0.2, Character Capability & Mastery v0.1, and SA-001 v0.1;
- `Contracts/GENESIS_EMERGENT_PLAY_AND_BEHAVIOR_DESIGN_v0.1.md`, GEP-002 owner-direction amendments, `development/combat_slice/GEP002_PREP.md`, and `development/combat_slice/catalog.json`.

No Oracle deployment, live campaign mutation, Hask Meadow change, `shared-0002` claim, or dice operation was performed for this amendment.
