# CC-005b: authenticated, viewer-safe projections · movement-projected odds · campaign-grant overlay

**Branch:** `dev/cc005-server-verify`, continuing from v0.5 (`67ff276`). Each step was committed separately.
The owner's decisions are recorded in `CC005B_DECISIONS.md` (D1–D5).

**Boundaries:** noncanonical sandbox. Nothing connects to the live campaign or the Oracle authority. Hask Meadow and `shared-0002` are untouched.

## 1. Campaign-grant overlay: Minor Telekinesis (D1)

**How the grant is applied**
- `campaign_overlay.js` reads the owner ruling file `campaigns/starwars_litrpg/creator/jedi_fundamentals.json` (2026-11-11, `approved_provisional`).
- `newState({campaign, overlays})` grants `minor_telekinesis` **only** when both hold:
  - the session's campaign is `starwars_litrpg`;
  - the rule's `granted_to` names the character.
- The grant records its rule, version, status, `granted_by` and source document.
- The shared sheet and `powers_known` are untouched.
- **The server worker loads overlays from the repository's own file.** A client-supplied overlay is ignored, and an unknown campaign is refused.

**The profile:** `status: campaign_ruling`. Main action, 0 FP, one visible **unattended** object of 10 lb or less within 30 ft. The limits are copied from the rule file.

**What it can do in combat in this slice** (the loose objects are dropped weapons):
- **Retrieve** Aero's own dropped weapon. It returns to his hand unlit.
- **Reposition** another creature's *dropped* weapon 30 ft away. Its owner then needs 30 ft of movement to recover it (instead of the usual 10).

This positional consequence is a **Genesis sandbox adaptation, pending owner review**.

**Refused:** held (attended) objects, so it can't disarm; creatures; anything beyond 30 ft. It never deals damage. No Force Pull or Push profile exists or is granted.

**UI:** a "Campaign overlay: starwars_litrpg (Jedi Fundamentals)" switch, a "Campaign ruling" card badge, and an object picker.

## 2. Ranged-in-melee disadvantage, opt-in (D4)

**Rule:** a ranged attack roll has disadvantage while a hostile within 5 ft can see the attacker and isn't incapacitated. The switch stays **off by default**.

**Exceptions (tested):**
- the hostile is down;
- the hostile is hidden;
- the hostile is incapacitated;
- the attacker is hidden.

Grappled or prone hostiles **still count**. Melee attacks are never affected. NPCs are bound by the same rule. Provenance, approval scope and exceptions are recorded in `catalog.json`.

## 3. Movement-projected odds

Each step's odds now use the distances the engine projects **after the earlier planned steps**. For example:
- close-then-strike shows a real hit chance;
- a planned withdrawal shows the blaster's long-range disadvantage.

## 4. Authenticated, viewer-specific projections (D3)

**Role tokens**
- `open` issues a **player token** and, **only for practice sessions**, a GM token for the sandbox debug client. A **bound** session never gives the client a GM token.
- Tokens are stored server-side only as SHA-256 hashes and never appear in journals.
- Every route checks its role:

| Code | Meaning |
|---|---|
| 401 | No token, or a forged one |
| 403 `FORBIDDEN_ROLE` | Right session, wrong role: a player committing an NPC turn or rolling GM dice |

**Server-run GM** (`/atomic/gm_step`): the server commits the NPC's policy plan and rolls GM dice itself. It stops only when the player is needed:
- player dice;
- a player reaction decision;
- the player's turn;
- the end of the fight.

A whole bound duel has been played with **only the player token**.

**Projections** (`/atomic/view`, computed server-side by the engine worker)
- **Player projection** (`engine.playerProjection`):
  - Aero's own sheet in full.
  - For others: a condition word instead of HP; no AC, budgets or reaction counts.
  - Damage log text is rewritten to drop enemy HP.
  - Receipts lose any undiscovered enemy AC.
  - Hidden actors and their rolls are omitted.
  - Pending NPC dice are reported as "waiting on GM", without revealing their purpose or target.
- **Discovered AC is a learned bound** from Aero's side's own resolved attacks:
  - a hit at total T means AC ≤ T;
  - a clean miss at T means AC ≥ T+1;
  - natural 1s and 20s teach nothing.

  It is proven to always contain the true AC over 200 seeded duels, including parry and riposte cases. *A bug that read Aero's own Parry as Ilsa's was found and fixed by that test.*
- **Debug view** (full state): only with a GM token **on a practice session**. Bound sessions refuse it (`DEBUG_NOT_AUTHORIZED`).

**UI "Player view (server projection)"**
- Enemy plates, the Roll Theater's "vs AC" and the odds come **only from the server's projection**: a condition word, AC as learned bounds, and hit chances as a **range** across those bounds (with the unknown part assumed 10–20, and labelled as such).
- Incoming odds and the simulation are hidden, because they need the enemy's numbers.
- Tokens persist per viewer, so a reload reconnects.

## 5. Tests

**New**
- `test_cc005b.cjs`: 16 checks covering the overlay, the ranged-in-melee rule and its exceptions, movement-projected odds, AC-bound soundness over 200 duels, and projection leak checks.
- `test_cc005b_server.cjs`: 16 checks covering 401, 403, no token leaks, the player denied NPC commits and GM rolls, a full bound duel with only the player token, the bound debug view refused, no enemy HP or AC in the player projection, the practice debug view, hidden predator omission, overlay applied server-side, unknown campaign refused, and client overlays ignored.
- `test_playtest_ui.cjs`: 54 checks, now including the overlay and the player view.

**Updated** (owner D1): two older data tests now also accept `status: campaign_ruling` (only for files under `campaigns/starwars_litrpg/creator/`).

**Full regression:** run before each commit (see the commit messages).

## 6. Remaining gaps before any live connection

- **The client still bundles the fixtures.** The page ships NPC stat blocks (`catalog.json`, `scenarios.json`) and replays the journal locally, so a determined player could read them in the browser. The *server* projection is correct, but true concealment needs a **thin player client** that renders only `/atomic/view` and drives turns with `gm_step`, `roll` and `decide`. The server routes for that exist and are tested; the page does not use them exclusively yet.
- **Sandbox tokens are not identity.** They are bearer secrets kept in the browser. A live integration must bind sessions to the gateway's authenticated actor and provider (GPT's lane, owner approval).
- **Encounter ids are not authenticated.** Bound encounter ids are still free text; the campaign authority must issue them.
- **Telekinesis repositioning:** the "30 ft to recover" consequence needs owner review. Other unattended scene objects (crates, panels) need scene object data.

## 7. Next

GEP-002 preparation is in `GEP002_PREP.md`.
