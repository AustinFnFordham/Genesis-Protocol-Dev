# Diegetic Frontend — Architecture & Data-Binding Map (v0.1)

Scope: what is required to build the datapad UI against the Genesis schemas, per project constraints (WebGPU/Three.js, dynamic JSON reactivity, identity-locked visuals).

## 1. Stack decision for v0.1 vs production

| Layer | v0.1 (today) | Production |
|---|---|---|
| Rendering shell | Plain HTML/CSS "dataslate" chrome | Three.js r160+ WebGPURenderer scene with the datapad as a textured quad/CSS3D layer |
| Data transport | Static `campaign_data.json` compiled from Gold YAML | Local API (`api/` exists in the hub) streaming JSON state deltas over WebSocket |
| Reactivity | Vanilla JS store + `render(entity)` re-paint | Same store contract; renderer swaps to GPU scene graph updates |
| Dice/FX | CSS animation stub | Three.js RNG dice rigid-bodies + FFG symbol overlay |
| Portraits | `ui.image_path` static | ComfyUI local endpoint: anchor portrait + IP-Adapter/PuLID lock, SAM inpaint on `gear_variables` change |

The binding contract below is identical in both — that's what makes v0.1 "production-shaped."

## 2. The binding contract (schema → component)

One rule everywhere: **components bind to schema paths, never to prose**. Every panel is a pure function of a validated entity dict.

### Universal header (all entity types)
| Schema path | Component | Notes |
|---|---|---|
| `metadata.id` / `id` | slate title chip + data-attr for O(1) registry lookups | dual-read handles legacy vs core schemas |
| `metadata.name` / `name` | display name | |
| `metadata.status` | GOLD/WIP badge | wip renders an amber "UNVERIFIED DATA" glitch overlay — the guardrail made visible |
| `taxonomy.era` / `era` | era chip(s) | |
| `taxonomy.tags` / `narrative_tags` | tag rail | tags are registry ids — clicking a tag = registry query, not text search |
| `ui.color_hex` | slate accent color | e.g. Shadowstalker locks `#1B1F24` |
| `ui.icon_path`, `ui.image_path` | icon/portrait slot | portrait slot is the ComfyUI hook point |

### Faction (faction_core)
| Path | Component |
|---|---|
| `essence.overview`, `essence.ideology` | INTEL tab body |
| `structure.power`, `structure.ranks[]` | hierarchy ladder widget |
| `connections.headquarters_id` | link chip → loads location slate (file-chaining in action) |
| `connections.key_npc_ids[]`, `connections.relationships[]` | relationship graph list |
| `synergy_engine.rules[]` | "CHAOS PROTOCOLS" collapsible — render `llm_guidance` as GM whisper text |

### Creature / Nemesis (creature_core)
| Path | Component |
|---|---|
| `stats.*` | stat block grid (STR/DEX/... with SW5e modifiers computed client-side) |
| `attacks[]` | attack cards; render `condition` fields (e.g. `attacker_has_surprise`) as lock icons — mechanically gated UI |
| `ai_behavior`, `llm_guidance` | GM-eyes-only tab (hidden in player mode) |
| `narrative`, `flavor_text` | dossier tab |
| `image_generation.base_prompt` | portrait pipeline seed |

### Species (species_core) — wookiee
`traits[]` → trait cards with mechanics hooks; `cultural_matrix`/`culture` → culture tab; progression example → level table.

### Class / Subclass
`levels[]`/`features[]` → progression table bound to `CharacterClassFeature` registry ids; subclass slate chains to parent class via `parent_id`.

### Campaign state (the QA click-through)
`CampaignState.schema.json` drives the top bar: party members, location id (chains to location slate), FFG pools (Duty/Obligation/Morality as gauges). v0.1 ships a mock `campaign_state.json` conforming to that schema.

## 3. Hard requirements extracted

1. **Registry loader**: UI boots by loading a manifest of gold entities into a `Map<urid, entity>` — O(1) lookups, mirrors the backend registry. All cross-entity rendering resolves pointer ids through it; unresolved ids render as red "BROKEN CHAIN" chips (visual ref-validation).
2. **Schema-version tolerance**: components read via small accessor helpers (`getId(e)`, `getName(e)`, `getTags(e)`) so legacy-shape and core-shape files both render during migration.
3. **State reactivity**: single `dispatch(patch)` entry applying RFC6902 patches to client state — the same patch format the forge emits, so backend deltas replay natively in the UI.
4. **Player/GM view flag** gating `ai_behavior`, `llm_guidance`, `gm_guidance`, trigger thresholds.
5. **Visual pipeline hooks** (stubbed in v0.1): portrait slot calls `/comfy/portrait?anchor=<id>` — contract only, no local diffusion dependency for QA.

## 4. Foreseen blockers (honest list)

- **Mixed schema generations**: creature/class/subclass gold outputs still carry legacy shapes until their platinum profiles fully restructure them; the accessor layer absorbs this but true prod UI wants one shape.
- **WebGPU**: needs Chrome/Edge on the RTX box (fine locally; not in this sandbox). v0.1 falls back to DOM rendering.
- **No API server yet**: `api/` routes exist in the hub but weren't audited; v0.1 uses static JSON + `python -m http.server`.
- **Portrait pipeline**: ComfyUI endpoint not stood up today — slot renders placeholder with the base_prompt shown.
