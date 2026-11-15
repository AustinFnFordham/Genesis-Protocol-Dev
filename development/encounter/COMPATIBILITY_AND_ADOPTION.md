# Encounter control, pacing, dice modes and Narrative Consequences: compatibility report and staging adoption plan

2026-11-15. Branch `dev/encounter-controller`; commit `2425e54` is preserved and this report is added
on top of it. Nothing was activated, migrated, rerolled, advanced, merged or deployed. Live Hask
Meadow is at `ebda584` (revision 1125) and its records are byte-identical on this branch.

## 0. What was and was not read

| Source | Status |
| --- | --- |
| `development/experimental_resolution/README.md`, `policy.py`, `engine.py`, `test_resolution.py`, `compare_scenes.py` at `rc/canonical-dice-recovery-f241ea6` = `1acf2a0f82c5a5cc374cc3d72fd839e2040d3d5c` | Read in full. Identical on this branch |
| `DICE_RECOVERY_RECONCILIATION.md`, `dice_transaction.py`, `test_legacy_dice_recovery.py` (recovery contract) | Read |
| `CAMPAIGN_CHARTER.md`, `creator/TURN_CONTRACT.md`, `creator/DESIGN_DECISIONS.md`, runbook `SKILL.md` (live text at `ebda584`), `hidden/PACK_PROFILE.md` | Read: the adopted pacing, companion and action-economy decisions |
| `Genesis_Gemini_Link_Continuity_Audit_2026-11-13.md`, sections 13–16 | **Not available.** Not attached to the session, not in the project documents, not in any of the 18 remote branches (searched by file name and by content), including the three branches other sessions pushed since (`dev/gemini-mcp-provider`, `dev/chatgpt-gateway-adapter-6942257`, `dev/shared-mobile-gateway-reconciled`) |

Consequence: every "existing requirement" below is sourced from the repository. Nothing here is
reconciled against the Gemini Link design, and no row should be read as agreeing or disagreeing
with it. Section 5 lists what must be rechecked when the audit is supplied.

## 1. Three axes, kept separate

| Axis | Values | Who sets it | Where it lives | Selected by another axis? |
| --- | --- | --- | --- | --- |
| Encounter mode | `scene`, `combat`; proposed `standoff` | The GM, by a committed event with a reason | `turn_context.mode`; proposed `encounter_mode` events | No |
| Resolution temperature | Regular (default), Heroic, Legendary | The player, per submitted action | `action.resolution_settings.temperature`, copied into the `player_declaration` event | No |
| Narrative Consequences | Off (default), On | The player, per submitted action | `action.resolution_settings.narrative_consequences` | No |

Verified in code and by test (`test_a_companion_roll_is_never_treated_as_the_players`): beginning an
encounter changes no dice setting; the next action defaults to Regular/Off; the tracker carries no
resolution field; the controller reads and writes no resolution data.

Correction to the earlier diagnosis: Regular/Heroic/Legendary and the narrative d6 **exist as design
and as tested code**. What is absent is their integration into live Hask Meadow (no marker, no
controls on the live page, no settings on live actions). The audit file now says so.

## 2. Experimental resolution: preserved exactly

Nothing in `development/experimental_resolution/` was changed by the encounter work. The gateway
calls the existing engine; there is no second resolver.

| Property (README / code) | Preserved? | Evidence |
| --- | --- | --- |
| Formulas: Regular raw; Heroic `11 + floor((raw-1)/2)`; Legendary `16 + floor((raw-1)/4)` | Yes | `policy.effective` untouched; `test_dice_modes_follow_the_inspected_policy_across_providers` |
| Eligibility: player-controlled check, attack or save with exactly one positive single d20 | Yes | `policy.resolve` untouched |
| Critical precedence: original 20 is the only critical; original 1 auto-misses only in Regular; checks and saves compare totals | Yes | Untouched; inherited `test_natural_critical_policy`, `test_npc_attack_critical_rules_remain_regular` pass |
| Raw / selected / effective faces, other dice and modifiers kept separately | Yes | Engine record untouched |
| Submitted settings immutable; unknown values fail closed | Yes | Action binding in the engine; settings are part of the gateway's immutable action identity and are written into the declaration event |
| Narrative d6 on its own domain-seeded stream, zero ordinary draws | Yes | `engine.narrative_face` untouched |
| Deterministic replay | Yes | `engine.replay` asserted after multi-provider and encounter turns |
| Recovery: accepted plan resumed byte for byte; keyed retries return receipts; unkeyed interruption needs explicit `--recover-pending` | Yes | Inherited recovery suites pass; gateway rolls are always keyed `<action_id>:<roll_key>` |
| Private task/degree/margin/DC and causal candidates stay private | Yes | `public_resolution` allowlist untouched; gateway leak tests |
| Chaos assessment commits nothing by itself | Yes | `assess_causal` untouched |
| Sandbox-only: explicit non-canonical marker, source campaign directories refused | Yes | No marker added anywhere |

