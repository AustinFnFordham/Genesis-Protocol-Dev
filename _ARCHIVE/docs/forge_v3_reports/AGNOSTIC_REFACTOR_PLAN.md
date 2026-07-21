# Forge V3 Agnostic Refactor - Implementation Plan

**Goal:** Transform Forge from faction-specific to dataset-agnostic kernel with profile-driven configuration.

**Timeline:** 6 major milestones, each building on the previous

---

## 🎯 Core Principles

1. **Kernel = Generic State Machine** - Never knows about factions, species, items, etc.
2. **Profile = Complete Contract** - Everything dataset-specific lives in profiles
3. **Schema Identity ≠ Resolution** - Canonical `$id` stays in schemas, resolution in profiles
4. **O(1) Runtime** - Orchestration logic doesn't change with dataset size
5. **Compiler-Grade Trust** - Deterministic validators before any LLM involvement

---

## 📋 Milestone 1: Schema Resolver Infrastructure (CRITICAL - Fixes Current Blocker)

**Status:** 🔴 BLOCKING - Required for all validation

**Problem:** Schemas use canonical `$id` URLs (e.g., `https://sw5e-data-hub.local/schemas/common/common_urid.schema.json`) but validator tries to fetch them, causing STRUCTURE blockers.

**Solution:** Create local schema resolver that maps canonical `$id` → local file paths.

### Implementation Steps

#### 1.1 Create Schema Resolver Module
**File:** `forge_core/schema/schema_resolver.py`

**Responsibilities:**
- Load primary schema from profile
- Build in-memory `$id → schema_dict` store
- Resolve `$ref` locally first (never network unless explicitly enabled)
- Fail fast on unresolved canonical IDs

**Key Functions:**
```python
class SchemaResolver:
    def __init__(self, primary_schema_path: str, ref_map: Dict[str, str], base_path: str)
    def load_schema_store(self) -> Dict[str, Dict]  # $id → schema
    def create_validator(self, schema: Dict) -> Draft7Validator  # With resolver
    def resolve_ref(self, ref: str) -> Optional[Dict]  # Local lookup
```

#### 1.2 Update Profile Schema Configuration
**File:** `forge_core/profiles/faction_core.profile.yml`

**Add:**
```yaml
schema:
  primary_path: schemas/faction/faction_core.schema.json
  primary_id: https://sw5e-data-hub.local/schemas/faction/faction_core.schema.json
  ref_map:
    https://sw5e-data-hub.local/schemas/common/common_urid.schema.json: schemas/common/common_urid.schema.json
    https://sw5e-data-hub.local/schemas/common/common_atomic.schema.json: schemas/common/common_atomic.schema.json
    # ... all referenced schemas
```

#### 1.3 Update Gaugewright to Use Resolver
**File:** `agents/validators/gaugewright.py`

**Changes:**
- Accept `SchemaResolver` instance instead of raw schema path
- Use resolver's `create_validator()` method
- Remove direct `Draft7Validator()` instantiation

#### 1.4 Update Orchestrator to Initialize Resolver
**File:** `forge_core/orchestrator.py`

**Changes:**
- In `__init__`, create `SchemaResolver` from profile config
- Pass resolver to `_run_gaugewright()`
- Store resolver in orchestrator instance

**Dependencies:** None (foundational)

**Testing:**
- ✅ Schema validation works offline
- ✅ No network calls during validation
- ✅ STRUCTURE blocker resolved
- ✅ All `$ref` resolve correctly

**Estimated Effort:** 4-6 hours

---

## 📋 Milestone 2: Profile Contract Definition

**Status:** 🟡 FOUNDATION - Required before removing hardcoded assumptions

**Problem:** No formal contract for what a profile must provide. Hardcoded assumptions scattered throughout code.

**Solution:** Define complete profile schema and update config loader to enforce it.

### Implementation Steps

#### 2.1 Create Profile Schema
**File:** `schemas/profile/profile.schema.json`

