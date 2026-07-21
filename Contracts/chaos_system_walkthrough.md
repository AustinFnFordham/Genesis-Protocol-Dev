# Chaos System Walkthrough

*Forge V3 — Genesis Protocol*

A unified source of truth for the Chaos Engine and profile-driven validation.

---

## System Overview

The Chaos Engine is a **tag-driven, event-reactive rules framework** that applies to any entity type.

```
┌─────────────────────────────────────────────────────────────┐
│                    CHAOS ENGINE                             │
├─────────────────────────────────────────────────────────────┤
│  Tags + Event → Condition Check → Effect                    │
│                                                             │
│  Profiles control what each entity type can do              │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Contracts

| Contract | Path | Purpose |
|----------|------|---------|
| Chaos Engine | [chaos_engine_contract.md](contracts/chaos_engine_contract.md) | Event/condition/effect models |
| Profile Spec | [profile_contract_spec.md](contracts/profile_contract_spec.md) | Validation policy format |
| Naming | [chaos_block_naming.md](contracts/chaos_block_naming.md) | Block naming decision |

---

## Profile System

Profiles externalize validation policies from code to YAML:

**Location:** `forge_core/profiles/<name>.profile.yml`

**Structure:**
```yaml
profile_id: faction_core
schema_id: faction_core.schema.json
entity_type: faction

tag_policy:
  wip_allow_unknown: true
  gold_block_unknown: true
  required_namespaces: [tag_era_]
  allowed_namespaces: [tag_faction_, tag_trait_, ...]

chaos_policy:
  enabled: true
  allowed_trigger_events: [on_check, on_save, ...]
  allowed_effect_categories: [skill_bonus, ...]
```

---

## Available Profiles

| Profile | Entity Type | Chaos Enabled |
|---------|-------------|---------------|
| `faction_core` | faction | ✅ |
| `feat_core` | feat | ✅ |
| `location_core` | location | ✅ |

---

## Rule Anatomy

Every chaos rule requires 7 fields:

| Field | Purpose |
|-------|---------|
| `rule_id` | Unique identifier (`^rule_[a-z0-9_]+$`) |
| `narrative` | Player-facing description (Soul) |
| `llm_guidance` | GM/AI narration instructions |
| `trigger_tags` | Tags that must be present |
| `trigger_event` | When to evaluate |
| `condition` | Predicate gate |
| `effect` | Outcome (Atomic) |

---

## Validation Commands

```powershell
# Single file with profile
python forge.py validate --path <file> --profile faction_core --mode wip --json

# Batch directory
python forge.py validate --path <dir> --profile faction_core --mode wip
```

---

## No-Bleed Rule

Profiles define strict allowlists:

- `allowed_trigger_events` — What events this entity type can react to
- `allowed_effect_categories` — What effects this entity type can produce
- `allowed_namespaces` — What tag prefixes are permitted

This prevents scope creep (e.g., a location trying to grant combat bonuses).

---

## Concept Validators

We have introduced **project-wide validators** that run on all entity types:

### 1. Atomic Validator
*Checks `ATOM_-` codes*
- Validates URIDs match patterns (`fac_`, `tag_`, `rule_`)
- Ensures enums (`trigger_event`, `effect_category`) are valid
- Structural correctness of atomic objects

### 2. Soul Validator
*Checks `SOUL_-` codes*
- Enforces narrative depth (min lengths for descriptions)
- Detects lazy placeholders ("TODO", "TBD")
- Ensures essential `essence` or `soul` blocks exist

### 3. Synergy Validator
*Checks `SYN_-` codes*
- Validates Chaos Rules against profile policy
- Enforces "No-Bleed" rule (no location rules doing combat things)
- Checks narrative quality of rule descriptions

### 4. Agent Output Validator
*Checks `AGT_-` codes*
- Validates JSON Patch (RFC6902) protocol
- Ensures audit hashes (`before_hash`, `after_hash`) are valid

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [ARTICLES_OF_CREATION.md](../ARTICLES_OF_CREATION.md) | System laws |
| [PLATINUM_DEFINITION.md](../PLATINUM_DEFINITION.md) | Quality gates |
| [CHAOS_ENGINE_RULEBOOK.md](../CHAOS_ENGINE_RULEBOOK.md) | Design philosophy |

---

## Atomic & Soul Enforcement Integration

Forge V3 uses specialized agents to enforce data quality contracts:

### Reagent Inspector (Atomicity)
- **Contract**: `docs/contracts/atomic_checklist.md`
- **Role**: Ensures fields are the correct type, enumerations are valid, and structure is flattened.
- **Key Command**: `inspect --fix` (Apply deterministic structural patches)

### Canticle Examiner (Soul)
- **Contract**: `docs/contracts/soul_checklist.md`
- **Role**: Ensures narrative fields exist, are non-empty, and free of placeholders/editor notes.
- **Key Command**: `examine` (Report narrative gaps)

> [!NOTE]
> These agents are "scaffolding" engineers. They fix the container, but they never write the creative content inside it.
