# Source comparison and candidate resolution — 2026-11-05

Structured candidates: `candidates/CANDIDATES_2026-11-05.yml` (noncanonical, nothing promoted, no gate run, no runtime or source file changed). Extends `REGISTRY_DEPENDENCY_REPORT.md`.

## What the sources actually are
- **OmniBrew SW5e data** (`E:\StarWars\sw5e-data`): species Chiss (PHB) and Miraluka (EC), traits, manual rules text. **No Trooper or Bounty Hunter class exists there** (ten classes only; Bounty Hunter is a PHB *background*). So Trooper and Bounty Hunter are Genesis-original classes, not SW5e rules.
- **Genesis game data** (`game_data.zip` and `forge_v3/backend`): the only source of both classes.
- **Sourcebook PDFs and FFG/EDGE books were not found** under `E:\StarWars`. The `StarWarsFFG-2.0.3` folder is Foundry system code with no career or specialization data. Tell me where the books are and I will look at the Style options there.

## Results
| Dependency | Class | Finding |
|---|---|---|
| Chiss | Source-backed candidate | SW5e PHB and Forge agree on INT+2/CHA+1 and 30 ft. Id mapping confirmed; two key-shape defects fixed in memory pass the schema. Varon's Shyriiwook has no recorded origin. |
| Miraluka | Source-backed candidate | SW5e (EC) and Forge agree on WIS+2/CHA+1 and Miralukese. SW5e Force Sight and Force-Sensitive (denounce / curse / bestow curse) are negated by the approved severance, recorded as an override, not an edit. |
| Bounty Hunter | Source-backed candidate | A **schema-valid** copy exists in `game_data.zip` (has `level_progression`). The forge copy differs only in shape. Saves STR+WIS, hit die 1d10. `hunter_quarry` has no definition file anywhere I looked. |
| Trooper | Unresolved dependency | Same structure in both copies. **No Style option is defined in any file.** AP has spenders (Suppressive Fire 2 AP and Heavy Weapons Specialist 1 AP as feats, Heavy Gunner 3 AP at 11) but no starting pool or recovery. |
| Adaptive Countermovement | Explicit campaign adaptation | Cross-checked against SW5e reaction and opportunity-attack rules (`the-order-of-combat.md`, pp. 90–91 per its source tag; `making-an-attack.md`; `actions-in-combat.md`): no conflict. |
| Sensory band, Rassira's weapons | Explicit adaptation / unresolved | No source records. Needs item definitions and balance review. |

## Gameplay fallback applied
Ammunition Points: Varon takes no AP spender, so nothing at Level 1 depends on a pool. Continue normally; I did not invent one.

## Defaults recorded, not applied (per your instruction)
Rassira: source ASI, source saves (STR+WIS), source Strain base 12 pending Jade's confirmation of the DEX choices. Languages with origins: Miraluka(lese) (species), Basic, Dathomiri (Dathomir witch-raised upbringing), Huttese (background or history). `commit_ready: false` stays until the mechanics and equipment validate.

## Decisions I actually need
1. **Adaptive Countermovement registration:** approve registering it as a campaign-local option, as the only Trooper Style, since the other three are not in any file. Does the 10 ft come out of his normal movement? (The text reads as no.)
2. **Bounty Hunter era adaptation:** the class needs an era-compatibility ruling that I'm keeping in the GM lane to avoid spoiling the setting. I'll propose it there; I only need your go-ahead to use the Genesis Bounty Hunter class under an explicit adaptation.
3. **Location of the sourcebooks** if you want the missing Trooper Styles and `hunter_quarry` text sought in them.

Everything else waits on Jade or on the Custodian lane.
