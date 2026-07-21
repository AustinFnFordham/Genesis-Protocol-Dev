# Forge V3 Improvements Summary

## Date: 2026-01-06

This document summarizes the improvements made to enhance Blacksmith's ability to handle `additionalProperties` violations and improve the overall workflow.

---

## 1. Enhanced Blacksmith Prompt ✅

**File:** `prompts/blacksmith.txt`

**Changes:**
- Added comprehensive section `G) REMOVE ADDITIONAL PROPERTIES (CRITICAL)` with:
  - Explicit instructions to use "remove" operation for `additionalProperties` violations
  - Clear examples of correct vs. wrong patch operations
  - Before/after examples showing the expected behavior
  - Emphasis on checking for `repair_action: "remove"` in issue objects

**Key Additions:**
```text
G) REMOVE ADDITIONAL PROPERTIES (CRITICAL)
- For "Additional properties are not allowed" errors:
  - You MUST use "remove" operation, NOT "add" or "replace"
  - Check for "repair_action": "remove" in the issue object
  - Extract property names from the error message
  - Generate one "remove" operation per invalid property
```

**Impact:**
- Provides clear, explicit guidance to the LLM on handling `additionalProperties` violations
- Includes multiple examples to reinforce correct behavior
- Emphasizes the critical nature of using "remove" operations

---

## 2. Enhanced Validation Report ✅

**Files Modified:**
- `forge_core/validators/schema_validator.py`
- `agents/validators/gaugewright.py`

### 2.1 Schema Validator Enhancement

**File:** `forge_core/validators/schema_validator.py`

**Changes:**
- Added property extraction from error messages using regex
- Added `repair_action: "remove"` field to findings for `additionalProperties` errors
- Added `invalid_properties` list containing extracted property names
- Enhanced `fix_hint` to include explicit remove operation examples

**Code Changes:**
```python
if "additionalProperties" in validator_type:
    import re
    all_props = re.findall(r"'([^']+)'", message)
    if all_props:
        repair_action = "remove"
        remove_ops = []
        for prop in all_props:
            prop_path = f"{pointer}/{prop}" if pointer else f"/{prop}"
            remove_ops.append(f'{{"op": "remove", "path": "{prop_path}"}}')
        fix_hint = f"Remove invalid properties using remove operations: {', '.join(remove_ops)}"
        
        finding["repair_action"] = repair_action
        finding["invalid_properties"] = all_props
```

### 2.2 Gaugewright Enhancement

**File:** `agents/validators/gaugewright.py`

**Changes:**
- Added `additionalProperties` error type handling in `_validate_schema`
- Extracts property names from error messages
- Builds explicit remove operation examples in `repair_hint`
- Enhances `Issue.to_dict()` to include `repair_action` and `invalid_properties` for `additionalProperties` errors

**Code Changes:**
```python
elif error_type == "additionalProperties":
    import re
    all_props = re.findall(r"'([^']+)'", message)
    if all_props:
        # Build explicit remove operations
        remove_ops = []
        for prop in all_props:
            prop_path = f"{path}/{prop}" if path else f"/{prop}"
            remove_ops.append(f'{{"op": "remove", "path": "{prop_path}"}}')
        repair_hint = f"Remove invalid properties using remove operations: {', '.join(remove_ops)}"
        expected = f"No additional properties allowed. Remove: {', '.join(all_props)}"
        actual = f"Found additional properties: {', '.join(all_props)}"

# Enhance to_dict for additionalProperties
if error_type == "additionalProperties":
    all_props = re.findall(r"'([^']+)'", message)
    if all_props:
        issue.repair_action = "remove"
        issue.invalid_properties = all_props
        # Override to_dict to include these fields
        original_to_dict = issue.to_dict
        def enhanced_to_dict():
            d = original_to_dict()
            d["repair_action"] = "remove"
            d["invalid_properties"] = all_props
            return d
        issue.to_dict = enhanced_to_dict
```

