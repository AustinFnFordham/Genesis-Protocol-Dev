/* PANEL 1 (LEFT): THE CHARACTER ANCHOR — fixed identity/core status.
 * Bound to the mounted campaign runtime (metadata.active_player). When no
 * campaign is mounted it shows an honest empty state — NEVER the legacy client
 * save, so no character/ship from another campaign can leak here. Equipment is
 * owned by the Operative tabs (ActionPanel), not this anchor. */
import React, { useState } from 'react';
import { useGenesis } from '../state/store.js';
import { portraitUrl } from '../state/registry.js';

const mod = (v) => { const m = Math.floor((v - 10) / 2); return (m >= 0 ? '+' : '') + m; };

function MountedAnchor({ rt, proj, setOverlay }) {
  const [imgOk, setImgOk] = useState(true);
  const pid = rt.metadata?.active_player;
  const sheet = rt.player_characters?.[pid];
  // prefer the resolved projection identity (canonical names) when available
  const pIdn = proj?.operative?.character_runtime?.identity;
  if (!pid || !sheet) {
    return <div data-region="operative" style={{ padding: 16, color: 'var(--sys-color-warning)', fontSize: 'var(--sys-font-size-body)' }}>
      ⚠ Anchor unresolved — no active player in the mounted runtime ({rt.mounted}).</div>;
  }
  const idy = sheet.identity ?? {}; const d = sheet.defenses ?? {}; const res = sheet.resources ?? {};
  const scores = sheet.abilities?.scores ?? {}; const conditions = d.conditions ?? [];
  const speciesName = pIdn?.species?.name ?? idy.species_name ?? idy.species;
  const className = pIdn?.class?.name ?? idy.class_name ?? (idy.class && !String(idy.class).startsWith('class_') ? idy.class : null);
  const line = [speciesName, className ?? 'class not established',
    (idy.subclass_plan ? `Planned: ${idy.subclass_plan}` : (idy.background_name ?? idy.background)), `L${idy.level ?? '?'}`].filter(Boolean).join(' · ');
  const Gauge = ({ label, cur, max, red }) => max != null && (
    <div style={{ marginTop: 6 }}>
      <div style={{ display: 'flex', fontSize: 'var(--sys-font-size-meta)', letterSpacing: 1.5, color: 'var(--sem-text-secondary)' }}>
        <span>{label}</span><span style={{ flex: 1 }} /><span style={{ color: red ? 'var(--sys-color-error)' : 'var(--sys-color-accent)' }}>{cur}/{max}</span>
      </div>
      <div className={`gauge ${red ? 'red' : ''}`}><i style={{ width: `${Math.max(0, Math.min(100, (cur / max) * 100))}%` }} /></div>
    </div>
  );
  return (
    <div data-region="operative" data-character-id={pid} style={{ display: 'flex', flexDirection: 'column', minHeight: 0, overflowY: 'auto', padding: 12 }}>
      <div className="portrait-frame" style={{ maxWidth: '100%' }}>
        {imgOk ? <img src={portraitUrl(pid)} alt="" onError={() => setImgOk(false)} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
          : <span className="ph">◈</span>}
        <span className="label">{pIdn?.name ?? idy.name ?? pid}</span>
      </div>
      <div style={{ marginTop: 10, fontSize: 'var(--sys-font-size-narrative)', letterSpacing: 1 }}>{pIdn?.name ?? idy.name ?? pid}</div>
      <div style={{ fontSize: 'var(--sys-font-size-meta)', color: 'var(--sem-text-secondary)' }}>{line}</div>
      <Gauge label="HP" cur={d.current_hp} max={d.maximum_hp} red={d.current_hp < d.maximum_hp * 0.4} />
      <Gauge label="STRAIN" cur={d.current_strain} max={d.maximum_strain} />
      <Gauge label="FORCE POINTS" cur={res.current_force_points} max={res.maximum_force_points} />
      {d.armor_class != null && <div style={{ fontSize: 'var(--sys-font-size-control)', color: 'var(--sem-text-secondary)', marginTop: 6 }}>ARMOR CLASS <span style={{ color: 'var(--sys-color-accent)' }}>{d.armor_class}</span></div>}
      {Object.keys(scores).length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 5, marginTop: 10 }}>
          {['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma'].map((k) => scores[k] != null && (
            <div key={k} className="stat-hex" style={{ padding: '10px 2px 8px' }}>
              <div className="k" style={{ fontSize: 'var(--sys-font-size-meta)' }}>{k.slice(0, 3).toUpperCase()}</div>
              <div className="v" style={{ fontSize: 'var(--sys-font-size-narrative)' }}>{scores[k]}</div>
              <div style={{ fontSize: 'var(--sys-font-size-meta)', color: 'var(--sys-color-accent)' }}>{mod(scores[k])}</div>
            </div>
          ))}
        </div>
      )}
      {conditions.length > 0 && (
        <div style={{ marginTop: 8 }}>{conditions.map((c, i) => <span key={i} style={{ fontSize: 'var(--sys-font-size-meta)', color: 'var(--sys-color-error)', border: '1px solid var(--sys-color-error)', padding: '1px 6px', marginRight: 4 }}>{String(c.name ?? c)}</span>)}</div>
      )}
      <span className="holo-btn primary" style={{ fontSize: 'var(--sys-font-size-control)', padding: '6px 10px', marginTop: 12, textAlign: 'center', display: 'block' }}
        onClick={() => setOverlay('progression')}>⬢ Access DNA Record</span>
    </div>
  );
}

export default function CharacterAnchor() {
  const setOverlay = useGenesis((s) => s.setOverlay);
  const gmCampaign = useGenesis((s) => s.gmCampaign);
  const gmRuntime = useGenesis((s) => s.gmRuntime);
  const proj = useGenesis((s) => s.mounted?.projection);
  if (!gmCampaign) {
    return <div data-region="operative" data-campaign-id="" style={{ padding: 16, color: 'var(--sem-text-secondary)', fontSize: 'var(--sys-font-size-body)' }}>
      No operative on record — mount a campaign to deploy.</div>;
  }
  if (!gmRuntime) return <div data-region="operative" style={{ padding: 16, color: 'var(--sem-text-secondary)' }}>resolving mounted runtime…</div>;
  return <MountedAnchor rt={gmRuntime} proj={proj} setOverlay={setOverlay} />;
}
