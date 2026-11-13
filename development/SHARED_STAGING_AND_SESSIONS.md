# Shared staging, session-driven GMs and the single execution path (2026-11-13, HOLD)

Continues `development/PROVIDER_INTERCHANGE.md` from candidate `4261c1f`. Branch heads were rechecked
before work: `litrpg/campaign-scaffold` `d84a52c`, `rc/canonical-dice-recovery-f241ea6` `1acf2a0`,
`rc/experimental-resolution-acd961c` `f241ea6`: all unchanged. Nothing was deployed, no billing was
enabled, no canonical record was modified, live play was not advanced.

## 1. Inputs that did not arrive

| Expected | Status | Consequence |
| --- | --- | --- |
| `Genesis_Gemini_Link_Continuity_Audit_2026-11-13.md` | Not attached to the session, not in the repository on any branch, not in the project documents | **No reconciliation was performed.** No conflict list exists. Nothing in this candidate claims to agree with the audit |
| Gemini's full-stack bundle and report | Not supplied. No file in the repository contains `turns/execute` or any Gemini app source | **Gemini's source was not inspected.** Its `/api/v1/…/turns/execute`, recovery and lease routes are known only from the description in the request. No mapping was written against guessed shapes |

## 2. One authoritative execution path

Decision, independent of the missing inputs: the gateway (`gm_provider/gateway.py`) is the only
place where a turn is claimed, tables are fixed, dice are requested, a batch is committed and a
revision is published. Every other surface is a transport onto those calls:

| Transport | For | Adds machinery? |
| --- | --- | --- |
| `gmctl.py` | Agent sessions with a shell, operators | No |
| `service.py` player routes `/v1/campaigns/…` | Player clients | No |
| `service.py` GM routes `/v1/gm/{campaign}/{provider}/{verb}` | GM sessions that can only make HTTPS calls | No: each verb is one gateway call |
| `runner.py` | Model-API providers | No |

How Gemini's app is to be connected, once its source is available, in order of preference:
1. **Adapt the client** to call the player routes (submit, status, state, recovery, reroute). Its
   server then holds no dice, lease, receipt or campaign-state logic at all.
2. Where its UI is built around its own route names, add **aliases** in `service.py` that translate
   request and response shapes and call the same handler. An alias must not carry state.

What its reported routes must become, by intent (shapes to be confirmed against the source):

| Reported Gemini route | Authoritative operation | Note |
| --- | --- | --- |
| `…/turns/execute` | `POST /v1/campaigns/{id}/actions` then poll `GET …/actions/{action_id}` | Execution is asynchronous and idempotent on `action_id`. A synchronous "execute and return the narration" call must not roll or commit in the app's own server |
| recovery route | `GET /v1/campaigns/{id}/recovery` | Reports phase, accepted mechanical work and what may happen next |
| lease route | Read-only: `recovery.lease`. A client never takes, renews or releases a GM lease | Only a GM run does, through `claim` and `release` |

Anything in the bundle that rolls dice, keeps its own turn counter, lease table, receipt store or
campaign state is a conflict to be removed, not merged. That list cannot be written until the
source is read.

## 3. Recovery is keyed on accepted work, not on revision

The campaign revision moves only when the ledger batch commits. Tables fixed and dice accepted leave
it unchanged, so "revision unchanged" does not mean "nothing happened". Two additions make the real
state visible to every client and worker:

- `mechanical(action_id)`: `{tables_fixed, rolls_accepted, batch_accepted, batch_committed,
  fingerprint}`. Counts and flags only; safe for players. Included in every action status.
- `recovery()` (`gmctl recovery`, `GET …/recovery`): revision and head (or `record_mid_write`),
  the in-flight action with its phase (`interpret` / `resolve` / `publish`), its `mechanical`
  block, the lease, whether a reroute is allowed, and what may legally happen next.

Releasing a lease returns the turn; it removes nothing. Tested at each point
(`test_gateway.RecoveryAfterRelease`):

