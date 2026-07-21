# Genesis Protocol — Condensed Project History

One-page summary of the ~70 phase/status reports now archived in `_ARCHIVE/docs/`. Full originals preserved there.

## Era 1 — Data Hub foundation (2025)
The SW5e Data Hub was assembled from source imports (`source_data/`, 1,230 files) into a categorized backend (nested `SW5e_Data_Hub/backend/`, actions through species). Early Genesis Protocol phases (Phase 0–1, Priority 1–2) established schemas and converted legacy data. **The Great Tagging Pass** brought all 947 data files under the Master Tag Lexicon (297 tags, `master_tags.yml`) across 9 data categories. Items, starships, powers, and features expansions completed. Reports: `_ARCHIVE/docs/GenesisProtocol_reports/`.

## Era 2 — New_Genesis (pipeline v2, 2025)
Batch upgrade/audit tooling (audits, reforges, synergy maps, platinum polish) produced 23 production NPC statblocks and extensive class/subclass deepening. Superseded by Forge V3; tree retained at `SW5e_Data_Hub/New_Genesis/` as legacy + usable data examples.

## Era 3 — Forge V3 (current, late 2025–2026)
The live system at `SW5e_Data_Hub/forge_v3/`. Governed by **ARTICLES_OF_CREATION.md** (immutable laws: atomic/soul/chaos ontology, no silent loss, no schema drift, determinism first). Key milestones (reports in `_ARCHIVE/docs/forge_v3_reports/`):

- Milestones 2–6: orchestrator, agent dispatcher, patch engine, registry, gates
- Agent cluster implemented: Foreman, Alchemist, Bard, Runesmith + validator suite
- Gold promotion system complete (2026-01-06): gold gate module, mode-aware validators (wip vs gold), deterministic migration, promote command, test suite
- Production-ready fixes (2026-01-08): centralized `master_tags.yml` path resolution — note: forge intentionally reads tags from the nested hub (`SW5e_Data_Hub/SW5e_Data_Hub/data/tags/`)
- Platinum tier defined (`PLATINUM_DEFINITION.md` kept live in forge_v3/)

## Current state (per 2026-07-10 audit)
- Pipeline: built and production-ready; gold tier nearly empty (6 files) — mass promotion not yet run
- Data: two active wip stores need reconciliation (backend/wip: 757 files vs forge_v3/data/wip: ~156)
- Living docs kept in `forge_v3/`: Articles of Creation, Comprehensive Walkthrough, Agentic Workflow Flowmap, Chaos Engine Rulebook, Platinum Definition, Phase Checklist, Next Steps, Model Recommendations, Acceptance Test Baseline, Gold Freeze & Next Steps, Refinements TODO

## Side project
`The-Ender-Protocol/` — AWS Bedrock hackathon app (Lambda + SAM), independent of the game data pipeline. Setup docs archived to `_ARCHIVE/docs/ender_docs/`.
