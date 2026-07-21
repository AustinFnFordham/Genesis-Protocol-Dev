# Tag System Discovery Report

> Generated: 2026-01-02

## A) Tag File Candidates

### Found Files

| Path | Size | Last Modified |
|------|------|---------------|
| `SW5e_Data_Hub/data/tags/master_tags.yml` | 47,994 bytes | Fri Jan 2 11:34:45 2026 |
| `SW5e_Data_Hub/data/tags/master_tags.yml.backup` | (backup) | - |
| `SW5e_Data_Hub/master_tags.yml` | (root duplicate) | - |
| `SW5e_Data_Hub/data/tags/faction_tags.yml` | (subset) | - |

### Canonical Choice: `SW5e_Data_Hub/data/tags/master_tags.yml`

**Rationale**: This is the path referenced in:
- `forge.py` lines 232-237
- `forge.yml` line 127
- `migrate_master_tags.py`

### First 30 Lines

```yaml
version: '2.0'
tags:
- id: tag_guardian
  category: archetype
  description: A Force-wielding protector who excels at defense and protection
  mechanics:
    hooks:
    - hit_die
    - primary_ability
    - resource_type
    - role
- id: tag_sentinel
  category: archetype
  description: A balanced Force user who investigates threats and maintains order
  mechanics:
    hooks:
    - hit_die
    - primary_ability
    - resource_type
    - role
- id: tag_consular
  category: archetype
  description: A diplomatic Force user focused on healing and peaceful resolution
  mechanics:
    hooks:
    - hit_die
    - primary_ability
    - resource_type
    - role
```

---

## B) Lexicon Validator Candidates

### Found Files

| Path | Type |
|------|------|
| `forge_v3/forge_core/validators/lexicon_validator.py` | Primary validator |
| `forge_v3/forge_core/validators/__init__.py` | Exports module |

### Canonical Choice: `forge_core/validators/lexicon_validator.py`

### Key Functions

| Function | Purpose |
|----------|---------|
| `LexiconValidator.__init__(master_tags_path)` | Load and parse tags |
| `LexiconValidator.validate(data, file_path, entity_type)` | Run validation |
| `validate_lexicon(data, file_path, master_tags_path, entity_type)` | Convenience wrapper |

### Call Chain from forge.py

```
forge.py:70    → from forge_core.validators.lexicon_validator import validate_lexicon
forge.py:285   → lexicon_report = validate_lexicon(data, file_path, master_tags_path, entity_type)
forge.py:453   → lexicon_report = validate_lexicon(data, file_path, master_tags_path, entity_type)
```

---

## C) EXACT Config/Argument Path

### forge.py Resolution Logic (lines 232-237)

```python
# Resolve master_tags path
forge_root = os.path.dirname(__file__)
master_tags_path = os.path.join(forge_root, "..", "SW5e_Data_Hub", "data", "tags", "master_tags.yml")
if not os.path.exists(master_tags_path):
    # Try alternative location
    master_tags_path = os.path.join(forge_root, "data", "tags", "master_tags.yml")
```

### Priority Order

1. `{forge_root}/../SW5e_Data_Hub/data/tags/master_tags.yml` (primary)
2. `{forge_root}/data/tags/master_tags.yml` (fallback)

### forge.yml Reference (line 127)

```yaml
  tags: "data/tags/master_tags.yml"
```

---

## Summary

| Artifact | Canonical Path |
|----------|----------------|
| Tag Lexicon | `SW5e_Data_Hub/data/tags/master_tags.yml` |
| Validator | `forge_v3/forge_core/validators/lexicon_validator.py` |
| Config | `forge.py` lines 232-237 |
