# Provider interchange: release candidate, HOLD

Branch `dev/provider-interchange`. Base: canonical recovery candidate `1acf2a0`
(`rc/canonical-dice-recovery-f241ea6`) merged with the live head `d84a52c`
(`litrpg/campaign-scaffold`, 2026-11-13). Campaign records under
`campaigns/starwars_litrpg/runs/` are byte-identical to the live head. Nothing here is merged to
production, deployed, published to the live Datapad, sent to its worker, or applied to Hask Meadow.

The product is one persistent Genesis campaign with interchangeable GM providers. Claude, GPT and
Gemini are each usable for a turn, a session or ongoing play; switching keeps continuity and any
provider can be returned to. Claude → GPT → Gemini is an acceptance test, not the architecture.

## 1. What this candidate contains

| Area | Files | State |
| --- | --- | --- |
| Adjudication repair, executable | `ui/turn_contract.js` (`cost: "none"`, `by`), `ui/test_action_economy.py`, `ui/fixtures/handoff_round9.json`, rebuilt `ui/genesis_datapad.html` | Implemented, tested |
| Adjudication repair, GM guidance | `creator/ACTION_ECONOMY_RULING.md`, runbook §3d, `TURN_CONTRACT.md` §2, `gm_provider/GM_GUIDE.md` | Scoped provisional ruling; owner may amend |
| NPC re-evaluation guard | `gm_provider/npc_review.py`, `test_npc_review.py`, enforced by the gateway on every tables move | Implemented, tested. Structural: proves bookkeeping, not judgment |
| Recovery + experimental resolution | `1acf2a0` unchanged, reconciled with the live head (two UI merge conflicts resolved, page rebuilt) | All inherited suites pass; one inherited defect fixed (`projections.py`, missing `visibility` key crashed `test_roster.py`) |
| Shared provider boundary | `gm_provider/gateway.py`, `store.py`, `runner.py` | Implemented, tested with scripted providers and one real provider |
| Provider adapters | `gm_provider/providers.py`: Anthropic, OpenAI, Google (model API), agent session, scripted | Wire formats tested against a local fake; **no live GPT or Gemini call was possible** |
| Player API + worker | `gm_provider/service.py`, operator CLI `gm_provider/gmctl.py` | Implemented, tested over real local HTTP |
| Connection contract | `development/GEMINI_CONNECTION_CONTRACT.md` | Verified against the implemented service only; nothing is hosted |
| Verification | `development/run_all_checks.sh`, `prepare_browser_fixtures.py`, `verification/provider_interchange/` | 39 of 39 suites pass |

Not supplied: `Genesis_Gemini_Link_Continuity_Audit_2026-11-13.md` was not attached to the session,
is not in the repository on any branch, and is not in the project documents. Its decisions could not
be read or verified. Everything here was derived from the source contracts and code. See gate G0.

## 2. Consequence Engine boundaries (unchanged)

| Subsystem | Who does it in a turn | Enforced by |
| --- | --- | --- |
| Atomic (legality, resources, mechanical outcomes, committed truth) | Gateway only: `turn_contract.js`, the dice resolver, `batch.py` | Providers have no write path. Dice, tables, batch and publication are gateway calls |
| Soul (identity, portrayal, narration, dialogue) | The GM provider | Narration and context lints; no player-character events without a declared step |
| Chaos (causal interactions and consequences) | The GM provider proposes; nothing commits without validation | Events must cite accepted rolls; NPC evaluations must cite what changed; `policy.assess_causal` remains the only gate for narrative-axis effects and still commits nothing by itself |
| SID, AMD | Untouched. Q15/Q16 stay provisional design metadata; `moral_evaluation` validation is inherited | `ledger.validate_event` |
| Knowledge / visibility | Gateway | `brief.player_leaks`, context lint, private-table check, player API has no GM endpoint |
| Authority, scheduling, ownership | Ledger batch, lease, routing | One in-flight action per campaign; one lease; one operation record per action |

No missing equation was invented. No simulator was rewritten. No second campaign database exists:
the ledger in git remains the only canonical record. The store holds what the Datapad database
holds today (action rows, the lease, published public pages) plus the routing choice.

