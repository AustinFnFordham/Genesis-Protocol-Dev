# Forge Architecture Alignment Notes

**Kernel / Profile Separation · Schema Infrastructure · O(1) Runtime Guarantees**

---

## Core Principle

**Make Forge a kernel, and load everything else from profiles.**

---

## ✅ Kernel (Never Data-Type Specific)

These components **must remain fully agnostic**:

* `orchestrator.py` state machine (Step 0 → 1 → 2 → 3)
* Adapter boundary + patch application
* Run artifacts / manifests
* Schema loading and `$ref` resolution
* Finding routing + bundling
  *(rules are generic; behavior driven by profile config)*
* Deterministic migration framework
  *(transforms selected by profile)*

The kernel should never “know” whether it is processing factions, species, items, planets, etc.

---

## ✅ Profile Packs (Data-Type Specific)

Everything that varies by dataset **must live in the profile**:

* Which schema is canonical
* Which validators run and their thresholds (gold / platinum)
* Owned vs global URID policy
* Prompt pack + agent roster + expected output shapes
* Completeness thresholds (minItems / minLength)
* Registry policy:

  * what can be created
  * what must already exist

This gets us to:

> **“Throw any dataset in front of Forge, as long as the profile is correct.”**

---

## Separation of Concerns (The Refactor We’re Circling)

### 1) Orchestrator Becomes a Generic State Machine

Instead of *any* faction-specific logic, the orchestrator should:

1. Load profile (from config)
2. Run deterministic validators listed by profile
3. Route findings by domain
4. Dispatch bundles to agents listed by profile
5. Apply patches
6. Repeat until gates pass

**Explicitly remove references to:**

* Hardcoded `master_tags.yml` paths
* Faction-specific thresholds
* Faction-specific prompts
* `connections.headquarters` special casing
* `fac_*` owner derivation assumptions

All of the above become **profile rules**, not kernel logic.

---

### 2) Validators Become “Validator Plugins”

Each validator should conform to:

```python
validate(data, ctx, *, profile, mode) -> findings[]
```

Where `ctx` includes:

* File path
* Data root(s)
* Loaded registries (tags, species index, etc.)
* Schema resolver

Validators must **not decide dataset type**.
They read rules exclusively from the profile.

---

### 3) Schema / `$ref` Resolution Becomes Infrastructure

This is the missing piece that felt “scattered.”

We want **one authoritative module**, e.g.:

```
forge_core/schema/schema_resolver.py
```

Responsibilities:

* Load primary schema
* Build `$id` → schema store
* Resolve `$ref` via local store first
* Never rely on network unless explicitly enabled

This fixes the remote URL issue **without rewriting schemas** and **without slowing validation**.

---

## Finalizing All Schemas (Yes — But Do It in Layers)

Agents will never reliably create correct files unless:

* They have the schema
* They have a gold/platinum example
* They know owned/global path rules

So yes—finalize schemas, but **layer them**:

### Layer A: Canonical Schema Graph

* Each schema has a stable `$id`
* `$ref` uses canonical URIs (hub URLs are correct)

### Layer B: Local Resolver Mapping

* Local build maps canonical `$id` → local file
* Offline-safe
* Runtime O(1)

### Layer C: Schema Pack for Agents

Agents don’t need full `jsonschema`; they need:

* Shape contract
* Required fields
* Allowed keys (`additionalProperties: false`)
* ID patterns
* Minimal examples

We can auto-generate schema summaries (JSON → MD / compact JSON) per profile and feed those into prompts.

---

## The Big Batch Problem — Registry Handling

When batches generate new tags / URIDs, we need deterministic reconciliation.

**Never allow models to edit master registries mid-run.**

That’s how we get:

* Drift
* Duplicates
* Broken merges

### Correct Pattern: Registry Delta Stage

At the end of a batch:

1. Collect all unknown tags / species / URIDs
2. Output `registry_delta.json` (or `.yml`)
3. Run a deterministic registry gate:

   * dedupe
   * normalize naming
   * collision checks
   * mark as `PROPOSED`, not accepted

---

