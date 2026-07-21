# Soul/Essence Contract

> **This is the format the pipeline will treat as truth.**

The Soul/Essence layer defines **narrative and creative content** that gives entities meaning beyond mechanics.

> [!IMPORTANT]
> **GLOBAL RULE:** Soul content is required for all entity types. The specific fields vary by entity schema, but every entity must have narrative substance.

---

## Core Principle

> **Soul is the story. Essence is the feeling.**

Soul content must:
- Be human-readable and evocative
- Pass minimum length requirements
- Provide value to GMs and players
- Guide LLM narration

---

## Soul Blocks by Entity Type

### Faction: `essence` block

```yaml
essence:
  overview: "Compelling multi-paragraph description..."      # minLength: 100
  ideology: "What they believe and why..."                   # minLength: 50
  style_guide:
    voice: "Menacing, calculating..."                        # minLength: 20
    aesthetic: "Shadows, dark alleys..."                     # minLength: 20
  gm_guidance: "How to portray this faction..."              # minLength: 50
```

### Feat: `soul` block

```yaml
soul:
  description: "What this feat represents..."                # minLength: 50
  flavor_text: "Quote or evocative phrase..."                # optional
  narrative_effect: "What it feels like in-game..."          # minLength: 30
```

### Location: `essence` block

```yaml
essence:
  description: "What travelers see and feel..."              # minLength: 100
  atmosphere: "The mood and sensory details..."              # minLength: 50
  secrets: "What lies beneath the surface..."                # optional
```

---

## Validation Rules

| Code | Severity | Condition |
|------|----------|-----------|
| `SOUL_001` | MAJOR | Missing required soul/essence block |
| `SOUL_002` | MAJOR | Field below minimum length |
| `SOUL_003` | MINOR | Optional field present but empty |
| `SOUL_004` | INFO | Soul content could be richer |

---

## Length Requirements

| Field Type | WIP Minimum | Gold Minimum |
|------------|-------------|--------------|
| Overview/Description | 50 | 100 |
| Ideology/Voice | 20 | 50 |
| GM Guidance | 30 | 50 |
| LLM Guidance (rules) | 40 | 40 |
| Narrative (rules) | 20 | 20 |

---

## Validator: `soul_validator.py`

**Purpose:** Validate that all entities have sufficient narrative content.

**Checks:**
- Required soul/essence blocks present
- String fields meet minimum lengths
- Content is non-placeholder (no "TODO", "TBD", etc.)
- Rich content guidance (optional, INFO level)
