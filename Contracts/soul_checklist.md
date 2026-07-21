# SOUL Checklist Contract (Project-Wide)
# Version: 1.1.0
# Scope: Global narrative hygiene enforcement. No style policing.

checks:
  - id: SOUL_001
    intent: Ensure core narrative identity exists.
    pass_condition: "Field `essence.summary` (or equivalent) is present and non-empty."
    fail_message_template: "Missing required narrative summary in {path}."
    severity_in_wip: BLOCKER
    severity_in_gold: BLOCKER
    autofix_allowed: false
    suggested_fix: "Write a brief definition of the entity."

  - id: SOUL_002
    intent: Prevent trivial or empty descriptions.
    pass_condition: "Narrative fields must contain at least 20 characters."
    fail_message_template: "Narrative at {path} is too short ({length} chars). Minimum 20."
    severity_in_wip: MAJOR
    severity_in_gold: BLOCKER
    autofix_allowed: false
    suggested_fix: "Expand description to at least one full sentence."

  - id: SOUL_003
    intent: Detect obvious development placeholders.
    pass_condition: "Content must not contain: ['TODO', 'FIXME', 'TBD', 'TK', 'INSERT TEXT'] (case-insensitive)."
    fail_message_template: "Placeholder '{token}' found in {path}."
    severity_in_wip: MAJOR
    severity_in_gold: BLOCKER
    autofix_allowed: false
    suggested_fix: "Replace placeholder with actual content or remove."

  - id: SOUL_004
    intent: Detect filler text.
    pass_condition: "Content must not contain 'lorem ipsum' sequence."
    fail_message_template: "Filler text (Lorem Ipsum) detected in {path}."
    severity_in_wip: MAJOR
    severity_in_gold: BLOCKER
    autofix_allowed: false
    suggested_fix: "Replace filler text with actual content."

  - id: SOUL_005
    intent: Detect bracketed editor notes.
    pass_condition: "Content must not contain unescaped square `[...]` or angle `<...>` brackets."
    fail_message_template: "Editor brackets detected in {path}: '{match}'."
    severity_in_wip: MAJOR
    severity_in_gold: BLOCKER
    autofix_allowed: false
    suggested_fix: "Remove editor notes or integrate them into the narrative."

  - id: SOUL_006
    intent: Enforce capitalization on sentences.
    pass_condition: "Narrative text blocks must start with an uppercase letter or number."
    fail_message_template: "Text at {path} starts with lowercase: '{start}'."
    severity_in_wip: INFO
    severity_in_gold: MAJOR
    autofix_allowed: true
    suggested_fix: "Capitalize the first letter."

  - id: SOUL_007
    intent: Enforce metadata/status validity.
    pass_condition: "Metadata status must match the validation mode."
    fail_message_template: "Status mismatch: File is in {mode} mode but metadata.status is '{status}'."
    severity_in_wip: INFO
    severity_in_gold: BLOCKER
    autofix_allowed: false
    suggested_fix: "Update metadata.status to match the directory/lifecycle stage."

allowed_exceptions:
  technical_terms:
    allow_brackets: false
    allow_digits_start: true

  formatting:
    allow_markdown_headers: false