### Dedicated Registry Agent (Later)

* Agent writes **proposals only**
* Deterministic validator has final say
* Still gated through delta files, never direct edits

This keeps complexity **linear in new entries**, not total registry size.

---

### Registry Acceptance Flow

Initially:

* We review / accept deltas manually
* Forge applies accepted deltas to master registries
* Next batch sees them as known

Later:

* Dedicated Registry Agent assists proposal writing only

---

## The “Perfect File” Pipeline (Profile-Driven, Generic)

### Step 0 — Deterministic Truth (No Agents)

1. Load profile
2. Load schema pack + build local `$id` store
3. Load required registries (tags, species, etc.)
4. Run deterministic validators:

   * schema
   * lexicon
   * references
   * ownership

If Step 0 fails on infrastructure (e.g., missing schema ref mapping), **stop**.

No LLM should attempt to Blacksmith a broken compiler.

---

### Step 1 — Reach Gold Baseline (Repairs Allowed)

5. Scaffolding / ownership placement (deterministic)
6. Deterministic migration transforms
7. **Structural repair loop**:

   * validate
   * bundle STRUCTURE
   * dispatch Blacksmith
   * apply RFC6902 ops
   * repeat until STRUCTURE blockers/majors = 0
8. **Reference repair loop**:

   * validate
   * bundle REFERENCE
   * dispatch Alchemist
   * apply patches
   * repeat until REFERENCE blockers/majors = 0

At this point, Gold should be achievable if the profile supports it.

---

### Step 2 — Platinum Content Fill (Content Creation Allowed)

9. Completeness validator (platinum thresholds)
10. Bundle COMPLETENESS → Genesis_Smith
11. Narrative validator → Runesmith / Canticle
12. Optional Bard polish (non-blocking)

---

### Step 3 — Gates and Artifacts

13. Gold gate pass (strict)
14. Platinum gate pass (thresholds + prose)
15. Produce artifacts:

* run manifest
* registry delta proposals
* final validation reports

---

## Immediate Actions to Keep Momentum

### A) Move `_legacy_schema`

Archiving `Faction_Core.schema.json` is correct.
It is not the same contract as the thin `faction_core.schema.json`, and keeping both live guarantees confusion.

---

### B) Fix the Faction-Specific Tool Calling Bug

Do this **before batching anything else**.

Even with perfect schemas, a hidden faction assumption will break species runs in ways that look like “model failure.”

---

### C) Create a Single `Profile` Object

Even a minimal version:

* `profile.schema.primary`
* `profile.registries.required`
* `profile.agents.by_domain`
* `profile.validators.enabled`
* `profile.thresholds.by_mode`

Then remove all hardcoded faction paths and thresholds.

---

### D) Emit Registry Delta on Every Run

Even before full automation:

* Output unknown tags / URIDs into a file
* This alone makes batch runs auditable and sane

---

## About Keeping It O(1)

“O(1)” here means:

> The orchestration logic does not change when the dataset changes.

Profiles change. The kernel does not.

We will still do O(n) work for validation during build (that’s unavoidable), but we avoid O(k) engineering work for each new dataset.

---

## Remote URL Sanity Check

The hub URL is **not** the problem.

It is a good canonical ID.

The problem is simply that we don’t yet have a schema resolver mapping `$id → local file`.

Fix that **once** in the kernel, and every profile benefits.

---

## Schema Reference Clarification (Important)

That reference:

```
https://sw5e-data-hub.local/schemas/common/common_urid.schema.json
```

Exists to provide:

* Canonical identity
* Cross-repo consistency
* Future API compatibility

The fix is **not** to remove it.

The fix is to:

* Keep canonical `$id`
* Add a resolver map in Gaugewright’s schema validation layer

This preserves:

* Correct schema validation
* Offline determinism
* Future API deployment

---

## Dataset-Agnostic Architecture (Target State)

### Core Engine (Generic)

* Orchestrator state machine
* Schema validation
* Lexicon validation
* URID resolution
* Routing / bundling
* Deterministic migration
* Gold / Platinum gates

### Profile (Dataset-Specific)

