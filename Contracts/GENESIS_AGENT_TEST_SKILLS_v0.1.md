# GENESIS — Agent Skills for Gameplay Engineering and UAT (SKL-001)
**Version:** 0.1.0 | **Status:** proposed skill catalog, not installed/running | **Date:** 2026-11-03
**Parents:** AAS-001, HRM-001, ALG-001, UAT-001; existing Genesis Lookup, Rules Lawyer, Runtime Steward concepts.

## Why skills first, not LoRA
A skill is a bounded repeatable workflow: instructions, permitted read tools, output schema, evidence requirements and test fixtures. It can be executed by an existing model or deterministic service. A LoRA is a weight adaptation, not an authority gate or a substitute for exact retrieval. Start with prompt/skill/tooling; collect labeled failures; train only if evaluations demonstrate persistent behavior gaps despite good rules and tools.

## Skills and minimum contracts
| Skill | Input | Tools / logic | Output | Forbidden |
|---|---|---|---|---|
| **Genesis Lookup** | question, scope, campaign, actor | registry, graph, temporal/vector candidates, dereference | sourced evidence pack | promote vector match into canon |
| **Intent Parser** | player text, scene | constrained classification + clarifying rules | typed action candidates, ambiguity | mutate world |
| **Rules Lawyer** | typed intent, actor, ruleset | exact feature/ability lookup, precondition engine | legal/reject, rule refs, dice request | fabricate powers or rolls |
| **Combat Adjudicator** | legal combat action, context | combat machine, seeded dice, effect resolver | effect proposal + trace | bypass resource budget |
| **Progress Keeper** | XP/level/feature intent | progression rules and prerequisites | legal progression patch proposal | grant features from narrative |
| **Chaos Examiner** | accepted event, scoped context | taxonomy, typed edges, declarative predicates | candidate causal effects + source facts | direct mutation, ghost edges |
| **Actor Planner** | actor's beliefs/goals/resources/time | utility+GOAP/HTN experiments; scheduling | candidate plan and next due job | use omniscient info |
| **Runtime Steward** | full adjudication trace | schema/authority/visibility/revision/replay checks | approve/reject + reason and owning layer | ignore failed checks |
| **UAT Scenario Generator** | domain and variations | template + metamorphic/property-based case synthesis | isolated fixture plans | use runtime fixtures as Gold |
| **Replay Auditor** | snapshots, ledger, seed, rules version | deterministic rebuild, hashes, lineage graph | divergence report | infer success from prose |
| **Narrative Fidelity Auditor** | events, world/actor knowledge, draft prose | citation cross-check, forbidden fact diff | allowed narrative + errors | voice player or invent consequence |
| **Benchmark Analyst** | repeated labeled runs | scoring/ablation statistics | algorithm selection record | recommend from anecdote alone |

## Skill artifact contract
Each skill must eventually have a versioned `SKILL.md` or equivalent manifest with: ID, purpose, input schema, output schema, allowed data scopes/tools, authority restrictions, prerequisites, deterministic checks, error modes, latency/model budget, trace format, test cases, and maintainers. The skill must state **whether it runs deterministic code or model reasoning**, with no hidden promotion rights.

## Proposed first implementation tranche
1. Genesis Lookup + Rules Lawyer + Runtime Steward with *read-only* evidence traces.
2. UAT Scenario Generator + Replay Auditor to generate and validate repeatable fixtures.
3. Chaos Examiner and Actor Planner after CIS rule/schema and scheduler gates are tested.
4. Narrative Fidelity Auditor for litRPG campaign-to-novel flow.
5. Benchmark Analyst for algorithm comparisons and later targeted fine-tuning decision.

## Training decision gate
Only consider LoRA/SFT if: (a) enough legally usable examples exist, (b) high-quality labels and held-out scenarios exist, (c) baseline tools/retrieval/state-machine implementation is stable, (d) model behavior—not missing truth—is the failure, and (e) improved model actually beats the baseline on unchanged tests. Keep rules, IDs and authority outside weights. No model can become the authoritative ledger.

**This is a design catalog; agent skills were not created or installed by this document.**