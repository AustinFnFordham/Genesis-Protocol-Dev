# NARRATIVE TRUTH GATE (2026-07-19)

Your shuttle QA transcript drove this pass. All work preserved; the gate now stands between the model and the fiction.

## Root causes found
1. **My seed data was wrong**: I had invented "Chief Engineer Nona" from the hidden ledger's festival line. Corrected cast: Dax Ferren (pilot), operatives **Senn Varga / Ilo Reeth / Maza Ketrel** (the unfamiliar team), **Besk Ollor** chief of six engineers. Nona Ladiern restored to canon as the Harvest Festival's namesake — not aboard.
2. **No canon lookup existed** — the GM improvised lore into the vacuum.
3. **Rules validation was prompt-level** — the CM rationalized telekinesis as "Force Connection."

## Implemented
- **Lookup**: per-campaign `canon` block (facts + prohibitions: Walking Cloaks, festival truth, Force Connection's information_boundary, travel state) injected as AUTHORITATIVE_CANON_LOOKUP — law in the prompt, screened in code.
- **Rules Lawyer (deterministic code)**: `power_effect_requires_exact_feature_validation` — a power_use declaration must name a power the sheet contains, or it is ILLEGAL before any model sees it. `noncombat_does_not_mean_nonmechanical`: Force-assisted object actions classify as power_use.
- **Character Keeper**: `dialogue_memory` (last 24 lines) persisted in runtime, fed to the GM, enforced by the steward — repeated lines and repeated suggested questions are violations.
- **Steward hard checks (code)**: `gm_may_not_speak_for_active_player` (voiced player beats blocked), `npc_identity_collision_blocks_turn` (unknown speakers blocked), repetition repair, hidden-leak screen, option dedup. Cast completeness rides the canon facts + opening contract.
- **Record Keeper**: fact_class provenance unchanged.

## Campaign opening contract
`GET /api/v1/gm/opening` — authored `opening.md` in the campaign dir is gold and served verbatim (**your Meridian text is now that file**, plus a scene-entry coda placing the full cast); otherwise the GM generates under the three-movement contract (chronicle inheritance → character inheritance → mission through story) with prohibitions enforced. The client renders the exposition as narrator beats before any action window; the runtime metadata line is demoted to a small SYSTEM summary after.

## Spoken-line dialogue contract
GM options are now `{spoken_line, intent:{topic,goal,tone}}` — natural lines ("Chief Besk, do you have any concerns about the reactivation process?"), never command summaries. The client displays and declares the spoken line; intent rides as metadata. Custom response always available.

## Regression (rerun of your shuttle scenario)
- "I float a ration pack with the Force" → **power_use → Rules Lawyer: ILLEGAL (Known powers: Battle Insight, Burst) → GM narrates: "The ration pack… doesn't move."** The transcript bug is dead — and it was killed by code, not by prompt.
- Options returned as natural spoken lines addressed to the real cast (Besk, Senn, Ilo). Zero steward violations, zero player-voiced beats.
- Opening serves `source: authored`, beginning "The Meridian Reach had learned long ago not to wait for rescue."

## Next (per your order, now unblocked)
Tactical token truth-path + Ship crew resolution → reaction-window UI → Combat Master → Diorama → full tactical escalation. Shadows of Empire needs the same canon-block treatment (its cast is thinner; the AI pipeline can author its canon facts from the CampaignState entity).
