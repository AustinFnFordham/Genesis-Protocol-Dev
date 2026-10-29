# Design decisions and proposals (2026-10-27)

## Decided
- **Point buy**, 27 points, base scores 8-15 (standard SW5e/5e costs: 8=0, 9=1, 10=2, 11=3, 12=4, 13=5, 14=7, 15=9), species increases applied after. `4d6kh3` stays supported in the roller but unused.
- **3 subclasses per class.** Treated as named attractors in the tree (below), not cages.
- **Repo to go private** (owner action, pending). Stays inside the Star Wars project; `fluffy-chainsaw` is not ours.

## Decided 2026-10-29: `id` vs `urid`
Records carry both. `id` is the local slug and the key the schemas already require (`species_echani` style, human-readable). `urid` is the registry's global key, **derived, never hand-written**: `urid = "<entity_type>_<id>"` lowercase. The vector index keys on `urid` and is never canonical. One rule, deterministic, validator can enforce `urid == f(entity_type, id)`.

## Decided 2026-10-29: fluid progression tree (schema implemented)
The data already stores `progression_tree` as a flat node list (`node_id`, `feature_id`, `level_requirement`, `type`, `prerequisites`). Keep it, and make the schema match it (the `level_progression` requirement is the stale part). To make it fluid:
1. **Nodes are tagged** (`tags`, matching the Master Tags vocabulary). A class owns a *root* set of nodes, not an exclusive set.
2. **Availability = prerequisites + affinity.** A node unlocks when its prerequisite nodes are held and the character's recorded **tag affinity** (accumulated from committed events: what they actually did) meets `affinity_requirements`. The player still *chooses* to take it, so progression is both choice and behavior.
3. **Cross-tree nodes are legal** if prerequisites and affinity are met. Synergy edges (`synergy_inputs`, already in the Chaos audit fields) connect nodes across classes.
4. **Subclasses = three named branch clusters per class**, each a recommended path through the tree. Taking most of a cluster earns the subclass title. Hybrids earn an emergent title or class when nodes from two trees pass a threshold, announced by the System.
5. **Schema additions (all optional, additive):** per node `tags[]`, `affinity_requirements{tag: n}`, `branch` (cluster id), `synergy_edges[]`; per character `tag_affinity{tag: n}` updated only by the Record Keeper.

## System design (principles; content lives in `hidden/`)
- **Voice.** The System is its own character: terse, literal, mercantile, sometimes cruel. It never explains hidden mechanics. It may talk trash.
- **Caches (loot boxes).** Achievements award caches by tier (`salvage` < `standard` < `reinforced` < `prized` < `singular`). Contents are drawn with the dice script from loot tables made of **validated registry items** only. Caches give items, consumables, credits, information, and cosmetics. They never grant abilities; abilities come from play. If a drawn item does not exist, it goes through the Forge workflow first, so the loot list grows the valid file set. Party achievements award party caches.
- **Violence.** Graphic and consequential. Blaster and saber wounds cauterize, which is its own horror. Injuries have anatomy: lost limbs, scarring, shock, infection. No plot armor. The System may comment.
- **Achievements** are data (`schema/Achievement.schema.json`): trigger over committed events (Atomic), reward (Atomic), announcement (Soul). The Record Keeper evaluates triggers, never narration.

## Implemented 2026-10-29
`schema/Class.schema.json` now defines `progression_tree` (node graph with optional `tags`, `affinity_requirements`, `branch`, `synergy_edges`). `level_progression` is no longer required; one of the two must be present (`anyOf`). The old field is kept because `ui/v0.1`, `app/genesis-os/public/registry.json`, and `GENESIS_DATA_FLOW_MAP.md` still read it. Effect on the 100 class/subclass records: validated set 3 -> 6 passing; shortlisted classes passing 0 -> 3 (consular, soldier, bounty_hunter).

## Still open
Subclass design (3 per class), cache tiers and gear-bonus rules, System voice architecture, achievement budget, in-world explanation of the System. Discussed in chat 2026-10-29; to be written up once agreed.
