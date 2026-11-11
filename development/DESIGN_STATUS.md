# Consolidated development status

This development increment starts at a31251790597e9ca1c3140b4ebdd2d937571a9f3 on
dev/dice-history-gm-brief. No live branch or Artifact publication is part of it.

| Requirement | Status | Evidence or outstanding work |
| --- | --- | --- |
| Player dice history | Implemented in development | Publicly referenced rolls, deduplicated by roll ID, existing redaction policy, paginated history and Journal loading |
| Independent RNG verification | Implemented | JavaScript reference stream replays recorded rolls and checks state cursor and roll count, synthetic distribution diagnostic |
| Compact GM brief | Implemented as opt-in development CLI | Selectively ported e167ce2, checkpoint payload checked against replay, bounded history previews with retrieval IDs, full typed fields preserved |
| Shared provider refresh | Partial | Provider-neutral JSON through turn.py brief, expected-head rejection, player and GM audiences. Automatic provider wiring remains unimplemented |
| Batched ledger events / processing indicator | Unimplemented | Existing append-only ledger and processor behavior retained. Requires an isolated batch/recovery increment |
| Scene simplification / Journal chapters / turn repair | Unimplemented | Existing implementation inspected. No chapter taxonomy or repair transaction behavior inferred from the short retrieved brief |
| Aero–Wick relationship evidence | Partial existing prototype | Compact entity histories retain sourced observations. No relationship score, intent, or canonical change inferred |
| SID-001 Q15 | Provisional design only | Pre-seeded causal worldbuilding with evidence-gated expansion. No runtime algorithm or certification |
| SID-001 Q16 | Provisional design only | Layered/adaptive foundation discussed. No finalized runtime algorithm or certification |
| Campaign Genesis | Unimplemented | Requires full consolidated acceptance criteria and a separate isolated increment |
| Live Claude workflow | Untested | Generated HTML is local development output. No database write, merge, or Artifact republish |

The prior conversation retrieval supplied the milestone list and Q15/Q16 summaries,
but did not return the full original Consolidated Development & Gameplay Improvement
Brief. Exact design acceptance criteria for the remaining gameplay/UI work are
therefore unavailable in this handoff. This increment does not certify that brief
as complete.

## Compact brief usage

Run from the repository root.

```sh
python -B .claude/skills/litrpg-process-turn/turn.py brief sandbox --compact --audience gm --out /tmp/gm-brief.json
python -B .claude/skills/litrpg-process-turn/turn.py brief sandbox --compact --audience player
python -B .claude/skills/litrpg-dice/audit_rng.py campaigns/starwars_litrpg/runs/sandbox
python -B development/benchmark_brief.py
```

GM briefs and checkpoints contain private information. They are never routed
through player exports. A cached reducer checkpoint is verified against a replay
of its prefix; it does not currently accelerate disk validation. Compact previews
bound the history text, with every omitted event still available through
brief.py history. The campaign-specific prototype aliases and fields remain
explicit limitations, especially for other campaigns.

The prototype's player projection is now reduced independently from public
events, so hidden typed hands, flags or presentation events cannot overwrite the
player bundle. Internal table provenance in public summary text is removed at the
presentation boundary. Historical source events remain authoritative and intact.

## Publication compatibility

The state remains at most 96,000 bytes and history pages at most 150,000 bytes.
Dice history is loaded on demand, using the same page manifest and pages-first,
snapshot-last publication plan. New snapshots have an additive dice_history
manifest. Older snapshots without it remain supported. Player rolls show raw
total, formula, explicit modifier, mode and final total. Existing NPC redaction
is preserved and hidden rolls are omitted. Existing advantage logs can lose the
original first face when the alternate wins; this increment preserves those logs
and does not claim to restore unavailable historical faces.

Local browser coverage used Chromium at a 390-by-844 viewport. It does not
constitute an iPhone or deployed Claude Artifact test.
