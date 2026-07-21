/* THE LIVING DIORAMA — tactical holotable v1.
 * Everything on this board is a render of Combat.schema grid_state:
 * tokens (x/y/z/elevation/facing/cover/conditions), environmental_hazards
 * (effect-linked, trigger_source), lighting. Every mutation is an RFC6902
 * batch through the patch bus — movement, hazard ignition, all of it.
 * Paper-miniature style: metal token bases + billboarded sprite planes that
 * always face the camera (awaiting alpha-masked ComfyUI portraits). */
import React, { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Billboard, Html, Line } from '@react-three/drei';
import { useGenesis, getName } from '../state/store.js';
import { submitIntent } from '../state/intents.js';

const CELL = 0.5; // world units per grid cell

function gridToWorld(gx, gy, W, H) {
  return [(gx - W / 2) * CELL, 0, (gy - H / 2) * CELL];
}

/* ---------- token: scratched-metal base + billboard paper sprite ---------- */
function Token({ tok, entity, color, W, H, selected, onSelect }) {
  const [x, , z] = gridToWorld(tok.x, tok.y, W, H);
  const elev = (tok.elevation ?? 0) * 0.14;
  const ringRef = useRef();
  useFrame((s) => {
    if (ringRef.current && selected) ringRef.current.rotation.z = s.clock.elapsedTime * 1.2;
  });
  const name = entity ? getName(entity) : tok.entity_id;
  return (
    <group position={[x, elev, z]} onClick={(e) => { e.stopPropagation(); onSelect(tok.token_id); }}>
      {/* elevation pylon */}
      {elev > 0 && (
        <mesh position={[0, -elev / 2, 0]}>
          <cylinderGeometry args={[0.05, 0.08, elev, 6]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.4} transparent opacity={0.35} />
        </mesh>
      )}
      {/* scratched metal base */}
      <mesh position={[0, 0.035, 0]}>
        <cylinderGeometry args={[0.21, 0.24, 0.07, 24]} />
        <meshStandardMaterial color="#2a3138" metalness={0.9} roughness={0.55} />
      </mesh>
      <mesh position={[0, 0.075, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.16, 0.2, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.9} />
      </mesh>
      {/* selection halo */}
      {selected && (
        <mesh ref={ringRef} position={[0, 0.08, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.28, 0.31, 32, 1, 0, Math.PI * 1.5]} />
          <meshBasicMaterial color="#33e1ff" transparent opacity={0.85} />
        </mesh>
      )}
      {/* facing indicator */}
      <mesh position={[Math.sin((tok.facing ?? 0) * Math.PI / 180) * 0.26, 0.075, Math.cos((tok.facing ?? 0) * Math.PI / 180) * 0.26]}
        rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.035, 3]} />
        <meshBasicMaterial color={color} />
      </mesh>
      {/* billboarded paper sprite (ComfyUI portrait slot) — HTML label, no web font */}
      <Billboard position={[0, 0.52, 0]}>
        <mesh>
          <planeGeometry args={[0.62, 0.82]} />
          <meshBasicMaterial color="#0b141d" transparent opacity={0.92} />
        </mesh>
        <mesh position={[0, 0, 0.001]}>
          <planeGeometry args={[0.58, 0.78]} />
          <meshBasicMaterial color={color} transparent opacity={0.14} />
        </mesh>
        <Html position={[0, 0, 0.01]} center distanceFactor={5} style={{ pointerEvents: 'none', width: 90, textAlign: 'center' }}>
          <div style={{ fontFamily: 'Consolas, monospace' }}>
            <div style={{ fontSize: 'var(--sys-font-size-display)', color, textShadow: `0 0 10px ${color}`, lineHeight: 1 }}>{String(name).charAt(0).toUpperCase()}</div>
            <div style={{ fontSize: 'var(--sys-font-size-micro)', color: '#cfe8f5', marginTop: 4 }}>{String(name).slice(0, 20)}</div>
          </div>
        </Html>
      </Billboard>
      {/* condition chips */}
      {(tok.conditions ?? []).length > 0 && (
        <Html position={[0, 1.05, 0]} center distanceFactor={7} style={{ pointerEvents: 'none' }}>
          <div style={{ display: 'flex', gap: 3 }}>
            {(tok.conditions ?? []).map((c) => (
              <span key={c} style={{ fontSize: 'var(--sys-font-size-micro)', letterSpacing: 1, color: '#ffb300', border: '1px solid rgba(255,179,0,.6)', background: 'rgba(20,12,0,.85)', padding: '1px 6px', whiteSpace: 'nowrap', textTransform: 'uppercase' }}>
                {c.replace(/^status_/, '')}
              </span>
            ))}
          </div>
        </Html>
      )}
    </group>
  );
}

