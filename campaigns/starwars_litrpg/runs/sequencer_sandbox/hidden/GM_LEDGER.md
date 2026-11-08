# Sequencer sandbox (NON-CANON) — end-to-end harness for turn-contract/3

Branch `litrpg/turn-builder` only. Proves: Datapad plan (sequences, branches, custom steps) -> GM processor
(branch runbook) -> dice -> ledger -> plan_progress -> Datapad, including interruption, partial commit and recovery.
Nothing here is campaign canon or Aero's knowledge, and it never touches Hask Meadow (`hask_meadow_r2`).

Scene: a copy of the dig crew's shed at the silos (from the player-visible fixture `ui/fixtures/hask_r2_sequencer.json`).

Hidden simulation (sandbox stats, invented for this harness, not Hask Meadow's pack):
- "Sandbox mastiff": starts ~300 ft north-east in the reeds, approaching at a walk while lights and noise draw it.
  Stealth +4. Bite +5 to hit, 1d6+2 piercing (kept below Aero's 11 HP so no continuity event is needed). AC 12, HP 13.
- Detection is checked when conditions change (it closes to within 60 ft; light or noise at the shed), not every 5 ft:
  its Stealth roll vs Aero's passive Perception 14.
- It closes 60 ft per sequence of activity at the shed; the chain cut (light + noise) brings it straight in.
- Wick's knowledge table (fixed before any roll, 1d6), for "is something shut in there?":
  1-3 he does not know (unsettled: no case is taken, missing information is never a yes);
  4-5 he heard the crew say something is shut inside (settles "Wick confirms something is trapped inside");
  6 he says the crew only stored tools there and meant to open it (settles "credible information supporting opening").