## 3. Actor control and dice eligibility (Wick)

How eligibility is actually decided (`engine.py` line 130):
`controlled = roll.requested_by == action.actor and roll.requested_by in marker.controlled_actors`.
Both must hold. The roll must be requested by the character who submitted the declaration, and that
character must be listed in the campaign copy's marker.

| Situation | Dice treatment | Why |
| --- | --- | --- |
| Aero's own check, attack or save, Aero is the declaring actor | Eligible for the submitted temperature and narrative axis | Both conditions hold |
| Wick acts because Aero told him to | Regular, no narrative axis | The roll is requested by the GM, not by the declaring actor |
| Wick is `player_directed` in the encounter record | Regular, no narrative axis | Encounter control is not read by the resolver. Tested |
| Wick is `gm`-driven | Regular, no narrative axis | Same |
| The player takes Wick as the active PC (charter: "any other party member they later take control of") **and** he is added to `controlled_actors` | Eligible on turns he declares | This is a change of active PC and of campaign configuration. It needs an owner ruling on the record. No command, turn or readied action can cause it |

So a player-issued command cannot change Wick's control classification (no event kind changes
control; `test_control_classification_is_not_changed_by_play`) or his dice treatment (the gateway
accepts a roll only for the declaring character, `gm` or `gm_hidden`; a request "as" the ally is
refused). Committed play is consistent with this: Wick's shot was rolled by `gm` as an ordinary roll.

Whether player-directed tactical control should ever carry the player's dice settings is not
decided anywhere. It is listed as decision D3; the code's answer today is no.

## 4. Initiative and pacing: each item classified

Classes: **ER** existing requirement (adopted text in the repository). **IB** implemented behaviour
(how the live worker ran, with no adopted rule either way or following its runbook). **NP** new
proposal (authored in `ENCOUNTER_RULING.md` / `ACTION_ECONOMY_RULING.md`, provisional, not adopted).
**UD** unresolved decision.

