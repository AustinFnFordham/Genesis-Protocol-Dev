# Agent Implementation Status

**Date:** 2026-01-04  
**Issue:** 10 prompt files exist, but only 5 agents are fully implemented in the workflow

---

## Agent Categorization

### ✅ Fully Implemented (5 agents)

These agents are called in the orchestrator and generate patches:

1. **Blacksmith** ✅
   - **Location:** `forge_core/orchestrator.py::_call_blacksmith()`
   - **Phase:** TEMPERING
   - **Role:** Structural repair (schema violations)
   - **Status:** Fully functional

2. **Alchemist** ✅
   - **Location:** `forge_core/orchestrator.py::_call_alchemist()`
   - **Phase:** TEMPERING
   - **Role:** Reference/synergy fixes
   - **Status:** Fully functional

3. **Genesis_Smith** ✅
   - **Location:** `forge_core/orchestrator.py::_call_genesis()`
   - **Phase:** TEMPERING
   - **Role:** Content generation (minItems/minLength)
   - **Status:** Fully functional

4. **Canticle_Examiner** ✅
   - **Location:** `forge_core/orchestrator.py::_run_canticle_examiner()`
   - **Phase:** INSCRIPTION
   - **Role:** Narrative quality validator (triggers Runesmith)
   - **Status:** Fully functional (validator, not patch-generator)

5. **Runesmith** ✅
   - **Location:** `forge_core/orchestrator.py::_call_runesmith()`
   - **Phase:** INSCRIPTION
   - **Role:** Narrative prose polish
   - **Status:** Fully functional

---

### ❌ Not Implemented (3 agents)

These agents have prompts but are not called in the workflow:

6. **Bard** ❌
   - **Prompt:** `prompts/bard.txt` (exists)
   - **Expected Phase:** INSCRIPTION (after Runesmith, non-blocking)
   - **Role:** Narrative enhancement (flavor/soul improvements)
   - **Status:** **NOT IMPLEMENTED**
   - **Issue:** Listed in `agent_dispatcher.py` but never called in orchestrator
   - **Should be:** Called after Runesmith in INSCRIPTION phase as non-blocking enhancement

7. **Spark_Igniter** ❌
   - **Prompt:** `prompts/spark_igniter.txt` (exists)
   - **Expected Phase:** SPARK (optional, after INSCRIPTION)
   - **Role:** Creative expansion suggestions
   - **Status:** **PLACEHOLDER ONLY**
   - **Location:** `forge_core/orchestrator.py::_run_spark()` (line 444-450)
   - **Issue:** Just prints message, doesn't actually call LLM
   - **Should be:** Generate creative suggestions for expanding content

8. **Foreman** ❌
   - **Prompt:** `prompts/foreman.txt` (exists)
   - **Expected Phase:** Final audit (after all phases)
   - **Role:** Final quality gate validation
   - **Status:** **NOT IMPLEMENTED**
   - **Issue:** Mentioned in docstring but never called
   - **Location:** `report_builder.py::record_foreman_reaudit()` exists but never used
   - **Should be:** Final validation before marking as PLATINUM

---

### ⚠️ Validators (Not Patch-Generating Agents)

These are validators that check for issues but don't generate patches:

9. **Gaugewright** ⚠️
   - **Prompt:** `prompts/gaugewright.txt` (exists)
   - **Location:** `forge_core/orchestrator.py::_run_gaugewright()`
   - **Phase:** TEMPERING (validation step)
   - **Role:** Schema validator (JSON Schema + ID checks)
   - **Status:** ✅ Used as validator
   - **Note:** This is a **validator**, not a patch-generating agent. It finds issues that Blacksmith fixes.

10. **Reagent_Inspector** ⚠️
    - **Prompt:** `prompts/reagent_inspector.txt` (exists)
    - **Location:** **NOT CALLED IN ORCHESTRATOR**
    - **Expected Phase:** TEMPERING (validation step)
    - **Role:** Reference/synergy validator
    - **Status:** ❌ **NOT USED**
    - **Issue:** Prompt exists but validator is never called
    - **Note:** Should validate references before Alchemist fixes them
    - **Should be:** Called in TEMPERING phase to validate references (similar to Gaugewright)

---

## Summary

### Current State
- **5 agents fully implemented:** Blacksmith, Alchemist, Genesis_Smith, Canticle_Examiner, Runesmith
- **1 validator used:** Gaugewright
- **1 validator unused:** Reagent_Inspector
- **3 agents missing:** Bard, Spark_Igniter, Foreman

### Expected vs Actual

| Agent | Type | Status | Phase | Notes |
|-------|------|--------|-------|-------|
| **Gaugewright** | Validator | ✅ Used | TEMPERING | Finds issues for Blacksmith |
| **Reagent_Inspector** | Validator | ❌ Not Used | TEMPERING | Should validate references |
| **Blacksmith** | Agent | ✅ Implemented | TEMPERING | Fixes structure |
| **Alchemist** | Agent | ✅ Implemented | TEMPERING | Fixes references |
| **Genesis_Smith** | Agent | ✅ Implemented | TEMPERING | Fills content |
| **Canticle_Examiner** | Validator | ✅ Used | INSCRIPTION | Finds narrative issues |
| **Runesmith** | Agent | ✅ Implemented | INSCRIPTION | Polishes prose |
| **Bard** | Agent | ❌ Missing | INSCRIPTION | Should enhance flavor |
| **Spark_Igniter** | Agent | ❌ Placeholder | SPARK | Should generate suggestions |
| **Foreman** | Agent | ❌ Missing | Final | Should do final audit |

