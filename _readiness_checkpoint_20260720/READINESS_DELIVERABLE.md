# Genesis Protocol — Rules & Data Readiness Deliverable
Generated 2026-07-20. Deterministic work only. No LLM enrichment, no broad promotion, no Campaign Genesis.

## 1. Reconciled Inventory (authoritative; supersedes 380/956/150/159)
- physical files under data/wip: 412
- entity files / parsed entities: 180 / 180 (unparseable: 0)
- validation: PASS 3 / WARN 18 / FAIL 159
- quarantined (platinum): 19
- total findings: 1584  | total blockers: 1037
- distinct URIDs: 102  | duplicate URIDs: 48
- unresolved references (distinct): 32
Reconciliation: 180 = parsed entities. 412 = physical (incl. reports/summaries/manifests/backups). "380" was a loose estimate; "956" was the 2026-07-12 blocker count (now 1037); 150 was 07-12 fails, 159 current.

## 2. Schema Authority Matrix
Two schema dirs:
- E:\StarWars\schema : 40 files, metaschema-VALID 15, INVALID 25 (section-header keys like 'SECTION 7: IMAGE GENERATION and UI' / 'MIGRATION NOTE:' where subschemas belong). Annotated design docs, NOT machine-valid JSON Schema.
- forge_v3/schemas : 65 files — the machine-usable set the forge validator loads (core WIP gates + rich runtime schemas).
Per-family canonical (recommended): faction->faction_core (WIP) / Faction (runtime, E:\ copy INVALID); feat->feat_core; approach->approach_core; asset->asset_core; location->location_core; planet->planet_core; species->CONFLICT species_core (minimal WIP) vs Species (rich runtime) [recommend WIP-gate vs runtime-projection split]; npc->npc_core.
GATE: 25/40 E:\schema files fail metaschema -> per directive NO general migration against them until fixed. forge_v3 core set is the safe target.

## 3. Dry-Run Migration Manifest (no files moved)
180 entities, 127 misrouted. Families: feat 108, location 20, faction 11, approach 10, asset 10, npc 9, planet 5, species 4, subclass 1, creature 1, unknown 1.
Full per-file manifest: 04_dryrun_migration_manifest.json.

## 4. Reference-Impact Report
- 47 misrouted files have inbound references -> moves must rewrite refs, not just relocate.
- ~125 files carry DUPLICATED urids (48 distinct ids duplicated across two dir trees). Dedup decision REQUIRED before moves.
- 32 unresolved outbound references (faction rank feature_choices point at feat ids with no entity file).

## 5. fac_black_sun Before/After Evidence
- Was ALREADY metadata.status: gold before this session (not created by me). My change: cosmetic re-dump only (transforms=[]). Passes gold 0 findings.
- Never moved to data/gold; NOT in runtime allowlist. All 11 factions RESTORED to pre-migration state. Promotion PROVISIONAL.
- Evidence: fac_black_sun.BEFORE.yml / .AFTER.yml / .validation_gold.txt ; 01_faction_mutation_report.json.

## 6. Campaign-Isolation Status (NOT isolated — defect confirmed)
- store.js journal is a SINGLE GLOBAL array, not keyed by campaign_id.
- transcript/gmFeed = projection of ONE server-owned active save_state.json, not per-campaign ledgers.
- On campaign load the store APPENDS and does NOT clear journal/gmFeed -> Aero bleeding into Shadows is real at the state layer.
- Positive: phantom-party load guard already exists.
Required: campaign-scope ledger+transcript+journal+projections+scene+party+crawl+session_context; on switch clear->load->rebuild; server per-campaign ledger/transcript files.

## 7. Item-Taxonomy Contract
- Item.schema.json (both dirs) HAS item_type enum: Weapon, Armor, Gear, Consumable, Artifact, Droid_Part, Starship_Component, Trade_Good, Other.
- Defect: sheet buckets by ARRAY NAME (equipment.weapons[]) with NO check that members are item_type==Weapon.
- Enforce at 4 layers: (1) schema: weapons[] items must be item_type==Weapon; ships are Starship not Item; (2) validator rule ITEM_TYPE_SLOT; (3) runtime projection routes by item_type not array; (4) UI selectors filter by item_type.
- Cases: YT-2400 -> Starship (ship); flight jacket -> Armor (apparel); lucky sabacc chip -> Trade_Good/Gear (trinket).

## 8. Updated Validation Burn-Down
- After restoring factions to pristine: PASS 3 / WARN 18 / FAIL 159, blockers 1037 (net-zero vs pre-session; earlier faction burn-down reverted per directive).

## 9. Remaining Human Decisions
1. Ratify canonical schema source (recommend forge_v3/schemas) and fix the 25 metaschema-invalid E:\schema files (strip SECTION/MIGRATION-NOTE keys).
2. species_core vs Species: ratify WIP-gate vs runtime-projection split or unify.
3. Duplicate URIDs (48 ids / ~125 files): canonical location per entity; dedup before moves.
4. Unresolved refs (32): author missing rank feats OR mark feature_choices draft/incomplete.
5. tag_stub: confirm map to explicit draft/incomplete status (not strip).
6. tag_align_neutral: schema-change (add neutral) vs data-change (map grey) — table ruling.
7. Owner/target convention for misrouted owned content nested under factions.
8. fac_black_sun: keep provisional-gold or fully revert (was already gold pre-session).
