# Grapple progression: design scaffold (CC-007 §6) — FOR OWNER REVIEW, grants nothing

**Data:** `skills/grappling.scaffold.v0.1.json`. It reuses the mastery substrate: the same XP gate, receipts, curves and milestone eligibility.

**Status:** `scaffold`.
- There are **no numbers** beyond those already on the sheet.
- No abilities are defined or granted.
- The milestones are `family_placeholder` entries that only "open" a family for design.

## Layers: what kind of thing each capability is

| Layer | Meaning | Earned by |
|---|---|---|
| **Trained skill** | Gets better with validated use | Mastery XP (this substrate) |
| **Purchased or taught** | A named technique learned from a teacher or training | A recorded grant (`recordGrant`), never XP alone |
| **Class feature** | Comes with class level (for example Sentinel) | Class progression. **Outside** the substrate. |

## Families and dependencies

```
basic_capability (implemented, CC-007 C: grapple, escape, drag, release; sheet-sourced)
 ├─ escape_and_counterplay   (trained)  — more reliable escapes; resisting being grappled
 └─ control_and_drag         (trained)  — better dragging; positioning a held creature
      └─ learned_maneuvers   (taught)   — named techniques (throws, pins…) — NONE DEFINED
           └─ compound_attacks (taught) — grapple + strike combinations using several budgets (the SA-001 study applies)
class_features — anything from class level stays a class feature, never earned by XP
```

**Placeholder gates:**
- L5 opens `escape_and_counterplay`.
- L10 opens `control_and_drag`.
- L15 opens `learned_maneuvers`.

These are design gates for owner content, not grants.

## XP events (placeholders)

`grapple_attempt`, `escape_attempt` and `drag`, each 1 XP. They come only from server-verified engine events: `contest` with pid `grapple` or `escape_grapple`, and `drag`.

**No adapter is wired yet** (there is no grapple curve or content to award towards).

## Needed from the owner

- Grapple skill-tree concepts: what each family actually contains.
- A curve, or confirmation of the Telekinetic Control curve.
- Whether escape practice counts for the escaper's own grappling skill.
- Whether compound attacks depend on SA-001 (see `SA001_PROPOSED_CONTRACT.md`).
