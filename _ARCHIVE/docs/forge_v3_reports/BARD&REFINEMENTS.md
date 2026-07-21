## Does the Step 0→1→2→3 pipeline work?

Yes — as a *compiler-style* pipeline it’s fundamentally correct:

* **Step 0 (Deterministic Truth)** prevents “LLM repairs” from masking broken infrastructure (schema ref resolution, registry load, etc.).
* **Step 1 (Gold Baseline)** isolates *structural* and *reference* correctness before we let content-generation touch anything.
* **Step 2 (Platinum Fill)** is the right place to allow **Genesis** to expand content and **Runesmith/Canticle** to polish.
* **Step 3 (Platinum Gate / Foreman)** gives us a clean “final link step” that proves the output is still valid after all edits.

So: the sequencing is right. The **refinement we still need** is making sure the *kernel stays profile-driven* and we don’t accidentally hardcode faction behavior again.

---

## The main refinement we should make

### 1) Bard-as-Optimizer Pattern

### Core idea

We run Bard on every file, but **we don’t automatically accept Bard’s rewrite**.

Instead:

1. Bard generates a **candidate patch** (RFC6902 ops) + **self-scored metrics**
2. A deterministic **NarrativeJudge** (Foreman-owned, profile-driven) compares:

   * Original content vs Bard candidate
3. If Bard is better **and** doesn’t break invariants:

   * apply patch
   * run micro validation loop
   * keep it
4. If not:

   * discard Bard patch
   * keep original

So Bard becomes like a compiler “-O2” pass: *nice to have, never required for correctness*.

---

## What “better” means (profile-driven)

We should avoid vague “vibes” and make this measurable. For Platinum, pick a small rubric with weights:

### Narrative Quality Score (0–100)

* **Specificity** (0–25): concrete details, named hooks, actionable GM utility
* **Clarity** (0–25): readable, not bloated, no contradictions
* **Tone match** (0–20): matches `essence.style_guide`
* **Table usefulness** (0–20): missions/hooks/rumors/conflicts are playable
* **Consistency** (0–10): no broken references, no lore mismatches introduced

**Accept rule (example):**

* accept Bard patch only if:

  * `score_new >= score_old + 8`, and
  * no new registry deltas (unless explicitly allowed), and
  * no schema/lexicon/reference regressions

That “+8” is the key: prevents churn where Bard rewrites but doesn’t truly improve.

---

## Safety rails (so Bard doesn’t wreck structure)

Bard should be constrained to a **whitelist of pointers** in the profile, like:

* `essence.overview`
* `essence.ideology`
* `essence.gm_guidance.*`
* `essence.culture.*`
* `tone_levers.notes`
* **never** `metadata`, `taxonomy`, `structure`, `connections`, `synergy_engine`

And Bard outputs **patch-only**, not whole-file rewrites.

---

## Micro validation loop (required)

After applying Bard patch, rerun:

* schema validator
* lexicon validator
* reference validator
* completeness validator (platinum thresholds)
* narrative validator (Canticle)

If any regressions: rollback Bard patch.

This keeps the pipeline deterministic.

---

## Where Foreman fits

Foreman shouldn’t “judge vibes” manually — Foreman should:

* run NarrativeJudge scoring
* enforce accept threshold
* verify no regressions
* log the decision in the manifest:

```json
"bard_pass": {
  "attempted": true,
  "accepted": true,
  "score_old": 62,
  "score_new": 74,
  "delta": 12,
  "changed_paths": ["essence.overview", "essence.gm_guidance.hooks"]
}
```

This makes it auditable and batch-safe.

---

## Best pipeline placement

Put Bard late in Step 2:

**Step 2: Platinum Content Fill**

1. Completeness → Genesis
2. Narrative QA → Canticle / Runesmith fixes
3. **Bard optimizer pass (accept/reject)**
4. Micro-validate
5. Step 3 gate

Reason: Bard works best after the content is already “full”, so it’s polishing substance, not inventing structure.

---

## Recommendation

Do it — but only if we implement the **accept/reject gate** and keep Bard inside a **profile whitelist**.

If we skip that, Bard will cause drift and make batches unpredictable.

---

## Other refinements we should lock in now (so we don’t refactor again later)

### 2) Step 2 must not be allowed to create new globals

Genesis (and even Runesmith) will sometimes “invent” new tags/species/planets/etc.

We should enforce:

* **Step 2 can propose new registry entries via DeltaContract**
* **Step 2 cannot auto-write global registries**
* **Step 3 gate fails if Platinum requires globals that don’t exist and no accepted delta is present**

That keeps drift contained and makes batch runs safe.

---

### 3) Every agent patch should be followed by a deterministic re-validate (micro-loop)

To keep the pipeline stable and debuggable, we should do:

* apply patch ops
* immediately rerun the relevant deterministic validators
* update findings
* stop early if we’re oscillating (same diff repeats)

This prevents “Genesis filled content but broke schema” from slipping all the way to Step 3.

---

### 4) Step 0 should explicitly produce “Compiled Truth” artifacts

Step 0 shouldn’t just “validate”; it should *compile the build context*:

* `schema_resolution_report.json`
* `tag_index.json` (or in-memory + optional artifact)
* `registry_index.json` (URID → path/type/owner)
* `ownership_policy_snapshot.json`

Then every validator and agent uses *that* as the source of truth.

This is how we keep the system O(1) *at runtime* and deterministic *at build time*.

---

### 5) Step boundaries must be strict about what kinds of changes are allowed

This prevents content agents from trying to “fix structure” or structure agents from trying to “write lore”.

We should lock rules like:

* **Step 1 agents may only modify schema-canonical fields** (structure/reference repair)
* **Step 2 Genesis may only modify whitelisted content pointers** (completeness targets from profile)
* **No step can mutate registries directly** (only deltas)

---

## Verdict

### ✅ The pipeline works

The sequencing and responsibilities are correct for a compiler-grade build process.

### 🔧 We should refine it in 3 concrete ways before scaling to species

1. Make **Bard required/optional** a **profile decision** (not kernel).
2. Make **Delta/Registry behavior** a first-class, enforced rule of Step 2 and Step 3.
3. Make **Step 0 output “compiled truth artifacts”** that every other step consumes.

If we lock those, we can safely move into **species_core.profile.yml** next without discovering a second wave of faction-specific assumptions mid-batch.
