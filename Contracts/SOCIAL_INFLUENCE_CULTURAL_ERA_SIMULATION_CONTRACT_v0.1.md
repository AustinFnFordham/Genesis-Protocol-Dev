# Genesis Protocol — Social Influence, Culture, and Era Simulation (SID-001)

**Date:** 2026-11-05  
**Status:** Proposed, owner review; not runtime-enforced or schema-ratified  
**References:** CIS-001, ALG-001, UAT-001, AMD candidate equations; `schema/Species.schema.json`; user-owned `BeforeTheFall.docx` (original rules); `Genesis_Protocol_Campaign_Genesis_Design_Specification.docx` (22-page expansion).

## 1. Purpose (function before math)
**Social Influence Dynamics (SID)** models how observable behavior, cultural norms, group expectations, institutional incentives, interpersonal influence, and individual convictions interact over world time **without assuming that common behavior is morally justified or that influence eliminates agency**.

**Five required phenomena:** imitation; conformity; resistance; internalization; cultural divergence. Additional dimensions: social stratification, socioeconomic conditions, leadership succession, migration, knowledge access, policy change, faction reputation, and historical adaptation.

**Output:** A causal, versioned *ERA state* for a culture, institution, region, faction, or population cohort; not one universal morality number. AMD remains the individual moral/behavioral subsystem. Knowledge/Belief determines who knows what; socioeconomics determines material pressures; SID aggregates and propagates social behavior; Chaos connects causal possibilities.

## 2. Scale and inheritance
1. **Species type** is biological/fictional classification, **not a uniform culture**. Species `cultural_features`, `cultural_significance`, `cultural_notes` exist in legacy `schema/Species.schema.json`; avoid silently changing these fields. Their content can link to cultural definitions but does not prove all species members share one ethic.
2. **Cultural reference** is a historically and geographically scoped set of norms, institutions, traditions, language, and source-backed descriptions. Forge may derive **candidates** from permitted lore and source books, with provenance and uncertainty. No AI-derived cultural value is authoritative absent validation/promotion.
3. **Local cohorts and institutions** carry population weights, social practices, social approval, exposure, power relations, socioeconomic access, and visibility. No per-citizen LLM calls.
4. **Individuals** inherit *context and exposure*, not forced beliefs. Most background NPCs use archetypes/cohorts. Named recurring actors may develop distinct convictions, personal memories, and goals. Promotions to named actors preserve existing source facts.
5. **Era state** is a time-sliced snapshot/ledger of institutions, demographics, resources, traditions, conflicts, alliances, adaptations, and source lineage. It evolves through accepted events, not an LLM deciding that a new age exists.

## 3. Functional inputs and outputs (notation is provisional)
`SID.evaluate(culture_id, cohorts, leadership, observed_events, knowledge_distribution, socioeconomic_state, world_delta, seed, ruleset_version)`
-> `{candidate_norm_changes, imitation_candidates, conformity_pressures, resistance_candidates, internalization_candidates, divergent_cohort_candidates, evidence, followup_jobs}`.

Cross-domain feeds: `F_AMD` (individual experience), `F_SOC` (social dynamics), `F_KNOW` (information), `F_ECO` (resources), `F_POL` (institutional decisions), `F_ENV` (hazards), `F_TIME` (scheduler). **Function signatures before formulas**; no arbitrary moral scalar mandated.

**Canonical symbol proposal:**
- `X_t`: complete world state at simulation step t; `X_{t+1}`: next step, not runtime complexity.
- `Δt`: fictional elapsed time. Event-driven ticks may have `Δt=0`.
- `N^c_{c,t}`: cultural reference norms for culture c at time t.
- `N^g_{g,t}`: group/cohort norms; `V_{i,t}`: personal convictions (only when authored/established).
- `B_{i,t}`: observed behavior; `K_{i,t}`: knowledge/beliefs; `R_{ij,t}`: relationship state; `E_{g,t}`: socioeconomic state.
- `θ_d`: calibration parameters for domain d; `ζ_i`: contextual appraisal outputs.
- `F_d`: explicitly registered domain update algorithm, not one global opaque function.

`O(k log n)` is the **performance objective for extracting/processing k due events from a priority queue of n pending jobs**, assuming O(log n) per heap operation and bounded per-job resolution; total costs include lookups, domain logic, and model calls. Benchmark heap scheduler vs periodic full population scan. This is **not** a guarantee for overall simulation complexity.

