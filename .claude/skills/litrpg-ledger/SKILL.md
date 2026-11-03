---
name: litrpg-ledger
description: Commit and query the Star Wars LitRPG event ledger. Use after EVERY resolved action, discovery, relationship change, or World event, before narrating it. The Arc Record and the novel are generated from this ledger.
---

# LitRPG event ledger

Every consequential thing that happens is committed here **before** it is narrated. Narration may embellish a committed event; it may not invent a consequential one.

```
python3 .claude/skills/litrpg-ledger/ledger.py add --kind attack_resolved --summary "Aero's shot misses the guard" \
   --actor aero --world-time "Day 1, dusk" --roll roll_t3_2 --caused-by evt_0004 --idem t3_attack
python3 .claude/skills/litrpg-ledger/ledger.py add --kind npc_plan --summary "Guard captain decides to report Aero" \
   --visibility gm_only --type fact --world-time "Day 1, dusk"
python3 .claude/skills/litrpg-ledger/ledger.py add --kind rumor --summary "The companion hears the guard fell" \
   --type belief --known-to companion_a --world-time "Day 1, night"
python3 .claude/skills/litrpg-ledger/ledger.py validate
python3 .claude/skills/litrpg-ledger/ledger.py show --as player --session 2
```

Rules:
- `--type fact` is world truth; `report` is what someone observed or was told; `belief` is what an actor holds and may be false. `report` and `belief` need `--known-to`.
- `gm_only` events go to `hidden/events.jsonl`; all others to `records/events.jsonl`. `show --as player` redacts hidden causes.
- `--caused-by` may only name earlier events (acyclic ancestry). `--roll` must exist in the roll log: roll first, then commit.
- Use `--idem` on anything that could be submitted twice. A duplicate returns the original event, never a second one.
- The ledger refuses new events while it is invalid. Run `validate` and fix tampering first.
- Run `python3 -I .claude/skills/litrpg-ledger/test_ledger.py` after touching the script.
- Tags are discovery hints, not proof. State changes (achievements, affinity, relationship shifts) cite event ids.
