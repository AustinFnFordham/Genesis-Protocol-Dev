# PHASE ONE — AUTHORITY AND TRUTH (2026-07-18)

The Engine Architecture Reconstruction is executing. The principle is now enforced in code:
**the AI interprets and proposes; deterministic engines validate and execute; no participant — including the AI GM — may bypass mechanical law.**

## Shipped

### GEN-ARCH-001 — `E:\StarWars\RUNTIME_AUTHORITY.md`
The law of state: truth hierarchy (immutable definitions → runtime instances → campaign snapshot → append-only event ledger → derived projections), the full authority matrix, the envelope contract, the intent pipeline, the chaos contract, RNG policy, and AI boundaries.

### GEN-ARCH-002 — Event envelopes (`src/state/events.js`)
Every mutation ships as an envelope: event_id, authority, intent_id, caused_by, visibility, rng_seed, RFC6902 operations. Append-only ledger — in-memory tail + persisted server-side to `api_bridge/saves/event_ledger.jsonl` (new `POST/GET /api/v1/ledger`). Rejections are ledgered too. Deterministic seeded RNG (`derivedSeed` from campaign seed + ledger length) ready for GEN-TEST-002 replays.

### GEN-ARCH-003 — Authority matrix, fail-closed (`src/state/authority.js`)
Per-engine write permissions as (authority, target, path-prefix). `store.dispatchEvent` is now the ONLY legal mutation path: authority gate → validate-before-apply RFC6902 → ledger → Chaos matcher. `revelation` and `ai_gm` are hard-rejected. The old raw `dispatchPatches` is gone from the public surface (`_applyPatches` is internal).

### GEN-RULE-001 — Universal intent contract (`src/state/intents.js`)
`submitIntent(type, payload)` with deterministic resolvers: `travel`, `equip_item`, `unequip_item`, `move_token`, `trigger_hazard`, `scene_action`, `scene_flag`, `end_turn`, `advance_character`, `ship_op`. Every UI call site rewired — GalacticMap, LivingDiorama, DialogueSystem, ProgressionTree, Workbench, ShipManagement, CharacterForge (DATA-mode probes under explicit `data_inspector` authority). Zero `dispatchPatches` calls remain in components.

### GEN-EXPLORE-002 — Travel cannot teleport
The map submits an intent; the exploration engine checks lane existence and blockade status, spends `travel_days` (each day advances the world), and only then does `campaign_engine`-sanctioned arrival land. Verified live: Coruscant→Mustafar (no lane) **rejected with route guidance**; Coruscant→Falleen (3.5d patrolled lane) accepted, 4 world phases elapsed.

### GEN-CHAOS-001 — Chaos as data (`src/state/chaos.js`)
Generic matcher over SynergyRules-shaped rules: tag AND/`_any` OR/`_exclude` NOT, `trigger_event`, conditions; arbitration Specificity → Exclusion → Priority; per-envelope consequence budget. **The fuel-canister incubation chain is now six data rules** (`worldPhase.js` contains zero hardcoded narrative). The matcher consumes accepted envelopes and routes candidate consequences to owning engines (`nemesis_engine` spawn/reveal, `providence_engine` obligation ticks). SynergyRules gold entities load from the registry automatically when populated.

### AI Content Pipeline (runtime Creator engine)
`POST /api/v1/generate/entity` on the bridge: brief → qwen2.5-coder:32b (Ollama, JSON mode) → **deterministic repair** (reuses `tools/build_genesis_sandbox.repair`) → **schema validation gate (zero violations or it does not exist)** → `data/campaign_local/` store with full provenance block (`model, brief, repair_ops, deterministic_fallback, tier`) → live O(1) registry, no restart. Gold is never touched. Ollama-down degrades to pure deterministic synthesis.

### Referential integrity (new forge gate)
`tools/check_referential_integrity.py` — walks every CampaignState, resolves party/companion/location refs against all stores, exits 1 on phantoms. **Caught exactly the audit's #1 blocker**: 3 phantom party members in "Shadows of Empire: Remnants". `tools/generate_phantom_party.py` ran Aran Voss, Tala Ren, and Kass Zoran through the full AI pipeline: **3/3 PASS, zero violations each** (qwen's proposals cleared the gate clean — ~25s per character), written to `data/campaign_local/` with provenance, served live by the bridge. The checker now reports **fully referentially complete (139 entities)**. "Shadows of Empire: Remnants" has a real party.

## Live QA (browser, localhost:1420)
- revelation-authority raw patch → **rejected, ledgered**
- inventory_engine writing `/world_phase` → **rejected** (cross-engine fail-closed)
- legal providence envelope → accepted, ledger +1
- teleport to unconnected node → **rejected**; legal lane travel → arrival + time passage
- canister flag + 6 phase advances → breadcrumbs, spawn, and **Kaelen, the Ash-Blind reveal all fired from data rules**
- 28 events in the server ledger; only console errors are the two intentional QA rejections
- `npm run build` green (4.3s)

## Found & fixed en route
- `bgs.repair()` returns `(doc, ok)` — both new consumers were treating it as `doc` (root-type violation storm)
- Integrity checker missed `party.character_ids` (dict-shaped party) — refs now collected recursively
- Ollama service was down and lost `OLLAMA_MODELS=B:\Ollama` when relaunched bare — restart script sets it explicitly

## Next (Phase Two seeds)
- Persist + replay: boot-time ledger replay for GEN-TEST-002 determinism proofs
- `scene_action` resolver growth (attack, power_use, item_use, craft, rest)
- Chaos rules → real SynergyRules gold entities through the forge (the baseline array is the projection contract)
- AI GM proposal loop: qwen submits intents through the same gate the player uses