## 4. Actual Before the Fall basis: preserve its game mechanics
Original rules:
- Citadel and telescope; local map and galaxy map; factions with **forward motivation** and **hidden motivation**.
- Federation leadership, the Great Disaster deadline; resources classified **Abundant / Customary / Scarce**.
- Projects, one-faction community actions, discussions, Pitch In, sabotage, Scorn/Renown, discoveries and maps.
- Four season suits in card deck, one Joker in each season, King of Spades finishes game; cards offer two outcomes to choose from.
- Turn order: draw/reveal card, choose outcome, take action, annotate maps, update projects/resources/time, and chronicle consequences.
- Original Scorn/Renown rules are not equivalent to moral truth; the subsequent Campaign Genesis specification correctly proposes richer faction trust, resentment, obligation, legitimacy, public and hidden reputation.

**Simulation adaptation:** Preserve an **authentic playable chronology mode**, while a separate **headless UAT mode** supplies seeded event-card draws, virtual leader policies and deterministic checks. Do not silently substitute a uniform random disaster generator for the original deck/suit/Joker/King-of-Spades event system. If using non-deck random variables, label them as an *extended experiment*; keep the baseline fixture faithful.

## 5. Before the Fall headless experiment design
```yaml
experiment_id: sid_before_the_fall_leadership_v1
source_rules: BeforeTheFall.docx
mode: headless_uat
simulation_seed: 101
ruleset_version: pinned
setup:
  factions:
    - id: federation
      public_goal: save_population
      hidden_goal: test_owned
    - id: research
      public_goal: discover_habitable_world
      hidden_goal: test_owned
  resources:
    food: customary
    fuel: scarce
    medicine: abundant
  cultures: [baseline_ref_with_source]
  leadership_policies: [collaborative, opportunistic]
turn:
  event_card: seeded_deck_with_suits_jokers_king_of_spades
  leader_decision: from_legal_action_set
  validate: [motivation_consistency, knowledge, resources, authority, constraints]
  commit: [chronology_event, state_revision, map, resource_delta, project_delta]
measure:
  - imitation
  - conformity
  - resistance
  - internalization
  - cultural_divergence
  - scarcity_and_inequality
  - trust_and_institutional_legitimacy
  - faction_project_completion
  - reveal_of_hidden_motivation
  - historical_era_provenance
  - replay_equivalence
  - computation_cost
status: not_run
```
**Counterfactual tests:** same seed, swap faction leader/policy; same seed, change abundance to scarcity; same card, change group cultural reference; change who knows an allegation; remove an alliance; introduce famine; test whether results change only when causal conditions warrant. Also measure fair alternative policies and avoid hardcoding that disasters necessarily create evil, revolt or instability.

## 6. Required acceptance criteria
1. No event or social norm materializes without accepted cause and provenance.
2. Identical seed and actions produce identical chronological history and era state (versions pinned).
3. No population-wide model calls; cohorts first, promote named actors when relevant.
4. Individual disagreement and cross-cultural divergence are supported.
5. Cultural norms differ from ethical approval, private belief, and player agency.
6. Political policy propagates through material circumstances and knowledge channels, not omniscience.
7. Before the Fall original actions/cards remain playable and separable from automated simulator extensions.
8. No turn advances unbounded world time; performance benchmark targets `O(k log n)` **scheduler overhead**, not total universe compute.
9. Scorn/Renown are sourced legacy mechanics; a new reputation model is explicitly versioned rather than replacing them silently.
10. Output is a valid historical **ERA** with cultures, institutions, unresolved events, provenance, and inherited campaign hooks, not a forced predetermined story.

## 7. Open implementation gates
- Decide whether cultural definitions live in new `Culture` schema linked from Species, or a versioned six-layer identity architecture; preserve older cultural features on migration.
- Define group norm representation: descriptive prevalence, perceived approval, coercive pressure, actual institutional policy.
- Design faction-leader policy/agency selection rules and fairness constraints.
- Specify card/event dataset ingestion and copyright-aware source handling.
- Select and benchmark utility AI, GOAP/HTN, event-rule matching, and heap scheduling with ALG-001.
- UAT criteria for one original Before the Fall playthrough, one seed-replayed headless run, and one counterfactual leadership crisis.

**Decision status:** User has endorsed the *purpose and testing direction*; schemas, equations, implementation and acceptance results are not ratified merely by this document.


## 8. SID Design Interview Decisions (provisional; 2026-11-05)
**Question 1 — Initiator:** Owner selects **event-driven** cultural-change evaluation. Evaluate on accepted events (including media exposure, leadership/policy decisions, scarcity and contact as applicable), not a continuous automatic rewriting of cultures. Event type alone does not mandate change. Other actors/institutions affect transmission and response, and autonomous population behavior may be represented through accepted events.

