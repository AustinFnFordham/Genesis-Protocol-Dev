# Schema Refinement Plan

## Date: 2026-01-08

This document outlines the recommended approach for refining schemas to prevent drift, maintain consistency, and enable global changes across all entity types.

---

## Executive Summary

The current schema structure has **dataset-specific schemas** (faction, species, npc, location, planet, etc.) that reference **common primitives** (URID patterns, atomic mechanics). To prevent drift and enable consistent updates, we need to:

1. **Identify common patterns** that can be extracted to shared schemas
2. **Establish a refactoring strategy** that allows global changes without breaking existing files
3. **Create a migration path** for schema updates
4. **Document the schema hierarchy** and dependencies

---

## Current Schema Structure

### Tier A: Common Contracts (Already Extracted)

These are already shared across all entity types:

- **`schemas/common/common_urid.schema.json`**: URID patterns (`fac_*`, `npc_*`, `loc_*`, `pla_*`, etc.)
- **`schemas/common/common_atomic.schema.json`**: Atomic mechanics (duration, condition, predicate, etc.)
- **`schemas/common/validation_report.schema.json`**: Validation report structure
- **`schemas/common/registry_index.schema.json`**: Registry index structure
- **`schemas/common/master_tags.schema.json`**: Tag lexicon structure
- **`schemas/common/migration_map.schema.json`**: Migration map structure

**Status:** ✅ These are already well-structured and reusable.

### Tier B: Dataset Primaries (Need Review)

These are entity-specific schemas that may share common patterns:

- **`schemas/faction/faction_core.schema.json`**: Faction entities
- **`schemas/species/species_core.schema.json`**: Species entities
- **`schemas/npc/npc_core.schema.json`**: NPC entities
- **`schemas/location/location_core.schema.json`**: Location entities
- **`schemas/planet/planet_core.schema.json`**: Planet entities
- **`schemas/feat/feat_core.schema.json`**: Feat entities
- **`schemas/item/item_core.schema.json`**: Item entities (if exists)
- **`schemas/class/class_core.schema.json`**: Class entities (if exists)

**Status:** ⚠️ These may have duplicate patterns that should be extracted.

### Tier C: Ancillary Entities (Lower Priority)

These are supporting entities that may reference primaries:

- **`schemas/rule/rule_core.schema.json`**: Chaos Engine rules
- **`schemas/synergy/synergy_core.schema.json`**: Synergy definitions
- **`schemas/effect/effect_core.schema.json`**: Effect definitions

**Status:** ⚠️ These are lower priority but should follow the same patterns.

---

## Common Patterns to Extract

### 1. Metadata Block Pattern

**Current State:** Each entity type likely has a `metadata` block with similar fields:
- `id` (URID)
- `name` (string)
- `slug` (string)
- `version` (SemVer)
- `status` (enum: wip, todo, gold, platinum)
- `source_dataset` (string)
- `content_origin` (enum: canon, legends, homebrew)
- `owner_id` (URID, optional)
- `entity_path` (string)

**Recommendation:**
- Create `schemas/common/common_metadata.schema.json`
- Define `metadata_block` as a `$defs` entry
- All entity schemas reference: `"$ref": "https://sw5e-data-hub.local/schemas/common/common_metadata.schema.json#/$defs/metadata_block"`

**Impact:** 
- ✅ Single source of truth for metadata structure
- ✅ Global changes (e.g., add `last_updated` field) affect all entities
- ✅ Consistent validation across all entity types

### 2. Taxonomy Block Pattern

**Current State:** Many entities have a `taxonomy` block with:
- `tags` (array of tag URIDs)
- `categories` (array of strings, optional)
- `keywords` (array of strings, optional)

**Recommendation:**
- Create `schemas/common/common_taxonomy.schema.json`
- Define `taxonomy_block` as a `$defs` entry
- Entity schemas reference it via `$ref`

**Impact:**
- ✅ Consistent tag structure across all entities
- ✅ Global changes to tag requirements affect all entities

### 3. Essence/Soul Block Pattern

**Current State:** Some entities have `essence` (factions, locations) or `soul` (feats) blocks with narrative content:
- `overview` (string)
- `ideology` (string, optional)
- `culture` (string, optional)
- `style_guide` (object with `tone`, `themes`)
- `narrative` (object with `origin_story`, `history`)
- `gm_guidance` (object with `hooks`, `missions`, `rumors`, `conflicts`)

**Recommendation:**
- Create `schemas/common/common_narrative.schema.json`
- Define `essence_block` and `soul_block` as `$defs` entries
- Entity schemas reference the appropriate block