**Required Sections:**
```json
{
  "schema": {
    "primary_path": "string",
    "primary_id": "string",
    "ref_map": "object"
  },
  "registries": {
    "tags": "path",
    "species": "path",
    "planets": "path"
  },
  "ownership": {
    "owned_kinds": {"prefix": "directory"},
    "global_kinds": ["prefix1", "prefix2"]
  },
  "validators": {
    "enabled": ["gaugewright", "lexicon", "urid", "completeness"],
    "thresholds": {
      "wip": {...},
      "gold": {...},
      "platinum": {...}
    }
  },
  "agents": {
    "by_domain": {
      "STRUCTURE": ["blacksmith"],
      "REFERENCE": ["alchemist"],
      "COMPLETENESS": ["genesis_smith"],
      "NARRATIVE": ["runesmith", "canticle"]
    }
  },
  "completeness": {
    "min_items": {"pointer": count},
    "min_lengths": {"pointer": length}
  }
}
```

#### 2.2 Update ProfileConfig Dataclass
**File:** `forge_core/forge_config.py`

**Add Fields:**
- `registries: Dict[str, str]` - Registry paths
- `ownership: OwnershipConfig` - Owned vs global policy
- `validators: ValidatorConfig` - Enabled validators + thresholds
- `agents: AgentRoutingConfig` - Domain → agent mapping

#### 2.3 Update Profile Loader
**File:** `forge_core/forge_config.py` → `load_config()`

**Changes:**
- Validate profile against profile schema
- Emit BLOCKER if profile missing required fields
- Provide clear error messages for missing config

**Dependencies:** Milestone 1 (schema resolver needed to validate profile schema)

**Testing:**
- ✅ Profile validation catches missing fields
- ✅ Clear error messages for misconfiguration
- ✅ Backward compatibility with existing profiles

**Estimated Effort:** 3-4 hours

---

## 📋 Milestone 3: Remove Hardcoded Faction Assumptions

**Status:** 🟡 CORE REFACTOR - Makes system truly agnostic

**Problem:** Orchestrator and validators contain hardcoded faction-specific logic:
- `master_tags.yml` path hardcoded
- `fac_*` prefix assumptions
- Faction-specific field mappings (`first_missions`, `hooks`, etc.)
- Entity type detection from URID prefix

**Solution:** Move all dataset-specific logic to profile, make orchestrator generic.

### Implementation Steps

#### 3.1 Remove Hardcoded Registry Paths
**Files:** `forge_core/orchestrator.py`, `forge_core/validators/lexicon_validator.py`

**Changes:**
- Remove hardcoded `master_tags.yml` path resolution
- Read registry paths from `profile.registries.tags`
- Make lexicon validator accept registry path from profile
- Update `_run_lexicon_validator()` to use profile config

#### 3.2 Remove Entity Type Detection from URID
**File:** `forge_core/orchestrator.py`

**Changes:**
- Remove `if metadata_id.startswith("fac_"):` logic
- Read entity type from `profile.entity_type` or file path pattern
- Store entity type in orchestrator from profile, not inference

#### 3.3 Remove Faction-Specific Field Mappings
**File:** `forge_core/orchestrator.py` → `_run_completeness_validator()`

**Changes:**
- Remove hardcoded mappings: `first_missions` → `/essence/gm_guidance/first_missions`
- Use `profile.completeness.min_items` directly (already has full pointers)
- Remove fallback to `config.thresholds.factions`
- Fail if profile doesn't provide completeness config

#### 3.4 Remove Faction-Specific Prompts
**File:** `forge_core/orchestrator.py` → `_run_spark_igniter()`

**Changes:**
- Remove hardcoded "faction" references in prompts
- Load prompts from profile or use generic templates
- Make prompts dataset-agnostic

#### 3.5 Update Validator Signatures
**Files:** All validators in `agents/validators/` and `forge_core/validators/`

**New Signature Pattern:**
```python
def validate(
    candidate: Dict[str, Any],
    ctx: ValidationContext,  # File path, data root, registries, resolver
    *,
    profile: ProfileConfig,
    mode: str
) -> Dict[str, Any]:
```

**Create ValidationContext:**
```python
@dataclass
class ValidationContext:
    file_path: str
    data_root: str
    registries: Dict[str, Any]  # Loaded registry data
    schema_resolver: SchemaResolver
    entity_type: str
```

