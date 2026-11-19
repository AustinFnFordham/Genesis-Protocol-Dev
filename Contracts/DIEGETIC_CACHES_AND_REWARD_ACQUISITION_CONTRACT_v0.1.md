# Genesis Protocol — Diegetic Caches, Generated Loot, and Reward Acquisition
**ID:** LOOT-001 | **Version:** 0.1 design draft | **Date:** 2026-11-18 | **Status:** design only, not deployed

## 0. Purpose and existing decisions
Adapt the **feel** of dramatic, player-opened LitRPG reward caches into an original, system-agnostic Genesis mechanic: achievement or world event → sealed reward → player-triggered reveal → staged item(s) → plausible in-world acquisition → inventory/equipment → authorized consequences.

This is **not** a copy of another title's text, presentation, item names, voice, or copyrighted specific reward content. A cache can be a diegetic System reward, found container, recovered shipment, battlefield salvage entitlement, faction award, or other scenario-specific construct.

**Existing repository truths to preserve:**
- `campaigns/starwars_litrpg/creator/DESIGN_DECISIONS.md`: tiers are `salvage < standard < reinforced < prized < singular`. Achievements issue caches. Loot outcomes are drawn with the approved dice mechanism from validated Registry item tables; candidates absent from Registry must pass Forge first. Existing decision: caches provide items/consumables/credits/information/cosmetics, and do not directly teach permanent abilities.
- `schema/Item.schema.json`: an item has physical/narrative identity as well as mechanical stats. `Contracts/08_Visual_Inventory_System.md` covers an immersive inventory. `Contracts/03_Drag_Drop_Card_System.md` covers cards.
- `Contracts/SECONDARY_ACTION_AND_CAPABILITY_ACTIVATION_CONTRACT_v0.1.md` (SA-001): equipment may grant a **conditional capability or alternate activation profile** while equipped. That is NOT a cache directly granting a permanent learned ability.
- Accepted ledger events, ruleset boundaries, Registry and Forge gates remain authoritative; no retroactive edit of established history.

## 1. The intended player experience
1. **Earn / discover:** A validated event grants a sealed cache or an encounter establishes a loot source. The Datapad displays the cache in *unopened* state; do not silently roll its contents or give the PC known contents.
2. **Open deliberately:** The player taps **Open**. A short, skippable audiovisual flourish may play (rarity-themed lighting, animation, celebratory or sardonic System voice). The user can skip/reduce motion; opening is never forced. The server controls legality and outcomes, not the animation.
3. **Reveal:** Deterministic draw and/or already-approved Forge output identify concrete rewards. Display item cards with name, rarity, narrative identity, *verified* mechanical effects and conditions, or explicit "mechanics pending approval" if not yet available.
4. **Stage:** Player can inspect and choose **claim now (if physically available), stash, reserve for delivery, leave in world, share/assign (if legal), or decline**. Staging is neither inventory possession nor equipment.
5. **Narrative acquisition:** The GM provides a scene explaining *how the reward reaches the actor*—lifting a weapon off a defeated enemy, finding it in nearby storage, receiving it from a faction, a legitimate System materialization, etc.—subject to known world facts and established delivery rules. Some modes can complete instantly, others require search/travel/interaction or a future scene.
6. **Acquire:** Only an accepted transfer/loot/claim event moves the item instance to an authorized inventory, location, or party stash. Encumbrance, ownership, equip restrictions and losses are handled by Atomic.
7. **Equip / activate:** A separate authorized equip/attune/use event changes effective capabilities, subject to prerequisites and item effects. The character sheet and Turn Builder update by projection, not by model assertion.

## 2. Two clocks; never confuse reveal with possession
Distinguish:
- **Reward entitlement**: actor or party is owed a cache.
- **Sealed cache**: unopened; contents not player-known.
- **Revealed reward**: contents determined and uniquely identified, not yet necessarily obtained.
- **Staged/pending**: known item assigned a prospective destination but not transferred.
- **World-present / claimable**: item instance exists at an established location and can be reached/looted.
- **Acquired**: transfer to inventory/stash accepted, including weight/capacity accounting.
- **Equipped/active**: legal equip and grants take effect.
- **Consumed / lost / transferred**: follow accepted events; remove conditional grants appropriately.

The UI may show a card in a *staging tray* without making its bonuses active. Nothing is equipped simply because it was revealed. A narrated reward without a lawful physical/economic transfer is not inventory truth.

## 3. Source-of-truth and causal provenance
Every reward needs stable references:
- Triggering accepted event or achievement; cache definition and tier; receiving actor/party.
- Authorized RNG request/receipt, selected loot-table revision, deterministically selected candidate IDs.
- Canonical Registry URID(s) and immutable item-instance ID(s), Forge evidence when generated.
- World origin / delivery channel, source location/actor/container, ownership/access conditions, acquisition event(s).
- Item history and current storage/equip state; corresponding rule/effect versions.

For a *defeated-enemy scene*, do not retroactively add an item to an NPC inventory, resurrect missing loot, or rewrite earlier rolls. Use only items already established there, or a **new forward-time, justified discovery** from plausible untouched crates/cargo/other scene resources; if lore/world evidence cannot justify it, stage the reward for a later credible delivery. An enemy's death is a possible eligibility trigger, not proof that every awarded item was on their body.

## 4. AI-generated items: creative invention versus mechanics authority
**Soul** may create original names, lore, aesthetics, quirks, item descriptions, provenance candidates, and reveal presentation grounded in the active setting. It may propose cosmetic/nonmechanical qualities and *propose* mechanical effects.

**Atomic/Forge/Registry must first accept** every mechanically consequential property: damage, bonuses, action-cost conversions, bonus Secondary uses, charges, limitations, stacking, equip prerequisites, trade value, and ruleset legality. An item that grants Tactical Assessment as a Bonus Action must link to an existing Registry capability and a validated activation-profile grant. The model cannot invent a mechanical advantage at award time and silently make it effective.

