# Encounters, initiative and per-actor turns: scoped GM ruling (2026-11-15)

Status: **provisional campaign ruling, not in force.** It takes effect only when the owner approves it
and the release that carries it is deployed. It fills gaps: before it, the campaign had no encounter
rules beyond `TURN_CONTRACT.md` §4 item 3 (one action, one bonus, one reaction, movement, one free
object interaction; extended social actions use the action; ordinary speech is free), §4b ("when
initiative starts, the sequence ends") and the shape of `combat_round` events. The repository holds
no SW5e combat-chapter text, so every line is a ruling in the standard d20 reading, not a quotation.
Companion files: `ACTION_ECONOMY_RULING.md` (objects, hands, NPC cooperation). Executable form:
`development/encounter/encounter.py`. Owner decisions still open are in §9.

## 1. Who is in an encounter
Every creature that can act in it is a participant with a stable actor id, its own initiative count
and its own budget: the player character, companions and bystanders who act, and each hostile
creature individually. A creature that is merely nearby and not acting is not a participant.

## 2. Each actor's turn budget
On its own turn: one action; one bonus action only if a feature it has grants one; movement up to its
speed; one free object interaction (`ACTION_ECONOMY_RULING.md`). Off its turn: one reaction.
- Everything except the reaction is regained at the start of the actor's own turn and is gone when
  that turn ends.
- The reaction is regained at the start of the actor's own turn, not at the top of the round.
- Dash is an action that adds the actor's speed to its movement for that turn.
- An incapacitated actor (unconscious, stunned, paralyzed) still has a turn in the order; it can
  spend nothing in it and has no reaction.

## 3. Order
Highest initiative first. Each participant takes exactly one turn per round. Creatures of one kind
may share one initiative count; they then act one after another on that count. A shared count is an
ordering convenience only: there is no shared action pool, no pooled movement, no extra attack and
no shared reaction. A creature that joins acts when its count next comes up. A creature that leaves
is removed and keeps no claim on the round.

## 4. Commands, Ready and Help
- Speaking a command is free for the speaker and is not an action for the listener. It does not
  give the listener a turn.
- The listener acts on its own turn. To act on a word spoken during someone else's turn, it must
  have taken **Ready** on its own earlier turn (its action then; its reaction when the trigger
  happens; one readied act; it lapses unused at the start of its next turn).
- **Help** is an action: it aids one creature's next ability check, or its next attack against a foe
  within 5 ft of the helper. Steadying, coaching or bracing that is not the Help action is fiction
  with no modifier, unless a rule for it is adopted (§9).

## 5. When a turn ends
A submitted declaration is not the end of a turn. The GM resolves every legal step in it, in order,
and stops at the first genuine decision or interruption. The turn ends when the player says so
("end my turn"), or when nothing is left to spend. Otherwise the same turn continues with what
remains, and the round does not advance. The validator reports which (`TURN_ENDS` /
`TURN_CONTINUES`).

## 6. Observation, speech and the core actions
| Activity | Cost |
| --- | --- |
| What is plainly there to see or hear (passive Perception) | Nothing. It is reported, not bought |
| Brief speech, a question, a short instruction | Nothing (`TURN_CONTRACT.md` §4 item 3) |
| A sustained exchange, questioning, persuasion with a check | The action (same line: "extended social actions in combat use the action") |
| **Search**: a deliberate, focused look or listen that calls for a check | The action |
| Dash, Disengage, Dodge, Help, Hide, Ready | The action |
| Opening or closing a comm, a switch, a latch | The object interaction (`ACTION_ECONOMY_RULING.md` §1) |
| Asking someone to hand something over | Speech; the handing is theirs (`ACTION_ECONOMY_RULING.md` §3) |

Dash, Disengage, Dodge, Help, Hide, Ready and Search are always available in combat. The validator
adds them to every combat context; an option list is never the limit of what may be declared.

## 7. Encounter mode
`combat`: initiative and six-second turns. Warranted while a creature can act on an opponent within a
round, or a hazard runs round by round. `standoff`: the same creatures, hostile and in place, but
neither side can reach the other within a round. No initiative; time passes as the fiction needs;
the hostile side's patience, plans and positions keep moving in the hidden simulation. `scene`:
no encounter.
- A mode changes only through a committed `encounter_mode` event with a stated reason citing
  committed events, between turns. It is never automatic and never silent.
- Entering a standoff removes nobody and heals nothing. Combat resumes, in the existing order, the
  moment someone attacks, a barrier between the sides opens or is breached, a side moves to where it
  can reach the other, or a hazard starts running round by round.
- Nearby enemies alone do not keep combat running, and a quiet round alone does not end it.

## 8. What the player sees
A tracker in the turn context: mode, round, who is acting, who is next, and for each visible
participant its initiative, who decides it, conditions, readied action and what it has left.
Creatures the character has not perceived appear as one anonymous slot per side and count, with no
names, numbers, budgets or positions. The tracker is derived from the record by the encounter
controller; a GM provider cannot write it.

## 9. Owner decisions still required
1. **Who decides Wick's actions in an encounter.** The charter says party members other than the
   active PC are "GM-driven and transferable" and that companions act from their own convictions.
   Wick is not recorded as a party member. Options: (a) GM-driven: he acts on his own turn from his
   own state; your words inform him; (b) player-directed: you declare his turn's tactics on his
   count, and the GM may still have him balk where his convictions demand. Until ruled, the
   controller records `control: undecided` and will not start his turn.
2. **Wick's initiative.** Not rolled. To be rolled when the encounter record is adopted.
3. **A steadying/bracing rule.** Whether physically supporting someone's aim outside the 5 ft Help
   case should give anything (for example advantage cancelling long-range disadvantage). Not
   invented here.
4. **Blaster pistol and Wick's statistics.** Both are provisional in GM rulings; no item or NPC
   record exists in the repository.
5. **Shared count for the dogs.** Kept as established (one count, 7). Individual counts would need
   new rolls.
