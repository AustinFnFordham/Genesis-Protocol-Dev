# Experimental dual-axis resolution

Owner-proposed mechanics; sandbox-only and not activated in a live worker.
The source roller's mulberry32, formula parser and face selection are reused.
Existing raw roll fields retain their prior meaning and independent replay.
The effective resolution is an additive, versioned projection, not a rewrite.

## Policy

| Setting | Effective d20 |
| --- | --- |
| Regular (default) | raw face |
| Heroic | 11 + floor((raw - 1) / 2) |
| Legendary | 16 + floor((raw - 1) / 4) |

Advantage/disadvantage selects the original face first. Original/alternate faces,
the selected raw face, effective face, other dice, flat modifiers and effective
total remain separately auditable. Each face from 11–20 has two preimages in
Heroic; each face from 16–20 has four in Legendary. These are uniform before
advantage/disadvantage, not afterward.

Eligibility requires an active player-controlled check, attack or save with
exactly one single positive d20 term. Other dice in a mixed check are retained
unchanged. NPC/hidden rolls, damage, multiple-d20 pool formulas and other rolls
remain ordinary. Existing parser restrictions on advantage formulas still apply.

Attacks: an original 20 auto-hits and is critical in all three modes; an effective
20 from another original face is not critical. An original 1 auto-misses only in
Regular. Checks/saves compare the total with the target without an automatic
natural-face override in this experimental policy. Any governing domain rule
requiring other handling must be adjudicated before requesting this resolver;
no universal saving-throw or injury rule is introduced here.

The degree is the exact numeric margin band specified by the owner: <= -10 severe
failure, -9..-5 hard failure, -4..-1 narrow failure, 0..4 narrow success, 5..9 strong
success, >= 10 exceptional success. It never supersedes a mechanical rule. For
example, a critical attack can succeed despite a negative numeric margin; its
private record explicitly retains both the margin degree and critical override.

Narrative Consequences defaults Off, independently of temperature. When On for
an eligible roll, the d6 maps 1 -> 2 Threat, 2 -> 1 Threat, 3/4 -> Neutral,
5 -> 1 Advantage, 6 -> 2 Advantage. A domain-separated per-request mulberry32
stream is seeded from SHA256(domain, private campaign seed, turn, action ID,
roll key). It consumes zero ordinary draws. Private execution records retain
domain/algorithm/request/draw index for replay. No public seed is emitted.

Chaos candidate assessment requires cited events, a rule/effect identity and a
domain validation callback. It cannot create a candidate, spend points, mutate
state, recruit an NPC or choose a player action. No eligible candidate is a valid
result even with two points. Atomic must separately validate any explicit effect
commit. The wider 0–5+ budget model and SID Q15/Q16 remain provisional.

## Immutable input and isolated configuration

The composer adds this optional field to the submitted action:

```json
{"resolution_settings":{"temperature":"regular","narrative_consequences":false}}
```

Legacy envelopes default to Regular/Off. Unknown values fail closed. The UI shows
the controls only when the public snapshot has experimental resolution enabled.
It resets them on a new context, freezes selections at submit, and displays the
submitted settings on the action. Pre-roll approval includes those settings.

The engine requires an `experimental_resolution.json` marker in an isolated copy:

```json
{"enabled":true,"canonical":false,"campaign_id":"resolution-staging-copy","controlled_actors":["aero"]}
```

It refuses the repository's original `campaigns/starwars_litrpg/runs/` directories.
Do not add a marker to Hask Meadow, change the registry, or reuse a live database.
The current candidate creates none of those markers in source campaigns.

## Worker procedure for a future staging adapter

1. Read the authorized staging queue row, CAS version and worker lease. Claim it
   through that environment's actual lease protocol. This module is not a remote
   queue adapter; local locks alone do not certify a remote worker lease.
2. Preserve action ID, declaration, actor, public revision/head/context and both
   selections. Load a compact brief with `brief.build(entry, action=action)` or
   the registered CLI's new `--action` option. The brief binds the submitted
   settings to the public revision. Do not publish its GM audience.
3. Run existing rules preflight. Create a GM roll request with stable `roll_key`,
   authorized `step_id`, formula, advantage mode, kind, requested actor, cited
   rules, purpose and private DC if required. A temperature never legalizes an
   invalid declaration. Condition/trigger adjudication remains the GM's duty.
4. Execute in the isolated copy:

   ```sh
   python -B development/experimental_resolution/engine.py CAMPAIGN ACTION_ID ACTION_JSON REQUEST_JSON
   ```

   The result is **GM-private**. The ordinary log includes only allowlisted
   resolution metadata. Private task result/degree/margin/DC and causal candidates
   are kept outside player exports. Public roll history displays the effective
   total and narrative points while retaining raw faces.
5. On interruption, repeat the exact request and action. An accepted plan is
   resumed byte-for-byte before any RNG call. One roll per action/step/actor/kind
   is supported; renaming its key cannot reroll it. More complex multi-roll steps
   require explicit sequencer decomposition or a reviewed future roll-plan
   contract. Changing the formula, actor, mode, DC or settings is not a retry.
6. Validate and batch commit the declaration (including settings), public safe
   resolution, authorized consequences, narration and next context. Preserve
   pending steps. Use `policy.public_resolution()` for public event details.
   Keep private calculations and evidence in a hidden event or execution record.
   Ledger validation binds public resolution metadata to the immutable roll,
   original declaration settings and step. NPC/GM metadata is kept private.
7. Follow the existing committed-and-pushed publication protocol: all bounded
   history pages first, snapshot last under CAS. Do not call progress Complete
   until actual remote publication succeeds. Keep publication-pending separate
   from a failed resolution. The existing local roundtrip tests are not proof
   that steps 1 and 7 work against a real remote service.

## Crash recovery and legacy limit

The engine uses the existing local ledger writer lock and a durable private
write-ahead plan. Both append prefixes and any already-written suffix must match
exactly. The ordinary cursor is replaced atomically only after logs are flushed.
A receipt is durable before clearing the pending barrier. Event/roll readers fail
closed while a dice transaction is pending. Changed bytes require manual review;
the engine never truncates a log, reseeds dice or silently reconciles a cursor.

At the original frozen candidate, a real process-kill test demonstrated that
legacy `roll.py` could append a public roll before replacing its cursor. The
legacy recovery follow-up adds a private write-ahead journal and shared writer
lock to that CLI. Roll and `--advance-turn` retries with the same `--request-id`
return durable receipts, including after the response is lost. Unkeyed commands
remain compatible; after their pending journal clears, another invocation is a
new operation. Remote workers must supply stable operation IDs before promotion.
The experiment refuses to run while a legacy transaction is pending. Neither
path retrospectively repairs older interruptions lacking an accepted journal.
See `development/LEGACY_DICE_RECOVERY.md` for the tested recovery boundary.

## Tests

Set TMPDIR to `development/.qa/tmp` and PYTHONDONTWRITEBYTECODE=1. Run:

```sh
python -B development/experimental_resolution/test_resolution.py
python -B development/experimental_resolution/compare_scenes.py
python -B development/test_worker_roundtrip.py
```

The comparison is six equal-seed, six-scene scripted diagnostic workloads. It
records success counts, independent narrative outcomes, zero unsupported effects,
retained decision points, local timings and public progression. It makes no claim
about entertainment quality, real model calls, token use or remote latency.
Real process termination at seven write boundaries and torn log/state-temporary
tests verify recovery without regenerating accepted dice. Linux was exercised;
native Windows, real iOS Safari and remote worker integration remain unverified.
