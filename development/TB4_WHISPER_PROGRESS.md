# TB4 + WHISPER — progress and handoff (authoritative)

Contract: `Contracts/TB4_WHISPER_001_v0.1.md` (v0.1.0) and `development/TB4_WHISPER_CLAUDE_IMPLEMENTATION_PROMPT_v0.1.md`,
both cherry-picked from `docs/tb4-whisper-contract-v0.1-20261117` @ `e85857f`.
Integration branch: `integration/tb4-whisper-v01`. Milestone branches: `tb4/m<N>-<slug>` from the latest integration HEAD.

## Recovery procedure (any agent)
1. `git fetch origin && git checkout integration/tb4-whisper-v01 && git pull --ff-only`
2. Read this file top to bottom. Verify HEAD matches "Verified integration HEAD" below (or a later progress commit).
3. `bash development/run_all_checks.sh` (needs python3, node, playwright chromium) — expect `failed=0`.
4. Continue the first milestone not marked COMPLETE. Never restart or reimplement completed milestones.

## Owner rulings for this initiative (2026-11-17, in conversation with Claude)
1. **Going live.** A finished milestone moves into the live app (`litrpg/campaign-scaffold` + main Datapad) when it can be
   integrated non-destructively. New behaviour goes in **behind an on/off switch, as separate code that is easy to remove**.
   If it cannot be integrated safely, it stays on this branch. This supersedes the contract's "never merge to live" for
   finished, switched work; it does not authorize rewriting Hask Meadow history.
2. **Taunt** (bonus action, owner-ratified mechanics, resolves contract §9 items 1–2 for the test grant):
   costs 1 bonus action; player's exact words/gesture kept; **contested check: Aero's Charisma (Intimidation or Deception)
   vs the target's Wisdom (Insight)**; on success the target has **disadvantage on attack rolls against anyone other than
   the taunter until the start of the taunter's next turn**. No forced attack, no mind control; the target still acts from
   its own motives. Still opt-in per campaign (switch), off in live until the owner switches it on.
3. **Preview.** Both: a Codespaces devcontainer (private port) and the private test Datapad artifact.

## Baseline (M0)
- Chosen base: `litrpg/campaign-scaffold` @ `eacb14d` — the newest complete code (it contains `integration/mobile-test-build`
  `b2d59bb` plus the owner-adopted dice settings and encounter tracker for live Hask Meadow, 2026-11-15).
  The contract was written against `staging/mobile-test`; that branch is the test campaign's data branch, not newer code,
  so it was **not** merged (its test-campaign data must not enter code branches). Only the two contract docs were taken.
- Contract conflict noted: contract §9.7 says the 11-15 encounter ruling is not authorized live. The owner adopted it
  for Hask Meadow on 2026-11-15 (`eacb14d`, runbook §3e). Live keeps the owner ruling; this initiative does not change it.
- Protected path digest: `git rev-parse HEAD:campaigns/starwars_litrpg/runs/hask_meadow_r2` = `96ca84df78599b2053a24ef21a99ab5f0bbfc387`
  at baseline. Every milestone must leave it unchanged (check with the same command).
- Remote gateway (context only, no writes): `shared-1` rev 40, `evt_0043`, pending `shared-0002`, `storage_recovery_required=true`.

## Gap inventory (current vs contract), recorded at M0
| Area | Already in code | Missing for TB4 |
|---|---|---|
| Ordered steps, branches, pending steps, Continue, reaction prompts | `turn_contract.js` contract 3, composer sequencer | — (preserve) |
| Primary / bonus / movement / object / reaction / speech pickers | composer Build mode, palette (Say/Do/Go/Handle/Gear) | per-category **Custom** box in every category (only one global Custom today) |
| Custom free text kept literally | `free` steps, `unmapped`, Custom editor | literal text for every category through declaration → action row |
| Secondary Activity | none | grouping/annotation only, never a slot |
| Suggestion selector | GM-published options listed as-is | pure deterministic ranker, ≤4 + Custom, `known_legal/needs_adjudication/blocked` |
| Taunt | none | opt-in grant + bonus-action cost + contested-check request shape |
| End turn, per-actor budgets, tracker, NPC cooperation | contract 3 + encounter controller (live) | — (preserve) |
| WHISPER start-of-turn context | none | felt/expression/motive/reflection, `unspecified` ≠ calm, private scope |
| What-if thoughts | none | collapsed, zero canonical effect |
| A evidence envelopes | ledger visibility (public/gm_only), `npc_review.py` citations | typed envelopes + actor-scoped retrieval (pure) |
| B episodic memory / appraisal | none (AMD docs only) | event-linked memory + candidate appraisals (pure) |
| C typed causal resolution | CIS-001 proposal only | bounded typed rule evaluator returning proposals (pure) |

## Milestones
| # | Status | Branch / commits | Integration merge | Live? |
|---|---|---|---|---|
| M0 Baseline, fixtures, preview | COMPLETE | `tb4/m0-baseline` @ `37a102b` | `2598d59` | Not needed (dev tooling only) |
| M1 Turn Builder 4 UI | COMPLETE | `tb4/m1-turn-builder` @ `78a5b80` | `1f743e5` | **Yes**: `litrpg/campaign-scaffold` @ `a88df71`, switch `tb4_builder` on, main Datapad v11 |
| M2 Action economy, Taunt | COMPLETE | `tb4/m2-action-economy` | `f6879a7` | **Yes**: `litrpg/campaign-scaffold` @ `c58abff`, switch `tb4_taunt` on, main Datapad v12 |
| M3 WHISPER context | NOT STARTED | | | |
| M4 Algorithm A | NOT STARTED | | | |
| M5 Algorithm B | NOT STARTED | | | |
| M6 Algorithm C | NOT STARTED | | | |
| M7 Integration / UAT | NOT STARTED | | | |

