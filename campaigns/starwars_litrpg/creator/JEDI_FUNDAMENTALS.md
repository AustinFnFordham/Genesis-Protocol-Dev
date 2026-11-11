# Jedi Fundamentals: Minor Telekinesis — campaign rule, IN FORCE (provisional)

Owner ruling 2026-11-11. **Scope: the Star Wars LitRPG campaign only (`campaigns/starwars_litrpg`, Hask Meadow run 2 onward). Not a universal Genesis rule and not a baseline Force-training mechanic** (see "Path to baseline" below). Machine form: `creator/jedi_fundamentals.json`. Test: `ui/test_campaign_features.py`.

## What it is
A trained Jedi's basic, non-offensive telekinesis: the everyday handling of a small object at a distance. It is a **campaign feature granted by an explicit recorded exception**, not a Force power. It does not count against `powers_known`, is not on any power list, and grants no part of an unlearned power.

## Who has it (explicit grants only)
Being Force-sensitive, a Force user or a member of a Force tradition does **not** qualify anyone. A character has this feature only when both hold:
1. The record establishes completed formal Jedi training: the rank of Jedi Knight or above on a validated sheet, or an owner ruling that names an equivalent.
2. The character is listed in `jedi_fundamentals.json` → `granted_to`, with the evidence cited.

| Character | Evidence | Granted |
|---|---|---|
| Aero (Aeleron Do'ordo) | sheet `identity.current_rank: Newly Knighted Jedi`; `council_ruling: knighthood legitimate` | owner ruling 2026-11-11 |

Other appropriately trained Jedi get the same feature with the same limits, by the same test, when they enter play: player characters by an added grant entry; NPCs by a GM ledger event that cites the training the record establishes for them (never assumed from a title alone). Padawans, initiates, untrained sensitives and non-Jedi traditions are not covered; each needs its own ruling.

## Limits (owner-set)
- **Target:** one object at a time; visible to the character; unattended (not held, worn or carried by a creature, not fixed in place); weighing no more than 10 lb.
- **Range:** the object must be within 30 ft to be affected, and stays within 30 ft while moved. Retrieval range is the same 30 ft.
- **Effect:** gently lift, reposition, retrieve or manipulate it (bring it to hand, set it down, turn it, press or slide something that a light touch would move).
- **Cost:** no Force Points.
- **Outside combat:** straightforward uses need no roll. A roll is called only when there is meaningful uncertainty (see open item 1).
- **In combat:** it takes the character's action.
- **Never:** damage; moving, shoving, tripping or restraining a creature; disarming; taking anything a creature holds, wears or carries; intercepting a projectile or a thrown object in flight; substituting for any unlearned combat Force power.
- **Consequences stay real:** it is seen and heard like any other act; a moved light source moves its light; a fragile thing set down badly can break; time passes; the world can act on it.

## Reconciliation (checked 2026-11-11 before enabling)
- **Character sheet** (`api_bridge/gm/aero_character_runtime.yml`): unchanged. It is the shared runtime for other Genesis campaigns, so a campaign-scoped exception is not written into it. `forcecasting.powers_known: 2` (Battle Insight, Burst) stays correct: this is a feature, not a third power. The sheet's rank and council ruling are the evidence for the grant.
- **Power registry:** no promoted Force Push, Force Pull or telekinesis record exists. The only records are unpromoted drafts in `registry/candidate_builds/cand_powers_541b498235e0dfc6/draft/`: `power_force_pull` (level 0, action, 30 ft, pulls a **creature or object** 10 ft: forced movement) and `power_force_push` (level 1, 2 Force Points, pushes 10 ft with a Strength save or prone). This rule overlaps Force Pull only for small unattended objects and is deliberately narrower: no creatures, no forced movement, no save, no combat effect. Having it is never evidence of knowing either power. The drafts are not promoted or altered by this ruling.
- **Source authority** (charter): tier 3, a provisional ruling: campaign-scoped, labeled, logged (`hidden/UAT_LOG.md` PR-002; `creator/DESIGN_DECISIONS.md` 2026-11-11). Charter rule 2 ("capability comes from the sheet; no convenient powers") is unchanged; this is its one recorded exception, and capability now comes from the sheet **plus** the grants in `jedi_fundamentals.json`.
- **Turn validator** (`ui/turn_contract.js`): no change needed. It never judges powers; it flags a free-text power as `UNLISTED_POWER` and defers to the GM. The GM check (runbook §2.4, §3) now reads the sheet and this rule. The Datapad lists the feature under Features for a granted character (`ui/export_state.py` overlay), and the GM may publish it as a turn-context option.

## How the GM applies it
1. Check the grant (the character is in `granted_to`). No grant: `UNKNOWN_POWER`, as before.
2. Check every limit against committed events: visible, unattended, 10 lb or less, within 30 ft. A use outside a limit is refused for that reason, not shrunk to fit and not upgraded.
3. Outside combat, no roll unless open item 1 applies. In combat, it is the action.
4. Commit what moved as `equipment_change` / `environment_change` like any other handling of an object, citing this rule in `details.rule: "jedi_fundamentals"`.

## Open items for the owner (defaults in use until ruled)
1. **The roll when one is needed.** Default: d20 + the character's forcecasting ability modifier + proficiency bonus (Aero: +4), against a hidden DC set before rolling. Not owner-set.
2. **Hands.** Default: no free hand required (the ruling names none).
3. **Holding an object aloft over time.** Default: possible while the character does nothing else demanding; in combat it takes the action each round. No concentration rule is invented.

## Path to baseline
The owner wants this evaluated for the baseline Force-training mechanics. That needs, at least: a registry record for the feature with provenance; a definition of "appropriately trained" per tradition and rank; a decision on how it relates to a promoted Force Pull; and tests in the rules engine. Until then it stays a campaign rule with named grants.
