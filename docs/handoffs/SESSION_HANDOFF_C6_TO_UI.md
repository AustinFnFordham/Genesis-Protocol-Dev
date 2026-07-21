# SESSION HANDOFF — C.6 → UI (D–L)
Generated 2026-07-21. Status: Phase A GATE_FAIL. C.6 reclassified FAIL (see below).

## Source control
- **branch:** none — `E:\StarWars` is NOT a git repository (verified `no .git`).
- **latest commit hash:** n/a. RECOMMEND: `git init` + `.gitignore` (exclude `**/.venv`, `node_modules`, `**/__pycache__`, `_readiness_checkpoint_*`, `api_bridge/_*.py` temp scripts, `**/*.bak.json`, `logs/`, `dist/`, `.forge_runs`) before further large changes.
- **durable checkpoint (this session):** named directory `E:\StarWars\_readiness_checkpoint_20260720\` + `registry\golden_slice\` lane + runtime backups. This document is the index.

## C.6 status (reclassified — corrected)
```yaml
c6_status:
  reference_presence_coverage: pass      # every required slot points to some record (COMB registry)
  cardinality_infrastructure: pass       # indexes + 303 edges + synergy (no auto-unlock)
  migration_fidelity: fail               # quantities/equipped/transcript/opening_status LOST in migration
  semantic_resolution: fail              # species_human!=Human, bg_smuggler double-prefix, class_operator wrong source, Tala/Kass unresolved, Sentry dropped, vessel id disagreement
  live_registry_integration: fail        # server.build_registry does NOT load registry/golden_slice/; 100% was COMB-only
  overall_c6_gate: fail
