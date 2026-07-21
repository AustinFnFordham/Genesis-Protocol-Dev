# ARTICLES OF CREATION

**(Genesis Protocol — Forge V3)**

This document defines the immutable laws, conceptual ontology, and operational constraints governing all content, schemas, agents, and pipelines within the Forge V3 system.

**Any agent, model, or human acting within this system must obey these articles.**  
**Deviation is a system error, not a creative choice.**

---

## I. PRIME DIRECTIVE (WHY THIS EXISTS)

### Article 1 — The Goal

The goal of Forge V3 is to create a coherent, scalable, machine-verifiable Star Wars RPG data universe that is:

- **Canon-consistent** per file
- **Deterministic** in structure
- **Generative** in content
- **Validatable** at scale
- **Playable** by humans
- **Operable** by machines

This system must scale to 10,000+ files without requiring manual curation.

---

## II. CORE ONTOLOGY (WHAT THINGS ARE)

> [!IMPORTANT]
> These concepts are not vibes. They are **types**.

### Article 2 — Atomic

**Atomic data is the smallest unit of mechanical truth.**

**Atomic objects:**
- `effect_object`
- `condition_group`
- `trigger_event`

**Atomic data:**
- Has no lore obligation
- Is deterministic
- Is reusable
- Is schema-referenced

Atomic data never contains prose beyond what is strictly necessary.

> **Atomic is physics.**

---

### Article 3 — Soul

**Soul is authored meaning.**

**Soul lives in:**
- `essence`
- `narrative`
- `style_guide`
- `gm_guidance`

**Soul:**
- Can vary per file
- Can contradict other files (if canon permits)
- Must never violate schema
- Must never invent mechanics

> **Soul is voice, not rules.**

---

### Article 4 — Chaos

**Chaos is conditional, emergent behavior.**

> [!IMPORTANT]
> **GLOBAL RULE:** The Chaos Engine is project-wide infrastructure. No validator, schema, or contract may assume factions are the home of chaos rules. **Any entity may host rules if enabled by that entity's profile.**

**Chaos lives in:**
- `synergy_engine.rules`

**Chaos rules:**
- Are triggered by tags + events
- Are conditional, not guaranteed
- Must reference atomic mechanics
- Must include `llm_guidance` for narrative execution

Chaos is opt-in at runtime, never hard-coded.

> **Chaos is possibility, not randomness.**

---

### Article 5 — Canon Scope

**Canon is per-file, not global.**

Each file declares:

```yaml
metadata:
  content_origin: canon | legends | homebrew
```

Canon consistency is enforced **within a playthrough**, not across the entire dataset.

Contradictions are allowed across files if canon scopes differ.

---

## III. DATA INTEGRITY LAWS (WHAT MUST NEVER HAPPEN)

### Article 6 — No Silent Loss

No meaningful content may be deleted without one of the following:

1. Migration into a schema-approved structure
2. Extraction into a micro-entity
3. Quarantine into `_legacy` (WIP only)

> [!CAUTION]
> **Deletion without migration is forbidden.**

---

### Article 7 — No Schema Drift

**Schemas are law.**

No agent may:
- Add fields
- Rename fields
- Change semantics

**Schema changes require:**
1. Explicit schema task
2. Version bump
3. Walkthrough update

> [!WARNING]
> If data doesn't fit the schema, **evolve the schema** — never "work around" it.

---

### Article 8 — Determinism First

All runs must begin with deterministic validation:

1. URID validation
2. Schema validation
3. Lexicon validation
4. Lint SOP

> **LLMs never run first.**

---

## IV. PATCH DISCIPLINE (HOW CHANGES ARE EXPRESSED)

### Article 9 — Patch-Only Output

All non-deterministic agents must output **RFC6902 JSON Patches** only.

**Allowed operations:**
- `add`
- `replace`
- `remove` (WIP only, never on soul content)

**Forbidden:**
- Full file rewrites
- Inline YAML dumps
- Structural invention

> **Patches are auditable. Patches are reversible.**

---

### Article 10 — Scope Lock

Each task declares:
- Allowed files
- Allowed roots
- Allowed paths

**Any patch outside scope is invalid.**

---

## V. AGENT DOCTRINE (WHO DOES WHAT)

### Article 11 — Agent Roles Are Sacred

| Agent              | Role              | Writes | Phase       |
|--------------------|-------------------|--------|-------------|
| Gaugewright        | Schema / URID     | ❌     | Tempering   |
| Completeness       | Min rules         | ❌     | Tempering   |
| Blacksmith         | Structural repair | ✅     | Tempering   |
| Genesis_Smith      | Content fill      | ✅     | Tempering   |
| Reagent_Inspector  | Semantic audit    | ❌     | Tempering   |
| Canticle_Examiner  | Narrative critique| ❌     | Inscription |
| Runesmith          | Prose rewrite     | ✅     | Inscription |
| Spark_Igniter      | Ideas only        | ❌     | Spark       |
| Foreman            | Final audit       | ❌     | Foreman     |

> [!IMPORTANT]
> **Agents must not cross roles.**

---

### Article 12 — AG vs Local Workers

**Anti-Gravity (AG):**
- Designs systems
- Writes schemas
- Builds pipelines
- Creates Platinum exemplars

**Local Agents:**
- Execute instructions
- Apply patches
- Run batch jobs
- Never redesign architecture

> **The Architect builds the factory. The workers run it.**

---

## VI. PROFILES & DIRECTORIES (HOW SCALE WORKS)

### Article 13 — Profiles Are Contracts

Every directory operates under a **profile** defining:

- Schema ID
- Entity type
- Allowed roots
- Completeness rules
- Lexicon policy
- Patch allowlists

> **No LLM may run without a profile.**

---

## VII. QUALITY TIERS (WHEN DATA IS "DONE")

### Article 14 — Status Gates

| Status   | Meaning                                          |
|----------|--------------------------------------------------|
| WIP      | `_legacy` allowed, WARN allowed                  |
| Gold     | No `_legacy`, WARN forbidden                     |
| Platinum | Gold + narrative + chaos + cross-refs complete   |

> **Promotion requires explicit validation.**

---

## VIII. RECORD & PROOF (HOW WE TRUST THE SYSTEM)

### Article 15 — Proof of Work

Every change must record:

- What changed
- Files touched
- Validation command
- JSON output summary
- Time taken

> **If it isn't logged, it didn't happen.**

---

## IX. FINAL LAW

### Article 16 — The System Is the Authority

**No single file, agent, or human overrides the system.**

If something feels "awkward":

1. Investigate the schema
2. Investigate the ontology
3. Improve the pipeline

> [!CAUTION]
> **Do not hack around the rules.**
