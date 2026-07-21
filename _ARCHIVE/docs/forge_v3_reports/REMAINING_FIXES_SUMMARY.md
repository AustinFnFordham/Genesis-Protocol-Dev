# Remaining "Will Break Later" Fixes - Summary

## Date: 2026-01-06

This document summarizes fixes for the remaining issues that would cause problems later.

---

## ✅ Issue 1: Scoundrel Rule Trigger Tags Mismatch - FIXED

### Problem
- `trigger_tags` had: `tag_scoundrel`
- `condition.target` had: `tag_class_scoundrel`
- **Mismatch** - trigger system expects same namespace as conditions

### Fix Applied
**File:** `data/wip/factions/core/fac_black_sun.yml`

**Changed:**
```yaml
trigger_tags:
  - tag_faction_black_sun
  - tag_scoundrel  # ❌ Wrong
```

**To:**
```yaml
trigger_tags:
  - tag_faction_black_sun
  - tag_class_scoundrel  # ✅ Matches condition target
```

### Status: **FIXED**

---

## ✅ Issue 2: Background Condition Targets Not Tags - FIXED

### Problem
- Condition targets used: `criminal_background`, `noble_background`
- Trigger tags used: `tag_criminal_background`, `tag_noble_background`
- **Inconsistent** - should use `tag_background_*` format

### Fix Applied
**File:** `data/wip/factions/core/fac_black_sun.yml`

**Changed:**
```yaml
trigger_tags:
  - tag_criminal_background  # ❌ Wrong format
condition:
  target: criminal_background  # ❌ Missing tag_ prefix
```

**To:**
```yaml
trigger_tags:
  - tag_background_criminal  # ✅ Correct format
condition:
  target: tag_background_criminal  # ✅ Correct format
```

**Also fixed:**
- `tag_noble_background` → `tag_background_noble`
- `noble_background` → `tag_background_noble`

### Normalization Function Enhancement
**File:** `forge_core/normalizers.py`

**Added:** Normalization of `trigger_tags` arrays in synergy rules:
```python
# Normalize trigger_tags array
if "trigger_tags" in rule and isinstance(rule["trigger_tags"], list):
    rule["trigger_tags"] = [normalize_synergy_target(tag) for tag in rule["trigger_tags"]]
```

### Status: **FIXED**

---

## ✅ Issue 3: `synergy_engine` Schema Verification - VERIFIED

### Problem
- Concern that `synergy_engine` might not be in schema
- If `additionalProperties: false` is strict, this would fail Gold

### Verification
**File:** `schemas/faction/faction_core.schema.json`

**Found:**
- Line 32-33: `synergy_engine` is explicitly defined in root properties
- Line 639-644: `synergy_engine_block` definition exists
- Schema allows `synergy_engine` at root level ✅

### Status: **VERIFIED** (no changes needed)

---

## ⚠️ Issue 4: `_legacy.refs_created` Work Queue - DOCUMENTED

### Problem
- `_legacy.refs_created` contains a TODO queue of entity IDs
- These need to be resolved before Gold promotion
- Currently: 5 approaches, 5 assets, 2 locations

### Current State
```yaml
_legacy:
  refs_created:
    approaches:
      - approach_black_sun_interstellar_extortion
      - approach_black_sun_pheromone_manipulation
      - approach_black_sun_corporate_sabotage
      - approach_black_sun_political_leverage
      - approach_black_sun_assassination
    assets:
      - asset_black_sun_blackmail_archives
      - asset_black_sun_vigo_spy_network
      - asset_black_sun_forged_chain_codes
      - asset_black_sun_cryoban_security
      - asset_black_sun_guri_replicant_codes
    locations:
      - loc_xizors_palace
      - loc_spice_terminals
```

### Resolution Requirements
**Documented in:** `docs/contracts/gold_promotion_requirements.md`

**Requirements:**
1. All `refs_created` items must be resolved (created as stubs or migrated)
2. `_legacy` block must be removed before Gold promotion
3. Gold promotion gate should enforce: `refs_created_count == 0`

### Status: **DOCUMENTED** (requires migration work)

---

## Files Modified

1. ✅ `data/wip/factions/core/fac_black_sun.yml`
   - Fixed `tag_scoundrel` → `tag_class_scoundrel` in trigger_tags
   - Fixed `tag_criminal_background` → `tag_background_criminal`
   - Fixed `criminal_background` → `tag_background_criminal`
   - Fixed `tag_noble_background` → `tag_background_noble`
   - Fixed `noble_background` → `tag_background_noble`

2. ✅ `forge_core/normalizers.py`
   - Enhanced `normalize_synergy_engine()` to also normalize `trigger_tags` arrays

3. ✅ `docs/contracts/gold_promotion_requirements.md`
   - New file documenting Gold promotion requirements
   - Includes `refs_created` resolution requirements

---

## Testing Checklist

- [x] All trigger_tags match their corresponding condition targets
- [x] All background tags use `tag_background_*` format
- [x] `synergy_engine` verified in schema
- [x] `_legacy.refs_created` requirements documented

---

## Next Steps

1. **Run normalization test:**
   ```bash
   python -c "from forge_core.normalizers import normalize_synergy_engine; import yaml; data = yaml.safe_load(open('data/wip/factions/core/fac_black_sun.yml')); result = normalize_synergy_engine(data); print('Normalized')"
   ```

2. **Verify trigger_tags normalization:**
   - Check that all `trigger_tags` arrays are normalized
   - Verify they match condition targets

3. **Plan `refs_created` resolution:**
   - Decide: Create stubs or migrate to canonical structures?
   - Implement migration agent logic
   - Test stub file creation

---

## Summary

**Fixed:** 3 out of 4 issues
- ✅ Issue 1: Trigger tags mismatch - FIXED
- ✅ Issue 2: Background targets not tags - FIXED
- ✅ Issue 3: synergy_engine schema - VERIFIED
- ⚠️ Issue 4: `_legacy.refs_created` - DOCUMENTED (requires migration work)

**Status:** All immediate fixes complete. `refs_created` resolution is a migration task that requires creating stub files or migrating data.

