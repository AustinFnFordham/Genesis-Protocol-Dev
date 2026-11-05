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


**Question 5 — Emergence of collective action (provisional; owner response 2026-11-05):** Owner chooses **progressive organizational development**. SID must separately represent isolated dissent, interpersonal alignment, intentional coordination, organized cells/networks and operationally capable factions. This is **not** a mandatory linear ladder: existing institutions can split abruptly, a tiny cell may be high-leverage, large movements may remain ineffective, loose networks may persist, and mobilization may stall or reverse. Distinguish social membership, organization, resources, institutional access, legitimacy, cohesion, visibility, risk of detection, and realized influence. Do not conflate shared opinion with organization or headcount with power. Individual preferences can remain private and never produce social change. Model organization, infiltration, sabotage and espionage as consequential outcomes via permitted actor actions and constraints; do not auto-grant them to dissenters. Preserve actor agency, event provenance, and causal history. Outcomes may include successful reform, repression, fragmentation, capture, backlash, or no change. Math and transition thresholds remain deferred.

**Unrelated user-pasted Claude gameplay update:** Ammunition Points, Bounty Hunter licensing, new skill proposals and Vigilance initiative/surprise effects were pasted along with the owner's Q5 selection. These are **not** stated SID requirements and are not approved by Q5. Keep those ruleset decisions in a separate gameplay/content workstream.

**Next design question:** What exactly enables social influence to travel between people and groups (personal ties, institutions, mass media, reputation, resource dependence, coercion, etc.), and how should exposure differ from belief change?


**Question 6 — Influence propagation (provisional; owner selection 2026-11-05):** Choose a **multichannel influence network**. Personal ties, institutions, mass media and entertainment, rumor, economic dependencies, authority, coercion, and reputation may all convey distinct signals to different recipients. Retain network source/channel, recipient exposure, timing, and provenance; do not equate message reach with belief adoption. Distinguish exposure, interpretation/comprehension, perceived credibility, private conviction, public compliance, and mobilization, but do **not** assume these are obligatory or strictly ordered steps (fear-induced compliance can precede belief, misunderstanding can propagate, repeated trusted reinforcement can change adoption likelihood, and recipients may remain unmoved). Recipients can simultaneously belong to multiple competing social networks and reject otherwise trusted sources on individual claims.

**Research-informed cautions:** Centola and Macy (2007), *Complex Contagions and the Weakness of Long Ties*, doi:10.1086/521848, distinguish broad information reach from behaviors requiring reinforcement by multiple ties. Cialdini, Kallgren and Reno (1991), *A Focus Theory of Normative Conduct*, doi:10.1016/S0065-2601(08)60330-5, distinguish descriptive, injunctive, and personal norms; hearing what many people do does not necessarily communicate what the recipient believes should be done. These motivate evaluation cases, not fixed universal effects.

**Acceptance scenarios:** wide holonet reach but low credibility; narrow highly trusted network mobilizes participants; simultaneous contradictory official and interpersonal sources; coercion produces public behavior with unchanged private conviction; misinformation spreads without comprehension; social reinforcement produces delayed change; complete nonresponse is valid. Keep channel weights and network structure undecided until later design/math phase.

**Next interview question (Q7):** How do individual and group members adjudicate conflicting influences—source trust, corroboration, identity alignment, material consequences, personal autonomy, and uncertainty?


**Question 7 — Contextual conflict resolution (provisional; owner selection 2026-11-05):** SID must handle simultaneous contradictory influences by taking into account source-specific trust, evidence/corroboration, existing convictions and identity, institutional coercion and incentives, personal relationships, prior experience, access to alternatives, and uncertainty. Outcomes may diverge between professed loyalty, private belief, overt behavior, covert information-gathering, and collective action. No hardcoded source priority or automatic alignment from birth cohort, species, media exposure or institutional role. NPC motivations and private conclusions must be derived from established state and later events; PC agency is never overwritten. Keep SID's social information/pressure evaluation distinct from AMD's appraisal of moral conflict and psychological consequences; allow typed events to connect them without conflating them.

