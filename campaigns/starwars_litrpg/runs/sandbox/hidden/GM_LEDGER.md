# Sandbox (NON-CANON) — round-trip test harness

This run exists only to prove Datapad Submit -> GM processor -> dice -> ledger -> Datapad.
Nothing here is campaign canon, nothing here is Aero's knowledge, and it never touches Hask Meadow.

Scenario: a holo-sim training round aboard an unnamed courier. One training remote.
- Training remote (hidden stats): AC 13, HP 4, speed 30 ft hover. Each round it fires a stun bolt: +3 to hit, 1 damage (training setting). It does not move closer than 10 ft.
- Resolve declarations exactly as in the live campaign (validator, dice skill, ledger skill, narration spec).
- After each resolved turn publish a fresh turn_context. End the sim when the remote is at 0 HP.
- New training remote (round 2): same hidden stats as round 1 (AC 13, HP 4). Aero's saber is still lit (state flag carried).