| Released after | What a successor (same or other provider) can do | Asserted |
| --- | --- | --- |
| Tables fixed | Continue from those tables | New tables refused `TABLES_FIXED`; review refused `TOO_LATE_FOR_REVIEW`; fingerprint unchanged by further releases; revision unchanged while `tables_fixed` is true |
| Dice accepted | Use the accepted results | Three successive runs under three providers each ask for the roll under a new key and receive the same `roll_id`; roll log and dice cursor byte-identical; revision unchanged while `rolls_accepted` is 1 |
| Ledger batch accepted, interrupted | Finish the accepted bytes | New tables and new rolls refused `ALREADY_COMMITTED`; the committed narration is the original provider's; batch fingerprint unchanged; one roll |
| Publication pending | Publish only | Reroute refused `NOT_REROUTABLE`; tables and `fail` refused `ALREADY_COMMITTED`; a release leaves it `resolved`; a different provider publishes; ledger head unchanged |

## 4. Who is reasoning: recorded, not assumed

`claim` takes the run's own statement `{kind, model, session, mock}`. It is stored with the
operation and written into the committed GM-only ruling (`details.gm_provider.identities`), one
entry per run that touched the turn. Scripted providers are recorded `kind: scripted, mock: true`;
model-API runs record the configured model id; agent sessions record what they state with
`--model` and `--session`. This is an attestation. The gateway cannot verify which model a session
is; the session link is the evidence a reviewer follows.

## 5. The shared staging environment (exists now)

Branch `staging/provider-shared`, directory `staging/shared-1/`:

```
staging/shared-1/environment.json     campaign_id shared-1, canonical: false
staging/shared-1/campaign/            isolated copy of the non-canon sandbox (ledger, dice, receipts)
staging/shared-1/store/               actions/, locks/, routing/, view/   (JSON documents with versions)
```

`store.GitStore` keeps the queue, the lease and the published pages as files in the **same git
history as the staging ledger**. A store write is a commit pushed without force; a rejected
non-fast-forward push is the compare-and-set. Accepted private work (tables, dice receipts, the
batch) is pushed at each acceptance so another session starts from it. Consequences:

- There is one queue. It is not independently authoritative: it cannot be ahead of, or diverge from,
  the ledger, because both are the same commits. Deleting `store/` loses requests and the lease,
  never campaign truth; `view/` is rebuilt from the ledger.
- Any client or GM session with git access to that branch can take part. No server, no database, no
  model credential, no billing.
- It is slower than a database (a fetch and a push per write) and is meant for staging and
  acceptance, not for live play.
- Hask Meadow is not in it and cannot be: `open_shared` refuses an environment not marked
  non-canonical, and the experimental engine refuses source campaign directories.

State at hand-off: revision 40, head `evt_0043`. Turn `shared-0001` was resolved by Claude through
this environment. Turn `shared-0002` ("Touch the remote's housing to test it") is **queued for
`gpt-session`** and waiting.

## 6. Access and invocation requirements per route

"Verified" means read from primary documentation or executed in this work. Product terms change;
confirm on the real account before relying on a line marked unverified.

| Provider | Route | What it needs | Billing | Status |
| --- | --- | --- | --- | --- |
| Claude | Agent session + `gmctl` | A Claude session with a shell and push access to the staging branch | None beyond the session | **Executed** (three turns in total) |
| Claude | Anthropic API adapter | `ANTHROPIC_API_KEY`, `GENESIS_CLAUDE_MODEL`, a host for the worker | API usage | Wire format only |
| GPT | Agent session + `gmctl` (`gpt-session`) | An OpenAI agent session that has a shell and a checkout of the repository with push rights to `staging/provider-shared`, plus `python3`, `node`, `git` and network access to GitHub from inside its sandbox | No API key. Whatever the ChatGPT/Codex plan includes | **Not executed: no such session can be started from here.** Product terms unverified: the OpenAI documentation pages could not be read in this run |
| GPT | HTTPS-only session (an assistant with an HTTP action) | A reachable `service.py` and a `gpt-session` GM token | None for the gateway | Transport tested with a scripted stand-in. Needs hosting |
| GPT | OpenAI API adapter | `OPENAI_API_KEY`, `GENESIS_GPT_MODEL`, a host for the worker | API usage, must be authorised | Wire format only |
| Gemini | Agent session + `gmctl` (`gemini-session`) via Gemini CLI | Gemini CLI in a local checkout with git credentials. The CLI documents built-in shell commands, non-interactive use, and sign-in with a personal Google account with a stated free tier (60 requests/min, 1,000/day) | None on that free tier, per its documentation | **Not executed: needs a machine the owner controls.** Capabilities verified from the Gemini CLI documentation |
| Gemini | Agent session via Jules | Repository access through its GitHub integration | Unverified | Unverified: only a secondary article was readable |
| Gemini | HTTPS-only (the Gemini app / AI Studio bundle) | A reachable `service.py`; whether the app's server may call an external HTTPS origin and hold a token server-side | Unverified | **Blocked on the bundle** and on the AI Studio documentation, which could not be read in this run |
| Gemini | Google API adapter | `GEMINI_API_KEY`, `GENESIS_GEMINI_MODEL`, a host for the worker. The Gemini CLI documentation states an API-key free tier (100 requests/day) | Free tier or API usage | Wire format only |