**Question 2 — Conditions for enduring change:** Owner selects **combined, context-dependent evaluation**. Do not predetermine one driver (severity/duration, prior norms/cultural compatibility, social transmission and perceived approval, perceived practical effectiveness); evaluate these jointly at an appropriate level, with varying relevance by cohort, historical moment, and domain. Distinguish (a) externally enforced practice, (b) observed behavior, (c) perceived descriptive norm, (d) perceived injunctive norm, (e) private convictions, and (f) durable intergenerational tradition. Those may diverge rather than move simultaneously.

**Research caveats / UAT probes:**
- Gelfand, Gavrilets & Nunn, *Norm Dynamics* (Annual Review of Psychology 2024), doi:10.1146/annurev-psych-033020-013319 — ecology, historical context, social networks, transmission, mismatch, and persistence jointly shape norms.
- Giuliano, *Sticky Traditions* (NBER Working Paper 35125, 2026), https://www.nber.org/papers/w35125 — deeply rooted traditions may persist while some redistributive/prosocial attitudes shift faster; rates are domain-specific.
- Bicchieri & McNally, *Shrieking Sirens: Schemata, Scripts, and Social Norms* (2018), doi:10.1017/S0265052518000079 — events and social expectations are mediated by context, scripts, and learned interpretation.
- Meta-analysis of social norm appeals, *Human Communication Research* (2020), doi:10.1093/hcr/hqz023 — messaging effects often small and heterogeneous, so media exposure cannot automatically reprogram population convictions.

**Test requirements:** same crisis and duration, vary information reach, institutional trust, existing tradition, leader policy, material constraints, and cross-group network; allow compliance without internalization, durable practice without policy endorsement, resistance/backlash, and no change. No moral approval inferred from prevalence. Explicitly do not treat culture traits as immutable species attributes.

**Next design question:** What state layers must SID represent and preserve when responding to an event? No coefficient selection until functional requirements are signed off.


**Question 3 — Cultural state representation (provisional; owner response 2026-11-05):** Owner selects **D: full layered cultural state**, with a critical caveat: track layered cultural states separately, then **derive changes algorithmically** from context, historical baseline, exposure, leadership behavior and interactions. Cultural response must not be selected in advance by narrative labels. In particular, exposure to a violent leader may intensify existing hostility in some communities while causing resistance, unrest, fragmentation or institutional transformation in previously anti-violence societies. These are **test hypotheses, not inevitable transitions**: any culture may respond in multiple ways depending on its institutions, knowledge, material incentives, coordination capacity, sanctions, and individual variation. Do not automatically equate leadership violence with anarchy, or hostility with one monotonic numerical axis. Preserve distinct layers: policy/institutional rules, publicly observable practice, descriptive expectations, perceived approval, private convictions (cohort estimates or individually established), transmission, and historical memory. Keep source baselines separate from simulated revisions; retain event provenance and evidence to distinguish compliance from internalization. **Mathematics deferred** until function/acceptance criteria are specified.


**Question 4 — Unit of influence (provisional; owner response 2026-11-05):** Owner selects **adaptive multiscale simulation**: civilizations, institutions/factions, communities, cohorts and individuals are represented at different resolutions. Increase detail when a person/group/event becomes consequential. Individual disagreement is valid and need not alter aggregate culture; coordinated recruitment and collective action can turn personal dissent into organized factions, espionage, sabotage, infiltration, ranks, resistance or reform, with either positive or negative consequences. The simulation must model discovery/coordination/mobilization pathways rather than turning every dissenter into an automatically effective movement. Character autonomy and individual dissent persist even without group-level effects.

**Correction to historical continuity principle:** Increasing resolution must preserve **established historical events, dated facts, prior decisions, and provenance**, not freeze **personality, opinion, or culture**. A person born during/after a cultural shift will typically have a different formative context than someone born before it; people alive during transitions may change attitudes, loyalties, practices and identities through experience. Neither demographic membership nor historical era guarantees conformity. At resolution promotion, do not retcon established individual facts; where no individual facts exist, infer only plausible initial distributions conditioned on birth cohort, exposure, personal history and current society, and mark generated details as newly established. Track generational formation and lifecycle change distinctly from changes in observational resolution.

**Acceptance scenarios:** (1) lone dissenter remains isolated and does not affect group policy, (2) like-minded individuals build a network and may mobilize a faction, (3) infiltrating a powerful institution produces downstream changes if successful, (4) recruitment effort can fail or trigger backlash, (5) two generations in the same place carry different formative cultural baselines, (6) the same individual's convictions can legitimately evolve without falsifying earlier events. Defer math and thresholds until the collective-action pathway is specified.

**Next question:** What should qualify as effective collective action or faction emergence: mere shared opinion, coordinated intent, shared resources/communication, public actions, or a context-specific combination?