/* ---------- hazard zone ---------- */
function Hazard({ hz, W, H }) {
  const [x, , z] = gridToWorld(hz.x, hz.y, W, H);
  const r = (hz.radius ?? 1) * CELL;
  const ref = useRef();
  const boom = useRef();
  useFrame((s) => {
    if (ref.current) ref.current.material.opacity = hz.triggered ? 0.5 : 0.16 + Math.sin(s.clock.elapsedTime * 2.4) * 0.08;
    if (boom.current && hz.triggered) {
      boom.current.scale.setScalar(1 + Math.sin(s.clock.elapsedTime * 3) * 0.12);
    }
  });
  const color = hz.triggered ? '#ff4d2a' : '#ffb300';
  return (
    <group position={[x, 0.02, z]}>
      <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[r, 40]} />
        <meshBasicMaterial color={color} transparent opacity={0.18} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[r - 0.02, r, 40]} />
        <meshBasicMaterial color={color} transparent opacity={0.7} />
      </mesh>
      {/* the canister itself */}
      <mesh position={[0, 0.12, 0]}>
        <cylinderGeometry args={[0.08, 0.08, 0.24, 10]} />
        <meshStandardMaterial color={hz.triggered ? '#3a1205' : '#4a4238'} emissive={color} emissiveIntensity={hz.triggered ? 1.4 : 0.15} />
      </mesh>
      {hz.triggered && (
        <mesh ref={boom} position={[0, 0.25, 0]}>
          <sphereGeometry args={[r * 0.55, 16, 16]} />
          <meshBasicMaterial color="#ff7a2a" transparent opacity={0.3} />
        </mesh>
      )}
      <Html position={[0, 0.55, 0]} center distanceFactor={8} style={{ pointerEvents: 'none' }}>
        <span style={{ fontSize: 'var(--sys-font-size-micro)', letterSpacing: 1.5, color, whiteSpace: 'nowrap', textShadow: `0 0 8px ${color}` }}>
          {hz.triggered ? '☠ IGNITED' : `⚠ ${hz.effect_id.replace(/^effect_/, '').replace(/_/g, ' ')}`}
        </span>
      </Html>
    </group>
  );
}

/* ---------- narrative d20 (cosmetic spin; result is computed on click) ---------- */
function NarrativeDie({ rolling }) {
  const ref = useRef();
  useFrame((s, dt) => {
    if (!ref.current) return;
    const spin = rolling ? 13 : 0.4;
    ref.current.rotation.x += dt * spin;
    ref.current.rotation.y += dt * spin * 0.8;
    ref.current.position.y = rolling ? 0.45 + Math.abs(Math.sin(s.clock.elapsedTime * 9)) * 0.4 : 0.35;
  });
  return (
    <mesh ref={ref} position={[0, 0.35, 2.6]}>
      <icosahedronGeometry args={[0.22, 0]} />
      <meshStandardMaterial color="#0d1b28" emissive="#33e1ff" emissiveIntensity={rolling ? 1.1 : 0.5} metalness={0.6} roughness={0.3} />
    </mesh>
  );
}

