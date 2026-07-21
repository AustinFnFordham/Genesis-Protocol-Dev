/* GEN-RULE-001 — THE UNIVERSAL INTENT CONTRACT.
 * Revelation NEVER mutates state. It submits typed intents here; deterministic
 * resolvers judge them and emit event envelopes through store.dispatchEvent.
 * Every outcome — acceptance or rejection — is explicit and ledgered.
 *
 * submitIntent({ type, actor, payload }) →
 *   { accepted: true, events: [envelope], summary }
 * | { accepted: false, reason } */
import { useGenesis } from './store.js';
import { runWorldPhase } from './worldPhase.js';
import { applyInfluence } from './influence.js';
import { applyRomance } from './romance.js';

let _iseq = 0;
const intentId = () => `int_${Date.now().toString(36)}_${(_iseq++).toString(36)}`;

/* ---------- resolver helpers ---------- */
function ctx() {
  const g = useGenesis.getState();
  return { g, campaign: g.campaign, active: g.campaignActive };
}
function reject(reason) { return { accepted: false, reason }; }
function accept(events, summary) { return { accepted: true, events: events.filter(Boolean), summary }; }

/* ---------- RESOLVERS ---------- */

/** GEN-EXPLORE-002 — travel cannot teleport.
 * destination → lane legality → risk → time → world phase → arrival event. */
function resolveTravel(iid, { destination }) {
  const { g, campaign, active } = ctx();
  if (!active) return reject('No active campaign — start a New Game to travel.');
  const mapUrid = g.manifest.find((m) => m.schema === 'GalacticMap')?.urid;
  const gmap = g.registry.get(mapUrid);
  if (!gmap) return reject('No GalacticMap in registry.');
  const here = campaign.current_location_id;
  if (destination === here) return reject('Already at this location.');
  const dest = (gmap.nodes ?? []).find((n) => n.node_id === destination);
  if (!dest) return reject(`Unknown destination: ${destination}`);

  // LANE LEGALITY: a hyperlane must connect here → destination.
  const lane = (gmap.lanes ?? []).find(
    (l) => (l.from_node === here && l.to_node === destination) || (l.to_node === here && l.from_node === destination)
  );
  if (!lane) return reject(`No hyperlane connects ${here} → ${destination}. Plot a route through connected nodes.`);
  if (lane.status === 'blockaded') return reject(`Lane ${lane.name ?? lane.lane_id} is BLOCKADED. Find another route or break the blockade.`);

  const days = lane.travel_days ?? 1;
  const env = g.dispatchEvent({
    event_type: 'travel_completed',
    authority: 'exploration_engine',
    target: 'campaign',
    intent_id: iid,
    actor_id: campaign.party?.[0] ?? 'party',
    ops: [{ op: 'replace', path: '/current_location_id', value: destination }],
    journal_payload: {
      kind: 'travel',
      text: `Hyperspace jump — ${days}d via ${lane.name ?? lane.lane_id} (danger ${lane.danger_rating ?? '?'}). Arrived at ${dest.name}. Bounty level here: ${dest.bounty_level ?? '?'}.`,
    },
    diagnostics: { lane: lane.lane_id, travel_days: days, danger: lane.danger_rating },
  });
  if (!env) return reject('Travel event rejected by authority/guardrail.');
  // Time passes: each travel day advances the universe.
  for (let d = 0; d < days; d++) runWorldPhase('travel');
  return accept([env], `Arrived at ${dest.name} (${days}d).`);
}

