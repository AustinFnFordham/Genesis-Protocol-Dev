# Genesis Protocol — GEP-002 Owner Direction: Impact Control, WHISPER Gate & Combat Theater
**ID:** GEP002-OWNER-001 · **Date:** 2026-11-22 · **Version:** 0.1 · **Status:** Approved design intent / UNAPPROVED quantitative mechanics / visual future-state brief.

**Scope:** documentation-only clarification to `Contracts/GENESIS_EMERGENT_PLAY_AND_BEHAVIOR_DESIGN_v0.1.md` (GEP-001) and `development/combat_slice/GEP002_PREP.md`. Based on Combat CC-005b branch `dev/cc005-server-verify` at `7b53add21f6a1e22d4057810d171fe1b0349b153`. Does not implement rules, consume dice, update live character state, change gateway, or promote a campaign mechanic. No edit to Claude's combat files; cherry-pick independently when safe.

## 1. Owner design decisions and open questions

**D1 — Outcome frequencies:** Owner is UNSURE about exact severity bands and rates. Keep all numeric injury/fatality distributions as sandbox hypotheses. Design tests before proposing a canonical threshold. Overforce need not kill; a safe intended incapacitation remains available.

**D2 — Inverted nonlethal impact check:** Owner explicitly wants a separate mechanically distinctive 'low is controlled, high may be excessive' roll for an eligible *finishing blow declared nonlethal*. A normal high attack roll must remain advantageous. The impact-control roll is NOT the attack roll and does not replace its hit/miss/critical semantics. Actor control/precision training should help by SUBTRACTING a verified, source-backed control modifier from the impact d20, e.g. `intensity = d20 - approved_control_modifier`. The name, scaling, eligibility and source of `approved_control_modifier` remain TBD; do not automatically reuse attack bonus, proficiency or Ability modifier without source review. As an illustration only, a sample d20 face of 15 and control value +4 produces 11, which is safer than raw 15. A higher result above an upper **safe-force ceiling** reflects overshoot. Calling this 'low roll succeeds' should not invert conventional d20 attack checks.

An *example, not an adopted rule*: for a control modifier of +4, safe ceiling 15 at composed strain makes only a raw natural 20 overshoot (1/20 = 5%). At a maxed mental-strain state, hypothetical safe ceiling 11 would produce overforce on raw 16–20 (5/20 = 25%). Both require deterministic simulation and balancing across trained/untrained, damage type, weapon, target vulnerability, injuries, environmental hazards and plausible lethality. The impact control roll is shown under **PLAYER — AERO** and is requested from the same authoritative Atomic dice service with immutable receipts; do not automatically choose a dice face. No roll is made by this documentation.

**D3 — Psychological catastrophe gate:** The owner ties *catastrophic, unintentional loss-of-control consequences* to a fully maxed mental-strain meter plus applicable situation/traits, not generic low HP or any ordinary insult. Mechanical eligibility requires prior committed evidence for strain reaching its max, an eligible high-stakes trigger, and a prospectively opted-in campaign/ruleset boundary. Baseline nonlethal overshoot may still occur for ordinary control mistakes, but severe tragedy must additionally meet approved severity/injury and psychological cascade criteria. Max strain is **necessary, not automatically sufficient**; success/failure both remain possible, with deterministic/receipt-backed resolution. No generic universal anger/fear rule.

**D4 — GM contract versioning:** The owner recalls having a versioned GM contract. Source inspection confirms the published `campaigns/starwars_litrpg/creator/TURN_CONTRACT.md` identifies `turn-contract/3`, and the GM workflow is provider-neutral. However, `development/gm_provider/GM_GUIDE.md` is a separate living document with NO explicit formal version header at this time. Do not silently overwrite its rule 1 ('Never act for the player character'). Add an additive, explicitly versioned and ruleset-gated exception `rule:whisper` as a future GM/rules contract upgrade only after owner approves the exact trigger/action model. Legacy `turn-contract/3` and GM_GUIDE behavior remain as is. GM may propose eligibility but never freehand authorize involuntary violence or bypass pending player dice/choices.

**D5 — Thin-player and cinematic interface:** The owner approves building toward a **thin, true player-only client** that consumes server projections. Ideal visual future state is duel-themed, with clear ownership of actions and dice, separate avatar perspectives, and alternating response beats like a visual novel or messenger thread:
  1. **PLAYER — AERO** avatar/character panel presents the chosen maneuver, predicted constraints, and player's roll button.
  2. **OPPONENT — NPC** panel presents visible defensive reactions, GM-owned dice, effects and outcomes (no player button for NPC rolls).
  3. Deterministic server verification commits authoritative events/receipts. Only THEN the UI plays descriptive sword slash, blaster-tracer, dodging motion, parry, counter or impact VFX mapped to each accepted event. A committed miss must NEVER animate as a hit.
  4. **Soul exchange:** fresh narration as alternating character-tagged thread bubbles or visual-novel dialogue cards. Player's declared words appear in their original ordering and exact text. NPC-specific prose must remain grounded in what the player may observe; do not leak private NPC thoughts, unseen reactions, AC, HP, secret locations or rolls.
  5. A striking, **diagonal split-screen protagonist/antagonist cut-in** may introduce a clash, critical turning point or reaction window. It is optional cinematic treatment, not a permanent screen partition; keep action chooser/composer accessible and usable on iPad/phone.
  6. Avatar cards may show portraits and appropriate conditions/role labels; energy and behavior effects can use CSS/SVG/sprites initially. Avoid slow generative asset calls on every event. Use preproduced assets and event-specific animation variants as early milestones. Later consider ComfyUI for assets/portrait variants and motion/visual pipelines, but no such connector is proven or invoked by this document.
  7. Respect reduced-motion settings, subtitle/text accessibility, focus states, minimum touch targets, muted effects option and latency. Animation is never required to resolve a roll. Never conceal an ongoing player response checkpoint beneath a long Soul narration.
  8. Server must be the only publisher of player-visible state; don't ship `catalog.json`/`scenarios.json` with private NPC stat blocks, even if client toggles 'Player view'. The CC-005b report explicitly identifies this remaining source leak. The thin view is a safety/authority requirement before cosmetic polish.

