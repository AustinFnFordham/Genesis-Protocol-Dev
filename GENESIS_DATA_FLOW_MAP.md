# GENESIS PROTOCOL — Master Data-Flow Map (v1.0)

Mandated blueprint audit: `.UI_Ideas/` (27 documents, ~17.6k lines) cross-referenced against the 41 root schemas + 12 core-entity schemas. This map is the binding contract for every module. No module implementation may bind a field not traceable to a schema path here.

## 0. Global architecture (all systems)

```
                    ┌─────────────── TAURI SHELL (Rust) ───────────────┐
                    │  fs: Gold registry loader   ipc: patch channel   │
                    └──────────────────────┬───────────────────────────┘
   Gold YAML/JSON ──► registry Map<URID,entity> (O(1))                 
                                          │ boot snapshot              
                    ┌─────────────────────▼───────────────────────────┐
   AI GM / Forge ──►│  PATCH BUS: RFC6902 ops {op,path,value}         │──► undo log / replay
   (local, det.)    └─────────────────────┬───────────────────────────┘
                                          │ applyPatch(store)          
                    ┌─────────────────────▼───────────────────────────┐
                    │  React global store (single state tree)         │
                    │  slices: character / combat / codex / inventory │
                    │          campaign / ui                          │
                    └───────┬─────────────┬──────────────┬────────────┘
                       DOM datapads   R3F/WebGPU      ComfyUI node
                       (dataslate UI) (diorama/forge) (identity-locked portraits)
```

Principles carried from the vertical slice (proven working): schema-path binding only; broken URID refs render visibly; `metadata.status` drives GOLD/WIP chrome; GM/Player gate on `llm_guidance`/`ai_behavior`/`gm_guidance`; every state change is an RFC6902 op — the exact format the forge emits (verified in v0.1 QA).

## 1. Character Forge & Morality Engine

Blueprints: 01_State_Management, 02_Progression_Tree, 04_Visual_Character_Creation, 05_Force_Morality, 09_Narrative_Character_Creation, 14_Sub_Tree_Choice, 17_Legendary_Glow.

| Schema | Feeds | Key paths → components |
|---|---|---|
| `Character` | avatar state | `stats.*`→StatBlock; `visual_dna.identity_constants`→ComfyUI anchor lock; `visual_dna.gear_variables`→inpaint trigger on change; `alignment/morality`→aura shader + palette theme |
| `CharacterCreator` | creation wizard | step definitions → wizard stages; validation gates call the same jsonschema the forge uses (guardrail in-UI) |
| `SpeciesProgression` | species tracks | progression nodes → tree branches (Wookiee Feral Strength etc.) |
| `Class` / `Subclass` | tree roots | `level_progression[].features[]`(feature_id,feature_type) → node graph; `class_identity_profile`→theming |
| `CharacterClassFeature` / `Feature` | node payloads | feature registry ids resolved O(1); `effects[]`→tooltip mechanics |
| `CulturalFeatures` / `EnvironmentalAdaptations` | cultural branches | unlock conditions → branch gating |
| `Power` | power cards (03_Drag_Drop) | `alignment` → dark/light node gating + card indicators; scaling tiers → card upgrade animation |

Morality flow (05): FFG conflict events arrive as patches to `/party/N/ffg_pools/morality` → threshold crossings dispatch UI theme patch (`/ui/palette`) + shader uniform (corruption) + progression-tree gate recompute. Deterministic thresholds live in data, not UI code.

## 2. Living Diorama (Tactical Combat)

Blueprints: 10_Living_Diorama, 16_Tactical_Visual_Novel, 06_Animation, 07/13/19 roadmaps.

| Schema | Feeds |
|---|---|
| `Combat` / `CombatRules` | encounter state: grid, initiative order, round/turn pointers → holotable scene graph |
| `Action` / `Master_Action` | action economy UI; `range increments`/`cover` → projected overlays on grid |
| `Adversary` / `Creature` / `Squad` | tokens; `ai_behavior`+`llm_guidance` → GM whisper layer; conditional attacks (e.g. `attacker_has_surprise`) → lock badges (proven in v0.1) |
| `narrative_outcome` (.UI_Ideas schema — must be adopted into schemas/) | Triumph/Despair spend cards → environmental FX triggers (`trigger_event` enum drives when cards are playable) |
| `Status` / `Effect` | condition chips on tokens; durations tick on turn patches |

