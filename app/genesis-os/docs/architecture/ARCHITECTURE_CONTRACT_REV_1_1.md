# GENESIS UX/UI ARCHITECTURE CONTRACT — REVISION 1.1 (ratified 2026-07-20)
Addendum to UX_UI_ARCHITECTURE_CONTRACT.md (Rev 1.0). Ten clarifications accepted.

## 1. Coherence classification is graded (not binary)
Panels relying on `active_player` rather than an explicit `selected_character_id`
are **campaign-scope: coherent / character-scope: PROVISIONAL**. Applies to
CharacterAnchor, ActionPanel, ShipStations. Campaign-keyed ≠ revision-keyed /
epoch-safe. STATE_SOURCE_INVENTORY.yml updated accordingly.

## 2. Registry is a definition source, NOT a live-state authority
Keep the validated registry for class/subclass/feature/item/power/prereq/
progression-choice/Data-Sifter lookup. Rule:
`registry may ENRICH or RESOLVE a mounted projection by URID; registry may NOT
independently decide what belongs to the mounted campaign.` DNA Record =
`CharacterRuntime.progression + validated registry definitions referenced by URID`.
Implemented: ProjectionBuilder exposes `definitions{urid: doc}` for ONLY the URIDs
the runtime references, excluding sandbox fixtures in live mode.

## 3. state_revision — operational semantics
```yaml
state_revision:
  owner: server
  type: monotonically_increasing_integer
  scope: campaign
  increments_on: [accepted_canonical_mutation, restart, character_added_or_removed,
    visibility_changing_reveal, journal_or_map_mutation, ship_registration]
  does_not_increment_on: [local_tab_change, hover, composer_typing, panel_scroll]
  client_rule: client MUST NEVER invent or increment it
```
Current source: runtime `metadata.runtime_version` (bumped by record_keeper_commit).
TODO: extend increments to character add/remove, reveal, ship registration, map mutation.

## 4. Atomic single-commit
The whole projection commits in ONE Zustand `set({ mounted: {context, projection, status} })`.
No sequential campaign→character→journal→map→ship writes. IMPLEMENTED (store.mountProjection).

## 5. Narrative stream chunk guards (separate from REST)
```yaml
narrative_chunk: {campaign_id, mount_epoch, base_state_revision, turn_id, sequence_number, final}
reject_if: [other_campaign, older_mount, superseded_turn, duplicate_sequence, after_restart]
```
TODO when streaming (SSE) replaces the current POST /gm/turn round-trip.

## 6. Unified projection ≠ unbounded payload
Projection carries `transcript{entries, cursor, has_earlier, latest_sequence}` (paginate old
pages separately). Same for large journal/map. IMPLEMENTED (transcript cursor in ProjectionBuilder).

## 7. Legacy retirement matrix — see LEGACY_RETIREMENT_MATRIX.yml (every path gets a disposition).

## 8. Test vs live mode visibly separate
`runtime_mode: live | test | development` on the projection (env GENESIS_DATA_MODE).
Live REJECTS sandbox_gold entities from campaign membership. IMPLEMENTED
(ProjectionBuilder excludes fixtures in live; provenance.excluded_fixture_count).

## 9. No new cache library this pass
Use existing Zustand + a thin CampaignMountCoordinator (store.mountProjection). Do NOT add
TanStack Query now. IMPLEMENTED.

## 10. Projection provenance
`provenance{campaign_source, character_runtime_source, registry_build_id,
projection_builder_version, excluded_fixture_count, definitions_resolved, hidden_fields_removed}`.
IMPLEMENTED + verified in both-campaign samples.

## Implementation order (A–L) and status
A. ProjectionBuilder + /gm/projection ............ DONE (verified, both campaigns)
B. Atomic Zustand mounted projection ............. DONE (store.mountProjection, one set)
C. Explicit selected_character_id ................ DONE (store.selectedCharacterId + projection field)
C.5 Projection Contract Validation + Semantic Normalization ... DONE, GATE PASS both campaigns.
   Fixed: equipment stringify (structured _norm_item, no dict->name); identity taxonomy
   {species/class/subclass/background:{id,name}} + validate_identity (species-as-class = error,
   unresolved = warning); structured progression block (URID-based); definitions = STATIC only
   (character runtimes excluded; party -> party.characters_by_id summaries); Starship -> starships
   slot + command_record.ship_vessel_id + operative.owned_starship_ids; structured Journal (meaningful
   events, not every utterance) separate from event ledger; fixture_filter evidence (20 known fixtures,
   live_projection_fixture_hits:0); hidden-state seeded-token matrix (0 leaks); schema+semantic
   validation with LIVE FAIL-SAFE (projection_emitted:false blocks commit; client honors it).
   projection_gate (both campaigns): schema_valid semantic_valid malformed_equipment_entries:0
   identity_taxonomy_errors:0 duplicate_character_sources:0 unresolved_required_progression_refs:0
   live_fixture_hits:0 hidden_state_leaks:0 journal_is_structured:true starship_taxonomy_valid:true.
   HONEST DATA GAPS (warnings, not errors): Shadows chars lack class_id/class_name and registry
   can't resolve species_human -> names are NULL (not echoed ids). progression is structurally
   present but EMPTY (no selections authored) -> DNA Record will show honest-empty until authored.
   state_revision still uses runtime_version; broaden coverage (§3 TODO) before Playwright.
D. Re-point DNA Record ........................... PENDING
E. Re-point Map .................................. PENDING
F. Re-point Ship ................................. PENDING
G. Re-point Nemesis (+server visibility filter) .. PENDING
H. Remove scripted Dialogue fallback (live) ...... PENDING
I. Panel containment + scroll ownership .......... PENDING
J. Suggestion grid + composer + auto-follow ...... PENDING
K. Shared design tokens applied .................. tokens authored; not yet applied in JSX
L. Live Playwright acceptance .................... PENDING
