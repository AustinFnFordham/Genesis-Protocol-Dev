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

## Owner rulings 2026-11-05 14:15
1. Ammunition Points: when a Trooper first takes an AP spender, resolve within the approved range: pool = proficiency bonus or 2x proficiency bonus; recovery = short or long rest. Nothing applied now (Varon needs none at Level 1).
2. Bounty Hunter licensing: assume the character is licensed by virtue of the class. At Level 1 standing/renown starts at 0. Specific guild or issuer is GM-side. Not yet written into any character sheet.
3. FFG skills adjacent to SW5e skills may be added as distinct skills with their own scope instead of folded into the nearest SW5e skill. Definitions pending (see SOURCE_COMPARISON).

## Owner ruling 2026-11-05 16:22 (Vigilance, proposed skill, Wisdom)
When surprise is possible, a Vigilance check gives a chance to protect against it. Success: not surprised. Failure: not protected from surprise, but the roll adds to initiative. Critical failure (natural 1): not protected, and the roll subtracts from initiative. Amounts are provisional (see SOURCE_COMPARISON) and nothing is applied to any sheet or source yet.

## 2026-11-05 16:33 Vigilance numbers withdrawn pending redesign
Owner challenge: (1) a failure bonus to initiative needs a coherent reason and does not offset losing the surprise action; (2) a natural 1 applying a fixed penalty regardless of the scene is not justified; (3) an expected value of +0.6 initiative does not show the mechanic is fair or interesting. The +2/-4 figures and the "failure adds to initiative" ladder are withdrawn and nothing was applied. Direction under investigation: separate independent layers (task result, narrative side effect, character appraisal, social consequence) instead of one success/failure ladder; AMD stays morality-only and is not coupled to skill checks. The surprise/no-surprise outcome and the DC rule (10 + best Stealth modifier, hidden-ledger pre-commitment) are unchanged.

## 2026-11-06 — Experience Contract (owner brief: LitRPG experience & Datapad development)
- **Adopted (owner-requested):** composite turns with a contextual composer (charter rule 1's "no menus unless asked" — the owner asked); free text stays first-class and runs through the same validator. Contract: `creator/TURN_CONTRACT.md`, implementation `ui/turn_contract.js` (one file used by the Datapad and the GM processor).
- **Adopted:** preflight before any roll (economy, capability, range/area, geometry, resources, visible reaction and opportunity-attack risks, alternatives). Outside combat there is no action economy; beats resolve in sequence.
- **Adopted:** automatic GM response. Submit writes the action, then the page calls the viewer's `Claude Code Remote` connector `fire_trigger` on the poke-only scheduled task "Genesis Datapad turn processor" (`trig_011svPGdUcPjEghbaSmrNFKF`). Each firing is a fresh cloud GM session running `.claude/skills/litrpg-process-turn` (claim-once, preflight, dice, ledger, narration, view/state, git). No laptop needed.
- **Adopted (owner-set):** `creator/NARRATIVE_SPEC.md` — adult horror, injury bands tied to committed damage, lasting damage only from a committed `lasting_injury`, perspective rules, intensity tiers. Lint: `turn.py lint`.
- **Proposed, NOT in force:** Protagonist Continuity (`creator/PROTAGONIST_CONTINUITY.md`, `creator/continuity_rule.json` status `proposed`). Standard death rules apply until the owner approves it here. The System-attributed variant needs a separate canon decision.
- **Run 2:** Hask Meadow restarted as `runs/hask_meadow_r2` (same premise and hidden truth, no run-1 knowledge). Run 1 is archived UAT evidence and never processed. The non-canon `runs/sandbox` is the round-trip test harness.
- **Open owner decisions:** approve or change Protagonist Continuity; encounter balance for a level-1 protagonist against the pack (UAT-0028).

## 2026-11-06 17:46 — Owner rulings on the Experience Contract slice
- **Protagonist Continuity: APPROVED provisionally (non-System version), campaign-level only.** Modifications applied in v2 (`creator/PROTAGONIST_CONTINUITY.md`, `continuity_rule.json` status `approved_provisional`): window runs until Hask Meadow is complete AND level 3 is reached (whichever is later); an explicit `continuity_expiring` step (notice, protection holds until the end of the next long rest, never lapses mid-encounter) precedes `continuity_expired`; no automatic termination: Mark n applies n cumulative costs, grievous wounds from Mark 2, an extra grievous wound from Mark 3; survival must be coherent in a hostile scene (hidden truth, else a fixed table over taken / interrupted / left for dead; extra harm in the same defeat adds grievous wounds, never death); no System lore.
- **Drover-dogs:** no weakening for Aero's level. Established capabilities and the five-dog premise kept; coherent motives, tactics, morale, geometry, fair warnings and counterplay in `runs/hask_meadow_r2/hidden/PACK_PROFILE.md`. Hidden purpose stays hidden.
- **One-tap Submit:** not complete until a genuine mobile Submit is verified. Worker hardening: campaign lock, git-before-publish ordering, usage records, scope limits (runbook + task prompt).
- **Experience:** KOTOR-style dialogue lines and composable action economy every turn; horror narration grounded in the ledger. Run 1 stays UAT evidence; run 2 does not advance until the owner submits.

## 2026-11-11 — Owner ruling: Jedi Fundamentals: Minor Telekinesis (provisional, campaign-scoped)
- **Approved provisionally:** a trained Jedi's basic non-offensive telekinesis, as a campaign feature granted by explicit recorded exception. Rule: `creator/JEDI_FUNDAMENTALS.md`; machine form and grant list: `creator/jedi_fundamentals.json`. Limits as the owner set them: one visible, unattended object of 10 lb or less, within 30 ft; lift, reposition, retrieve or manipulate; no Force Points; no roll outside combat unless there is meaningful uncertainty; an action in combat; no damage, forced creature movement, disarming, projectile interception or substitution for an unlearned combat power; normal consequences apply.
- **Not a power.** It does not count against `powers_known` and is not Force Push or Force Pull (both exist only as unpromoted registry drafts; neither is promoted or changed).
- **Explicit grants only.** Granted to Aero on the evidence of his sheet (Newly Knighted Jedi; knighthood ruled legitimate). Force sensitivity alone qualifies no one. Other appropriately trained Jedi get it by the same test, each recorded.
- **Sheet unchanged** (shared runtime); the Datapad shows the feature through an exporter overlay for run 2 only. Charter rule 2 otherwise unchanged. Validator unchanged (it never judged powers).
- **Turn 42 (evt_0864):** the statement that nothing Aero has can call a thrown lamp back is superseded for capability by a public `owner_ruling` event. No event or roll is voided; nothing was thrown and nothing is invented.
- **Open (defaults in the rule doc):** the roll used when one is needed, whether a free hand is required, holding an object aloft over time. **To evaluate:** integration into baseline Force-training mechanics.
