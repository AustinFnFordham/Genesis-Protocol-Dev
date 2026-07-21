# Phase 2 & 3 Test Results

## Date: 2026-01-08

## ✅ Phase 2 Test Results

### Test Command
```bash
python forge.py promote \
  --path "data/wip/factions/core/fac_children_of_the_watch.yml" \
  --to platinum \
  --max-iterations 1 \
  --dry-run
```

### Results
- ✅ **Schema resolver working**: "✅ Schema resolver: 3 schemas loaded, 0 cache hits"
- ✅ **STRUCTURE blockers: 0** (Phase 1 still working)
- ✅ **ValidationContext created** (no errors)
- ✅ **TagIndex loaded** (no errors)
- ✅ **DeltaCollector initialized** (no errors)
- ✅ **No syntax or runtime errors**

### Delta File
- No delta file written (expected - no unknown tags to propose)
- DeltaCollector is working, just had nothing to propose

## ✅ Phase 2 Status: **PASSED**

All Phase 2 components working:
1. ✅ ValidationContext created and used
2. ✅ TagIndex provides O(1) tag checks
3. ✅ DeltaCollector ready to emit proposals
4. ✅ No regressions from Phase 1

## 📋 Phase 3: Proof of Agnosticism

### Created: `profiles/species_core.profile.yml`

**ProfileContract-compliant profile** with:
- `id`, `version`, `dataset_kind` (required)
- `paths.roots`, `paths.output_root` (required)
- `schema.primary_path`, `schema.primary_id`, `schema.ref_map` (required)
- `registries.tags`, `registries.globals` (required)
- `ownership.owned_kinds`, `ownership.global_kinds` (required)
- `validators.enabled`, `validators.mode_severity` (required)
- `routing.domain_routing` (required)
- `agents.by_domain` (required)
- `promotion.gates`, `promotion.artifacts` (required)

### Next Steps for Phase 3 Proof

1. **Create test species file** (if none exists)
   - `data/wip/species/species_human.yml`
   - `data/wip/species/species_wookiee.yml`

2. **Test with species profile:**
   ```bash
   python forge.py promote \
     --path "data/wip/species/species_human.yml" \
     --profile species_core \
     --to gold \
     --dry-run
   ```

3. **Verify:**
   - Kernel unchanged
   - Behavior changes purely by profile swap
   - Schema validation uses species schema
   - Tag validation uses same TagIndex
   - DeltaCollector works the same

## 🎯 Phase 3 Exit Criteria

- ✅ ProfileContract-compliant `species_core.profile.yml` created
- ⏳ Test with species file (pending test file)
- ⏳ Confirm kernel unchanged, behavior changes by profile
