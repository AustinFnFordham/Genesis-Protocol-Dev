# CC-006: mobile-first combat composer (thin player client)

- **Branch:** `dev/cc005-server-verify`, continuing from CC-005c (`16b4750`).
- **Scope:** an interface redesign of `/play.html`. No mechanics changed.
- **What the browser does:** it renders the server's player projection and submits player intent, nothing more.
- **What's unchanged:** combat maths, NPC policy, dice, and the `/atomic/*` request and response contracts.
- **Not touched:** Hask Meadow, `shared-0002`, Oracle.

## Milestones

| Milestone | Commit | What |
|---|---|---|
| A: single-screen shell | `71cecef` | See [Milestone A](#milestone-a-single-screen-shell) |
| B: category rail | `be9f44a` | See [Milestone B](#milestone-b-category-rail) |
| C: drawers and plan states | `f80fa90` | See [Milestone C](#milestone-c-drawers-and-plan-states) |
| D: three-zone polish | this commit | See [Milestone D](#milestone-d-three-zone-polish) |

### Milestone A: single-screen shell

- **One viewport.** The app fills `100dvh` with safe-area insets and the document never scrolls; regions scroll internally.
- **Always on screen:**
  - the **checkpoint row** (Roll, reaction or GM status), which takes priority over browsing;
  - the **turn dock**, showing the server's legality verdict, the action economy left after the plan, FP, Clear and Commit.
- **Layout by width:**

  | Width | Layout |
  |---|---|
  | Under 700 px | Actions / Scene / Turn tabs |
  | 700–1099 px | Actions and Scene share a pane; the Turn column stays visible |
  | 1100 px and up | Three zones |

- **Race fixes:**
  - Roll and decision taps now mark the turn busy.
  - `busy` stays set until the new view has rendered, so a stale prompt can no longer be tapped. This was the root cause of an intermittent `test_play_ui` timeout.
  - The roll prompt no longer shows "vs AC null".

### Milestone B: category rail

- **The categories now come from the server.** `player_api` adds `card.category`, derived from each profile's cost, trigger and maneuver type, never its display name: maneuver, attack, main, secondary, bonus, reaction, movement, object, free, plus "Off-sheet".
- **The rail** shows a usable/total count per category and one category at a time, and remembers the choice. It is a horizontal strip on phones and vertical on wide screens.
- **Disabled actions open a drawer** explaining why they can't be used (reason, cost, rules, source, status). Tapping one adds nothing to the plan.

### Milestone C: drawers and plan states

- **Info button (44 px) on every card.** Details open in a bottom sheet on phones and a side panel on wide screens.
- **Plan steps show the server's state:** legal, illegal, conditional, or checking.
- **Step drawer:** tapping a step opens its preflight breakdown:
  - verdict and reasons;
  - the target's distance when the step happens;
  - cost;
  - odds range;
  - sources of advantage or disadvantage;
  - damage;
  - whether it depends on the feint.
- **Compound costs** are flagged inline.
- **Character drawer** (header button): your own sheet, the economy left, campaign grants, and the combat history you have seen.
- **Commit** reads "Checking…" and stays disabled until the newest preflight answers. The existing sequence guard is kept.

### Milestone D: three-zone polish

- The newest turn is highlighted and older beats dim.
- A victory or defeat banner offers "New fight".
- On phones, the Scene tab shows a dot when there is narration you haven't read.
- The layout test asserts how many zones sit side by side for each width: 3 at 1100 px and up, 2 at 700–1099 px, 1 below.

## Tests

`run_all_checks.sh`: **71 suites, 0 failed** at every milestone.

**`test_play_ui.cjs`: 28 checks (was 20).** It keeps every CC-005c leak and security check and adds:
- categories are server-assigned;
- the rail lists only categories that actually exist;
- reactions are not merged into other categories;
- disabled and available cards can both be inspected;
- the character drawer shows no enemy numbers;
- a **delayed, out-of-order preflight answer never replaces the newer plan's verdict** (network-level delay injection);
- Commit is disabled while validation is unsettled;
- the step drawer works;
- Clear cancels the plan.

**`test_play_layout.cjs`: new, 131 checks.**
- **Viewports:**
  - iPhone SE 320×568;
  - iPhone 13 in portrait and landscape;
  - iPad Pro 11″ and 12.9″ in both orientations;
  - iPad split view 507×1024;
  - desktop 1280×720 and 1920×1080;
  - a short keyboard-up viewport.
- **At each one:** a real turn is played with the player token only, and the test checks:
  - no document scroll in either direction;
  - no overlapping or clipped regions;
  - every control is at least 44 px;
  - Commit is on screen;
  - the server's legality verdict is shown;
  - the Roll button is on screen without scrolling;
  - the roll prompt has no null or undefined text;
  - the expected number of zones;
  - no page errors.

**Screenshots:** in `screens/cc006/`. The full set is regenerated with `SHOT_DIR=… node test_play_layout.cjs`.

## Remaining defects and gaps

- **Enemy status while composing:** on phones and in iPad portrait, it is visible only on the Scene tab. A compact enemy strip on the Actions pane is the obvious next fix.
- **Two-layout prototype not done yet:** the owner's GEP-002 direction asks for two phone/tablet layouts compared by task metrics. Only one exists (tabs plus a persistent dock).
- **No drag reordering yet:** reordering uses ▲/▼ buttons (accessible), and nothing else.
- **No live reconnect feedback:** reconnecting keeps the plan and never rerolls (covered by the reload-mid-roll test). There is no automatic retry or backoff yet; the header chip shows "offline — retry".
- **Real devices not tested:** Playwright emulates iOS sizes, touch and device scale only. Safari's dynamic toolbar and the software keyboard still need a check on an actual iPhone and iPad.
- **Unchanged from before:** sandbox tokens are not identity, encounter ids are not authenticated, and the Telekinesis repositioning rule is still awaiting owner review.

## Next

1. A compact enemy strip in the Actions pane on narrow screens.
2. The second layout prototype, compared against the first on taps-to-commit and on information visible while composing.
3. Optional drag reordering.
4. The event-driven Combat Theater from the GEP-002 direction.
