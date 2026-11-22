# GEP-002 preparation: nonlethal overforce and WHISPER psychological pressure (sandbox)

**Status:** preparation only. Nothing here is a rule.

**Inputs**
- GEP-001 §3 (nonlethal control and accidental overforce), §4 (WHISPER) and §11.1–2 (open decisions).
- Owner decision D2 (2026-11-22): design a versioned player-control exception. **WHISPER identifies** eligible triggers, **Atomic validates and resolves** them, **Soul narrates** the accepted consequences. The GM may *propose* but never seize control. The exception is gated prospectively, with no live activation.

## 1. Reuse, don't duplicate

| Need | Existing machinery to reuse | What's added |
|---|---|---|
| Declared intent (lethal / nonlethal) | The plan step schema: a step field `intent`, validated by `validatePlan`, flowing into the `attack` and `damage` events | One optional field on attack steps; the default stays as today |
| Force-control resolution | `rollDice` → Atomic `need_dice` → the player's Roll button → server verification | A `control` roll kind (purpose, formula, vs: "safe ceiling"), owned by the actor who declared the strike |
| Outcome bands | The engine `log` event stream (`ev`), plus Soul `facts()` | New versioned event types: `subdued`, `overforce`, `control_held` |
| Psychological state | Not present yet. It will be a **projection** of committed events (like `knowledge()`), never free model text | A `psych` projection with source event ids, traits, strain, triggers and decay. It is server-side and viewer-projected (hidden from other players by default) |
| Eligibility and gating | Ruleset switches with provenance (as for `ranged_in_melee_disadvantage`), plus campaign overlays (`campaign_overlay.js`), plus bound sessions (enabled before the encounter) | The switch `whisper_cascades` and a campaign boundary record. It can only be enabled at session open, never mid-encounter |
| Involuntary action | The engine's existing `decide()` / `Pause` mechanism (who decides), plus Atomic `decide` | A new decision owner `rule:whisper` that is **only** valid when the gate is on and eligibility was proven by prior committed facts. It uses legitimate action resources; it never adds attacks or skips a pending player dice gate |
| Narration | Soul `narrate()` with `guard` | Templates for the physical mechanism of overforce: the strike, where it lands, and why it lands too hard. No prose-only tragedies |

## 2. Nonlethal overforce (§3): two separate dimensions

1. **Hit or connect:** the ordinary attack roll, unchanged. **A higher attack total is never worse.** A natural 20 can still be a critical hit.
2. **Force control:** only for a declared `intent: nonlethal` strike that hits.
   - A separate `control` check against a **safe-force ceiling**.
   - Strain, injury and weapon lethality can **lower the ceiling** or raise the risk of exceeding it.
   - Training and focus can raise it.
   - The candidate bands below are **open numbers, for the owner to set**.

| Band | Effect (candidate) |
|---|---|
| Control held | Safe subdual: the target is unconscious and stable where the rules allow |
| Small overshoot | Uncontrolled injury with complications |
| Large overshoot | Potentially fatal overforce (the current death and injury rules apply) |
| Failed connection | No incapacitation |

**Required simulations before any adoption** (in the `audit/balance_sim.cjs` style):
- the accident rate at low stress vs high stress;
- trained vs untrained;
- fist vs lightsaber vs blaster;
- confirmation that a high attack roll never *increases* fatality.

## 3. WHISPER pressure (§4)

- **Inputs are committed facts only:** HP bands as *pressure*, never universal fear; ally down; betrayal; surrender after a kill; and the character's own traits and values.
- **Eligibility is computed before the roll and recorded:** which trigger facts, which trait, which gate version.
- **The outcome is resolved by an Atomic check** with a bounded consequence envelope. Composure must be possible too.
- **Rarity target:** owner-set, for example under 1 cascade per N eligible high-stakes moments, verified by simulation.
- **Visibility:** the player sees observable cues, never a precise "mental bar".

## 4. Contract changes needed before any live use (owner)

- **GM_GUIDE rule 1:** add a versioned exception, `rule:whisper`, so that an adopted, gated mechanic can determine a player character's involuntary act. The GM may only *propose* eligibility, and the engine decides.
- **Campaign boundary record:** whether involuntary violence and accidental killing are allowed, content limits, and the player's advance consent. It is set at campaign or session start.
- **Rules version:** `cc-sandbox-0.6` or later, opt-in per session.

## 5. First GEP-002 milestone (proposed)

**Scope:** the sandbox duel only, with the gates off by default.

**Build:**
1. A `nonlethal` intent on Echani and lightsaber strikes.
2. A `control` roll in the Roll Theater, labelled PLAYER — AERO (the player's own roll).
3. The bands as clearly labelled fixture numbers.
4. A `psych` projection with two triggers (ally down, surrender after a kill).
5. One gated cascade type: **overforce on a declared nonlethal strike**.

**Prove:**
- the acceptance stories from GEP §12 ("Psychological mercy", "Surrender consequence");
- that a high attack roll never causes the tragedy;
- that every accident has receipts and a physical mechanism;
- that the gate cannot be flipped mid-encounter.
