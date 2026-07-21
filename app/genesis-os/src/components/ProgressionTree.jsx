/* DNA RECORD — frosted-glass overlay. Bound EXCLUSIVELY to the mounted
 * projection's operative (identity refs + progression_summary + resolved
 * definitions). No registry 'guardian' fixture, no Aran/Sandbox leakage.
 * An unresolved class renders an honest unresolved state. (D–L step D) */
import React from 'react';
import { useGenesis } from '../state/store.js';

function facet(f) { return f?.name ?? null; }

export default function ProgressionTree() {
  const proj = useGenesis((s) => s.mounted?.projection);
  const cid = useGenesis((s) => s.mountedCampaignId);
  const setOverlay = useGenesis((s) => s.setOverlay);
  const op = proj?.operative?.character_runtime ?? {};
  const idn = op.identity ?? {};
  const prog = proj?.operative?.progression_summary ?? op.progression ?? {};
  const defs = proj?.definitions ?? {};

  const resolve = (urid) => defs[urid]?.name ?? String(urid).replace(/^(feature|power|item|subclass)_/, '').replace(/_/g, ' ');
  const features = op.features ?? [];
  const powers = op.powers ?? [];
  const classResolved = !!(idn.class?.class_id && idn.class?.name);

  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(4,7,13,0.72)', backdropFilter: 'blur(7px)' }} onClick={() => setOverlay(null)}>
      <div className="holo-panel boot-in" data-region="dna-record" data-campaign-id={cid ?? ''} data-character-id={proj?.selected_character_id ?? ''}
        style={{ width: 'min(94%, 720px)', maxHeight: '90%', overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
        <div className="holo-title">DNA Record — {facet({ name: idn.name }) ?? proj?.selected_character_id ?? '—'}
          <span style={{ flex: 1 }} />
          <span style={{ cursor: 'pointer', color: 'var(--dim)' }} onClick={() => setOverlay(null)}>✕ CLOSE</span>
        </div>
        <div style={{ padding: 16, fontSize: 'var(--sys-font-size-control)', lineHeight: 1.6 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            <div>Species: <b style={{ color: 'var(--cyan)' }}>{facet(idn.species) ?? '—'}</b></div>
            <div>Level: <b>{idn.level ?? prog.current_level ?? '—'}</b></div>
            <div>Class: {classResolved
              ? <b style={{ color: 'var(--cyan)' }}>{facet(idn.class)}</b>
              : <span style={{ color: 'var(--amber)' }}>unresolved — no class established for this character</span>}</div>
            <div>Subclass: <b>{facet(idn.subclass) ?? '—'}</b>
              {prog.planned_subclass && <span style={{ color: 'var(--amber)', marginLeft: 6 }}>· Planned: {prog.planned_subclass.name ?? resolve(prog.planned_subclass.subclass_id)}</span>}
            </div>
            <div>Background: <b>{facet(idn.background) ?? '—'}</b></div>
          </div>

          <div className="sec-h" style={{ marginTop: 12 }}>Unlocked Features ({features.length})</div>
          {features.length === 0 && <div style={{ color: 'var(--dim)' }}>No features recorded.</div>}
          {features.map((f, i) => (
            <div key={i} style={{ fontSize: 'var(--sys-font-size-meta)', color: '#cfe8f5', marginBottom: 2 }}>
              ◈ {f.name ?? resolve(f.urid)} <span style={{ color: 'var(--dim)', fontSize: 'var(--sys-font-size-caption)' }}>{f.urid}</span>
            </div>
          ))}

          <div className="sec-h" style={{ marginTop: 10 }}>Powers ({powers.length})</div>
          {powers.length === 0 && <div style={{ color: 'var(--dim)' }}>No powers available.</div>}
          {powers.map((p, i) => (
            <div key={i} style={{ fontSize: 'var(--sys-font-size-meta)', color: '#cfe8f5', marginBottom: 2 }}>◇ {p.name ?? resolve(p.urid)}</div>
          ))}

          {(prog.pending_choice_groups ?? []).length > 0 && <>
            <div className="sec-h" style={{ marginTop: 10 }}>Pending Choices</div>
            {prog.pending_choice_groups.map((g, i) => <div key={i} style={{ fontSize: 'var(--sys-font-size-note)', color: 'var(--amber)' }}>⬡ {g.name ?? g}</div>)}
          </>}
          <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--dim)', marginTop: 12 }}>
            Progression is resolved from the mounted campaign runtime + validated registry definitions by URID. No fixtures.
          </div>
        </div>
      </div>
    </div>
  );
}
