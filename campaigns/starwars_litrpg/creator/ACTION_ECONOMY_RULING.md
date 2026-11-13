# Action economy and object handling: scoped GM ruling (2026-11-13)

Status: **provisional campaign ruling**, Star Wars LitRPG, in force for adjudication from the release
that carries it. It records how the GM applies the action economy already stated in
`TURN_CONTRACT.md` §4 ("one action, one bonus, one reaction, movement, one free object interaction;
ordinary speech is free") to cases that text does not spell out. The repository holds no SW5e
combat-chapter text to cite, so each line below is a ruling, not a quotation; it follows the
standard d20 reading the campaign has used. The owner may replace any line; history is not rewritten.

Origin: Hask Meadow round 9 (`evt_1379`–`evt_1385`, action `amwedw246slt3u6`). Two defects were
confirmed there: the validator billed "let go of the blaster" as an object interaction, and round 7
billed drawing a blade already in hand back through a cut as one, which pushed switching it off onto
the action (`evt_1345`). Those records stand as committed; see "Historical repair" below.

## 1. What an object interaction is
One per turn is free; a second one in the same turn takes the action. It is **taking possession of or
operating an object**: draw, stow, holster, clip on, pick up, take something from a container or from
someone's grip, open or close, throw a switch, hand something to someone.

## 2. What is not an object interaction (no cost)
- **Release.** Letting go of, dropping, or taking a hand off something. The thing falls, stays where
  it is, or stays with whoever else holds it. Setting it down with care somewhere chosen is §1.
- **Contact without possession.** Laying a hand on something another character holds (steadying,
  pointing, guiding) does not put it in Aero's possession. The first deliberate contact that
  redirects the object is the turn's object interaction; keeping the hand there, and taking it away,
  cost nothing. His hand is occupied while it stays there.
- **Repositioning something already held.** Shifting grip, lowering, raising, pointing, drawing a
  held blade back out of a cut. Igniting or extinguishing a held lightsaber remains §1.
- **Receiving.** Another character puts an object into a hand Aero already has free. Aero spends
  nothing; he needs that hand free at that moment.
- **Brief speech**, including a short instruction to someone. Only an extended exchange takes the action.

## 3. Whose act it is
Each character has their own hands and their own economy. What an NPC does is never charged to Aero
and never checked against Aero's hands (only what Aero receives is). An instruction is Aero's speech;
carrying it out is the NPC's act.

## 4. NPC cooperation
An NPC asked to do something decides from their own state, knowledge and relationship. The GM neither
assumes cooperation nor invents refusal. When the outcome is not settled by committed events, it is
decided by a table fixed before rolling, like any other undecided fact. If the NPC declines or
hesitates, the steps that depended on it stop as a `prerequisite` stop and the player decides.

## 5. Hands
Hands are judged per item and per task from the record: how many hands the item or the task needs,
which of Aero's hands are occupied at that point in the declared order, and whether the recipient
takes part. There is no blanket "two free hands" rule. An item with no stated hand requirement is
one-handed.

## 6. Order
Steps resolve in the player's order. A release declared before a receive frees the hand for it; the
same two steps in the other order stop at the receive (`HANDS`). The GM never reorders steps, adds a
release the player did not declare, or picks which hand.

## 7. Rolls
A routine act (pressing out an ember, handing something over, letting go) takes no roll. A roll is
called only when the outcome is uncertain and something meaningful rides on it.

## How the Datapad and the validator carry it
The GM publishes, from committed events only:
- `objects[].cost: "none"` on §2 acts;
- `objects[].by: "<npc id>"` on acts another character performs (§3, §4), with `takes_hands` when
  Aero receives something.
`turn_contract.js` then spends no object interaction for them, shows "(no action)" or "(theirs to
do, no cost to you)", and adds the `NPC_COOPERATION` note. Objects without these fields keep the old
accounting, so contexts already in the ledger read exactly as before. Tests:
`ui/test_action_economy.py`.

## Historical repair (not applied)
`evt_1345` (round 7): the withdraw was billed as the object interaction and the deactivation as the
action. Under §2 the withdraw costs nothing and the deactivation is the free interaction, so Aero's
action that round would have remained. Nothing mechanical followed from the spent action in the
committed record. If the owner wants it noted in the campaign record, the form is one public
`owner_ruling` event citing this file; no event is voided and nothing is rerolled.