/** Inventory: equip/unequip through inventory_engine. */
function resolveEquip(iid, { character, entry }) {
  const { g } = ctx();
  if (!g.registry.get(character)) return reject(`Unknown character ${character}`);
  const label = typeof entry === 'string' ? entry : entry.name ?? entry.item_id;
  const env = g.dispatchEvent({
    event_type: 'item_equipped', authority: 'inventory_engine', target: character, intent_id: iid,
    actor_id: character, ops: [{ op: 'add', path: '/equipment/-', value: entry }],
    diagnostics: { label },
  });
  return env ? accept([env], 'equipped') : reject('equip rejected');
}
function resolveUnequip(iid, { character, index }) {
  const { g } = ctx();
  const char = g.registry.get(character);
  if (!char?.equipment?.[index]) return reject('Nothing socketed there.');
  const env = g.dispatchEvent({
    event_type: 'item_unequipped', authority: 'inventory_engine', target: character, intent_id: iid,
    actor_id: character, ops: [{ op: 'remove', path: `/equipment/${index}` }],
  });
  return env ? accept([env], 'stripped') : reject('unequip rejected');
}

/** Combat: token movement + hazard triggers on the grid. */
function resolveMoveToken(iid, { combat, tokenIndex, x, y }) {
  const { g } = ctx();
  const doc = g.registry.get(combat);
  if (!doc?.grid_state?.tokens?.[tokenIndex]) return reject('No such token.');
  const env = g.dispatchEvent({
    event_type: 'token_moved', authority: 'combat_engine', target: combat, intent_id: iid,
    ops: [
      { op: 'replace', path: `/grid_state/tokens/${tokenIndex}/x`, value: x },
      { op: 'replace', path: `/grid_state/tokens/${tokenIndex}/y`, value: y },
    ],
  });
  return env ? accept([env], 'moved') : reject('move rejected');
}
function resolveTriggerHazard(iid, { combat, hazardIndex, hazard }) {
  const { g, campaign } = ctx();
  const events = [];
  const env = g.dispatchEvent({
    event_type: 'hazard_triggered', authority: 'combat_engine', target: combat, intent_id: iid,
    ops: [{ op: 'replace', path: `/grid_state/environmental_hazards/${hazardIndex}/triggered`, value: true }],
    journal_payload: { kind: 'combat', text: `DESPAIR — ${hazard?.name ?? 'hazard'} detonates. The fire spreads beyond the grid. Someone lived here.` },
  });
  if (!env) return reject('hazard rejected');
  events.push(env);
  // The world remembers: campaign flag set by campaign_engine (Chaos consumes this).
  if (campaign && !campaign.flags?.canister_ignited) {
    events.push(g.dispatchEvent({
      event_type: 'flag_set', authority: 'campaign_engine', target: 'campaign', intent_id: iid,
      caused_by: [env.event_id],
      ops: [{ op: 'add', path: '/flags/canister_ignited', value: true }],
      visibility: 'gm_only',
    }));
  }
  return accept(events, 'hazard triggered');
}

/** Scene actions from Dialogue: trust shifts via relationship_engine, plus
 * optional GEN-REL-001 influence ripple ({ alignment, magnitude, radius })
 * and optional romance beat ({ delta, event }). */
function resolveTrustShift(iid, { target, delta, influence, romance }) {
  const { g, campaign } = ctx();
  const doc = g.registry.get(target);
  if (!doc) return reject(`Unknown entity ${target}`);
  const has = typeof doc.trust_meter === 'number';
  const cur = has ? doc.trust_meter : 25;
  const ops = has
    ? [{ op: 'replace', path: '/trust_meter', value: Math.max(0, Math.min(100, cur + delta)) }]
    : [{ op: 'add', path: '/trust_meter', value: Math.max(0, Math.min(100, cur + delta)) }];
  const env = g.dispatchEvent({
    event_type: 'trust_shifted', authority: 'relationship_engine', target, intent_id: iid, ops,
    diagnostics: { delta },
  });
  if (!env) return reject('trust shift rejected');
  const player = campaign?.party?.[0];
  let ripple = null;
  if (influence?.alignment && player) {
    ripple = applyInfluence({ actor: player, ...influence, intent_id: iid });
  }
  if (romance?.delta && player) {
    applyRomance({ player, companion: target, delta: romance.delta, event: romance.event ?? 'scene', intent_id: iid });
  }
  return accept([env], `trust ${delta > 0 ? '+' : ''}${delta}${ripple?.applied ? ` · ${influence.alignment} ripple m${influence.magnitude ?? 3}` : ''}`);
}

