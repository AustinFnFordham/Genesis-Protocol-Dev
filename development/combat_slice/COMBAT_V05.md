# Combat v0.5 (CC-005): server-verified turns (sandbox, noncanonical)

**Branch:** `dev/cc005-server-verify`, built on `dev/cc004-combat-v04` (`2455ab7`). The design spec commit `4749ae0` (GEP-001, docs only) was cherry-picked in.

**Not touched:** Oracle, `shared-0002`, live Hask Meadow, any ledger, any character sheet, any campaign roll. GEP-001 was read in full before any change. It is treated as design direction, not as approval of any mechanic.

## 1. GEP-001 vs existing contracts: contradictions (reported; no rule changed)

| # | GEP-001 says | Existing source says | Status in this sandbox |
|---|---|---|---|
| C1 | Telekinesis/Minor Telekinesis is **not** on Aero's runtime sheet; reconcile the provenance of the older campaign-scoped exception before any grant (§1) | CC-002 and the Capability contract cite the campaign-scoped ruling | **RESOLVED (owner, 2026-11-22): a provenance question, not a contradiction.** The authority is `campaigns/starwars_litrpg/creator/JEDI_FUNDAMENTALS.md` and `jedi_fundamentals.json`. It is a campaign feature for `starwars_litrpg` (Hask Meadow run 2 onward), deliberately not on the shared sheet and not a learned power. It is applied through a campaign-grant overlay (CC-005b). See `CC005B_DECISIONS.md`. |
| C2 | Approved WHISPER loss-of-control may cause involuntary PC acts (§4); this needs an explicit versioned exception | `development/gm_provider/GM_GUIDE.md` rule 1: "Never act for the player character…". CC-002 §3: "The GM never chooses undeclared PC responses". Capability contract §5: "preserve the player's declared choice of whether and how to respond". | **Direct contradiction** with three live rules. Nothing is implemented. Adopting it needs a versioned GM_GUIDE/rules exception that says who may execute it, for which campaign, enabled before play (GEP §11.9). |
| C3 | Don't show secret enemy AC or DC in roll labels or odds; use visible/known state (§2, §5) | CC-002 §7 agrees ("never hidden DCs/enemy AC"). **But** your CC-003 sandbox brief asked for enemy HP, modifiers and dice to stay visible, and the v0.3/v0.4 Roll Theater and odds panel show enemy AC. | **Conflict between your sandbox brief and GEP/CC-002.** Unchanged for now (sandbox). **Proposal:** show enemy AC/DC only with "Full mechanics (debug)" on; otherwise "vs Ilsa's defense", and compute odds only from what Aero knows. Needs your call. |
| C4 | "typically **4 or 5** authored response choices plus custom" (§7) | GM_GUIDE: "3–5 `dialogue` lines in distinct approaches". GEP also redefines **Approach** (relational tone), separate from **Method** (procedure); GM_GUIDE uses "approaches" loosely for tone. | Minor. Combat is unaffected. Reconcile in GEP-004: make the minimum 4, and rename the GM_GUIDE field or document the two terms. |
| C5 | Echani unarmed strike has no false empty-hand requirement (§1) | CC-002 agrees for kick, knee and elbow. Grapple needs a free hand per the sheet. | **Consistent.** Verified in the engine: `unarmed_strike` has no hand requirement, and `grapple` requires `offhand_free`. |
| C6 | Deflect redirect goes to a player-selected visible creature within 30 ft (§11.8) | Sheet: "redirect … at one visible creature within 30 ft". My v0.4 always sent it back at the shooter. | **v0.4 was wrong. Fixed in v0.5** (below). |
| C7 | SA-001 Secondary is a distinct prospective budget; don't present it as live (§1) | SA-001 §9: "Do not merge, enable, or present Secondary Action as live" until approved | **Consistent.** The sandbox keeps it behind the `secondary_action` switch and labels Secondary cards as proposals. |

## 2. What v0.5 implements

**Server-side reconstruction**
- `atomic_engine_worker.cjs` runs the **same engine**, in Node, as a long-lived child of the preview server.
- It rebuilds each session **from the server's own journal only**: commits, accepted dice and decisions. The client's state is never an input.
- From that reconstruction the server decides:
  - whose turn it is (`NOT_YOUR_TURN`), with no commits while a turn is unfinished (`TURN_PENDING`) and none after the end (`ENCOUNTER_OVER`);
  - whether a plan is legal **in the server's state** (`ILLEGAL_PLAN`). For example, a strike that is only in reach because the page edited its own distance is refused;
  - the NPC's plan, which must equal the GM policy computed on the server (`GM_PLAN_MISMATCH`);
  - which dice the engine needs next. Anything else is refused (`NOT_NEEDED`), so you can't roll ahead to peek;
  - who rolls them. The player cannot roll the NPC's dice (`ROLLER_MISMATCH`);
  - which player decision is pending (`DECISION_NOT_PENDING`, `NOT_PLAYER_DECISION`, `BAD_CHOICE`).

