# Genesis Protocol — Production Readiness Report (2026-07-11)

## Executed this session (all authorized, all non-destructive)

**1. WIP merge (Article 6 honored).** All 109 unique backend entities copied MD5-verified into `forge_v3/data/wip/` — the single live store, now 171 entities. The complete original backend store (all 982 files incl. run history) preserved untouched at `SW5e_Data_Hub/SW5e_Data_Hub/backend/_legacy_wip_merged_2026-07-11/`. Correction: the "117 unique factions" were actually 5 faction cores + ~112 owned entities (feats/locations/stubs).

**2. Lexicon root cause + tag canonization.** The 229 LEX_004 errors weren't 229 bad tags — forge was silently falling back to a 6-tag acceptance-test stub because the full lexicon was never installed at its primary path (`SW5e_Data_Hub/data/tags/master_tags.yml`). Installed the full 314-tag lexicon there, then deliberately extended it with 32 tags mined from the wip inventory (new categories: location_type, asset_type, approach_type, rank, era, background; plus additions to class, faction_identity, faction_trait — two with `redundancy.aliases` so `--canonize-tags` auto-maps the malformed `tag_established`/`tag_galactic_power`).

**LEX_004: 229 → 17.** The 17 survivors are exactly the two tags excluded on purpose: `tag_faction_feat` (×15) and `tag_stub` (×2) — workflow markers the platinum agents should strip, not lexicon material.

**3. Schema repairs (stale refs, Article 7 respected — no semantics changed).**
- `location_core` + `npc_core`: metadata ref repointed from faction_core's removed `$defs` to `common_metadata` (restores documented intent)
- `common_urid`: added missing `planet_id` def (`^planet_[a-z0-9_]+$`), referenced by location_core but never defined
- Known bug left for you: `forge.py validate --debug-paths` crashes (`forge_root` undefined, forge.py:621)
- Pre-existing issue flagged, not touched: the lexicon contains 17 duplicate tag ids (tag_scout, tag_sith, tag_military, ...) — dedupe deliberately, categories may differ between copies

**4. Ollama relocation — with a twist.** The project `blobs/` wasn't your live store: your server runs from **B:\Ollama** (GUI setting), which was already missing blobs. Merged the project's 50 GB into B:\Ollama, which healed it: `llama3.1:8b`, `qwen2.5:14b`, `qwen2.5:32b`, and `qwen2.5-coder:32b` (forge_v3's default agent model) are all serving again. `OLLAMA_MODELS` (user) → `B:\Ollama`. `E:\StarWars` is now 50 GB lighter; `E:\OllamaModels` holds only the merge logs.

## Current validation state (full wip, 171 entities)

| | Count |
|---|---|
| PASS | 2 |
| WARN | 17 (feats + planets, minor findings only) |
| FAIL | 152 |
| SCH_001 (blocker) | 956 — legacy `mechanics`/extra root keys awaiting platinum restructuring |
| LINT_001 (major) | 400 — same root cause |
| URID_004 (major) | 60 — owned entities missing `owner_id` |
| LEX_004 | 17 — intentional workflow markers |

## Your move: fire the platinum loop

Everything deterministic is done. The remaining 956 blockers need the agents. On your machine:

```powershell
E:\StarWars\RUN_PLATINUM.ps1                  # repair pass (offline-only, max 10 iterations/file)
E:\StarWars\RUN_PLATINUM.ps1 -PromoteToGold   # same, but promote passing files to gold
```

It batches all 7 categories with correct profiles and logs to `forge_v3\logs\`. qwen2.5-coder:32b is confirmed available in your healed store. Quarantine stays untouched until gold promotion completes, per your instruction.
