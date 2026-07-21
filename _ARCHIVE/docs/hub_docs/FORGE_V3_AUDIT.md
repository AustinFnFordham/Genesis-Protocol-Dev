# FORGE_V3_AUDIT.md

**Scope**: `forge_v3/` deep-dive for upcoming structural + workflow refactor (no code changes performed).  
**Date**: 2026-01-04  

This document summarizes what exists today, how data moves through the system, where artifacts are created/consumed, where the system violates the **Articles of Creation**, and where the **agentic loop** is fragile (especially around JSON Schema validation).

---

## Executive Summary (Current State)

- **Two parallel pipeline stacks** exist inside `forge_v3/`, with overlapping responsibilities but **inconsistent contracts**:
  - **Stack A (Phase Orchestrator)**: `forge_core/orchestrator.py` (“TEMPERING → INSCRIPTION → SPARK”)  
    - Deterministic checks: `agents/validators/gaugewright.py` (Draft7) + `agents/validators/completeness_validator.py`
    - LLM calls: direct `ollama run` / `POST /api/generate`
    - Output: `logs/forge/<file_id>/compiled_report.*` and a single YAML output path.
  - **Stack B (Graph-Closed Platinum Loop)**: `forge_core/platinum_loop.py`  
    - Deterministic checks: `forge_core/validators/*` (Draft2020-12 schema registry) + URID/Lexicon/Lint/Legacy + optional Synergy
    - LLM calls: `forge_core/local_llm_adapter.py` + `forge_core/agent_dispatcher.py` + `forge_core/patch_engine.py`
    - Output: localized `.forge_runs/<run_id>/...` next to the file being processed (plus patch audits).

- **Profiles are duplicated** and **not shape-compatible** across stacks:
  - `forge_core/profiles/*.profile.yml` (used by `forge.py validate` and parts of `platinum_loop`)
  - `profiles/*.forge.yml` (used by Stack A via `forge_core/config.py` dataclasses)
  - Some profiles (notably `planet_core.profile.yml`, `planet_era_state.profile.yml`) do **not** match the contract expected by validators like `SynergyValidator` (expects `chaos_policy.enabled`, allowlists).

- **Run artifact journaling is split** and partially dead-ended:
  - `forge.py platinum` creates a run context under `forge_v3/.forge_runs/...` via `forge_core/run_context.py`, but the actual loop then creates a different run directory next to the target file. The first one is effectively unused by the loop.

---

## Inventory

### Schemas (JSON Schema)

Location: `forge_v3/schemas/`

- **Entity schemas**
  - `schemas/faction/faction_core.schema.json`
  - `schemas/feat/feat_core.schema.json`
  - `schemas/approach/approach_core.schema.json`
  - `schemas/asset/asset_core.schema.json`
  - `schemas/location/location_core.schema.json`
  - `schemas/npc/npc_core.schema.json`
  - `schemas/planet/planet_core.schema.json`
  - `schemas/planet/planet_era_state.schema.json`
  - `schemas/species/species_core.schema.json`

- **Common / infrastructure schemas**
  - `schemas/common/common_atomic.schema.json`
  - `schemas/common/common_urid.schema.json`
  - `schemas/common/master_tags.schema.json`
  - `schemas/common/migration_map.schema.json`
  - `schemas/common/registry_index.schema.json`
  - `schemas/common/validation_report.schema.json`

- **Duplicate/legacy naming**
  - `schemas/Faction_Core.schema.json` (note the parallel faction schema naming; used by `profiles/faction_core.forge.yml`, while `forge.py validate` tends to use `faction/faction_core.schema.json`).

### Profiles / Contracts

There are **two profile systems**:

- **Validator profiles (simple dict contract)**: `forge_v3/forge_core/profiles/*.profile.yml`
  - `faction_core.profile.yml`
  - `feat_core.profile.yml`
  - `location_core.profile.yml`
  - `planet_core.profile.yml` *(shape mismatch vs validator expectations; see audit)*
  - `planet_era_state.profile.yml` *(shape mismatch; see audit)*

- **Orchestrator profile overlays (dataclass-driven)**: `forge_v3/profiles/*.forge.yml`
  - `faction_core.forge.yml` (schema pointer, normalization pointers, completeness, patch allowlists, path aliases)

### Logic Controllers / Entry Points

- **Primary CLI**: `forge_v3/forge.py`
  - `forge`: Stack A orchestrator (`forge_core/orchestrator.py`)
  - `validate`: deterministic validator runner + report writer (`*_validation_report.json`, `batch_validation_summary.json`)
  - `platinum`: Stack B graph-closed loop (`forge_core/platinum_loop.py`) with staging (`forge_core/run_context.py`)
  - `apply-patch`: apply RFC6902 patch to YAML + audit log (`.patch_audit.jsonl`)

