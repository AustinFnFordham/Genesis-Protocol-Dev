/* PANEL 3 (RIGHT): COMMAND & RECORD.
 * Interactive Journal (Bethesda-style log of everything that happened) +
 * the Galactic Map tab for plotting hyperspace courses. Ship tab reserved. */
import React, { useEffect, useRef, useState } from 'react';
import { useGenesis } from '../state/store.js';
import GalacticMap from './GalacticMap.jsx';
import NemesisWeb from './NemesisWeb.jsx';
import ShipManagement from './ShipManagement.jsx';
import DiceFeed from './DiceFeed.jsx';

const KIND_STYLE = {
  system: { color: 'var(--dim)', icon: '◈' },
  event: { color: 'var(--cyan)', icon: '◆' },
  travel: { color: 'var(--cyan)', icon: '➤' },
  progression: { color: 'var(--gold)', icon: '⬢' },
  combat: { color: 'var(--red)', icon: '✦' },
  dialogue: { color: '#ff8899', icon: '❝' },
  nemesis: { color: 'var(--red)', icon: '☠' },
};

export default function CommandPanel() {
  const { journal, patchLog, gmCampaign, restartCampaign, restartBusy, openAddCharacter } = useGenesis();
  const proj = useGenesis((s) => s.mounted?.projection);   // header binds to the mounted projection, NOT the legacy save
  const [tab, setTab] = useState('journal');
  const feedRef = useRef();
  useEffect(() => { feedRef.current?.scrollTo(0, 99999); }, [journal]);

  const onRestart = async () => {
    if (!gmCampaign) return;
    if (!window.confirm(`Restart "${gmCampaign}" from its opening crawl?\n\nCLEARED (backed up as a regression fixture, not deleted): transcript, chronicle, journal, active scene, session runtime.\nRETAINED: opening crawl, campaign foundation, character definitions.`)) return;
    await restartCampaign(gmCampaign);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div style={{ padding: '8px 8px 2px', display: 'flex' }}>
        {[['journal', 'Journal'], ['dice', 'Dice'], ['map', 'Map'], ['nemesis', 'Nemesis'], ['ship', 'Ship']].map(([k, label]) => (
          <span key={k} className={`holo-btn ${tab === k ? 'primary' : 'ghost'}`}
            style={{ fontSize: 'var(--sys-font-size-micro)', padding: '4px 8px' }}
            onClick={() => setTab(k)}>{label}</span>
        ))}
      </div>

      {tab === 'journal' && (
        <div ref={feedRef} style={{ flex: 1, overflowY: 'auto', padding: '6px 12px', fontSize: 'var(--sys-font-size-meta)', lineHeight: 1.55 }}>
          {gmCampaign && (
            <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
              <span className="holo-btn ghost" style={{ fontSize: 'var(--sys-font-size-micro)', padding: '4px 8px' }} onClick={openAddCharacter}>+ Add Character</span>
              <span className="holo-btn ghost" style={{ fontSize: 'var(--sys-font-size-micro)', padding: '4px 8px', opacity: restartBusy ? 0.5 : 1 }} onClick={onRestart}>
                {restartBusy ? 'restarting…' : '↻ Restart from Opening'}
              </span>
            </div>
          )}
          {proj?.campaign && (
            <div style={{ borderBottom: '1px solid var(--sys-color-line)', paddingBottom: 6, marginBottom: 6 }}>
              <div style={{ color: 'var(--sys-color-accent)', letterSpacing: 1, fontSize: 'var(--sys-font-size-body)' }}>{proj.campaign.title}</div>
              <div style={{ fontSize: 'var(--sys-font-size-meta)', color: 'var(--sem-text-secondary)' }}>
                {proj.active_engagement?.active_scene?.location ?? proj.campaign.era} · rev {proj.state_revision}
              </div>
            </div>
          )}
          <div style={{ fontSize: 'var(--sys-font-size-micro)', letterSpacing: 2, color: 'var(--dim)', marginBottom: 4 }}>CHRONICLE — structured campaign record</div>
          {journal.length === 0 && <div style={{ color: 'var(--dim)' }}>the record is empty — the galaxy awaits your first move.</div>}
          {journal.map((j, i) => {
            const st = KIND_STYLE[j.kind] ?? KIND_STYLE.system;
            return (
              <div key={j.eventId ?? i} style={{ margin: '7px 0', animation: 'bootIn .4s ease-out' }}>
                <span style={{ color: st.color, marginRight: 6 }}>{st.icon}</span>
                <span style={{ fontSize: 'var(--sys-font-size-micro)', color: 'var(--dim)', marginRight: 6 }}>
                  {new Date(j.t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                <span>{j.text}</span>
                {(j.location || j.participants?.length) && (
                  <div style={{ fontSize: 'var(--sys-font-size-micro)', color: 'var(--dim)', marginLeft: 18 }}>
                    {j.location && <>◈ {j.location} </>}
                    {j.participants?.length > 0 && <>· {j.participants.filter(Boolean).join(', ')}</>}
                  </div>
                )}
              </div>
            );
          })}
          <div className="sec-h">Patch Bus — {patchLog.length} batches</div>
          {patchLog.slice(-4).map((p, i) => (
            <div key={i} style={{ fontSize: 'var(--sys-font-size-label)', color: 'var(--dim)' }}>
              {p.ops.map((o) => `${o.op} ${o.path}`).join(' · ')} → {p.target}
            </div>
          ))}
        </div>
      )}

      {tab === 'dice' && <DiceFeed />}

      {tab === 'map' && (
        <div style={{ flex: 1, overflowY: 'auto', padding: '4px 6px' }}>
          <GalacticMap compact />
        </div>
      )}

      {tab === 'nemesis' && (
        <div style={{ flex: 1, overflowY: 'auto', padding: '4px 6px' }}>
          <NemesisWeb />
        </div>
      )}

      {tab === 'ship' && (
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <ShipManagement />
        </div>
      )}
    </div>
  );
}