## 3. The shared boundary

The smallest boundary the code justifies is **one stateless function per provider**:
`step(context) -> move`. The gateway does everything else.

```
player client ──HTTP──> service.py ──> Gateway ──> turn_contract.js   (preflight)
                                         │──────> brief.py           (GM context, private)
GM provider <── context ─────────────────│──────> roll.py / engine   (dice, receipts)
            ─── move ───────────────────>│──────> batch.py           (one ordered batch)
                                         └──────> export_state        (pages first, snapshot last)
```

Moves: `review` (send back, before anything mechanical) or `tables` → zero or more `rolls` →
`commit`. Each call receives what was already accepted for the action, so any provider can continue
an action another started. Each provider therefore:

- loads the latest authoritative context and the GM-private information it is permitted (`context`);
- does its own interpretation, NPC portrayal and consequence proposals (`tables`, `commit`);
- requests authoritative mechanical resolution (`rolls`) and submits changes through the shared
  validators and commit machinery (`commit`);
- preserves campaign identity, revision/head, pending decisions, ordered steps and committed results
  (stale input is refused; step order, declared-step citations and pending steps are checked);
- can be used repeatedly and switched away from and back to (routing is per action and per campaign);
- reports unsupported capabilities or missing connections explicitly (`/v1/providers`, `blocked`);
- is never silently substituted (`NOT_ROUTED_HERE`; the worker blocks rather than falls back).

Validators applied to every commit: reserved kinds (`player_declaration`, `owner_ruling`,
`ruling_void`, narration, scene, context are gateway- or owner-authored), `ACTS_FOR_PLAYER`,
`STEP_ORDER`, `UNKNOWN_ROLL`, `ROLL_UNACCOUNTED`, `PRIVATE_LEAK`, `CONTEXT_LINT`, `NARRATION_LINT`,
`BAD_CONTEXT`, then `ledger.validate_event` on every event inside `batch.apply`.

## 4. Switching, and what happens to an in-flight turn

Operation identity is the action id. Each action has one operation record
(`hidden/provider_ops/<sha256(action_id)>.json`, a private receipt journal beside the existing dice
and batch receipts): the accepted tables, the accepted rolls, the committed batch, and which
providers ran.

| State of the action | Who may act | What a different provider can do |
| --- | --- | --- |
| `submitted` | Only the provider it is routed to | Nothing, until the player or operator reroutes it |
| `processing`, lease live | Only the run holding the lease | Refused `PROVIDER_BUSY`. Reroute is refused too |
| `processing`, lease expired or released, nothing accepted | The routed provider (a new run) | After an explicit reroute: interpret from scratch. No mechanical state existed |
| `processing`, tables fixed and/or rolls accepted | The routed provider | After an explicit reroute: continue. Tables cannot be replaced (`TABLES_FIXED`); a roll for the same step/actor/kind returns the accepted result even under a new key; a review is refused (`TOO_LATE_FOR_REVIEW`) |
| ledger batch accepted, interrupted | Any routed run | The exact accepted bytes are finished. Nothing is authored |
| `resolved`, publication pending | Any provider's run | Publication only: pages, then snapshot. Nothing is authored |
| `committed`, `needs_revision`, `failed` | Nobody | The next declaration may go to any provider |

A second provider can never independently resolve the same pending declaration: it cannot claim
without routing, cannot reroute while the lease is live, and inherits the operation record when it
does take over. Stale state is refused at submit (`STALE`), at context, and by `batch.apply`
(expected head and revision). Duplicate submissions return the existing row; a reused id with
different content is refused (`ACTION_ID_REUSED`).

## 5. Dice modes and narrative outcomes

