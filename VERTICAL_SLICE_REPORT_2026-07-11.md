# Vertical Slice — Execution Report (2026-07-11)

## Phase 1 result: slice validated, first Gold promotion

| Entity | Profile | Status | Blockers | Tier |
|---|---|---|---|---|
| fac_black_sun | faction_core | **PASS — clean** | 0 | **GOLD** (promoted, passes gold-mode validation at `data/gold/factions/core/`) |
| creature_shadowstalker_nexu | creature_core | WARN | 0 | wip |
| species_wookiee | species_core | WARN | 0 | wip |
| guardian | class_core | WARN | 0 | wip |
| subclass_guardian_protector | subclass_core | WARN | 0 | wip |
| loc_xizors_palace | location_core | WARN | 0 | wip |

**Zero schema violations across all six.** The five WARNs are lint-canon majors only (see blockers list below). Every migration was deterministic with originals preserved (`.premigration.bak` / `.preslice.bak` files + `_legacy` blocks + the backend `_legacy` store).

## Pipeline bugs found & fixed while getting there (the platinum loop now RUNS)

1. `faction_core.profile.yml`: unquoted `{run_id}` parsed as YAML dict → kernel refused profile. Quoted.
2. `orchestrator._run_urid_validator` — called by Step 0 but didn't exist (lost mid-refactor). Reimplemented, wraps the deterministic urid_validator.
3. `_call_blacksmith()` didn't accept `append_allowlist`/`creator_string_allowlist` its caller passes. Wired through.
4. `ForgeConfig.mode` referenced in 4 agent-callers but never existed. Safe fallback added.
5. **23 legacy schemas were metaschema-invalid** (comment strings as property values) — every Class/Creature/Subclass/etc. validation failed generically. All repaired (`.bak_20260711` kept). Two edge cases remain: `Item.schema.json`, faction_core metaschema nit.
6. `load_profile()` ignored ProfileContract fields → class/subclass/creature profiles resolved to nonexistent schemas. Now honors `schema.primary_id` + `dataset_kind`.
7. Profiles want tags at `forge_v3/tags/` — created as a junction to the canonical lexicon (no drift).
8. forge.yml agent models pointed at un-pulled `qwen2.5-coder:14b`/`qwen2.5:7b` → repointed to your `qwen2.5-coder:32b` / `qwen2.5:14b` per your directive (backup: `forge.yml.bak_20260711`). Platinum's own model check also pulled `deepseek-r1:32b`, `phi4`, `mistral` into B:\Ollama.
9. Windows runs need `PYTHONUTF8=1` (cp1252 crashes otherwise) — baked into RUN_PLATINUM.ps1 mentally; add `$env:PYTHONUTF8='1'` if running manually.

Verdict on the agents: the Blacksmith (qwen2.5-coder:32b) ran real iterations but hallucinated patch paths on move-heavy migrations; the valid-op filter correctly rejected them (guardrail works). Deterministic migration scripts did what the agent couldn't — per Article 8, that's the right order anyway.

## Remaining blockers to full-slice Gold (deliberate work, not hacks)

- **Lint canon vs legacy schemas disagree** on allowed root keys for creature/class/subclass/species/location (~80 LINT_001 majors). The lint SOP expects core-shape roots; the profiles' schemas are legacy-shape. One of them is law — your call which (I'd migrate the schemas to core-shape, matching faction).
- `location_core.schema.json` is half-migrated: flat shape + metadata block; palace's core-shape blocks (`taxonomy/essence/connections/ui`) sit in `_legacy` awaiting the schema decision.
- Black Sun's rich relationship narratives + mechanical_effects (from the old `connections.relationships`) are preserved in `.premigration.bak` but not yet extracted into `synergy_engine.rules` — a proper Chaos Engine authoring pass.
- `subclass` URID_004 wants `owner_id`, but class guardian's id is bare `guardian` (no `class_` prefix) — URID convention decision needed for classes.

## Phases 2–4: UI is live

- `UI_ARCHITECTURE_v0.1.md` — full schema→component binding map, prod vs v0.1 stack, hard requirements.
- `ui/v0.1/` — diegetic dataslate (single-file, production-shaped logic): O(1) registry Map, broken-ref chips, GOLD/WIP badges with an "UNVERIFIED DATA" overlay on wip entities, GM/Player view gate on `ai_behavior`/`llm_guidance`, condition-locked attack cards (Silent Pounce shows its `attacker_has_surprise` gate), RFC6902 dispatch (watch the HP gauge drop ~6s after load — that's a simulated forge state delta replaying through the same patch format the pipeline emits).
- Headless binding QA: all panels bind (3 gaps found & fixed — mid-migration `_legacy` fallbacks).
- **Live now: `http://localhost:8777`** (`ui/v0.1/serve.ps1` restarts it anytime; it rebuilds `campaign_data.json` from Gold/WIP on every launch, so re-running after future promotions auto-upgrades badges from WIP to GOLD).

## QA click-through script

1. Top bar: campaign state renders from `CampaignState`-shaped mock; Xizor's Palace is a live link (file-chaining).
2. Black Sun slate: GOLD badge, no warning overlay; NETWORK tab → allies/enemies/neutral resolve to chips (unknown factions render red = visible ref validation).
3. Shadowstalker: WIP overlay; STATBLOCK → Silent Pounce padlock; toggle GM VIEW → BEHAVIOR tab reveals `ai_behavior`/`llm_guidance`.
4. Wait for the `[PATCH replace /party/0/hp/current]` line in the console log — UI reacted to a backend-format delta with no reload.
