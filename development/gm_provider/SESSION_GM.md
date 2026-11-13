# Run one Genesis GM turn from an agent session (any model)

You are an AI agent session with a shell and a git checkout of `AustinFnFordham/Genesis-Protocol-Dev`.
You will act as Game Master for exactly one queued turn of an isolated, non-canonical staging
campaign, through the shared gateway. You need no API key and nothing is billed by this procedure:
the reasoning is yours, the dice and the record are the gateway's.

Your provider id is given to you by the person who started you: `gpt-session`, `gemini-session`
or `claude-session`. Use exactly that id. If the queued action is routed to another id, stop.

## Rules that cannot be bent
- Work only on branch `staging/provider-shared`, only under `staging/shared-1/`, and only through
  `gmctl.py`. Do not edit files by hand, do not run `git commit`/`git push` yourself (the gateway
  commits and pushes each accepted step), do not touch `campaigns/`, do not force-push.
- Never state a die result. Ask the gateway for every roll. An accepted roll is final.
- If the gateway refuses a move, read the reason and fix that move. If it says `LEASE_LOST`,
  `NOT_ROUTED_HERE` or `PROVIDER_BUSY`, stop and report; do not retry around it.
- Say truthfully which model you are in `--model`. If you do not know, write `unknown`.

## Procedure
```sh
git fetch origin && git checkout staging/provider-shared && git pull --ff-only
G="python3 -B development/gm_provider/gmctl.py --shared staging/shared-1"
ME=<your provider id>;  RUN="$ME-$(date +%s)"

$G recovery                                   # what is in flight, routed to whom, what was already accepted
$G claim $ME --run $RUN --model "<your model name and version>" --session "<link or id of this session>"
$G context $ME --run $RUN --out /tmp/context.json     # GM-private. Read it. Do not paste it anywhere public.
```
Read `development/gm_provider/GM_GUIDE.md` in full: it defines your authority, the adjudication
rules and the JSON shape of each move. Then, as that guide says:

```sh
# 1. Your interpretation and the tables you fix before any die  (or a review, instead of everything else)
$G tables $ME --run $RUN /tmp/tables.json
# 2. Each roll you need, one file per request; the answer is binding
$G roll   $ME --run $RUN /tmp/roll1.json
# 3. After reading the results (re-run `context` to see them under operation.rolls): consequences,
#    narration, scene and the next turn context
$G commit $ME --run $RUN /tmp/proposal.json
$G recovery                                   # in_flight must now be null and the revision higher
```
If `context.operation.tables` is already filled or `operation.rolls` is not empty, another GM started
this turn. Continue from what is there: do not send new tables, do not ask again for a roll that
exists. If you cannot finish, run `$G release $ME --run $RUN` and say so; what was accepted is kept.

## Report back
The action id, the final status, the roll ids, the ledger event ids, the model name you attested,
and anything the gateway refused along the way.
