/* GEN-CHAOS-001 — THE CHAOS ENGINE: a generic matcher over SynergyRules data.
 * The Chaos Engine writes NOTHING. It consumes accepted event envelopes,
 * matches them against SynergyRules-shaped data (trigger tags: AND / _any:
 * OR / _exclude: NOT; trigger_event; conditions), arbitrates by
 * Specificity → Exclusion → Priority, and emits CANDIDATE CONSEQUENCES that
 * the OWNING engines execute through dispatchEvent under their own authority.
 * The fuel-canister incubation chain lives below as pure data — worldPhase.js
 * no longer hardcodes it. Per-phase budget caps prevent consequence storms. */
import { useGenesis } from './store.js';

/* ---------------------------------------------------------------- *
 * THE RULES — SynergyRules-shaped. These belong in the forge as
 * SynergyRules gold entities; this array is the runtime projection
 * (loaded from registry when SynergyRules instances exist, with
 * these as the seeded baseline).                                    *
 * ---------------------------------------------------------------- */
export const BASELINE_RULES = [
  // —— THE FUEL-CANISTER INCUBATION CHAIN (was hardcoded in worldPhase.js) ——
  {
    rule_id: 'chaos_canister_phase1_chatter',
    priority: 50,
    trigger: { trigger_event: 'world_phase_advanced', conditions: { flag: 'canister_ignited', phase_equals: 1 } },
    mechanical_effect: {
      consequence: 'journal_breadcrumb', owner: 'nemesis_engine',
      payload: { kind: 'nemesis', text: 'Chatter on the local net: someone is asking about the fire in the lower levels.' },
    },
  },
  {
    rule_id: 'chaos_canister_phase2_footage',
    priority: 50,
    trigger: { trigger_event: 'world_phase_advanced', conditions: { flag: 'canister_ignited', phase_equals: 2 } },
    mechanical_effect: {
      consequence: 'journal_breadcrumb', owner: 'nemesis_engine',
      payload: { kind: 'nemesis', text: 'A dockside broker was seen paying for security footage of your landing pad.' },
    },
  },
  {
    rule_id: 'chaos_canister_phase3_hunter_hired',
    priority: 60,
    trigger: { trigger_event: 'world_phase_advanced', conditions: { flag: 'canister_ignited', phase_equals: 3 } },
    mechanical_effect: {
      consequence: 'spawn_nemesis', owner: 'nemesis_engine',
      payload: {
        urid: 'nemesis_unknown_actor',
        breadcrumb: { kind: 'nemesis', text: 'A docking official mentions someone was asking about your Wookiee. They paid well.' },
        doc: {
          id: 'nemesis_unknown_actor', name: 'UNKNOWN ACTOR', classification: 'shadow_node',
          archetype: 'blood_feud',
          grudge_origin: 'The Guardian ignited the fuel canister. The fire took everything I loved.',
          progression_stage: 'emergence', threat_level: 2, revealed: false, tracking_target: null,
        },
      },
    },
  },
  {
    rule_id: 'chaos_canister_phase5_transponder',
    priority: 50,
    trigger: { trigger_event: 'world_phase_advanced', conditions: { flag: 'canister_ignited', phase_equals: 5 } },
    mechanical_effect: {
      consequence: 'journal_breadcrumb', owner: 'nemesis_engine',
      payload: { kind: 'nemesis', text: 'Your ship’s transponder pinged a registry it never contacted. Someone bought your route history.' },
    },
  },
  {
    rule_id: 'chaos_canister_phase6_reveal',
    priority: 70,
    trigger: { trigger_event: 'world_phase_advanced', conditions: { flag: 'canister_ignited', phase_equals: 6 } },
    mechanical_effect: {
      consequence: 'reveal_nemesis', owner: 'nemesis_engine',
      payload: {
        urid: 'nemesis_unknown_actor',
        breadcrumb: { kind: 'nemesis', text: 'THE HUNTER REVEALS: Kaelen, the Ash-Blind. "I was a moisture farmer. Until a Wookiee decided a fuel canister was worth more than my family."' },
        patches: [
          { op: 'replace', path: '/name', value: 'Kaelen, the Ash-Blind' },
          { op: 'replace', path: '/revealed', value: true },
          { op: 'replace', path: '/progression_stage', value: 'confrontation' },
          { op: 'replace', path: '/threat_level', value: 5 },
        ],
      },
    },
  },
  // —— Obligation pressure while wanted ——
  {
    rule_id: 'chaos_wanted_obligation_tick',
    priority: 20,
    trigger: { trigger_event: 'world_phase_advanced', conditions: { wanted_min: 1 } },
    mechanical_effect: { consequence: 'obligation_tick', owner: 'providence_engine', payload: {} },
  },
];

const PHASE_BUDGET = 6; // max consequences per triggering envelope (storm cap)

/* ---------- tag/condition matching (SynergyRules semantics) ---------- */
function tagsMatch(trigger, envTags) {
  const has = (t) => envTags.includes(t);
  if (trigger.actor_tags && !trigger.actor_tags.every(has)) return false;          // AND
  if (trigger.actor_tags_any && !trigger.actor_tags_any.some(has)) return false;   // OR
  if (trigger.actor_tags_exclude && trigger.actor_tags_exclude.some(has)) return false; // NOT
  return true;
}
function conditionsMatch(cond, { campaign, phase }) {
  if (!cond) return true;
  if (cond.flag && !campaign?.flags?.[cond.flag]) return false;
  if (cond.phase_equals !== undefined && phase !== cond.phase_equals) return false;
  if (cond.phase_min !== undefined && phase < cond.phase_min) return false;
  if (cond.wanted_min !== undefined && (campaign?.wanted_level ?? 0) < cond.wanted_min) return false;
  return true;
}
function specificity(rule) {
  const t = rule.trigger ?? {};
  return (t.actor_tags?.length ?? 0) + (t.target_tags?.length ?? 0)
    + Object.keys(t.conditions ?? {}).length + (t.trigger_event ? 1 : 0);
}

