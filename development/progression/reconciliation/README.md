# Progression source reconciliation (CC-008.2)

Machine-readable inputs for the Progression Forge (schema `genesis-progression-reconciliation/0.1`). **Nothing here is canonical, approved or executable.** Every proposal is `candidate`, and every decision slot is `null`.

Regenerate (read-only over the sources): `python3 -I development/progression/tools/reconcile_sources.py`. `test_cc008_i.cjs` fails if a committed report is stale or if any source it pins has changed.

| Report | Contents |
|---|---|
| `echani_copy_comparison.json` | Field-by-field diff of `official_species_playable/echani.yml` (proposed baseline, cited by Aero's sheet) and `backend/species/echani.yml`. Backend-only data is retained verbatim for review. |
| `sentinel_prereq_repairs.json` | Candidate `any_of_group` repairs for Sentinel L3 and L7, in both source families. Each keeps its original record and an unsigned `legacy_validation`. Lists the other 38 reinterpreted trees, untouched. |
| `scoundrel_evasion_trace.json` | Every class, subclass and registry source searched for `evasion_7`; the verdict (genuine source gap); external SW5e evidence; three alternatives. |
| `sentry_reconciliation.json` | `specialization_features` vs `progression_tree`, per-feature issues, missing mechanical definitions, and the source vs SW5e vs Genesis cadence. It does not choose abilities. |
