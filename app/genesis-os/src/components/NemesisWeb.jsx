/* THE NEMESIS WEB — bound to the mounted projection's player-visible nemesis
 * list (server visibility-filtered). No registry fixtures, no Aran/Assassin
 * fallback, no hidden-state exposure. Empty = no known nemesis. (D–L step G) */
import React from 'react';
import { useGenesis } from '../state/store.js';

const STAGE_COLOR = { emergence: '#ffb300', escalation: '#ff7a2a', confrontation: '#ff4d5a' };

export default function NemesisWeb() {
  const proj = useGenesis((s) => s.mounted?.projection);
  const cid = useGenesis((s) => s.mountedCampaignId);
  const nemeses = proj?.command_record?.player_visible_nemesis ?? [];

  if (nemeses.length === 0) {
    return (
      <div data-region="nemesis" data-campaign-id={cid ?? ''} style={{ padding: 16, color: 'var(--dim)', fontSize: 'var(--sys-font-size-control)' }}>
        No player-visible Nemesis information is available.
      </div>
    );
  }
  return (
    <div data-region="nemesis" data-campaign-id={cid ?? ''} style={{ fontSize: 'var(--sys-font-size-meta)', padding: '6px 4px' }}>
      {nemeses.map((n, i) => {
        const revealed = n.revealed !== false;
        const col = revealed ? (STAGE_COLOR[n.progression_stage] ?? '#ff4d5a') : '#8a6a7a';
        return (
          <div key={n.id ?? i} className="holo-panel" style={{ margin: '6px 4px', padding: '7px 10px' }}>
            <div style={{ color: col, fontSize: 'var(--sys-font-size-meta)', letterSpacing: 1 }}>
              {revealed ? (n.name ?? n.id) : '▓▓▓▓▓ UNKNOWN ACTOR'}
              <span style={{ color: 'var(--dim)', fontSize: 'var(--sys-font-size-micro)', marginLeft: 8 }}>{n.archetype ?? ''}</span>
            </div>
            <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--dim)', marginTop: 2, fontStyle: 'italic' }}>
              {revealed ? `"${n.grudge_origin ?? 'grudge origin sealed'}"` : 'grudge origin: [ENCRYPTED]'}
            </div>
          </div>
        );
      })}
    </div>
  );
}
