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
| M3 WHISPER context | COMPLETE | `tb4/m3-whisper` | `03e9f71` | **Yes**: `litrpg/campaign-scaffold` @ `0eb060f`, switch `whisper_context` on, main Datapad v13 |
| M4 Algorithm A | COMPLETE (pure evaluator) | `tb4/m4-evidence` | `a4fc246` | Code only, not wired to play (no in-force authority yet) |
| M5 Algorithm B | COMPLETE (pure evaluator) | `tb4/m5-memory` | `34ccb6c` | Code only, not wired to play |
| M6 Algorithm C | COMPLETE (pure evaluator) | `tb4/m6-causal` | `a5dac51` | Code only, not wired to play |
| M7 Integration / UAT | COMPLETE | `tb4/m7-integration`, `tb4/m7-fixes` | `fe36923`, `ee155c2` | **Yes** (code + fixes): `litrpg/campaign-scaffold` @ `67249c9`, main Datapad v14 |

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

## M3 — WHISPER start-of-turn context (switch `whisper_context`)
Files: `campaigns/starwars_litrpg/ui/src/whisper.js` (new, removable), hooks in `composer.js` (`WHon()`/`WHapply()`),
`build_datapad.py`, chip pressed style in `src/head.html`, `development/whisper/whisper.py` (pure boundaries),
`development/gm_provider/gateway.py` (strips `whisper` from the public `player_declaration`, adds a `gm_only`
`whisper_context` event), runbook + GM guide text. Tests: `development/whisper/test_whisper_context.py`,
`ui/test_whisper_ui.cjs`, `test_gateway.Interchange.test_whisper_context_never_enters_the_public_ledger`. `suites=50 failed=0`.
Behaviour: optional felt emotion (chips + own words), what Aero shows (open / controlled / masked + text), motive, private
reflection. Blank = no `whisper` key at all (TB4-10). A context alone cannot be submitted as a turn. What-if prompts are
static; reading them writes nothing (TB4-12); "Use as my reflection" is the only way one becomes text. Observers see only
the expression (TB4-11/18). No morality, alignment or diagnosis is derived (TB4-26/28). No numbers.
Live path caveat: the live worker (runbook, not the gateway) must strip `whisper` itself when writing `player_declaration`;
the runbook says so. If it slips, the only reader of the public ledger is still the owner, but it is a defect to report.
Owner decision still open (contract §9.3): whether any WHISPER field ever becomes a canonical character-state event.
Currently: GM-only record of what the player stated, nothing canonical about Aero's psychology.

## M4 — Algorithm A: evidence-grounded knowledge (pure)
Files: `development/whisper/evidence.py`, `development/whisper/fixtures/cmp001_ten_missing_crates.json` (CMP-001),
`development/whisper/test_evidence.py`. Envelopes are derived views over accepted events (ledger `knowledge_type`,
`visibility`, `known_to`), never stored. Visibility is enforced first: `gm_only` only for the GM (and NPCs who were part
of it, GM-side), `pc_private` only for the player/PC, NPC knowledge only through exposure (`known_to`/authorship).
Claims stay claims (TB4-16), absent observers know nothing (TB4-17), private context never reaches NPCs (TB4-18),
unknown entities refused (TB4-19), retractions marked per listener. Diagnostic: `python3 development/whisper/evidence.py
development/whisper/fixtures/cmp001_ten_missing_crates.json npc:dockworker_7` (or `player`, `gm`).
Not done (needs owner/architecture decision): feeding these envelopes into NPC prompts or the live GM context.

## M5 — Algorithm B: episodic memory and appraisal candidates (pure)
Files: `development/whisper/appraisal.py`, `fixtures/tb4_moral_001.json` (TB4-MORAL-001), `test_appraisal.py`.
`memories(events, actor)` (built on Algorithm A), `moral()`, `psychological()`, `social()`, `appraise()`.
Covers TB4-13, -14, -15, -17, -26, -27, -28. Findings are labels with citations, never scores; `canonical: False`.
Not done (owner/architecture decision): presenting PC candidates in the Datapad after a turn (accept/edit/reject/defer)
and committing an accepted transition; NPC appraisals through `npc_review.py`. Justification labels
(`defense_of_self/other`, `none_established`) are GM rulings expected on `attack_resolved` details — a convention to adopt.

## M6 — Algorithm C: typed causal proposals (pure)
Files: `development/causal/causal.py`, `fixtures/causal_fixture.json`, `test_causal.py`.
Relation types fixture-local (`observes, communicates, believes, protects, threatens, depends_on, trusts, contains`) —
not added to the global Registry ontology (owner gate CIS-001 §11). Domains/transitions are a small allow-list.
Rules with status `candidate` never fire; the fixture marks two as `candidate_enabled` for testing only.
Covers TB4-19, -20, -21, -22 and CIS-001 §4/§5 cases. Proposals carry `commits: False`; applying one means handing it to
the existing gateway as a GM proposal (not implemented: needs owner ratification of rules and domain owners).

