# Protagonist Continuity — campaign rule, IN FORCE (provisional)

Owner ruling 2026-11-06 (17:46): approved provisionally, non-System version, with modifications. **Scope: this Star Wars LitRPG campaign only (Hask Meadow run 2 onward). Not a universal Genesis rule.** Machine form: `creator/continuity_rule.json`. Tool: `creator/continuity.py`. Test E: `creator/test_continuity.py`.

## Purpose
Protect the continuity of the story during the opening, not the character's body. Real rolls, damage and defeats all stand. A protected character who would die survives through a consequential continuation, and the consequences are serious, cumulative and grounded in the rules and the ledger.

## Who and when
- **Protected:** main-party player characters with validated sheets (Aero now).
- **Window:** from the start of run 2 until **both** the Hask Meadow arc is complete **and** the character has reached level 3 (whichever happens later).
- **Transition to normal mortality (explicit):** when both conditions are met, the GM commits a public `continuity_expiring` event and the Datapad shows: *"Protagonist Continuity ends at the end of your next long rest. After that, death is permanent."* Protection holds until that long rest ends and never lapses mid-encounter. Then the GM commits `continuity_expired`. From then on charter rule 8 applies in full: three failed death saves, massive damage or an instant-death effect kill.
- **During the window, a protected character cannot permanently die.** The death saves are not a bluff: successes still stabilize normally (no defeat, no cost); failures decide *when* a defeat lands.

## Trigger
A protected character **would die**: a third failed death save, damage at 0 HP equal to or above maximum HP, an instant-death effect, or a hostile finishing a helpless character.

## Effect
1. **Nothing is rewritten.** Every committed attack, roll, damage, drag and lost item stands. No roll is repeated.
2. **The character lives**: 0 HP, unconscious, stable. They regain 1 HP after 1d4 hours (rolled) unless a cost or the scene says otherwise. Stable is not safe: the world keeps acting on its own schedule.
3. **Coherent survival path.** Why the character is still alive must follow from the world, chosen in this order:
   1. Established hidden truth about what these hostiles do with a downed foe (used directly, no roll).
   2. Otherwise a die over the *eligible* paths, written down before rolling:
      - **Taken**: a committed event shows them moving or holding the character. They wake where they were taken.
      - **Interrupted**: an already-established actor was already heading here (a committed event or plan, never invented on the spot).
      - **Left for dead**: always eligible. The hostiles believe the body finished and move on.

   The chosen path governs what the hostiles do next. Further harm in the **same defeat** (before the character regains consciousness) adds one grievous wound per further would-die moment, at most two per defeat. It never kills.
4. **Defeat Marks and costs (cumulative, escalating, no auto-termination).** Each defeat adds one Mark. Mark *n* applies *n* costs (as many as are eligible), rolled from the eligible list. Earlier costs persist.

   | Cost | Eligible when | Effect |
   |---|---|---|
   | Lasting wound | the defeating harm was physical | `lasting_injury` on the damaged part: disadvantage on checks using it (−10 ft speed for a leg) until treated (Medicine DC 15 in a safe place) and two long rests. **From Mark 2: grievous** (see below). |
   | Lost equipment | an item was dropped, taken or broken in the ledger | stays where the ledger left it; recovering it is a goal |
   | Exhaustion | always | two levels of exhaustion (SW5e condition), one recovers per long rest; capped at level 5 while protected |
   | Escalation | a hostile actor has an active plan | that actor's next scheduled move comes one step sooner or stronger (logged `gm_only`) |

   - **Grievous wound** (Mark 2+ lasting wounds, Mark 3+ always one extra, same-defeat extra harm): as a lasting wound, but it persists until bacta-tank treatment at a real medical facility or a cybernetic replacement. Both are established Star Wars technology, not System lore.
   - Marks never reset during the window, and the protection never ends early. Each defeat costs more than the last.
5. **Records.** The GM commits `continuity_invoked` (public), one `continuity_cost` per cost, any `lasting_injury` events, the survival path (`gm_decision` with the table), and the new conditions. Narration follows `NARRATIVE_SPEC.md`: the loss is shown, not softened.

## What it never does
Invent System lore, an ally, an item or an escape. Change a roll. Claim the character escaped unharmed. Reveal or rewrite a hostile's hidden purpose.

## Hask Meadow dry run (Test E, run-1 evidence, not canon)
Aero's third failed death save came while the pack dragged him into the trees (evt_0084; pack table evt_0079 = drag; saber left by the fence evt_0087).
- **Under this rule:** Mark 1. The survival path would be "Taken" (evidence evt_0079) or "Left for dead", by a die. One cost would be rolled from lasting wound (evt_0076), lost equipment (evt_0087), exhaustion and escalation (evt_0005).
- **Next scene:** Aero wakes 1d4 hours later where the path puts him, hurt, without his saber. The mystery continues because of the loss.