```

## What was done this session (and REVERTED)
- Built `registry/golden_slice/` lane (45 records: 15 exact_validated, 24 authored-STUB residuals, 3 relationship_edge, 2 character_instance, 1 campaign_local). LANE KEPT.
- Migrated both runtimes to URID refs — **caused data-loss regressions** (below) — then **ROLLED BACK** to pre-migration backups (hash-verified). Live runtimes are now the clean pre-migration (C.5-good) state.

## Exact files changed (this session, still in place)
- `api_bridge/projection.py` — reference-integrity measure, asset_relationships (URID), monotonic revision via `_bump_revision`, structured normalization, validation + fail-safe.
- `api_bridge/gm_controllers.py` — `_bump_revision`/`revision.json` lineage, `route_equipment` structured + starships slot, `normalize_equipment`, `player_visible_state` de-escape + normalize boundary, shadows identity taxonomy, `get_opening` persistence, `restart_campaign_from_opening`, item taxonomy (`classify_item`/`validate_item_slots`).
- `api_bridge/server.py` — GET `/api/v1/gm/projection` (+runtime_mode), `/gm/restart`, `/gm/item_check`, campaign_id/mount_epoch on turn+chronicle.
- `api_bridge/registry_index.py` — NEW: cardinality indexes + synergy_query.
- `api_bridge/projection.py` reference model; `api_bridge/_golden_migrate.py` — NEW migration pipeline (rerun target).
- FRONTEND: `src/state/store.js` (mounted projection atomic commit, mountProjection coordinator, selectedCharacterId, mount epoch + stale guards, journal=chronicle, diagnostics channel), `src/components/{CampaignSelect,DialogueSystem,CommandPanel,ActionPanel,App}.jsx`, `src/components/AddCharacter.jsx` (NEW), `src/styles/{design-tokens,component-tokens}.css` (NEW, not yet applied in JSX).
- `registry/golden_slice/**` — NEW lane + `migration/*.bak.json` backups.
- Docs: `app/genesis-os/docs/architecture/*` (contract Rev1.1 + C.5/C.6 artifacts).

## Runtime backup paths (pre-migration, DO NOT OVERWRITE)
- `registry/golden_slice/migration/meridian_reach_20260721_025511.bak.json`  (sha256[:16] = c29584ff987e472e)
- `registry/golden_slice/migration/shadows_of_empire_20260721_025511.bak.json` (sha256[:16] = f62175189a97bbd6)
- Live runtimes currently EQUAL these hashes (rollback applied).

## Commands
- **Rollback (already applied; re-run to re-restore):** `cd api_bridge && python _rollback_checkpoint.py`
- **Migration (RERUN with fidelity fix next session):** `cd api_bridge && set PYTHONUTF8=1 && python _golden_migrate.py`
- **Registry build (must be wired to load golden_slice):** in `api_bridge/server.py` `build_registry()`; run via server start.
- **Projection validation (live):** `curl http://localhost:8788/api/v1/gm/projection` after `POST /api/v1/gm/mount {campaign_id}`.
- **Frontend build:** `cd app/genesis-os && npm run build`
- **Live servers:** api bridge → `cd api_bridge && set PYTHONUTF8=1 && python server.py` (port 8788); dev UI → `cd app/genesis-os && npm run dev` (port 1420, strictPort).
- **Playwright acceptance (to be authored):** `cd app/genesis-os && npx playwright test e2e/` (specs from `docs/architecture/LIVE_UI_ACCEPTANCE_TESTS.md`).

## Gate evidence paths (`_readiness_checkpoint_20260720/`)
c6_final_gate.json, lane_preflight.json, rollback_verification.json, golden_slice_reference_inventory.v2.json, golden_source_candidates_{meridian_reach,shadows_of_empire}.v2.json, projection_{...}.c6.json, projection_gate_*.json, 05_campaign_isolation_test.json, 06_phase_a_tests.json, PHASE_A_REPORT.md, READINESS_DELIVERABLE.md.

## Known regressions (from the reverted migration — MUST fix before re-applying)
- Ration pack quantity 10→1; Blaster ammunition 50→1; Standard blaster pistol equipped true→false.
- opening_status completed→opening; transcript + journal emptied (migration rebuilt runtime without preserving transcript/chronicle projection + lifecycle).
- species_human shown instead of Human; bg_smuggler double-prefixed; class_operator resolved from a Bounty-Hunter Operator subclass doc (unverified as Aran's class); Tala/Kass unresolved; Sentry planned subclass dropped from resolved view; vessel id disagreement (current_vessel_id vs assigned vs command_record.ship.vessel_id).
- 24 authored residual lane records are STUBS (no mechanics/effects/tags/prereqs; mechanical_match null).

## Remaining C.6 closure tasks (next session, in order)
1. Add a field-level before/after **migration_fidelity** validator (identity, quantities, equipped, resources, transcript, journal, opening lifecycle, relationships, asset assignments, unique-item state, campaign history). All must pass.
2. Fix migration to PRESERVE mutable state + transcript/chronicle/opening lifecycle (migrate identity/features/powers/items to refs WITHOUT resetting quantities/equipped/lifecycle).
3. Repair semantic resolution: species_human→Human, bg_smuggler→canonical Smuggler (no double-prefix), verify class_operator authority (or reclassify Aran class), resolve Tala/Kass, restore Sentry planned subclass in resolved view, reconcile vessel ids.
4. **Enrich the 24 authored residuals** from runtime backups (move original mechanics/effects into lane records; preserve global vs campaign-local vs instance vs edge vs mutable distinctions; no un-reviewed promotion of adopted Meridian mechanics to global).
5. Wire `server.build_registry` to ingest `registry/golden_slice/`; prove the REAL live `/gm/projection` returns registry_resolution_coverage_percent:100, missing:0, unresolved:0 (not COMB-offline).
6. Re-run migration + rebuild live projections + pass the REAL live C.6 gate.

## D–L execution order (after C.6 live pass)
A/B/C done (ProjectionBuilder, atomic commit, selected_character_id). Then:
D repoint DNA Record (ProgressionTree) → projection.operative.progression + definitions.
E repoint Map (GalacticMap) → command_record.map.visible_nodes (empty state if none).
F repoint Ship (ShipManagement tab) → command_record.ship (empty state).
G repoint Nemesis (NemesisWeb) → command_record.player_visible_nemesis (server visibility-filtered, empty state).
H remove scripted Dialogue Malice fallback from live mode.
I container refactor + fixed headers / scrollable tab bodies (Operative + Command&Record).
J suggestion 2x2 grid + composer populate-not-transmit + transcript auto-follow.
K apply design tokens (design-tokens.css/component-tokens.css) in JSX.
L live Playwright acceptance + screenshots (LIVE_UI_ACCEPTANCE_TESTS.md).

## Expected clean-state criteria (Phase A GATE_PASS)
Every visible panel shares one campaign_id/mount_epoch/state_revision; character panels share character_id; 0 console errors; 0 error-boundary faults; 0 cross-campaign leaks; 0 cross-character leaks; 0 fixture fallbacks; stable scrolling; crawl no-remount from unrelated actions; readable tokenized typography; persistence across restart; rendered screenshots for both campaigns + after restart.