/** Direct romance beat outside a trust shift. */
function resolveRomanceGesture(iid, { companion, delta, event }) {
  const { g, campaign } = ctx();
  const player = campaign?.party?.[0];
  if (!player) return reject('No active player character.');
  const r = applyRomance({ player, companion, delta, event: event ?? 'gesture', intent_id: iid });
  return r.accepted ? accept([], `${r.status} (${r.points})`) : reject(r.reason);
}

/** Scene flags from the adjudicator (holocron cracked, overrides remembered)
 * — social_engine owns scene state. */
function resolveSceneFlag(iid, { target, flags }) {
  const { g } = ctx();
  const doc = g.registry.get(target);
  if (!doc) return reject(`Unknown entity ${target}`);
  const has = doc._scene_flags !== undefined;
  const value = has ? { ...doc._scene_flags, ...flags } : flags;
  const env = g.dispatchEvent({
    event_type: 'scene_flag_set', authority: 'social_engine', target, intent_id: iid,
    ops: [{ op: has ? 'replace' : 'add', path: '/_scene_flags', value }],
    visibility: 'gm_only',
  });
  return env ? accept([env], 'scene flag set') : reject('scene flag rejected');
}

/** Providence: the player ends their turn; the universe takes its own. */
function resolveEndTurn(iid) {
  const { active } = ctx();
  if (!active) return reject('No active campaign.');
  const summary = runWorldPhase('end_turn');
  return accept([], `world phase ${summary.phase ?? '?'}`);
}

/** Progression: spending advancement through progression_engine. */
function resolveAdvance(iid, { character, ops, label }) {
  const { g } = ctx();
  if (!g.registry.get(character)) return reject(`Unknown character ${character}`);
  const env = g.dispatchEvent({
    event_type: 'character_advanced', authority: 'progression_engine', target: character, intent_id: iid,
    ops, journal_payload: label ? { kind: 'progression', text: label } : null,
  });
  return env ? accept([env], 'advanced') : reject('advancement rejected');
}

/** Starship: crew assignment / registration through starship_engine. */
function resolveShipOp(iid, { ops, label, event_type = 'ship_updated' }) {
  const { g, active } = ctx();
  if (!active) return reject('No active campaign.');
  const env = g.dispatchEvent({
    event_type, authority: 'starship_engine', target: 'campaign', intent_id: iid,
    ops, journal_payload: label ? { kind: 'ship', text: label } : null,
  });
  return env ? accept([env], 'ship updated') : reject('ship op rejected');
}

const RESOLVERS = {
  travel: resolveTravel,
  equip_item: resolveEquip,
  unequip_item: resolveUnequip,
  move_token: resolveMoveToken,
  trigger_hazard: resolveTriggerHazard,
  scene_action: resolveTrustShift, // trust + influence ripple + romance beats
  scene_flag: resolveSceneFlag,
  romance_gesture: resolveRomanceGesture,
  end_turn: resolveEndTurn,
  advance_character: resolveAdvance,
  ship_op: resolveShipOp,
};

/** THE GATE. All Revelation gameplay flows through here. */
export function submitIntent(type, payload = {}) {
  const resolver = RESOLVERS[type];
  if (!resolver) return reject(`No resolver for intent '${type}' — mechanical law has no such verb.`);
  const iid = intentId();
  try {
    const outcome = resolver(iid, payload);
    if (!outcome.accepted) console.warn(`INTENT REJECTED [${type}]:`, outcome.reason);
    return outcome;
  } catch (e) {
    console.error(`INTENT ERROR [${type}]:`, e);
    return reject(`resolver error: ${e.message}`);
  }
}

/* dev/QA hook */
if (typeof window !== 'undefined') window.__intent = submitIntent;