* Schema entrypoint
* Resolver map (URI → local path)
* Owned / global URID policy
* Completeness thresholds
* Prompt packs
* Enabled validators
* Batch scope directories

Result:

> We batch anything by swapping the profile.

---

## Large Batch Reality (120 Species Files)

Batch build produces:

* Files
* Batch-local registry index

Then run a linker / consolidation pass:

* Accept or reject new globals
* Ensure owned entities stay owned
* Fail if globals are missing

We already have the correct rule:

> **No auto-create globals during gold promotion.**

That makes batch runs safe and deterministic.

---

## Runtime vs Build-Time Complexity (We’re Aligned)

### Build-Time (Forge)

* O(n) scan once
* Build indices
* After that: O(1) lookups

### Runtime (Game / API)

* Load registry index into memory
* O(1) entity and tag lookups
* Cached summaries + structured state
* Minimal LLM context

Autosave every 15–20 rounds fits perfectly:

* Snapshot state
* Rolling summaries
* Retrieval keys instead of full history

---

## Example File Reality Check

### `fac_children_of_the_watch.yml`

* Already Gold
* Thin content:

  * Short lists
  * Empty UI paths
  * Missing mechanical effects

That’s exactly what Platinum completeness is supposed to fix.

### `fac_black_sun.yml`

* Not Gold yet:

  * `_legacy` present
  * `refs_created` present
  * Must resolve globals

Correct order:

1. Black Sun → Gold
2. Black Sun → Platinum

---

## One Mandatory Decision Before Batching: `loc_*` Policy

We must choose **one truth**:

* Are `loc_*` owned?
* Or are they global?

Recommended long-term model:

* `pla_coruscant` (global planet)
* `loc_black_sun_counting_room` (owned site)
* HQ points to owned `loc_*`, which references `pla_*`

Resolve this **before batching**.

---

## What We Should Do Next (In Order)

1. Implement offline schema resolver mapping in Gaugewright
2. Make orchestrator + validators profile-agnostic
3. Extract dataset policies into profiles
4. Add batch linker / indexer step
5. Resolve `loc_*` policy
6. Test with 2–3 factions + 5–10 species
7. Batch confidently

---

---

# Forge Architecture Review & Finalization Plan

**Schema Infrastructure · Profile-Driven Pipeline · O(1) Runtime Safety**

---

## 1) Why the Schema Is Trying to Resolve

`https://sw5e-data-hub.local/...`

There are **two separate schema concepts being conflated**, and your pause here was correct.

### A) `$id` Is an Identifier (Not a Fetch Instruction)

* `$id` can be a URL
* It does **not** need to be reachable
* It exists to uniquely identify schemas across systems

This is **good practice** and should be preserved.

### B) `$ref` Points to `$id`, and the Validator Tries to Fetch It

Your schemas contain `$ref` entries like:

```text
https://sw5e-data-hub.local/schemas/common/common_urid.schema.json
```

Because the validator is created without a resolver / schema store:

```python
Draft7Validator(self.schema)
```

`jsonschema` attempts normal URI resolution — meaning it tries to fetch that URL.

🚨 **This is not a data problem. It is a schema infrastructure problem.**

---

## 2) Correct Fix (Do NOT Rewrite Schema IDs)

**Best practice**:
Keep canonical `$id` URLs **unchanged**, and provide a **local schema registry** that maps `$id → local schema file`.

### What Needs to Exist

Create a dedicated module:

```text
forge_core/schema/schema_loader.py
```

### Responsibilities

* Load schema JSON/YAML
* Build a schema store keyed by `$id`
* Create validators with a resolver / registry

### Conceptual Flow

```python
schema_store = {
  schema["$id"]: schema_dict,
  ...
}

validator = Draft7Validator(
  primary_schema,
  resolver=RefResolver.from_schema(primary_schema, store=schema_store)
)
```

### Why This Is the Right Move

* Keeps schemas canonical
* Avoids network calls
* Supports future API-backed schema delivery
* Keeps validation **deterministic and O(1)**

---

## 3) Orchestrator & Validators Must Become Profile-Agnostic