- **Stack A (Phase orchestrator)**
  - `forge_core/orchestrator.py`
  - `agents/validators/gaugewright.py` (Draft7 schema validator + ID/type checks)
  - `agents/validators/completeness_validator.py` (minItems/minLength/banned phrase)

- **Stack B (Graph-closed platinum loop)**
  - `forge_core/platinum_loop.py`
  - `forge_core/agent_dispatcher.py` (finding→agent routing, prompt loading, per-agent reports)
  - `forge_core/local_llm_adapter.py` (Ollama adapter + retry/parsing)
  - `forge_core/patch_engine.py` + `forge_core/patch_preflight.py` (patch guardrails and audit)
  - `forge_core/run_context.py` (staging + journaling)
  - `forge_core/graph_utils.py` (URID collection + path resolution heuristics)
  - `forge_core/synergy_loader.py` (optional cross-file checks; writes synergy reports)

- **Auxiliary tooling**
  - `forge_v3/tools/orchestrate_directory.py` (directory orchestrator; appears incomplete and contract-mismatched)
  - `forge_v3/tools/*` (tag dedupe, tag migration, path migration)

### Agent Definitions (Where “agents” live)

There are **two agent namespaces**:

- `forge_v3/forge_core/agents/`
  - `alchemist_agent.py`
  - `bard_agent.py`
  - `foreman_agent.py`
  - `runesmith_agent.py`

- `forge_v3/agents/`
  - `base.py` (legacy-ish BaseAgent wrappers)
  - `validators/` (deterministic validators used by Stack A)
  - `creators/`, `patchers/`, `spark/` (present but currently just package shells)

---

## Dependency & Dataflow Mapping (File Creation → Validation)

### Mermaid: end-to-end (including artifact creation)

```mermaid
flowchart TD
  %% Entrypoints
  A[User/Tool invokes forge_v3/forge.py] --> B{Command?}
  B -->|validate| V0[Deterministic validators]
  B -->|forge| F0[Stack A: ForgeOrchestrator]
  B -->|platinum| P0[Stack B: Platinum Loop]
  B -->|apply-patch| AP0[patch_engine.apply_patch_to_file]

  %% validate path
  V0 --> V1[urid_validator]
  V0 --> V2[schema_validator (Draft2020-12 registry)]
  V0 --> V3[lexicon_validator (master_tags)]
  V0 --> V4[lint_sop]
  V0 --> V5[Write <file>_validation_report.json]
  V0 --> V6[Write batch_validation_summary.json (directory mode)]

  %% Stack A path
  F0 --> F1[Normalize + migrate_legacy_to_core]
  F1 --> F2[CompletenessValidator (Python)]
  F1 --> F3[Gaugewright (Draft7 JSON Schema)]
  F3 --> F4{Gate passed?}
  F4 -->|No| F5[Call Genesis/Blacksmith via Ollama]
  F5 --> F6[apply_patches_safely (patching.py)]
  F6 --> F1
  F4 -->|Yes| F7[Write output YAML to paths.output_dir]
  F7 --> F8[Write logs/forge/<file_id>/compiled_report.*]

  %% Stack B path
  P0 --> P1[Stage input into data/wip (run_context._stage_to_wip)]
  P0 --> P1a[init_run_dir => forge_v3/.forge_runs/<run_id>/...]:::deadend
  P1 --> P2[platinum_loop creates local run dir: <target_dir>/.forge_runs/<run_id>/]
  P2 --> P3[BFS collect URIDs (graph_utils.collect_urids_from_data)]
  P3 --> P4[Resolve URID->path (graph_utils.resolve_urid_to_path)]
  P4 --> P5{File exists?}
  P5 -->|No| P6[stub_generator.create_stub_file]
  P6 --> P3
  P5 -->|Yes| P7[Validate (urid+schema+lexicon+lint+legacy)]
  P7 --> P8{Fail?}
  P8 -->|No| P9[Mark visited + write_file_state.json]:::deadend
  P8 -->|Yes| P10[dispatch_findings (agent_dispatcher)]
  P10 --> P11[Sandbox apply patch ops]
  P11 --> P12[Re-validate sandbox]
  P12 --> P13{Strict improvement?}
  P13 -->|Reject| P14[record_reject => rejected.jsonl]:::deadend
  P13 -->|Accept| P15[apply_raw_patches => write YAML + .patch_audit.jsonl]
  P15 --> P16[record_accept => accepted.jsonl]:::deadend
  P15 --> P3

  %% apply-patch path
  AP0 --> AP1[Write YAML (unless dry_run)]
  AP1 --> AP2[Append .patch_audit.jsonl]

  classDef deadend fill:#eee,stroke:#999,stroke-dasharray: 4 3,color:#333;
```

### “Dead-end” artifacts (created but not consumed by the pipeline)

