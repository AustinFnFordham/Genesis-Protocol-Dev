/* SHIP (Command & Record tab) — bound EXCLUSIVELY to the mounted projection's
 * command_record.ship. No registry fixtures, no Millennium Falcon, no sandbox
 * crew. Empty means an honest empty state. (D–L step F) */
import React from 'react';
import { useGenesis } from '../state/store.js';

export default function ShipManagement() {
  const proj = useGenesis((s) => s.mounted?.projection);
  const cid = useGenesis((s) => s.mountedCampaignId);
  const ship = proj?.command_record?.ship;

  if (!ship) {
    return (
      <div data-region="ship" data-campaign-id={cid ?? ''} style={{ padding: 16, color: 'var(--dim)', fontSize: 'var(--sys-font-size-control)' }}>
        No ship is registered to this campaign.
      </div>
    );
  }
  const hull = ship.hull ?? {}; const strain = ship.strain ?? {};
  return (
    <div data-region="ship" data-campaign-id={cid ?? ''} style={{ padding: '10px 14px', fontSize: 'var(--sys-font-size-control)', overflowY: 'auto' }}>
      <div style={{ color: 'var(--cyan)', letterSpacing: 1, fontSize: 'var(--sys-font-size-body)' }}>{ship.name ?? ship.vessel_id}</div>
      <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--dim)', marginBottom: 8 }}>{ship.vessel_id} · silhouette {ship.silhouette ?? '—'} · spd {ship.speed ?? '—'} · armor {ship.armor ?? '—'}</div>
      <div style={{ fontSize: 'var(--sys-font-size-meta)' }}>Hull {hull.current ?? '—'}/{hull.threshold ?? '—'} · Strain {strain.current ?? '—'}/{strain.threshold ?? '—'}</div>
      {(ship.stations ?? []).length > 0 && <>
        <div className="sec-h" style={{ marginTop: 10 }}>Stations</div>
        {ship.stations.map((st) => (
          <div key={st.station_id} style={{ fontSize: 'var(--sys-font-size-note)', color: '#cfe8f5', marginBottom: 2 }}>
            ⌖ {st.name} — {st.occupied_by ?? 'unoccupied'} <span style={{ color: 'var(--dim)' }}>({(st.available_actions ?? []).join(', ')})</span>
          </div>
        ))}
      </>}
      {(ship.weapons ?? []).length > 0 && <>
        <div className="sec-h" style={{ marginTop: 8 }}>Weapons</div>
        {ship.weapons.map((w, i) => (
          <div key={i} style={{ fontSize: 'var(--sys-font-size-note)', color: '#cfe8f5' }}>⌖ {w.weapon_id ?? w.name} · arc {w.arc ?? '—'} · dmg {w.damage ?? '—'}</div>
        ))}
      </>}
    </div>
  );
}
