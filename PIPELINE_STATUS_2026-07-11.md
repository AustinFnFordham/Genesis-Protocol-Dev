# Genesis Protocol — Pipeline Initialization Report (2026-07-11)

## Status: Deterministic layer OPERATIONAL

The Forge V3 pipeline (`SW5e_Data_Hub/forge_v3/`) was exercised end-to-end at the deterministic-validation layer, per Article 8 (Determinism First). All commands available: `forge`, `validate`, `apply-patch`, `promote`, `platinum`.

## Fix applied (schema bug, minimal + non-destructive)

`location_core.schema.json` and `npc_core.schema.json` still pointed their `metadata` block at `faction_core.schema.json#/$defs/metadata_block`, but that block had been extracted to `common/common_metadata.schema.json` — a stale ref that crashed every location/NPC/planet validation with `Unresolvable JSON pointer: $defs/metadata_block`. Both refs were repointed to the common schema (restoring the extraction's documented intent — see common_metadata's own description: "Extracted to prevent drift"). No fields added, renamed, or changed (Article 7 respected).

Requires `jsonschema>=4.18` (`pip install "jsonschema>=4.18" jsonpatch`).

## The two WIP stores — resolved picture

| Store | Real entities (.yml) | Notes |
|---|---|---|
| `forge_v3/data/wip/` | 62 (18 factions, 15 feats, 12 planets, 5 approaches, 5 assets, 5 locations, 2 species) | Newest work (edits through 2026-01-10) |
| `SW5e_Data_Hub/backend/wip/` | 121 (119 factions, 1 planet, 1 species) | Earlier bulk run (~2026-01-04); the "757 files" were mostly its 706 old validation-report JSONs |
| Overlap | **2 factions only** (`fac_black_sun`, `fac_children_of_the_watch`) — forge_v3 versions are newer | Stores are complementary, not duplicates |

Note: forge intentionally reads `master_tags.yml` (297 tags) from the nested hub — the nested hub is live infrastructure, not junk.

## Validation results (wip mode)

~180 entities validated. Current state: 0 pass clean, ~17 warn, rest fail. Finding profile from 93 sampled reports:

| Code | Count | Meaning |
|---|---|---|
| SCH_001 | 298 (BLOCKER) | Schema violations — mostly `additionalProperties` (e.g. legacy `mechanics` root key not yet migrated) |
| LEX_004 | 229 (MAJOR) | Unknown tags not in Master Tag Lexicon (e.g. `tag_approach_combat`) |
| URID_004 | 53 (MAJOR) | Owned entities missing `owner_id` |
| LINT_001 | 37 (MAJOR) | Unknown root keys (again `mechanics`) |
| URID_007/001, LINT_002/003 | few | owner_id on globals, missing id, key order, empty blocks |

Interpretation: the data isn't broken — it's mid-migration. The dominant failures are legacy `mechanics` blocks awaiting migration into schema-approved structure (Article 6) and tags awaiting canonization (`--canonize-tags` exists for this).

## Recommended next steps (in order)

1. **Merge backend/wip into forge_v3/data/wip** — 117 unique backend factions moved in (originals to `_legacy` per Article 6); keep forge_v3's newer versions of the 2 overlaps. I can do this on your go-ahead.
2. **Tag canonization pass**: rerun validation with `--canonize-tags` to burn down the 229 LEX_004s; add genuinely new tags to `master_tags.yml` deliberately.
3. **Run the `platinum` loop locally** (validate → agent → patch → revalidate) to migrate `mechanics` blocks — needs your Ollama models (the 50 GB in `blobs/` — llama3.1:8b, qwen2.5:14b/32b, qwen2.5-coder:32b), so it must run on your RTX machine, not here.
4. **First gold promotions** once blockers hit zero: `python forge.py promote`.

The 9-agent roster (Gaugewright, Canticle Examiner, Reagent Inspector, Foreman, Blacksmith, Runesmith, Alchemist, Spark Igniter, Extractor) lives in the hub-root `forge.py` (v2, faction-focused); forge_v3 consolidated to Foreman/Alchemist/Bard/Runesmith + deterministic validator suite. Both preserved.
