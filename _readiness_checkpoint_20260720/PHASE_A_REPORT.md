# GENESIS PROTOCOL — PHASE A COMPLETION REPORT (2026-07-20)
Deterministic app/UI repairs. No Phase B migration, no LLM enrichment, no broad promotion, no Phase C creator, no Campaign Genesis.

## 1. Exact files changed
SERVER:
- api_bridge/gm_controllers.py — opening persistence (generated-once cache), restart_campaign_from_opening (backup-before-clear), item taxonomy: classify_item / route_equipment / validate_item_slots, Shadows equipment projection routed by item_type.
- api_bridge/server.py — POST /api/v1/gm/restart, GET /api/v1/gm/item_check.
CLIENT (app/genesis-os/src):
- state/store.js — campaign-switch now replaces ALL projections; journal = per-campaign chronicle projection (hydrateJournalFromChronicle); opening (loadOpening); restartCampaign; addCharacter flow.
- components/CampaignSelect.jsx — removed leaky shadows special-case + premature gmCampaign set.
- components/DialogueSystem.jsx — persisted opening crawl rendered as a distinct block (not injected into transcript).
- components/CommandPanel.jsx — structured chronicle journal (location/participants), 'event' style, Add Character + Restart-from-Opening controls.
- components/ActionPanel.jsx — item-type UI slots (weapons filtered to item_type==Weapon; armor/gear/vehicles slots; defensive client classifier).
- components/AddCharacter.jsx — NEW: role picker + campaign association + party-state interface contract (Phase C route marked unfinished).
- App.jsx — AddCharacter overlay mounted.

## 2. State-flow (before -> after)
BEFORE: campaign switch -> gmFeed rehydrated per-campaign (ok) BUT `journal` global array never cleared + shadows-only loadCampaignFromEntity -> Aero journal bled into Shadows.
AFTER: switch -> refreshGmRuntime detects mount change -> clears {journal, opening, dice, reaction, draft, patchLog} -> hydrateSession(transcript) + hydrateJournalFromChronicle(chronicle) + loadOpening(crawl). Every panel is a projection of the newly-mounted campaign's server-owned records.

## 3. Campaign storage paths
api_bridge/gm/campaigns/<campaign_id>/ : runtime_state.json (session), transcript_archive.jsonl (append-only canonical transcript), chronicle.jsonl (structured journal), turn_log.jsonl (provenance), opening.md (authored crawl) | opening.generated.json (persisted crawl).
Backups: api_bridge/gm/_restart_backups/<cid>_<stamp>/.

## 4. Chronicle & transcript API contracts
- GET /api/v1/gm/transcript?offset&limit -> {entries:[{entry_id,type,speaker_id,text,narration,mood,scene_id,...}], total, canonical_retention:"campaign_lifetime", projection_window:200}. Append-only, campaign lifetime.
- GET /api/v1/gm/chronicle?n -> {entries:[{event_id,timestamp,objective_event,participants,location,source_resolution,fact_class}]}. Structured record — NOT a transcript copy.
- Client Journal maps chronicle -> {t,kind(event|combat),text,location,participants,eventId}. Transcript drives center Narrative; chronicle drives right Journal.

## 5. Opening-crawl source & persistence
get_opening() priority: authored opening.md (gold) -> persisted opening.generated.json (source="persisted") -> generate once under OPENING_SYSTEM, hidden-leak-screen, PERSIST to opening.generated.json. Belongs to campaign_id, stable across ordinary mounts, replays on restart. force_regenerate only via restart. Rendered as a distinct crawl block in the center panel, dismissible with the action_window.

## 6. Restart migration & backup
POST /api/v1/gm/restart {campaign_id, confirm:true}. Requires explicit confirm (UI window.confirm). BEFORE reset: whole campaign dir snapshotted to _restart_backups/ (session files MOVED, opening/foundation/character defs COPIED — nothing destroyed). Rebuilds fresh session from builder. Returns {backup_dir, cleared[], retained[], opening_preserved}. CLEARED: runtime/transcript/chronicle/turnlog. RETAINED: opening crawl, campaign foundation, character definitions.

## 7. State-layer isolation test — PASS
05_campaign_isolation_test.json: 5-step Meridian<->Shadows switch, word-boundary matching (Ilo != pilot), zero foreign leaks, correct cast, hidden_gm_state excluded.

