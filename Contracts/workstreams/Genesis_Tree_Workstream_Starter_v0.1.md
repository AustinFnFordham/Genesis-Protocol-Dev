# Genesis Protocol — Progression Tree Workstream Starter v0.1

**Status:** portable design brief committed to this isolated docs branch; not canonical mechanics; no campaign or service changes authorized.  
**Purpose:** seed a NEW CHAT dedicated exclusively to character progression trees, unlock design, XP curves, milestone choices, and prerequisite graphs. Implementation/deployment stays in the main development chat.

## Start-here instructions for new chat

You are co-designing Genesis Protocol's versioned progression content library. Do not invent canon or grant unearned features to active characters. Begin with Aero (Echani species, Sentinel class, Sentry archetype planned but not yet selected, Jedi background). Read actual class/species/subclass source files and current combat profile sources before presenting mechanical claims. Build complete, testable designs collaboratively in passes: inventory existing → source provenance → prerequisites → independent XP thresholds → tier/milestone offers → precise effects, costs and limitations → balance and progression simulations → owner approval → implementation handoff. Preserve the distinction between recorded/approved rules, legacy/source proposals, new candidate content, and implemented code.

### Advancement cadence — owner-aligned candidate architecture

- **Base Class:** character level progression 1–20, source-backed class features, resources and authored bonuses at appropriate levels.
- **Archetype/Subclass:** chosen at **character level 3**, receiving an identity-defining entry feature; specialty three-choice milestone opportunities at **3/6/9/12/15/18** where compatible with source rules. Avoid a redundant second choice at L3 if archetype selection itself is the choice; document the grant and choice semantics.
- **Species/Heritage:** traits and eligible milestone upgrades at **character levels 5/10/15/20**, preserving the original species intent when valid and distinguishing inherited traits from cultural training.
- **General Skill Mastery:** independent verified-use XP; simple bonuses at **mastery levels 5/10/15/20**. Individual skills need explicit cumulative experience threshold tables and prerequisites.
- **Specialized Skill Mastery:** independent verified-use XP; full branching tree and up-to-three candidate upgrades at **mastery 3/6/9/12/15/18** (or source-authored alternative). Three displayed options must be genuinely eligible; don't fabricate eligibility.
- **Parent-linked profiles:** no duplicate XP ledger. Use parent's XP and selected choice lane, still with up-to-three meaningful authored options at eligible milestones. Event grants and cooldown/cost changes must be explicit.
- **Shared Disciplines:** proposed broader experiential pools (Force, Martial Arts, Armed Combat, Reaction/Timing, Awareness, Marksmanship, Social Influence, Mobility, Equipment). One accepted event has one primary mastery owner and bounded cross-discipline credit; no unlimited XP farming, no passive grant of unlearned powers.
- **Class level, mastery level and discipline level are distinct.** Do not conflate class advancement XP with earned technique practice. Each *leveling track* requires its own explicit XP curve (or governing level threshold source), cumulative threshold, evidence rule, rewards and prerequisites. Choose a shared curve where sensible but allow track-specific scaling.
- **Milestone choices:** roguelike presentation of three eligible upgrades, choose one; unchosen candidates remain discoverable subject to later prerequisites. A skill tree is its graph of upgrades, not the action or a generic milestone choice card. Rarity or hybrid combinations never bypass prerequisites.
- **Combo/Maneuver/Tactic:** freely composed legal combo ≠ trained/purchased specialized Maneuver with unique mechanical benefit ≠ evidence-developed, conditional Tactic. Techniques are specific capability methods. Team variants require individual authorization and per-PC action budgets. Mature features should enable emergence without duplicating XP or granting actions for free.

### Current sandbox prototype — do not silently promote to canon

CC-007 reports `development/progression/mastery.js` implemented for validated event XP, idempotent receipts, milestone eligibility and recoverable awarding. Proposed **Telekinetic Control**: level 0 range 30 ft, weight 10 lb; +5 ft range and +1 lb per mastery level; an additional +5 lb at levels 5, 10, 15; level 5 cumulative XP 130, level 10 610, level 20 3,620; per-transition XP = 10 + 5L + L². Milestone ideas are fine manipulation (L5), sustained hold (L10), eligibility to start Force Pull/Push training (L15) rather than automatic granting. XP policy, farming prevention and uncertain-use checks need review. Out-of-combat Telekinesis should allow ordinary at-will uses while retaining established weight and distance limits; meaningful, verified use drives mastery rather than counting every trivial repetition.

### Owner's 34 progression profile selections