Combat loop: Rules Adjudicator emits patch batch per action resolution (`/combat/tokens/N/hp`, `/combat/grid/fx[]`) → R3F scene reacts (volumetric FX), datapad cracks at HP thresholds (`/ui/damage_state`).

## 3. Relational Codex & Nemesis Tracking

Blueprints: 12_Relational_Codex, 18_Interactive_Journal, 11_Narrative_Dialogue.

| Schema | Feeds |
|---|---|
| `CampaignState` | top-level session state: party, `current_location_id`, FFG pools (proven binding in v0.1) |
| `Faction_Core` (+ faction_core entity schema) | codex nodes; `connections.allies/enemies/neutral` → edge graph; `structure.ranks` → hierarchy |
| `Nemesis` | nemesis web: formation triggers, progression path (Emergence→Escalation→Confrontation), scars log → node evolution |
| `Lore` / `Background` | journal cards, discovery states |
| `narrative_outcome` | choice consequences → faction influence deltas → map border shifts |
| `SynergyRules` | Chaos Engine: rules host on ANY entity (Article 4); `trigger_tags`+`trigger_event` → codex event feed |

## 4. Holographic Vendor & Physical Inventory

Blueprints: 08_Visual_Inventory, 15_Holographic_Vendor, 03_Drag_Drop.

| Schema | Feeds |
|---|---|
| `Item` / `Object` / `Property` | 3D workbench assets; rarity → Legendary Glow tiers (17) |
| `Modification` | mod chips; drop targets = weapon slot sockets; drop = patch `/inventory/items/N/modifications/-` (RFC6902 add) |
| `CraftingRecipe` | recipe trees; ingredient refs resolve O(1) or render broken-chain |
| `Starship*` (Starship, StarshipAction, StarshipCareer, StarshipWeapon) | ship bay view: hardpoint sockets = StarshipWeapon slots; careers → crew role UI |

## 5. State slices ↔ schema ownership (Redux-style, per 01_State_Management)

| Slice | Owning schemas | Written by |
|---|---|---|
| `campaign` | CampaignState | GM agent patches |
| `character` | Character, SpeciesProgression, Power | player actions + adjudicator |
| `combat` | Combat, Action, Status, Effect | adjudicator only (deterministic) |
| `codex` | Faction, Lore, Nemesis, SynergyRules | Nemesis/Faction engines (background) |
| `inventory` | Item, Modification, CraftingRecipe, Starship* | player actions, vendor engine |
| `ui` | (no schema — ephemeral) | UI only; never persisted |

Rule: engines write ONLY to their slices, ONLY via the patch bus. The UI never mutates entity data directly — it proposes patches; the validation layer (same jsonschema as the forge) accepts or rejects. The guardrail is in the render path.

## 6. Gaps found by the audit (must be resolved before their modules)

1. `narrative_outcome-Schema.json` lives in `.UI_Ideas/`, not `schema/` — adopt formally (draft-07; suite is 2020-12 — needs upgrade on adoption).
2. No `GalacticMap`/`Region` schema — the codex map (12) implies one; planets exist but no node-graph schema. Needs an Articles-compliant schema task.
3. `Combat.schema.json` has no grid/coordinate block — 10_Living_Diorama needs `position/facing/elevation` per token. Schema task.
4. `visual_dna` (DNA-split prompting) is specified in the compendium and Character UI docs, but `Character.schema.json` must be verified to carry `identity_constants/gear_variables/environment_context` arrays (sandbox will surface this).
5. Two ComfyUI contracts needed: `portrait(anchor_id, gear_variables[], environment)` and `inpaint(region_mask, prompt)` — define as Tauri commands now, stub locally.
