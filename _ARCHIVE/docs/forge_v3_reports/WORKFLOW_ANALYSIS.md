# Forge V3 Workflow Analysis & Dependency Tree

**Date:** 2026-01-04  
**Purpose:** Comprehensive review of agentic workflow, dependency mapping, and improvement opportunities

---

## 1. Dependency Tree

### Core Entry Points
```
forge.py (CLI)
├── cmd_forge() → forge_core/orchestrator.py::run_forge()
├── cmd_validate() → forge_core/validators/* (direct)
├── cmd_platinum() → forge_core/orchestrator.py::run_platinum_loop()
└── cmd_apply_patch() → forge_core/patch_engine.py::apply_patch_to_file()
```

### Orchestrator Flow (Main Workflow)
```
ForgeOrchestrator
├── run_file()
│   ├── _run_scaffold_validation()
│   │   └── forge_core/scaffolder.py
│   │       ├── derive_owner_id()
│   │       ├── ensure_owned_dirs()
│   │       └── check_generic_hq_poison()
│   │
│   ├── _run_migration_validation()
│   │   └── forge_core/migration.py::migrate_legacy_to_core()
│   │
│   ├── _run_tempering() [ITERATIVE]
│   │   ├── _normalize() → forge_core/normalization.py
│   │   ├── _migrate_legacy() → forge_core/migration.py
│   │   ├── _run_completeness_validator()
│   │   │   └── agents/validators/completeness_validator.py
│   │   ├── _run_gaugewright()
│   │   │   └── agents/validators/gaugewright.py
│   │   ├── route_findings() → forge_core/finding_router.py
│   │   ├── build_bundles() → forge_core/bundler.py
│   │   ├── _call_blacksmith() [STRUCTURE bundles]
│   │   │   └── forge_core/local_llm_adapter.py::OllamaAdapter
│   │   ├── _call_genesis() [COMPLETENESS bundles]
│   │   │   └── forge_core/local_llm_adapter.py::OllamaAdapter
│   │   └── _apply_patches() → forge_core/patching.py
│   │
│   ├── _run_inscription() [ITERATIVE]
│   │   └── (TODO: Canticle/Runesmith calls)
│   │
│   └── _run_spark() [OPTIONAL]
│       └── (Placeholder)
│
└── run_platinum_loop() [GRAPH-CLOSED]
    ├── BFS traversal of URID references
    ├── For each file: orchestrator.run_file()
    └── Graph closure validation
```

### Agent Dispatcher (Legacy/Alternative Path)
```
agent_dispatcher.py
├── dispatch_findings()
│   ├── group_findings_by_agent() [CODE-BASED ROUTING]
│   │   └── FINDING_ROUTING dict (code prefix → AgentRole)
│   ├── call_agent()
│   │   ├── load_agent_prompt()
│   │   ├── OllamaAdapter.generate()
│   │   └── write_agent_report()
│   └── (Returns DispatchSummary)
│
└── ⚠️ ISSUE: Uses old code-based routing, not finding_router.py
```

### Validators
```
forge_core/validators/
├── urid_validator.py → validate_urid()
├── schema_validator.py → validate_schema()
├── lexicon_validator.py → validate_lexicon()
├── legacy_validator.py → validate_no_legacy()
└── (others: atomic, refs, synergy, soul, etc.)

agents/validators/
├── completeness_validator.py → validate_completeness()
└── gaugewright.py → validate_schema()
```

### Patch Engine
```
forge_core/patching.py
├── canonicalize_patch_path()
├── sanitize_patch_ops()
├── apply_patches_safely()
│   ├── jsonpatch.apply()
│   └── Transactional rollback on error
└── dedupe_and_sort_ops()
```

### Configuration
```
forge_core/forge_config.py
├── load_config() → forge.yml + profile YAML
├── ForgeConfig (dataclass)
│   ├── agents: Dict[str, AgentConfig]
│   ├── phases: Dict[str, PhaseConfig]
│   ├── profile: ProfileConfig
│   └── routing: RoutingConfig
└── Deep-merge profile overlays
```

