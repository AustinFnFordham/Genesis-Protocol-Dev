# Atomic Checklist Contract (Project-Wide)
# Version: 1.1.0
# Scope: Structural and type correctness for all atomic data objects.

checks:
  - id: ATOMIC_001
    intent: Prevent ambiguous condition grouping.
    pass_condition: "If `conditions` reference has > 1 item, `logic` field (AND/OR) must be present."
    fail_message_template: "Condition group with {count} items missing explicit 'logic' operator."
    severity_in_wip: MAJOR
    severity_in_gold: BLOCKER
    autofix_allowed: false
    suggested_fix: "Add `logic: AND` (default) or `logic: OR`."

  - id: ATOMIC_002
    intent: Ensure numeric values are processed as numbers.
    pass_condition: "Fields expecting integers/floats must not be strings."
    fail_message_template: "Field '{field}' has type '{type}', expected '{expected}'."
    severity_in_wip: MAJOR
    severity_in_gold: BLOCKER
    autofix_allowed: true
    suggested_fix: "Remove quotes from numeric value."

  - id: ATOMIC_003
    intent: Enforce strictly defined effect scopes.
    pass_condition: "Field `target_scope` must be one of: `self`, `target`, `area`, `world`."
    fail_message_template: "Invalid scope '{value}'. Must be one of: self, target, area, world."
    severity_in_wip: MAJOR
    severity_in_gold: BLOCKER
    autofix_allowed: false
    suggested_fix: "Change to nearest valid scope."

  - id: ATOMIC_004
    intent: Enforce valid stacking types.
    pass_condition: "Field `bonus_type` must be a valid bonus type enum."
    fail_message_template: "Invalid bonus_type '{value}'."
    severity_in_wip: MAJOR
    severity_in_gold: BLOCKER
    autofix_allowed: false
    suggested_fix: "Use 'untyped' or standard 5e bonus type."

  - id: ATOMIC_005
    intent: Effects must point to a real thing.
    pass_condition: "Target URID must exist in registry or be a recognized keyword."
    fail_message_template: "Effect target '{target}' not found in registry/enums."
    severity_in_wip: MINOR
    severity_in_gold: MAJOR
    autofix_allowed: false
    suggested_fix: "Check spelling or add `stat_` prefix."

  - id: ATOMIC_006
    intent: Prevent duration ambiguity.
    pass_condition: "If `duration.value` > 0, `duration.unit` must be present."
    fail_message_template: "Duration value {value} missing unit."
    severity_in_wip: MAJOR
    severity_in_gold: BLOCKER
    autofix_allowed: true
    suggested_fix: "Add `unit: rounds`."

  - id: ATOMIC_007
    intent: Prevent nesting errors in simple lists.
    pass_condition: "Lists like `trigger_tags` must contain strings, not objects/lists."
    fail_message_template: "Array '{field}' contains non-string item at index {index}."
    severity_in_wip: MAJOR
    severity_in_gold: BLOCKER
    autofix_allowed: true
    suggested_fix: "Flatten list or extract object to ID."

  - id: ATOMIC_008
    intent: Enforce regex conformity for system IDs.
    pass_condition: "ID fields must match `^[a-z_][a-z0-9_]*$`."
    fail_message_template: "ID '{value}' contains invalid characters."
    severity_in_wip: MAJOR
    severity_in_gold: BLOCKER
    autofix_allowed: false
    suggested_fix: "Snake_case the ID and remove special chars."
