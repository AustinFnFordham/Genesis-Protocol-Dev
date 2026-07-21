# Platinum Promotion Implementation

## Overview

This document describes the implementation of `promote --to platinum` which runs the full "perfect file" pipeline.

---

## Command

```bash
python forge.py promote --path <file> --to platinum [--expand] [--enable-synergy] [--max-iterations N]
```

---

## Workflow

### For Platinum Promotion:

1. **Orchestrator Loop** (if `--to platinum`)
   - Runs full repair loop in wip mode
   - Phases: Scaffold → Migration → Structural (Blacksmith) → Reference (Alchemist) → Completeness (Genesis) → Narrative (Runesmith/Canticle)
   - Spark Igniter only if `--expand` or greenfield
   - Foreman final audit included in orchestrator

2. **Deterministic Migration**
   - Clears `refs_created`
   - Creates owned stubs under strict paths

3. **Gold Validation**
   - Validates in gold mode (all validators)

4. **Gold Gate**
   - Enforces all gold requirements

5. **Status Update**
   - Sets `metadata.status: platinum`

### For Gold Promotion:

1. **Deterministic Migration**
   - Clears `refs_created`
   - Creates owned stubs

2. **Gold Validation**
   - Validates in gold mode

3. **Gold Gate**
   - Enforces all gold requirements

4. **Status Update**
   - Sets `metadata.status: gold`

**Note:** Gold promotion does NOT run orchestrator loop (structural correctness only, not narrative polish)

---

## What Makes a "Perfect" File

### Gold-Perfect (Structurally Perfect)
- ✅ Schema clean
- ✅ `_legacy` gone
- ✅ `refs_created` empty
- ✅ All tags exist
- ✅ All URIDs resolve, with ownership rules enforced
- ✅ No global auto-creation

### Platinum-Perfect (Human Perfect)
- ✅ Gold, plus:
- ✅ Canticle passes (tone/specificity/clarity)
- ✅ Runesmith polish done
- ✅ Semantic names / tidy stubs / conventions honored
- ✅ Optional Bard suggestions (non-blocking)
- ✅ Foreman final audit passed

---

## Implementation Status

### ✅ Completed
- `promote --to gold` command
- `promote --to platinum` command (calls orchestrator)
- Orchestrator integration
- Gold Gate evaluation
- Manifest generation

### 📝 Specification
- Full pipeline specification documented in `docs/contracts/perfect_file_pipeline.md`

---

## Usage Examples

### Promote to Gold (Structural Correctness Only)
```bash
python forge.py promote --path data/wip/factions/core/fac_black_sun.yml --to gold
```

### Promote to Platinum (Gold + Narrative Polish)
```bash
python forge.py promote --path data/wip/factions/core/fac_black_sun.yml --to platinum
```

### Promote to Platinum with Expansion
```bash
python forge.py promote --path data/wip/factions/core/fac_black_sun.yml --to platinum --expand
```

---

## Key Differences

| Feature | Gold | Platinum |
|---------|------|----------|
| Orchestrator Loop | ❌ No | ✅ Yes |
| Narrative Polish | ❌ No | ✅ Yes |
| Foreman Audit | ❌ No | ✅ Yes (in orchestrator) |
| Structural Correctness | ✅ Yes | ✅ Yes |
| Gold Gate | ✅ Yes | ✅ Yes |

---

## Notes

- **Gold is "correct," not "beautiful"** - it focuses on structural correctness
- **Platinum is "perfect"** - it includes narrative polish and human readability
- Orchestrator loop is only run for platinum promotion
- Gold promotion is faster (no LLM calls for narrative polish)

