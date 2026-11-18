# Claude Implementation Prompt — Genesis Turn Builder 4 + WHISPER

**Paste the text below into Claude and attach `GENESIS_TB4_WHISPER_DESIGN_CONTRACT_v0.1.md`.**

---

Claude, continue Genesis Protocol in the existing repository **`AustinFnFordham/Genesis-Protocol-Dev`**.

## Your work order

Implement a small, testable, backward-compatible release candidate for **Turn Builder 4** and **WHISPER**, strictly grounded in the attached **`TB4-WHISPER-001 v0.1.0` design contract**. Read the **entire** contract, including the source-of-truth inventory, conflict register, acceptance matrix and protected paths, before changing code.

**These names mean different things.** Turn Builder 4 is the **player-facing declaration and plan composer**. WHISPER is the **AMD/emotional state, intention, memory, and appraisal umbrella**, not the suggestion generator. Don't rename them or collapse either into the generic GM model. Contextual suggestions are a pure, optional builder service.

### 0. Inspect/reconcile first

1. Fetch the current relevant branches, commit tips, and working-tree status. Examine at least `staging/mobile-test`, `integration/mobile-test-build`, `dev/encounter-controller`, and any newer applicable release candidate. Select a fresh isolated implementation branch from the most complete, safe source **without losing or duplicating existing work**. Pin and report the chosen base SHA and differences.
2. Reopen the exact repo sources identified in contract §1; don't assume the attached contract is synchronized with every latest branch. Verify all existing turn builder, encounter, recovery, provider integration, and Datapad features.
3. Identify which portions of Turn Builder 4 are already present. Produce a concise current-vs-required gap inventory **before writing new modules**. Don't reimplement a working sequencer, event store, validator, provider adapter, OAuth gateway, or dice machine.
4. Establish a read-only protected-path baseline of Hask Meadow, its dice/ledger files, and any live publication artifacts. Do not mutate them.

### 1. Implement the user-facing slice first

- Preserve `turn-contract/3` as the accepted input/validation foundation, with backward-compatible optional v4 fields rather than replacing it.
- In the existing Datapad/composer, give **every appropriate category** a contextual suggestion area **and editable Custom box**: primary, bonus, secondary activity, movement, speech, object interaction, reaction, optional emotion, intention, conditional sequence. Custom text must survive parsing and submission unchanged.
- Preserve ordered sequence/branch/pending-step mechanics, hand/position feasibility, resource costs, NPC autonomy, explicit interruptions, and freeform declarations. Explain unavailable options rather than silently altering plans.
- Add a small deterministic suggestion-selector module (zero model calls). Filter by visible context, authorization, available resources, actual grants and declared player style; show up to four grounded options and always Custom. Do not infer secret NPC state or fabricate feats/powers. Integrate this module into the existing static HTML build process if separate.
- Implement a **bonus-action Taunt demonstration in an isolated opt-in fixture**. Taunt is intended as a mechanical bonus action with player-authored text/gesture; ordinary insults remain costless brief speech. Do not invent resistance rules, DCs, forced attacks, target mind control, cooldowns or global grant. The current encounter ruling is still provisional. Show the owner any remaining rule decision before live adoption.
- Treat **Secondary Activity as a UI/semantic grouping, not an extra free action slot**. Individual steps keep their actual mechanical costs and ownership.

### 2. Add the WHISPER precursor without overbuilding AMD

- Add optional start-of-turn *felt emotion*, *outward expression*, *intent/motive*, and *private reflection*. **Unspecified** must differ from calm, numb, or none-felt; don't diagnose or stereotype a character from one observation.
- Distinguish `thought/hypothetical`, `player-declared inner state`, `intent`, `speech`, `attempt`, `accepted outcome`, and `GM presentation`. Viewing or dismissing an intrusive/“What if...?” prompt is never canonical evidence. Use static/cached/on-demand optional text, **not automatic model calls per suggestion**.
- For PCs, WHISPER generates evidence-backed **candidate** emotional transitions after accepted events, but cannot impose a subjective feeling. Provide `accept/edit/reject/defer` semantics in a noncanonical fixture or private projection; actual accepted state, if supported, still goes through the existing gateway and correct scope.
- Separate **moral**, **psychological**, and **social** appraisals. An angry feeling isn't a dark-side deed; attempted harm can matter even on a miss; inability to save someone isn't intentional cruelty. A deliberate omission can matter only when knowledge, feasibility, risk, and alternatives are established.
- Do not invent AMD coefficients, alignment penalties, trauma diagnoses, stress modifiers, or permanent personality changes. Keep the original experimental math intact and documented as not yet calibrated.

