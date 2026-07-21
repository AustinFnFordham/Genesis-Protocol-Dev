# Platinum Promotion Fixes - Implementation Plan

## Status: In Progress

## Issue 1: Reagent_Inspector False Tag Validation Blockers ✅ FIXED

**Problem:** Reagent_Inspector (LLM agent) was emitting BLOCKER severity for tag existence without access to master_tags.yml, causing false positives.

**Solution:**
1. ✅ Updated `prompts/reagent_inspector.txt` to remove tag existence validation
2. ✅ Added filtering in orchestrator to downgrade tag existence issues from Reagent_Inspector to MINOR
3. ⚠️ **TODO:** Add `_run_lexicon_validator()` method to orchestrator (method call exists but implementation missing)

**Files Modified:**
- `prompts/reagent_inspector.txt` - Updated to not validate tag existence
- `forge_core/orchestrator.py` - Added filtering logic and lexicon validator call

**Remaining Work:**
- Add `_run_lexicon_validator()` method implementation to orchestrator (line ~1017)

---

## Issue 2: Platinum Completeness Thresholds ⏳ TODO

**Problem:** Platinum promotion needs explicit minItems/minLength requirements for completeness validation.

**Required Thresholds (for factions):**
- `gm_guidance.first_missions`: >= 8
- `gm_guidance.hooks`: >= 8
- `gm_guidance.rumors`: >= 8
- `gm_guidance.conflicts`: >= 4
- `culture.customs`: >= 4
- `culture.taboos`: >= 4
- `culture.status_markers`: >= 4
- `tone_levers.temperatures`: present + keys complete
- `relationships[*].mechanical_effect`: present for each relationship
- `ui.icon_path` and `ui.image_path`: non-empty (or explicitly allowed empty in Gold but required in Platinum)

**Files to Modify:**
- `forge_core/validators/completeness_validator.py` - Add Platinum mode thresholds
- Or create `forge_core/validators/platinum_completeness_validator.py`

---

## Issue 3: loc_* Ownership Policy Conflict ⏳ TODO

**Problem:** 
- Policy says: `loc_*` = owned locations (faction-scoped)
- Data uses: `loc_coruscant` as global location

**Options:**
1. **Recommended:** Make planets global: `pla_coruscant`
   - Faction HQ owned: `loc_black_sun_coruscant_counting_room` (owned location)
   - Or use `site_*` for global "Coruscant Underlevels" registry

2. **Alternative:** Keep `loc_*` as global and use different prefix for owned locations (like `facloc_*`)

**Files to Modify:**
- `forge_core/migration/deterministic_migration.py` - Update `classify_urid()` logic
- `docs/contracts/gold_promotion_requirements.md` - Clarify ownership rules
- Update `fac_black_sun.yml` to use correct URID format

---

## Issue 4: Platinum Workflow Structure ⏳ TODO

**Current:** Mixed structure/reference/completeness issues

**Required:** Step 0→1→2→3 structure

### Step 0 - Deterministic Truth (Always First)
- ✅ Deterministic schema validator
- ⚠️ Deterministic lexicon validator (needs implementation in orchestrator)
- ✅ Deterministic URID resolver

### Step 1 - Reach Gold Baseline
- ✅ Scaffold validation/repair
- ✅ Deterministic migration
- ✅ Structural loop (Gaugewright ↔ Blacksmith) until STRUCTURE blockers/majors = 0
- ⚠️ Reference loop (deterministic ref validators + Alchemist) until REFERENCE blockers/majors = 0

### Step 2 - Platinum Content Fill
- ⚠️ Completeness phase (deterministic minItems/minLength checks) → Genesis_Smith
- ⚠️ Narrative phase (Canticle) → Runesmith
- Optional Bard polish (non-blocking)

### Step 3 - Platinum Gate
- ✅ Gold gates pass
- ⚠️ Canticle pass (or narrative majors = 0)
- ⚠️ UI assets non-empty if required by Platinum
- ✅ No _legacy, no refs_created, no unresolved refs

**Files to Modify:**
- `forge_core/orchestrator.py` - Restructure tempering phase to follow Step 0→1→2→3
- `forge_core/gates/platinum_gate.py` - Create new gate module (or extend gold_gate.py)

---

## Immediate Next Steps

1. **Complete Issue 1:** Add `_run_lexicon_validator()` method to orchestrator
2. **Test:** Run platinum promotion on `fac_children_of_the_watch.yml` to verify tag validation fix
3. **Implement Issue 2:** Add Platinum completeness thresholds
4. **Resolve Issue 3:** Fix loc_* ownership policy
5. **Restructure Issue 4:** Update orchestrator workflow

---

## Testing Plan

### Test 1: Tag Validation Fix
```bash
python forge.py promote --path "data/wip/factions/core/fac_children_of_the_watch.yml" --to platinum --max-iterations 2
```
**Expected:** No false tag existence blockers from Reagent_Inspector

### Test 2: Completeness Thresholds
**Expected:** Genesis_Smith receives clear minItems requirements and fills content

### Test 3: loc_* Policy
**Expected:** `loc_coruscant` handled correctly (either as global or migrated to `pla_coruscant`)

---

## Notes

- Gold promotion is working correctly ✅
- Platinum promotion architecture is sound, needs these fixes
- File `fac_children_of_the_watch.yml` is already Gold, good test case
- File `fac_black_sun.yml` needs Gold promotion first, then Platinum
