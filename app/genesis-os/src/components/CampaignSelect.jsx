/* CAMPAIGN SELECT — the campaign-selection layer. One campaign instance
 * mounts into the controller stack at a time; the previous unloads cleanly.
 * Worlds never bleed into one another. */
import React, { useEffect, useState } from 'react';
import { useGenesis } from '../state/store.js';

const GM_API = 'http://localhost:8788/api/v1/gm';

export default function CampaignSelect() {
  const [campaigns, setCampaigns] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await (await fetch(`${GM_API}/campaigns`)).json();
        setCampaigns(r.campaigns);
      } catch { setErr('API bridge offline — start api_bridge/server.py'); }
    })();
  }, []);

  const mount = async (cid) => {
    if (busy) return;
    setBusy(true);
    try {
      const g = useGenesis.getState();
      g.setUnresolvedAction(null);
      // ATOMIC MOUNT (Contract Rev 1.1): the coordinator increments the epoch,
      // fetches the WHOLE projection, verifies campaign+epoch, and commits it in
      // one set(). No sequential per-field hydration; stale responses discarded.
      const res = await g.mountProjection(cid);
      if (res && res.ok === false) throw new Error(res.error ?? 'mount failed');
      g.setEngagement('dialogue');
    } catch (e) { setErr(String(e.message)); }
    setBusy(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 14 }}>
      <div style={{ letterSpacing: 4, color: 'var(--cyan)', fontSize: 'var(--sys-font-size-body)' }}>CAMPAIGN SELECT</div>
      <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--dim)', letterSpacing: 1 }}>one campaign mounts into the controller stack at a time</div>
      {err && <div style={{ color: '#ff4d5a', fontSize: 'var(--sys-font-size-note)' }}>{err}</div>}
      {campaigns === null && !err && <div style={{ color: 'var(--dim)', fontSize: 'var(--sys-font-size-note)' }}>reaching the bridge…</div>}
      {(campaigns ?? []).map((c) => (
        <div key={c.campaign_id} className="holo-panel" onClick={() => mount(c.campaign_id)}
          style={{ width: 420, padding: '12px 18px', cursor: 'pointer', borderColor: c.mounted ? 'var(--gold)' : undefined }}>
          <div style={{ color: c.mounted ? 'var(--gold)' : 'var(--cyan)', fontSize: 'var(--sys-font-size-control)', letterSpacing: 1 }}>
            {c.name} {c.mounted && '◈ MOUNTED'}
          </div>
          <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--dim)', marginTop: 3 }}>
            {c.era} · {c.player}
          </div>
          <div style={{ fontSize: 'var(--sys-font-size-micro)', color: 'var(--dim)', marginTop: 2 }}>
            {c.source} · {c.instantiated ? 'save exists — resumes' : 'first mount — instantiates'}
          </div>
        </div>
      ))}
      <div className="holo-panel" onClick={() => useGenesis.getState().setEngagement('creator')}
        style={{ width: 420, padding: '12px 18px', cursor: 'pointer', borderStyle: 'dashed' }}>
        <div style={{ color: 'var(--dim)', fontSize: 'var(--sys-font-size-control)', letterSpacing: 1 }}>+ NEW CAMPAIGN</div>
        <div style={{ fontSize: 'var(--sys-font-size-label)', color: 'var(--dim)', marginTop: 3 }}>forge a character; a campaign instantiates around them</div>
      </div>
      {busy && <div style={{ color: 'var(--dim)', fontSize: 'var(--sys-font-size-note)' }}>mounting…</div>}
    </div>
  );
}