## M7 — integration, recovery, UAT readiness
- TB4-RECOVERY-001 / TB4-22: `test_gateway.Interchange.test_tb4_recovery_001_turn_builder_and_whisper_survive_a_crash_and_handoff`
  (scripted providers: crash before commit, reroute to another provider, same dice bytes, one accepted declaration,
  TB4 words unchanged, WHISPER only GM-side). Scripted provider identities are recorded as mocks (existing behaviour).
- Preview diagnostics page (`development/preview/out/diagnostics.html`, linked from the banner) shows Algorithms A/B/C on
  their fixtures. `test_preview.cjs` checks it.
- Running the suite on the live branch found two real issues, fixed in `tb4/m7-fixes`: What-if buttons under the 44px
  touch target; switch-off tests assumed a fixture without switches.
- TB4-25 cost: no code path in the suite calls a model or paid API (scripted providers only; not network-instrumented).
  New suites take 16.0 s of the 174.1 s full run (`development/.qa/check_results.json`).
- Final: `suites=53 failed=0` on both `integration/tb4-whisper-v01` and `litrpg/campaign-scaffold`.
- Protected path: integration branch `hask_meadow_r2` tree = baseline `96ca84d…` (unchanged). Live branch differs only
  by the owner switch file `features.json`; ledger, hidden ledger and dice untouched (revision 1125).

## UAT for the owner (iPad)
1. Main Datapad (live) or the test Datapad: in combat, check the Custom box under each category, the Suggested chips and
   the style buttons; submit a turn with your own words and see them in the GM's result.
2. Bonus action → Taunt: pick a target, Intimidation or Deception, type your exact words.
3. WHISPER panel: pick feelings, what Aero shows, why. Open What-if and close it (nothing should change).
4. Codespaces: create a codespace on `integration/tb4-whisper-v01`, open port 8080, try the preview and its diagnostics link.
Rate fun / agency / clarity 1–5 per item; note anything confusing with the turn and commit shown in the banner.

## Owner decisions 2026-11-17 (evening) — see contract Addendum A
| # | Decision | Status |
|---|---|---|
| 1 | Private episodic history; long-term changes only on explicit player confirmation | M8 COMPLETE, real E2E verified |
| 2 | Post-turn WHISPER proposals with Accept / Edit / Reject / Defer / custom | M8 COMPLETE, real E2E verified |
| 3 | Actor-specific NPC knowledge view in the GM's NPC context, behind a switch | M9 COMPLETE (gateway test; real-worker NPC use not yet observed) |
| 4 | Causal families 1–4 for bounded testing, proposals only, gateway for any commit | M10 COMPLETE (pure; not wired to play) |
Live gate: switches for M8–M10 stay **off** in Hask Meadow until their end-to-end tests (real worker round trip on the
test campaign) are verified.

## M8 — WHISPER post-turn review + private history (switch `whisper_review`)
`development/whisper/post_turn.py`; `gateway.whisper("review"|"respond")` (between turns, shared side-commit helper with owner
records); `whisper_review`/`whisper_response` are player-visible ledger events tagged `pc_private` (NPC evidence views exclude
them); export publishes `state.whisper {pending, history}`; Datapad review card (Accept / Use my edit / Reject / Later / your
own words); `gmctl whisper-review|whisper-respond`; test bridge handles `kind: whisper_response` rows. Long-term candidates
appear only after 2+ confirmed experiences of the same theme. Tests: `test_post_turn.py`, `test_whisper_review.cjs`,
gateway `test_whisper_post_turn_review_end_to_end`.
**Real end-to-end on the test campaign (2026-11-18 UTC):** turn `m8e2e-1794970143` (Aero falls back, ends turn, private
fear/motive) → cloud worker: near hound's opportunity attack (crit, 10), Wick's turn, each hound's turn, round 2 → review
`evt_0049` published → answer row `w-e2e-1794971900` (edit) → worker recorded `evt_0050` → test Datapad shows it in history,
pending cleared, no motive text in feed/journal. The rows were written by Claude in the Datapad's exact shape (the phone tap
itself was not exercised).
Bugs found and fixed by this round trip: (1) the gateway dropped `confirmed_warnings` before the dice resolver, so any
turn with a confirmed risk could not roll (`test_confirmed_warning_dice.py`); (2) `hp_change` shape was undocumented —
the GM wrote `amount`, the Datapad reads `delta`; now documented and enforced (`HP_CHANGE_SHAPE`). The test campaign's
`evt_0026` keeps its accepted `amount` field (history is not rewritten), so the test Datapad still shows Aero at 11 HP
and the review missed the damage; (3) the bridge gave no row patch for a refused WHISPER answer.

## M9 — NPC knowledge in the GM context (switch `npc_knowledge`)
`gateway.context` → `npc_knowledge.by_npc[npc]` (Algorithm A, visibility first, claims typed, retractions marked, never
WHISPER, never GM-only facts the NPC was not part of). GM proposal events may now carry `known_to` and `knowledge_type`
(validated); the test worker's GM already used `known_to` in the round trip above. Live path: `evidence.py <run dir> npc:<id>`.
Test: gateway `test_npc_knowledge_view_is_actor_scoped`. Not yet observed: a real worker run with the switch on.