/** Deterministic arbitration: Specificity ↓, Exclusion presence ↓, Priority ↓, rule_id ↑. */
function arbitrate(rules) {
  return rules.slice().sort((a, b) =>
    specificity(b) - specificity(a)
    || ((b.trigger?.actor_tags_exclude ? 1 : 0) - (a.trigger?.actor_tags_exclude ? 1 : 0))
    || (b.priority ?? 0) - (a.priority ?? 0)
    || (a.rule_id < b.rule_id ? -1 : 1));
}

/* ---------- consequence executors (run under the OWNING engine's authority) ---------- */
const EXECUTORS = {
  journal_breadcrumb(g, env, payload) {
    g.addJournal(payload.kind ?? 'system', payload.text);
  },
  spawn_nemesis(g, env, payload) {
    if (g.registry.has(payload.urid)) return;
    const doc = { ...payload.doc, tracking_target: g.campaign?.party?.[0] ?? null };
    g.registerEntity(payload.urid, doc, 'Nemesis', 'wip');
    if (!g.campaign?.characters) {
      g.dispatchEvent({ event_type: 'save_slice_init', authority: 'campaign_engine', target: 'campaign', caused_by: [env.event_id], ops: [{ op: 'add', path: '/characters', value: {} }], visibility: 'gm_only' });
    }
    // campaign_engine owns the save slice; nemesis_engine owns the entity itself
    g.dispatchEvent({
      event_type: 'nemesis_spawned', authority: 'campaign_engine', target: 'campaign', caused_by: [env.event_id],
      ops: [{ op: 'add', path: `/characters/${payload.urid}`, value: doc }],
      visibility: 'gm_only', diagnostics: { chaos_rule: true },
    });
    if (payload.breadcrumb) g.addJournal(payload.breadcrumb.kind, payload.breadcrumb.text);
  },
  reveal_nemesis(g, env, payload) {
    if (!g.registry.has(payload.urid)) return;
    g.dispatchEvent({
      event_type: 'nemesis_revealed', authority: 'nemesis_engine', target: payload.urid,
      caused_by: [env.event_id], ops: payload.patches,
    });
    if (payload.breadcrumb) g.addJournal(payload.breadcrumb.kind, payload.breadcrumb.text);
  },
  obligation_tick(g, env) {
    const c = g.campaign;
    if (!c?.ffg_pools) return;
    g.dispatchEvent({
      event_type: 'obligation_ticked', authority: 'providence_engine', target: 'campaign', caused_by: [env.event_id],
      ops: [{ op: 'replace', path: '/ffg_pools/obligation', value: Math.min(100, (c.ffg_pools.obligation ?? 0) + (c.wanted_level ?? 1)) }],
      visibility: 'gm_only',
    });
  },
};

let _matching = false; // re-entrancy guard: consequences emit events too

/** Load SynergyRules instances from the registry (gold data) + baseline. */
function activeRules(g) {
  const fromRegistry = [];
  for (const m of g.manifest) {
    if (m.schema === 'SynergyRules') {
      const doc = g.registry.get(m.urid);
      const rules = doc?.rules ?? (doc?.rule_id ? [doc] : []);
      for (const r of rules) if (r.rule_id && r.trigger && r.mechanical_effect) fromRegistry.push(r);
    }
  }
  return [...fromRegistry, ...BASELINE_RULES];
}

/** THE MATCHER — installed into the store; runs on every ACCEPTED envelope. */
export function chaosMatch(envelope) {
  if (_matching) return; // consequences don't cascade within one match pass
  const g = useGenesis.getState();
  if (!g.campaignActive) return;
  const phase = envelope.event_type === 'world_phase_advanced'
    ? envelope.diagnostics?.phase ?? g.campaign?.world_phase ?? 0
    : g.campaign?.world_phase ?? 0;
  const envTags = envelope.diagnostics?.tags ?? [];

  const matched = activeRules(g).filter((r) => {
    const t = r.trigger ?? {};
    if (t.trigger_event && t.trigger_event !== envelope.event_type) return false;
    if (!tagsMatch(t, envTags)) return false;
    if (!conditionsMatch(t.conditions, { campaign: g.campaign, phase })) return false;
    return true;
  });
  if (!matched.length) return;

  _matching = true;
  try {
    for (const rule of arbitrate(matched).slice(0, PHASE_BUDGET)) {
      const fx = rule.mechanical_effect;
      const exec = EXECUTORS[fx?.consequence];
      if (!exec) { console.warn('CHAOS: no executor for', fx?.consequence); continue; }
      exec(useGenesis.getState(), envelope, fx.payload ?? {});
    }
  } finally {
    _matching = false;
  }
}

/* Install the matcher into the store (breaks the import cycle). */
useGenesis.setState({ _chaosMatch: chaosMatch });

/* dev/QA hook */
if (typeof window !== 'undefined') window.__chaos = { chaosMatch, BASELINE_RULES };
