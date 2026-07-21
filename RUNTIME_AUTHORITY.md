# RUNTIME AUTHORITY — The Law of State (GEN-ARCH-001, v1.0)

Every state path has exactly one authoritative owner. This document is that registry.
Terminology per the Engine Architecture Reconstruction: Engine / Agent / Resolver / Module / Registry Entity / Runtime Instance / Campaign State / Event Ledger are NOT interchangeable.

## 1. The Truth Hierarchy

| Layer | What it is | Mutability | Where it lives |
|---|---|---|---|
| **Immutable definitions** | Registry Entities: schemas + Gold content (species, item templates, faction definitions, abilities, recipes, SynergyRules) | Read-only at runtime. Changed only by the Forge pipeline (validate → gold gate) | `forge_v3/schemas/`, `forge_v3/data/gold/`, `forge_v3/data/sandbox_gold/` |
| **Mutable instances** | Runtime Instances: the player's particular blaster, Malice's current trust, this campaign's Falcon, a spawned nemesis | Only via accepted event envelopes | `campaign.characters` (in save) + in-memory registry overlay |
| **Campaign snapshot** | The authoritative CampaignState of one campaign | Only via accepted event envelopes with campaign-writing authority | `api_bridge/saves/save_state.json` (+ timestamped snapshots) |
| **Event ledger** | Append-only, causally ordered envelopes explaining every accepted mutation | Append-only. Never edited, never deleted. Corrections are new events | `api_bridge/saves/event_ledger.jsonl` + in-memory tail |
| **Runtime projection** | The in-memory O(1) `Map<URID, entity>` + zustand state tree | Derived. Rebuilt from definitions + snapshot + ledger at boot | app store / API bridge memory |
| **Revelation projection** | What the UI shows | Derived from runtime projection, filtered by knowledge/visibility. Owns ONLY ephemeral UI state (selection, tabs, overlays) | React component state |

**Rule:** anything below the line of "derived" may be thrown away and rebuilt. Anything above it may only change through an envelope.

## 2. The Authority Matrix (enforced in code — `src/state/authority.js`)

Write permission = (authority, path-prefix) pairs. Unauthorized patches **fail closed** and are ledgered as rejections.

| Authority | May write (path prefixes) |
|---|---|
| `campaign_engine` | campaign: `/campaign_id`, `/name`, `/created_at`, `/party`, `/current_location_id`*, `/characters`, `/flags`, `/scene`, save metadata (*only via travel outcome events from `exploration_engine`) |
| `chronicle_engine` | ledger append + `/journal` rendering. Never gameplay outcomes |
| `rules_engine` | Authorizes/rejects outcomes. Writes nothing directly |
| `combat_engine` | entities: `/grid_state/**`; characters: `/hit_points`, `/conditions`, `/strain`, `/wounds` |
| `social_engine` | scene state; requests relationship changes via `relationship_engine` |
| `relationship_engine` | entities: `/trust_meter`, `/relationships/**`, relationship instances/memories/stages |
| `companion_engine` | companions: `/goals`, `/decisions`, personal progression. Trust via relationship_engine |
| `faction_engine` | factions: `/resources`, `/plans`, `/investigations`; map: `/nodes/*/territory_control/**` |
| `nemesis_engine` | nemeses: full lifecycle (`/progression_stage`, `/revealed`, `/threat_level`, `/plans`, grudges) |
| `inventory_engine` | characters: `/equipment/**`, item instances, ownership, durability |
| `progression_engine` | characters: `/level`, `/xp`, `/features/**` |
| `exploration_engine` | Resolves travel → emits location-change outcome (committed by campaign_engine); discovery states |
| `providence_engine` | campaign: `/world_phase`, `/ffg_pools/**`, clocks, scheduled events; requests subscribed engine actions |
| `chaos_engine` | NOTHING directly. Emits candidate-consequence events only |
| `starship_engine` | campaign: `/ship/**` |
| `creator_engine` | May ADD new validated entities (campaign-local, provenance-tagged). Never mutates existing ones |
| `ai_gm` (agent) | NOTHING. Submits structured intents/proposals; consumes knowledge-filtered context |
| `revelation` (module layer) | NOTHING authoritative. Submits player intents; owns ephemeral UI state only |

## 3. The Event Envelope (GEN-ARCH-002 — `src/state/events.js`)

Every accepted mutation ships as:

```json
{
  "event_id": "evt_<ulid>",
  "campaign_id": "...",
  "event_type": "travel_completed | hazard_triggered | ...",
  "world_phase": 18,
  "world_time": "iso-or-campaign-clock",
  "actor_id": "entity_or_system",
  "authority": "one_of_the_matrix_rows",
  "intent_id": "int_<id> | null",
  "caused_by": ["evt_prior"],
  "visibility": "public | gm_only | character:<urid>",
  "schema_version": "1.0.0",
  "ruleset_version": "1.0.0",
  "rng_seed": 12345,
  "target": "campaign | <urid>",
  "operations": [ RFC6902 ],
  "journal_payload": { "kind": "...", "text": "..." },
  "diagnostics": {}
}
```

RFC6902 remains the mutation language; a raw patch without an envelope is illegal.

## 4. The Intent Pipeline (GEN-RULE-001 — `src/state/intents.js`)

`Revelation → submitIntent(typed intent) → resolver (deterministic) → outcome {accepted, envelopes[]} | {rejected, reason}`

Typed intents (v1): `travel`, `move_token`, `equip_item`, `unequip_item`, `scene_action`, `end_turn`, `advance_character`, `assign_station`. Growing set: attack, power_use, item_use, craft, rest, interact.
Travel resolution pipeline (GEN-EXPLORE-002): destination intent → route options (lanes) → legality → risk → time advancement → world phase → arrival event. **`current_location_id` cannot be written except by an accepted travel outcome.**

## 5. The Chaos Contract (GEN-CHAOS-001 — `src/state/chaos.js`)

Chaos rules are DATA (`SynergyRules` instances: `trigger.actor_tags` AND, `*_any` OR, `*_exclude` NOT, `trigger_event`, priority by specificity→exclusion→priority). The matcher consumes accepted envelopes, aggregates context (location tags, faction ownership, wanted status, witnesses), and emits **candidate consequence events** — never state. Owning engines resolve their candidates. Deterministic match order; per-phase budget caps prevent consequence storms (GEN-WORLD-001 seed).

## 6. RNG Policy
Campaign carries `seed`; every resolver that rolls derives from `(campaign.seed, event_ledger.length)` — same seed + same intents ⇒ identical outcomes (GEN-TEST-002 requirement).

## 7. AI Boundaries
The AI GM and the Creator pipeline **propose**: intents, narration, and candidate entities. Every proposal passes the same deterministic gates (schema validation, authority matrix, rules resolution) as player input. A model response that fails validation is discarded and ledgered as a rejected proposal — it can never become truth by insistence.
