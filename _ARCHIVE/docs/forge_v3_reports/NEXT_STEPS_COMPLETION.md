# Next Steps Completion

## Date: 2026-01-06

This document tracks completion of the next steps from pipeline testing.

---

## Step 1: Fix Test File Issues ✅

### 1.1 Add Missing Slug ✅

**File:** `data/wip/factions/core/fac_black_sun.yml`

**Change:**
- Added `slug: black_sun` to metadata section

**Status:** ✅ COMPLETE

### 1.2 Fix Tags ✅

**Verification:**
- Checked all tags in file against `master_tags.yml`
- All tags exist: `tag_criminal_syndicate`, `tag_faction_underworld`, `tag_trait_organized`, `tag_trait_wealthy`, `tag_trait_espionage`, `tag_species_falleen`

**Status:** ✅ VERIFIED (all tags exist in master_tags.yml)

**Note:** If validation still shows unknown tags, it may be a path resolution issue with master_tags.yml location.

---

## Step 2: Test Platinum Promotion ⚠️

### Status: **IN PROGRESS**

**Command:**
```bash
python forge.py promote --path "data/wip/factions/core/fac_black_sun.yml" --to platinum --dry-run --max-iterations 2
```

**Requirements:**
- Ollama running ✅
- LLM models available ✅
- Orchestrator loop execution

**Expected:**
- Orchestrator runs full repair loop
- Migration clears refs_created
- Gold validation passes
- Gold Gate passes
- Status updates to platinum

---

## Step 3: Test Actual Promotion (Non-Dry-Run) ⏳

### Status: **PENDING**

**Prerequisites:**
- Step 1 complete ✅
- Step 2 successful (or at least verified orchestrator works)
- All blockers resolved

**Command:**
```bash
python forge.py promote --path "data/wip/factions/core/fac_black_sun.yml" --to gold
```

**Expected:**
- Migration creates stubs
- File updated (refs_created cleared, _legacy removed)
- `metadata.status` set to `gold`
- Manifest created

---

## Summary

### ✅ Completed
1. Added missing `slug` to metadata
2. Verified all tags exist in master_tags.yml

### ⚠️ In Progress
1. Testing platinum promotion (orchestrator integration)

### ⏳ Pending
1. Test actual promotion (non-dry-run) after all blockers resolved

---

## Next Actions

1. **Verify slug fix:** Re-run gold validation to confirm slug blocker resolved
2. **Test platinum:** Run platinum promotion with more iterations if needed
3. **Resolve remaining blockers:** Fix any remaining schema/validation issues
4. **Test actual promotion:** Run non-dry-run promotion once all blockers resolved

---

## Notes

- Tags are verified to exist in master_tags.yml
- Slug has been added to metadata
- Remaining blockers may be:
  - `_legacy` block (expected - will be removed by migration in non-dry-run)
  - `refs_created` (expected - will be cleared by migration in non-dry-run)
  - Path resolution issues with master_tags.yml

