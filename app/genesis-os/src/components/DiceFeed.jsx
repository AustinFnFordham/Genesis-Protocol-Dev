/* DICE FEED (Command & Record) — the table's dice, rolled where you can see
 * them. Every roll comes from the deterministic dice service and is
 * steward-verified; this feed ANIMATES results, it never generates them.
 * Die shape is dynamic — derived from the formula (d4/d6/d8/d10/d12/d20). */
import React, { useEffect, useRef, useState } from 'react';
import { useGenesis } from '../state/store.js';

const DIE_GLYPH = { 4: '▲', 6: '■', 8: '◆', 10: '◇', 12: '⬟', 20: '⬢' };
const sidesOf = (formula) => parseInt(String(formula).match(/d(\d+)/)?.[1] ?? '20', 10);

function Die({ roll }) {
  const sides = sidesOf(roll.formula);
  const [spin, setSpin] = useState(true);
  const [face, setFace] = useState('?');
  useEffect(() => {
    let n = 0;
    const iv = setInterval(() => {
      n += 1;
      setFace(1 + Math.floor(Math.random() * sides)); // cosmetic tumble only
      if (n > 9) { clearInterval(iv); setSpin(false); setFace(null); }
    }, 70);
    return () => clearInterval(iv);
  }, []); // eslint-disable-line
  const nat = (roll.individual_dice ?? []).join('+');
  const crit = sides === 20 && (roll.individual_dice ?? []).includes(20);
  const fumble = sides === 20 && (roll.individual_dice ?? []).includes(1);
  return (
    <div className="holo-panel" style={{ padding: '6px 10px', marginBottom: 6, borderColor: crit ? 'var(--gold)' : fumble ? 'var(--red)' : 'var(--amber)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{
          fontSize: 'var(--sys-font-size-heading)', color: crit ? 'var(--gold)' : fumble ? 'var(--red)' : 'var(--amber)',
          display: 'inline-block', transition: 'transform .07s',
          transform: spin ? `rotate(${Math.random() * 60 - 30}deg) scale(1.1)` : 'none',
          textShadow: '0 0 12px currentColor',
        }}>{DIE_GLYPH[sides] ?? '⬢'}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 'var(--sys-font-size-caption)', letterSpacing: 1, color: 'var(--dim)' }}>
            {roll.formula}{roll.mode !== 'normal' ? ` (${roll.mode})` : ''} · {roll.purpose || 'roll'}
          </div>
          <div style={{ fontSize: 'var(--sys-font-size-micro)', color: 'var(--dim)' }}>{roll.context ?? ''}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          {spin
            ? <span style={{ fontSize: 'var(--sys-font-size-narrative)', color: 'var(--dim)' }}>{face}</span>
            : <>
              <span style={{ fontSize: 'var(--sys-font-size-title)', color: crit ? 'var(--gold)' : fumble ? 'var(--red)' : 'var(--cyan)' }}>{roll.final_total}</span>
              <div style={{ fontSize: 'var(--sys-font-size-micro)', color: 'var(--dim)' }}>[{nat}]{roll.modifiers ? `${roll.modifiers > 0 ? '+' : ''}${roll.modifiers}` : ''}</div>
            </>}
        </div>
      </div>
      {crit && !spin && <div style={{ fontSize: 'var(--sys-font-size-micro)', color: 'var(--gold)', letterSpacing: 2, marginTop: 2 }}>◈ NATURAL TWENTY</div>}
      {fumble && !spin && <div style={{ fontSize: 'var(--sys-font-size-micro)', color: 'var(--red)', letterSpacing: 2, marginTop: 2 }}>◈ NATURAL ONE</div>}
    </div>
  );
}

export default function DiceFeed() {
  const diceEvents = useGenesis((s) => s.diceEvents);
  const ref = useRef();
  useEffect(() => { ref.current?.scrollTo(0, 999999); }, [diceEvents]);
  if (!diceEvents.length) {
    return <div style={{ padding: 16, color: 'var(--dim)', fontSize: 'var(--sys-font-size-caption)' }}>
      No rolls yet. When the Combat Master calls for dice, they land here —<br />
      seeded, service-rolled, steward-verified. The table never lies.
    </div>;
  }
  return (
    <div ref={ref} style={{ flex: 1, overflowY: 'auto', padding: '6px 10px' }}>
      {diceEvents.map((r, i) => <Die key={`${r.roll_id}_${i}`} roll={r} />)}
    </div>
  );
}
