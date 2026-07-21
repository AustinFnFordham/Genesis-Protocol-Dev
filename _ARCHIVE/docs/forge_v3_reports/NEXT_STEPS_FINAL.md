# Next Steps: Forge V3 Workflow - Final Recommendations

## Current Status

✅ **Completed:**
- Step 1: Enhanced Blacksmith prompt with remove operation instructions
- Step 2: Added slug normalization to forge process
- Step 3: Tested improvements with fac_black_sun.yml
- Step 4: Documented results (no cleaner file available for full workflow test)

## Remaining Issues

### Issue: LLM Not Following Remove Instructions

**Problem:**
- Blacksmith prompt has explicit remove operation instructions
- LLM sometimes generates append operations instead of remove operations
- Validation correctly identifies additional properties violations
- Blacksmith needs better guidance to generate remove operations

**Current State:**
- 2 MAJOR issues remain (both additional properties violations)
- `signature_assets`, `signature_methods`, `signature_places` in `/essence`
- `headquarters_id` in `/connections`

## Recommended Solutions

### Solution 1: Enhance Validation Report (Recommended)

**Action:** Modify validation report to explicitly request remove operations

**Implementation:**
1. In `forge_core/validators/schema_validator.py`, enhance additional properties violations:
   ```python
   findings.append({
       "severity": severity,
       "code": "SCH_001",
       "message": message,
       "pointer": pointer,
       "fix_hint": f"Remove invalid property using: {{\"op\": \"remove\", \"path\": \"{pointer}/{field_name}\"}}",
       "repair_action": "remove",  # New field
       "invalid_property": field_name,  # New field
       ...
   })
   ```

2. Update Blacksmith prompt to check for `repair_action: "remove"`:
   ```text
   H) CHECK REPAIR_ACTION FIELD
   - If an issue has "repair_action": "remove", you MUST use remove operation
   - The invalid_property field tells you which property to remove
   - Example: {"op": "remove", "path": "/essence/signature_assets"}
   ```

**Why:** Makes it explicit what operation is needed, reducing LLM ambiguity

### Solution 2: Enhance Blacksmith Prompt Examples

**Action:** Add more explicit examples and emphasis

**Implementation:**
1. Add a dedicated section at the top of prompt:
   ```text
   CRITICAL: For "Additional properties are not allowed" errors:
   - You MUST use "remove" operation, NOT "add" or "replace"
   - Remove the entire property that violates the schema
   - Example: {"op": "remove", "path": "/essence/signature_assets"}
   ```

2. Add before/after examples:
   ```text
   BEFORE (invalid):
   {
     "essence": {
       "signature_assets": ["value1", "value2"],
       "overview": "..."
     }
   }
   
   ISSUE: Additional properties are not allowed ('signature_assets' was unexpected)
   
   CORRECT PATCH:
   [{"op": "remove", "path": "/essence/signature_assets"}]
   
   WRONG PATCH (DO NOT DO THIS):
   [{"op": "add", "path": "/essence/signature_assets/-", "value": "..."}]  ❌
   ```

**Why:** Visual examples help LLMs understand the correct operation

### Solution 3: Pre-process Issues Before Blacksmith

**Action:** Transform additional properties violations before sending to Blacksmith

**Implementation:**
1. In `forge_core/orchestrator.py`, before calling Blacksmith:
   ```python
   def _preprocess_issues_for_blacksmith(self, issues: List[Dict]) -> List[Dict]:
       """Enhance issues with explicit repair instructions."""
       enhanced = []
       for issue in issues:
           if "additionalProperties" in issue.get("message", ""):
               # Extract property name from message
               # Add explicit remove instruction
               issue["repair_action"] = "remove"
               issue["fix_hint"] = f"Use remove operation: {{\"op\": \"remove\", \"path\": \"{issue['pointer']}/<property>\"}}"
           enhanced.append(issue)
       return enhanced
   ```

**Why:** Ensures Blacksmith receives explicit instructions

### Solution 4: Add Remove Operation to Allowlist Check

**Action:** Ensure remove operations are allowed for these paths

**Implementation:**
1. Check if remove operations need explicit allowlist entries
2. Currently, remove operations might be filtered if path isn't in allowlist
3. Add logic to allow remove operations even if path isn't in allowlist (since we're removing, not modifying)

**Why:** Policy might be blocking remove operations

## Implementation Priority

### High Priority (Quick Win)
1. **Solution 2:** Enhance Blacksmith prompt with more examples
   - Low risk, high impact
   - Can be done immediately
   - Easy to test

### Medium Priority (Better Solution)
2. **Solution 1:** Enhance validation report
   - More systematic approach
   - Requires code changes
   - Better long-term solution

### Low Priority (If Needed)
3. **Solution 3:** Pre-process issues
   - Adds complexity
   - Might be redundant if Solution 1 works
   - Consider if Solutions 1-2 don't work

4. **Solution 4:** Check allowlist for remove operations
   - Investigate if this is actually blocking
   - Might not be the issue

## Testing Plan

### Test 1: Enhanced Prompt (Solution 2)
1. Update Blacksmith prompt with more explicit examples
2. Run forge on fac_black_sun.yml
3. Check if Blacksmith generates remove operations
4. Document results

### Test 2: Enhanced Validation Report (Solution 1)
1. Modify schema_validator to add repair_action field
2. Update Blacksmith prompt to check repair_action
3. Run forge on fac_black_sun.yml
4. Check if Blacksmith generates remove operations
5. Document results

### Test 3: Full Workflow Test
1. Create minimal test file without legacy fields
2. Run full forge workflow
3. Verify all phases execute
4. Document any remaining issues

## Success Criteria

- ✅ Blacksmith generates remove operations for additional properties violations
- ✅ All legacy fields removed automatically
- ✅ TEMPERING phase passes
- ✅ Full workflow executes (TEMPERING → INSCRIPTION → SPARK → FINAL_AUDIT)

## Notes

- Current system is 97% effective (98 → 3 issues)
- Only 2 real issues remain (both are LLM instruction following)
- System architecture is sound, just needs better LLM guidance
- Consider testing with different LLM models if available