### LLM Adapter
```
forge_core/local_llm_adapter.py
├── LocalLLMAdapter (ABC)
├── OllamaAdapter
│   ├── generate() → HTTP POST to localhost:11434
│   ├── _parse_json_patch() → Extract patch ops
│   └── Retry logic + timeout handling
└── StubLLMAdapter (for testing)
```

---

## 2. Workflow Analysis

### Current Workflow (Orchestrator Path)

#### Phase 1: SCAFFOLD
- **Purpose:** Validate ownership and directory structure
- **Dependencies:** `scaffolder.py`
- **Output:** Owner ID, directory structure validated
- **Gate:** Must pass to continue

#### Phase 2: MIGRATION
- **Purpose:** Deterministic legacy field migration
- **Dependencies:** `migration.py`
- **Output:** Migrated candidate (no _legacy blocks)
- **Gate:** Always passes (deterministic)

#### Phase 3: TEMPERING (Iterative)
- **Purpose:** Structural repair + content fill
- **Flow:**
  1. Normalize fields (lists, strings, objects)
  2. Migrate legacy (if any remain)
  3. Validate:
     - CompletenessValidator (Python-based)
     - Gaugewright (Schema + ID validation)
  4. Route findings → domains (STRUCTURE/REFERENCE/COMPLETENESS)
  5. Build bundles (group by domain)
  6. Dispatch agents:
     - STRUCTURE → Blacksmith
     - REFERENCE → Alchemist (TODO: not implemented)
     - COMPLETENESS → Genesis_Smith
  7. Apply patches (with guardrails)
  8. Re-validate
  9. Gate check: Exit when STRUCTURE + REFERENCE blockers/majors == 0
- **Max Iterations:** 6 (configurable)
- **Stall Detection:** Exits after 2 iterations with no progress

#### Phase 4: INSCRIPTION (Iterative)
- **Purpose:** Narrative polish
- **Status:** ⚠️ Placeholder (not implemented)
- **Max Iterations:** 2

#### Phase 5: SPARK (Optional)
- **Purpose:** Creative suggestions
- **Status:** ⚠️ Placeholder (not implemented)

### Alternative Workflow (Platinum Loop)

#### Graph-Closed Validation
- **Purpose:** Validate root file + ALL referenced URIDs recursively
- **Flow:**
  1. BFS traversal starting from root file
  2. For each file:
     - Create stub if missing
     - Run orchestrator.run_file() (full repair)
     - Collect URIDs from repaired data
     - Enqueue referenced files
  3. Continue until queue empty or max iterations
  4. Final validation: Zero blockers/majors + zero unresolved URIDs
- **Gate:** Platinum = pass + zero blockers + zero unresolved URIDs

---

## 3. Improvement Opportunities

### 🔴 Critical Issues

#### 1. **Dual Routing Systems**
**Problem:** Two separate routing mechanisms exist:
- `finding_router.py` + `bundler.py` (used by orchestrator)
- `agent_dispatcher.py::FINDING_ROUTING` (code-based, legacy)

**Impact:** Inconsistency, maintenance burden, potential routing mismatches

**Recommendation:**
- Deprecate `agent_dispatcher.py::FINDING_ROUTING`
- Update `agent_dispatcher.py::dispatch_findings()` to use `finding_router.py` + `bundler.py`
- Consolidate routing logic in one place

**Files to Update:**
- `forge_core/agent_dispatcher.py::dispatch_findings()` → Use `route_findings()` + `build_bundles()`

#### 2. **Platinum Loop Not Using Orchestrator**
**Problem:** `run_platinum_loop()` in `orchestrator.py` calls `orchestrator.run_file()` but then re-validates manually instead of using orchestrator's internal state.

**Impact:** Duplicate validation logic, findings not extracted from orchestrator's report

**Recommendation:**
- Extract findings from `orchestrator.report` instead of re-validating
- Or: Add `get_findings()` method to `ForgeOrchestrator` to expose current state

