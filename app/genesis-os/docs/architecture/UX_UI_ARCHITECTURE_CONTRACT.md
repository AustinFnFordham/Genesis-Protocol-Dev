# GENESIS PROTOCOL — UX/UI ARCHITECTURE & STATE MANAGEMENT CONTRACT
Revision: 1.0 (2026-07-20). Status: RATIFICATION DRAFT. Phase A = GATE_FAIL.

## 0. The non-negotiable rule
> **One server-owned campaign state, one atomically mounted client projection,
> and many contained UI views of that same projection.**

No panel may display data belonging to another campaign, character, revision,
mount epoch, or visibility scope, or to a QA fixture. When valid data is
unavailable, render an explicit empty / loading / error state — never a fixture.

## 1. Why this contract exists (grounded findings)
The live app currently runs TWO competing data sources (see
`STATE_SOURCE_INVENTORY.yml`):
- **A) Mounted projection** — `gmRuntime` via `GET /gm/state` (per-campaign, coherent).
  Consumed by: CharacterAnchor/Operative, ActionPanel, CommandPanel Journal, ShipStations.
- **B) Boot registry** — `loadRegistry()` → 41 sandbox fixtures + manifest (campaign-blind).
  Consumed by: **ProgressionTree/DNA Record, GalacticMap, ShipManagement (Ship tab), NemesisWeb**,
  and DialogueSystem's scripted Malice fallback.

Every observed defect (DNA Record shows Aran/Guardian/Sandbox while Operative shows
Aero; Map shows Coruscant/Mustafar; Ship shows Millennium Falcon; Nemesis shows Aran)
is a source-(B) panel ignoring the mounted campaign. The fix is architectural: all
panels consume ONE projection; source (B) is removed from live character/campaign views.

## 2. Layered architecture
```
Canonical server state (gm_controllers + validated entities)
  -> FastAPI domain layer (CampaignService, CharacterService, RulesService,
     RegistryService, NarrativeService, VisibilityService, ProjectionBuilder)
  -> API/stream layer (REST + SSE), every response tagged {campaign_id, mount_epoch, state_revision}
  -> React client (server-state cache + CampaignMountCoordinator + one shared UI store)
  -> Container components (Operative / ActiveEngagement / CommandRecord / Modal)
  -> Presentational components (props in, events out; NO fetch, NO fixture, NO mutation)
```

## 3. State ownership (three categories)
- **Server state** — persistent game truth (campaigns, characters, party, rounds/turns,
  scenes, transcripts, journals, ledgers, objectives, maps, ships, equipment,
  relationships, player-visible nemesis, hidden GM ledgers, table rulings, opening crawls).
- **Global client state** — mounted context + shared UI behavior ONLY: `{mounted_campaign:
  {campaign_id, mount_epoch, state_revision, status}, selected_character:{character_id},
  active_tabs, narrative_ui:{is_near_bottom, unread_count, opening_crawl_expanded},
  modal_state, request_state}`.
- **Local component state** — transient visual only (hover, focus, dropdown, unsent draft,
  selected-suggestion, animation, resize, local scroll). May NOT own campaign/character/
  inventory/journal/transcript/ship/map/relationship/progression truth.

Genesis uses **zustand** (`useGenesis`) as the single shared UI store — do NOT add Redux
alongside it. Server data should move behind a query/cache layer (TanStack Query or a
thin projection fetcher); today it is fetched ad hoc per component (the defect).

## 4. The mounted projection
Server returns ONE envelope per mount (`MOUNTED_PROJECTION.schema.json`): `{campaign_id,
mount_epoch, state_revision, selected_character_id, campaign, operative{character_runtime,
available_actions,...}, party, active_engagement{opening_crawl, active_scene, transcript,
suggestions, objectives}, command_record{journal, map, player_visible_nemesis, ship},
visibility{hidden_fields_removed:true}, provenance}`. Every panel selects from THIS.

## 5. Atomic mount + stale-response discard
```
select campaign -> increment mount_epoch -> status=MOUNTING -> request projection
  -> server builds coherent, visibility-filtered projection
  -> client applies ONLY if response.campaign_id == current AND response.mount_epoch == current
  -> atomic commit; all panels render one revision
Header must NOT change to Meridian while Map/Journal/Ship/Nemesis finish Shadows requests.
```
Phase A added `mount_epoch` + client stale-guards on gm/state, chronicle, opening; the
remaining work extends this to a single projection endpoint and every panel.