Unchanged from the inspected policy (`development/experimental_resolution/policy.py`, README):
Regular raw; Heroic `11 + floor((raw-1)/2)`; Legendary `16 + floor((raw-1)/4)`; player-controlled
single-d20 checks, attacks and saves only; original 20 is the only critical; original 1 auto-misses
only in Regular; narrative d6 on a separate domain-seeded stream; private task/margin/DC stay
private; `public_resolution` is the only public form. The gateway uses the experimental engine
only when the campaign copy carries the explicit non-canonical marker. Without it, non-default
settings are refused at submit (`UNSUPPORTED_SETTINGS`): never emulated, never silently enabled.
Hask Meadow carries no marker and none was added. Settings are part of the immutable action and
are written into the `player_declaration` event.

## 6. Provider capability and setup matrix

| Provider id | Transport | Needs | Executed here | Verified |
| --- | --- | --- | --- | --- |
| `claude-session` | Agent session driving `gmctl.py` (the transport the live Datapad worker already uses) | A Claude session with repo access | **Yes, actual**: two turns on an isolated copy | Real model, real gateway, real dice and ledger |
| `claude` | Anthropic Messages API | `ANTHROPIC_API_KEY`, `GENESIS_CLAUDE_MODEL` | No: no key in this environment | Request/response shape against a local fake only |
| `gpt` | OpenAI Chat Completions API (JSON mode) | `OPENAI_API_KEY`, `GENESIS_GPT_MODEL` | No: no key | Shape against a local fake only |
| `gemini` | Google Generative Language API `generateContent` (JSON response) | `GEMINI_API_KEY`, `GENESIS_GEMINI_MODEL` | No: no key | Shape against a local fake only |
| scripted | In-process test double | Nothing | Yes | Mock; proves the boundary, not a model |

Optional: `GENESIS_<P>_BASE_URL` (for a proxy or regional endpoint), `GENESIS_MAX_OUTPUT_TOKENS`
(Claude). Model ids have no default on purpose: the operator names the model; the code never guesses
or falls back. No billing was enabled and no key was created.

## 7. Operator guide (staging)

```sh
# 1. An isolated copy (never a source campaign) and a store
python3 - <<'PY'
import sys; sys.path.insert(0, "development/gm_provider")
import staging; staging.make("/srv/genesis/staging", campaign_id="staging-1", experimental=False)
PY
G="python3 -B development/gm_provider/gmctl.py -c /srv/genesis/staging/campaign -i staging-1 -s /srv/genesis/staging/store.sqlite"

# 2. What can run here
$G providers                       # availability and the reason when unavailable
$G select gemini                   # GM for new declarations; reversible, recorded

# 3. Player side (or use the HTTP API)
$G state ; $G submit action.json ; $G status ACTION_ID

# 4. GM side
$G run gemini                      # a model-API provider plays the routed turn to a stop
$G claim claude-session --run R1   # an agent session instead: context, tables, roll, commit
$G reroute ACTION_ID gpt           # explicit handoff; refused while a lease is live

# 5. Service
GENESIS_PLAYER_TOKEN=... GENESIS_ALLOWED_ORIGIN=https://<ui origin> \
  python3 -B development/gm_provider/service.py serve --campaign ... --id staging-1 --store ... --autorun
```

Outcomes of a run: `committed`, `needs_revision`, `resolved_unpublished` (safe to repeat),
`blocked` (provider cannot run; the action waits), `released` (provider kept failing validation;
accepted tables and rolls are kept), `not_routed`, `busy`, `nothing`. After `blocked` or `released`
either run the same provider again or reroute. Never delete an operation record or a receipt.

Recovery is the inherited machinery: a pending dice journal or ledger batch makes readers fail
closed until the same request is repeated; the gateway repeats it from the operation record.
For canonical campaigns the gateway takes a `durable` hook that must succeed before anything is
published; production must pass the fenced git commit and push there (`turn.py push`). Staging
runs without it.

## 8. Verification summary

Run `bash development/run_all_checks.sh`. Recorded in `verification/provider_interchange/`.