## M0 — Baseline, preview, fixtures
Files: `.devcontainer/devcontainer.json`, `development/preview/{build_preview.py,serve_preview.py,features.json,test_preview.cjs}`,
`development/run_all_checks.sh` (+ preview suite), `.gitignore` (preview output), this file, contract docs.
Fixture: noncanonical `development/mobile_test/fixture_campaign` ("Sim Deck: Drill Seven", `mobile-test-1`; public state
only is embedded in the preview). Further contract fixtures (CMP-001, TB4-WICK-001, TB4-MORAL-001, TB4-RECOVERY-001) are
added with the milestones that test them.
Tests: `bash development/run_all_checks.sh` → `suites=45 failed=0` (44 existing + preview).

### Preview — how to open it
- **Codespaces (iPad):** GitHub → repo → branch `integration/tb4-whisper-v01` → Code → Codespaces → Create. The container
  builds and serves the preview on port 8080 (private) automatically; open the Ports tab → 8080 → open in browser.
  If it is not running: `python3 -B development/preview/serve_preview.py --host 0.0.0.0 --port 8080`.
  Not verified by Claude inside a real Codespace (no access); the same command was verified locally (HTTP 200, banner).
- **Local:** `python3 -B development/preview/serve_preview.py` → http://127.0.0.1:8080/
- **Test Datapad (claude.ai):** https://claude.ai/artifact/CnRh7iAy75JNZePbPhUeqb — real GM worker on the noncanonical
  `mobile-test-1` campaign (scheduled task `trig_01J5tRZ3t2WehBNzx3Z3Z2Wj`). Republished per milestone when the UI changes.
- What the preview is: the real Datapad page + fixture public state + in-browser storage. No GM, dice or network;
  submissions are stored and marked "preview only". Reset with the banner's "Reset preview state".

## M1 — Turn Builder 4 (switch `tb4_builder`)
Files: `campaigns/starwars_litrpg/ui/src/tb4.js` (new, removable), hooks in `src/composer.js` (all guarded by `TB4on()`),
`build_datapad.py` (inlines tb4.js before composer.js), `export_state.py` (`FEATURE_SWITCHES`; reads `<run>/features.json`
`switches`), `test_tb4.cjs` (22 checks), runbook note in `.claude/skills/litrpg-process-turn/SKILL.md`.
What it does (combat Build mode): a Custom box in Primary, Bonus, Secondary activity, Movement, Object and Reaction;
speech keeps "Write my own line". Literal words go to `declaration.tb4.custom` and `unmapped`. Secondary activity is never
a slot. Up to four deterministic suggestions per category from published options only, marked fits the rules / GM checks /
not now, ranked by an optional explicit play style (no learning). Scene mode already had a Custom step editor; unchanged.
To remove: delete `src/tb4.js`, its line in `build_datapad.py`, and the `TB4on()` hooks; or set the switch false.
Tests: `bash development/run_all_checks.sh` → `suites=46 failed=0`.
Live: switch file `campaigns/starwars_litrpg/runs/hask_meadow_r2/features.json` (new file only; ledger untouched,
revision still 1125). Main Datapad republished (v11); live `view/state` got `features` (v89). Test Datapad v2 + switch.
Known gap: the test campaign's worker runs code from `staging/mobile-test` (`b2d59bb`), whose export does not publish
switches yet; merge integration into `staging/mobile-test` before the next real test-worker round trip.

## M2 — Taunt (switch `tb4_taunt`) and action-economy guards
Files: `campaigns/starwars_litrpg/ui/tb4_rules.py` (new, removable: grant + `resolve_taunt`), call in `export_state.build`,
Taunt fields in `src/tb4.js`, runbook + `development/gm_provider/GM_GUIDE.md` resolution text,
tests `ui/test_taunt_rules.py`, `ui/test_tb4_taunt.cjs`.
Mechanics: exactly the owner ruling above. Grant appears only in combat with a visible hostile; ties go to the target;
the effect never compels. Without the switch Taunt is `UNKNOWN_OPTION` (TB4-04) and insults stay free speech (TB4-05).
Already covered by existing suites (unchanged): scene→combat transitions, interrupted/continuing turns, conditional
sequences, reaction prompts (`test_scene_sequencing.py`, `test_sequencer.py`, `test_datapad_sequencer_ui.cjs`), NPC
cooperation objects (`test_action_economy.py`), per-actor budgets (`development/encounter/*`).
Tests: `suites=48 failed=0`.
Live: switch added to the run's `features.json`; live `view/state` v90 carries the Taunt option and switches (the
published turn context was only appended to, GM options untouched). Ledger untouched (revision 1125).
Test env: `staging/mobile-test` now runs integration code (`a1aef18`), switches on; its gateway publishes them on the
next commit (the test Datapad state was patched to match meanwhile, v4).

## Open owner decisions
- WHISPER fields: which become canonical events vs private projections (contract §9.3) — M3 keeps them private, noncanonical.
- Long-term preference learning — default off (§9.4).
- Light/dark mechanics, AMD weights (§9.5–9.6) — not implemented; no numbers invented.

## Next action
Start M3 (WHISPER start-of-turn context, switch `whisper_context`) on `tb4/m3-whisper` from the integration HEAD.
