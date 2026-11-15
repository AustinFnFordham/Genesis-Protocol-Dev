# Barn encounter audit, Hask Meadow (2026-11-15). Read-only

> **Scope correction, 2026-11-15 (second pass).** Read this audit with
> `COMPATIBILITY_AND_ADOPTION.md`. Two corrections apply throughout:
> 1. Dice. Regular/Heroic/Legendary and the independent narrative d6 are designed and implemented in
>    the experimental resolver (`development/experimental_resolution/`, inspected at `1acf2a0`). They
>    are not integrated into live Hask Meadow. This audit's statements describe the live integration
>    only; they are not statements about the design or the code.
> 2. "Defect". Several findings below measure committed play against `ENCOUNTER_RULING.md` and
>    `ACTION_ECONOMY_RULING.md`, which were written after that play and are not adopted. Those
>    findings are proposals for change, not evidence that an adopted rule was broken. The
>    compatibility report classifies each one.

Audited at ledger head `evt_1417`, public revision 1125, commit `ebda584`: combat round 11, Aero's
turn. Nothing was committed, rolled, advanced or changed. Hidden positions, hit points, target
numbers and tables are deliberately left out of this file. Sources read: `CAMPAIGN_CHARTER.md`,
`creator/TURN_CONTRACT.md`, the run's public and GM-only events `evt_1240`–`evt_1417`, the roll log,
`hidden/PACK_PROFILE.md`, `ui/turn_contract.js`, `.claude/skills/litrpg-dice/roll.py`, `registry.json`.

## What the runtime actually has
- **No encounter controller.** Initiative exists as one `combat_start` event (`evt_1240`: Aero 21,
  "the drover-dogs" 7) and `combat_round` events with `order: [aero, drover_dog_pack]`. Rounds are
  advanced in GM prose.
- **Only Aero has a tracked budget** (`turn_context.budget`). Wick has no initiative count and no
  budget. The dogs have one shared count and no per-dog budget record; each dog's conduct is decided
  by its own private d6 table each round.
- **No companion rules for encounters.** The charter covers who controls party members and how
  companions react; nothing covers a companion's turn.
- **Dice, live integration.** The live worker rolls through `roll.py` (seeded mulberry32 stream,
  `normal`/`advantage`/`disadvantage`). Hask Meadow carries no experimental-resolution marker, the
  live page does not show the resolution controls, and its submitted actions carry no
  `resolution_settings`, so every live roll is Regular with Narrative Consequences off.
- **Dice, design and code.** Resolution temperature (Regular/Heroic/Legendary) and the independent
  narrative d6 exist: policy, transactional engine, public/private filters, composer controls,
  replay and crash-recovery tests, on `rc/canonical-dice-recovery-f241ea6` (`1acf2a0`) and carried
  on this branch. They are sandbox-only by their own README and gate.
- **Three separate things.** Encounter mode (`turn_context.mode`: scene/combat, and the proposed
  standoff) governs the action economy. Resolution temperature and Narrative Consequences are two
  independent per-action player settings. By the inspected design none of them selects another:
  starting initiative changes no dice setting. So in live play no required transition failed and
  nothing failed to display; the settings were simply never offered there. Round 10's rolls were all
  ordinary: Wick's shot `1d20+2` at disadvantage, total 10; eight private d6 tables; two `1d20+2`
  Stealth rolls for the dogs.

## 1. Is initiative still necessary?
No. Combat began at `evt_1240` when the lit blade went through the hatch against a creature lying
against it. That was a real contest. Since round 7 every way into the barn has been shut, barred or
bolted, the dogs do not open doors (`evt_1062`), and Aero has made no attack since round 6. No
participant has been able to act on an opponent within a round for five rounds. The one live hazard,
a smouldering scorch in the boards, runs on a scale of minutes. Under `ENCOUNTER_RULING.md` §7 this
is a **standoff**, not combat and not exploration: the pack is hostile, close and still acting. The
change needs a committed, reasoned mode event at the next resolution and your agreement; it is not
applied here.

## 2. Displayed action costs (context `evt_1417`)
| Option as displayed | Displayed cost | Finding | Rule |
| --- | --- | --- | --- |
| Listen toward the left wall / the small door / the hatch; Look and listen around the floor | Action | Right only as a deliberate Search with a check. What is plainly audible was already reported free each round (`evt_1394`, `evt_1411`). Four near-identical paid listens crowd out everything else | `ENCOUNTER_RULING.md` §6 |
| Watch the smoking scorch | Action | Wrong. Seeing whether a visible scorch is flaming is ordinary observation | §6 |
| Ask Wick something | Action slot, text says speech is free | Mislabelled. A question is free; only a sustained exchange takes the action | `TURN_CONTRACT.md` §4 item 3 |
| Ask Wick for the blaster back | Action | Wrong. Asking is speech; handing it over is Wick's act; receiving needs a free hand | `ACTION_ECONOMY_RULING.md` §2–§3 |
| Read Wick through the Force (Insight) | Action | Defensible: a deliberate check | §6 |
| Minor Telekinesis | Action | Right | `JEDI_FUNDAMENTALS.md` |
| Open the comm | Action | Wrong. Operating a device is the object interaction | `ACTION_ECONOMY_RULING.md` §1 |
| Bracing the barrel with the hilt (round 10) | Object interaction | Over-charged. Shifting a thing already held costs nothing. No consequence: the interaction was not needed for anything else that turn | `ACTION_ECONOMY_RULING.md` §2 |

Both ruling files are candidates awaiting approval; under the live text only the `TURN_CONTRACT.md`
rows are binding today.

