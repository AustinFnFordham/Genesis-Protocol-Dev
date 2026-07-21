/* THE GALACTIC MAP — bound to the mounted projection's command_record.map.
 * No hardcoded Coruscant/Mustafar/Falleen, no registry fixtures. An empty map
 * is a designed empty state, not a fallback. (D–L step E) */
import React, { useState } from 'react';
import { useGenesis } from '../state/store.js';

export default function GalacticMap({ compact = false }) {
  const proj = useGenesis((s) => s.mounted?.projection);
  const cid = useGenesis((s) => s.mountedCampaignId);
  const nodes = proj?.command_record?.map?.visible_nodes ?? [];
  const here = proj?.active_engagement?.active_scene?.location;
  const [sel, setSel] = useState(null);

  if (nodes.length === 0) {
    return (
      <div data-region="map" data-campaign-id={cid ?? ''} style={{ padding: 16, color: 'var(--dim)', fontSize: 'var(--sys-font-size-control)', lineHeight: 1.5 }}>
        No mapped campaign locations have been established.
        {here && <div style={{ fontSize: 'var(--sys-font-size-note)', marginTop: 6 }}>Current location: <span style={{ color: 'var(--cyan)' }}>{here}</span></div>}
      </div>
    );
  }
  const W = 380, H = compact ? 300 : 420;
  const xs = nodes.map((n) => n.x ?? n.coordinates?.x ?? 0), ys = nodes.map((n) => n.y ?? n.coordinates?.y ?? 0);
  const minX = Math.min(...xs, 0) - 2, maxX = Math.max(...xs, 1) + 2, minY = Math.min(...ys, 0) - 2, maxY = Math.max(...ys, 1) + 2;
  const px = (n) => [((( n.x ?? n.coordinates?.x ?? 0) - minX) / (maxX - minX)) * (W - 60) + 30,
                     ((( n.y ?? n.coordinates?.y ?? 0) - minY) / (maxY - minY)) * (H - 60) + 30];
  const selNode = nodes.find((n) => (n.node_id ?? n.id) === sel);
  return (
    <div data-region="map" data-campaign-id={cid ?? ''} style={{ fontSize: 'var(--sys-font-size-meta)' }}>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}>
        {nodes.map((n) => {
          const [x, y] = px(n); const nid = n.node_id ?? n.id;
          const isHere = here === (n.name ?? nid);
          return (
            <g key={nid} style={{ cursor: 'pointer' }} onClick={() => setSel(nid)}>
              <circle cx={x} cy={y} r="5.5" fill="#0a141f" stroke={sel === nid ? '#33e1ff' : '#2a7a99'} strokeWidth="1.6" />
              <text x={x} y={y - 12} fill={isHere ? '#ffd54f' : '#cfe8f5'} fontSize="8" textAnchor="middle">{n.name ?? nid}</text>
            </g>
          );
        })}
      </svg>
      {selNode && (
        <div className="holo-panel" style={{ margin: '8px 4px', padding: '8px 12px' }}>
          <div style={{ color: 'var(--cyan)' }}>{selNode.name ?? selNode.node_id} <span style={{ color: 'var(--dim)', fontSize: 'var(--sys-font-size-micro)' }}>{selNode.region ?? ''}</span></div>
        </div>
      )}
    </div>
  );
}
