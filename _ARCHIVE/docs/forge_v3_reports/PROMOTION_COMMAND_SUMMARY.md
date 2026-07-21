# Promotion Command Summary

## Commands

### Gold Promotion (Structural Correctness)
```bash
python forge.py promote --path <file> --to gold [--dry-run] [--json]
```

**What it does:**
- ✅ Runs deterministic migration (clears `refs_created`, creates owned stubs)
- ✅ Validates in gold mode
- ✅ Runs Gold Gate
- ✅ Writes manifest
- ✅ Sets `metadata.status: gold` on success

**What it does NOT do:**
- ❌ Run orchestrator loop (no narrative polish)
- ❌ Call Spark Igniter / Genesis / Runesmith
- ❌ Invent missing global entities
- ❌ Try to "repair until it passes"

**Gold is "correct," not "beautiful."**

---

### Platinum Promotion (Perfect File)
```bash
python forge.py promote --path <file> --to platinum [--expand] [--enable-synergy] [--max-iterations N] [--dry-run] [--json]
```

**What it does:**
1. ✅ **Orchestrator Loop** (full repair in wip mode):
   - Scaffold → Migration → Structural (Blacksmith) → Reference (Alchemist) → Completeness (Genesis) → Narrative (Runesmith/Canticle)
   - Spark Igniter only if `--expand` or greenfield
   - Foreman final audit included

2. ✅ **Deterministic Migration** (clears `refs_created`)

3. ✅ **Gold Validation** (all validators in gold mode)

4. ✅ **Gold Gate** (enforces all requirements)

5. ✅ **Status Update** (sets `metadata.status: platinum`)

**Platinum = Gold + Narrative Polish**

---

## Key Differences

| Feature | Gold | Platinum |
|---------|------|----------|
| Orchestrator Loop | ❌ | ✅ |
| Narrative Polish | ❌ | ✅ |
| Foreman Audit | ❌ | ✅ (in orchestrator) |
| Structural Correctness | ✅ | ✅ |
| Gold Gate | ✅ | ✅ |
| Speed | Fast | Slower (LLM calls) |

---

## What Makes a "Perfect" File

### Gold-Perfect
- Schema clean
- `_legacy` gone
- `refs_created` empty
- All tags exist
- All URIDs resolve
- No global auto-creation

### Platinum-Perfect
- Gold, plus:
- Canticle passes (tone/specificity/clarity)
- Runesmith polish done
- Semantic names / tidy stubs
- Foreman final audit passed

---

## Implementation Status

✅ **COMPLETE**
- Gold promotion command
- Platinum promotion command
- Orchestrator integration
- Gold Gate evaluation
- Manifest generation

**Full specification:** `docs/contracts/perfect_file_pipeline.md`