## 8. Browser/UI isolation test — tokenized round-trip PASS (state+server layer); live screenshots NOT captured this session
06_phase_a_tests.json roundtrip: unique tokens appended to each campaign's transcript+chronicle; Meridian sees TOKEN_MERIDIAN not TOKEN_SHADOWS; Shadows sees TOKEN_SHADOWS not TOKEN_MERIDIAN; return to Meridian sees its token, not Shadows'. Exact-identifier matching (no substring).
NOTE: rendered-panel screenshots require the dev server + api_bridge + Ollama (GM turns) running with Chrome driving — not launched in this headless session. The panel-replacement behavior is proven at the state/server layer; a Playwright e2e can capture pixels once the stack is up.

## 9. Application-restart persistence — PASS
Per-campaign files persist on disk; both campaigns restore independently by mount. Restart test confirms fresh session + preserved crawl + backup retention (token gone from live transcript, present in backup).

## 10. Hidden-state exclusion — PASS
player_visible_state strips hidden_gm_state; verified absent from visible state AND transcript serialization. (Extends to the future varon_hidden_gm_ledger.yml — a reveal event must copy an approved fact into visible knowledge; the ledger is never read directly by player-facing surfaces.)

## 11. Item taxonomy — schema/validator/projection/UI
- item_type authority = Item.schema enum [Weapon,Armor,Gear,Consumable,Artifact,Droid_Part,Starship_Component,Trade_Good,Other] (+Starship for whole vessels).
- classify_item(): item_type wins; deterministic name heuristics fallback; apparel WITHOUT armor mechanics = Gear (not Armor).
- validate_item_slots(): deterministic failures for non-weapon-in-weapon-slot, non-armor-in-armor-slot, starship-in-carried-slot.
- route_equipment(): projection routes by type; weapons[] receives ONLY item_type==Weapon.
- UI ActionPanel: defensive client classifier; weapons filtered to Weapon; armor/gear/vehicles rendered in their own slots.
- SCHEMA-EMBEDDED if/then constraint on a CharacterRuntime sheet: enforced via the deterministic validator (validate_item_slots) rather than JSON-Schema if/then; a CharacterRuntime schema in Phase C can embed it natively.

## 12. Corrected UI classification evidence (06_phase_a_tests.json)
classify: YT-2400 light freighter->Starship, Flight jacket->Gear, Lucky sabacc chip->Trade_Good, DL-44 blaster->Weapon, Beskar chestplate->Armor.
route_equipment(["YT-2400 freighter","Flight jacket","Lucky sabacc chip","DL-44 blaster"]) -> weapons:[DL-44 blaster], gear:[Flight jacket, Lucky sabacc chip], vehicles:[YT-2400 freighter], armor:[].
validate_item_slots(all-in-weapons bad sheet) -> 4 violations (freighter x2: non-weapon + starship-in-carried; jacket; chip); real blaster NOT flagged.

## 13. Add Character route & state contract
Entry point: Command&Record Journal -> "+ Add Character" -> role picker overlay (primary_player_character | secondary_player_controlled_character | companion | temporary_party_member | imported_character) -> campaign association shown. Phase A establishes route only; NO character written. Documented completion contract: POST /api/v1/gm/party/add {campaign_id, role, character_runtime} -> participant registry + turn/round + party + narrative/journal/relationship/event systems. Phase C route explicitly marked unfinished in-UI.

## 14. Turn/round/action-model status
PRESENT (canonical runtime): combat block {active, round, turn, initiative, positions, tokens, effects}; metadata.active_player (active participant); seeded DiceService per turn.
MISSING (documented, carried to Phase C as a blocker for full playability): out-of-combat participant registry, action_owner, actions_remaining/reactions_remaining, out_of_combat_action_state, encounter_state as a first-class model. Add Character's party-state contract (13) will register participants into this model once built. NO second action model was invented in the client.

## 15. Build & test outputs
- vite build: PASS (852 modules, built clean) x2.
- 05_campaign_isolation_test.json: PASS. 06_phase_a_tests.json: PHASE_A_TESTS_PASS=true (item_classify, item_enforcement, opening_stable, opening_authored_stable, roundtrip, restart, hidden all true).

## 16. Confirmation
No Phase B migration ran (data untouched; factions restored pristine earlier). No LLM enrichment. No gold promotions (fac_black_sun remained provisional/unmoved). No Phase C Character Creator implemented (route only). No Campaign Genesis work. Readiness-gate data decisions still pending Austin.
