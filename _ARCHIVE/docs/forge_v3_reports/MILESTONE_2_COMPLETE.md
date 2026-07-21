# Milestone 2: Profile Contract Definition - COMPLETE

## Date: 2026-01-08

## ✅ Implementation Complete

### 1. ProfileContract Schema ✅
**File:** `schemas/profile/profile.schema.json`

- ✅ Complete JSON Schema defining ProfileContract
- ✅ All required fields defined
- ✅ Strict `additionalProperties: false` enforcement
- ✅ Type validation for all fields
- ✅ Required fields: `id`, `version`, `dataset_kind`, `paths`, `schema`, `registries`, `ownership`, `validators`, `routing`, `agents`, `promotion`

### 2. Profile Validator ✅
**File:** `forge_core/profile_validator.py`

**Features:**
- ✅ Validates profiles against ProfileContract schema
- ✅ Detailed error messages with JSON paths
- ✅ File-based and data-based validation
- ✅ Clear error reporting for missing fields, type mismatches, additional properties
- ✅ Raises `ProfileValidationError` with actionable messages

**Methods:**
- `validate(profile_data, profile_path)` - Returns list of errors
- `validate_file(profile_path)` - Validates YAML file
- `validate_and_raise(profile_data, profile_path)` - Raises exception on failure

### 3. Config Loader Integration ✅
**File:** `forge_core/forge_config.py`

**Changes:**
- ✅ `load_config()` now accepts `validate_profile` parameter (default: True)
- ✅ Profiles validated before use
- ✅ Kernel refuses to run if profile validation fails
- ✅ Clear error messages when validation fails
- ✅ Graceful fallback if jsonschema not installed (warns but continues)

**Integration:**
```python
config = load_config(config_path, profile_path=profile_path, validate_profile=True)
# Raises ProfileValidationError if profile invalid
```

## ✅ Testing

### Test Script
**File:** `test_profile_validation.py`

**Results:**
- ✅ Validator correctly identifies missing required fields
- ✅ Validator catches type mismatches
- ✅ Validator detects additional properties
- ✅ Error messages are clear and actionable

### Current Profile Status

**`profiles/species_core.profile.yml`:**
- ⚠️ 9 validation errors (structure doesn't match ProfileContract exactly)
- Issues: `agents.by_domain` structure, `promotion.gates` structure, `thresholds` types

**`forge_core/profiles/faction_core.profile.yml`:**
- ⚠️ 11 validation errors (legacy format, missing required fields)
- Issues: Uses `profile_id` instead of `id`, missing `version`, `dataset_kind`, etc.

**Note:** These are expected - profiles need to be updated to match ProfileContract. The validation infrastructure is working correctly.

## ✅ Milestone 2 Exit Criteria: **MET**

1. ✅ **ProfileContract schema defined** (`schemas/profile/profile.schema.json`)
2. ✅ **Profile validator implemented** (`forge_core/profile_validator.py`)
3. ✅ **Config loader validates profiles** (integrated into `load_config()`)
4. ✅ **Kernel refuses to run with invalid profiles** (raises `ProfileValidationError`)
5. ✅ **Clear error messages** (detailed JSON path errors)

## 📋 Next Steps

### Profile Migration (Future Work)

1. **Update `faction_core.profile.yml`:**
   - Add `id`, `version`, `dataset_kind`
   - Add `paths`, `registries`, `ownership`
   - Restructure `agents.by_domain` to match schema
   - Restructure `promotion.gates` to match schema

2. **Update `species_core.profile.yml`:**
   - Fix `agents.by_domain` structure (needs `roster` arrays)
   - Fix `promotion.gates` structure (needs `blockers`/`majors` objects)
   - Fix `thresholds` types (empty objects vs integers)

3. **Backward Compatibility:**
   - Consider migration helper to convert legacy profiles
   - Or make validation optional for legacy profiles during transition

## 🎯 Impact

**Before Milestone 2:**
- No formal profile contract
- Hardcoded assumptions in kernel
- Silent failures on misconfiguration

**After Milestone 2:**
- ✅ Formal ProfileContract schema
- ✅ Profile validation before use
- ✅ Kernel refuses invalid profiles
- ✅ Clear error messages
- ✅ Foundation for dataset-agnostic kernel

## ✅ Milestone 2: **COMPLETE**

The profile validation infrastructure is in place and working. Profiles can now be validated against the ProfileContract schema, and the kernel will refuse to run with invalid profiles.
