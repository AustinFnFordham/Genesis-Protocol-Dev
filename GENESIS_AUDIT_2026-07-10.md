# Genesis Protocol — Phase 1 Audit (2026-07-10)

Non-destructive inventory of `E:\StarWars`. Nothing was moved, modified, or deleted.

## Verdict: Canonical source of truth

**`SW5e_Data_Hub/forge_v3/` is the live system.** Evidence:

- 1,457 files modified in 2026 (every other tree is dormant: New_Genesis = 2, source_data = 0)
- Contains the current orchestrator (`forge_core/orchestrator.py`), the agent cluster (`agents/`: alchemist, bard, foreman, runesmith + validators), 53 schemas, and `ARTICLES_OF_CREATION.md`
- Implements the gold/wip promotion tiers mandated by the Articles (Article 6: quarantine to `_legacy`, no silent loss)

**One open question:** there are TWO active wip stores, both touched in 2026:

| Store | Files | Contents |
|---|---|---|
| `forge_v3/data/wip/` | ~156 | approaches, assets, factions, feats, locations, planets, species |
| `SW5e_Data_Hub/SW5e_Data_Hub/backend/wip/` | 757 | factions, feats, planets, species |

The path router (`path_router.yml`) uses relative paths (`data/wip`), so the pipeline writes wherever it's run from. The nested-hub wip is the larger, more recent output. **These must be reconciled in Phase 3 — likely the 757-file store is your newest generation run.**

Gold tier is nearly empty (6 files) — almost everything is still awaiting promotion.

## Tree-by-tree assessment

| Tree | Status | Notes |
|---|---|---|
| `SW5e_Data_Hub/forge_v3/` | **CANON — live pipeline** | Agents, schemas, Articles, gold/wip data |
| `SW5e_Data_Hub/SW5e_Data_Hub/` (nested) | **CANON data / legacy code** | backend/wip (757 files, 2026) is live output; rest is an older full copy (2,271 yml/json) |
| `SW5e_Data_Hub/New_Genesis/` | Legacy (pipeline v2) | 1,681 files incl. 23 production NPC statblocks — usable data examples |
| `SW5e_Data_Hub/source_data/` | Legacy source import | 1,230 files, untouched in 2026 — keep as reference/seed data |
| `SW5e_Data_Hub/GenesisProtocol/` | Docs only | 12 phase reports — archive candidates |
| `The-Ender-Protocol/` | Separate project | AWS Bedrock hackathon app; 8 iterating `app_ui_*.py` versions |
| `Genesis_Protocol_Obsidian/` | Design vault | Architecture diagrams/notes — keep |
| `blobs/` + `manifests/` | **50 GB Ollama model cache** | llama3.1:8b, qwen2.5:14b/32b, qwen2.5-coder:32b. Machine-specific cache, not project data |
| `schema/` (root) | Older schema copy | 40 schemas vs forge_v3's 53 — superseded |

## Junk / quarantine candidates (SW5e_Data_Hub root)

- ~30 loose `debug_*.txt`, `*.log`, report `.txt` files at the hub root
- 14 loose one-off `.py`/`.ps1` migration scripts (superseded by forge_v3)
- `docs.zip`, `SW5e_Data_Hub.zip` — snapshot archives
- `dxdiag_output.txt` — hardware diagnostic, unrelated

## Documentation sprawl (~416 .md files)

forge_v3: 134 · New_Genesis: 87 · docs/: 38+55 · GenesisProtocol: 12 · misc phase reports at multiple roots. Heavy overlap: many MILESTONE_*, NEXT_STEPS_*, IMPLEMENTATION_* files describe completed phases.

## Proposed Phase 2 plan (all non-destructive)

1. Create `E:\StarWars\_QUARANTINE\` — move (not delete) debug/log/txt junk, loose one-off scripts, and the two .zip snapshots there for your review.
2. Create `E:\StarWars\_ARCHIVE\docs\` — consolidate completed-phase .md reports (milestones, phase reports, next-steps) with an index; leave living docs (`ARTICLES_OF_CREATION.md`, agent/workflow docs, walkthroughs) in place.
3. Write a condensed `PROJECT_HISTORY.md` summarizing the archived reports.
4. Leave all data trees untouched (forge_v3, nested backend, New_Genesis, source_data) — data reconciliation belongs to Phase 3 under the pipeline's own validation.
5. Flag (not move) the 50 GB Ollama cache — recommend relocating it outside the project via `OLLAMA_MODELS` env var; your call.

## Proposed Phase 3 plan

1. Reconcile the two wip stores (backend/wip 757 vs forge_v3/data/wip 156) — dedupe by URID, newest wins, losers to `_legacy`.
2. Run forge_v3 deterministic validation over the unified wip against the 53 schemas.
3. Produce a promotion-readiness report: what can move wip → gold, what fails validation and why.