You correctly identified the real risk:

> The orchestrator and validators are faction-shaped.

That is **not batch-safe**.

### The Rule

**No datatype assumptions** in:

* orchestrator
* validators
* routing
* completeness rules
* prompts

Those belong exclusively in **profiles**.

---

## 4) What a Profile Must Define (Compiler Spec)

A profile is the **entire contract** for a datatype.

### Schema & Paths

* `schema_primary`
* `schema_deps_dirs`
* registry paths (tags, species, planets, etc.)

### Ownership Rules

* `owned_kinds` (prefix → directory)
* `global_kinds`
* location policy (see §6)

### Validation Rules

* gold gates
* platinum thresholds
* UI requirements

### Agent Configuration

* which agents exist
* which prompts apply
* routing rules

Once this exists:

> **Any dataset becomes batchable by swapping the profile.**

---

## 5) The “Perfect File” Pipeline (Gold + Platinum)

This is the **exact pipeline** that produces a “perfect” file.

---

### **Step 0 — Deterministic Truth (No LLMs)**

1. Load profile
2. Load schemas + schema store
3. Run deterministic validators:

   * schema
   * lexicon (from `master_tags.yml`)
   * URID / reference resolution

**Output:** Routed findings by domain
(STRUCTURE / REFERENCE / COMPLETENESS / NARRATIVE)

---

### **Step 1 — Reach Gold Baseline**

4. **Scaffolder (deterministic)**

   * ownership paths
   * URID resolution
   * allowed stub creation

5. **Deterministic Migration**

   * resolves `_legacy.refs_created`
   * creates owned stubs only
   * never creates globals
   * removes `_legacy` when empty

6. **Structural Loop**

   * Gaugewright ↔ Blacksmith
   * until STRUCTURE blockers = 0

7. **Reference Loop**

   * deterministic checks + Alchemist
   * until REFERENCE blockers = 0

8. **Gold Gate**

   * no `_legacy`
   * refs resolved
   * schema clean
   * tags exist
   * globals must pre-exist

✅ **Gold-perfect (compiler-grade correctness)**

---

### **Step 2 — Platinum Content Fill (Generative, Bounded)**

9. **Completeness Pass**

   * deterministic thresholds
   * Genesis_Smith fills missing content only in allowed fields

10. **Narrative Pass**

* Canticle / Runesmith improves tone & clarity
* schema remains inviolable

11. **Optional Bard Polish**

* non-blocking
* flavor-only

---

### **Step 3 — Platinum Gate**

12. Verify:

* Gold gate passes
* completeness thresholds met
* narrative majors = 0
* UI assets present (if required)

✅ **Platinum-perfect**

---

## 6) `loc_*` Ownership Policy Must Be Resolved

You identified a real contradiction.

### Current Conflict

* Policy: `loc_*` = owned
* Reality: `loc_coruscant` = global

### Option A (Recommended)

* Global planets: `pla_coruscant`
* Owned locations: `loc_black_sun_counting_room`
* HQ references planet + owned site

### Option B

* Make `loc_*` global
* Introduce `site_*` or `facloc_*` for owned locations

🚨 This must be resolved before large batches.

---

## 7) Batch Strategy (Compiler-Style)

Yes — **test first, then batch**.

### Recommended Flow

1. Test 2–3 files per datatype
2. Run full pipeline
3. Fix systemic issues
4. Batch safely

### For Large Batches (e.g. 120 Species)

Add a **registry index build step**:

```json
{
  "urid": "...",
  "path": "...",
  "type": "...",
  "tags": [...]
}
```

Benefits:

* Forge validation becomes fast
* Game engine/API lookups become **O(1)**
* Cache-friendly

---

## 8) Why This Preserves O(1) Runtime Performance

* Deterministic schema validation happens **offline**
* Registry index enables constant-time resolution
* Runtime engine only loads:

  * indexed data
  * cached summaries
* LLM context stays light
* Autosave + context snapshotting becomes trivial

---

## 9) Recommended Next Steps (In Order)

To keep momentum **and avoid rework later**:

1. Implement `schema_loader` + local schema store
2. Refactor orchestrator & validators to be profile-driven
3. Resolve `loc_*` ownership policy
4. Add registry index builder for batch runs


These should be explicitly tracked as pipeline milestones:

* **Schema Resolver Module** (`schema\_resolver.py`)
  *Single source of truth for `$id` → local mapping*
* **Profile Contract Definition** (formal schema for profiles themselves)
* **Registry Delta Stage** (explicit pipeline step, not just an artifact)
* **Batch Linker / Index Builder** (produces runtime O(1) indices)
* **Prompt Pack Enforcement** (orchestrator must refuse default prompts if profile doesn’t specify them)
* **`loc\_\*` Policy Resolution** (blocking decision before large batches)

# Canonical Schema IDs vs Profile Configuration

This section clarifies where schema **identity** belongs versus where schema **resolution** belongs, and how to keep the system modular, future-proof, and O(1)-friendly.

---

## 1) Canonical Schema Identity (`$id`) — Lives in the Schema

The `$id` field is the **public identity** of a schema within the schema graph.

### Why it must stay in the schema
- `$id` defines *what the schema is*, not *where it lives*
- `$ref` resolution depends on stable, canonical identifiers
- Changing `$id` per profile would fracture the schema graph
- Tooling and validation become unreliable if identity is contextual

### Design rule
- `$id` must be **explicit, stable, and immutable once published**
- `$id` **must not** depend on:
  - local file paths
  - profile names
  - environment configuration

### Why hub-style URIs are correct
Using canonical URIs like:

https://sw5e-data-hub.local/schemas/common/common_urid.schema.json


is good practice because:
- It decouples identity from storage
- It supports future API/hosted schemas
- It allows offline validation when paired with a resolver map

**Conclusion:**  
✅ `$id` belongs in the schema and should never be profile-defined.

---

## 2) Schema Resolution (`$id` / `$ref` → Local Path) — Profile / Config Driven

What changes across systems is **where schemas live**, not what they represent.

### Resolver responsibility
Profiles (or environment config) define how to resolve canonical `$id` values to local files.

Conceptually:
canonical schema ID
→ local file path

Example:
https://sw5e-data-hub.local/schemas/common/common_urid.schema.json
→ deps/schemas/common/common_urid.schema.json


### Design rule
- Profiles define **offline resolution behavior**
- Schemas remain canonical and portable
- No schema edits are required when paths change

---

## 3) Profile vs Config: Clean Separation

### Profile owns: *Schema graph intent*
Profiles define **what schema graph is in use**.

Recommended profile fields:

