# Platinum Fixes Action Plan

## Overview
This document addresses the 6 critical issues identified in the user's feedback to achieve true "Platinum" status.

---

## Issue 1: `_legacy` Still Present ✅ VERIFIED

### Current State
- Schema **explicitly allows** `_legacy` at root (line 38-41 in `faction_core.schema.json`)
- Schema validator **checks for `_legacy` in gold mode** (line 104-114 in `schema_validator.py`)
- File header says "Validated against faction_core.schema.json" but doesn't clarify WIP vs Gold

### Action Items

#### 1.1 Update File Header Comment
**File:** `data/wip/factions/core/fac_black_sun.yml`

**Change:**
```yaml
# ============================================================================
# fac_black_sun.yml - v4.2 Container Structure
# Migrated from legacy format. Validated against faction_core.schema.json
# ============================================================================
```

**To:**
```yaml
# ============================================================================
# fac_black_sun.yml - v4.2 Container Structure
# Migrated from legacy format. WIP-validated against faction_core.schema.json
# NOTE: _legacy block present - must be resolved before Gold promotion
# ============================================================================
```

#### 1.2 Verify Gold Mode Validation
**Test Command:**
```bash
python forge.py validate --path "data/wip/factions/core/fac_black_sun.yml" --profile faction_core --mode gold --json
```

**Expected:** Should show `_legacy` as BLOCKER

**Status:** ✅ Schema validator already enforces this (line 104-114)

---

## Issue 2: `headquarters_id` vs HQ Object Pattern ⚠️ SCHEMA MISMATCH

### Current State
- **File uses:** `connections.headquarters_id: loc_coruscant` (simple string)
- **Schema expects:** `connections.headquarters: { id, name }` (object) - line 493-498 in schema

### Decision Required
**Option A: Use `headquarters_id` (simple, stable)**
- Pros: Simpler, less migration work
- Cons: Schema mismatch needs fixing

**Option B: Use `headquarters: { id, name }` (more descriptive)**
- Pros: Matches schema, more structured
- Cons: Requires migration of existing files

### Recommendation: **Option A** (simpler)
- Update schema to allow `headquarters_id` as alternative
- Keep `headquarters` object as optional/alternative
- Less migration work for 500+ files

### Action Items

#### 2.1 Update Schema
**File:** `schemas/faction/faction_core.schema.json`

**Change `connections_block` definition:**
```json
"headquarters": {
    "type": "object",
    "additionalProperties": false,
    "required": ["id", "name"]
}
```

**To:**
```json
"headquarters": {
    "oneOf": [
        {
            "type": "string",
            "description": "Location URID reference (simple form)"
        },
        {
            "type": "object",
            "additionalProperties": false,
            "required": ["id", "name"],
            "description": "Location object with id and name (descriptive form)"
        }
    ]
},
"headquarters_id": {
    "type": "string",
    "description": "DEPRECATED: Use headquarters as string instead"
}
```

**OR** (simpler approach):
```json
"headquarters_id": {
    "$ref": "https://sw5e-data-hub.local/schemas/common/common_urid.schema.json#/$defs/location_id"
},
"headquarters": {
    "type": "object",
    "additionalProperties": false,
    "required": ["id", "name"],
    "description": "Alternative to headquarters_id - provides both id and name"
}
```

#### 2.2 Update File to Match Decision
If choosing Option A (headquarters_id):
- No change needed - file already uses this
- Just need schema update

If choosing Option B (headquarters object):
- Update file to use object form
- Create migration script for other files

---

## Issue 3: Tag Taxonomy Consistency ✅ VERIFIABLE

### Current State
- File uses: `tag_era_rebellion`, `tag_align_dark`, `tag_species_falleen`
- Lexicon validator exists and checks against `master_tags.yml`

### Action Items

#### 3.1 Run Lexicon Validator
**Test Command:**
```bash
python forge.py validate --path "data/wip/factions/core/fac_black_sun.yml" --profile faction_core --mode wip
```

**Check for:**
- LEX_004 errors (unknown tags)
- LEX_002 errors (missing tag_ prefix)
- LEX_001 errors (should use canonical form)

#### 3.2 Verify Tags in Master Registry
**File:** `../SW5e_Data_Hub/data/tags/master_tags.yml` (or `data/tags/master_tags.yml`)

**Verify these tags exist:**
- `tag_align_dark`
- `tag_era_rebellion`
- `tag_species_falleen`
- `tag_criminal_syndicate`
- `tag_faction_underworld`
- `tag_trait_organized`
- `tag_trait_wealthy`
- `tag_trait_espionage`

**If missing:** Add to master_tags.yml or fix file to use correct tags

---

## Issue 4: Feature Choice Shape (`feat_id` Field Name) ✅ VERIFIED

### Current State
- **File uses:** `feature_choices: [{ feat_id: "feat_..." }]`
- **Schema expects:** `feat_id` field (line 257-262 in schema)

### Status: ✅ **MATCHES SCHEMA**

**Verification:**
- Schema line 257: `"required": ["feat_id"]`
- Schema line 260: `"feat_id": { "$ref": "...feat_id" }`
- File uses: `feat_id: feat_black_sun_associate_quiet_ear`

**Action:** None needed - already correct

---

## Issue 5: Synergy Engine References Inconsistency ⚠️ NEEDS NORMALIZATION

### Current State
Mixed naming in `synergy_engine.rules[*].condition.conditions[*].target`:
- `target: tag_faction_black_sun` ✅ (tag_ prefix)
- `target: class_operative` ❌ (no tag_ prefix)
- `target: species_falleen` / `tag_species_falleen` ❓ (inconsistent)
- `target: tag_scoundrel` ❓ (is this a class tag?)