**Dependencies:** Milestone 1, Milestone 2

**Testing:**
- ✅ Faction files still validate correctly
- ✅ Can create species profile and validate species files
- ✅ No hardcoded paths in codebase
- ✅ Profile provides all dataset-specific config

**Estimated Effort:** 8-10 hours

---

## 📋 Milestone 4: Registry Delta Stage

**Status:** 🟢 BATCH SAFETY - Required before large batches

**Problem:** No mechanism to handle new tags/URIDs discovered during batch runs. Risk of LLMs editing master registries.

**Solution:** Add explicit registry delta stage that collects unknown entities and outputs proposals.

### Implementation Steps

#### 4.1 Create Registry Delta Collector
**File:** `forge_core/registry/delta_collector.py`

**Responsibilities:**
- Track unknown tags during validation
- Track unknown URIDs (species, planets, etc.)
- Collect proposed new entries with metadata
- Output delta file at end of run

**Output Format:**
```json
{
  "run_id": "...",
  "timestamp": "...",
  "proposed_tags": [
    {
      "urid": "tag_new_tag",
      "namespace": "tag_trait_",
      "proposed_by": "file_path",
      "status": "PROPOSED"
    }
  ],
  "proposed_urids": [
    {
      "urid": "species_new_species",
      "kind": "species",
      "proposed_by": "file_path",
      "status": "PROPOSED"
    }
  ]
}
```

#### 4.2 Integrate Delta Collection into Orchestrator
**File:** `forge_core/orchestrator.py`

**Changes:**
- Initialize `DeltaCollector` in orchestrator
- Pass collector to validators via `ValidationContext`
- Validators report unknown entities to collector
- At end of run, write delta file to run directory

#### 4.3 Create Registry Delta Validator
**File:** `forge_core/registry/delta_validator.py`

**Responsibilities:**
- Dedupe proposed entries
- Normalize naming
- Check for collisions with existing registries
- Mark entries as `PROPOSED` (never auto-accept)

#### 4.4 Add Delta Stage to Pipeline
**File:** `forge_core/orchestrator.py`

**Changes:**
- After Step 1 (Gold baseline), run delta collection
- Output `registry_delta.json` to run directory
- Document delta file in run manifest

**Dependencies:** Milestone 3 (validators need to report unknown entities)

**Testing:**
- ✅ Unknown tags collected during validation
- ✅ Delta file created with proposals
- ✅ No master registry edits during run
- ✅ Delta file format is valid and auditable

**Estimated Effort:** 4-5 hours

---

## 📋 Milestone 5: Resolve loc_* Ownership Policy

**Status:** 🟡 BLOCKING DECISION - Required before large batches

**Problem:** Policy says `loc_*` = owned, but data uses `loc_coruscant` as global. This will cause cross-faction contamination.

**Solution:** Make explicit decision and update all relevant code.

### Decision Required

**Option A (Recommended):**
- Global planets: `pla_coruscant`
- Owned locations: `loc_black_sun_counting_room`
- HQ references owned `loc_*`, which can reference `pla_*`

**Option B:**
- Make `loc_*` global
- Introduce `site_*` or `facloc_*` for owned locations

### Implementation Steps (Assuming Option A)

#### 5.1 Update Profile Ownership Policy
**File:** `forge_core/profiles/faction_core.profile.yml`

**Add:**
```yaml
ownership:
  owned_kinds:
    loc_: "locations"  # Owned locations
    feat_: "feats"
    npc_: "npcs"
  global_kinds:
    - pla_  # Planets (global)
    - tag_  # Tags (global)
    - species_  # Species (global)
```

#### 5.2 Update URID Classifier
**File:** `forge_core/migration/deterministic_migration.py`

**Changes:**
- Update `classify_urid()` to recognize `pla_*` as global
- Keep `loc_*` as owned
- Update path resolution logic

#### 5.3 Update Reference Validator
**File:** `forge_core/validators/urid_validator.py`

**Changes:**
- Validate `pla_*` references point to global registry
- Validate `loc_*` references point to owned paths
- Update error messages