**Impact:**
- ✅ Consistent narrative structure
- ✅ Global changes to narrative requirements (e.g., `minLength` for `overview`) affect all entities

### 4. Structure Block Pattern

**Current State:** Some entities have a `structure` block (factions, organizations) with:
- `ranks` (array of rank objects)
- `hierarchy` (object, optional)
- `roles` (array, optional)

**Recommendation:**
- Create `schemas/common/common_structure.schema.json`
- Define `structure_block` as a `$defs` entry
- Entity schemas that need structure reference it

**Impact:**
- ✅ Consistent structure definitions
- ✅ Global changes to structure requirements affect all entities

### 5. Connections Block Pattern

**Current State:** Many entities have a `connections` block with:
- `allies` (array of URIDs)
- `enemies` (array of URIDs)
- `neutral` (array of URIDs, optional)
- `locations` (array of location URIDs, optional)
- `npcs` (array of NPC URIDs, optional)

**Recommendation:**
- Create `schemas/common/common_connections.schema.json`
- Define `connections_block` as a `$defs` entry
- Entity schemas reference it

**Impact:**
- ✅ Consistent relationship structure
- ✅ Global changes to connection requirements affect all entities

### 6. UI Block Pattern

**Current State:** Many entities have a `ui` block with:
- `color` (string, hex color)
- `icon` (string, icon identifier)
- `banner` (string, image path, optional)
- `description` (string, short description for UI)

**Recommendation:**
- Create `schemas/common/common_ui.schema.json`
- Define `ui_block` as a `$defs` entry
- Entity schemas reference it

**Impact:**
- ✅ Consistent UI metadata structure
- ✅ Global changes to UI requirements affect all entities

---

## Recommended Refactoring Steps

### Phase 1: Extract Common Blocks (Low Risk)

**Goal:** Extract metadata, taxonomy, connections, and UI blocks to common schemas.

**Steps:**
1. **Create common schema files:**
   - `schemas/common/common_metadata.schema.json`
   - `schemas/common/common_taxonomy.schema.json`
   - `schemas/common/common_connections.schema.json`
   - `schemas/common/common_ui.schema.json`

2. **Update entity schemas:**
   - Replace inline `metadata` block with `$ref` to common schema
   - Replace inline `taxonomy` block with `$ref` to common schema
   - Replace inline `connections` block with `$ref` to common schema
   - Replace inline `ui` block with `$ref` to common schema

3. **Test:**
   - Run validation on all existing files
   - Ensure no regressions

**Timeline:** 1-2 days

**Risk:** Low (no semantic changes, only structural)

### Phase 2: Extract Narrative Blocks (Medium Risk)

**Goal:** Extract essence/soul blocks to common schema.

**Steps:**
1. **Create common schema:**
   - `schemas/common/common_narrative.schema.json`
   - Define `essence_block` and `soul_block` as `$defs`

2. **Update entity schemas:**
   - Replace inline `essence` block with `$ref` to `essence_block`
   - Replace inline `soul` block with `$ref` to `soul_block`

3. **Test:**
   - Run validation on all existing files
   - Ensure narrative validation still works

**Timeline:** 2-3 days

**Risk:** Medium (narrative blocks may have entity-specific variations)

### Phase 3: Extract Structure Blocks (Low Risk)

**Goal:** Extract structure blocks to common schema.

**Steps:**
1. **Create common schema:**
   - `schemas/common/common_structure.schema.json`
   - Define `structure_block` as a `$defs` entry

2. **Update entity schemas:**
   - Replace inline `structure` block with `$ref` to common schema

3. **Test:**
   - Run validation on all existing files

**Timeline:** 1-2 days

**Risk:** Low (structure blocks are relatively simple)

### Phase 4: Schema Versioning (High Value)

**Goal:** Add versioning to schemas to enable migration tracking.

**Steps:**
1. **Add version field to all schemas:**
   - Add `"version": "1.0.0"` to schema root
   - Document version in schema comments

2. **Create migration map:**
   - Track schema version changes
   - Document breaking changes

3. **Update SchemaResolver:**
   - Support version-aware resolution
   - Log schema version mismatches

**Timeline:** 2-3 days

**Risk:** Low (additive change)

---

## Global Changes That Become Possible

Once common blocks are extracted, these global changes become trivial:

### 1. Add `last_updated` to Metadata

**Before:** Update 10+ entity schemas individually
**After:** Update `common_metadata.schema.json` once

### 2. Change `status` Enum

**Before:** Update 10+ entity schemas individually
**After:** Update `common_metadata.schema.json` once

### 3. Add `minLength` to `overview` Field

