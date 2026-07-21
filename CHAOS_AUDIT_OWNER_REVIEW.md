# CHAOS ENGINE — RULE AUDIT FOR OWNER REVIEW (2026-07-20)

Per the Unified Directive: **no Chaos rule activates until audited and owner-approved.** Chaos proposes; the Steward validates; Atomic commits. This sheet inventories every existing rule and its gaps against the required contract (schema validation, namespaced tags, explicit predicates/exclusions, priority, persistence, idempotency, provenance, deterministic fixtures).

## Inventory (6 baseline rules in `src/state/chaos.js` + registry SynergyRules)

| # | rule_id | trigger | consequence | gaps vs contract |
|---|---|---|---|---|
| 1 | chaos_canister_phase1_chatter | world_phase_advanced + flag canister_ignited + phase=1 | journal breadcrumb | tags not namespaced; no idempotency key; no fixture |
| 2 | chaos_canister_phase2_footage | …phase=2 | journal breadcrumb | same |
| 3 | chaos_canister_phase3_hunter_hired | …phase=3 | spawn_nemesis (nemesis_unknown_actor) | same + spawn payload embeds entity (should reference a template URID) |
| 4 | chaos_canister_phase5_transponder | …phase=5 | journal breadcrumb | same |
| 5 | chaos_canister_phase6_reveal | …phase=6 | reveal_nemesis (patch batch) | same + patch batch inline (should be consequence template ref) |
| 6 | chaos_wanted_obligation_tick | world_phase_advanced + wanted≥1 | obligation_tick | same; idempotent per phase only by accident |
| 7 | SynergyRules registry placeholder (`sandbox_rule_id`) | empty trigger | none | placeholder — recommend deprecation |
| 8–14 | *(reserved: no further executable rules found in gold/sandbox; the "14" from earlier audits counted per-file synergy blocks in wip entities — those are deprecated by SynergyRules.schema and were never executable)* | | | recommend formal deprecation record |

## Recommendation (requires owner signature — NOT self-approved)
1. Rules 1–6: normalize to `genesis.chaos.canister_chain.v1` + `genesis.chaos.obligation_pressure.v1` as SynergyRules entities with namespaced tags (`world.phase`, `campaign.flag.canister_ignited`), explicit predicates, `idempotency: once_per_phase`, provenance `origin: design_doc_butterfly_effect`, and one deterministic fixture each (seeded phase-march replay).
2. Rule 7: deprecate.
3. Per-file synergy blocks in wip: mark `deprecated_by: SynergyRules.schema` during forge migration; never promote.
4. Until signed: baseline rules remain active ONLY in the legacy client worldPhase path (pre-GM campaigns); the four-controller runtime consults no Chaos rules yet — so activation-by-default is already prevented on the GM path.

## Open owner gates (unchanged, awaiting your decisions)
disposition_of_the_14_existing_chaos_rules (this sheet) · canonical_romance_stages · complete_force_overcast_contract · hideout_economy_balance · droid_customization_batch_validation
