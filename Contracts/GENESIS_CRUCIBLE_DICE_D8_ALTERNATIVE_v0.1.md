# Genesis Crucible Dice — D6 Qualifying Gate vs D8 Doubled Symbols
**Addendum:** GCD-001-A | **2026-11-23** | **STATUS: candidate variants, not accepted canonical dice, not Hask Meadow resolution.**
**Purpose:** Preserve owner's two alternative fixes for major-symbol frequency and 3:1 conversion asymmetry, with corrected exact figures. No live dice, character stats, stores, Ruin/Resolve pools or Oracle changes.

## Problem under the previous d6 face map
At 3 Agency vs 2 Entropy d6, at least one Resolve or Ruin *symbol* appears in **59.812%** of rolls, while 3+ net Strain is impossible because no more than 2 Entropy dice can contribute 1 each. Automatic banking makes "major" points routine. GCD-001 already documents exact odds and major-symbol-vs-bank separation.

## Variant A — Keep current mapped d6; qualify major banking
On each d6 face 6, the **normal** Success / Cancel Success contribution applies to the objective regardless of whether a major token is earned.
- Resolve symbol may earn at most 1 player Resolve **per accepted eligible roll** only if Resolve face occurred AND (`net_spark >= 1` OR `signed_success_margin >= 2`).
- Ruin symbol may earn at most 1 GM/scene Ruin per eligible roll only if Ruin face occurred AND (`signed_success_margin < 1` OR `net_strain >= 1`).
- These are **sample qualification predicates**, not immutable game law. Source/scene stakes, actor authorization, anti-farming and pool ownership still needed.
- To address 3 Strain conversion impossibility, either an authored high-tier Entropy die may have Double-Strain, OR a separately enabled context-dependent `2 net Strain -> 1 Ruin` alternative may apply under source-validated high mechanical pressure. The latter has major balance and character-health implications. Neither is automatic.
- Exact modeled 3 Agency vs 2 Entropy d6 conditional earn chances using these predicates: **22.749%** at least one qualified Resolve, **18.647%** at least one qualified Ruin. Both can qualify in the same roll (~3.344%). These probabilities are *conditional-rule candidates*, not rare-event guarantee.

## Variant B — Custom d8 Agency & Entropy dice (owner's current alternative)
| Face | Agency d8 | Entropy d8 |
|---|---|---|
| 1 | Blank | Blank |
| 2 | Success | Cancel Success |
| 3 | Success | Cancel Success |
| 4 | Spark | Strain |
| 5 | Success + Spark | Cancel Success + Strain |
| 6 | Success + Spark | Cancel Success + Strain |
| 7 | Double Spark | Double Strain |
| 8 | Resolve symbol + 1 normal Success | Ruin symbol + 1 normal Cancel Success |

**Arithmetic:** `signed_success_margin = agency_success - entropy_cancel`. Task success candidate = margin>=1, with domain-approved higher thresholds if applicable. Net Sparks and Strains cancel one-to-one; face 7 contributes **two** minor symbols, not a new dice roll. On face 8 major symbols do not cancel against each other; their ordinary success/cancel contributions still do. A major die symbol is not necessarily a banked point.

### Exact independent fair-d8 results
| Pool | Objective success | Nonzero net minor | 3+ net Spark | 3+ net Strain | At least one Resolve symbol | At least one Ruin symbol | Either major |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3 Agency / 2 Entropy | 54.901% | 76.303% | 11.353% | 1.807% | 33.008% | 23.438% | 48.709% |
| 4 Agency / 2 Entropy | 73.818% | 81.604% | 22.924% | 0.977% | 41.382% | 23.438% | 55.120% |
| 3 Agency / 3 Entropy | 33.749% | 76.894% | 6.938% | 6.938% | 33.008% | 33.008% | 55.120% |

Thus the owner's proposed d8 probability table is **accurate** to one decimal place IF its "Resolve Banked / Ruin Banked" columns are interpreted as *at least one major symbol appears AND every such symbol immediately qualifies to bank*. Any earning gate changes those banked probabilities. Even at d8, 3v2 still creates any major symbol **48.709%** of rolls; full auto-banking remains frequent.

**Optional 3-to-1 conversion** only after cancellation and only with NET leftover minor symbols; consume the symbols once for EITHER immediate effects OR one banked point, with a source-approved per-roll cap and anti-farming. Never also count the converted minors as a separate event spend.

## Variant C — Major symbols only on authorized special dice
An alternative is to remove Resolve/Ruin symbols from routine Agency/Entropy dice and permit them on separately granted Mastery / Conscience / scene-event dice. This may make major moments *rarer* but also risks tying Resolve earning too tightly to gear quality, privileging rich characters or falsely moralizing ordinary skills. Need a concrete exact face map, trigger frequency and progression access before approving this variant. No assumption that Conscience Die exists or may choose PCs' moral actions.

## Interoperability and UI
- Keep existing d20 authoritative rules and the live Combat Judge unchanged. Comparison experiment uses a versioned isolated `genesis-crucible-d8/0.1-candidate` engine and synthetic receipts; no mixing d20 attack hit and d8 success unless a separate bridging mapping is accepted.
- Do not impose a GAMEPLAY cap of 8 dice because a phone can only show 8 at once. Group, scroll or visually summarize all legally rolled dice. Higher-level mastery may continue to scale.
- Opponent/GM-private stats do not become public merely because the client renders Entropy dice or estimates; use projected uncertainty when necessary.
- Do not call the Conscience Die a predictor of the PC's chosen sacrifice/survival. WHISPER's private self-appraisal remains player-controlled, and external mechanical pressure effects require validated rules.
- Exact spend timing, inspiration-like resources, collection/expiration and non-cancelable major semantics require the same independent authorization/replay tests specified in SSRR-001 and WCP-001.

**Open owner decision:** choose a variant, or create a hybrid with clear rules. All three variants remain PROPOSALS; none are an instruction to modify Hask Meadow.
