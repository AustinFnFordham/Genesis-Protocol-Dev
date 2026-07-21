/* SHIP VIEW — station-based, DATA-DRIVEN (reference layout, no copied values).
 * Everything renders from the mounted vessel runtime (gmRuntime.ship):
 * stations exist only if the vessel exposes them, actions come from station
 * data, damaged systems disable actions with a visible reason. Clicking an
 * action SUBMITS A DECLARATION through the same four-controller pipeline as
 * every other view — this screen never mutates hull, strain, shields,
 * position, or crew. If vessel data is incomplete, the placeholder is
 * explicit about what is missing. */
import React from 'react';
import { useGenesis } from '../state/store.js';

const SYS_COLOR = { operational: 'var(--cyan)', damaged: 'var(--amber)', disabled: 'var(--red)', destroyed: 'var(--red)' };

export default function ShipStations() {
  const { gmRuntime, setActionPrefill, setEngagement } = useGenesis();
  const ship = gmRuntime?.ship;
  const pcs = gmRuntime?.player_characters ?? {};
  const npcs = gmRuntime?.active_npcs ?? {};
  const crewName = (id) => pcs[id]?.identity?.name ?? npcs[id]?.name ?? id;

  if (!gmRuntime) {
    return <div style={{ padding: 30, color: 'var(--dim)', fontSize: 'var(--sys-font-size-meta)' }}>No campaign mounted — select a campaign to board a vessel.</div>;
  }
  if (!ship) {
    return (
      <div style={{ padding: 30, fontSize: 'var(--sys-font-size-note)' }}>
        <div style={{ color: 'var(--amber)' }}>ship_view_status: placeholder_layout</div>
        <div style={{ color: 'var(--dim)', marginTop: 6 }}>data_source: mounted_vessel_runtime<br />missing_data: [vessel_runtime] — this campaign has no vessel mounted.</div>
      </div>
    );
  }

  const declare = (text) => {
    setActionPrefill(text);
    setEngagement('dialogue'); // shared declaration pipeline — Narrative resolves
  };

  const missing = ['crew_station_rules', 'defensive_arc_values'].filter(() => true); // structural placeholders, explicit per spec
  const shieldArcs = ship.shields ?? {};
  const Gauge = ({ label, cur, max }) => (
    <div style={{ minWidth: 130 }}>
      <div style={{ display: 'flex', fontSize: 'var(--sys-font-size-micro)', letterSpacing: 1.5, color: 'var(--dim)' }}>
        <span>{label}</span><span style={{ flex: 1 }} /><span style={{ color: cur < max * 0.4 ? 'var(--red)' : 'var(--cyan)' }}>{cur}/{max}</span>
      </div>
      <div className={`gauge ${cur < max * 0.4 ? 'red' : ''}`}><i style={{ width: `${(cur / max) * 100}%` }} /></div>
    </div>
  );

  return (
    <div style={{ padding: '12px 18px', overflowY: 'auto', fontSize: 'var(--sys-font-size-note)' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 'var(--sys-font-size-body)', color: 'var(--cyan)', letterSpacing: 1 }}>{ship.name}</span>
        <span style={{ fontSize: 'var(--sys-font-size-label)', color: 'var(--dim)' }}>{ship.vessel_id} · SIL {ship.silhouette} · SPD {ship.speed} · ARM {ship.armor}</span>
      </div>

      <div style={{ display: 'flex', gap: 18, marginTop: 10, flexWrap: 'wrap' }}>
        <Gauge label="HULL" cur={ship.hull?.current ?? 0} max={ship.hull?.threshold ?? 1} />
        <Gauge label="STRAIN" cur={ship.strain?.current ?? 0} max={ship.strain?.threshold ?? 1} />
        <div style={{ fontSize: 'var(--sys-font-size-label)', color: 'var(--dim)' }}>
          SHIELDS&nbsp;
          {['fore', 'aft', 'port', 'starboard'].map((a) => (
            <span key={a} style={{ marginRight: 8, color: (shieldArcs[a] ?? 0) > 0 ? 'var(--cyan)' : 'var(--dim)' }}>
              {a.toUpperCase()} {shieldArcs[a] ?? 0}
            </span>
          ))}
        </div>
      </div>

      {/* systems strip */}
      <div style={{ display: 'flex', gap: 10, marginTop: 8, flexWrap: 'wrap' }}>
        {Object.entries(ship.systems ?? {}).map(([sys, st]) => (
          <span key={sys} style={{ fontSize: 'var(--sys-font-size-micro)', letterSpacing: 1, color: SYS_COLOR[st] ?? 'var(--dim)', border: `1px solid ${SYS_COLOR[st] ?? 'var(--line)'}`, padding: '2px 8px' }}>
            {sys.toUpperCase()}: {String(st).toUpperCase()}
          </span>
        ))}
      </div>

      {/* STATIONS — generated from the vessel. No pilot seat unless exposed;
          no turret unless the vessel has one. */}
      <div className="sec-h" style={{ marginTop: 14 }}>Crew Stations — generated from {ship.vessel_id}</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10 }}>
        {(ship.stations ?? []).map((st) => {
          const sysDown = Object.entries(ship.systems ?? {}).some(([s, v]) => v !== 'operational' && st.station_id.includes(s));
          return (
            <div key={st.station_id} className="holo-panel" style={{ padding: '8px 12px', opacity: st.status === 'operational' ? 1 : 0.6 }}>
              <div style={{ color: 'var(--cyan)', letterSpacing: 1.5, fontSize: 'var(--sys-font-size-note)' }}>{st.name.toUpperCase()}
                <span style={{ float: 'right', fontSize: 'var(--sys-font-size-micro)', color: st.status === 'operational' ? 'var(--dim)' : 'var(--red)' }}>{st.status}</span>
              </div>
              <div style={{ fontSize: 'var(--sys-font-size-label)', color: st.occupied_by ? '#cfe8f5' : 'var(--amber)', margin: '3px 0 6px' }}>
                {st.occupied_by ? `◈ ${crewName(st.occupied_by)}` : '— unmanned —'}
                <span style={{ color: 'var(--dim)' }}> · req: {(st.required_proficiencies ?? []).join(', ')}</span>
              </div>
              {(st.available_actions ?? []).map((a) => (
                <div key={a} className="holo-btn ghost" style={{ fontSize: 'var(--sys-font-size-label)', padding: '3px 8px', marginBottom: 3, display: 'block', opacity: sysDown ? 0.4 : 1 }}
                  title={sysDown ? 'linked system is not operational' : `declare: ${a} at ${st.name}`}
                  onClick={() => !sysDown && declare(`At the ${st.name} station, I ${a.toLowerCase()} `)}>
                  ▸ {a}{sysDown && <span style={{ color: 'var(--red)' }}> (system down)</span>}
                </div>
              ))}
              {(st.disabled_actions ?? []).map((a) => (
                <div key={a} style={{ fontSize: 'var(--sys-font-size-label)', color: 'var(--dim)', textDecoration: 'line-through', marginBottom: 3 }}>{typeof a === 'string' ? a : `${a.action} — ${a.reason}`}</div>
              ))}
            </div>
          );
        })}
      </div>

      {(ship.weapons ?? []).length > 0 && <>
        <div className="sec-h" style={{ marginTop: 12 }}>Weapons</div>
        {(ship.weapons ?? []).map((w) => (
          <div key={w.weapon_id} style={{ fontSize: 'var(--sys-font-size-caption)', color: '#cfe8f5', marginBottom: 3 }}>
            ⌖ {w.weapon_id} · arc {w.arc} · rng {w.range} · dmg {w.damage} · {(w.qualities ?? []).join(', ')}
            <span style={{ color: SYS_COLOR[w.current_status] ?? 'var(--dim)', marginLeft: 8 }}>{w.current_status}</span>
          </div>
        ))}
      </>}

      <div style={{ fontSize: 'var(--sys-font-size-micro)', color: 'var(--dim)', marginTop: 14, letterSpacing: 1 }}>
        ship_view_status: placeholder_layout · data_source: mounted_vessel_runtime · missing_data: [{missing.join(', ')}]<br />
        all actions submit declarations through the four-controller pipeline — this screen mutates nothing. attempt anything plausible.
      </div>
    </div>
  );
}