These are **created by code** but appear **never read back** by any other code-path in `forge_v3/`:

- **RunContext artifact tree created by `forge.py platinum`**: `forge_v3/.forge_runs/<run_id>/...`  
  - Created by `forge_core/run_context.py:init_run_dir()`, but `platinum_loop` then creates/uses a *different* run directory next to the file.
- **Journals inside that RunContext tree**
  - `accepted.jsonl`, `rejected.jsonl`
  - `file_states/*.json`
  - `best_snapshots/*`
  - `final_reports/` (created but not written by the loop)
- **`forge_v3/configs/`**: present but empty.

Note: Some artifacts are “human-consumption only” (reports, audits). Those are not dead ends if they are intentional outputs, but they still matter for folder design.

---

## “Articles of Creation” Audit (Compliance & Violations)

This section lists the highest-signal places where current logic conflicts with the system laws in `forge_v3/ARTICLES_OF_CREATION.md`.

### A) Determinism First (Article 8) — Violations / Risk

- **Schema validation can silently degrade to “PASS” in Stack A**
  - `ForgeOrchestrator._run_gaugewright()` returns `PASS` when schema file is missing.
  - `agents/validators/gaugewright.py` returns only a *MINOR* issue if `jsonschema` is not installed (“skipping schema validation”).  
  - This violates “Schemas are law” + “LLMs never run first” because the pipeline can proceed as if structure is valid even when schema validation is unavailable.

- **Draft mismatch produces inconsistent truth**
  - Stack A schema validation uses **Draft7** (`agents/validators/gaugewright.py`).
  - Stack B schema validation uses **Draft2020-12** (`forge_core/schema_loader.py`).
  - Same file can pass one stack and fail another depending on draft features (`$defs`, `$id`, `$ref` semantics).

### B) Profiles Are Contracts (Article 13) — Contract Drift

- `forge_core/validators/synergy_validator.py` expects:
  - `chaos_policy.enabled`
  - `allowed_trigger_events`
  - `allowed_effect_categories`
- But `forge_core/profiles/planet_core.profile.yml` and `planet_era_state.profile.yml` instead define:
  - `chaos_policy.feature_density`, `allowed_mutations`
  - and tag policies using wildcard namespaces (e.g., `tag_location_*`)

Impact:
- Any `synergy_engine` content on planets would be treated as out-of-policy (because `enabled` defaults false).
- “No-Bleed” allowlists won’t actually enforce the intended shape for those entity types.

### C) Agent Roles Are Sacred (Article 11) — Role/Config Confusion

- `forge_v3/forge.yml` config includes an “agent” named `gaugewright` with an LLM model, but Gaugewright is defined as a deterministic validator (and used that way in Stack A).
- There is a second, separate validator system in `forge_core/validators/*` that does not map 1:1 to Stack A agent naming.

Net: the system’s vocabulary (“agent role”) is overloaded, and contracts/docs are not aligned to the actual executable paths.

### D) Hybrid Mechanics vs Narrative Logic (“d20 vs FFG narrative dice”) — Audit Findings

Within `forge_v3/`, the mechanics vocabulary is overwhelmingly **d20-coded** (advantage/disadvantage, saves, attacks). Concrete observations:

- `schemas/common/common_atomic.schema.json` defines `modifier_object.type` including `advantage` / `disadvantage`.
- `forge_core/transforms.py` maps legacy `rule.type: advantage|disadvantage` to `effect.category: check_advantage|check_disadvantage`.

Why this is a hybrid-rule risk:
- If upstream/legacy content used “advantage” to mean **FFG narrative dice Advantage** (not d20 advantage), this transform collapses that nuance into a d20 mechanic. That is precisely the kind of “mechanics overriding narrative” semantic drift that hybrid systems are prone to.

Recommendation for refactor (design intent, not implementation yet):
- Introduce an explicit atomic primitive to represent **narrative dice outcomes** (e.g., `narrative_dice_delta` with fields like `advantage`, `threat`, `triumph`, `despair`) *if* the hybrid rules require it.
- Keep d20 advantage/disadvantage as a separate atomic primitive and disallow cross-mapping without a declared conversion policy.

---

## Workflow Failure Analysis (Fragility of the Agentic Loop)

### 1) JSON Schema validation error handling gaps (high risk)

- `forge_core/schema_loader.py` and `forge_core/validators/schema_validator.py` do not wrap validation with robust exception handling for:
  - invalid schemas
  - resolver/ref failures
  - validator construction errors
  - unexpected error object shapes

Observed issue:
- When schema lookup fails, `SchemaRegistry.validate()` returns `{"error": "Schema not found: ..."}`; downstream `schema_validator.validate_schema()` doesn’t treat that as a proper finding (message/path are missing), so the report can become **low-signal** and not clearly block the run.

### 2) Patch application can “succeed” while silently skipping operations (high risk)

