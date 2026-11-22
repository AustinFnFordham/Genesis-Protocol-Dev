# CC-003 difficulty and RNG audit (sandbox, noncanonical)

The owner won about 1 fight in 6. This audit checks whether the dice are at fault before it touches any numbers. Every number below can be reproduced:

- `node audit/rng_audit.cjs` (raw output in `rng_results.json`)
- `node audit/balance_sim.cjs 1000` (raw output in `balance_results_1000.json`)
- Both are asserted in `test_cc003.cjs`, which runs as part of `run_all_checks.sh`.

## 1. The dice are fair

| Check | Result | Expected |
|---|---|---|
| Single stream, 200,000 d20 | χ² 20.2 (df 19; 99.9% critical value 43.8), mean 10.496 | mean 10.5 |
| Lag-1 autocorrelation | 0.00115 | 0 |
| First roll across 20,000 seeds | χ² 26.4, uniform; neighbouring seeds matching 4.94% | 5% |
| Advantage mean (100,000 rolls) | 13.808 | 13.825 |
| Disadvantage mean (100,000 rolls) | 7.146 | 7.175 |

**Mechanics checked against the code:**

- **Attack rolls.** A natural 1 always misses and a natural 20 is always a critical hit. Advantage and disadvantage cancel each other out.
- **Probability module.** It predicts hit chances that match 4,000 real engine runs to within sampling error (test: "exact predictions match the real engine empirically").
- **Pause and resume.** When the engine stops for a reaction, it resumes from the unchanged snapshot. The earlier rolls replay identically, and no die is drawn twice or skipped (CC-002 replay tests).
- **No hidden information.** NPC policies only use what they can see. Ilsa's Parry decision reads only the visible attack total and her own AC. No policy reads Aero's HP or his plan.

## 2. Why Aero loses (1,000 seeded fights per row)

| Configuration | Aero win % (95% CI) | Avg rounds | Damage taken | Round-1 damage | Aero hit % | Enemy hit % | Top causes of defeat |
|---|---|---|---|---|---|---|---|
| Duel, simple play | **16.2 ±2.3** | 2.1 | 10.2 | 8.2 | 46 | 70 | Riposte 324 · thrust in round 1: 256 |
| Duel, tactical play | **30.5 ±2.9** | 2.2 | 9.1 | 7.3 | 53 | 62 | Riposte 242 · thrust in round 1: 200 |
| Predator, simple play | 39.7 ±3.0 | 2.3 | 9.1 | 7.1 | 65 | 72 | Bite 495 |
| Predator, tactical play | 64.0 ±3.0 | 2.2 | 7.4 | 6.1 | 68 | 57 | Bite 291 · critical pounce in round 1: 46 |

**Simple play** means: close the distance, strike, then Flow Strike, with no reactions. **Tactical play** adds Feint, a Force-guided first strike, Parry, Riposte and Dodge, plus a readied Dodge when Aero is at 4 HP or less.

The owner's 1 win in 6 (about 17%) is exactly the simple-play duel rate. That is bad luck only in the sense of being the expected outcome.

**Causes:**

1. **Aero's margin is two hits.** He has 11 HP, and Ilsa's thrust does 1d8+3 (4–11, average 7.5). She hits AC 13 65% of the time. Her round-1 damage alone averages 7.3, about two-thirds of Aero's HP. A fight lasts about two rounds, which leaves almost no room for tactics to pay off.
2. **Ilsa's defenses stack.**
   - AC 15 already means Aero's +5 strike hits only 55% of the time.
   - Her Parry turns another 10 points of those hits into misses, for a net hit chance of 45%.
   - Every miss gives her a free counter (Riposte).
   - **Riposte is the single biggest killer** in the duel.
3. **Aero's best defense is a proposal and costs his offense.** Parry and Dodge use his one Reaction. A readied Dodge spends his Secondary action, which is the same resource Feint needs.
4. **Predator.** The pounce from hiding always has advantage, and Aero cannot act first. With tactics this fight is fair (64%). Without them it is a coin toss weighted against him.

## 3. Alternatives (sandbox proposals; nothing is rerolled, only fixture data changes)

| Proposal | Win % (tactical play) | Effect |
|---|---|---|
| **P1** Intro Ilsa: AC 14, HP 16, blade +4 / 1d6+3 | **57.5 ±3.1** | Still dangerous (Riposte is still the top killer), but winnable with good play |
| **P2** Ilsa keeps her stats but has no Riposte | **61.1 ±3.0** | Fights last longer (3.1 rounds), so tactics have time to matter |
| **P3** Predator: stealth vs passive Perception (here: Aero notices it first) | 86.4 ±2.1 | Too easy if Aero always notices it; the real proposal is a stealth contest, whose odds land between this row and the baseline |
| **P4** Predator: HP 11, bite 1d6+2 | 79.0 ±2.5 | Easier, but the pounce still crits |

## 4. Recommendations (owner decision; all remain sandbox proposals)

1. **Introductory duel: adopt P2 (no Riposte for the intro Ilsa).** Keep Riposte for the "rematch" version.
   - This removes the main cause of defeat, keeps her AC and damage honest, and lengthens fights to about three rounds, where Feint, Parry and Takedown decisions matter.
   - P1 is the alternative if Riposte is part of her identity.
2. **Predator:**
   - Keep its stats.
   - Make the ambush a stealth contest against Aero's passive Perception rather than automatic.
   - Leave the switch off until you approve it.
   - Tactical play is already about 64%.
3. **Aero:** leave HP 11 / AC 13 as on his sheet. This is a Level-1 weakness and should stay one. Approving Parry, Riposte and Dodge (currently proposals) is what moves him from simple-play to tactical-play odds.
4. **Show the numbers in play.** The composer now shows hit chances and the incoming threat, so the player can see why a readied Dodge or a Parry is worth spending.