| # | Item | Class | Source | Did committed play break an adopted rule? |
| --- | --- | --- | --- | --- |
| 1 | One action, one bonus action, one reaction, movement, one free object interaction | ER | `TURN_CONTRACT.md` §4 item 3 | No |
| 2 | Ordinary speech is free; extended social actions in combat use the action | ER | Same | No. The "Ask Wick something" option stated exactly this. Listing "Ask Wick for the blaster back" in the action slot sits badly with it, but its text did not charge an action for the asking |
| 3 | Resolve in the player's order; stop at the first step that needs the player; never add a step or decide a condition | ER | `TURN_CONTRACT.md` §4b, runbook §3 | No |
| 4 | "One narrative decision point per turn" | ER | `TURN_CONTRACT.md` §4b | No |
| 5 | After the declared steps, resolve every NPC and enemy turn up to the player's next decision point | ER (runbook) | Runbook §3 | No. Ending Aero's turn after a complete submission and running the pack's turn is what this text prescribes. **My earlier wording called this a procedure defect; it is the adopted procedure producing a poor result** |
| 6 | A turn stays open after a mid-turn stop | IB, consistent with ER 3 | `evt_1382` (HANDS stop) | No |
| 7 | A submission does not end the turn; the turn ends on the player's word or when nothing is left | **NP** | `ENCOUNTER_RULING.md` §5 | Not applicable. It would replace item 5's effect in combat |
| 8 | When initiative starts, the scene sequence ends | ER | `TURN_CONTRACT.md` §4b | No |
| 9 | When to leave initiative | **UD** (no adopted text) | — | No rule existed to break. Keeping combat for rounds 7–11 was a GM judgment |
| 10 | Standoff mode and its resume triggers | **NP** | `ENCOUNTER_RULING.md` §7 | Not applicable |
| 11 | Only the active PC is player-controlled; others are GM-driven and transferable; companions act from their own convictions | ER | Charter, "Companions and relationships" | No. Wick's compliance followed his recorded convictions and a table |
| 12 | A companion's initiative count and turn budget | **UD → NP** | None before; `ENCOUNTER_RULING.md` §1–§4 | No rule existed. Wick acting outside initiative is a gap, not a violation |
| 13 | A listener acts on a spoken word only through Ready | **NP** | `ENCOUNTER_RULING.md` §4 | Not applicable. The shot is consistent with one legal reading under it; that is an observation, not a judgment |
| 14 | Help needs the foe within 5 ft of the helper; bracing gives no modifier | IB as a GM ruling (`evt_1402`), restated as NP | `evt_1402`; `ENCOUNTER_RULING.md` §4 | No. The ruling was made at the time and applied |
| 15 | Enemies as one initiative label ("the drover-dogs", 7) | IB | `evt_1240` | No |
| 16 | Each hostile creature tracked with its own budget on a shared count | **NP** | `ENCOUNTER_RULING.md` §3 | Not applicable. Under it, the dogs' recorded moves fit their budgets |
| 17 | Pack doctrine: lure, do not charge, isolate, withdraw at half; "light and noise: roll honestly" | ER (owner ruling 2026-11-06) | `PACK_PROFILE.md`, `evt_0012` | No |
| 18 | Undecided facts are settled by a table fixed before rolling | ER | Runbook §3 | No |
| 19 | NPC tables must account for what changed; a third identical outcome needs a reason | **NP** | `npc_review.py`, runbook §3d (candidate) | Not applicable |
| 20 | Reactions: a declared reaction is a standing instruction; an undeclared one stops the plan with a prompt; surprised means none | ER | `TURN_CONTRACT.md` §4c | No |
| 21 | Reaction regained at the start of the actor's own turn | **NP** | `ENCOUNTER_RULING.md` §2 | Not applicable |
| 22 | Letting go, contact, shifting a held thing and receiving cost nothing | **NP** | `ACTION_ECONOMY_RULING.md` §2 | Not applicable. The round-7 and round-10 charges were consistent with the only adopted text ("one free object interaction") read strictly |
| 23 | Observation of what is plainly perceptible is free; Search is the action | **NP** | `ENCOUNTER_RULING.md` §6 | Not applicable. Passive perception was in fact reported free each round (IB) |
| 24 | Core actions always offered in combat | **NP** | `ENCOUNTER_RULING.md` §6; validator | Not applicable. Round 1 offered three of them (IB); no rule required it |
| 25 | Options are examples, never a closed list | ER | `TURN_CONTRACT.md` §2 | No. Free text was always accepted |
| 26 | Narration only from committed events; injuries match damage | ER | `NARRATIVE_SPEC.md`, runbook §4 | No lint failure. "The brace steadied the aim" described no mechanical effect; a style concern |
| 27 | Narrate what changed; do not restate standing facts | **NP** | Pacing policy | Not applicable |
| 28 | Resolution temperature and Narrative Consequences | Existing **design and code**, experimental; not adopted for live | `experimental_resolution/` | Not applicable to live play |

Net: against adopted rules the committed barn turns show **no violation**. What is real is (a) gaps
where no rule existed (companion turns, leaving initiative, per-creature budgets), (b) an adopted
procedure (item 5) that fragments a coherent intent in a combat with no contact, and (c) GM judgment
calls. The audit's "verified defects" heading overstated (b) and (c); its header now says so.

## 5. Checks requested

