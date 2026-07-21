# PHASE TWO — THE SOUL SYSTEMS (2026-07-18)

Phase One built the law. Phase Two gives it a soul — implemented **directly from the intent library at `SW5e_Data_Hub/docs/systems/`** (the systems docs and the engines are one architecture; the docs are the spec, the engines are the enforcement).

## Shipped

### GEN-REL-001 — Inter-Party Influence Engine (`src/state/influence.js`)
`docs/systems/INTER_PARTY_INFLUENCE_ENGINE.md`, implemented deterministically. A tagged action ripples through the party: the actor's `alignment_tracking.alignment_score` (0 Dark … 100 Light) shifts by full magnitude; every other party member and companion makes a **seeded** Wisdom resistance check (DC 10 + magnitude + actor CHA mod, exactly per spec); failures drift magnitude/2 toward the influencing alignment. Every roll is ledgered in envelope diagnostics — the AI GM narrates the ripple, it never decides it. Alignment reads are tolerant of all three legacy shapes (`alignment_tracking`, `ffg_morality`, `moral_compass`).

**Live QA:** Kass Zoran commits a dark act (magnitude 7, DC 16) → Kass 80→73; Aran Voss rolls 15+1=16 — resists by exactly 1; Tala Ren nat-20 resists; the nexu and Malice fail and drift 4 dark. Narrative feedback lands in the journal per the spec's voice.

### Alignment Transform Engine (`src/state/alignmentTransform.js`)
`docs/systems/ALIGNMENT_TRANSFORM_ENGINE.md`: on band crossings (dark ≤30 / neutral / light ≥70) the engine scans owned features for `corruption_transform` data and swaps mirrored light/dark variants (`corrupts_to_feature_id` / `purifies_to_feature_id`), honoring `retains_mastery`, emitting `feature_corrupted`/`feature_purified` envelopes with the `ui_transition` hint in diagnostics for Revelation to animate. Pure data — the engine knows no specific feature. Redemption and fall arcs without respecing.

### Romance & Relationship System (`src/state/romance.js`)
`docs/systems/ROMANCE_RELATIONSHIP_SYSTEM.md` levels 1+2: the player carries a `romance_relationships` registry keyed by companion; thresholds 0/25/50/75/100 → Friendship → Close Friendship → Romantic Interest → Dating → Committed. Companion-side `romance_potential` gates accrual. History rides with the points (last 20 beats) so the AI GM can narrate memory. New `romance_gesture` intent; `scene_action` now carries optional `influence` and `romance` payloads.

**Live QA:** Voss + Malice: +30 → Close Friendship (level-up event), +25 → Romantic Interest, history intact.

### GEN-TEST-001 — The test campaign is playable
`store.loadCampaignFromEntity()` instantiates **"Shadows of Empire: Remnants"** from its CampaignState entity with **referential integrity as a hard gate** (missing party members abort the load — no phantom can ever board again). The Reconciliators (Voss / Ren / Zoran, the AI-forged entities from Phase One) load as the live party with session context. Deterministic seed derived from campaign_id: `378539591`, every run. `▶ LOAD TEST CAMPAIGN` button on the creator screen.

### GEN-TEST-002 — Determinism replay harness
Boot snapshot + `replayCheck()`: re-applies every accepted campaign-target envelope from the ledger onto the snapshot and compares with live state. `campaign.characters` is correctly treated as a derived save-sync slice (entity envelopes own that truth). **Live QA: 5 events replayed, exact reproduction.** Same seed + same intents ⇒ same galaxy.

### Dialogue wired for consequence
The Malice scene now carries moral physics: LOYAL = dark m3 · DEFIANT = neutral m3 + romance +5 · PROTECTIVE = light m4; Slicer Override adjudicator tags violence dark m6, kneeling dark m2, the detonator gambit dark m4 + romance +6, holocron-smashing neutral m3 + romance +4. Every wheel click can now tilt the whole party's souls — and Malice remembers who bared their teeth at her.

## Authority matrix additions
`relationship_engine` += `/alignment_tracking`, `/romance_relationships` on entities. No other grants. Build green (4.0s), zero unexpected console errors.

## Found & fixed
- Replay initially diverged: entity-driven `characters` sync isn't campaign-enveloped — comparison now correctly scopes to campaign-authoritative state.
- Malice's manifest name is "Sith Assassin" (`companion_sith_assassin`) — name-based lookups need the fallback (DialogueSystem already had it).

## Next (Phase Three seeds, from the systems library)
- **Starship careers** (`STARSHIP_CAREERS_SYSTEM.md` + `skill_tree_system.yml`): dual progression, 5 tiers, career synergies — natural extension of `ship_op`/`advance_character`.
- **Species progression / cultural features / environmental adaptations** (`ADVANCED_SYSTEMS_IMPLEMENTATION_GUIDE.md`): level-tier scaling as Feature data through the forge.
- **Adversary→Companion conversion** (`ADVERSARY_TO_COMPANION_CONVERSION_GUIDE.md`): defeat + influence + alignment compatibility → recruitment resolver (Kaelen could be turned).
- Mirrored `corruption_transform` Feature pairs authored through the AI pipeline so the Transform engine has real gold data to swap.
- Romance level 3 (campaign-level dynamics: jealousy, party cohesion) once multiple companions are in play.