**Chaos** may propose compatibility, contingent interactions, consequences and semantic discovery; it cannot grant an unvalidated effect or override an established character history.

Suggested ordering for novel rewards:
- Create bounded **candidate** from existing approved rarity/loot profile and canonical references.
- Run Forge Atomic → Soul → Chaos gates, Registry resolution, validation evidence and approval.
- Only then put the eligible item into a loot table/reveal or mark it pending. If validation fails, keep a proposal outside canonical loot until repaired; do not substitute an unannounced overpowered artifact.

A *nonmechanical advantage* (a memorable scent, recognition by someone who knows an emblem, a useful inscription) must distinguish ordinary flavor from an actual gameplay permission or guaranteed effect. If it changes rolls, NPC knowledge, access, or faction status, that change requires authorization and evidence.

## 5. Legibility of the reward card
Each revealed card needs:
- Rarity/tier, identity, type, physical description, original flavor and history.
- Status: **reveal only / staged / claimable / in inventory / equipped**.
- Verified effects and source; if effects are not verified, visibly say "candidate — no gameplay benefit yet".
- Activation profile(s): Primary/Bonus/Secondary/Reaction/Passive, charges, cooldowns, repeat-use limits, prerequisites, and whether any grant lasts only while equipped.
- Weight, carry/equip restrictions, attunement or slot details if applicable.
- Provenance: where/why it was awarded, and whether the exact physical source is established.
- Visible actions: inspect, stage, claim when possible, equip when possessed, transfer/store/leave.

Rarity fanfare is a UI presentation classification and **does not** authorize stronger stats. No external purchase, gambling monetization, hidden real-money cost, or pressure mechanics are part of this design.

## 6. Mechanical example — legendary support-item grant
Illustrative only; must not be installed as a real Registry item without Forge acceptance.

**The Strategist's Eye** (legendary) can grant **Tactical Assessment** using a Bonus Action while equipped. Normal learned Tactical Assessment costs a Secondary Action under the proposed SA-001 mechanics.
- If the player doesn't know Tactical Assessment, the item gives temporary, source-bound access via Bonus.
- If the player knows it, the character may have both Bonus and Secondary activation routes.
- Two uses in a turn are **not automatic**: shared per-turn use cap, target rules, charges and effect-stacking policy must permit them. If once-per-turn, a second route does not bypass the cap without an explicit extra-use grant.
- A cache revealing this item does not teach the learned skill. Removing the item removes the equipment-sourced route.
- A physical inventory pickup isn't a skill acquisition; a skill-tree advancement is a different accepted transaction.

## 7. Multiplayer, parties, inventory and recovery
- A party cache must identify who can open it, who may claim an item, how competing claims are resolved, and which actions require consensus/GM adjudication. No duplicate distribution from simultaneous clients.
- Repeat Open / claim / equip calls with the same stable request ID must be idempotent. Resolve interrupted animations independently of committed draws; do not reroll on replay/crash/provider switch.
- Pre-existing hidden rewards can remain GM-only until reveal, but public projections must not leak unopened contents or hidden loot tables.
- Inventory must not expose private GM descriptions that identify unseen factions/locations/plot twists.
- Forged new items must be content-versioned so later generator changes don't mutate historical instances.

## 8. Cross-domain support
This module touches: achievement triggers; dice; validated loot tables; Forge/Registry; Soul item narrative; Chaos typed interactions; campaign economics; actor/party inventory and equip; character progression and active capability resolution; Turn Builder; UI effects; journal; GM knowledge; causal provenance.

These must use a shared accepted ledger, not parallel sources of truth. A cache reveal can be player-facing without automatically creating an inventory or equipping an item. The character's current sheet is a projection of confirmed holdings and active grants.

## 9. Gated development and test plan
**Phase A — Contract only (this branch):** agree states, owner authority, flow, approved item representation, and two-clock causality; no live mutation.

**Phase B — Noncanonical test slice:** scripted achievement → sealed cache → player Open → deterministic receipt → registered item reveal → stage/claim → plausible acquisition event → equip → capability update. Test no retroactive item spawn; no balance invention; closed cache secrecy; duplicate calls; concurrent party claim; crash recovery; unequip withdrawal; source/grant scope; screen-reader/reduced-motion and skip reveal.

**Phase C — Forge generation path:** candidate artifact → Atomic/Soul/Chaos gates → Registry version pinning → reveal eligibility, with explicit failed-validation behavior and GM provenance alternatives.

**Phase D — Gameplay release:** only after owner review, live-safety checks and disabled-by-default switch; keep playtest and live campaigns separate.

## 10. Open decisions (do not silently choose)
- Physical crate versus diegetic System entitlement, default channel by campaign/ruleset and whether opening can occur in combat.
- Reward entitlement: contents drawn at award time or Open time; both are possible but one deterministic authoritative commitment point is needed.
- Limits on opening, trading, abandoning, rerolling (default **no reroll**), party allocation and escrow.
- Rarity economics and reward budget; permitted created-item mechanics and approval authority.
- Whether items can be *delivered directly to inventory* without a physical acquisition scene in certain settings.
- Which source types may carry retroactive flavor versus only forward-time materialization (never rewrite accepted facts).
- Presentation tone and accessibility settings.

## 11. Handoff / scope
This is a **design-only** contract on `docs/tb4-whisper-contract-v0.1-20261117`. It does not alter `integration/tb4-whisper-v01`, Hask Meadow, `staging/mobile-test`, or the running private preview. Work may continue the current playtest/UI milestone independently and should consume this contract **only as design input**, not as authority to enable new resources or instantiate novel loot.