**Related rules-design observation (not a SID mechanic or approved ruling):** User appended Claude's proposed Vigilance d20 check: versus 10 + enemy best Stealth modifier; failure +2 initiative and natural 1 -4; success no specified initiative modifier. User specifically requests review of better mathematical design for failure, FFG-like narrative consequences and psychological appraisal, while continuing SID interview without finalizing any math. Separate check result (detected ambush/avoided surprise), combat consequences (initiative), narrative complications (independent of success), and AMD appraisal (threat, confidence, trust, salience, interpretation). Do not treat a natural 1 as forced fear/trauma, do not reward ordinary failure with an intrinsic mechanical bonus without a design rationale, and audit probabilities for proficiency, modifiers, edge outcomes and multiple adversaries before approving. FFG Advantage/Threat and Triumph/Despair demonstrate orthogonal narrative outcomes (FFG official overview: https://www.fantasyflightgames.com/en/news/2013/6/18/running-the-galaxy/). Psychological appraisal is individually variable and should not be inferred directly from a die result (Kilby et al. 2018, https://doi.org/10.1016/j.paid.2018.07.001). No Vigilance numbers or AMD coupling adopted in this contract.

**Next interview question (Q8):** Which categories of consequences should be generated by social/information events and where are subsystem boundaries (immediate action, individual appraisal, social transmission, faction response, longer-term institutional/ERA change)? No formula design yet.


**Question 8 — Causal orchestration and bounded ownership (provisional; owner selection 2026-11-05):** Choose **event-driven orchestration with bounded subsystem ownership**. An accepted event causes dispatch to eligible evaluators, which generate typed proposed changes only for fields they own. A dependency-aware consequence/orchestration layer validates event provenance, visibility and causal reach, authority, conflicting writes, and ordering; canonical updates occur only after appropriate validation and ledger commit. SID may update social exposure, expectations, influence and mobilization state; AMD owns moral/psychological appraisal; knowledge/epistemic systems own who knows or believes evidence; Chaos owns typed entity relationships; factions/institutions own policy and institutional state. These roles are initial ownership proposals for future review, not authorization for cross-layer writes. Dissent, trust and other shared concepts must have exactly one authoritative field owner with cross-subsystem references or derived views, not duplicated mutable copies. Hidden/unknown facts do not affect uninformed actors until a causal information path reaches them. One event may produce zero or multiple changes, and some effects can be delayed. Prevent circular same-turn feedback and double-counting. PC intent/actions never synthesized by SID. Need to specify conflict handling, retries, idempotence and event time semantics before implementation.

**Requested single illustrative umbrella expression, not finalized mathematics:** X_{t+1}=Commit_ledger(Validate_authority(Resolve_dependencies(X_t, {F_i(X_t, View_i(E_t,K_t,G_t), theta_i)}_{i in Eligible(E_t)}))), where X is authoritative world state, E accepted event(s), K knowledge/provenance, G social/causal graph, View is visibility-filtered input, F_i proposed changes from domain owner i (SID, AMD, Chaos, faction/economy etc.), and Commit is an atomic append-only state transition. Functions and parameters are placeholders, not calibrated equations or an agreed evaluation order.

**Next interview question (Q9):** How should Genesis adjudicate multiple eligible subsystem proposals when they conflict or form causal dependencies within the same event (priority/fixed ordering, two-phase snapshot, dependency graph, authority adjudicator)? Keep this as functional behavior, not formulas.


**Question 9 — Hybrid transactional orchestration (provisional; owner selection 2026-11-05):** Evaluate an accepted event using a consistent pre-event snapshot and visibility-filtered inputs, explicit domain ownership and causal dependency graph, bounded follow-on events, validations, and atomic ledger commit. Distinguish evaluation phases from irreversible state writes; the next wave sees an accepted updated snapshot, not concurrent uncommitted proposals. Same-event causal chains require explicit intermediate dependency resolution or queued child events, never invisible circular re-evaluation. Include deterministic replay inputs, idempotency keys, rejection records, and conflict resolution by field ownership. Guard against knowledge leakage, invented NPC/PC actions, simultaneous contradictory proposals, double-counting of rumor/consequence, and unbounded propagation.

