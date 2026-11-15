# Proposed runtime migration: adopt the encounter record in Hask Meadow run 2. NOT APPLIED

For owner review. Nothing here has been written to the campaign. It rewrites no event, voids nothing
and rerolls nothing: it appends, in one ordinary turn resolution after approval.

Preconditions
1. `ENCOUNTER_RULING.md` and `ACTION_ECONOMY_RULING.md` approved (or amended).
2. Owner decisions 1 and 2 of `ENCOUNTER_RULING.md` §9 made (Wick's control; his initiative is then
   rolled once with the dice skill, purpose "Wick's initiative", by `gm`).
3. This candidate deployed to the worker and the Datapad page republished from the built file.

Events appended at the next resolution, in this order
1. `owner_ruling` (public): the two rulings are in force from this event; cites the files.
2. `encounter_start` (GM-only, because it lists creatures Aero has not seen):
   `encounter_id: barn_evt_1240`, `mode: combat`, participants:
   - `aero`: initiative 21 (`evt_1240`), control `player` (charter).
   - `wick`: initiative as rolled, control as ruled, speed 30, no bonus action.
   - one participant per drover-dog taking part (ids as in the GM record), each `hidden: true`,
     `group: drover_dog_pack`, initiative 7 (`evt_1240`), speed 40, control `gm`. The voice-dog is
     not a participant.
   The current round number (11) is carried in the event's summary; the controller's own round
   counter starts at 1 and is a count of rounds under the record, stated as such.
3. If the owner agrees: `encounter_mode` → `standoff`, reason "every way into the barn is shut,
   barred or bolted and the dogs do not open doors; no attack since round 6", citing `evt_1062`
   and the latest positions event.
4. The turn's ordinary events, narration and context, with the tracker derived by the controller.

Not included: any change to hit points, positions, the round-7 or round-10 object-interaction
charges, or Wick's shot. If the owner wants the two over-charges noted, that is one more public
`owner_ruling` line; nothing mechanical followed from either.

Rollback: the appended events are ordinary ledger events. Reverting the deployment leaves them in
the record as inert history; a `ruling_void` naming them removes their effect for the Datapad.
