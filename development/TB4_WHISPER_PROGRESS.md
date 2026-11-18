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
| M0 Baseline, fixtures, preview | COMPLETE (see below) | `tb4/m0-baseline` | see log | Not needed (dev tooling only) |
| M1 Turn Builder 4 UI | NOT STARTED | | | |
| M2 Action economy, Taunt | NOT STARTED | | | |
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

## Open owner decisions
- WHISPER fields: which become canonical events vs private projections (contract §9.3) — M3 keeps them private, noncanonical.
- Long-term preference learning — default off (§9.4).
- Light/dark mechanics, AMD weights (§9.5–9.6) — not implemented; no numbers invented.

## Next action
Start M1 on `tb4/m1-turn-builder` from the integration HEAD.
