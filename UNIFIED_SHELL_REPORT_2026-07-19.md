# ONE LIVING CAMPAIGN — Unified Shell & Campaign Isolation (2026-07-19)

Nothing was undone. The systems that existed beside one another now run as one continuous game flow.

## 1. Campaign isolation — one mounted world
`gm/campaigns/<id>/` now owns each campaign's runtime, chronicle, turn log — fully separate instances. The controller stack mounts **one** campaign at a time (`POST /api/v1/gm/mount`), unloading the previous cleanly; `GET /api/v1/gm/campaigns` lists them. Meridian Reach is **test data as a campaign definition**, not hardcoded world truth — nothing about Nona, Dax, or the sensor array lives in controller logic; it's all in that campaign's builder and runtime files.

**Shadows of Empire: Remnants is now a real GM campaign**, instantiated from forge gold: the CampaignState entity + all three AI-forged Reconciliators projected into character-sheet-runtime shape, opening at docking bay 9 on Vardos with Captain Reyes watching manifests and Yuel the dockhand broker. Its own hidden ledger (who wants the intel = unresolved thread, no reveal without a causal path).

**Isolation verified live:** ran a Shadows turn (Yuel: *"triple the usual for intel on the listening-post breach"* — the GM built on the CampaignState session summary), then remounted Meridian — separate chronicles confirmed, Meridian resumed at turn 3 with the punch and Nona history intact. No bleed in either direction. Hardcoded `aero` removed from the turn loop — everything reads `metadata.active_player`.

## 2. One shell, contextual views
Persistent nav in the engagement header: **CAMPAIGNS · ◈ LIVING TABLE · NARRATIVE · TACTICAL · SHIP · DATA**. Ship promoted to a center view. No view is a destination without a way back.

**Campaign Select is the front door** — the app boots to it. Cards show era, party, source, and whether a save exists (resumes) or first mount instantiates. NEW CAMPAIGN routes to the creator.

**Mode routing:** the controllers don't care which screen is visible — when a GM turn escalates to combat, the shell auto-switches to TACTICAL (1.6s after the narration lands) and flags the unresolved turn. When a conversation is open, wandering to another tab shows the amber guard: *"You are in an unresolved conversation on the Living Table — ▸ return."* Inspection is free; accidental abandonment isn't. Verified live: banner appears on TACTICAL, return link lands back in the conversation.

## 3. Contextual action panel (left panel, under the anchor)
Generated from the **mounted Character Sheet Runtime + current mode** — never a hardcoded universal list. Scene mode: Speak / Interrupt / Inspect / Move / Use Item / Custom. Combat mode: Attack / Move / Guard / Assist / Use Item / Interact / End Turn. Below: the character's actual **weapons with attack bonuses** (hover = damage), **powers with costs** (Battle Insight FREE, Burst FREE; FP 3/3 readout), **reactions** (Sentinel Balance, Lightsaber Deflect). Clicking prefills a declaration and routes to the Living Table — the same resolved runtime drives the controllers and the UI, so player and AI GM read identical truth. *"Attempt anything plausible."* stays permanent.

## 4. Recommended runtime flow — implemented
Load Campaign → instantiate/mount → Living Table frames the scene → declarations flow → hostile actions hit the Combat Master → TACTICAL opens only when escalation requires → Record Keeper commits → play resumes from the new state.

## Known refinements (honest list)
- **Anchor/runtime unification:** the left Operative anchor still reads the client zustand campaign; when Meridian is mounted it shows the Shadows character. Next stitch: anchor renders the mounted runtime's active player (Aero's portrait/HP/strain from his sheet).
- Ship view uses the existing gauges/stations component — the station-organized layout (Pilot/Nav/Comms/Turret/Engineering) from your reference is the next Ship pass, and it should generate from the loaded vessel data.
- Narrative (scripted Malice) view remains as legacy alongside the Living Table; eventually the Living Table's conversation beats *become* the Narrative view with portraits, and the tabs merge into contextual views of one runtime.
- Reaction-window quick-time UI still pending (server already recommends `brawl` escalations).

## QA summary
Build green · both campaigns mount/remount cleanly with preserved separate histories · Shadows GM turn in-world and violation-free · action panel reads live sheet data · unresolved-action guard and return path verified · active_player migration backfill for pre-isolation runtimes.