**Impact:**
- Validation reports now explicitly request "remove" operations for `additionalProperties` violations
- Property names are extracted and provided to agents
- Fix hints include ready-to-use patch operation examples
- Agents receive structured guidance on what to remove

---

## 3. Test File Creation ✅

**File:** `data/wip/factions/core/fac_test_minimal.yml`

**Purpose:**
- Created a minimal, clean test file to verify the full workflow
- Contains all required fields with valid data
- No legacy fields or `additionalProperties` violations
- Useful for testing the complete pipeline without legacy migration complexity

**Status:**
- File created successfully
- Can be used for future workflow validation

---

## Expected Behavior After Improvements

### Before:
1. Blacksmith would generate `test` operations (filtered out)
2. Blacksmith would try to `add` or `replace` instead of `remove`
3. Validation reports didn't explicitly request remove operations
4. Property names weren't extracted from error messages

### After:
1. Validation reports extract property names and include `repair_action: "remove"`
2. Validation reports include explicit remove operation examples in `fix_hint`
3. Blacksmith prompt has comprehensive guidance on handling `additionalProperties`
4. Blacksmith receives structured data indicating what needs to be removed

### Example Validation Report Output:
```json
{
  "severity": "MAJOR",
  "code": "SCH_001",
  "message": "Additional properties are not allowed ('signature_assets', 'signature_methods', 'signature_places' were unexpected)",
  "pointer": "/essence",
  "fix_hint": "Remove invalid properties using remove operations: {\"op\": \"remove\", \"path\": \"/essence/signature_assets\"}, {\"op\": \"remove\", \"path\": \"/essence/signature_methods\"}, {\"op\": \"remove\", \"path\": \"/essence/signature_places\"}",
  "repair_action": "remove",
  "invalid_properties": ["signature_assets", "signature_methods", "signature_places"]
}
```

---

## Testing Results

### Test 1: fac_black_sun.yml
- **Status:** Still showing some issues with Blacksmith generating `test` operations
- **Progress:** Blacksmith now produces some valid remove operations (3 patches applied in iteration 2)
- **Remaining Issues:** 
  - LLM still occasionally generates `test` operations (being filtered)
  - Some patch operations fail due to non-existent paths

### Test 2: fac_test_minimal.yml
- **Status:** Different issues (REFERENCE issues, not `additionalProperties`)
- **Note:** This file doesn't have `additionalProperties` violations, so it tests other parts of the workflow

---

## Next Steps

1. **Monitor LLM Behavior:**
   - Continue testing with `fac_black_sun.yml` to see if Blacksmith improves with the enhanced prompts
   - Consider adding more examples to the prompt if needed

2. **Verify Property Extraction:**
   - Test that property names are correctly extracted from various error message formats
   - Ensure regex handles edge cases (single property, multiple properties, etc.)

3. **Enhance Error Handling:**
   - Add validation to ensure remove operations target existing paths
   - Improve patch application error messages

4. **Documentation:**
   - Update workflow documentation to reflect these improvements
   - Document the `repair_action` and `invalid_properties` fields in validation reports

---

## Files Modified

1. `prompts/blacksmith.txt` - Enhanced with explicit remove operation guidance
2. `forge_core/validators/schema_validator.py` - Added property extraction and repair_action
3. `agents/validators/gaugewright.py` - Added additionalProperties handling and enhanced to_dict
4. `data/wip/factions/core/fac_test_minimal.yml` - Created test file

---

## Conclusion

These improvements provide:
- **Better Guidance:** Enhanced prompts with explicit examples
- **Structured Data:** Validation reports now include `repair_action` and `invalid_properties`
- **Clear Instructions:** Fix hints include ready-to-use patch operations

The improvements create a more deterministic path for handling `additionalProperties` violations, though LLM behavior may still vary. The system now provides maximum guidance to help the LLM generate correct operations.

