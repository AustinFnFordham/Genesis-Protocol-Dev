/* THE ROMANCE & RELATIONSHIP SYSTEM (Soul family).
 * Implements docs/systems/ROMANCE_RELATIONSHIP_SYSTEM.md level 1+2:
 * romance points live on the PLAYER character as a registry keyed by
 * companion urid (level-2 "relationship registry"); thresholds
 * 0/25/50/75/100 map to Friendship → Close Friendship → Romantic Interest
 * → Dating → Committed Relationship. Companion-side romance_potential /
 * romance_compatibility (level-1, already in Companion schema data) gates
 * whether points accrue at all. All writes are relationship_engine
 * envelopes; history rides with the points so the AI GM can narrate memory. */
import { useGenesis, getName } from './store.js';

export const ROMANCE_LEVELS = [
  { min: 0, status: 'Friendship' },
  { min: 25, status: 'Close Friendship' },
  { min: 50, status: 'Romantic Interest' },
  { min: 75, status: 'Dating' },
  { min: 100, status: 'Committed Relationship' },
];

export const romanceStatus = (points) =>
  [...ROMANCE_LEVELS].reverse().find((l) => points >= l.min)?.status ?? 'Friendship';

/** Companion-side gate: does this companion romance at all? */
export function romancePotential(companionDoc) {
  const r = companionDoc?.romantic_relationship;
  if (!r) return true; // no block = no opinion; the GM decides narratively
  return r.romance_potential !== false;
}

/** Award (or deduct) romance points between the player and a companion.
 * Returns { accepted, points, status, levelUp } or a rejection. */
export function applyRomance({ player, companion, delta, event = 'moment', intent_id = null }) {
  const g = useGenesis.getState();
  const pc = g.registry.get(player);
  const comp = g.registry.get(companion);
  if (!pc || !comp) return { accepted: false, reason: 'unknown participant' };
  if (!romancePotential(comp)) {
    return { accepted: false, reason: `${getName(comp)} is not open to romance.` };
  }
  const reg = pc.romance_relationships ?? {};
  const cur = reg[companion] ?? { romance_points: 0, current_status: 'Friendship', relationship_history: [] };
  const points = Math.max(0, Math.min(100, (cur.romance_points ?? 0) + delta));
  const status = romanceStatus(points);
  const levelUp = status !== cur.current_status;
  const entry = {
    ...cur,
    romance_points: points,
    romance_level: points,
    current_status: status,
    relationship_history: [
      ...(cur.relationship_history ?? []).slice(-19),
      { event, points_gained: delta, date: new Date().toISOString().slice(0, 10) },
    ],
  };
  const has = pc.romance_relationships !== undefined;
  const env = g.dispatchEvent({
    event_type: levelUp ? 'romance_level_changed' : 'romance_points_changed',
    authority: 'relationship_engine', target: player, intent_id,
    ops: [{ op: has ? 'replace' : 'add', path: '/romance_relationships', value: { ...reg, [companion]: entry } }],
    visibility: 'gm_only',
    diagnostics: { companion, delta, points, status },
  });
  if (!env) return { accepted: false, reason: 'romance write rejected' };
  if (levelUp) {
    useGenesis.getState().addJournal('relationship',
      `Something shifts between you and ${getName(comp)} — ${status.toUpperCase()}.`);
  }
  return { accepted: true, points, status, levelUp };
}

/* dev/QA hook */
if (typeof window !== 'undefined') window.__romance = applyRomance;
