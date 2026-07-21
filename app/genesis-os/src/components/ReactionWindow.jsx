/* REACTION WINDOW (§17.8) — the quick-time prompt. When stakes shift but
 * full combat isn't warranted, the GM offers a timed choice. Options are
 * suggestions from the resolved mechanics; free action always remains.
 * Choosing submits a DECLARATION — the window decides nothing itself. */
import React, { useEffect, useState } from 'react';
import { useGenesis } from '../state/store.js';

export default function ReactionWindow() {
  const { reactionWindow, setReactionWindow, setActionPrefill, setEngagement } = useGenesis();
  const [left, setLeft] = useState(null);
  const [custom, setCustom] = useState('');

  useEffect(() => {
    if (!reactionWindow) { setLeft(null); return; }
    setLeft(reactionWindow.timer_seconds ?? 10);
    const iv = setInterval(() => setLeft((l) => {
      if (l <= 1) { clearInterval(iv); return 0; }
      return l - 1;
    }), 1000);
    return () => clearInterval(iv);
  }, [reactionWindow]);

  if (!reactionWindow) return null;
  const choose = (text) => {
    setReactionWindow(null);
    setActionPrefill(text);
    setEngagement('dialogue');
  };

  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(4,7,13,0.7)', backdropFilter: 'blur(4px)' }}>
      <div className="holo-panel boot-in" style={{ width: 'min(92%, 520px)', padding: '16px 22px', borderColor: 'var(--red)' }}>
        <div style={{ fontSize: 'var(--sys-font-size-caption)', letterSpacing: 3, color: 'var(--red)' }}>◈ REACTION WINDOW
          {left != null && <span style={{ float: 'right', color: left <= 3 ? 'var(--red)' : 'var(--amber)', fontSize: 'var(--sys-font-size-control)' }}>{left}s</span>}
        </div>
        <div style={{ fontSize: 'var(--sys-font-size-control)', margin: '10px 0 14px', lineHeight: 1.5 }}>{reactionWindow.prompt}</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {(reactionWindow.options ?? []).map((o) => (
            <span key={o} className="holo-btn primary" style={{ fontSize: 'var(--sys-font-size-note)', padding: '7px 16px' }} onClick={() => choose(o)}>{o}</span>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
          <input value={custom} onChange={(e) => setCustom(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && custom.trim() && choose(custom)}
            placeholder="…or attempt anything plausible"
            style={{ flex: 1, background: 'rgba(10,20,31,.8)', border: '1px solid var(--line)', color: '#cfe8f5', padding: '6px 10px', fontSize: 'var(--sys-font-size-note)', fontFamily: 'inherit' }} />
          <span className="holo-btn ghost" style={{ fontSize: 'var(--sys-font-size-label)', padding: '6px 10px' }} onClick={() => setReactionWindow(null)}>dismiss</span>
        </div>
        {left === 0 && <div style={{ fontSize: 'var(--sys-font-size-label)', color: 'var(--dim)', marginTop: 8 }}>the moment passes — hesitation is also a choice the world sees.</div>}
      </div>
    </div>
  );
}