## 3. Your support and coaching of Wick's shot
- **Effect on the roll: none.** The GM ruled the brace "takes the tremor out of the muzzle" as
  fiction and gave no modifier, because Help aids an attack only against a foe within 5 ft of the
  helper and the target was 90 ft away behind a closed door (`evt_1402`). Under the rules as they
  stand that is correct. The narration, though, described a steadier aim and so implied a benefit
  that was never applied.
- **Roll inputs, as accepted:** `1d20+2` (Wick's Dexterity, no proficiency), disadvantage for long
  range (90 ft, beyond the pistol's 40 ft normal range), total 10. The attack was against the door's
  planks, because something on the far side of a closed door cannot be targeted. It missed. The
  target number stays private.
- **Timing.** Wick fired during Aero's turn in round 10, on the word. He has no initiative count, so
  the record cannot say whose time that was. The one legal reading is Ready: his round-9 conduct
  (aim held on the door, told to fire only on your word) is his action, and the shot is his reaction.
  That reading gives him exactly one attack across rounds 9 and 10, so no extra act was created. But
  it was never recorded as a readied action, and nothing tracked his reaction.
- **Provisional inputs.** The pistol's profile and Wick's Dexterity come from GM rulings, not from an
  item or NPC record.
- Nothing is rerolled and no bonus is added after the fact.

## 4. The dogs
- **Within their means.** Rounds 6–10: each dog made at most one move per round, never more than its
  speed, and no dog attacked, acted twice or reacted. No budget was exceeded.
- **Consistent with their record.** Not rushing a pair shut inside, shadowing along the wall, staying
  silent after being hurt, and moving off after a shot at the door all follow the established pack
  doctrine (lure, do not charge; wait out; withdraw when hurt enough) and the fact that they cannot
  open doors. No new ability or knowledge was invented.
- **The stalemate is real and structural.** Each round each dog rolled a private table whose most
  likely result was "holds". The tables were rebuilt each round but barely changed, and they did not
  weigh what had built up: two dogs hurt, a shot fired, minutes passing, the pair staying put.
  Rolling six-second tables for creatures that cannot reach anyone manufactures motion without
  consequence. The dogs were not protecting you and were not stalling by fiat; the encounter was
  being run at the wrong time scale.
- The recorded shared count let "the pack's turn" be resolved as one block. Nothing illegal came of
  it here, but nothing would have caught it if it had.

## 5. Rounds and fragmentation
| Round | Your submission | What happened to the turn |
| --- | --- | --- |
| 9 | Five-step plan (`amweckuad6tgvbq`) | Three steps resolved, stopped at "which hand takes the lantern". Turn correctly left open |
| 9 | Rules clarification (`amwedw246slt3u6`) | Sent back, no state change |
| 9 | Lantern, grip, let go (`amwhb0ln6bujkui`) | Resolved, then **the turn was ended for you** with action, bonus action and movement unspent, and the pack's turn was run |
| 10 | Brace, breathe, "Fire" (`amwhbehqstehbof`) | Resolved, then **the turn was ended for you** again with action, bonus action and movement unspent |

Two different things are being conflated. Round 9's first stop was an incomplete turn awaiting input.
The last two were treated as completed turns only because a submission arrived: the worker has always
ended the turn at the end of a combat submission. So one intent (set Wick up, fire) cost two rounds,
and the world moved twice. That is a procedure defect, not a ruling.

## 6. Interface
The round-1 context offered Dash, Disengage and Dodge. The current one offers none of the core
actions: ten options, eight of them "takes your action" observation or talk. The validator already
understands Dash, Disengage and Ready when the GM publishes them; the GM stopped publishing them.
Free text is still accepted, so nothing was forbidden, but the buttons taught the wrong lesson.

## Diagnosis
**Verified rules or implementation defects**
1. No encounter controller: no per-actor budgets, no turn order beyond two labels, no reaction tracking.
2. Wick acts with no initiative count and no budget; his shot's timing is unrecorded.
3. A combat submission always ends the turn, whatever is left unspent.
4. Core actions are not guaranteed in combat contexts.
5. Costs displayed for observation, a question, a request and the comm are wrong or mislabelled.
6. The brace was billed as an object interaction (harmless here).
7. Dice: no transition failed. The experimental modes exist in code and are not integrated into live play.

**GM interpretation and encounter design**
1. Initiative was kept for five rounds with no possible contact.
2. Per-round "hold" tables at six-second scale for unreachable creatures produced the stall.
3. The brace was narrated as steadier aim while giving nothing.
4. Each round's narration restated the whole scene.
5. NPC cooperation was handled well: Wick's compliance followed his recorded convictions and a table.

**Facts still needed**
1. Who decides Wick's actions in an encounter (owner).
2. Wick's initiative (a roll, at adoption).
3. Whether bracing or coaching should carry a mechanic (owner).
4. An item record for the blaster pistol and an NPC record for Wick.
5. Your agreement to move this encounter to standoff.

## Pacing policy (recommended)
1. Resolve the whole declared sequence in one pass. Stop only at a genuine decision, a failed
   prerequisite, a new threat, or the declared end of the turn.
2. A turn ends when you end it or nothing is left to spend. A submission alone never advances the round.
3. Use initiative only while someone can act on someone else within a round. Otherwise run a
   standoff: your declarations cover minutes, the pack's plans advance on a clock you can perceive
   the edges of, and initiative resumes on contact.
4. Give hostile creatures intentions that mature: a plan with a visible tell and a time by which it
   comes due, rebuilt when circumstances change, instead of a fresh hold-or-shift roll every six seconds.
5. Narrate what changed and what you can act on. Restate standing scene facts only when they changed
   or after a break.
6. Always offer the core actions. Charge an action only for a defined action.