#### 5.4 Migration Script (Optional)
**File:** `scripts/migrate_locations.py`

**If needed:** Script to migrate existing `loc_coruscant` → `pla_coruscant` and update references.

**Dependencies:** Milestone 2 (profile ownership config)

**Testing:**
- ✅ `pla_*` URIDs resolve to global paths
- ✅ `loc_*` URIDs resolve to owned paths
- ✅ HQ references work correctly
- ✅ No cross-faction contamination

**Estimated Effort:** 3-4 hours (plus migration if needed)

---

## 📋 Milestone 6: Step 0→1→2→3 Pipeline Restructure

**Status:** 🟢 FINAL POLISH - Perfect file pipeline

**Problem:** Current pipeline mixes structure/reference/completeness issues. Need clear sequencing.

**Solution:** Restructure orchestrator to follow explicit Step 0→1→2→3 sequence.

### Implementation Steps

#### 6.1 Create Pipeline State Machine
**File:** `forge_core/orchestrator.py`

**New Method:** `_run_perfect_file_pipeline()`

**Structure:**
```python
def _run_perfect_file_pipeline(self, candidate: Dict, file_id: str) -> Tuple[Dict, bool]:
    # Step 0: Deterministic Truth
    if not self._step_0_deterministic_truth(candidate):
        return candidate, False
    
    # Step 1: Gold Baseline
    candidate, gold_ok = self._step_1_gold_baseline(candidate)
    if not gold_ok:
        return candidate, False
    
    # Step 2: Platinum Content Fill
    candidate, platinum_ok = self._step_2_platinum_fill(candidate)
    if not platinum_ok:
        return candidate, False
    
    # Step 3: Platinum Gate
    return self._step_3_platinum_gate(candidate)
```

#### 6.2 Implement Step 0: Deterministic Truth
**Method:** `_step_0_deterministic_truth()`

**Actions:**
- Load schema resolver
- Load required registries
- Run deterministic validators (schema, lexicon, URID, references)
- Route findings by domain
- **FAIL FAST** if infrastructure issues (missing schema ref, etc.)
- **NO LLMs** in this step

**Exit Condition:** All STRUCTURE and REFERENCE blockers = 0 (deterministic only)

#### 6.3 Implement Step 1: Gold Baseline
**Method:** `_step_1_gold_baseline()`

**Actions:**
- Run deterministic migration (resolve `refs_created`, create owned stubs)
- **Structural Loop:** Gaugewright ↔ Blacksmith until STRUCTURE = 0
- **Reference Loop:** Deterministic checks + Alchemist until REFERENCE = 0
- Run Gold Gate validation

**Exit Condition:** Gold gate passes (no `_legacy`, refs resolved, schema clean)

#### 6.4 Implement Step 2: Platinum Content Fill
**Method:** `_step_2_platinum_fill()`

**Actions:**
- Run Completeness validator (platinum thresholds)
- Bundle COMPLETENESS → Genesis_Smith (bounded iterations)
- Run Narrative validator
- Bundle NARRATIVE → Runesmith / Canticle (bounded iterations)
- Optional Bard polish (non-blocking)

**Exit Condition:** Completeness thresholds met, narrative majors = 0

#### 6.5 Implement Step 3: Platinum Gate
**Method:** `_step_3_platinum_gate()`

**Actions:**
- Verify Gold gate still passes
- Verify completeness thresholds met
- Verify narrative majors = 0
- Verify UI assets present (if required by profile)
- Generate final artifacts

**Exit Condition:** All gates pass → Platinum-perfect file

#### 6.6 Update Main Orchestrator Flow
**File:** `forge_core/orchestrator.py` → `run_file()`

**Changes:**
- Replace current `_run_tempering()` with `_run_perfect_file_pipeline()`
- Keep `_run_inscription()` for narrative-only passes
- Update iteration logic to respect step boundaries

**Dependencies:** All previous milestones

**Testing:**
- ✅ Step 0 fails fast on infrastructure issues
- ✅ Step 1 produces Gold-perfect files
- ✅ Step 2 fills content without breaking structure
- ✅ Step 3 gates correctly
- ✅ Clean domain progression in run manifests