| Family | Profile ID | Display | Owner's progression type |
|---|---|---|---|
| Force & Sensory | `minor_telekinesis` | Minor Telekinesis | Full tree |
| Force & Sensory | `battle_insight` | Battle Insight | Full tree |
| Force & Sensory | `battle_insight_bonus` | Battle Insight (quick) | Parent-linked milestone lane |
| Force & Sensory | `burst` | Burst | Full tree |
| Force & Sensory | `force_connection` | Force Connection (focused) | Full tree |
| Force & Sensory | `force_augment` | Force-Guided Strike | Parent-linked milestone lane |
| Force & Sensory | `sentinel_balance` | Sentinel Balance | Three-choice milestones |
| Echani & Grappling | `unarmed_strike` | Echani Strike | Full tree |
| Echani & Grappling | `flow_strike` | Echani Flow Strike | Parent-linked milestone lane |
| Echani & Grappling | `grapple` | Echani Grapple | Full tree |
| Echani & Grappling | `escape_grapple` | Escape Grapple | Parent-linked milestone lane |
| Echani & Grappling | `release_grapple` | Release Grapple | Parent-linked milestone lane |
| Echani & Grappling | `controlled_takedown` | Blade Bind & Takedown | Full tree |
| Weapons & Equipment | `saber_strike` | Lightsaber Strike (one hand) | Three-choice milestones |
| Weapons & Equipment | `saber_strike_2h` | Lightsaber Strike (two hands) | Three-choice milestones |
| Weapons & Equipment | `blaster_shot` | Blaster Pistol Shot | Three-choice milestones |
| Weapons & Equipment | `blade_bind` | Blade Bind & Strip | Full tree |
| Weapons & Equipment | `parry` | Parry | Full tree |
| Weapons & Equipment | `riposte` | Riposte | Full tree |
| Weapons & Equipment | `lightsaber_deflect` | Lightsaber Deflect | Full tree |
| Weapons & Equipment | `recover_weapon` | Recover Weapon | Simple levels |
| Weapons & Equipment | `toggle_blade` | Ignite / Deactivate | Simple levels |
| Weapons & Equipment | `draw_sidearm` | Draw Blaster | Simple levels |
| Weapons & Equipment | `holster_sidearm` | Holster Blaster | Simple levels |
| Weapons & Equipment | `reload_sidearm` | Reload Blaster | Three-choice milestones |
| Tactical / Social / Utility | `feint` | Weapon Feint | Three-choice milestones |
| Tactical / Social / Utility | `readied_dodge` | Readied Dodge | Parent-linked milestone lane |
| Tactical / Social / Utility | `dodge_reaction` | Dodge (readied reaction) | Parent-linked milestone lane |
| Tactical / Social / Utility | `dodge_action` | Dodge Action | Three-choice milestones |
| Tactical / Social / Utility | `taunt` | Taunt | Three-choice milestones |
| Tactical / Social / Utility | `tactical_glance` | Tactical Glance | Full tree |
| Tactical / Social / Utility | `calm_beast` | Calm the Animal | Full tree |
| Tactical / Social / Utility | `move` | Move | Simple levels |
| Tactical / Social / Utility | `speak` | Speak | Simple levels |

Counts: 13 full trees, 8 three-choice milestone profiles, 7 parent-linked profiles and 6 simple proficiency profiles. These are **profile assignments**, not necessarily 34 different XP meters.

### Reconciliation questions to design, not silently answer

- Force Weapon Recall vs physical Recover Weapon; existing Telekinesis campaign grant does not automatically make recall a free/bonus action. Drawn saber vs recovered saber, ignition cost and FP augmentation require separate authored rules.
- Ordinary speech vs consequential diplomacy, deception, intimidation, teaching and leadership; no XP per spoken sentence.
- Walking/traversal proficiency vs Jump and FP-augmented Force Jump; movement activity proof and costs.
- Reaction/Timing as a cross-cutting discipline supporting Parry, Deflect, Riposte, Readied Dodge; a real Force-augmented reaction may split XP to Force but an ordinary Parry cannot.
- Parent-linked milestone lanes have authored options yet share the parent XP track; ensure no repeated award from setup/trigger pairs.
- Class, subclass/archetype, species, species culture, personal skill, Discipline and earned Tactic grants need distinct authority and graph identities; sources may disagree and require migration proposals.
- An upgrade should add tangible new mechanics rather than merely allowing an existing legal combo. Specify cost, boon, bane, trigger, success/failure consequences, choice persistence and scaling.
- Aero's species is Echani, his class Sentinel and planned Sentry subclass is **not automatically selected**; the other character combos can be done after this first reusable example: Varon, Rissa/Rassira (confirm exact source name), and the Togruta PC.

### Source material and known branches

Repository: `AustinFnFordham/Genesis-Protocol-Dev`

- Combat branch `dev/cc005-server-verify` @ `5ec21bb0ff705fd3b1e6bc7a86155475828db662`: CC-007 progression prototype and `development/combat_slice/catalog.json`, `development/progression/`.
- Design branch `docs/crucible-dice-whisper-design-v01-20261122`: Combo/Maneuver/Tactic lifecycle and dice design. Do not merge into the combat branch while working on trees.
- Source archives previously supplied to this conversation: `schemas.zip` (Class, Subclass, SpeciesProgression schemas), `game_data.zip` (`classes/sentinel.yml`, `subclasses/sentinel_subclasses/sentinel_sentry.yml`, Echani and progression examples), `systems(1).zip` (Progression Tree System, Sub-tree Choice System), `rules&guides.zip`. Reopen in new chat if files are not carried across; avoid inventing source details.
- Oracle runtime and GPT/Gemini/Codex OAuth changes are out of scope here.

### First deliverable for the new chat

Create an **Aero Echani × Sentinel × prospective Sentry progression design packet** with (a) source-backed class/species/rules inventory, (b) explicit level thresholds and independent XP curves wherever necessary, (c) levels 1–5 fully specified as testable choices where sources permit, (d) tentative 6–20 archetype/species roadmap, (e) skill-level 0–20 XP and milestone reward progression where selected, (f) typed prerequisite graph and deduplication/authority rules, and (g) owner decision register. Work collaboratively through proposals and balance tests before promoting any effect to canonical gameplay.
