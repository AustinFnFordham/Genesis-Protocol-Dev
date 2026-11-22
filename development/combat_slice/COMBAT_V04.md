# Combat v0.4: first playable milestone (sandbox, noncanonical)

**Branch:** `dev/cc004-combat-v04`, built on `dev/cc003-tactical-composer` (`01f9061`), which is built on `f514617`. Nothing was rebuilt; the existing engine, both encounters, receipts, replay, tests and the composer design are kept and extended.

**Protected boundaries:**
- No change to Hask Meadow, `shared-0002`, the Oracle gateway, any ledger or any character sheet.
- No real campaign rolls are made.
- No mechanic is promoted to canon.

## 1. Reconciliation (before coding)

| Item | Finding | Action |
|---|---|---|
| Latest design spec from the "Document Genesis Protocol designs" session | **Not found.** I checked every GitHub branch, the claude.ai project docs, `E:\StarWars` (files changed in the last 3 days), Google Drive and the artifact list. The closest source is `_change_logs/PLAYER_PLAYTEST_001.md` (capability-first grammar, custom tactics, agency popup, "I wish I had to push a button and saw an actual die roll"). | I built against the handoff's own summary and that playtest. **Owner: please share the spec's location.** |
| Dice authority | CC-002/003 drew dice in client JavaScript (a seeded stream), which conflicts with "Atomic is authoritative." The existing Atomic is the server-side DiceService (`api_bridge/gm_controllers.py`), which uses the same mulberry32 family and idempotency keys. | The engine now **pauses for dice** (`need_dice`), the same way it pauses for reactions. Dice come from a server-side sandbox Atomic service (below). |
| Aero's capabilities (`api_bridge/gm/aero_character_runtime.yml`) | Several sheet items had no card: two-handed lightsaber, blaster pistol (ammo 12 + 38, reload is an action), Burst, focused Force Connection, Echani Grapple, Lightsaber Deflect T1, Sentinel Balance. **No telekinesis exists on the sheet:** his two known powers are Battle Insight and Burst. | All of them are added as `status: sheet` profiles. Telekinesis is listed as "Not on Aero's sheet", with the reason. |
| Combo recognition | "Blade and Body" matched card labels, so it showed even when Aero was disarmed and fighting unarmed. | Synergies are now judged on what is actually in hand at each step (the engine's projection). A combo is "confirmed" only from resolved events. |
| Invented rule found in my own work | The ranged-in-melee disadvantage is a d20 convention, but it is not on the sheet. | It now sits behind the switch `ranged_in_melee_disadvantage`, off by default (an owner decision). |

## 2. What was implemented

**A. Action-economy coverage**
- **Groups:** Maneuvers & Techniques · **Attack (every execution)** · other Main · Secondary · Bonus · Reactions · **Movement** · **Object interactions** · Free & speech · **Not on Aero's sheet**.
- **Attack selector:** Lightsaber one-handed (1d8+3) and two-handed (1d10+3, needs a free off hand), Echani unarmed, Blaster Pistol shot (40/160 ft, disadvantage beyond 40 ft, uses ammo) and Echani Grapple (+5 vs Athletics/Acrobatics, free hand, speed 0, no damage).
- **Equipment state:**
  - Saber held, lit, unlit or dropped.
  - Blaster holstered or in the off hand. Drawing or holstering it is an object interaction (one per turn).
  - Reload is a Main action and draws from the reserve.
  - The off hand is busy while it holds the blaster or a grapple, which blocks the two-handed grip and a grapple.
- **Force:**
  - Battle Insight.
  - Burst: DEX save DC 12 for every other creature within 5 ft (allies too); on a failure, 1d4 force damage and prone.
  - Force Connection, focused: honest note that no combat roll in this sandbox uses Insight.
- **Reactions:** Parry and Riposte (proposals), Dodge (proposal), Lightsaber Deflect T1 (reduces damage by 1d10+2; at zero the bolt goes back at the shooter), and Sentinel Balance (inert here, and its card says why).
- **New fixture:** a malfunctioning relay droid (HP 7, AC 13, blaster), taken from the playtest, so Deflect and blaster-vs-blaster can be exercised.
- **Unavailable cards** show the most specific reason first: equipment, then conditions, then spent resources.

**B. Sticky Turn Composer**
- **Desktop:** the timeline and Roll Theater column is `position: sticky`. It stays on screen while you scroll the library, so you never chase the drop zone.
- **iPad and phone:** the composer is a bottom dock. It is capped at 48vh, can collapse, and shows a live summary ("Resolving · 1 step · your roll!"). The library is padded by the dock's measured height. Dragging opens the dock.

**C. Roll Theater (player-controlled rolls)**
- Two lanes: **PLAYER — AERO** and **GM — <NPC NAME>**, with turn dividers.
- Aero's dice **wait for his Roll button**. The engine does not move until the player presses it. GM dice are requested by the GM side, with short pacing.
- Every card shows: purpose · formula · dice · advantage or disadvantage with its reasons · target or DC (AC n / opposed by X's skill / must beat n / DC n / damage to X) · the dice Atomic returned · the calculation · the consequence (read back from the accepted log) · receipt · die number.
- The reaction prompt is an agency moment (a modal, labelled PLAYER — AERO · decision). Where the numbers are certain, it says so, for example "Parry would turn this hit".

**Dice authority (Atomic sandbox service, `atomic_service.py` behind `/atomic/*` on the preview server)**
- The seed is generated and kept **server-side**. The journal a client can read never contains it.
- Dice are drawn only under a **committed plan** for the current turn. Once a die has been drawn, the plan is **locked** (`PLAN_LOCKED`).
- Turns must be committed **in order** (`TURN_ORDER`), and dice can only be drawn for the **current** turn (`TURN_CLOSED`). A die stays bound to its turn (`TAPE_CONFLICT`). Together these close the "commit a decoy turn to peek at dice" hole.
- Sequence numbers are contiguous (`SEQ_GAP`). Re-asking for a die that was already drawn returns **the same value and roll id** (an idempotent retry, so nothing is rerolled after a reconnect).
- Player decisions are journaled and locked (`DECISION_LOCKED`).
- **Reconnect:** the page stores the session id and, on reload, rebuilds the exact state from the journal (`turn_driver.replay`). A turn interrupted mid-roll resumes with its already-drawn dice.
- **Audit:** closing a session reveals the seed, and every die equals `die_value(seed, seq, sides)`. That function is bit-identical to the engine's stream (1,050-draw parity test).
- **Standalone file or claude.ai artifact:** there is no server, so the page uses **offline practice dice**. They run the same protocol in the page, and the Roll Theater labels them "NOT authoritative".

**D. Mechanics first, Soul second**
- Mechanical state (HP bars, the theater) updates from each accepted engine pass.
- Soul narration is queued after each turn, runs asynchronously, and shows "Soul is narrating… (the mechanics above are already final)". The NPC turn does not wait for it.
- An optional `window.__genesisSoulProvider` can supply AI text. It is shown only if `guard` finds no invented numbers.
- **Found and fixed during testing:** the page was writing a display flag into accepted log entries. The browser test now proves that the page state equals a clean replay of the server journal.

**3. Combo truth**
- **Predicted synergy:** the composer recognises a plan, judged on the projected weapon in hand at each step.
- **Confirmed combo:** after resolution, read from the events. Every link must have happened: the feint won, the attack was made with the right weapon in hand, and the follow-up was made. The card reports "every link happened · n of m attacks hit".
- **Soul's name:** Soul may propose a flavour name for a confirmed combo. It is labelled "a name, not a mechanic", is never written to the synergy registry, and gives no bonus.
- **Fixed:** with Aero disarmed, unarmed + Flow Strike is now "Unarmed Flow", never "Blade and Body".

## 3. Room for the future features (nothing below is implemented)

| Future feature | Hook it should use | What not to do |
|---|---|---|
| Nonlethal combat and excessive force | A step field `intent: "lethal" \| "nonlethal"` that flows into the `attack` and `damage` events; consequences come from a Chaos/consequence reader of those events | A second damage path |
| WHISPER emotional cascades | Consume the same structured `ev` log (attack, damage, contest, disarm, grapple, down, …) through Soul's frozen `facts()` copy | A separate combat event bus |
| Player-authored Tactics, mastery, Nemesis | `catalog.synergies` already uses a declarative `sequence` with per-step predicates (`pid` sets, `main_hand`). A player Tactic is the same schema with `source: player`, plus environment predicates. Mastery evidence comes from `confirmedCombos` over resolved events. Nemesis adaptation reads the same evidence. | A second tactic or combo registry |
| Noncombat Approaches and Methods | Profiles are already action-economy-agnostic (`cost`, `requires`, `resolution`). Approaches add `resolution.type` values and reuse `availability` and `validatePlan`. | Separate validators |
| Emotionally contextual dialogue and humour, Scene Director | Read-only consumers of `facts()` and the accepted log; output is presentation only, like Soul | Anything that writes to engine state |

There is **one capability registry** (`catalog.profiles`), **one event stream** (the engine log, with `ev` entries) and **one dice authority** (Atomic with its tape).

## 4. Tests (all in `development/run_all_checks.sh`)

| Suite | Checks | Covers |
|---|---|---|
| `test_engine.cjs` (CC-002) | 27 | Unchanged and passing |
| `test_cc003.cjs` | 21 | Unchanged and passing |
| `test_cc004.cjs` | 18 | Attack coverage, Force audit (no telekinesis), draw/holster object cost, blaster range and ammo, reload, the two-handed hand rule, Burst saves and prone, grapple, Deflect reduce and redirect, the inert Sentinel Balance, disarmed ≠ Blade and Body, predicted vs confirmed, `need_dice` carrying purpose, owner and target, immutable tape, GM-owned NPC dice, Soul names are display-only, predictions sharing the engine's range rule |
| `test_atomic_service.py` | 23 | No commit → no dice, plan lock, decoy-peek defence, turn order, seq gap and conflict, idempotent retry, server restart, decision lock, seed never in the journal, audit after close, path safety, JS/Python bit parity |
| `test_atomic_flow.cjs` | 13 | Whole fights through the **real preview server**: every receipt `authority=atomic`; player vs GM dice; journal replay = identical state; lost responses retried (no duplicate or skipped dice); crash mid-turn → resume with the same dice; re-planning refused; cross-site (non-JSON) posts refused; relay droid (ranged) fight |
| `test_playtest_ui.cjs` | 46 | Desktop: groups, Attack selector, reasons, sticky timeline, mouse drag from far down the library, combo truth in the UI, object-vs-main accounting, compound confirmation, **the turn waits for Roll**, double-click doesn't double-roll, GM lane, receipts, narration, a full fight. iPad and phone: the dock stays on screen, touch drag into it, tap to add, Roll button on screen and ≥ 44 px, no horizontal scroll, tap targets. Preview server: Atomic authority, reload → same session, no reroll, page state = journal replay. |

## 5. Remaining capability and rules gaps

**Engine and rules gaps**
- **Distance projection in predictions:** predictions use the current distance, not the distance after a planned Move step. For example, the blaster's long-range penalty after a planned withdrawal is not shown.
- **Sentinel Balance** never triggers, because nothing forces Aero to make a DEX or CHA save.
- **Grapple:** there is no escape action in NPC policies, no drag at half speed, and no Shove or Takedown from a grapple.
- **Lightsaber Deflect:** the redirect always targets the shooter. The sheet says "one visible creature within 30 ft" (a choice). It has no once-per-round limit beyond the single Reaction.
- **Battle Insight:** concentration (up to 1 minute) is reduced to "until your next attack".
- **Sentinel Balance and Combat Communication:** neither tracks uses per long or short rest.
- **Force Connection, focused:** no combat roll uses it.
- **Out of scope here:** cover, terrain and a grid; multiple enemies or allies at once; the party (Rassira, Varon); called shots and wounds; nonlethal.
- **Burst:** the save, the self-exclusion and the prone rider are adopted table rulings (as the sheet itself notes).
- **Fixture numbers:** Ilsa, the stalker and the relay droid all use sandbox numbers. The CC-003 balance recommendations are still pending.

**Dice-authority gaps**
- The engine resolves the turn in the browser, and Atomic only supplies the dice. A tampered client could compute a wrong outcome from correct dice. The journal makes this detectable by server-side replay, but **the server does not yet re-run the engine to verify each turn.** That is the next step.
- A client can open a new session to get a new seed. Sessions are logged, but nothing stops this yet.

## 6. Next smallest milestone (v0.5)

**Server-verified turns.**
- The preview server re-runs the engine (Node) on each completed turn from the journal.
- It accepts the turn only if the resulting state hash matches what the client reports. Otherwise it refuses with the mismatching event.
- It exposes `/atomic/verify`, and the Roll Theater shows "verified" on each turn.
- Nothing new is designed: it uses `turn_driver.replay` and `stateHash`.
- This closes the last authority gap before Combat can be wired to the real Atomic DiceService and the gateway (which needs owner approval).
