# Character authority: discrepancy report (2026-11-05)

Sources compared: the owner's local runtimes (`api_bridge/gm/characters/{aero,varon,rassira}/runtime.yml`), the repo copy of Aero's runtime, the registry (golden slice and candidate drafts), and the campaign presentation (the card shown in play and the UI). The hidden ledgers in those folders were not opened. No character data was changed.

## Aero (Echani Sentinel, Jedi background, L1)
- Local runtime and repo copy match (same length and key fields; not byte-diffed). Echani and Sentinel exist in the golden-slice registry.
- Sheet fact missing from the play card: his languages are Galactic Basic, Echani, and Sith.
- Stale flags in the file (`campaign_phase: design`, `narration_started: false`): harmless, left as is.
- Several features are declared adopted or provisional by the sheet itself (Force Connection, Sentinel Balance, Deflect, Burst/Battle Insight overrides). They are used as written.
- Varon's file labels him "Aero Taron". His surname is Do'ordo; Taron is his master. Probably a legacy label.

## Varon Narik (Chiss Trooper, Soldier background, Private, L1)
- Strongest file of the three: 27-point buy, full derived numbers, rich Soul section.
- It cites urids (`species_chiss` and three Chiss features) that are not in the repo registry; Chiss is only a candidate draft that does not yet pass its schema. Trooper is not validated either.
- Adaptive Countermovement is an adopted fourth Trooper Style, not a source option. Trooper Ammunition Points and starting equipment are undefined in the sources.

## Rassira "Rissa" Sythrael Nox (L1, status: provisional candidate draft, not canonized)
- The file says Miraluka by species, Dathomirian witch-raised by culture, Bounty Hunter class, Scoundrel background. It explicitly says she is not Togruta or Human.
- Her Force connection is severed: no Force Points, powers or Nightsister magick, and her Force Sight is replaced by a cybernetic sensory band. Her dormant lightwhips are not active.
- This differs from "Dathomirian Nightsister" as the brief describes her. The file says Nightsister training is tradition, not species or class.
- The file says her build must not be canonized without owner approval or authoritative rules. Miraluka and Bounty Hunter are not in the repo registry as validated entries.

## Togruta companion
- No runtime or sheet exists in the repo or in the local characters folder (aero, varon, rassira, npcs only).
- The registry has only candidate species drafts `togruta` and `togruta_nightsister`, and a candidate `background_entertainer`. Nothing ties these to a specific character. No facts were invented.

## Rulings requested (only those that affect gameplay or canon)
1. Rassira: is the file correct (Miraluka, Force severed, Bounty Hunter), or should she be a Force-using Nightsister? Approve the build as written, or tell me what to change.
2. Varon: adopt Adaptive Countermovement as his Trooper Style?
3. Togruta: please provide her original sheet, or say we build her through play.
4. Registry: Chiss, Miraluka, Trooper and Bounty Hunter need validated entries before the app can mount Varon and Rassira in strict mode.