**Owner's mathematical presentation requirement:** Display the orchestration equation **fully expanded with actual known nested formulas** including numerators and denominators, not merely named F_i blocks. Show known preliminary AMD components (risk, dissonance, stress, normalization, historical baselines, target, gradient step) as genuinely proposed math; mark SID, knowledge routing, relationship updates, faction/economy functions as **unformulated and under interview**, not fabricated coefficients. Do not confuse the AMD gradient denominator with a population or belief-update denominator. Do not finalize any numerical parameters at this stage. Illustrative nested mapping may use explicit placeholders such as F_SID^TBD and domain views. The equation must represent proposal/validation/atomic commit rather than summing independently mutable global states. Later math interviews should define precise variables, units, update triggers and conservation/safety properties before parameter estimation.

**Next question Q10:** When should follow-on consequences materialize—immediately within one transaction, deferred event queue using explicit in-world latency, or hybrid based on causal prerequisites—and what historical order must be preserved?


**Question 10 — Hybrid temporal and causal scheduling (provisional; owner selection 2026-11-05):** A committed event may produce (a) immediate, validated consequences, (b) future scheduled evaluations that require elapsed fictional time, and (c) dormant condition-dependent evaluations activated only when causal prerequisites hold. A scheduled evaluation is **not** a precommitted outcome. Define event time vs discovery/observation time vs processing/commit time. Any event-triggered child work requires parent provenance, deterministic idempotency key, causal reach, earliest-eligible fictional time and visibility/knowledge boundaries. Prevent backwards causation, duplicate application, feedback loops, acting on future evidence, guaranteed revolutions from famines, and decisions preempting player agency. Time skips must process due events in causal order or provide an auditable aggregated equivalent; cancellations and changed prerequisites must invalidate or reconsider pending jobs rather than blindly committing them. Delayed consequences may be zero. Avoid estimating calendar-time durations or hazard coefficients until domain and UAT definitions are reviewed.

**Q10 contradiction checks to test:** (1) A rumor scheduled to spread tomorrow cannot influence uninformed leaders today; (2) famine triggers a later unrest evaluation, but relief shipment removes the conditions and no protest may occur; (3) simultaneous event proposals are ordered by dependencies with an explicit tie-break policy; (4) two observers discover the same incident at different times without altering the original occurrence; (5) one child event cannot be duplicated on retry; (6) a time skip does not skip meaningful previously queued events; (7) an offscreen region may evolve without rewriting committed facts or asserting unseen decisions as player choices.

**Next interview question Q11:** How should Genesis simulate offscreen societies and fast-forward periods with sparse observations: always process every event, use validated cohort/aggregate summaries, focus on consequential hotspots, or adaptive resolution with reconciliation when brought into view? No mathematical coefficients yet.


**Question 11 — Adaptive historical resolution (provisional; owner selection 2026-11-05):** Preserve detailed simulation for committed historical facts and consequential actors, while evolving offscreen background populations at coarser, auditable resolution. When regions or people become consequential, instantiate greater detail without retconning accepted events, established NPC biography, relationship histories, demographic totals, resource balances or in-world temporal order. Cohort distributions are conditional context, not destinies for individual beliefs. Persist sufficient provenance/uncertainty, random seeds and cohort constraints for replay and refinement. Maintain consistent population flows (births/deaths/migration) and avoid double counting actors who move between explicit and aggregate representations. High-resolution events can affect offscreen aggregates and vice versa only via legitimate dated causal paths. The system must not claim exact unobserved biographies from aggregate data.

