# Authoring a progression tree (CC-008 G)

This is a lightweight workflow for the owner and for agents. It **never changes the game runtime**: the tool reads JSON and writes reports only.

## 1. Write the tree

Start from `schema/genesis_progression_tree.schema.json` (`genesis-progression-tree/0.1`) and copy the closest example:

| Example | Shows |
|---|---|
| `trees/telekinetic_control.tree.json` | A specialized mastery with an owner-proposed curve and training-opportunity milestones |
| `fixtures/aero_vertical/aero_vertical.js` | Class (adapted from legacy), archetype, species and mastery trees, with cross-tree links |
| `fixtures/broken_tree.example.json` | Every common mistake, deliberately |

**Rules of thumb**
- **One track per tree.** Set `layer`.
- Set `xp_quantity`: `class_xp` only for class, `mastery_xp` or `discipline_xp` for earned tracks, and `none` plus `driven_by` for archetype and species tracks.
- **Every levelable track** declares: `start_level`, `max_level`, `curve` with `curve_status`, `cadence`, `evidence` and `provenance`.
- **Missing numbers** get `curve_status: "candidate"`; leave `"authoritative"` for sourced tables.
- **Requirements** always use `{all|any|any_of_group|not}`. A bare list is ambiguous and is rejected.
- **Candidate content** uses `status: "candidate"` and `candidate_*` ids. An `approved` tree can't contain candidate nodes or curves.
- **Grants** say what they are (`feature`, `profile`, `capacity`, `training_opportunity`, `track_unlock`) and who issues them (`authority` must match the layer). A training opportunity is never the power itself; list what it `never_grants`.
- **Repeatable grants** (for example ability score improvements) need `"repeatable": true`. Upgrades name their base node (`upgrades`).
- **Stacking:** two effects on the same `key` need a `stacking_group` (or an upgrade chain).
- **Conflicts** should be reciprocal.
- **Balance coverage:** list the simulations and tests that cover the tree's numbers in `balance_tests`.

## 2. Validate

```
node development/progression/tools/validate_tree.cjs my_tree.json [more.json …] \
     [--policy development/progression/policies/discipline_allocation.v0.1.json] \
     [--external class:sentinel,species:echani] [--md report.md] [--json] [--no-registry]
```

Exit codes: **0** pass, **1** errors, **2** usage.

**Checks**
- schema fields and provenance;
- Registry identities: URID format, approved URIDs, and feature grants against `registry/golden_slice`;
- exact prerequisite references, within and across trees;
- XP thresholds: monotonic, positive integer steps, complete tables;
- cadence range;
- reachability of every node;
- three-choice availability at each milestone (a warning when fewer than 3);
- grant authority by layer;
- duplicate rewards;
- stacking and conflict declarations;
- prerequisite cycles;
- unsatisfiable or empty choice groups;
- duplicate XP allocation in a Discipline policy;
- balance-test coverage.

## 3. Read the report

`--md` writes a readable level-by-level table per track (XP to next, cumulative XP, milestone markers, nodes at each level) and a mermaid **dependency graph**. `--json` gives the structured report: errors, warnings, reachability, tables and edges.

## 4. Test it in the sandbox

1. Load the tree with `framework.registry([...])`.
2. Award XP with `framework.awardXp` from committed, validated events (or through `disciplines.apply`).
3. Present milestones with `choices.offer` and `choices.select`.
4. Look at `test_cc008_f.cjs` for a full end-to-end example.

## 5. Promotion

Not part of this tool. Moving content from candidate to approved needs owner approval and a separate, versioned change.