| Requirement | Evidence | Kind |
| --- | --- | --- |
| Extended single-provider play | `test_extended_single_provider_play` (5 consecutive turns) | Mock provider |
| Switching between providers; returning to an earlier one | `test_switch_three_providers_and_return` (claude, gpt, gemini, claude, gemini, gpt); `test_player_api_three_providers_and_return` | Mock providers; real adapter HTTP code against a local fake |
| Each continues from its predecessor's committed result | Same tests: each narration must quote the predecessor's marker and head | Mock |
| Stale and duplicate submissions | `test_stale_and_duplicate_submissions`; HTTP 409 in the service test | Real gateway |
| Second provider cannot resolve a claimed declaration | `test_second_provider_cannot_resolve_a_claimed_declaration` | Real gateway |
| Interrupted execution, mid-turn handoff, no reroll | `test_interrupted_mid_turn_handoff_keeps_tables_and_dice`, `test_successor_cannot_replace_tables_or_reroll`, `test_provider_failing_mid_turn_keeps_accepted_dice`, `test_model_outage_mid_turn_then_same_provider_resumes` | Real dice and receipts |
| Interrupted ledger batch | `test_interrupted_ledger_batch_is_finished_byte_for_byte` | Real batch recovery |
| Publication recovery | `test_publication_recovery_by_any_provider_without_authoring` | Real publish set, store double |
| Unavailable provider, no substitution | `test_unavailable_provider_blocks_and_is_never_substituted`, `test_missing_credential_blocks_and_reroute_is_explicit` | Real gateway |
| Private-information boundary | `test_private_information_never_reaches_player_surfaces`; every HTTP body scanned for keys, tables, canaries | Real gateway and service |
| Dice modes across providers | `test_dice_modes_follow_the_inspected_policy_across_providers`, `engine.replay` | Real experimental engine on a marked copy |
| Adjudication repair | `test_action_economy.py` (8 cases) | Real validator |
| Regression, RNG replay, interruption, browser, protected paths | 27 Python suites, 9 browser suites, RNG audit of Hask Meadow and sandbox, built-page identity; every gateway test asserts source campaign files are unchanged | Inherited + new |
| **Claude → GPT → Gemini, model-backed** | `verification/provider_interchange/actual_provider_runs.json`: Claude actual (2 turns, including a return after GPT and Gemini were tried). **GPT and Gemini: not run. No credentials exist in this environment.** | Partly actual |

Not tested, stated plainly: a live GPT call; a live Gemini call; Claude through the Anthropic API
adapter; any hosted deployment; the live Datapad database; a real remote lease; real iOS Safari;
native Windows; token cost and latency of any model.

## 9. Release gates (all open)

- **G0 Audit.** Supply `Genesis_Gemini_Link_Continuity_Audit_2026-11-13.md`; reconcile its decisions
  with this candidate.
- **G1 Queue reachability.** The live queue, lease and published pages are a claude.ai artifact
  database, reachable only through Claude's ArtifactData tool and the artifact page itself. GPT and
  Gemini workers cannot read or write it. Decide one: (a) a Claude-run bridge that mirrors rows
  between the artifact database and the gateway store, or (b) host the gateway store as the queue
  and point a client at the HTTP API. Until then only Claude can GM the live Datapad.
- **G2 Credentials and models.** Owner provides keys and names the model for each provider, with
  billing authorised. Then run the three-provider sequence and the return handoff for real on a
  staging copy and record it.
- **G3 Hosting.** Choose where the service and the staging campaign copy run (needs git push rights
  for canonical campaigns and the `durable` hook wired to `turn.py push`). TLS, token rotation.
- **G4 Live worker adoption.** The Claude Datapad worker still follows the runbook directly. To make
  it one provider among three it should claim and commit through the gateway. Requires G1.
- **G5 Owner ruling.** Approve or amend `ACTION_ECONOMY_RULING.md`; decide whether the round-7
  historical note is recorded.
- **G6 Inherited gates.** Remote staging verification from `RELEASE_CANDIDATE_GATE.md` and
  `DICE_RECOVERY_RECONCILIATION.md` remains open. The live head moved 14 commits past the candidate's
  frozen base; they are merged here and must be re-merged at approval time.
- **G7 Prompt quality.** `GM_GUIDE.md` has only been exercised by a Claude session. Whether GPT and
  Gemini follow it well enough (narrative quality, schema adherence, rejection rate) is unmeasured.
