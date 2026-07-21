# UNIFY THE TRUTH BENEATH — Anchor, Narrative, Ship (2026-07-19)

Nothing removed. Narrative, Living Table, Tactical, and Ship remain distinct, first-class lenses. What changed is beneath them: **one truth path feeds them all.**

## 1. Anchor/runtime unification (the truth path)
```
Mounted Campaign Runtime → metadata.active_player → Character Sheet Runtime
        → Operative Anchor · Contextual Actions · Narrative portrait · (Tactical token, Ship crew — next)
```
- New store slice `gmRuntime` (`refreshGmRuntime()`) — the player-visible mounted runtime, refreshed on mount, on app boot, and after every GM turn commit.
- **When a campaign is mounted, the client save is never consulted.** The anchor renders identity, HP, strain, Force points, AC, ability scores, and conditions straight from the mounted sheet. The legacy client-save anchor survives only when nothing is mounted.
- Missing active player ⇒ explicit `⚠ ANCHOR UNRESOLVED — No active player is available in the mounted runtime` — never stale data, never a character from another campaign.
- ActionPanel now reads the identical `gmRuntime → active_player` path (its private fetch removed).

## 2. Narrative preserved — and made live
The Narrative view keeps everything that makes it distinctive: the cinematic feed, the alpha-masked portrait column with aura, the mood display, structured choice cards, the Slicer Override input, interruption-by-typing. **When a campaign is mounted, the four-controller GM drives it**: beats arrive as cinematic lines with speaker + per-beat mood (GM contract extended with `mood: calm|amused|guarded|angry|warm|tense`), the portrait column focuses whichever NPC is speaking (disposition shown beneath), suggested actions render as choice cards labeled *"attempt anything plausible"*, mechanics arrive as dice-verified SYSTEM lines, and combat escalation auto-routes to Tactical with the unresolved guard set to **the Narrative view**. The scripted Malice scene remains intact when nothing is mounted.

## 3. Ship view — station-based, data-driven
`ShipStations.jsx` renders **only** from `gmRuntime.ship` (vessel runtime added to both campaign builders + nondestructive migration backfills existing saves):
- **Meridian's Republic shuttle:** Pilot / Communications / Engineering — no turret, no weapons, because the vessel exposes none.
- **Shadows' YT-2400 "The Reconciliator":** Pilot (Voss) / Navigation (Ren) / Dorsal Turret (unmanned) / Engineering (Zoran) + dorsal laser cannon.
- Hull/strain gauges, shield arcs, system status strip; actions disabled with a visible reason when the linked system is down; unmanned stations flagged; required proficiencies shown.
- **Clicks submit declarations only** — prefill routes into the shared four-controller pipeline. The screen mutates nothing. Placeholder status is explicit: `ship_view_status: placeholder_layout · missing_data: [crew_station_rules, defensive_arc_values]`. No reference-image values copied as rules.

## 4. Regression (verified)
- Campaign isolation holds: mount swap Meridian ↔ Shadows returns the correct vessel, correct active player (`aero` vs `char_smuggler_pilot_aran_voss`), separate chronicles.
- **Dax punch provenance preserved:** `evt_1784506624_1` with dice `roll_1784506604_1` still in the Meridian chronicle.
- Build green (4.0s). Narrative view not removed — expanded.

## Acceptance status
anchor: all criteria ✅ (mounted-runtime source, cross-campaign leakage impossible by construction, explicit fallback).
narrative: all criteria ✅ (first-class, portraits/mood kept, live beats, interruptions, custom actions, shared runtime).
ship: all criteria ✅ structurally (data-driven stations, declarations only, shell nav + guard intact) — deeper station rules (proficiency gating vs assigned player, action economy) intentionally listed as missing_data.
regression: ✅ (isolation, both histories, provenance, no anchor leakage, narrative preserved).

## Next candidates
- Tactical token + Ship crew resolution through the same active_player path (the last two arrows of the truth diagram).
- Scene-state → recommended-view hints (Living Table suggests Narrative when a significant conversation begins) without forced switching.
- Reaction-window quick-time prompt; Combat Master driving the Diorama grid directly.
