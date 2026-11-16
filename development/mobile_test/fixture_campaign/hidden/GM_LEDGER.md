# Mobile test drill — GM-only notes (NONCANONICAL fixture)

Nothing here is canon. This scene is a holo-sim drill invented for the test build. Do not import any hidden fact
from Hask Meadow or any other campaign, and do not treat anything decided here as true anywhere else.

## Test settings (owner instruction 2026-11-15; not adopted into live Hask Meadow)
- Wick: temporary allied NPC, GM-driven, own initiative count (12), own turn and budget. Not a party member.
  Aero may ask him for things (speech, free). A command grants no extra action. He never rolls with the player's dice settings.
- Each sim hound has its own turn and budget. The three share initiative count 9 (group `sim_hounds`), acting one after another.
- Initiative counts are fixture values, not rolls. Do not roll initiative again.
- Dice: the player may choose Regular/Heroic/Legendary and Narrative Consequences per submission. They apply only to
  Aero's own d20 checks, attacks and saves. Request ordinary formulas; the resolver applies the setting.

## Layout at the start (feet)
Aero mid-floor. Wick 10 behind Aero. hound_1 15 ahead of Aero (25 from Wick). hound_2 40 ahead, by the right wall.
hound_3 HIDDEN behind the crate line on the left, 20 from Aero and 20 from Wick; the party has heard it once, not seen it.

## Statistics (fixture)
- Sim hound (each): AC 12, HP 9, speed 40. Bite +3 to hit, 1d6+1 piercing. Dexterity save +1. Passive Perception 12.
  A construct at 0 HP winks out. No morale: it is a drill program.
- Wick: AC 11, HP 8, speed 30. Blaster pistol +2 to hit, 1d6 energy, range 40/160. Passive Perception 11.
- Aero: the character sheet (api_bridge/gm/aero_character_runtime.yml) is authoritative. Lightsaber attack and damage from the sheet.
- Sim safety: a party member at 0 HP ends the drill (the deck cuts power). Protagonist Continuity is not used here.

## Behaviour
- hound_1: closes on the nearest party member and bites.
- hound_2: circles the right wall toward Wick; attacks him when it can reach him.
- hound_3: stays hidden in round 1 unless found or unless someone comes within 10 ft of the crate line; from round 2 it
  rushes whichever party member is farthest from the other. It appears in the public tracker only once perceived.
- Wick (his own motives and knowledge): frightened, wants to stay near Aero, will not advance toward a hound. On his turn he
  fires at a hound within 20 ft of him if he has a clear line, otherwise he keeps the pistol up and stays put or steps to keep
  Aero between him and the nearest hound. A short clear request from Aero that does not move him closer to a hound he follows;
  anything else is decided by a table fixed before rolling. Record an NPC evaluation for him every round.

## Procedure reminders
- Every creature's roll on its own turn: `requested_by: "gm"` (or `gm_hidden` for hound_3 while unseen), `subject` = its actor id,
  `provenance: {"kind":"gm_turn","actor_id": <same>}`. Keep hidden ids out of roll keys and purposes.
- Record `turn_start`, each `resource_spent`, and `turn_end` for every actor, in initiative order. Events for hound_3 while
  hidden are `gm_only`.
