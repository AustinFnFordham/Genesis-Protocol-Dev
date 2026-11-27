# Genesis progression schema and authoring specification (CC-008) — SANDBOX

- **Tree schema:** `schema/genesis_progression_tree.schema.json` (`genesis-progression-tree/0.1`).
- **Runtime:** `framework.js` (tracks, requirements, ledger, transactions) and `curves.js` (curve evaluator and tables).
- **Extends** CC-007's `mastery.js` (`genesis-mastery/0.1`), which is unchanged.

## 1. Vocabulary (never conflated)

| Term | Meaning | Where it lives |
|---|---|---|
| **Track** | One levelable progression. It either owns XP (`xp_quantity`) or follows another track (`driven_by`). | Tree document, `track` |
| **XP quantity** | The ledger quantity a track consumes: `class_xp`, `mastery_xp`, `discipline_xp` or `none` | `track.xp_quantity` |
| **Node** | An authored unlock at a level | `nodes[]` |
| **Grant** | What a node gives (see the grant types below), with its `authority` | `nodes[].grants[]` |
| **Executable action profile** | A combat/engine profile id (for example `escape_grapple`). Owning a grant of `type: profile` makes it available; legality is still Atomic's. | `grants[].type = profile` |
| **Choice group** | A set of nodes offered at milestones; `picks`, `offer_size` (default 3), `exclusive` | `choice_groups[]` |
| **Milestone** | A level at which a track offers choices (`cadence`, `choice_groups[].milestones`) | Track and group |
| **Requirement** | Explicit `all` / `any` / `any_of_group` / `not` over node, cross-tree node, track level, feature or training | `nodes[].requires` |
| **Unlocked feature** | A feature or profile entitlement recorded on the character (`features[]`) after a committed selection or core grant | Character state |

**Grant types**

| Type | What it is |
|---|---|
| `feature` | An entitlement |
| `profile` | An executable action profile |
| `capacity` | A numeric value |
| `training_opportunity` | Eligibility to train only; never the power itself |
| `track_unlock` | Opens an archetype |

## 2. Layers

| Layer | Typical XP | Typical cadence | Notes |
|---|---|---|---|
| `class` | `class_xp` (a threshold table) | Per node level | Character/class level. **Never the same number as a mastery level.** |
| `archetype` | `none`, driven by the class | 3/6/9/12/15/18 when authored (sources vary, so it's per tree) | Opened by a class `subclass_entry` node (a `track_unlock` grant) |
| `species` | `none`, driven by the class, or its own track (owner decision) | 5/10/15/20 | |
| `proficiency` | `mastery_xp` | 5/10/15/20 | Straightforward improvements |
| `specialized_mastery` | `mastery_xp` | 3/6/9/12/15/18 unless authored | Full-tree choices. Telekinetic Control uses 5/10/15. |
| `parent_linked` | `none`; shares the `parent` track's level | Its own choice groups | For example, escape and release under grappling |
| `discipline` | `discipline_xp` | Per pool | Aggregated from evidence by the allocation policy; never duplicates a mastery track |

## 3. Every levelable track declares

- `start_level`, `max_level`;
- a `curve` (versioned id with parameters, or an explicit cumulative `table`) and a `curve_status`;
- `cadence`;
- `evidence` (accepted authorities, eligible event types with their XP, required facts, `never_from`);
- `restrictions` (classes, species, required features);
- `provenance`.

**Curve status:**
- `authoritative`: from an approved source.
- `owner_proposal`: numbers given by the owner for simulation.
- `candidate`: generated for comparison only; **never adopted silently**.

## 4. Status and authority

`status`: `approved`, `approved_provisional`, `candidate` or `scaffold`.
- Only approved content may be promoted.
- Candidate nodes are usable **only in sandbox fixtures**.
- Each grant names its `authority`: `class`, `archetype`, `species`, `mastery`, `discipline`, `training` or `campaign_ruling`. The validator checks that the authority matches the tree's layer (§G).

### 4.1 Provenance class and executable grants (CC-008.1)

`status` says whether content may ship; `provenance_class` says **where its mechanics come from**. They are independent.

| `provenance_class` | Meaning | May carry `executable: true` grants? |
|---|---|---|
| `source_backed` | Stated in a cited source; not yet engine-implemented | No |
| `legacy` | Read from a legacy record (possibly reinterpreted by the adapter) | No |
| `proposed` | Authored here; not owner-approved. **A missing class is treated as `proposed`.** | No |
| `implemented` | Backed by an engine profile | Yes, if every `profile:` grant names a profile in `combat_slice/catalog.json` |
| `owner_approved` | Owner signed off | Yes, with `approval {by, on, ref}` |

An executable grant is also blocked, whatever the class, when:
- the node is `placeholder: true` (the source has no real mechanics, e.g. Sentry's `grant_ability` "Grants a special ability", or Echani tiers' free text);
- the node carries `legacy_reinterpretation` without `legacy_validation {by, on, decision}`;
- the tree lists `source_copies` with differing hashes and no `source_choice {chosen, by}` (e.g. the two Echani copies).

`framework.executableBlockers()` implements these rules. The validator reports them as errors, and `choices.statusOf()` re-checks them at runtime, so a tree that skipped validation still can't execute such a grant. In an `approved` or `approved_provisional` tree, every node must be `implemented` or `owner_approved`, no node may be a placeholder, and unresolved source copies are an error rather than a warning.

## 5. Legacy compatibility

`fromLegacyClass()` reads the legacy `Class.schema.json` `progression_tree` without changing it.

- **Ambiguous lists:** a bare prerequisite list that names several members of one exclusive `choice_group` is read as `any_of_group`, and the node records `legacy_reinterpretation` (CC-008 A §2.2).
- **Status:** adapted trees are always `candidate`.
- **Provenance:** every adapted node is `provenance_class: "legacy"` and keeps `legacy_prerequisites` verbatim. The tree records `legacy_source {path, sha256}`.
- **Promotion gate:** a tree with any reinterpretation (or any invalid prerequisite) gets `promotion.requires_explicit_validation: true`. It can't become approved until every reinterpreted node has `legacy_validation` and every node is owner-approved (`PROMOTION_WITHOUT_LEGACY_VALIDATION`).
- **Invalid prerequisites are reported, never repaired:** `DANGLING_PREREQUISITE`, `SELF_PREREQUISITE`, `PREREQUISITE_ABOVE_LEVEL`, `NON_LIST_PREREQUISITES`, `DUPLICATE_NODE_ID`. A dangling reference stays in `requires`, so the validator rejects the tree.
- **Audit:** `node tools/audit_legacy_prereqs.cjs` regenerates `legacy/legacy_prereq_audit.json`, a per-tree record of every reinterpretation over the 100 candidate builds and the 195 hub-archive trees. `test_cc008_h.cjs` checks that the committed report is current.
- **New trees** must use explicit requirement modes.

## 6. Character state (`genesis-progression-character/0.1`)

| Field | Contents |
|---|---|
| `ledger` | `class_xp` and `purchase_currency` |
| `tracks` | `{level, xp}` per track |
| `held` | `track/node` → the transaction that granted it |
| `features` | Granted feature and profile references |
| `training` | Completed training markers |
| `restrictions` | Class and species |
| `applied` | Idempotency map |
| `receipts`, `txns` | Hash-sealed records |
| `pending` | A two-phase transaction in progress |
| `offers` | Milestone offers (§D) |

**Integrity:** every award and selection is deterministic, idempotent, hash-sealed and recoverable.
