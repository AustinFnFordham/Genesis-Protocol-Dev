# Protagonist Continuity — PROPOSED (not in force)

Status: **proposed 2026-11-06, awaiting the owner's approval.** Until approval is recorded in `DESIGN_DECISIONS.md` and `continuity_rule.json` says `"status": "approved"`, the standard death rules apply. Tool: `creator/continuity.py` (dry-run only while proposed). Test E: `creator/test_continuity.py`.

## Why
The first Hask Meadow run ended the protagonist's story before chapter one. The dice were right; the campaign shape was wrong. This rule protects the **story**, not the character's body: Aero can lose, bleed, be dragged off and lose his saber. During the opening he cannot die.

## The rule (smallest coherent version)
**Who:** main-party player characters with validated sheets (Aero now).

**Protected phase:** from the start of the campaign until the earlier of Aero reaching level 3 or the close of the Hask Meadow arc. **During the protected phase, a protected character cannot permanently die.** That is stated plainly; the death saves are not a bluff.

**Trigger (mechanical, nothing else):** a protected character *would* die: a third failed death save, damage at 0 HP equal to or above maximum HP, or an instant-death effect.

**Effect: Spared.**
1. Every committed event stands: the hits, the damage, the drag, the dropped gear, the rolls. Nothing is re-rolled or rewritten.
2. The character is stable at 0 HP, unconscious. They wake per the normal rule (1 HP after 1d4 hours, rolled). The world keeps moving on its schedule meanwhile.
3. The GM commits a public `continuity_invoked` event, then applies **costs** (below) and adds one **Mark**.
4. No ally, item or escape is invented. Whatever happens next must follow from established events, hidden truth, or a GM table fixed before rolling and logged `gm_only`. A creature's motives are not canonized just to explain the survival.

**Costs.** Only *eligible* costs can be chosen, and each must cite the ledger events that make it possible. One is rolled from the eligible list (die size = number of eligible costs).
| Cost | Eligible when | Mechanical effect |
|---|---|---|
| Lasting wound | the killing harm was physical damage | a `lasting_injury` on the damaged part: disadvantage on checks using it, or −10 ft speed for a leg, until treated (Medicine DC 15 in a safe place) and two long rests |
| Lost equipment | an item was dropped, taken or broken in the ledger | that item stays where the ledger left it; recovering it is a goal, not a given |
| Taken / relocated | a committed event shows the character being moved or held by an actor | the character wakes where those actors took them; where, if undecided, comes from a table fixed beforehand that fits established facts |
| Exhaustion | always | two levels of exhaustion; one recovers per long rest |
| Escalation | a hostile actor with an active plan exists | that actor's next scheduled move happens sooner or stronger (one step), logged `gm_only` |

**Marks and expiry.**
- 1st invocation: one cost. 2nd: two costs. 3rd: three costs, **and the protected phase ends at once.**
- After the protected phase, death is permanent again (charter rule 8). Marks never reset during the phase.

## Variant (needs a separate canon decision)
*System-attributed survival.* The tally shard keeps its scorer alive, and each Mark becomes a debt the System can call in later. This would canonize a new System capability, so it is **not** part of the default proposal.

## Hask Meadow dry run (Test E, run 1 evidence, not canon)
Aero failed his third death save while the pack dragged him into the trees (evt_0084; pack table evt_0079 = drag); his lightsaber lay by the fence (evt_0087). Under this rule: Aero is Spared, stable at 0 HP. Eligible costs: lasting wound (evt_0076 bite), lost equipment (evt_0087), taken (evt_0079), exhaustion, escalation (evt_0005 pack hunting plan). The next scene would open when Aero wakes, 1d4 hours later, wherever the established drag ended, with whatever the GM's pre-fixed table says about that place. The mystery continues because of the loss.
