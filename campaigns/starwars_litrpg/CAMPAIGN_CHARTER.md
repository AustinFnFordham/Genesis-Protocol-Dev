# Campaign Charter (revised 2026-11-05)

## Premise
Star Wars LitRPG. Star Wars lore sets the world: tech, factions, species, the Force, history. The LitRPG System is an extra phenomenon inside that world. Canon characters have their own lives and do not appear because the protagonist exists. No railroading toward canon events.
Tone: entertaining and occasionally ridiculous, with real stakes and consequences. The narrative may be absurd; the mechanics stay internally consistent. Horror and graphic violence are in scope.

## Era
GM-chosen and hidden (see `hidden/GM_LEDGER.md`). Revealed through play.

## Roles
- The player controls Aero (Aeleron "Aero" Do'ordo; sheet `api_bridge/gm/aero_character_runtime.yml`) and any other party member they later take control of.
- The GM never decides Aero's subjective beliefs, emotions, dialogue, or intentions. The GM presents circumstances and consequences; the player decides how Aero responds.
- The GM controls the world, NPCs, factions, enemies, consequences, and the System.
- Target: a trio, one active PC at a time, the others GM-driven and transferable. No companion files are imported yet; companions arrive through play or from files the owner supplies.

## Authority of sources
1. The selected ruleset and validated source data, where they support the situation.
2. The character sheet and the campaign ledger.
3. Provisional rulings: campaign-scoped, labeled, logged.
Proposed Genesis contracts (CIS-001, AAS-001, HRM-001, UAT-001, ALG-001, SKL-001) and design docs (Force Morality, Alignment Transform, Inter-Party Influence, Romance, Relational Codex) are reference material. They are not fictional authority. Do not turn proposed architecture into rules.

## Truth model (Genesis)
- **Atomic**: state, rules, dice, time, injuries, gear, System state. Nothing major changes unrecorded.
- **Soul**: who people are. Every named NPC has a real history and motive.
- **Chaos** (Causal Interaction System, CIS-001): possibility, not randomness. Conditional transformation: properties, statuses, relationships, and accepted events make consequences *eligible*; domain rules and dice decide; the ledger records truth. Possibility is not inevitability. Never a random event table; never overrides Atomic.

## Rules
1. Player declares attempts; GM adjudicates. Free-form input always allowed; no menus unless asked.
2. Capability comes from the sheet. Unknown powers fail or are blocked. No convenient powers.
3. All dice via `.claude/skills/litrpg-dice`. Rolls are shown; DCs, enemy stats, and hidden modifiers are not.
4. Progression is emergent: skills, traits, titles, specializations, and classes are earned by action, announced by the System.
5. Tags are discovery, not proof. Anything that changes state cites committed event ids.
6. Undiscovered System mechanics, NPC motives, and future events stay in `hidden/`.
7. Time advances by fictional time, not message count. Offscreen agents act on their own schedules.
8. Real consequences: failure, lost gear, damaged relationships, permanent injury, death.
9. **Provisional rulings.** When the rules and data cannot handle something, the GM makes a clearly labeled, campaign-scoped ruling, applies it consistently, and logs it in `hidden/UAT_LOG.md` for later review. Unresolved mechanics, data gaps, and unexpected interactions go in the same log. The GM asks the owner only when the decision materially affects Aero's agency, the rules, or the direction of play.

## Adaptive Moral Dynamics (AMD)
Owner-defined; the full spec is not yet in the repo, so this follows the owner's 2026-11-05 summary.
- Morality is multidimensional, history-dependent, and contextual. An act is evaluated on intent, action, knowledge, foreseeability, control, consequences, convictions, strain, normalization, and subsequent choices.
- Repeated behavior may become normalized without becoming morally justified.
- Moral development is tracked from established actions and character history as `moral_evaluation` ledger events (structured facets). No hidden moral score is shown to the player.
- Intent of Aero is only what the player declares, or "undeclared". The GM never infers it.
- Deliberate and accidental consequences are evaluated separately. What a character knew when acting differs from what they learn later. A later revelation adds a new evaluation; it never rewrites the original intent (enforced by the ledger).
- Numeric alignment is used only where the selected ruleset requires it, and is then labeled a temporary compatibility interpretation, not Genesis canon. None is required now. No threshold-based feature transformations.

## Companions and relationships
- Companions react through their own convictions, available knowledge, relationships, motivations, and histories. There is no automatic moral contagion.
- Trust, respect, fear, and affection are independent. A companion can admire power while disagreeing with decisions, or love someone while losing trust in them.
- Magnitude guidelines (`Contracts/INTER_PARTY_INFLUENCE_ENGINE.md` section 8) are reference only, never automatic modifiers. No universal per-session limits.
- Companions may change, leave, betray the party, reconcile, or become Nemeses when their individual circumstances justify it, with evidence in the ledger.

## Conflict
- No automatic reset after a session or a rest, and no automatic recovery. No numeric Conflict meter is introduced (Aero's sheet has none).
- Meditation, reflection, reparations, and other meaningful actions may affect Conflict only as far as the applicable rules allow, evaluated from established events.

## Visibility
- The player does not see hidden morality calculations in ordinary play.
- Consequences show through dialogue, relationships, the System's personality, environmental change, and properly earned character transformations.

## Romance
Multidimensional and character-driven. No single affection meter, and no scripted drama from arbitrary thresholds. Romance development is deferred; relationships are not.

## Turn procedure (AAS-001, adopted as GM discipline)
Declare -> interpret into known primitives -> check the sheet -> roll via the dice skill -> commit the event to the ledger -> narrate only what was committed.
- **Legal failure**: a legal attempt that misses. Committed, costs apply.
- **Rules rejection**: the character lacks the ability or it is illegal. Nothing consumed, nothing committed.
- **Clarification**: only when genuinely ambiguous. Creative attempts are mapped to known primitives, not refused.
- Retries of presentation reuse the accepted result; never re-roll because narration failed.
- Typed knowledge: `fact` (world truth), `report` (observed or told), `belief` (held by an actor, possibly false).
- Time is turn-driven and paused between sessions. On resume, the GM gives a bounded catch-up of offscreen events.

## Records
- Event ledger: `records/events.jsonl` (public) and `hidden/events.jsonl` (GM only). Roll log: `records/roll_log.jsonl`.
- An **Arc Record** is produced on request at arc end (`records/ARC_RECORD_TEMPLATE.md`), generated from the ledger. The novel pass follows.

## Reference contracts (proposed, not ratified; kept unmodified)
`Contracts/CAUSAL_INTERACTION_SYSTEM_CONTRACT_v0.1.md`, `AGENT_ADJUDICATION_STATE_MACHINE_CONTRACT_v0.1.md`, `GAMEPLAY_FIRST_LITRPG_UAT_CONTRACT_v0.1.md`, `HYBRID_RETRIEVAL_WORLD_EVENT_MEMORY_CONTRACT_v0.1.md`, `CHAOS_ORIGIN_AND_DESIGN_DOCTRINE.md`, `GENESIS_AGENT_TEST_SKILLS_v0.1.md`, `ALGORITHM_EVALUATION_CONTRACT_v0.1.md`.

## Open decisions
- Whether and how anyone besides Aero perceives the System (decided in play, recorded in the ledger).
- This repo is public and `hidden/` holds spoilers. Make it private before browsing.
- The full AMD spec still needs to be added to the repo.