Agent-session operation therefore does not require API credentials or billing for any of the three
providers. It requires a session with a shell and push access to one branch. The exact procedure a
session follows is `development/gm_provider/SESSION_GM.md`.

## 7. Demonstration status

| Step | Provider | Reasoning | Result |
| --- | --- | --- | --- |
| Isolated copy, turn 1 (earlier) | `claude-session` | Real: Claude in this session | Committed |
| Isolated copy, turn 2 (earlier) | `gpt`, `gemini` API | None | Blocked: no credentials. Rerouted to Claude, committed |
| Shared environment, `shared-0001` | `claude-session` | Real: Claude in this session, attested model id `claude-fable-5-2` (configured id; the serving model may differ) | Committed, revision 35 → 40, pushed |
| Shared environment, `shared-0002` | `gpt-session` | **Not run** | Queued and waiting for a GPT session |
| Then | `gemini-session` | **Not run** | To be declared after `shared-0002` commits |
| Return handoff | `claude-session` | Not run | To be declared after the Gemini turn |

Everything else that shows three providers alternating is a scripted stand-in and is labelled so in
the tests, in the operation records and in the committed rulings (`mock: true`).

To complete the acceptance sequence the owner starts two sessions, each with the one instruction
"Follow `development/gm_provider/SESSION_GM.md` as provider `gpt-session`" (then `gemini-session`),
and between them queues the next declaration:

```sh
G="python3 -B development/gm_provider/gmctl.py --shared staging/shared-1"
$G declare shared-0003 gemini-session "Inspect the disabled remote again"
$G declare shared-0004 claude-session "Step back to where you started"
```

## 8. Datapad connection (prepared, not applied)

The Datapad page, its presentation and its database are untouched. The only presentation-affecting
code change in this candidate remains the validator labels from the adjudication repair. To let
non-Claude providers serve the Datapad, exactly one of these is needed, and neither is applied:

- **Bridge.** A Claude routine mirrors `actions`, `locks` and `view` between the artifact database
  and the gateway store. The Datapad is unchanged. The artifact database stays a mirror; the gateway
  store, in the campaign's history, stays the queue. One authoritative queue.
- **Repoint.** The page reads and writes through the player routes instead of the artifact database.
  One file changes (`ui/src/core.js` data access); markup and styles do not. Needs a hosted service.

## 9. Remaining blockers, precisely

1. The audit document: not supplied. Reconciliation not started.
2. Gemini's bundle and report: not supplied. Source not inspected; route aliases not written.
3. A GPT agent session with push access to `staging/provider-shared`: cannot be created from this
   environment. `shared-0002` waits for it.
4. A Gemini agent session (Gemini CLI on an owner machine, or Jules): same.
5. Hosting for `service.py`, needed only by HTTPS-only clients (the Gemini app) and HTTPS-only GM
   sessions. Not deployed by instruction. Requirements: a process with a clone of the staging branch
   and push rights, TLS, `GENESIS_PLAYER_TOKEN`, `GENESIS_GM_TOKENS`, `GENESIS_ALLOWED_ORIGIN`.
6. API routes: keys, model ids and billing authorisation, if wanted in addition to sessions.
7. Documentation that could not be read in this run (OpenAI Codex, Google AI Studio full-stack apps,
   Jules): the rows marked unverified in §6.