## M10 — causal families (pure)
`development/causal/causal.py` FAMILIES/APPROVED_STATUSES; proposals carry family, triggering event, evidence,
prerequisites, affected entities, owning domain and "possible, not inevitable". Only `taunted` is an approved status.

## Live status (Hask Meadow, `litrpg/campaign-scaffold` @ `1792078`)
Code for M8–M10 and all fixes is live; switches `whisper_review` and `npc_knowledge` are **off** there (owner gate). Main
Datapad v15. Turn them on in `campaigns/starwars_litrpg/runs/hask_meadow_r2/features.json` when you're satisfied.

## Open owner decisions
- WHISPER fields: which become canonical events vs private projections (contract §9.3) — M3 keeps them private, noncanonical.
- Long-term preference learning — default off (§9.4).
- Light/dark mechanics, AMD weights (§9.5–9.6) — not implemented; no numbers invented.

## Next action
1. Owner: try the test Datapad (review card is live there) and decide whether to switch `whisper_review` /
   `npc_knowledge` on for Hask Meadow.
2. Next agent: run one real test-worker turn with `npc_knowledge` on and check the GM used `npc_knowledge` for Wick/hounds.
3. Then: wire causal proposals (families 1–2 first) into the GM context as suggestions, behind a switch.

## M11 — Intent-first builder (ChatGPT Work, 2026-11-18; verification in progress)
Base verified remotely: `0fc859b0de13f7d33f0e18690d08dd70834b2f2e`; isolated branch `dev/m11-intent-first-work`.
M0–M10 preserved. No live merge, Artifact publication, worker trigger, or campaign writes authorized by this task.

Implementation:
- `ui/src/tb4.js`: ≤4 deduplicated contextual editable plan recommendations, using only published public options,
  the shared validator's availability, visible threats, equipment prerequisites and explicitly chosen style.
  A defensive action may include a published retreat/cover route only if the shared validator accepts the combination.
  Picking a card edits the existing builder; it never executes a turn. Target/trigger selection remains explicit.
- `ui/src/composer.js`: default plan-first combat builder, collapsed full mechanics catalog (including supporting
  activities and custom categories), persistent disclosure state, editable custom intent, selected target/trigger
  editors outside the catalog. Scene sequencer and reaction prompts retain their existing flows; Taunt and WHISPER remain.
  All budget badges use null-aware capacities, explicit remaining/planned quantities and respect zero.
- `ui/turn_contract.js`: prevent alternative-generation recursion while validating an alternative. Zero-action
  overspending returns ACTION_CONFLICT rather than overflowing into the UI's check-unavailable fallback; no costs or
  legality rules changed. Existing two-argument callers retain their API.
- Historical HP: inspected `staging/mobile-test` public `evt_0026`: target aero, `amount:-10`, hp_before 11, hp_after 1.
  Recommended and implemented a **read-only projection compatibility shim** (`ui/hp_compat.py`): signed integer
  legacy amount only when delta is absent; explicit delta (including zero) wins; no sign guessed from narration.
  Exporter and WHISPER appraisal share it. New writes still require delta through HP_CHANGE_SHAPE.
  No accepted event, dice, or prior review is rewritten. Existing missed reviews are not automatically backfilled.
- Preview: pinned PyYAML dependency + devcontainer install step, M11 banner, `development/preview/IPAD_PREVIEW.md`.
  Existing port 8080 forwarding remains private. No second application or campaign store introduced.

Local evidence:
- Full suite: 58 suites, 41 pass (38 Python; RNG audits; build equality). 17 Chromium-dependent suites cannot launch:
  expected bundled browser absent; installed system Chromium rejects Unix socket creation with EPERM under this
  executor. These are **not browser passes**. The full runner report is in ignored `development/.qa/check_results.json`.
- M11 pure tests pass; actual preview JS functional DOM tests pass (choose/edit/combine, disclosure persistence,
  mock submission literal intent, zero-budget subscription refresh). DOM is not a substitute for visual Safari testing.
- HP compatibility tests pass: signed legacy damage, modern delta precedence, immutable inputs, actual public exporter,
  and WHISPER pain appraisal citing the original event.
- Real local HTTP requests return 200 for `/`, `/diagnostics.html`, `/build.json`; embedded state is fixture-only.
- `.github/workflows/m11-verification.yml` prepares full Chromium regression on standard free public-repo runners,
  read-only repository permissions, no deployment/secrets/artifact storage. Remote execution not yet claimed.

Preview blocker: no Codespaces controls in connector; cloud browser signed out at GitHub login. Cannot verify account
allowance or create a private forwarded URL. No Codespace, billing change, paid resource, or working iPad link claimed.

Recovery: fetch this branch, read this section and `development/preview/IPAD_PREVIEW.md`, install preview requirements,
run `bash development/run_all_checks.sh` with Playwright Chromium available. Run the additional functional DOM test with
jsdom on NODE_PATH. Continue remote regression, then integration-only merge if verified; create/resume the personal
2-core Codespace only within available allowance. Keep 8080 private. Do not touch the live branch or test/live ledgers.