## 6. Canonical Character Runtime
One source (`CHARACTER_RUNTIME.schema.json`) drives Operative, attributes, equipment, DNA
Record, powers, relationships, portrait, participant registration, Add Character result.
`selected_character_context = {campaign_id, character_id, runtime_revision}`. DNA Record
receives `character_id` explicitly and renders `runtime.progression + validated class/subclass
defs + prereq-filtered registry choices` — registry provides DEFINITIONS, runtime provides
selected/unlocked/pending/locked + campaign rulings. Never Guardian for Aero; never Sandbox Entity.

Source normalization happens at ONE server boundary (`gm_controllers.player_visible_state` +
`normalize_equipment` + `_clean` de-escape — added Phase A). The Aero sheet's dict-armor and
`\x27` names are normalized there, not guessed in components.

## 7. Container containment
```
GenesisAppShell
├── OperativeContainer      (fixed: header, portrait/identity, core stats, Available Actions;
│                            tab bodies scroll: Weapons | Gear&Trinkets | Powers | Conditions)
├── ActiveEngagementContainer (scroll transcript viewport + collapsed crawl + NewMessages;
│                            constrained 2x2 suggestion grid; sticky composer)
├── CommandRecordContainer  (fixed: header, tabs, tab-actions Add Character/Restart;
│                            scroll body: Journal | Dice | Map | Nemesis | Ship)
└── ModalLayer              (DNARecord, AddCharacter, RestartConfirmation)
```
Presentational components: props in, events out. No fetch, no fixture fallback, no mutation.

## 8. Lifecycle states (every data container)
`uninitialized -> loading -> success -> empty -> stale -> error -> blocked`, driven by
`[data-state]` + the token layer (`design-tokens.css`, `component-tokens.css`). Empty states
are honest ("No ship is registered to this campaign."); `blocked` never reveals hidden existence.

## 9. Test instrumentation (mandatory)
Every visible region exposes `data-campaign-id`, `data-mount-epoch`, `data-state-revision`;
character regions also `data-character-id`. Live acceptance in `LIVE_UI_ACCEPTANCE_TESTS.md`.

## 10. Scope of this pass (in / out)
IN: state inventory; remove competing campaign source (B) from live views; one mounted
projection; normalized character/campaign; shell container refactor; lifecycle states;
shared tokens; binding metadata; remove sandbox fallbacks; UML/sequence docs; Playwright
live tests; responsive typography + scroll ownership.
OUT (this pass): Campaign Genesis, Chronology, LLM enrichment, broad schema migration, new
mechanics, full conversational Character Creator.

## 11. Handover artifacts (this directory)
STATE_SOURCE_INVENTORY.yml · COMPONENT_DATA_MAPPING.yml · MOUNTED_PROJECTION.schema.json ·
CHARACTER_RUNTIME.schema.json · CAMPAIGN_STATE_MACHINE.puml · NARRATIVE_STATE_MACHINE.puml ·
CAMPAIGN_SWITCH_SEQUENCE.puml · PLAYER_ACTION_SEQUENCE.puml · ../../src/styles/design-tokens.css ·
../../src/styles/component-tokens.css · LIVE_UI_ACCEPTANCE_TESTS.md · this contract.

## 12. Verification ledger (required at the end of every implementation message)
Fields: scope, architecture_contract_revision, files_changed, static_build, unit_tests,
integration_tests, live_runtime_started, rendered_ui_test, campaign_switch_test,
character_switch_test, persistence_restart_test, console_errors, error_boundary_activations,
stale_responses_discarded, cross_campaign_leaks, cross_character_leaks,
fixture_fallbacks_detected, screenshots_or_traces, known_failures, untested_requirements,
gate_status ∈ {IMPLEMENTED_UNVERIFIED, HEADLESS_VERIFIED, INTEGRATION_VERIFIED,
LIVE_UI_VERIFIED, GATE_PASS, GATE_FAIL}.
