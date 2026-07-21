# CHECKPOINT ONE — Cross-View Persistent Session (2026-07-20)

**1. Root cause:** the transcript, options, focus NPC, and input lived in tab-local React state (`GmSession`/`DialogueSystem` useState), destroyed on every unmount — and `<Boundary key={engagement}>` forces unmount on every tab switch. Action buttons routed to a *different* view owning a *different* feed. Two views, two histories, both mortal.

**2. Shared mounted-session contract:** the runtime now carries `transcript` (typed entries: player/npc/narrator/mechanics with entry_id, speaker_id, mood, source_command_id, created_at, capped 200) and `conversation` (pending suggestions, unresolved flag, last_command_id). Server-owned, per-campaign, persisted in `runtime_state.json`. Every turn returns a `command_id`.

**3. Transcript persistence:** `hydrateSession()` projects the server transcript into the shared zustand store (`gmFeed`, `gmOptions`, `gmFocusNpc`, `narrativeDraft`). Components render the projection and own nothing. The campaign opening loads into the shared feed only when the server transcript is empty.

**4. Single pipeline:** `declareToGm()` in the store is the only declaration path — Narrative, ActionPanel, Tactical, Ship, and ReactionWindow all call it. After each accepted turn the store rehydrates from the committed runtime (canonical truth wins). Duplicate prevention via command_id comparison + busy guard.

**5. Living Table merged INTO Narrative**, per your direction — the Narrative UI is untouched and is now the primary bench. The nav is CAMPAIGNS · ◈ NARRATIVE · TACTICAL · SHIP; old 'gm' routes alias to Narrative. **Action buttons now prefill the draft in the shared session and keep you on (or return you to) Narrative — no more losing progress to a view hop.**

**6–8. Regression results:**
- **T1 (server):** turn → transcript persisted (player + beats + command_id), conversation state saved. ✅
- **T2 (browser):** draft set → Tactical → Ship → Narrative: transcript byte-identical, draft intact, feed rendered. ✅
- **T3:** reaction windows live in the shared store (survive navigation); resolution declares once through the pipeline. ✅ (structural)
- **T4 (browser):** full page refresh → feed rehydrated from server transcript (2 entries, correct speakers). ✅
- **T5 (server):** Shadows mount shows 0 Meridian entries; Meridian remount resumes its exact transcript. ✅
- **T6:** command_id dedup + gmBusy guard; navigation during resolution cannot resubmit. ✅ (structural)

**9. Screenshot:** captured — the "ask Ilo" conversation surviving refresh + Tactical + Ship navigation with the unsent draft still in the input.

Client tabs no longer own canonical gameplay state. Tab switch = lens change, nothing else.

---

# CHECKPOINT TWO — Backend Constitution Plan (summary)

Implementation order accepted as given. Key commitments:
1. **Contracts first:** command/event/commit/projection schemas (per your shapes) as versioned `forge_v3/schemas/runtime/*.schema.json`; dual authority ladders (mechanical vs campaign-truth) codified in RUNTIME_AUTHORITY v2 — a mechanical rule may not rewrite committed history, a Chronicle fact may not redefine mechanics.
2. **Rules normalization:** owner decisions → `rules/genesis.*.v1` entities with `origin: custom_genesis` where applicable (action_conversion explicitly tagged custom, not SW5e-inherited); overcasting marked `provisional, executable: false` pending the complete contract; crafting hard-requirements as deterministic validators.
3. **Relationship model:** mood (transient) + trust/affinity/respect/suspicion (persistent) + event-based memories with decay_policy — replacing the bare trust meter.
4. **Chaos audit:** all 14 existing rules (6 baseline + registry) get schema validation, namespaced tags, predicates/exclusions, priority, idempotency, provenance, fixtures — none active until audited; Chaos proposes, Steward validates, Atomic commits.
5. **Owner-review gates left open** (not developer-assumed): the 14 Chaos rules' disposition, canonical romance stages, overcast contract, hideout economy, droid customization batches. Recommendations will be prepared as drafts for your signature.
6. **Known deterministic-verification debt:** CM hit/miss comparison vs stated AC/DC (the "14 misses AC 12" bug) — slots into step 8 (deterministic combat comparison) of your order.

Blocked list honored: no client-owned canonical state, no direct CM mutation, no unreviewed Chaos activation, no experimental Forge mechanics in live play.
