# Gold Promotion Implementation Status

## ✅ Completed

### 1. Path Consistency Fix
- ✅ Fixed all path examples to use `/data/<mode>/factions/<owner_id>/<type_dir>/<urid>.yml`
- ✅ Updated `GOLD_PROMOTION_IMPLEMENTATION_PLAN.md`
- ✅ Updated `docs/contracts/gold_promotion_requirements.md`

### 2. Gold Gate Module
- ✅ Created `forge_core/gates/gold_gate.py`
- ✅ Implements all 6 rules from requirements doc
- ✅ Returns `GoldGateResult` with pass/fail, reasons, blockers, artifacts

### 3. Schema Validator Update
- ✅ `additionalProperties` violations now BLOCKER in all modes

### 4. Lexicon Validator Mode-Aware
- ✅ Added `mode` parameter to `validate()` and `validate_lexicon()`
- ✅ LEX_004 (unknown tags) now BLOCKER in gold mode, MAJOR in wip mode
- ✅ Updated all calls in `forge.py` to pass mode parameter

### 5. Baseline Validation
- ✅ Ran `validate --mode gold` on `fac_black_sun.yml`
- ✅ Results: 3 blockers, 3 majors
  - Blockers: missing slug (normalization issue), _legacy present, lint error
  - Majors: 3 LEX_004 unknown tags (now should be BLOCKER after fix)

---

## ⚠️ Next Steps (In Order)

### Step 1: Verify Lexicon Mode-Aware ✅
- Test that LEX_004 errors are now BLOCKER in gold mode
- Re-run validation on `fac_black_sun.yml`

### Step 2: Add Tests for Lexicon + Legacy Gate
- Create `tests/test_gold_gate.py`
- Test: `_legacy` present + gold mode => FAIL with LEGACY_001
- Test: Unknown tag => WARN in wip, FAIL in gold
- Test with `fac_black_sun.yml` as "punching bag"

### Step 3: Deterministic Migration
- Create `forge_core/migration/deterministic_migration.py`
- Watch it:
  - Create owned stubs under `data/wip/factions/fac_black_sun/...`
  - Reduce `refs_created_count`
  - Still fail gold if any global ref is missing
- This is the compiler behavior we're aiming for

### Step 4: Complete Remaining Steps
- Update reference validators (mode-aware)
- Add promote command
- Complete all red-bar tests

---

## Current Validation Results (fac_black_sun.yml in gold mode)

**Before Lexicon Fix:**
- 3 blockers, 3 majors
- LEX_004 errors were MAJOR (should be BLOCKER)

**After Lexicon Fix (Expected):**
- 6 blockers, 0 majors
- LEX_004 errors now BLOCKER in gold mode

**Blockers:**
1. SCH_001: Missing 'slug' property (normalization issue - should be fixed by normalizer)
2. SCH_002: _legacy block present (expected - needs migration)
3. LINT_001: Unknown root key: _legacy (expected - lint_sop needs mode-aware update)
4. LEX_004: Unknown tag: tag_class_scoundrel (now BLOCKER)
5. LEX_004: Unknown tag: tag_background_criminal (now BLOCKER)
6. LEX_004: Unknown tag: tag_background_noble (now BLOCKER)

---

## Files Modified

- ✅ `forge_core/gates/gold_gate.py` (new)
- ✅ `forge_core/gates/__init__.py` (new)
- ✅ `forge_core/validators/schema_validator.py`
- ✅ `forge_core/validators/lexicon_validator.py`
- ✅ `forge.py`
- ✅ `GOLD_PROMOTION_IMPLEMENTATION_PLAN.md`
- ✅ `docs/contracts/gold_promotion_requirements.md`