## 2. Suggested interaction timeline, no fictitious game events

```text
[PLAYER • AERO portrait]  DECLARE "Strike nonlethally" -> validation -> [Roll Attack]
                         Atomic authorizes/returns accepted attack receipt
[OPPONENT • NPC portrait] REACTION? validated GM action/roll and conditions
[PLAYER • AERO portrait]  If eligible finishing hit: [Roll Impact Control]
                         Atomic applies normal attack + separately resolved intensity
[VERIFIED EXCHANGE]      Server authoritative consequences and receipts
[ANIMATION]              Event-driven sword slash / dodge / block / blaster flash
[SOUL THREAD]            Player-observable, speaker-tagged cinematic prose
[NEXT CHECKPOINT]        Ask for actual player choice, or GM proceeds when legal
```

The order of defensive reactions relative to the finishing blow must be determined by the real engine's reaction checkpoints and specific action contracts, not hardwired from this illustration. The player always retains control of the Roll button for their own eligible dice. An opponent's 'perspective' refers to a visible actor presentation, not omniscient private mental narration.

## 3. Minimum implementation staging (do not build all at once)

**First:** CC-005c or equivalent THIN CLIENT: remove private NPC bundles and client-side authoritative state inference; consume only `/atomic/view` and authenticated, role-separated action endpoints; server-owned encounter ids and gateway identity remain separate integration gates.

**Then:** GEP-002 mechanical proof: nonlethal intent, independently rolled impact intensity, max-strain eligibility projections, safe subdual/injury/severe-outcome candidates, source-constrained `rule:whisper`, no auto fatality on ordinary d20 high roll. Tests with synthetic fixtures only, no campaign state. Use multiple seeded simulations and print empirical rates. More than one qualifying roll may be required depending on accepted defense/reaction ordering.

**Then:** EVENT-DRIVEN Combat Theater presentation: avatar split, alternating roll lanes, timeline/scroll, Soul text conversation, CSS/SVG event VFX with accessibility and low-latency mode. Coexist with existing sticky composer; do not rebuild engine.

**Finally:** integrate optional pre-generated portrait and cinematic assets; later analyze ComfyUI/animation connector on a separate lane. Model output can request a presentation style but cannot alter mechanics.

## 4. Test stories / acceptance and exclusions

- Ordinary nonlethal success: control roll ≤ safe ceiling, eligible target incapacitated/stable, verified accepted events and a speaker-tagged narrative.
- Overforce attempt: high normal attack does not automatically increase severity; a separate higher impact intensity overshoots safe ceiling despite declared mercy. Accidental death remains a rare, downstream possibility only through authored severity and max-strain cascade gates. No spontaneous 'anger moves faster than thought' description without an actual physically coherent motion.
- High psychological pressure: same impact face under composed and maximally strained conditions can produce different outcomes; meter state is supported by committed facts, not guessed by a GM.
- Preserved agency: the player chooses a nonlethal intent and presses their own roll, but an approved and previously enabled `rule:whisper` may permit a mechanically proven involuntary physical outcome; no GM arbitrary agency seizure.
- Reaction beat: NPC's parry/deflect/dodge appears under NPC avatar and is based on valid action budget and accepted outcome, then corresponding sprite/VFX; a failed attack never shows a successful slash.
- Full concealment: source HTML and browser network data do not contain undiscovered NPC HP/AC or private plans; switching to player mode cannot reveal what was bundled privately.
- Mobile: compact two-avatar presentation, active roll always visible, accessibility, no gameplay dependence on animation performance; no auto-rolled PC dice after reconnection.
- Tests/claims: separate engine, server and browser checks, seeded accident-rate evidence, no auth bypass, no forged private data, no duplicate receipt/re-roll.
- Explicitly unresolved: exact injury and mortality bands, numeric ceiling, control modifier source, strain accumulation and decay, eligible weapon set, critical-hit handling, target injury physics, action resource timing, GM_GUIDE ruleset version and campaign consent boundary, final UI visual direction.

**Change control:** This is a design note only. It does not ratify example numbers, grant a Force power, change the GM guide, rewrite a player turn, alter the live campaign, or supersede CC-005b's source authority. Future mechanic and UI changes require separately scoped, tested and owner-approved commits.