```yaml
schema:
  primary_path: deps/schemas/faction/faction_core.schema.json
  primary_id: https://sw5e-data-hub.local/schemas/faction/faction_core.schema.json
  ref_map:
    https://sw5e-data-hub.local/schemas/common/common_urid.schema.json: deps/schemas/common/common_urid.schema.json
    https://sw5e-data-hub.local/schemas/common/common_atomic.schema.json: deps/schemas/common/common_atomic.schema.json
Profile responsibilities:

* Which schema is canonical
* Which schema IDs are expected
* How canonical IDs resolve locally

---

### Config / Environment owns: *Deployment wiring*

Config controls **where files physically live**.

Examples:

* repo root
* deps directory location
* packaged build paths
* network access toggles

Config should handle:

* path overrides
* filesystem layout
* environment differences (dev vs packaged vs CI)

---

## 4) Guardrail: Schema Identity Verification

Add a deterministic safety check:

> When loading `profile.schema.primary_path`, verify that the schema’s internal `$id` matches `profile.schema.primary_id`.

This prevents:

* accidentally validating against the wrong schema
* silent misconfiguration
* mismatched schema graphs

### Failure behavior

* Emit a STRUCTURE BLOCKER
* Halt before any agent is invoked

---

## 5) Registry Passes Must Not Rewrite Canonical IDs

Your concern about “one refactor forcing edits everywhere” is valid — and avoidable.

### Hard invariant

Registry passes must **never** rewrite:

* schema `$id`
* `$ref` canonical URIs
* stable entity URIDs

### Registry passes may:

* build indices
* propose new registry entries
* normalize *new* names
* emit delta files for review

### If a canonical ID must ever change

Treat it as a **versioned migration**:

* introduce new `$id`
* keep old `$id` as an alias in resolver mapping
* optionally migrate references via a tool (never forced)

---

## 6) Net Result

This architecture gives us:

* Canonical, stable schema identity
* Profile-driven, offline-safe resolution
* Zero mass-edits when paths change
* O(1) schema lookup via resolver map
* Future API compatibility
* Compiler-grade trust in validation

**Schema = identity**
**Profile = intent**
**Config = wiring**

---

## 7) Official Pipeline Addition (Recommended)

Add this to the Forge kernel:

* A schema resolver module that:

  * builds an in-memory `$id → file path` store
  * resolves `$ref` locally first
  * never hits the network unless explicitly enabled
  * fails fast on unresolved canonical IDs

This removes the current STRUCTURE blocker without weakening validation.


The “Perfect File” Pipeline (Gold + Platinum)

This is the **exact pipeline** that produces a “perfect” file.

---

### **Step 0 — Deterministic Truth (No LLMs)**

1. Load profile
2. Load schemas + schema store
3. Run deterministic validators:

   * schema
   * lexicon (from `master_tags.yml`)
   * URID / reference resolution

**Output:** Routed findings by domain
(STRUCTURE / REFERENCE / COMPLETENESS / NARRATIVE)

---

### **Step 1 — Reach Gold Baseline**

4. **Scaffolder (deterministic)**

   * ownership paths
   * URID resolution
   * allowed stub creation

5. **Deterministic Migration**

   * resolves `_legacy.refs_created`
   * creates owned stubs only
   * never creates globals
   * removes `_legacy` when empty

6. **Structural Loop**

   * Gaugewright ↔ Blacksmith
   * until STRUCTURE blockers = 0

7. **Reference Loop**

   * deterministic checks + Alchemist
   * until REFERENCE blockers = 0

8. **Gold Gate**

   * no `_legacy`
   * refs resolved
   * schema clean
   * tags exist
   * globals must pre-exist

✅ **Gold-perfect (compiler-grade correctness)**

---

### **Step 2 — Platinum Content Fill (Generative, Bounded)**

9. **Completeness Pass**

   * deterministic thresholds
   * Genesis_Smith fills missing content only in allowed fields

10. **Narrative Pass**

* Canticle / Runesmith improves tone & clarity
* schema remains inviolable

11. **Optional Bard Polish**

* non-blocking
* flavor-only

---

### **Step 3 — Platinum Gate**

12. Verify:

* Gold gate passes
* completeness thresholds met
* narrative majors = 0
* UI assets present (if required)

✅ **Platinum-perfect**

---
Next Steps (In Order) - Restated

To keep momentum **and avoid rework later**:

1. Implement `schema_loader` + local schema store
2. Refactor orchestrator & validators to be profile-driven
3. Resolve `loc_*` ownership policy
4. Add registry index builder for batch runs


These should be explicitly tracked as pipeline milestones:

* **Schema Resolver Module** (`schema\_resolver.py`)
  *Single source of truth for `$id` → local mapping*
* **Profile Contract Definition** (formal schema for profiles themselves)
* **Registry Delta Stage** (explicit pipeline step, not just an artifact)
* **Batch Linker / Index Builder** (produces runtime O(1) indices)
* **Prompt Pack Enforcement** (orchestrator must refuse default prompts if profile doesn’t specify them)
* **`loc\_\*` Policy Resolution** (blocking decision before large batches)

---

Build a comprehensive plan around this information and lets knock out this refactor quick so that we can move forward with the validation pipeline. If you are not sure about a direction to go with something, simply ask. The idea is for this to be agnostic as much as possible and then utilize profiling and configs to create unique data for each unique directory (not just factions) AND eventually completely different systems altogether. I have created a markdown file called ```AGNOSTIC_REFACTOR.md``` with the same information for reference. 