**Files to Update:**
- `forge_core/orchestrator.py::run_platinum_loop()` → Use orchestrator's report

#### 3. **Alchemist Not Implemented**
**Problem:** REFERENCE bundles are routed to Alchemist, but `_call_alchemist()` doesn't exist in orchestrator.

**Impact:** REFERENCE issues (LEX_, REF_, SYNERGY_) are not repaired

**Recommendation:**
- Implement `_call_alchemist()` similar to `_call_blacksmith()` and `_call_genesis()`
- Or: Route REFERENCE issues to Blacksmith temporarily

**Files to Update:**
- `forge_core/orchestrator.py::_run_tempering()` → Add Alchemist call

### 🟡 Medium Priority

#### 4. **INSCRIPTION Phase Not Implemented**
**Problem:** INSCRIPTION phase is a placeholder with no actual agent calls.

**Impact:** Narrative polish (PROSE_, TONE_, NARRATIVE_) not applied

**Recommendation:**
- Implement Canticle/Runesmith calls similar to TEMPERING agents
- Or: Disable INSCRIPTION phase by default until implemented

**Files to Update:**
- `forge_core/orchestrator.py::_run_inscription()` → Add agent calls

#### 5. **No Error Recovery in Agent Calls**
**Problem:** If an agent call fails (timeout, parse error), the workflow continues with empty patches.

**Impact:** Silent failures, no retry logic, no fallback strategies

**Recommendation:**
- Add retry logic with exponential backoff
- Add fallback to simpler models on failure
- Log failures to report for debugging

**Files to Update:**
- `forge_core/orchestrator.py::_call_blacksmith()`, `_call_genesis()`
- `forge_core/local_llm_adapter.py::OllamaAdapter.generate()`

#### 6. **Patch Application Not Atomic**
**Problem:** Patches are applied one bundle at a time, not as a single transaction.

**Impact:** Partial state if later bundles fail

**Recommendation:**
- Collect all patches from all bundles first
- Apply as single transaction with rollback
- Or: Apply per-bundle but with better error handling

**Files to Update:**
- `forge_core/orchestrator.py::_run_tempering()` → Batch patch application

#### 7. **No Parallel Agent Execution**
**Problem:** Agents are called sequentially even when bundles are independent.

**Impact:** Slower execution, especially for large files with many issues

**Recommendation:**
- Use `concurrent.futures.ThreadPoolExecutor` for parallel agent calls
- Ensure thread-safety in patch application

**Files to Update:**
- `forge_core/orchestrator.py::_run_tempering()` → Parallel dispatch

### 🟢 Low Priority / Enhancements

#### 8. **Stall Detection Too Aggressive**
**Problem:** Exits after 2 stalls, but some issues may require 3-4 iterations.

**Recommendation:**
- Increase `MAX_STALLS` to 3-4
- Or: Make configurable per profile

#### 9. **No Progress Metrics**
**Problem:** No visibility into which agents are most effective, which issues are hardest to fix.

**Recommendation:**
- Add metrics: agent success rate, average iterations per issue type, patch quality scores
- Export to report for analysis

#### 10. **Schema Hardening Not Applied to Validate Command**
**Problem:** `forge.py validate` uses `schema_validator.py` directly, not orchestrator's hardened `_run_gaugewright()`.

**Impact:** Missing SCH_MISSING meta-blockers in validate-only mode

**Recommendation:**
- Extract schema validation logic to shared module
- Use hardened version in both paths

#### 11. **No Caching of Validated Files**
**Problem:** Platinum loop re-validates files even if they haven't changed.

**Impact:** Slower execution for large graphs

**Recommendation:**
- Add file hash tracking in run manifest
- Skip validation if file unchanged since last run

#### 12. **Limited Test Coverage**
**Problem:** No unit tests for orchestrator, routing, bundling.

**Impact:** Risk of regressions, harder to refactor

