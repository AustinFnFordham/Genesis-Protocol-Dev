# Seed 782273157: diagnosis of the intermittent combat-test failure (CC-007 §8)

**Report (Codex):** seed `782273157` fails; control seed `477528826` passes. The failing duel had **5 player dice and 0 GM dice**.

## Which test

`test_cc005b_server.cjs`, "GM dice were rolled by the server-side GM".

The test plays a whole **bound** duel through the real server with **only the player token**. Aero's plan is close, Lightsaber Strike, Echani Strike, Flow Strike, with **no Feint**, so Ilsa never makes contest rolls during Aero's turn.

The old assertion:

```js
jb.tape.filter(d => d.roller === "gm").length > 0 && <player count> === <player count>
```

The second half compares a value with itself, so it is always true.

## Reproduction (deterministic; the evidence is kept in `test_cc007.cjs` §8)

The server's `atomic_service.die_value(seed, seq, sides)` is an exact port of `engine.js` `localDie`.
- For seed `782273157`, sequence numbers 0–4, both give **20, 7, 6, 15, 4**, checked in Python and JS.
- So the same tape, replayed in-process, reproduces the server fight exactly.

| Seed | Rounds | Ilsa's turns | Player dice | GM dice | Result |
|---|---|---|---|---|---|
| `782273157` | 1 | **0** | **5** | **0** | Victory on Aero's first turn |
| `477528826` (control) | 2 | 1 | 7 | 3 | Victory |

**What happened with the failing seed**
1. Aero closes on Ilsa.
2. **Lightsaber Strike, natural 20: CRITICAL.** Damage is 2d8+3 = 7 + 6 + 3 = **16** (20 → 4 HP).
3. Echani Flow Strike hits for **4**: Ilsa is at 0/20 and down.

That is exactly 5 dice: d20, 2×d8, d20, d4. There was no refused step and no skipped turn.

## Verdict

**An incorrect test assumption, not a defect.**

| Hypothesis | Verdict | Evidence |
|---|---|---|
| A legitimate fight that ended before GM dice were needed | **Yes** | The fight above. Ilsa never had a turn, and her only reactions in that window (Parry, which rolls nothing; Riposte, which needs a miss) roll no dice. |
| A missing GM step | No | `gm_step` stopped `over` correctly; no NPC turn existed |
| A resolution defect | No | Crit doubling and damage follow R-1 (owner 2026-11-25); every value matches `die_value` |
| A wrong test assumption | **Yes** | "GM dice > 0" holds only if the NPC acts. About 1 in 20 openings (a natural 20) plus a good follow-up ends the fight first. |

## Fix (`test_cc005b_server.cjs`; the assertion is made stricter, not weaker)

The real invariant is **ownership**:
- Every die in the journal tape was rolled by the side that owns the receipt's actor. Ilsa's dice are `roller: "gm"` (server-rolled); Aero's are `roller: "player"`.
- The GM-dice count must equal the number of Ilsa's dice.

That still catches the original concern: a player rolling GM dice, or GM dice missing when Ilsa rolled. It no longer fails a legitimate one-turn win. The tautological clause is gone.

## Regression coverage

`test_cc007.cjs` §8 replays both seeds and asserts:
- the dice values;
- the one-turn victory;
- 5 player dice and 0 GM dice;
- the cause (the crit, then 16 and 4 damage);
- no refused step;
- that the control seed has GM dice.