**Before:** Update 5+ entity schemas individually
**After:** Update `common_narrative.schema.json` once

### 4. Add `icon_size` to UI Block

**Before:** Update 10+ entity schemas individually
**After:** Update `common_ui.schema.json` once

### 5. Change Tag Structure

**Before:** Update 10+ entity schemas individually
**After:** Update `common_taxonomy.schema.json` once

---

## Preventing Drift

### 1. Schema Linting

**Recommendation:** Create a schema linter that checks:
- All entity schemas use `$ref` for common blocks (no inline definitions)
- All `$ref` URIs resolve correctly
- No duplicate definitions across schemas

**Implementation:**
```python
# tools/schema_linter.py
def lint_schemas():
    """Check for schema drift and inconsistencies."""
    # 1. Find all entity schemas
    # 2. Check that common blocks use $ref (not inline)
    # 3. Check that $ref URIs resolve
    # 4. Check for duplicate definitions
    # 5. Report violations
```

### 2. Schema Validation Tests

**Recommendation:** Create automated tests that:
- Validate all entity files against their schemas
- Ensure common blocks are used consistently
- Check that schema changes don't break existing files

**Implementation:**
```python
# tests/test_schema_consistency.py
def test_all_entities_use_common_blocks():
    """Ensure all entity schemas reference common blocks."""
    # Check that metadata uses $ref to common_metadata
    # Check that taxonomy uses $ref to common_taxonomy
    # etc.
```

### 3. Schema Documentation

**Recommendation:** Document:
- Which common blocks each entity type uses
- Entity-specific blocks that remain inline
- Migration path for schema updates

**Location:** `docs/schemas/SCHEMA_ARCHITECTURE.md`

---

## Migration Strategy

### For Existing Files

**No changes required** - existing files will continue to validate correctly because:
- `$ref` resolution is backward-compatible
- Schema structure doesn't change (only location)
- Validation logic remains the same

### For New Files

**Use refactored schemas** - new files will automatically use common blocks via `$ref`.

### For Schema Updates

**Process:**
1. Update common schema (e.g., `common_metadata.schema.json`)
2. Run schema linter to check for regressions
3. Run validation tests on all entity files
4. Update documentation
5. Commit changes

---

## Recommended Next Steps

### Immediate (This Week)

1. **Review existing schemas** to identify common patterns
2. **Create common schema files** for metadata, taxonomy, connections, UI
3. **Update one entity schema** (e.g., `faction_core.schema.json`) as proof of concept
4. **Test validation** on existing faction files

### Short Term (Next 2 Weeks)

1. **Complete Phase 1** (extract common blocks)
2. **Create schema linter** to prevent drift
3. **Update all entity schemas** to use common blocks
4. **Document schema architecture**

### Medium Term (Next Month)

1. **Complete Phase 2** (extract narrative blocks)
2. **Complete Phase 3** (extract structure blocks)
3. **Add schema versioning** (Phase 4)
4. **Create migration tooling** for schema updates

---

## Benefits Summary

### Consistency
- ✅ All entities use the same metadata structure
- ✅ All entities use the same taxonomy structure
- ✅ All entities use the same connection structure
- ✅ All entities use the same UI structure

### Maintainability
- ✅ Global changes require updating one file, not 10+
- ✅ Schema drift is prevented by linting
- ✅ Schema updates are tested automatically

### Developer Experience
- ✅ Clear schema hierarchy (common → entity-specific)
- ✅ Easy to understand which blocks are shared
- ✅ Easy to add new entity types (reference common blocks)

### Performance
- ✅ Schema resolution is faster (fewer duplicate definitions)
- ✅ Validation is more consistent (same rules for all entities)

---

## Risks and Mitigations

### Risk 1: Breaking Existing Files

**Mitigation:**
- Use `$ref` (backward-compatible)
- Test all existing files after refactoring
- Incremental rollout (one entity type at a time)

### Risk 2: Entity-Specific Variations

**Mitigation:**
- Common blocks use `additionalProperties: false` only where appropriate
- Entity schemas can extend common blocks with `allOf`
- Document entity-specific requirements

### Risk 3: Schema Resolution Complexity

**Mitigation:**
- Use explicit `ref_map` in profiles (already implemented)
- Test schema resolution in CI
- Document resolution order

---

## Conclusion

Refactoring schemas to extract common blocks is a **high-value, low-risk** change that will:
- Prevent drift across entity types
- Enable global changes with minimal effort
- Improve maintainability and consistency
- Reduce the risk of schema-related bugs

**Recommendation:** Proceed with Phase 1 (extract common blocks) as soon as possible, then iterate on Phases 2-4 based on priorities.
