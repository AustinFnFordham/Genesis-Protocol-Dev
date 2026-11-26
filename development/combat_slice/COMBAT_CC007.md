# CC-007: combat correctness and skill-progression foundation — handoff

**Branch:** `dev/cc005-server-verify`, starting from `6bf7aa8`. Everything is sandbox-only.

**Not touched:** Hask Meadow, `shared-1`, `shared-0002`, Oracle; the gateway and Crucible branches (not merged); the d20, Narrative Consequences and Crucible dice.

**Nothing promoted to live gameplay.**

## Commits

| SHA | What | Full regression |
|---|---|---|
| `90950cd` | Owner rulings amendment v1 (`CC007_OWNER_RULINGS.md`): R-1 to R-4; existing campaign rulings and new sandbox approvals kept separate | docs |
| `0b570ba` | **A:** Feint advantage lapses at the end of the feinter's turn (fixes audit X-1) | 72 suites / 0 failed |
| `1901a0c` | **B:** scripted-dice tests for natural 20 (critical doubles the dice, not the modifier), Parry vs critical, natural 1, and defender-wins-ties for Feint, Bind and Grapple | tests only |
| `0cff177` | **C:** basic Grapple: size limit, escape contest, drag at half speed, release conditions, Main cost | 72 / 0 |
| `3066729` | **D:** Sentinel Balance 2 uses per long rest: spend, decline, exhaustion, short vs long rest, replay | 72 / 0 |
| `2184182` | **E:** Battle Insight: the missing timing and concentration contract is documented; current behaviour pinned | 72 / 0 |
| `df0d05a` | **§8:** seed `782273157` diagnosis and test fix | 72 / 0 |
| `7c6eb35` | **§3:** SA-001 proposed contract and A/B/C balance study | — |
| `a22f832` | **§4/§5:** mastery substrate and the Telekinetic Control prototype | **73 / 0** |
| `b4a80fe` | **§6:** Grapple progression scaffold | — |

**Test counts:**
- `test_cc007.cjs`: 64 checks.
- `development/progression/test_progression.cjs`: 50 checks.
- Both are in `run_all_checks.sh`.

## Seed diagnosis (§8)

**Verdict: a legitimate fight plus a wrong test assumption.**

**What happened:** with seed `782273157`, Aero opens with a natural-20 critical (16 damage), then Flow Strike does 4. Ilsa is down before her first turn: 5 player dice, 0 GM dice.

**The fix (stricter, not weaker):** the old "GM dice > 0" check was replaced with an **ownership** invariant: every die is rolled by its owner's side, and the GM dice equal Ilsa's dice. A tautological clause was also removed.

**Evidence:** `SEED_782273157_DIAGNOSIS.md` and the §8 checks in `test_cc007.cjs`.

## Decisions remaining before any canonical adoption

| # | Topic | Options and recommendation | Document |
|---|---|---|---|
| D-1 | Telekinesis repositioning consequence | unchanged, still open | audit |
| D-9 | SA-001 | **Recommended: rule C** (no Secondary budget; tactical activities cost Bonus). A stays opt-in or progression-granted. | `SA001_PROPOSED_CONTRACT.md` |
| D-13 | Battle Insight concentration | Needs `round_seconds`, a concentration state, break rules and target validity | `BATTLE_INSIGHT_TIMING_CONTRACT.md` |
| G-1 | Creature sizes | Fixtures all labelled Medium; real sizes are needed | `scenarios.json` |
| P-1 | Defining a "legitimate use" for XP (anti-farming) | Options: a per-scene routine cap, requiring a declared purpose, or unlimited | `TELEKINETIC_CONTROL_PROGRESSION.md` |
| P-2 | Telekinesis range growth | Reaches 130 ft at L20; cap it or slow it? | same |
| P-3 | XP bonus classes | Demanding / novel (candidates); in-encounter (off) | same |
| P-4 | Milestone content at levels 5, 10, 15 | Eligibility only; needs owner approval | same |
| P-5 | Where live mastery state lives | Gateway ledger vs character runtime (GPT's lane) | same |
| P-6 | Uncertain-use roll | Jedi Fundamentals open item 1; uncertain uses are refused until it's set | same |
| G-2 | Grapple skill-tree content and curve | Owner to supply | `GRAPPLE_PROGRESSION_SCAFFOLD.md` |