**Turn verification** (`/atomic/complete`)
- After each turn, the server compares its reconstruction with the client's state hash.
- On a mismatch it journals a `verify ok:false` record and replies `STATE_MISMATCH`. The client then fetches `/atomic/state` and **adopts the server's result**.
- "✓ server-verified" appears on a turn **only** after the server's own reconstruction matched. A client-supplied hash proves nothing by itself: it is only compared.

**Anti-session-shopping** (`mode: "bound"`)
- A bound session belongs to one campaign-issued `encounter_id`.
- Opening that encounter again returns **the same session** (same seed, same history).
- Abandoning it is a recorded **forfeit**. It never yields a fresh seed, and the closed encounter accepts nothing.
- `practice` sessions still get fresh seeds, but are labelled `eligible_for_campaign_authority: false`.

**Roll identity:** every accepted die records turn, actor, plan hash, step index, purpose, target, kind and rules version (`cc-sandbox-0.5`), plus seq and roll id. The seed never appears in client-readable data.

**Deflect, corrected to the sheet**
- After a full stop, the **player** chooses one visible creature within 30 ft, or lets the bolt die on the blade.
- Aero himself, hidden creatures and anyone beyond 30 ft are never offered.
- This choice is a journaled player decision.

**Provenance:** the relay droid's HP 7 / AC 13 is labelled a playtest-001 fixture, pending approval. The `ranged_in_melee_disadvantage` switch records "common d20 convention; NOT on Aero's sheet; pending owner".

**UI**
- A redirect target dialog (PLAYER — AERO · decision).
- Per-turn verification badges in the Roll Theater (✓ server-verified / ✗ result rejected — server's result applied / practice · not verified).
- Server refusals are shown as alerts.
- Reconnecting compares against the server's reconstruction.
- Everything from v0.4 is kept.

## 3. Tests

| Suite | Checks | New in v0.5 |
|---|---|---|
| `test_engine.cjs` | 27 | — |
| `test_cc003.cjs` | 21 | — |
| `test_cc004.cjs` | 20 | Deflect player-chosen target and decline; candidates limited to 30 ft and visible; dice-request identity |
| `test_atomic_service.py` | 23 | (unchanged; service without the engine) |
| `test_atomic_flow.cjs` | 13 | Now runs with server verification on |
| **`test_cc005_server.cjs`** | **23** | Honest duel with every turn verified · server state = client state · **forged HP detected, server result adopted** · forged hash refused · illegal plan from an edited state · server decides the turn · forged NPC plan · player rolling NPC dice · unneeded dice · peek-ahead · decision not pending · roll identity in the journal · no seed leak · bound session resumes · forfeit stays closed · fresh seed never issued for a bound encounter · encounter id required · practice labelled ineligible · Deflect redirect picked by the player and verified |
| `test_playtest_ui.cjs` | 48 | Server refuses a plan built on an edited page; verified badge shown |

## 4. Remaining gaps before live campaign authority

- **No identity or authentication on the sandbox service.** Anyone with a session id can act for it. A live wiring must bind sessions to the gateway's authenticated actor and provider identity.
- **The sandbox journal is not the live ledger.** Mapping it to the gateway's combat, roll and storage APIs is GPT's integration lane, and needs your approval.
- **Bound encounter ids are free-form.** In campaign play they must be issued by the campaign authority; here any string works.
- **Replay cost:** the server re-runs the whole journal on each request. That's fine for these short fights; long encounters need snapshotting.
- **Full state is visible:** `/atomic/state` returns the full sandbox state. A campaign must project it per viewer, and C3 is still open.
- **Still open from v0.4:** distance projection in predictions, grapple escape, Battle Insight concentration, per-rest counters, multi-actor fights.

## 5. Next smallest milestone

**CC-005b: the visibility policy (C3) plus movement-projected odds.**
- Default view: no hidden enemy AC or DC in the Roll Theater or odds. Odds come only from Aero-known state.
- Distance after planned moves is projected.
- "Full mechanics" stays as an explicit debug toggle.
- This is small, closes a GEP acceptance item that conflicts with the current UI, and doesn't touch WHISPER numbers.
- After that, GEP-002 (nonlethal control and WHISPER evidence hooks) can start in the sandbox once you set the boundaries in GEP §11.1–2.