**Owner's calibration caveat:** Existing AMD coefficients are hand-set hypotheses. Because the ledger is append-only with saved event inputs, revised coefficients can be tested against reconstructed historical events before play. Distinguish (1) fixed-input counterfactual replay for sensitivity analysis, which holds observed events constant; (2) full branch simulation from an earlier checkpoint, where different parameter choices can change subsequent events and must not overwrite actual committed history. Store versioned parameter sets, initial states, seeds/random draws, known exposure views, and snapshots; compare to predeclared measures, held-out cases and acceptance scenarios. Reproducibility alone does not empirically validate coefficients. ABM calibration and sensitivity analysis should consider heterogeneous agent detail and parameter identifiability (Thiele et al. 2014, doi:10.18564/jasss.2503; Olukan et al. 2026, doi:10.18564/jasss.5872).

**Owner's AMD overlap concern:** Proposed responsibility R = H(0.5 I + 0.3 P + 0.2 PC) counts foreseeability both alone and in interaction with control. This may be an intentional interaction, but the arbitrary 0.5/0.3/0.2 weights are not independently interpretable as isolated contributions. No correction chosen. In the math-design phase, inspect semantic overlap, monotonicity and boundary cases, correlation/multicollinearity, and outcomes with P=0, C=0, I=0; compare additive, interaction-based and hierarchical alternatives against ethics/behavior scenarios before coefficient selection.

**Question 11 evaluation cases:** offscreen population events cross one another; a named NPC grows older through the skip; an emerged individual is removed from cohort statistical accounting without double-counting; same initial state + seed + parameter version reproduces replay; a counterfactual branch with different coefficients never silently rewrites canonical history; changes in simulation granularity cannot fabricate or erase politically consequential past events.

**Next question Q12:** When promoting aggregate/cohort histories into named NPCs or detailed communities, which individual facts are fixed, which must be generated consistently, and which remain unknown until observed/interacted with? This establishes commitments and epistemic boundaries before algorithms.


**Question 12 — Historically constrained progressive identity (provisional; owner selection 2026-11-05):** An abstract/cohort member promoted to a named individual must receive a coherent, persistent identity baseline grounded in the time-and-place-specific societal state, established ancestry/heritage, relevant life history, existing obligations, and applicable event consequences. Details may be progressively authored as causal encounters require, but established hidden facts must persist and may not be retconned merely to fit a later plot. Do not assume that a demographic label determines personal opinion or that a newly created NPC has already taken specific unobserved consequential actions. Distinguish: (1) irrevocably established historical facts, (2) established-but-not-player-known facts, (3) uninstantiated or uncertain facts constrained by history, (4) mutable traits/relationships updated only through accepted events. An NPC may potentially become friend, enemy, or neither; early generation must preserve all three possibilities without guaranteeing an outcome.

**Owner's family-tree consideration:** Kinship and familial networks are potentially high-value anchors for identity, inherited beliefs, obligations, social access and faction recruitment. Do **not** require exhaustive genealogical materialization for every individual. Model a sparse, canonical kinship graph with known relationships, generation/birth timing and legal/biological/adoptive relationship types where relevant; unresolved relatives may be represented as explicit unknowns or bounded placeholders rather than fabricated named canon. Resolve new people and relationships on demand with constraints (birth/death chronology, known ancestry, population accounting, pre-existing canonical relationships and sources). Never insert ghost edges with absent canonical targets; instead queue unresolved relationship proposals until valid endpoints are materialized. Avoid copying cohort-average personality into individuals.

**Q12 UAT probes:** a named person can later become ally or opponent through events; kinship reveals a plausible link without contradicting established lineage; secrets stay stable after NPC re-encounter; two individually instantiated siblings do not contradict a prior parent record; genealogical details not committed remain unknown rather than being retroactively claimed as decided; faction infiltration requires actual actions and access; promotion of an individual from aggregate state does not double-count population.

**Next interview Q13:** Which identity elements need to be committed at first instantiation, which can remain undecided, and what degree of relational/family scaffolding is necessary? Functional policy before any mathematics.