**An unused reaction or an unavailable bonus action cannot hold a turn open.** Verified. The
validator ends the turn when the player says so, or when nothing spendable on the player's own turn
is left. The reaction is never counted (it is spent off-turn and returns at the start of the next
turn). A bonus action is counted only when the context actually offers a bonus-action option.
`test_an_unused_reaction_or_unavailable_bonus_never_keeps_a_turn_open` shows a turn with action and
movement spent, the object interaction already spent, a reaction in hand and no bonus option closing
by itself, and the same turn staying open once a real bonus option is on offer. Movement or an
object interaction left unspent does keep the turn open until the player ends it; "end my turn"
always closes it.

**Leaving initiative weighs meaningful contests, not attack range.** The first version of
`assess_mode` looked only at whether one side could act on the other and at round-scale hazards. It
now also keeps initiative for any cited contest decided round by round (a chase, a race to a door or
switch, a breach in progress, someone slipping away, a countdown) and for any readied action waiting
on its trigger. Uncited claims count for nothing. It remains advice: only a committed, reasoned
`encounter_mode` event changes the mode. `test_initiative_is_kept_for_contests_not_only_attack_range`.

Applied to the barn (public facts only): no creature can act on an opponent within a round, no
contest is being decided by the round, and Wick's "do not fire till I say" is a standing instruction
that the record does not hold as a readied action. Advice: standoff. If Wick's posture is ruled a
readied action at adoption, the advice becomes combat until it fires or lapses.

## 6. Integration gaps

| Id | Gap | Evidence | Blocks |
| --- | --- | --- | --- |
| X1 | **The experimental engine allows one GM-requested roll per step and kind in an action.** Its no-reroll slot is `(action, step, kind, requester)`; two creatures both rolled by `gm` collide. The README says multi-roll steps "require explicit sequencer decomposition or a reviewed future roll-plan contract" | Reproduced: second creature's attack refused. Pinned by `test_known_gap_one_gm_roll_per_step_and_kind_under_the_experimental_engine`. The ordinary resolver has no such limit | Staging dice modes together with per-creature enemy turns. Fix belongs in the existing engine (add the roll's subject to the slot), reviewed; not a second resolver |
| X2 | The experimental engine requires every roll to cite a declared step. NPC turns after the player's steps have none; the gateway cites the first declared step for them | `engine.generate` | Clean provenance for NPC turns. Same reviewed change as X1 (an explicit `gm_turn` provenance) |
| X3 | The encounter record is enforced only through the provider gateway. The live Claude worker follows the runbook directly and does not call the gateway | `SKILL.md` on `litrpg/campaign-scaffold` | Enforcing initiative in live play |
| X4 | The live Datapad page predates the tracker, the core actions and the turn-continuation notes | `deploy.json`; live page built from `ebda584` | Showing any of this to the player |
| X5 | Continuity (`continuity.py`), contest/repair and `plan_progress` have not been exercised with encounter events | No test | Adoption in a campaign that uses them |
| X6 | A turn that continues across submissions means several actions in one turn. Dice settings are per action by the inspected design, so they could differ between submissions of one turn | README "Immutable input" | Nothing technically; decision D4 |
| X7 | The encounter round counter starts at 1 when the record is adopted; Hask Meadow's narrative round is 11 | Migration proposal | Presentation only |
| X8 | The Gemini Link audit sections 13–16 are unread | §0 | Any claim of compatibility with that design |

## 7. Outstanding decisions (exact)

| Id | Decision | Options | Default until decided |
| --- | --- | --- | --- |
| D1 | Who decides Wick's actions in an encounter | GM-driven on his own turn / player-directed tactics on his count | `undecided`; his turn cannot start |
| D2 | Wick's initiative | Roll once at adoption | Not rolled |
| D3 | Should player-directed control ever carry the player's temperature and narrative axis | No (code today) / yes for a directed companion's own d20s | No |
| D4 | May dice settings differ between submissions within one turn | Yes, per action (inspected design) / locked for the turn | Per action |
| D5 | Adopt "a submission does not end the turn" in place of runbook §3's effect in combat | Adopt / keep / adopt with a per-campaign switch | Not adopted |
| D6 | Adopt standoff mode and its triggers; move the barn encounter to it | Adopt and move / adopt, keep combat / decline | Not adopted |
| D7 | Is Wick's "do not fire till I say" a readied action at adoption | Yes (combat continues until it fires or lapses) / no, a standing instruction | Not recorded as readied |
| D8 | A mechanic for bracing or coaching outside the 5 ft Help case | None / a defined benefit | None |
| D9 | Approve or amend `ACTION_ECONOMY_RULING.md` and `ENCOUNTER_RULING.md` | — | Provisional |
| D10 | Records for the blaster pistol and for Wick | Create from the provisional rulings / supply | Provisional GM values |
| D11 | Keep the dogs on one shared count | Keep 7 / individual counts (new rolls) | Keep |
| D12 | Enable dice modes and Narrative Consequences for staging, then live | Per the experimental README's gate | Off everywhere live |
| D13 | Supply the Gemini Link audit | — | Unreconciled |

