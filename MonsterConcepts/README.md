# MonsterConcepts

Readable creature concept cards for Genesis Protocol. These are **archived drafts**, not validated encounter stat blocks. Existing values are preserved; missing rules are marked rather than invented. Nothing here changes campaign state.

## Shadowstalker Nexu

> “You never see the first one. You hear the second—and realize the first is behind you.”  
> — Authored dockside rumor, Level 1313

**Imperial black-kennel predator**  
**ID:** `creature_shadowstalker_nexu`  
**Large Beast · Very rare · Galactic Empire**

A lean, void-black nexu variant bred by clandestine Imperial kennels for silence, obedience, and terror operations. Retractable talons, split jaws, and whisker-spines that sense air pressure and sound let it stalk through vents and scaffolding in total darkness. Gene-edited from captured nexu stock and conditioned with shock collars; some escaped into megastructure undercities.

**Habitat:** Undercity, industrial zones, sewers.

### Recorded attributes

| STR | DEX | CON | INT | WIS | CHA |
|---|---|---|---|---|---|
| 18 | 20 | 16 | 12 | 16 | 12 |

### Recorded attacks

| Attack | Range | Damage | Conditions and effects |
|---|---|---|---|
| Silent Pounce | Melee | 2d8 + Dexterity Modifier | Requires `attacker_has_surprise == true`. Leaps from shadow with crushing momentum. |
| Rend | Melee | 2d6 + Strength Modifier | Split-jaw bite and raking claws. On hit, target takes another 1d4 damage at the start of its next turn. |

### Behavior and GM direction

- Avoids open light and separates the party.
- Targets isolated or loud prey first.
- Retreats after a hard hit and re-engages from another angle.
- Uses steam vents, flickering lights, narrow gantries, and blind corners.
- Escalates from single ambushes to coordinated pack tactics as it learns the party's rhythms.
- Authored motives: territory defense and hunger triggered by vibration patterns.

### Recorded Chaos relationships

| Relationship | Target | Authored purpose |
|---|---|---|
| `rel_engineered_by` | `galactic_empire` | Intimidation and deniable disappearances in occupied sectors |
| `rel_habitat` | `coruscant_1313` | Maintenance shafts and coolant ducts |

These target IDs and relationship types have not been validated here.

### Atomic pass needed

HP, defenses, speed, attack bonuses, action costs, damage types, and precise reach are missing. Rend needs explicit stacking and removal rules. Surprise needs a defined mechanical trigger. Darkness hunting has no numerical sensing range. No balance approval or mechanical conversion has been performed.

**Provenance:** `SW5e_Data_Hub/backend/creatures/shadowstalker_nexu.yml`. Its source field, “Imperial Security Bureau Black-Kennel Brief 17-C,” is in-world flavor, not verified external publication evidence.

---

## Vornskr

**The Force-hunting canine**  
**ID:** `creature_vornskr`  
**Medium Monstrosity · Pack predator · Native to Myrkr**

A Force-sensitive canine predator that tracks and ambushes Force users. Intelligent, coordinated, and relentless, it hunts in packs of three to six and tries to separate prey from allies. Its pack protects wounded members, shares kills, and establishes hunting territories.

**Habitat:** Forest, jungle, Myrkr, Force-rich areas.

### Recorded FFG-aligned attributes

| Brawn | Agility | Intellect | Cunning | Willpower | Presence |
|---|---|---|---|---|---|
| 5 | 7 | 2 | 6 | 4 | 3 |

| Wounds | Strain | Soak | Melee defense | Ranged defense |
|---|---|---|---|---|
| 30 | 12 | 4 | 2 | 1 |

These values have not been converted to a d20 stat block. Wounds are not silently treated as HP.

### Recorded attacks

All three use **Brawl (Brawn)**.

| Attack | Damage | Crit | Recorded effect |
|---|---|---|---|
| Force-Enhanced Bite | 7 | 3 | On hit, target makes a difficult Willpower check or cannot use Force powers until the end of its next turn. |
| Pack Strike | 6 | 4 | Two attacks as one action. Each successful hit reduces target movement speed by 5 ft until the end of its next turn. |
| Force Pounce | 9 | 3 | After moving at least 20 ft straight toward a Force-sensitive target, a bite hit knocks it prone and adds unspecified Force damage. |

### Recorded abilities

| Ability | Existing text summarized |
|---|---|
| Force Sense | Senses Force-sensitive creatures within 300 ft and prioritizes them. |
| Pack Tactics | Advantage on attacks if a non-incapacitated ally is within 5 ft of the target. |
| Force Resistance | Advantage on saves against Force powers; cannot be affected by mind-affecting Force abilities. |
| Enhanced Tracking | Survival check to follow a Force signature across great distances. |
| Pack Coordination | Another vornskr within 30 ft grants +1 to attacks and saves; three or more nearby increase the bonus to +2. |
| Force Disruption | A hit on a Force-sensitive creature gives it disadvantage on Force-related checks until the end of its next turn. |

### Behavior and tags

Coordinates attacks to surround and isolate Force users; becomes more aggressive around strong Force presence and avoids places where the Force is suppressed.

Recorded tags: `archetype: force_hunter`, `environment: forest`, `threat: high`, `size: medium`, `behavior: pack`, `combat: force_disruption`, `lore: myrkr`, `hunt: force_sensitive`.

### Atomic pass needed

The record mixes FFG-style characteristics, soak, wounds, and crit ratings with d20 advantage, saves, and movement in feet. Resolve that ruleset contract before use. Extra pounce damage, tracking difficulty, movement speed, attack resolution, and interaction/stacking limits need explicit definitions. Existing Force immunity and disruption mechanics remain unvalidated.

**Provenance:** `SW5e_Data_Hub/backend/creatures/vornskr.yml`. The file cites *Heir to the Empire* and FFG *Allies and Adversaries*; individual authored mechanics have not been checked against those publications.

---

## Original records

Both cards were transcribed from the archive at commit `eacb14d5be09cc393263189084f81abab1db513d`:

[SW5e_Data_Hub.zip](https://github.com/AustinFnFordham/Genesis-Protocol-Dev/blob/eacb14d5be09cc393263189084f81abab1db513d/_QUARANTINE/hub_root_debris/SW5e_Data_Hub.zip)

Related archived record: `SW5e_Data_Hub/backend/companions/party_companions/shadowstalker_nexu_alpha.yml`.

The Shadowstalker is a nexu variant; the Vornskr is the canine. Neither card authorizes replacing established campaign creatures.

## Proposed Forge passes — workshop only

Soul → Atomic → Chaos → Convergence → validated tags and Registry → maps and indexes → retrieval.

Assign stable IDs early. Each pass may return a record for repair; unresolved dependencies stay explicit. This is a workshop proposal, not an adopted change to Forge doctrine or implementation.
