/* TACTICAL VIEW — mounted-runtime mode. Tokens resolve through the SAME
 * truth path as the anchor: gmRuntime.combat.tokens (initialized by the
 * Combat Master on escalation). Clicks submit DECLARATIONS — this screen
 * mutates nothing. Always provides a route back to the scene. The legacy
 * holotable (registry test data) renders only when no campaign is mounted. */
import React, { useState } from 'react';
import { useGenesis } from '../state/store.js';

const CELL = 26;

export default function TacticalRuntime() {
  const { gmRuntime, setEngagement, setActionPrefill, unresolvedAction } = useGenesis();
  const combat = gmRuntime?.combat;
  const [sel, setSel] = useState(null);

  const back = () => setEngagement(unresolvedAction?.view && unresolvedAction.view !== 'diorama' ? unresolvedAction.view : 'dialogue');

  if (!combat?.active) {
    return (
      <div style={{ padding: 30, color: 'var(--dim)', fontSize: 'var(--sys-font-size-meta)', textAlign: 'center' }}>
        No active combat in the mounted campaign.<br />
        <span style={{ fontSize: 'var(--sys-font-size-caption)' }}>The Tactical View opens automatically when the Combat Master escalates a scene.</span><br /><br />
        <span className="holo-btn" style={{ fontSize: 'var(--sys-font-size-caption)', padding: '6px 14px' }} onClick={back}>◂ RETURN TO SCENE</span>
      </div>
    );
  }

  const { tokens = [], grid = { width: 20, height: 14 }, initiative = [], turn, round } = combat;
  const declare = (text) => { setActionPrefill(text); setEngagement('dialogue'); };
  const selTok = tokens.find((t) => t.token_id === sel);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '6px 14px', borderBottom: '1px solid var(--line)' }}>
        <span className="holo-btn ghost" style={{ fontSize: 'var(--sys-font-size-label)', padding: '3px 10px' }} onClick={back}>◂ RETURN TO SCENE</span>
        <span style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--red)', letterSpacing: 2 }}>⚔ ROUND {round}</span>
        <span style={{ fontSize: 'var(--sys-font-size-label)', color: 'var(--dim)' }}>initiative: {initiative.map((p) => tokens.find((t) => t.token_id === p)?.name ?? p).join(' → ')}</span>
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 'var(--sys-font-size-label)', color: 'var(--amber)' }}>turn: {tokens.find((t) => t.token_id === turn)?.name ?? turn}</span>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 14 }}>
        <svg width={grid.width * CELL} height={grid.height * CELL} style={{ background: 'rgba(10,20,31,.5)', border: '1px solid var(--line)' }}>
          {[...Array(grid.width + 1)].map((_, i) => <line key={`v${i}`} x1={i * CELL} y1={0} x2={i * CELL} y2={grid.height * CELL} stroke="#12303f" strokeWidth="0.5" />)}
          {[...Array(grid.height + 1)].map((_, i) => <line key={`h${i}`} x1={0} y1={i * CELL} x2={grid.width * CELL} y2={i * CELL} stroke="#12303f" strokeWidth="0.5" />)}
          {/* click a cell while a token is selected → movement declaration */}
          <rect x={0} y={0} width={grid.width * CELL} height={grid.height * CELL} fill="transparent"
            onClick={(e) => {
              if (!selTok?.is_pc) return;
              const r = e.currentTarget.getBoundingClientRect();
              const gx = Math.floor((e.clientX - r.left) / CELL), gy = Math.floor((e.clientY - r.top) / CELL);
              declare(`I move to grid position ${gx},${gy}. `);
            }} />
          {tokens.map((t) => (
            <g key={t.token_id} style={{ cursor: 'pointer' }} onClick={(e) => { e.stopPropagation(); setSel(t.token_id); }}>
              <circle cx={t.x * CELL + CELL / 2} cy={t.y * CELL + CELL / 2} r={CELL * 0.38}
                fill={t.is_pc ? '#0a2a3a' : '#3a0a12'}
                stroke={sel === t.token_id ? 'var(--gold)' : t.is_pc ? 'var(--cyan)' : 'var(--red)'}
                strokeWidth={turn === t.token_id ? 2.5 : 1.2} />
              <text x={t.x * CELL + CELL / 2} y={t.y * CELL + CELL / 2 + 3} textAnchor="middle" fontSize="9"
                fill={t.is_pc ? 'var(--cyan)' : '#ff8899'}>{(t.name ?? '?').slice(0, 2).toUpperCase()}</text>
              <text x={t.x * CELL + CELL / 2} y={t.y * CELL - 4} textAnchor="middle" fontSize="7" fill="var(--dim)">{t.name}</text>
            </g>
          ))}
        </svg>
        {selTok && (
          <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--cyan)', alignSelf: 'center' }}>{selTok.name}:</span>
            {selTok.is_pc ? (<>
              <span className="holo-btn ghost" style={{ fontSize: 'var(--sys-font-size-label)', padding: '3px 10px' }} onClick={() => declare('I move toward ')}>Move</span>
              <span className="holo-btn ghost" style={{ fontSize: 'var(--sys-font-size-label)', padding: '3px 10px' }} onClick={() => declare('I take a defensive stance. ')}>Guard</span>
              <span className="holo-btn ghost" style={{ fontSize: 'var(--sys-font-size-label)', padding: '3px 10px' }} onClick={() => declare('I end my turn. ')}>End Turn</span>
            </>) : (
              <span className="holo-btn ghost" style={{ fontSize: 'var(--sys-font-size-label)', padding: '3px 10px' }} onClick={() => declare(`I attack ${selTok.name} `)}>Attack {selTok.name}</span>
            )}
          </div>
        )}
        <div style={{ fontSize: 'var(--sys-font-size-micro)', color: 'var(--dim)', marginTop: 8, letterSpacing: 1 }}>
          tokens resolve from the mounted runtime · clicks submit declarations · the Combat Master owns this grid
        </div>
      </div>
    </div>
  );
}
