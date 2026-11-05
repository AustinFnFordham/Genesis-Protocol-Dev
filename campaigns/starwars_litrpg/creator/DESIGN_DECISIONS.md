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

## Owner decisions 2026-11-05 (supersede earlier proposals)
- **Withdrawn:** the -100..+100 morality scale, the +/-40 swap bands, automatic mirrored-feature swaps on band crossing, save-based companion alignment shifts, session-end Conflict resolution from player-listed good deeds, a single affection meter for romance.
- **Adopted:** Adaptive Moral Dynamics (multidimensional, history-dependent; normalization is not justification), convictions-only companion reactions with independent trust/respect/fear/affection, Conflict evaluated from fictional time and established events, diegetic visibility, character-driven romance deferred.
- **Reference only:** Force Morality, Alignment Transform, and Inter-Party Influence docs (magnitude guidelines kept as reference, not modifiers).
- **Play now.** Use current rules and source data; keep unresolved mechanics, provisional rulings, data gaps, and unexpected interactions in `hidden/UAT_LOG.md`.
- **Protagonist:** Aero (existing sheet). Point buy remains the method for creating any new character.

## Owner rulings 2026-11-05 (character authority)
- Rassira: her original runtime is correct. Miraluka, raised in Dathomirian witch traditions, Bounty Hunter, Force connection severed. Do not change her species or make her a Force-using Nightsister.
- Varon: Adaptive Countermovement is his intended Trooper Style. Keep the authored definition; report remaining validation issues rather than replacing it.
- Togruta companion: created through play. No sheet is to be invented now. Introduced organically (entertainer or another suitable role).
- Aero: original runtime stays authoritative. Surname Do'ordo; relationship with Master Vael Taron preserved.
- Other character state is not rewritten without a validated discrepancy.
- Presentation priority: Claude-native UI (Artifact, mobile-friendly) before Tauri. Tauri is not a prerequisite. UI actions must never silently fork campaign history; a draft is not a committed turn.

## Owner ruling 2026-11-05 (Rassira mechanics policy)
Source mismatch is not a character error. Rassira's designed values are preserved provisionally (commit_ready false); custom ability increases and saves need an explicit recorded exception with mechanical justification. Species languages are kept separate from culture/background languages. Ammunition Points are resolved at the Trooper class-resource level. Sensory band is validated as custom equipment. Details: characters/REGISTRY_DEPENDENCY_REPORT.md.

## Owner ruling 2026-11-05 (source tiebreaker)
Where sources disagree or balance is in question, stick to SW5e where that makes the most sense. FFG/EDGE stays reference for lore and comparative design only (hybrid rule unchanged). Does not rewrite already-promoted canonical records (e.g. species_chiss) or approved character customizations; it governs how new candidates are resolved and balanced.

## Owner ruling 2026-11-05 14:10 (supersedes the 13:45 tiebreaker wording)
SW5e is the default only where FFG has no data. Where SW5e and FFG both have data and conflict, determine why they conflict and choose the resolution that best marries the two (SW5e supplies the mechanical frame; FFG's intent is preserved through adaptation). No source simply overrides the other. Does not rewrite promoted records or approved customizations.
