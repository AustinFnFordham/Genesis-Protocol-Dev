/* THE WORLD PHASE ENGINE (Providence) — the universe takes its turn.
 * GEN-CHAOS-001 refactor: this engine now ONLY advances the clock and drifts
 * faction influence. The fuel-canister incubation chain (and all future
 * butterfly effects) live as SynergyRules-shaped DATA in chaos.js — the
 * Chaos matcher consumes the accepted `world_phase_advanced` envelope this
 * engine emits and routes candidate consequences to their owning engines. */
import { useGenesis } from './store.js';
import './chaos.js'; // installs the matcher into the store

/* dev/QA hook */
if (typeof window !== 'undefined') window.__runWorldPhase = (t) => runWorldPhase(t);

/* Faction influence drift: contested nodes bleed toward the strongest holder. */
function driftInfluence(s) {
  const mapUrid = s.manifest.find((m) => m.schema === 'GalacticMap')?.urid;
  const gmap = s.registry.get(mapUrid);
  if (!gmap) return null;
  const patches = [];
  (gmap.nodes ?? []).forEach((n, ni) => {
    const tc = n.territory_control ?? [];
    if (tc.length < 2) return;
    const sorted = tc.map((t, ti) => ({ ...t, ti })).sort((a, b) => b.influence - a.influence);
    const [top, next] = sorted;
    if (top.influence < 95 && next.influence > 5) {
      patches.push({ op: 'replace', path: `/nodes/${ni}/territory_control/${top.ti}/influence`, value: top.influence + 1 });
      patches.push({ op: 'replace', path: `/nodes/${ni}/territory_control/${next.ti}/influence`, value: next.influence - 1 });
    }
  });
  return patches.length ? { mapUrid, patches } : null;
}

/** Advance the universe one turn. Returns a summary for the caller. */
export function runWorldPhase(trigger = 'end_turn') {
  const g = useGenesis.getState();
  if (!g.campaignActive || !g.campaign) return { skipped: true };
  const phase = (g.campaign.world_phase ?? 0) + 1;
  const events = [];

  // 1. advance the clock — the enveloped event the Chaos matcher feeds on
  const env = g.dispatchEvent({
    event_type: 'world_phase_advanced',
    authority: 'providence_engine',
    target: 'campaign',
    ops: [{ op: 'replace', path: '/world_phase', value: phase }],
    visibility: 'gm_only',
    diagnostics: { phase, trigger },
  });
  if (!env) return { skipped: true, reason: 'phase advance rejected' };
  events.push('phase_advanced');

  // 2. faction influence drift (the borders breathe) — faction_engine authority
  const s = useGenesis.getState();
  const drift = driftInfluence(s);
  if (drift) {
    const dEnv = s.dispatchEvent({
      event_type: 'influence_drifted', authority: 'faction_engine', target: drift.mapUrid,
      caused_by: [env.event_id], ops: drift.patches, visibility: 'gm_only',
    });
    if (dEnv) {
      if (phase % 3 === 0) s.addJournal('system', 'Faction borders shifted while you weren’t looking. The map remembers.');
      events.push('influence_drift');
    }
  }

  if (events.length <= 1 && phase % 2 === 0) {
    s.addJournal('system', `World phase ${phase}: the galaxy turns quietly. For now.`);
  }
  return { phase, events, trigger };
}
