# Gemini app connection contract (v1, staging)

What a Gemini-hosted app (or any other player client) needs to play a Genesis campaign on an
ongoing basis: load, refresh, declare, wait, reconnect, and hand the GM seat to another provider.

**Verification status.** Every statement below was verified against the implemented service
(`development/gm_provider/service.py`) over real local HTTP by `test_service.py`. Nothing is hosted:
there is no public endpoint, no issued token, no Google project, and no Gemini app was inspected,
because none exists in the repository or the session and the continuity audit was not supplied.
Whether a given Gemini app surface may call an external HTTPS origin with a bearer token, and under
which origin it runs, must be confirmed on the real app before this is called a production contract.

## 1. Three separate things

| Concern | Where | Holds |
| --- | --- | --- |
| UI hosting | The Gemini app (or the Datapad artifact, or a static page) | Only the player token and public documents |
| Model execution | The Genesis GM worker (the service process, or an agent session) | Provider API keys, GM-private context |
| Canonical persistence | The campaign ledger in git; the store for queue, lease and published pages | Everything durable |

The app never calls a model to adjudicate and never holds a model key. Choosing "Gemini" as GM means
the worker calls the Gemini API with the worker's key. A Gemini model inside the app may help the
player phrase a declaration, but it is not the GM and its output is only a declaration.

## 2. Permissions

- One bearer token per player: `Authorization: Bearer <GENESIS_PLAYER_TOKEN>`. It grants: read the
  public campaign, submit declarations for the active player character, choose and reroute the GM
  provider. It grants nothing GM-side; no GM endpoint exists.
- CORS: the service answers a single configured origin (`GENESIS_ALLOWED_ORIGIN`). Set it to the
  app's real origin. All responses are `Cache-Control: no-store`.
- `GET /v1/health` and `GET /v1/providers` need no token and expose no secret (ids, availability,
  the missing-setting reason, model id).

## 3. Endpoints

| Call | Result |
| --- | --- |
| `GET /v1/providers` | `{providers: [{id, kind, available, reason, model, mock}]}` |
| `GET /v1/campaigns/{id}/state` | `{cursor: {campaign_id, revision, ledger_head, context_id}, state, pages: [names], in_flight, routing}` |
| `GET /v1/campaigns/{id}/pages/{page}` | One history page (feed, journal, dice history, chapters, events) |
| `POST /v1/campaigns/{id}/provider` `{provider}` | Routing for declarations submitted from now on |
| `POST /v1/campaigns/{id}/actions` (envelope below) | `202` and the action status; `200` with `duplicate: true` on a retry |
| `GET /v1/campaigns/{id}/actions/{action_id}` | `{action_id, status, provider, stage, blocked, review, error, publication, published_revision}` |
| `POST /v1/campaigns/{id}/actions/{action_id}/reroute` `{provider}` | Explicit handoff of an unfinished action |

`state` is the same document the Datapad reads (`view/state`): scene, character, `turn_context`
(options, objects, movement, dialogue, notes, hands, pending steps), recent feed and journal, and the
history manifest. It is built from the public ledger only.

Action envelope:

```json
{"action_id": "<6-64 chars, minted once per draft>",
 "campaign_id": "<id>", "actor": "aero",
 "based_on_revision": 45, "ledger_head": "evt_0050", "context_id": "evt_0050",
 "text": "free text, optional", "declaration": {"actor": "aero", "steps": [ ... ]},
 "contract": "turn-contract/3", "confirmed_warnings": false,
 "resolution_settings": {"temperature": "regular", "narrative_consequences": false},
 "gm_provider": "gemini"}
```

`based_on_revision`, `ledger_head` and `context_id` are copied from the `cursor` the declaration was
composed against. `gm_provider` is optional; without it the campaign routing applies; with neither,
the submit is refused. `resolution_settings` other than the default are accepted only where the
campaign has dice modes enabled.

## 4. Errors the app must handle

| HTTP | Code | Meaning for the app |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | Token missing or wrong |
| 409 | `STALE` | The campaign moved. Refresh `state`, keep the draft, let the player re-check |
| 409 | `TURN_IN_FLIGHT` | A declaration is still resolving. Poll it |
| 409 | `ACTION_ID_REUSED` | Same id, different content. Mint a new id for a new draft |
| 409 | `PROVIDER_BUSY` | Reroute refused: the current GM still holds the turn |
| 422 | `PROVIDER_NOT_SELECTED`, `UNSUPPORTED_SETTINGS` | Ask the player to choose |
| 400 | `UNKNOWN_PROVIDER`, `BAD_ACTION_ID`, `BAD_SETTINGS`, `NOT_ACTIVE_ACTOR`, `WRONG_CAMPAIGN` | Client error |
| 503 | `CAMPAIGN_BUSY` | The record is mid-write. Retry shortly |

## 5. Play loop

1. **Load / reconnect / refresh.** `GET state`. Render `state`. If `in_flight` is present, show its
   status and poll it; do not offer a new declaration.
2. **Declare.** Build the declaration against `state.turn_context`, mint `action_id` once, keep the
   draft locally, `POST actions`. On any network failure, repeat the same request with the same id.
3. **Wait.** Poll `GET actions/{id}` (2–5 s). `submitted` → `processing` (`stage`: claimed, context,
   rules, dice, ledger, narration, publishing) → `committed`. Then `GET state`; the revision is higher.
4. **Needs revision.** `status: needs_revision` with `review {summary, errors, warnings,
   alternatives}`. Show every reason. A chosen alternative is submitted as a new action.
5. **Blocked.** `blocked {code: PROVIDER_UNAVAILABLE | PROVIDER_NOT_CONFIGURED, provider, reason}`:
   the chosen GM cannot run. Nothing else will take the turn. Offer: wait, or reroute to another
   provider. Never reroute without the player's choice.
6. **Publication pending.** `status: resolved`, `publication.status: pending`: the turn is resolved
   for good and will appear; keep polling. Do not resubmit.
7. **Provider handoff.** For the next turns: `POST provider`. For the turn in flight:
   `POST reroute`, which succeeds only when no GM run holds the lease. A handoff mid-turn keeps the
   dice already rolled; the new GM continues from them.

## 6. Guarantees the app can rely on

- Submitting the same action twice never resolves it twice.
- A declaration made against an old revision is refused, never applied.
- The published state changes only to a complete, committed revision; history pages land before the
  snapshot that references them.
- No response contains GM-only events, tables, DCs, private roll data, operation records, the dice
  seed, or any provider credential.
- The provider that ran each turn is recorded privately with the turn; the app sees the routed
  provider on the action status.

## 7. Before production

Host and TLS; a real token per player with rotation; confirm the app's origin and outbound-call
permissions; wire the git durability hook for canonical campaigns; resolve gate G1 in
`PROVIDER_INTERCHANGE.md` (the live Datapad queue is not reachable from outside Claude).
