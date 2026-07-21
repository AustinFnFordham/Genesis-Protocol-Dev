# THE LIVING GALAXY — Build Report (2026-07-12, session 3)

Five new systems, all building green. The butterfly effect is now executable code.

## 1. The World Phase Engine (`src/state/worldPhase.js`)
The universe takes its turn. Every **End Turn** (Diorama) and every **hyperspace jump** (Map) advances `campaign.world_phase` via RFC6902 and consults deterministic consequence tables (Article 8 — the qwen GM can later replace the tables; the output contract of patches + journal entries is identical):

- **The fuel-canister incubation chain** — exactly your spec: rolling a Despair in combat now sets `flags.canister_ignited` and journals *"the fire spreads beyond the grid. Someone lived here."* Then, invisibly: phase 1 → net chatter breadcrumb; phase 2 → someone buys your landing footage; **phase 3 → `nemesis_unknown_actor` spawns** with `grudge_origin: "The Guardian ignited the fuel canister…"`, tracking your URID; phase 5 → transponder breach breadcrumb; **phase 6 → THE REVEAL: Kaelen, the Ash-Blind**, stage `confrontation`, threat 5.
- **Faction influence drift** — contested map nodes bleed 1 point per phase toward the strongest holder; the borders you watch on the map literally breathe.
- **Obligation pressure** — a wanted character's obligation ticks up every phase.

## 2. The Nemesis Web (`NemesisWeb.jsx`, Command panel tab)
Grudge nodes tethered to your player node. Unrevealed nemeses render as **glitching UNKNOWN ACTOR shadow silhouettes** — flickering ring, animated dashed tether, dossier reading `grudge origin: [ENCRYPTED] — the Nemesis Engine knows. You don't. Yet.` Revealed ones show name, progression stage, threat level, and the grudge quote. Spawned nemeses **ride inside the save file** — the grudge survives reboots.

## 3. Dialogue → Combat escalation
Draw a weapon on Malice through the Slicer Override and the adjudicator flags `escalate` — narration lands, the journal logs *"Negotiations have ended. Initiative rolls,"* and 1.4s later the center panel **seamlessly swaps NARRATIVE → TACTICAL**. (Smashing the holocron deliberately does NOT escalate — she respects audacity.)

## 4. The Holographic Workbench (`Workbench.jsx`, second frosted overlay)
Anchor button `⬡ Holographic Workbench`: left, the cargo pool (Item + Modification gold entities); right, **hardpoint sockets** (primary weapon / armor / utility ×2 / mod slot) and the current loadout. **HTML5 drag-and-drop**: drop a mod chip on a socket → RFC6902 `/equipment/-` patch → the Anchor's encumbrance tracker reacts instantly (amber flash + setback warning past 5). Click any loadout item to strip it.

## 5. Starship Management (`ShipManagement.jsx` — the Ship tab unlocks)
Binds the Millennium Falcon Starship gold entity + heavy turbolaser hardpoint. Hull/shield gauges, **crew assignment** (select crew member → click station: helm/gunnery/shields/engineering — yes, you can put Darth Malice on gunnery), all patched into `campaign.ship` in the save for the AI GM to read during space combat.

## Persistence hardened (bug found & fixed in QA)
Created characters were memory-only — a reload showed "NO OPERATIVE ON RECORD." Now **created characters and spawned nemeses ride inside the save file** (`campaign.characters`), rehydrate into the O(1) registry on boot, and entity patches sync back to the persisted copy. Verified: fresh save embeds `character_rrawrkhal`; resume drops you back in with the full Anchor.

## Pipeline note
The mass factions platinum batch **ran to completion without a retry storm** (the Phase-2 fixes held): 130 files processed, 446 loop events, 1 reached platinum on pure LLM power, 19 quarantined. Verdict: qwen2.5-coder can't reliably author move-heavy migration patches; the winning pattern remains deterministic migration scripts (as proven on the slice) with the LLM reserved for narrative passes. Recommend: replicate `migrate_connections_slice.py` across the faction quarantine list.

## 60-second QA script (browser was rate-gated at session end; everything below is build-verified)
1. Reload `localhost:1420` → save resumes → TACTICAL → Roll Narrative Dice until **DESPAIR** (canister detonates; journal entry appears).
2. **End Turn** three times → watch the Journal breadcrumbs arrive → Nemesis tab: the **UNKNOWN ACTOR** glitch node is tethered to you. End Turn to phase 6 → **Kaelen reveals**.
3. Anchor → `⬡ Holographic Workbench` → drag *Enhanced Focusing Crystal* onto **mod slot** → encumbrance ticks up live.
4. Ship tab → Register Ship → select Sith Assassin → click **GUNNERY**.
5. Dialogue → type *"I draw my blaster and open fire"* → the panel snaps to the holotable.
Dev hooks if you want to drive from console: `window.__genesis.getState()` and `window.__runWorldPhase()`.