### Problem
- No consistent rule for when to use `tag_` prefix
- Mixed namespaces (class, species, faction)
- Alchemist should normalize these but needs clear rules

### Decision Required

**Option A: Everything in condition targets must be tags (tag_*)**
- Pros: Consistent, all go through lexicon validator
- Cons: Need to ensure all references have tag_ prefix

**Option B: Condition type declares namespace**
- Pros: More flexible, allows non-tag references
- Cons: More complex validation logic

### Recommendation: **Option A** (everything is tags)

### Action Items

#### 5.1 Define Normalization Rules
**Create:** `docs/contracts/synergy_condition_targets_contract.md`

**Rules:**
1. All `condition.conditions[*].target` values MUST use `tag_` prefix
2. Class references: `class_operative` → `tag_class_operative`
3. Species references: `species_falleen` → `tag_species_falleen`
4. Faction references: Already correct (`tag_faction_black_sun`)
5. Background references: `background_criminal` → `tag_background_criminal`

#### 5.2 Update Alchemist Prompt
**File:** `prompts/alchemist.txt`

**Add section:**
```
SYNERGY CONDITION TARGET NORMALIZATION:
- All condition.conditions[*].target values MUST have tag_ prefix
- Convert class_* → tag_class_*
- Convert species_* → tag_species_*
- Convert background_* → tag_background_*
- Faction targets already use tag_faction_* (keep as-is)
- If target already has tag_ prefix, verify it exists in lexicon
```

#### 5.3 Create Normalization Function
**File:** `forge_core/normalizers.py`

**Add:**
```python
def normalize_synergy_target(target: str) -> str:
    """
    Normalize synergy condition target to tag_* format.
    
    Rules:
    - If already tag_*, return as-is
    - If class_*, convert to tag_class_*
    - If species_*, convert to tag_species_*
    - If background_*, convert to tag_background_*
    - If faction_*, convert to tag_faction_*
    """
    if target.startswith("tag_"):
        return target
    
    # Map namespace prefixes
    namespace_map = {
        "class_": "tag_class_",
        "species_": "tag_species_",
        "background_": "tag_background_",
        "faction_": "tag_faction_",
    }
    
    for prefix, tag_prefix in namespace_map.items():
        if target.startswith(prefix):
            return target.replace(prefix, tag_prefix, 1)
    
    # Unknown format - assume it needs tag_ prefix
    return f"tag_{target}"
```

#### 5.4 Update File
**File:** `data/wip/factions/core/fac_black_sun.yml`

**Find and fix:**
- `target: class_operative` → `target: tag_class_operative`
- `target: species_falleen` → `target: tag_species_falleen`
- Any other non-tag_ prefixed targets

---

## Issue 6: Mechanical Effect Targets Registry ⚠️ NEEDS VALIDATION

### Current State
Examples in file:
- `target: skill_persuasion`
- `target: attack_rolls`
- `target: save_charisma`

### Problem
- No registry/enum validation for these identifiers
- Schema references `common_atomic.schema.json#/$defs/effect_object` but need to verify it constrains targets

### Action Items

#### 6.1 Check Schema Definition
**File:** `schemas/common/common_atomic.schema.json`

**Verify:**
- Does `effect_object` define allowed `target` values?
- Is there an enum or pattern for valid targets?

#### 6.2 Create Registry (if needed)
**File:** `data/registries/mechanical_effects.yml` (or similar)

**Structure:**
```yaml
mechanical_effect_targets:
  skills:
    - skill_persuasion
    - skill_insight
    - skill_deception
    # ... etc
  rolls:
    - attack_rolls
    - damage_rolls
    - save_rolls
  saves:
    - save_charisma
    - save_wisdom
    - save_dexterity
    # ... etc
```

#### 6.3 Add Validator (if needed)
**File:** `forge_core/validators/mechanical_effect_validator.py`

**Purpose:** Validate `mechanical_effect.target` against registry

#### 6.4 Update Schema (if needed)
**File:** `schemas/common/common_atomic.schema.json`

**Add enum or pattern to `effect_object.target`**

---

## Implementation Priority

### Phase 1: Quick Wins (Do First)
1. ✅ Issue 1: Update file header comment
2. ✅ Issue 4: Verify feat_id (already correct)
3. ✅ Issue 3: Run lexicon validator and fix any issues

### Phase 2: Schema/Standardization (Do Next)
4. ⚠️ Issue 2: Decide on headquarters pattern and update schema
5. ⚠️ Issue 5: Define synergy target normalization rules and update file

### Phase 3: Registry/Validation (Do Last)
6. ⚠️ Issue 6: Check mechanical effect schema and add validation if needed

---

## Testing Checklist

After fixes, verify:
- [ ] `_legacy` shows as BLOCKER in gold mode
- [ ] `headquarters_id` or `headquarters` matches schema
- [ ] All tags pass lexicon validator (0 LEX_004 errors)
- [ ] All synergy condition targets use `tag_` prefix
- [ ] Mechanical effect targets are validated (or documented as acceptable)

---

## Files to Modify

1. `data/wip/factions/core/fac_black_sun.yml` - Update header, fix synergy targets
2. `schemas/faction/faction_core.schema.json` - Fix headquarters definition
3. `prompts/alchemist.txt` - Add synergy normalization rules
4. `forge_core/normalizers.py` - Add normalize_synergy_target function
5. `schemas/common/common_atomic.schema.json` - Verify/update effect_object.target
6. `docs/contracts/synergy_condition_targets_contract.md` - New file documenting rules