---

## Missing Implementations

### 1. Reagent_Inspector (Validator)

**Should be called in TEMPERING phase:**
- After Gaugewright validation
- Before routing findings
- Validates all references (tags, synergies, IDs)
- Issues become REFERENCE bundles for Alchemist

**Implementation needed:**
```python
def _run_reagent_inspector(self, candidate: Dict, phase: str, iteration: int) -> Dict:
    """Run Reagent_Inspector to validate references."""
    # Similar to _run_gaugewright() but for references
    # Call LLM with reagent_inspector.txt prompt
    # Return findings in REFERENCE domain
```

---

### 2. Bard (Agent)

**Should be called in INSCRIPTION phase:**
- After Runesmith (if INSCRIPTION passes)
- Non-blocking (INFO/WARN only)
- Enhances flavor text and narrative quality
- Optional suggestions, doesn't block pipeline

**Implementation needed:**
```python
def _call_bard(self, candidate: Dict, phase: str, iteration: int) -> List:
    """Call Bard for non-blocking narrative enhancements."""
    # Similar to _call_runesmith() but non-blocking
    # Returns suggestions + optional patches
    # Only applies if user opts in or quality is very low
```

**Integration point:** After INSCRIPTION gate passes, before SPARK

---

### 3. Spark_Igniter (Agent)

**Should be called in SPARK phase:**
- After INSCRIPTION passes
- Optional (if enabled)
- Generates creative expansion suggestions
- Returns YAML suggestions (not patches)

**Implementation needed:**
```python
def _run_spark(self, candidate: Dict, file_id: str) -> None:
    """SPARK phase: Generate creative suggestions."""
    # Call Spark_Igniter LLM
    # Generate expansion suggestions
    # Save to report (not applied as patches)
```

**Current status:** Placeholder only (line 444-450)

---

### 4. Foreman (Agent)

**Should be called at end:**
- After all phases complete
- Final quality gate
- Validates everything is resolved
- Gives final PASS/FAIL verdict

**Implementation needed:**
```python
def _run_foreman_audit(self, candidate: Dict, file_id: str) -> Tuple[Dict, bool]:
    """Foreman final audit."""
    # Call Foreman LLM with full candidate + report
    # Get final verdict
    # Check for any missed issues
    # Return (candidate, passed)
```

**Integration point:** After SPARK (if enabled), before `_finalize_success()`

---

## Recommended Implementation Order

1. **Reagent_Inspector** (High Priority)
   - Completes validation suite
   - Enables proper REFERENCE domain routing
   - Should be quick to implement

2. **Foreman** (High Priority)
   - Final quality gate
   - Catches missed issues
   - Important for PLATINUM status

3. **Bard** (Medium Priority)
   - Non-blocking enhancement
   - Improves quality but not critical
   - Can be added incrementally

4. **Spark_Igniter** (Low Priority)
   - Optional creative suggestions
   - Nice-to-have feature
   - Lowest priority

---

## Workflow Gaps

### Current Workflow
```
SCAFFOLD → MIGRATION → TEMPERING → INSCRIPTION → SPARK → SUCCESS
                                    │
                                    ├─ Gaugewright (validator) ✅
                                    ├─ Blacksmith ✅
                                    ├─ Alchemist ✅
                                    ├─ Genesis_Smith ✅
                                    │
                                    └─ Canticle_Examiner (validator) ✅
                                       └─ Runesmith ✅
```

### Complete Workflow (Should Be)
```
SCAFFOLD → MIGRATION → TEMPERING → INSCRIPTION → SPARK → FOREMAN → SUCCESS
                                    │
                                    ├─ Gaugewright (validator) ✅
                                    ├─ Reagent_Inspector (validator) ❌ MISSING
                                    ├─ Blacksmith ✅
                                    ├─ Alchemist ✅
                                    ├─ Genesis_Smith ✅
                                    │
                                    └─ Canticle_Examiner (validator) ✅
                                       └─ Runesmith ✅
                                          └─ Bard ❌ MISSING
                                             └─ Spark_Igniter ❌ PLACEHOLDER
                                                └─ Foreman ❌ MISSING
```

---

## Action Items

1. ✅ **Document missing agents** (this file)
2. ⚠️ **Implement Reagent_Inspector** - Add to TEMPERING validation
3. ⚠️ **Implement Bard** - Add to INSCRIPTION phase (non-blocking)
4. ⚠️ **Implement Spark_Igniter** - Complete SPARK phase
5. ⚠️ **Implement Foreman** - Add final audit gate

---

**Last Updated:** 2026-01-04

