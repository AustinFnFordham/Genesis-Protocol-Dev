/* THE CHARACTER FORGE — holo-themed. Bindings unchanged (schema paths only):
 * stats grid (hexes), tag rail, visual_dna panel, morality engine, GM seals,
 * R3F hologram reacting to entity accent + corruption, RFC6902 patch bus QA. */
import React, { useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { useGenesis, getName, getId, getTags, getHex, getStats, getVisualDna } from '../state/store.js';

function Hologram({ hex, corruption }) {
  const mesh = useRef();
  const ring = useRef();
  useFrame((state, dt) => {
    if (mesh.current) mesh.current.rotation.y += dt * 0.55;
    if (ring.current) ring.current.rotation.z += dt * 0.12;
  });
  const emissive = corruption > 0.5 ? '#8b0000' : hex;
  return (
    <group>
      <mesh ref={mesh} position={[0, 0.25, 0]}>
        <capsuleGeometry args={[0.55, 1.15, 8, 24]} />
        <meshStandardMaterial color={hex} emissive={emissive} emissiveIntensity={0.6}
          transparent opacity={0.45} wireframe />
      </mesh>
      <mesh position={[0, -0.82, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.85, 1.02, 48]} />
        <meshBasicMaterial color={hex} transparent opacity={0.75} />
      </mesh>
      <mesh ref={ring} position={[0, -0.81, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.15, 1.18, 48, 1, 0, Math.PI * 1.4]} />
        <meshBasicMaterial color={hex} transparent opacity={0.4} />
      </mesh>
      <ambientLight intensity={0.45} />
      <pointLight position={[3, 3, 3]} intensity={34} color={hex} />
    </group>
  );
}

const mod = (v) => { const m = Math.floor((v - 10) / 2); return (m >= 0 ? '+' : '') + m; };

export default function CharacterForge() {
  const { registry, selected, gmView, toggleGm, dispatchEvent } = useGenesis();
  const e = registry.get(selected);
  const stats = useMemo(() => getStats(e), [e]);
  useEffect(() => {
    const kick = () => window.dispatchEvent(new Event('resize'));
    const a = requestAnimationFrame(kick); const b = setTimeout(kick, 120);
    return () => { cancelAnimationFrame(a); clearTimeout(b); };
  }, []);
  if (!e) return <div style={{ padding: 40, color: 'var(--dim)' }}>select an entry from the registry…</div>;

  const hex = getHex(e);
  const morality = e?.psychological_profile?.ffg_morality ?? e?.moral_compass?.morality ?? e?.morality ?? 50;
  const corruption = 1 - Math.min(Math.max(morality, 0), 100) / 100;
  const dna = getVisualDna(e);
  const gmBlocks = [e.llm_guidance, e.ai_behavior, e?.essence?.gm_guidance].filter(Boolean);
  const tier = useGenesis.getState().manifest.find((m) => m.urid === selected)?.tier ?? 'gold';

  const simulateForgeDelta = () => {
    const candidates = [
      ['/resources/hp_current', (v) => Math.max(0, (v ?? 10) - 4)],
      ['/hit_points', (v) => Math.max(0, (v ?? 10) - 4)],
      ['/stats/dex', (v) => Math.max(1, (v ?? 10) - 1)],
      ['/ability_scores/dexterity', (v) => Math.min(20, (v ?? 10) + 1)],
      ['/metadata/version', () => '0.0.qa'],
    ];
    for (const [path, fn] of candidates) {
      const cur = path.slice(1).split('/').reduce((o, k) => (o == null ? undefined : o[k]), e);
      // DATA-mode QA probe — explicit data_inspector authority, never a gameplay surface.
      if (cur !== undefined) { dispatchEvent({ event_type: 'inspector_probe', authority: 'data_inspector', target: selected, ops: [{ op: 'replace', path, value: fn(cur) }], visibility: 'gm_only' }); return; }
    }
  };

  return (
    <>
      {tier !== 'gold' && <div className="wip-stripe">⚠ unverified data — entity has not cleared the gold gate ⚠</div>}
      <div style={{ padding: '14px 20px 6px', borderBottom: '1px solid var(--line)', display: 'flex', alignItems: 'baseline', gap: 14, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 'var(--sys-font-size-heading)', letterSpacing: 1, textShadow: '0 0 12px rgba(51,225,255,.3)' }}>{getName(e)}</span>
        <span style={{ color: 'var(--dim)', fontSize: 'var(--sys-font-size-note)', letterSpacing: 1 }}>{getId(e)}</span>
        <span style={{ flex: 1 }} />
        <span className={`holo-btn ${gmView ? '' : 'ghost'}`} style={{ fontSize: 'var(--sys-font-size-caption)', padding: '4px 12px', ...(gmView ? { color: 'var(--amber)', borderColor: 'var(--amber)', textShadow: '0 0 8px rgba(255,179,0,.5)' } : {}) }}
          onClick={toggleGm}>{gmView ? 'GM View' : 'Player View'}</span>
      </div>
      <div style={{ padding: '8px 20px 0' }}>
        {getTags(e).slice(0, 12).map((t) => <span key={String(t)} className="tag-chip">{String(t)}</span>)}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '210px 1fr 380px', gap: 0, flex: 1, minHeight: 0 }}>
        <div style={{ padding: 16 }}>
          <div className="portrait-frame">
            <span className="ph">◈</span>
            <span className="label">MASTER REFERENCE ANCHOR<br />awaiting ComfyUI node</span>
          </div>
          <div className="sec-h" style={{ marginTop: 18 }}>Morality Engine</div>
          <div style={{ fontSize: 'var(--sys-font-size-meta)' }}>{morality}/100</div>
          <div className={`gauge ${corruption > 0.5 ? 'red' : ''}`} style={{ width: '100%', marginTop: 4 }}>
            <i style={{ width: `${morality}%` }} />
          </div>
          <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--dim)', marginTop: 4 }}>corruption tint {(corruption * 100).toFixed(0)}% → hologram emissive</div>
        </div>
        <Canvas camera={{ position: [0, 0.6, 3.2], fov: 50 }} gl={{ preserveDrawingBuffer: true }}>
          <Hologram hex={hex} corruption={corruption} />
        </Canvas>
        <aside style={{ borderLeft: '1px solid var(--line)', overflowY: 'auto', padding: 16, fontSize: 'var(--sys-font-size-control)', lineHeight: 1.6 }}>
          {stats && (<>
            <div className="sec-h">SW5E Stats — live, patches re-render</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
              {['str', 'dex', 'con', 'int', 'wis', 'cha'].map((k) => stats[k] != null && (
                <div key={k} className="stat-hex">
                  <div className="k">{k.toUpperCase()}</div>
                  <div className="v">{stats[k]}</div>
                  <div className="m">{mod(stats[k])}</div>
                </div>
              ))}
            </div>
          </>)}
          <div className="sec-h">Visual DNA — identity lock</div>
          <div style={{ fontSize: 'var(--sys-font-size-note)' }}>
            <div style={{ color: 'var(--green)' }}>constants: {JSON.stringify(dna.identity_constants).slice(0, 110)}</div>
            <div style={{ color: 'var(--cyan)', marginTop: 3 }}>gear: {JSON.stringify(dna.gear_variables).slice(0, 110)}</div>
            <div style={{ color: 'var(--dim)', marginTop: 3 }}>gear change → SAM inpaint via `comfy_inpaint` (contract live in Rust)</div>
          </div>
          {gmView
            ? gmBlocks.map((b, i) => (
              <div key={i} className="gm-seal">■ GM DATA — DECRYPTED
                <pre>{(typeof b === 'string' ? b : JSON.stringify(b, null, 1)).slice(0, 560)}</pre>
              </div>))
            : gmBlocks.length > 0 && <div className="gm-seal">■ {gmBlocks.length} GM-only block(s) sealed</div>}
          <div className="sec-h">Patch Bus QA</div>
          <span className="holo-btn" style={{ fontSize: 'var(--sys-font-size-caption)', padding: '5px 14px' }} onClick={simulateForgeDelta}>simulate forge delta (RFC6902)</span>
          <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--dim)', marginTop: 4 }}>
            log: {useGenesis.getState().patchLog.length} op batch(es) — replayable
          </div>
        </aside>
      </div>
    </>
  );
}