**Recommendation:**
- Add pytest tests for:
  - `finding_router.py::classify_finding()`
  - `bundler.py::build_bundles()`
  - `orchestrator.py::_run_tempering()` (mocked agents)
  - `patching.py::apply_patches_safely()`

---

## 4. Dependency Issues

### Circular Dependencies
**Status:** ✅ None detected

### Missing Dependencies
1. **jsonpatch** - Used in `patching.py` but may not be installed
   - **Fix:** Add to requirements.txt or handle ImportError gracefully
2. **jsonschema** - Used in `gaugewright.py` but may not be installed
   - **Fix:** Add to requirements.txt or handle ImportError gracefully

### Import Path Issues
1. **agents.validators.completeness_validator** - Imported with sys.path manipulation
   - **Fix:** Use proper package structure or relative imports

---

## 5. Testing Recommendations

### Unit Tests Needed
1. **finding_router.py**
   - Test `classify_finding()` with various finding codes
   - Test domain classification accuracy

2. **bundler.py**
   - Test `build_bundles()` with mixed findings
   - Test expected_ops extraction for COMPLETENESS

3. **patching.py**
   - Test `canonicalize_patch_path()` with various path formats
   - Test `apply_patches_safely()` with invalid patches (rollback)

4. **orchestrator.py**
   - Test `_run_tempering()` with mocked agents
   - Test gate conditions (exit when STRUCTURE cleared)

### Integration Tests Needed
1. **Full Orchestrator Flow**
   - Test SCAFFOLD → MIGRATION → TEMPERING → INSCRIPTION
   - Verify report generation

2. **Platinum Loop**
   - Test graph closure with multiple files
   - Test stub creation
   - Test unresolved URID detection

3. **Agent Calls**
   - Test OllamaAdapter with real Ollama (if available)
   - Test error handling (timeout, parse errors)

### Manual Test Cases
1. **Simple File Repair**
   - Input: File with 1-2 schema issues
   - Expected: Blacksmith fixes, passes gate

2. **Completeness Fill**
   - Input: File missing required array items
   - Expected: Genesis_Smith adds content, passes gate

3. **Graph Closure**
   - Input: Root file with 3-4 referenced URIDs
   - Expected: All files validated, zero blockers

---

## 6. Performance Considerations

### Current Bottlenecks
1. **Sequential Agent Calls** - Agents called one at a time
2. **Re-validation After Each Iteration** - Full validation run each time
3. **No Caching** - Same validations repeated

### Optimization Opportunities
1. **Parallel Agent Execution** - Call independent agents concurrently
2. **Incremental Validation** - Only validate changed paths
3. **Result Caching** - Cache validation results per file hash
4. **Batch Patch Application** - Apply all patches in one transaction

---

## 7. Summary

### Strengths
✅ Well-structured orchestrator with clear phases  
✅ Domain-based routing and bundling  
✅ Guardrails and safety checks in patch application  
✅ Graph-closed validation for platinum  
✅ Offline-only enforcement  

### Weaknesses
❌ Dual routing systems (inconsistency)  
❌ Missing agent implementations (Alchemist, INSCRIPTION)  
❌ No error recovery in agent calls  
❌ Limited test coverage  
❌ Sequential execution (performance)  

### Priority Actions
1. **Fix dual routing** - Consolidate to `finding_router.py` + `bundler.py`
2. **Implement Alchemist** - Complete REFERENCE bundle handling
3. **Add error recovery** - Retry logic and fallbacks
4. **Add unit tests** - Start with routing and bundling
5. **Optimize performance** - Parallel agent execution

---

## 8. Next Steps

1. **Immediate (This Session)**
   - Test workflow with sample file
   - Identify any runtime errors
   - Document findings

2. **Short-term (Next Sprint)**
   - Fix dual routing issue
   - Implement Alchemist
   - Add error recovery

3. **Medium-term (Next Month)**
   - Add unit tests
   - Implement INSCRIPTION phase
   - Optimize performance

4. **Long-term (Future)**
   - Add metrics and analytics
   - Implement caching
   - Add CI/CD integration

