# Composite Turn Contract (turn-contract/1)

Owner-requested 2026-11-06 (Experience Contract, Parts III–V). Implementation: `ui/turn_contract.js` (single source, used by the Datapad preview and by the GM processor under node). Tests: `ui/test_turn_contract.py`.

This supersedes charter rule 1's "no menus unless asked": the owner asked. Free text stays first-class and goes through the same validator.

## 1. Who does what
| Role | Responsibility |
|---|---|
| Player | Declares speech, intent and actions for player-controlled characters. |
| Rules (validator + GM) | Action economy, capability, range, geometry, resources, risks; then dice. |
| Chaos | Eligible boons, banes and consequences (rules only; none active yet). |
| Atomic / Ledger | Canonical events. Nothing is narrated before it is committed. |
| Soul / Narration | Prose from committed events (`creator/NARRATIVE_SPEC.md`). |
| AMD / SID | Moral and social consequences from established events, never from a dialogue *label*. |
| Datapad | Shows state, captures declarations. It never adjudicates. |

## 2. Turn context (published by the GM every turn)
`view/state.turn_context`, player-visible only. It never contains DCs, enemy HP or AC, hidden capabilities or GM-only facts.
- `actor`, `actor_name`, `actor_conditions`, `mode` (`combat` or `scene`), `round`
- `budget`: `action`, `bonus_action`, `reaction`, `movement_ft`, `object_interaction` (what is left this turn)
- `resources` (Force Points etc.), `state_flags` (e.g. `saber_ignited`)
- `dialogue[]`: `{id, approach, text, extended}`. Approaches are tones (empathetic, investigative, assertive, deceptive, calming, defiant…), not Good/Evil buttons.
- `options[]`: `{id, slot: action|bonus_action, label, detail, area_ft?, reach_ft?, needs_target?, needs_trigger?, requires[], cost, aliases[]}`
- `objects[]`, `movement[]` (`feet`, `leaves_reach_of[]`, `blocked_by[]`), `reactions[]` (`trigger`)
- `visible[]`: what the actor can see: `{id, label, distance_ft, hostile, conditions}`

Options are contextual examples, not a closed list. Anything else may be written freely.

## 3. Declaration
```
{ actor, source: composer|freeform, freeform,
  speech: {option, text, approach, extended} | null,
  actions: [{option, target, trigger}], bonus_actions: [...],
  movement: {option} | null, objects: [ids], reactions: [ids], unmapped: [text] }
```
Free text is parsed into the same shape (aliases published with each option). Every matched action is kept, so a conflict is shown rather than silently resolved. The GM may re-read free text with judgment, but must re-run the validator on the result.

## 4. Preflight (before any roll)
1 parse; 2 acting character (only the active actor; viewing another member grants nothing); 3 action economy (one action, one bonus, one reaction, movement, one free object interaction; extended social actions in combat use the action; ordinary speech is free); 4 capabilities and requirements; 5 range, target and area (who an area power reaches and who it does not); 6 movement distance and path; 7 resource costs; 8 visible reaction and opportunity-attack risks (prone does not prevent an opportunity attack; Disengage does; hidden capabilities are never consulted); 9 incompatible selections; 10 an ordered legal preview.

- **Errors** block submission and come with legal alternatives that are themselves validated.
- **Warnings** (known risks) need the player's confirmation, never a silent drop.
- Preflight never predicts dice and never guarantees success: an unknown enemy reaction can still interrupt, an attack can still miss.

## 5. Dialogue
A chosen line is the player's declaration of speech. The listener answers from their own state, knowledge and relationships. A chosen approach never changes Aero's morality, alignment or personality by itself (AMD evaluates established acts, not labels).

## 6. Submission states
`draft → validating → submitted → processing → committed`, or `needs_revision` (legal conflict or stale state; no dice rolled) or `failed` (processing error; nothing narrated). Action ids are minted once per draft, so retries and double taps write the same document. The processor claims an action exactly once (versioned write) and processes only actions made against the current ledger revision.
