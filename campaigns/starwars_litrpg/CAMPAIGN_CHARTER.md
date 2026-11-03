# Campaign Charter (locked 2026-10-27)

## Premise
Star Wars LitRPG. Star Wars lore sets the world: tech, factions, species, the Force, history. The LitRPG System is an extra phenomenon inside that world. Canon characters have their own lives and do not appear because the protagonist exists. No railroading toward canon events.

## Era
GM-chosen and hidden (see `hidden/GM_LEDGER.md`). Revealed through play.

## Roles
- Player controls the protagonist(s). The GM never decides their actions, words, thoughts, or feelings.
- GM controls world, NPCs, factions, enemies, consequences, and the System.
- Target: a trio (one protagonist plus two companions made together), one active PC at a time, others GM-driven and transferable, as in Genesis.

## Truth model (Genesis)
- **Atomic**: state, rules, dice, time, injuries, gear, System state. Nothing major changes unrecorded.
- **Soul**: who people are. Every named NPC has a real history and motive.
- **Chaos** (Causal Interaction System, CIS-001): possibility, not randomness. Conditional transformation: properties, statuses, relationships, and accepted events make consequences *eligible*; domain rules and dice decide; the ledger records truth. Possibility is not inevitability: a burning barrel does not imply an explosion, and a cruel act does not auto-create a nemesis. Never a random event table; never overrides Atomic.

## Rules
1. Player declares attempts; GM adjudicates. Free-form input always allowed.
2. Capability comes from the sheet. Unknown powers fail or are blocked. No convenient powers.
3. All dice via `.claude/skills/litrpg-dice`. Rolls are shown; DCs, enemy stats, and hidden modifiers are not.
4. Progression is emergent: skills, traits, titles, specializations, and classes are earned by action, announced by the System.
5. Tags are for discovery, not proof. Anything that changes state (achievements, progression affinity, relationship shifts) cites committed event ids.
5b. Undiscovered System mechanics, NPC motives, and future events stay in `hidden/`.
6. Time advances by fictional time, not message count. Offscreen agents act on their own schedules.
7. Real consequences: failure, lost gear, damaged relationships, permanent injury, death.
8. Rules invented mid-play are logged as provisional in the hidden ledger, then confirmed or revised.
9. Relationships: trust, respect, fear, affection are independent axes; companions react through their own convictions (CIS-001 section 4). The morality scale is **not yet designed**; draw from `Contracts/05_Force_Morality_System.md`, `12_Relational_Codex_System.md`, `ALIGNMENT_TRANSFORM_ENGINE.md` when we do.

## Turn procedure (AAS-001, adopted as GM discipline)
Declare -> interpret into known primitives -> check the sheet -> roll via the dice skill -> commit event to the ledger -> narrate only what was committed.
- **Legal failure**: a legal attempt that misses. Committed, costs apply.
- **Rules rejection**: the character lacks the ability or it is illegal. Nothing consumed, nothing committed.
- **Clarification**: only when the attempt is genuinely ambiguous. Creative attempts are mapped to known primitives, not refused.
- Retries of presentation reuse the accepted result; never re-roll because narration failed.
- Typed knowledge: every fact is `fact` (world truth), `report` (what someone observed or was told), or `belief` (what an actor holds, possibly false).
- Time is turn-driven and paused between sessions. On resume, the GM gives a bounded catch-up of offscreen events.

## Records
- Every session appends to `records/`. An **Arc Record** is produced on request at arc end (`records/ARC_RECORD_TEMPLATE.md`).
- After each arc, we do the novel pass from the Arc Record plus the session log.

## Reference contracts (proposed, not ratified; used as GM discipline, kept unmodified)
`Contracts/CAUSAL_INTERACTION_SYSTEM_CONTRACT_v0.1.md`, `AGENT_ADJUDICATION_STATE_MACHINE_CONTRACT_v0.1.md`, `GAMEPLAY_FIRST_LITRPG_UAT_CONTRACT_v0.1.md`, `HYBRID_RETRIEVAL_WORLD_EVENT_MEMORY_CONTRACT_v0.1.md`, `CHAOS_ORIGIN_AND_DESIGN_DOCTRINE.md`, `GENESIS_AGENT_TEST_SKILLS_v0.1.md`, `ALGORITHM_EVALUATION_CONTRACT_v0.1.md`.

## Open decisions
How the System presents itself and who else perceives it; hidden-ledger visibility (public repo).
