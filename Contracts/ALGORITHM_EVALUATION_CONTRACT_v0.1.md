# GENESIS — Gaming Algorithm Evaluation Contract (ALG-001)
**Version:** 0.1.0 | **Status:** proposed evaluation protocol, no algorithm adopted by assertion | **Date:** 2026-11-03
**Parents:** CIS-001, AAS-001, HRM-001; Articles of Creation deterministic and no-drift requirements.

## Objective
Select the **smallest appropriate composition** of game algorithms based on player-experienced behavior, correctness and measured cost. Trinity describes philosophical roles, **not implementation technology**. Rust, Python, TypeScript or Lua/Luau are candidate execution environments—not an excuse to multiply sources of truth.

## Evaluation matrix (each needs fixture, baseline, ablation, measured results)
| Candidate | Bounded Genesis scenario | Baseline to beat | Key acceptance signal |
|---|---|---|---|
| Finite / hierarchical state machines | Combat action windows, dialogue, quest and relationship lifecycles | ad hoc conditions | No illegal transitions; comprehensible trace |
| Behavior Trees | Guard/companion tactical reactions and day routine | scripted if/else | Predictable, interruptible, bounded decisions |
| GOAP | Nemesis / senator plans under changing resources/knowledge | fixed plan list | Finds valid alternative plans, no omniscience |
| Utility AI | Actor chooses among survival, loyalty, revenge, duty | fixed priority | Stable but nuanced priorities; explainability |
| Event-driven rule evaluation (Osiris-like) | Witnessing betrayal, barrel ignition, social ripple | polling all rules | Complete matches, bounded latency, no double firing |
| Priority-queue scheduling | World days, delayed emotions, Nemesis clocks | full per-tick scan | Correct ordering, bounded catch-up, no starvation |
| A* pathfinding | Ship hyperlanes and tactical grid with obstacles | BFS/Dijkstra as applicable | Optimal route under admissible heuristic; valid traversal |
| Influence maps | Faction control, threat, military/political pressure | direct territory score | Consistent diffusion and actionable consequences |
| ECS | Large numbers of world/spatial entities | current registry+state objects | Measured throughput/memory gain without ownership loss |
| HTN | Multi-stage political coup / faction campaign | GOAP/simple agenda | Clear decomposition, robust precondition recovery |

## Selection criteria
**Required invariants:** deterministic committed results for fixed seed/input/ruleset; no illegal writes; no hidden-state disclosure; valid actor knowledge; coherent replay; bounded cycles/time; clear evidence. Evaluate latency P50/P95, CPU/RAM, model calls/tokens, throughput, cognitive complexity, testing/observability, schema burden, migration cost, maintainability and DRY/SOLID boundaries.

**Experiment template**
```yaml
experiment_id: alg_goap_senator_v1
candidate: GOAP
scenario_fixture: fixtures/senator_plot_v1.yml  # proposed fixture location
baseline: fixed_plan_list
hypothesis: "GOAP recovers when location lead fails without invented intelligence"
seed_set: [1, 2, 3, 7, 11]
ruleset_version: pinned
world_snapshot_hash: pinned
metrics: [legal_transition_rate, plan_completion, false_knowledge_rate, p95_ms, model_calls, trace_completeness]
ablation: disable_candidate_keep_same_fixture
outcome: not_run
decision: undecided
evidence_refs: []
```
Each candidate must be evaluated alone and in integration. When combining GOAP+Utility+BT, define ownership: utility chooses goal, GOAP plans actions, BT executes local behavior, scheduler wakes actor, domain rules adjudicate, commit layer persists. No subsystem gains autonomous commit rights.

## Language/engine experiments
- Rust: useful for deterministic core and sandbox orchestration. Consider an embedded script API only after stable authority boundary.
- Lua/Luau: an optional sandboxable script language for authored local behavior/ruleset adapters; evaluate `mlua` compatibility and capability restrictions, panic/time budgets, determinism and replay. No unrestricted filesystem/network or state mutation.
- Python: Forge validation, generation, model orchestration; avoid placing mutable canonical state in multiple processes.
- JS/TS React/Tauri: presentation/projections and current runtime bridge; preserve existing source until measured migration justified.

**Do not require LoRA to do this evaluation.** Start with tools/skills + deterministic tests + structured prompts. Consider fine-tuning only after accumulating a clean, labeled corpus with train/eval splits and a demonstrated recurring task that tool calling/prompt/rules changes fail to solve.

## Gate
A candidate is **adopted** only after benchmark and UAT proof; **deferred** if no measurable gain; **rejected** if it breaks invariants. Keep decision/evidence log and revisit when game scale changes. Avoid premature global algorithm mandates.