**Estimated Effort:** 6-8 hours

---

## 📊 Implementation Order & Dependencies

```
Milestone 1 (Schema Resolver)
    ↓
Milestone 2 (Profile Contract)
    ↓
Milestone 3 (Remove Hardcoded Assumptions)
    ↓
Milestone 4 (Registry Delta) ──┐
    ↓                            │
Milestone 5 (loc_* Policy) ─────┤
    ↓                            │
Milestone 6 (Pipeline Restructure) ← All dependencies
```

**Critical Path:** 1 → 2 → 3 → 6 (core functionality)
**Parallel Work:** 4 and 5 can be done in parallel after 3

---

## 🧪 Testing Strategy

### Unit Tests
- Schema resolver resolves all `$ref` locally
- Profile validation catches missing fields
- Validators work with any profile
- Delta collector tracks unknown entities

### Integration Tests
- Faction file → Gold → Platinum (existing workflow)
- Species file → Gold → Platinum (new dataset)
- Batch run produces delta files
- No hardcoded assumptions in logs

### Regression Tests
- Existing faction files still validate
- Existing profiles still work
- No performance degradation

---

## 📝 Migration Notes

### Backward Compatibility
- Existing profiles continue to work (with warnings)
- Legacy `thresholds.factions` fallback removed in Milestone 3
- Old schema paths still resolve (via resolver map)

### Breaking Changes
- **Milestone 3:** Removes hardcoded fallbacks (profiles must be complete)
- **Milestone 5:** Changes `loc_*` ownership (may require data migration)
- **Milestone 6:** Restructures pipeline flow (different iteration behavior)

---

## 🎯 Success Criteria

1. ✅ **Schema resolver works offline** - No network calls, all `$ref` resolve
2. ✅ **Profile is complete contract** - No hardcoded assumptions remain
3. ✅ **System is dataset-agnostic** - Can validate factions, species, items with profile swap
4. ✅ **Registry deltas are auditable** - No master registry edits during runs
5. ✅ **Pipeline is sequenced** - Step 0→1→2→3 produces perfect files
6. ✅ **O(1) runtime** - Orchestration logic doesn't change with dataset

---

## ⚠️ Risks & Mitigations

### Risk 1: Profile Migration Complexity
**Mitigation:** Provide migration script, keep backward compatibility during transition

### Risk 2: Schema Ref Map Maintenance
**Mitigation:** Auto-discover schema dependencies, validate ref map completeness

### Risk 3: Performance Impact
**Mitigation:** Cache schema store, lazy-load registries, benchmark before/after

---

## 📅 Estimated Timeline

- **Milestone 1:** 4-6 hours (1 day)
- **Milestone 2:** 3-4 hours (0.5 days)
- **Milestone 3:** 8-10 hours (1.5 days)
- **Milestone 4:** 4-5 hours (0.5 days)
- **Milestone 5:** 3-4 hours (0.5 days)
- **Milestone 6:** 6-8 hours (1 day)

**Total:** ~30-40 hours (4-5 days of focused work)

**With testing and iteration:** ~1-2 weeks

---

## 🚀 Quick Start: Fix Current Blocker

To unblock platinum promotion **right now**, implement just Milestone 1:

1. Create `forge_core/schema/schema_resolver.py`
2. Update profile with `ref_map`
3. Update Gaugewright to use resolver
4. Test: STRUCTURE blocker should be resolved

This is the **minimum viable fix** to continue platinum work while planning the full refactor.

---

## ❓ Questions for Clarification

1. **loc_* Policy:** Confirm Option A (pla_* global, loc_* owned) is preferred?
2. **Profile Migration:** Should we support legacy profiles during transition, or hard break?
3. **Schema Discovery:** Should resolver auto-discover schema dependencies, or require explicit ref_map?
4. **Registry Delta:** Should deltas be auto-accepted for certain kinds (e.g., owned entities), or always require review?

---

**Next Action:** Start with Milestone 1 to fix the immediate STRUCTURE blocker, then proceed through milestones in order.
