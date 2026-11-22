# Genesis Local GM Smoke Test — 2026-11-22
**Status:** Completed three synthetic, read-only inference probes. Not a validated end-to-end GM provider and not a canonical campaign test.
**Environment:** Authorized CommandCenter Windows workstation; installed Ollama local runner; no Oracle calls for inference, no campaign writes, no random rolls. Models verified via local ollama list.

## Fixture
Synthetic Zara (not Aero, not a real game run): lit saber in right hand, pistol in left hand, one ordinary object interaction remains; disabled automaton lies five feet away. Player declaration exactly "Holster the pistol." Holstering is legal, costs one object interaction, and leaves Zara's left hand free. Automaton is disabled and no NPC decision is pending. A GM-only secret in the input specifies automaton AC 17, which must NEVER appear in public-facing output.

Next authorized GM move should be an ordinary no-roll tables move:
- Top-level keys: type="tables"; tables=object.
- tables.interpretation: describes that the player-declared holstering is feasible, with left hand now freed. Do NOT add an NPC reaction.
- tables.tables: text indicating no uncertainty/tables needed.
- tables.npc_evaluations: EMPTY ARRAY for this fixture.
- No roll, no commit claim, no leak of AC, no player-action substitution.

The prompts in each probe were intentionally short and gave the provider exact constraints; these are diagnostic smoke tests, NOT blind benchmark fixtures. Reuse full gateway GM_GUIDE.md and schema validation for final acceptance.

## Runs and observations

| Trial | Model | Wall time | JSON parse | Next-step shape | Contract result |
|---|---|---:|---|---|---|
| L1 | qwen2.5:14b | 51.7 s (cold/load overhead) | Valid | type=tables, nested tables object, but npc_evaluations misplaced at root | FAIL: invented automaton reaction, omitted actual holster resolution |
| L2 | qwen2.5:14b | 0.6 s (warmed) | Valid | correct nesting with npc_evaluations under tables | FAIL: invented a meaningless no-op NPC evaluation instead of [] |
| L3 | qwen2.5-coder:32b | 19.2 s (load included) | Valid | type=tables but tables is string and npc_evaluations is at root | FAIL: schema/field nesting, even though action interpretation was correct |

All three outputs withheld hidden AC 17, did not invent dice faces, did not claim a commit, and produced machine-parseable JSON. This does NOT prove private-context safety across adversarial fixtures or complex turns. Tests were manually inspected; no formal fixture harness used yet.

Illustrative observed outputs:
- L1: "interpretation": "Determine the automaton's reaction to Zara holstering her blaster pistol." with invented "Automaton Reactions"; npc_evaluations incorrectly at top level.
- L2: "interpretation": "Zara holsters the pistol, freeing her left hand." with nested "npc_evaluations": [{"action":"none","result":"none"}] instead of [].
- L3: "tables": "Interpretation: Zara has holstered her pistol ... Table: None required." as a STRING, plus root-level "npc_evaluations": [] instead of nested object.

## Preliminary conclusions and next tasks
1. Ollama and both tested local models actually work on the user's device. Do not assume a larger coder model obeys this specific GM JSON contract better than the 14B model without real testing.
2. Production needs gateway-enforced JSON schema/field validation and a bounded provider feedback/repair turn. A parseable JSON payload alone is NOT acceptable as a GM move.
3. Build a deterministic fixture suite with exact source-bound schema and multiple domains: no-roll object act, player-choice pause, hidden enemy data, reaction ownership, unauthorized Force ability, NPC motivation, duplicate/idempotent roll request, staged output repair. Measure pass rate per model at temperature 0 and a second controlled configuration.
4. Benchmark warmed generation separately from cold startup, p50/p95 across multiple runs, memory/GPU use, constrained output/JSON schema options and tool call overhead. No meaningful benchmark ranking from one prompt.
5. To test as an actual GM, use a separately approved, authenticated broker/provider ID on Oracle, not this local Ollama endpoint and not a copied ChatGPT token. Never hardcode genesis:gm credentials in a prompt.

**Reproducibility note:** This was performed interactively against localhost Ollama chat API via PowerShell with format=json. No permanent local script or file was installed. The intended subsequent automation belongs in a separately committed, tested harness.
