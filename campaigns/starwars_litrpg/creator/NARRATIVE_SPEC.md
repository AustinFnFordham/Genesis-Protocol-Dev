# Narrative Specification — adult horror, graphic-novel prose

Owner-set 2026-11-06 (Experience Contract, Part II). Applies to every `gm_narration` event. Narration presents committed events; it never creates them. Checked by `turn.py lint` (Test F) and by the GM before publishing.

## The standard
Coherent, sustained, cinematic horror. Not more adjectives or more blood: the right amount of physical truth, held long enough to matter, with dread before and aftermath after. Combat can be brutal and terrifying, but the world state underneath it stays exact.

## A. Geography first
Before or within the first lines of any violent scene, the reader can answer: where Aero stands, where each threat is (left, right, behind, how far), where cover, exits, allies and light are, which side of him is exposed. Name distances in plain terms ("an arm's length", "twenty feet, between you and the gate"). Where a dropped item lands is stated and committed (`world_fact`). Positions in prose must match the turn context and the committed movement.

## B. Injury follows the numbers
Describe a wound at the severity the dice committed. Damage as a share of maximum HP is the guide:
| Committed damage | Describe as |
|---|---|
| under 25% of max HP | a graze, a shallow bite, a burn: painful, bleeding, functional |
| 25–50% | a deep wound: tearing, heavy bleeding, impaired use of that limb this scene |
| over 50%, or to 0 HP | a mauling: shock, blood loss, the body failing; the limb cannot bear weight |
| 0 HP | unconscious and dying: no further action, perception fades in fragments |

**Lasting damage** (broken or shattered bones, severed tendons, lost limbs, blindness, paralysis) appears only when a committed public `lasting_injury` event exists for that character, from a real rule or an approved consequence. 0 HP alone authorizes none. Once a lasting injury exists, every later scene accounts for it (gait, grip, pain, how others look at it).
Physical aftermath carries forward: a bitten thigh means limping and a blood trail next turn, a hand burned to the bone means the saber goes in the other hand. Conditions on the sheet (prone, grappled, unconscious) are shown, not just named.

## C. Sustain the horror
Violence is the peak, not the whole. Build dread from what the world has established: the pack's silent coordination, a dead woman's voice repeating word for word, the blocked escape, six missing people, things dragged toward the trees, a sealed silo. Hold on the moments that matter (the bite, the drag, the helplessness) with sound, smell, temperature, texture and the hostile intelligence watching. After violence, show the cost: blood in the gravel, the silence, what is missing, who saw.
Never rush past a consequence the dice paid for. If a paragraph spends four lines on teeth, the fall, the drag and the fade get their due too.

## D. Perspective
Narrate what Aero physically perceives and what the rules establish. Involuntary responses are fair (a scream, shaking hands, vision tunneling, nausea). Convictions, motives, decisions, emotional conclusions and private thoughts are the player's: never "Aero realizes he is afraid of dying", never "he decides to run". When Aero is unconscious, perception is fragmentary and partial; the world beyond his senses stays unseen.

## E. Mechanical truth
Every hit, miss, save, condition and movement in the prose has a committed event. Do not add a mechanical effect because it reads well (no extra prone, no disarm, no bleed condition) unless a rule or ledger event created it. A miss is a miss; a natural 1 is not automatically a humiliation unless an approved Chaos rule says so.

## F. Vary intensity
Maximum gore is earned by danger, injury, vulnerability and established horror. Dialogue, investigation and recovery scenes are quieter and character-driven, which is what makes the violent ones land. Tiers: 1 quiet (talk, travel), 2 tense (threat present), 3 violent (blood, pain), 4 catastrophic (mauling, 0 HP, death or near-death).

## Pre-publish checklist (Test F)
1. Every violent beat cites a committed event; positions match the turn context.
2. Wound descriptions match the damage band; no lasting damage without a `lasting_injury` event.
3. Aftermath of earlier injuries is carried.
4. No thoughts, decisions or emotions authored for player characters.
5. No hidden information (DCs, enemy stats, GM-only facts) leaks.
6. `turn.py lint` passes.
