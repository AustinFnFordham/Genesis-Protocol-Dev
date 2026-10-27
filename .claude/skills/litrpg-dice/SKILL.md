---
name: litrpg-dice
description: Roll dice for the Star Wars LitRPG campaign. Use for EVERY roll (checks, attacks, saves, damage, initiative, loot, chaos tables). Never invent or "imagine" a roll result in narration.
---

# LitRPG dice

All dice in `campaigns/starwars_litrpg` come from `roll.py` in this folder. Do not make up numbers.

```
python3 .claude/skills/litrpg-dice/roll.py "1d20+5" --purpose "Aero: Insight vs Dax" --dc 12
python3 .claude/skills/litrpg-dice/roll.py "1d20+4" --mode advantage --purpose "Stealth"
python3 .claude/skills/litrpg-dice/roll.py "2d6+1d4+3" --purpose "Sneak attack damage"
python3 .claude/skills/litrpg-dice/roll.py "4d6kh3" --purpose "Ability score"
python3 .claude/skills/litrpg-dice/roll.py --advance-turn
```

Rules (from the Genesis dice contract):
- Roll first, narrate after. The result is binding; a nat 20 stays a nat 20 and a miss stays a miss.
- Pass `--dc` for any check with a hidden target. The DC goes to `hidden/roll_dcs.jsonl` only. The public log `records/roll_log.jsonl` never stores it.
- Show the player the roll and total. Never show the DC, enemy stats, or hidden modifiers unless their character would know them.
- Call `--advance-turn` once per player declaration so the roll stream stays replayable.
- Same seed + same turn + same call order reproduces the same rolls (Genesis `DiceService` parity, tested in `test_roll.py`).
- Run `python3 -I .claude/skills/litrpg-dice/test_roll.py` after touching the script.