### 3. Minimum implementable Algorithms A / B / C

- **A — Evidence-grounded knowledge:** Typed, source-linked envelopes that distinguish accepted fact, claim, observation, belief, intent, attempt and outcome. Actor-scoped visibility and provenance must be enforced *before* ranking/retrieval. A false accusation is not world truth; private emotion is not NPC knowledge.
- **B — Event-grounded episodic memory and appraisal:** Link memories to accepted event IDs, actual observers, world time, and information channels; deterministic retrieval; modest appraisal candidates. Reuse the existing `npc_review.py` structural checks. Do not replace all NPC logic with a new LLM agent.
- **C — Typed causal dependency resolution:** Use canonical entity IDs and registered relation types/predicates; eligible domain proposals, dependency order, bounded work, explicit no-effect when evidence missing, and existing authority/commit. Respect `CIS-001` and the Chaos doctrine as *proposals*, not silently approved world rules.

If any part lacks an in-force schema or domain authority, deliver a **pure, noncanonical evaluator with documented fixtures and integration seam**. Do not fake full backend integration, bypass ledger validation, or start a new persistence layer. SID population/ERA simulation is explicitly out of scope except capturing structured exposure events for later use.

### 4. Automated tests and acceptance

Run the *existing full relevant regression suite*, then add deterministic scripted tests drawn from contract §7, especially:

- Each category has Custom, original literal player words survive, and any cost comes from validated rules rather than from the UI label.
- Approved sandbox Taunt costs exactly one bonus action; unapproved Taunt cannot silently become a granted mechanic; free speech remains free.
- Secondary Activity doesn't grant an additional action or another actor's turn.
- Existing scene sequencing, branches, pending steps, reaction prompts, movement/hand checks, equipment, and encounter safeguards still work.
- Unspecified emotion isn't automatically interpreted; private fear and controlled expression remain distinct; hypothetical thoughts have **zero canonical effect**.
- Attempted harmful act that misses differs from a failed good-faith rescue; deliberately withholding help requires evidence of ability and knowledge.
- Same false accusation heard by twelve people remains a claim, not fact; no hidden/private knowledge leakage; witness/no-witness metamorphic variation.
- Causal rules reject ghost relations, unsupported triggers, forbidden domain writes, and premature propagation.
- Repeated request IDs, interrupted recovery and provider handoff preserve exactly one accepted result and no rerolls.
- Legacy `turn-contract/1`–`/3` fixtures and old saved drafts remain compatible.
- Run mobile/iPad-size UI regression/visual review with a static local preview if test tooling exists.

**Cost constraint:** Use zero paid model/API calls. Scripted providers, offline unit/integration tests, local browser tests and covered Codespaces compute are allowed. Do not incur hosting charges, require an API key, start a public beta, or deploy.

### 5. Release safety and checkpoints

- Work **only in a new isolated branch**; no force pushes, no merge to main/live, no deployment, no changing the active Oracle/OAuth/MCP adapter.
- **Never modify or advance Hask Meadow**, including `campaigns/starwars_litrpg/runs/hask_meadow_r2/` and its hidden/public records. Do not reroll history or edit accepted campaign artifacts.
- The staging MCP was last read at `shared-1`, revision `40`, ledger `evt_0043`, pending action `shared-0002`, with `storage_recovery_required=true`. This is *context*, not a write authorization. Do not process that pending turn or claim recovery is resolved as part of this milestone.
- Don't silently activate the provisional November 15 encounter ruling or assert full CIS/SID/AMD runtime maturity.
- Keep commits small and reviewable: baseline/contract integration, player composer, WHISPER/evidence fixtures, tests. If one section is blocked, complete the safe independently testable sections and report what wasn't possible.
- Keep diagnostics and proposed user-visible fields free of GM-only secrets. No browser OAuth client secrets or privileged GM tokens.

### 6. Required report at end

Report: chosen branch and parent SHA; current-vs-required feature matrix; exact file changes; implementation of each area with `implemented / pure-fixture / blocked`; tests with commands and pass/fail totals; client preview evidence; protected-path and canonical-digest checks; zero-cost verification; conflicts or missing owner decisions; commit hashes; deployment status **HOLD**; and the next smallest UAT step for the project owner.

The owner is the only human playtester for now. Don't assume a public group or invent user-acceptance scores. **The definition of success is that a player can construct a cinematic, conditional plan in their own words, select a meaningful intent/emotional context, and trust Genesis to enforce costs and consequences without taking their agency or changing canon arbitrarily.**

**Begin by inspecting the repo and writing the concrete implementation delta, then do the work and tests in this same session. No production changes.**

---

**End of Claude implementation prompt v0.1.**