## 8. Ordered staging adoption plan

Each stage runs on an isolated, marked non-canonical copy (the `staging/provider-shared` pattern or
a fresh one), ends with `bash development/run_all_checks.sh` plus its own exit test, and can be
abandoned without touching a canonical record. No stage touches Hask Meadow.

| Stage | Adopts | Needs first | Exit test | Rollback |
| --- | --- | --- | --- | --- |
| 0 | Reconciliation with the Gemini Link audit §13–16; reclassify §4 rows it changes | D13 | A signed-off diff of §4 against the audit | None needed |
| 1 | Action-economy ruling and validator fields (`cost`, `by`) | D9 (that file) | A staged turn with a hand-off resolves with no object interaction billed; old contexts cost as before | Unpublish the fields; unmarked contexts are unaffected |
| 2 | Pacing: turn continuation, core actions, costs for observation and speech, change-first narration | D5, D9 | One multi-step intent resolves within one turn across two submissions; the round does not advance until "end my turn"; reaction-only turn closes | `core_actions: false`; revert the runbook section |
| 3 | Encounter record: participants, per-actor turns and budgets, tracker; ordinary dice only | D1, D2, D11; X5 tested | A staged fight with a companion and three hidden enemies: each acts once per round, off-turn spending is refused, the tracker shows one unseen slot; interrupted mid-turn and resumed by a second provider | Stop emitting encounter events; the fold returns "no encounter" |
| 4 | Encounter mode: standoff and return to combat | D6, D7 | Standoff entered with a cited reason, minutes pass, combat resumes on a breach in the existing order | Commit `encounter_mode: combat` |
| 5 | Dice modes with the encounter record | X1 and X2 fixed in the existing engine and reviewed; D3, D4 | Two enemies each roll an attack in one action under Heroic settings; only the player character's d20s are transformed; `engine.replay` ok; kill-and-resume at the seven write boundaries | Remove the marker; legacy fields keep their meaning |
| 6 | Narrative Consequences | Stage 5; SID Q15/Q16 remain provisional | On/Off across turns; effects only from validated causal candidates; "no eligible candidate" accepted with two points | Submit Off |
| 7 | Live worker and Datapad | X3, X4; all prior stages; inherited gates in `RELEASE_CANDIDATE_GATE.md` and `PROVIDER_INTERCHANGE.md` | Owner approval of the migration proposal; sandbox round trip on the live transport | Redeploy the previous page and runbook; appended events stay as inert history |

Stages 1–4 use only the ordinary resolver and do not depend on stage 5. Stage 5 must not start
before X1 is fixed: with per-creature turns it would refuse the second enemy's roll.

## 9. What changed on the branch in this pass

- `encounter.py`: `assess_mode` weighs contests and readied actions; nothing else.
- Tests added: contests keep initiative; control is not changed by play; a reaction or an unusable
  bonus action never holds a turn open; a companion's roll stays Regular under Heroic settings and
  initiative selects no dice setting; the engine limit X1 is pinned.
- `ENCOUNTER_AUDIT_2026-11-15.md`: scope correction header and corrected dice section.
- `ENCOUNTER_RULING.md`: states that it is new, cannot have been violated by earlier play, and
  selects no dice setting; §7 names contests.
- No change to `development/experimental_resolution/`, the dice transaction code, the ledger, any
  campaign record, the live branch or any deployment.
