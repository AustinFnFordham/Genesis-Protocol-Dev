# GENESIS — Hybrid Retrieval, Graph, Map, Registry and Vector Memory Contract (HRM-001)
**Version:** 0.1.0 | **Status:** proposed, not deployed | **Date:** 2026-11-03
**Parents:** CIS-001, AAS-001, RUNTIME_AUTHORITY.md, ARTICLES_OF_CREATION.md

## First principle: yes, vectors may *represent* both the world and events
Support two logically separate semantic collections, with typed pointers to original data:
- **World semantic projection:** material/species/class/faction/location, rules and relationship descriptions; source URID, canonical version, content hash, access scope.
- **Event semantic projection:** factual event summaries, perception/belief records and character memory, with campaign ID, event IDs, sequence, world time, known-to scope, and summary provenance.

These are **world and event memory stores**, but embeddings are not the *authority* for actual HP, location, inventory, treasury, clock, initiative or event sequence. Vectors store representations, metadata, semantic neighborhoods, and references. Exact canonical data remains structured, versioned and validated. A single vector nearest neighbor hit is a search candidate, not proof.

## The structures are complementary
| Structure | What it is | Strengths | Limits | Role |
|---|---|---|---|---|
| Registry | Canonical identity/definition resolution (URID -> entity, versions) | Precise, O(1) indexed key access, schema/provenance | Not semantic; doesn't describe traversal itself | Authority and identity |
| Index | Auxiliary lookup structure (hash, inverted, B-tree, temporal/spatial) | Exact filters, ranges, high throughput | Only indexed features | Retrieval acceleration |
| Graph | Nodes and typed semantic edges, e.g. `contains`, `trusts`, `depends_on` | Multi-hop causality, constraints, relationships | Traversal can explode, cycles, edge quality | Causal neighborhood |
| Spatial map | Coordinates, regions, layers, paths, adjacency and geometry | Distances, visibility, navigation, territories | Not a complete semantic model | Space and movement |
| Vector index | Nearest-neighbor search over embeddings | Paraphrases, analogies, cross-entity concept search | Approximate similarity, hallucination-prone if trusted as fact | Candidate discovery |
| Event ledger | Accepted, ordered historical events and transitions | Auditability, deterministic replay, causality | Expensive full scans absent indices | History and proof |

A **map** may contain a graph of navigable regions, but geometry, spatial constraints and semantic identity are not interchangeable. The canonical Registry resolves the URIDs that these structures reference.

## Directed acyclic vs cyclic: the precise boundary
- **Acyclic (required):** the *causal/provenance ancestry* of accepted events. Each event may depend only on earlier committed events; `caused_by` must not create future/ancestor loops. Data lineage and materialization dependency graphs should also be cycle-checked.
- **Cycles are legitimate:** the world **relationship graph** (A trusts B, B fears A; faction A embargoes B which pressures C which supports A), navigation graph (routes can return to start), and semantic neighborhoods. They cannot generally be forced into a DAG without losing meaning.
- **Runtime propagation:** bound fan-out, visited-rule/event pairs, budgets and idempotency keys prevent cycles causing endless consequences.

## Referential architecture
```text
User/agent query
 -> scoped query planner
 -> exact URID/index lookup + keyword/BM25 + vector candidates (world/events)
 -> resolve candidate IDs through canonical Registry/ledger
 -> graph neighborhood with bounded hops and relationship types
 -> spatial/time constraints from map/temporal index
 -> ruleset/version/provenance/knowledge filters
 -> evidence pack with exact refs, hashes, revision and rejected alternatives
 -> deterministic adjudication / constrained LLM interpretation
```

**Pointers rather than duplicated truth:** vector entry `{vector_id, kind, source_urid/event_id, canonical_version, content_hash, tenant/campaign, visibility, text_excerpt, embedding, embedding_model_version}`. A query returns IDs; a validator dereferences exact records. Re-embedding never changes authority, only candidate search performance.

## Hard data rules
- `char_aero.base_hp = 100` lives in authoritative character/rules records. Spoken dialogue cannot change base HP to 200 without an approved progression/effect transition.
- If the ruleset defines temporary HP, HP maximum and current HP, each is distinct. UI reads the authoritative projected fields and never infers them from prose.
- Event logs are append-only. Semantic summaries cite event IDs and indicate omissions, speculation and actor-view scope.
- Event vector records must not create fictional events; an actor belief can be indexed but must remain typed `belief` and not `objective_fact`.
- Every cache or semantic index is rebuildable after schema/embedding changes, isolated by campaign and ruleset.
- No invented links: exact URIDs and edge endpoints must resolve; if source missing, fail closed or clearly mark as unverified discovery.
- Prevent leaks through semantic retrieval: GM-only records inaccessible to player-facing query; actor-specific memory only includes what actor learned.
- Semantic recall is *not deterministic replay*. Replay uses committed event order, ruleset/seed and snapshots; vector similarity may vary with model/index changes.

## Retrieval workloads and validation
1. **Exact factual lookup:** "Does Aero have Power X?" -> character inventory/powers and requirements, exact refs; do not use cosine to settle.
2. **Related rules:** "Can I redirect the blast?" -> keyword + vector candidates + graph references -> exact ruleset gates.
3. **World map:** "Can I reach sector B?" -> graph connectivity, coordinates and route rules, not embedding proximity.
4. **Character memory:** "Why does the companion distrust Aero?" -> event history + witnessed facts + beliefs + confidence, not narrator omniscience.
5. **Long events:** summarize bounded history with citation to event IDs; information loss diagnosed by recall test and reconstruction.
6. **New Forge content:** semantic novelty/analogical discovery suggests candidate tags/relationships, but schema/gold gate and owner approval preserve canon.

## Performance evaluation without arbitrary defaults
Measure: recall@k of known required URIDs, MRR/nDCG candidate ranking, exact-filter precision, false-canon rate (target zero), cross-campaign leakage (zero), permission leaks (zero), P50/P95 latency, token savings, dereference success, rebuild determinism, update staleness, event-memory citation accuracy. Compare exact-only, BM25, vector-only, hybrid+graph and hybrid+graph+time/spatial filters.

## Minimal deployment decision
Use existing SQLite corpus Registry as the known foundation for exact indexing and provenance. First test *without* a new infrastructure dependency. If semantic lookup measurably helps, experiment with an embedded vector index (e.g. SQLite vector extension or sidecar) and versioned event/world collections. Graph may initially be indexed adjacency lists rather than a separate graph server. Avoid choosing a specific vendor until benchmarks identify needs.

## Open questions / governance
- Canonical edge schema and graph index storage.
- Scope of event summary embeddings and actor belief indexing.
- Privacy/access tiers; licensed-source isolation; spoiler prevention.
- Update strategy (event-triggered incremental vs periodic refresh).
- Whether spatial map supports multiple coordinates/reality layers.
- When external DB or Lua/Rust bindings become justified.

**No code/schema migration occurs from this document alone.**