- `forge_core/patch_engine.apply_patch()` defaults `skip_errors=True` and will silently skip operations that fail traversal/type/index constraints.
- `apply_raw_patches()` reports `success=True` if the function completes, even if some ops were skipped internally.

Impact:
- The agentic loop can believe it applied a fix, revalidate, and churn without clear introspection of *which* ops were applied vs dropped.

### 3) Run journaling split-brain (medium/high)

- `forge.py platinum` creates a run context at `forge_v3/.forge_runs/...`, but `platinum_loop` uses a different run directory next to the target file.
- Journals created by `run_context` (`accepted.jsonl`, `rejected.jsonl`, etc.) are never read by the loop, so “Proof of Work” is fragmented.

### 4) Adapter/contract mismatches (medium/high)

- `forge_core/validators/agent_output_validator.py` expects agent outputs with `changes[]` + `audit`, but the operational patch pipeline (`agent_dispatcher` → `patch_engine`) uses either:
  - a patch **list** (`local_llm_adapter.OllamaAdapter` returns list), or
  - a patch **document** with `patch` array (in other tool paths)

This mismatch creates weak enforcement and makes it easy for new code to call the wrong validator/patch applier pairing.

### 5) Concrete bug: `local_llm_adapter.OllamaAdapter` timeout path references undefined attribute

- The adapter references `self.timeout[1]` in a timeout handler, but `self.timeout` is not defined in the class initializer.
- If hit, the error handling path can itself raise, collapsing the agentic loop.

### 6) Routing/path resolution inconsistencies (medium)

There are three separate “where should this file live?” implementations:
- `forge_core/config/path_router.yml` + `forge_core/file_router.py`
- `forge_core/graph_utils.resolve_urid_to_path()` (heuristics)
- `forge_core/stub_generator.get_stub_path()` (faction-owned nesting rules)

Impact:
- Platinum loop can create stubs in a location that the resolver doesn’t later find, or vice versa, causing artificial “missing URID” churn.

---

## Proposed “Medallion” Folder Structure (Bronze / Silver / Gold)

Goal: separate *raw/ingest*, *working/normalized*, and *validated/publishable* data, and isolate *artifacts* from *source-of-truth content*.

### Recommended structure (target)

```text
forge_v3/
  data/
    bronze/                  # Raw intake / legacy imports / non-conformant sources
      _incoming/
      _legacy_exports/
    silver/                  # Working set (normalized, patchable, may still WARN)
      ... entity trees ...
      _staging/              # Optional: run-scoped working copies
    gold/                    # Deterministic PASS only (no _legacy, no WARN)
      ... entity trees ...

  artifacts/
    runs/
      <run_id>/
        manifest.json
        accepted.jsonl
        rejected.jsonl
        file_states/
        best_snapshots/
        agent_reports/
        synergy_reports/
        final_reports/
    patch_audit/             # Centralized patch audit logs (or keep per-folder but standardize)

  contracts/                 # Single canonical contract tree (schemas + profile specs + patch protocol)
  pipeline/                  # Orchestrators, validators, routers, adapters
```

### Mapping from today → target (conceptual)

- Today’s `data/wip` aligns most closely to **Silver**.
- Today’s `data/gold` aligns to **Gold**.
- Today’s “legacy imports” are currently mixed into WIP patterns; those should become **Bronze**.
- `.forge_runs/` folders should move under `artifacts/runs/` to avoid polluting content trees and to unify journaling.

---

## Refactor Hotspots (Technical Debt Summary)

Highest ROI items to address in a structural/workflow refactor:

1. **Unify stacks**: choose a single orchestration model (Phase Orchestrator vs Graph-Closed Platinum), or make one a thin wrapper over the other.
2. **Unify profile contract**: one profile format, one loader, one schema for profile validation.
3. **Unify schema validation**: one JSON Schema draft/version, one validator path, one error-report shape.
4. **Unify routing**: one canonical URID→path router used by stub generation, graph resolution, and migration tooling.
5. **Harden error handling** around schema validation, patch application (no silent skips), and LLM adapter failure paths.
6. **Normalize patch protocol**: decide on “patch list” vs “patch document” and enforce it with a single validator everywhere.

---

## Appendix: Notable “Never Used” / “Not Read Back” Outputs

- `forge_core/run_context.py` creates:
  - `forge_v3/.forge_runs/<run_id>/accepted.jsonl`
  - `forge_v3/.forge_runs/<run_id>/rejected.jsonl`
  - `forge_v3/.forge_runs/<run_id>/file_states/*`
  - `forge_v3/.forge_runs/<run_id>/best_snapshots/*`
  - `forge_v3/.forge_runs/<run_id>/final_reports/`
  
These appear to be **dead ends** in the current execution because `platinum_loop` does not consume that run directory.