/* ================================================================== */
export default function LivingDiorama() {
  const { registry, manifest } = useGenesis();
  const combatUrid = manifest.find((m) => m.schema === 'Combat')?.urid;
  const combat = registry.get(combatUrid);
  const gs = combat?.grid_state;
  const [selected, setSelected] = useState(null);
  const [moveMode, setMoveMode] = useState(false);
  const [rolling, setRolling] = useState(false);
  const [dieResult, setDieResult] = useState(null);

  const { W, H } = useMemo(() => ({ W: gs?.grid_size?.width ?? 24, H: gs?.grid_size?.height ?? 16 }), [gs]);
  // R3F sizes its canvas from a ResizeObserver that can miss the very first
  // paint when the flex container settles a frame late. Nudge it after mount.
  useEffect(() => {
    const kick = () => window.dispatchEvent(new Event('resize'));
    const a = requestAnimationFrame(kick);
    const b = setTimeout(kick, 120);
    return () => { cancelAnimationFrame(a); clearTimeout(b); };
  }, []);
  if (!gs) return <div style={{ padding: 40, color: 'var(--dim)' }}>no Combat entity with grid_state in registry…</div>;

  const tokens = gs.tokens ?? [];
  const selTok = tokens.find((t) => t.token_id === selected);
  const selIdx = tokens.findIndex((t) => t.token_id === selected);
  const other = tokens.find((t) => t.token_id !== selected);

  const colorFor = (tok) => {
    const e = registry.get(tok.entity_id);
    if (e?.ui?.color || e?.ui?.color_hex) return e.ui.color ?? e.ui.color_hex;
    return tok.entity_id.startsWith('adversary') || tok.entity_id.includes('nexu') ? '#ff4d5a' : '#33e1ff';
  };

  const losBlocked = selTok && other && (other.cover === 'full' || (Math.abs((selTok.elevation ?? 0) - (other.elevation ?? 0)) > 4));

  const moveTo = (gx, gy) => {
    if (!moveMode || selIdx < 0) return;
    submitIntent('move_token', { combat: combatUrid, tokenIndex: selIdx, x: gx, y: gy });
    setMoveMode(false);
  };

  const rollDice = () => {
    if (rolling) return;
    setDieResult(null); setRolling(true);
    // compute the outcome up front; the die spin is purely cosmetic
    const d20 = 1 + Math.floor(Math.random() * 20);
    const narr = Math.random();
    const symbol = d20 === 20 || narr > 0.82 ? 'TRIUMPH' : d20 === 1 || narr < 0.22 ? 'DESPAIR' : narr > 0.5 ? 'ADVANTAGE' : 'THREAT';
    setTimeout(() => {
      setRolling(false);
      setDieResult({ d20, symbol });
      if (symbol === 'DESPAIR') {
        const hi = (gs.environmental_hazards ?? []).findIndex((h) => !h.triggered && h.trigger_source === 'despair');
        if (hi >= 0) {
          // THE BUTTERFLY, governed: the combat engine triggers the hazard,
          // the campaign engine records the ignition, and the Chaos matcher
          // grows a nemesis from the flag — all as ledgered events.
          submitIntent('trigger_hazard', { combat: combatUrid, hazardIndex: hi, hazard: gs.environmental_hazards[hi] });
        }
      }
    }, 1150);
  };

  const endTurn = () => {
    useGenesis.getState().addJournal('combat', 'Turn ended. The galaxy takes its turn…');
    submitIntent('end_turn');
  };

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <Canvas style={{ width: '100%', height: '100%', display: 'block' }} camera={{ position: [4.5, 5.2, 6.5], fov: 42 }} gl={{ preserveDrawingBuffer: true }} onPointerMissed={() => setSelected(null)}>
        <color attach="background" args={['#04070d']} />
        <fog attach="fog" args={['#04070d', 9, 20]} />
        <ambientLight intensity={gs.lighting === 'darkness' ? 0.15 : 0.4} />
        <pointLight position={[4, 6, 4]} intensity={gs.lighting === 'flickering' ? 26 : 40} color="#7fd4ff" />
        <OrbitControls maxPolarAngle={Math.PI / 2.15} minDistance={3} maxDistance={14} target={[0, 0, 0]} />

        <Suspense fallback={null}>

        {/* board */}
        <gridHelper args={[W * CELL, W, '#1d4a5e', '#10293a']} position={[0, 0.001, 0]} />
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}
          onClick={(e) => {
            if (!moveMode) return;
            const gx = Math.round(e.point.x / CELL + W / 2);
            const gy = Math.round(e.point.z / CELL + H / 2);
            moveTo(gx, gy);
          }}>
          <planeGeometry args={[W * CELL, H * CELL]} />
          <meshStandardMaterial color="#08121c" metalness={0.4} roughness={0.8} transparent opacity={0.95} />
        </mesh>
        {/* terrain flavor blocks */}
        {[[7, 3, 0.5], [15, 12, 0.8], [10, 10, 0.3], [19, 4, 0.6]].map(([gx, gy, h], i) => {
          const [x, , z] = gridToWorld(gx, gy, W, H);
          return (
            <mesh key={i} position={[x, h / 2, z]}>
              <boxGeometry args={[CELL * 1.6, h, CELL * 1.6]} />
              <meshStandardMaterial color="#101c28" metalness={0.5} roughness={0.7} emissive="#1899b8" emissiveIntensity={0.06} />
            </mesh>
          );
        })}

        {tokens.map((tok) => (
          <Token key={tok.token_id} tok={tok} entity={registry.get(tok.entity_id)} color={colorFor(tok)}
            W={W} H={H} selected={selected === tok.token_id} onSelect={setSelected} />
        ))}
        {(gs.environmental_hazards ?? []).map((hz) => <Hazard key={hz.hazard_id} hz={hz} W={W} H={H} />)}

        {/* line of sight */}
        {selTok && other && (
          <Line
            points={[
              [...gridToWorld(selTok.x, selTok.y, W, H).map((v, i) => (i === 1 ? (selTok.elevation ?? 0) * 0.14 + 0.4 : v))],
              [...gridToWorld(other.x, other.y, W, H).map((v, i) => (i === 1 ? (other.elevation ?? 0) * 0.14 + 0.4 : v))],
            ]}
            color={losBlocked ? '#ff4d5a' : '#59ffa3'} lineWidth={1.5} dashed dashSize={0.12} gapSize={0.08}
          />
        )}
        <NarrativeDie rolling={rolling} />
        </Suspense>
      </Canvas>

      {/* HUD: action economy for selected token */}
      {selTok && (
        <div className="holo-panel" style={{ position: 'absolute', left: 14, bottom: 14, padding: '10px 14px', minWidth: 250 }}>
          <div style={{ fontSize: 'var(--sys-font-size-meta)', letterSpacing: 1, color: 'var(--cyan)', marginBottom: 6 }}>
            {getName(registry.get(selTok.entity_id)) ?? selTok.entity_id}
            <span style={{ color: 'var(--dim)', marginLeft: 8, fontSize: 'var(--sys-font-size-caption)' }}>
              ({selTok.x},{selTok.y}) elev {selTok.elevation ?? 0}m · cover {selTok.cover ?? 'none'} · facing {selTok.facing ?? 0}°
            </span>
          </div>
          <span className="holo-btn" style={{ fontSize: 'var(--sys-font-size-label)', padding: '4px 10px' }}>Action</span>
          <span className="holo-btn ghost" style={{ fontSize: 'var(--sys-font-size-label)', padding: '4px 10px' }}>Bonus</span>
          <span className={`holo-btn ${moveMode ? 'primary' : 'ghost'}`} style={{ fontSize: 'var(--sys-font-size-label)', padding: '4px 10px' }}
            onClick={() => setMoveMode(!moveMode)}>{moveMode ? 'Click a cell…' : 'Move'}</span>
          {other && (
            <div style={{ fontSize: 'var(--sys-font-size-caption)', marginTop: 6, color: losBlocked ? 'var(--red)' : 'var(--green)' }}>
              LOS to {getName(registry.get(other.entity_id)) ?? other.entity_id}: {losBlocked ? 'BLOCKED (cover/elevation)' : 'CLEAR'}
            </div>
          )}
        </div>
      )}

      {/* dice + result */}
      <div style={{ position: 'absolute', right: 14, bottom: 14, textAlign: 'right' }}>
        {dieResult && (
          <div className="holo-panel" style={{ padding: '8px 16px', marginBottom: 8, display: 'inline-block' }}>
            <span style={{ fontSize: 'var(--sys-font-size-heading)', color: 'var(--cyan)', textShadow: '0 0 10px var(--cyan-glow)' }}>d20: {dieResult.d20}</span>
            <span style={{
              marginLeft: 12, fontSize: 'var(--sys-font-size-control)', letterSpacing: 2,
              color: dieResult.symbol === 'DESPAIR' ? 'var(--red)' : dieResult.symbol === 'TRIUMPH' ? 'var(--gold)' : dieResult.symbol === 'ADVANTAGE' ? 'var(--green)' : 'var(--amber)',
            }}>◆ {dieResult.symbol}</span>
            {dieResult.symbol === 'DESPAIR' && <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--red)', marginTop: 3 }}>the fuel canister ignites — RFC6902 patch applied</div>}
            {dieResult.symbol === 'TRIUMPH' && <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--gold)', marginTop: 3 }}>narrative advantage — GM spends on the scene</div>}
          </div>
        )}
        <div>
          <span className="holo-btn primary" onClick={rollDice}>{rolling ? 'rolling…' : 'Roll Narrative Dice'}</span>
          <span className="holo-btn danger" onClick={endTurn}>End Turn ⏻</span>
        </div>
        <div style={{ fontSize: 'var(--sys-font-size-label)', color: 'var(--dim)', marginTop: 4 }}>lighting: {gs.lighting} · drag to rotate the holotable</div>
      </div>
    </div>
  );
}
