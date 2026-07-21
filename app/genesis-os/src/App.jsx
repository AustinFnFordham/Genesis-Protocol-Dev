/* GENESIS//OS — the 3-panel game shell (Phase 2).
 * LEFT: Character Anchor (persistent identity). CENTER: Active Engagement
 * (dialogue / diorama / creator, overlay modals). RIGHT: Command & Record
 * (journal + galactic map). DATA mode keeps the old registry browser for dev.
 * Boot: Tauri -> API bridge -> static fallback; a persisted save state skips
 * straight into the campaign. */
import React, { useEffect, useState } from 'react';
import { useGenesis } from './state/store.js';
import { loadRegistry } from './state/registry.js';
import CharacterAnchor from './components/CharacterAnchor.jsx';
import CharacterForge from './components/CharacterForge.jsx';
import CharacterCreator from './components/CharacterCreator.jsx';
import LivingDiorama from './components/LivingDiorama.jsx';
import DialogueSystem from './components/DialogueSystem.jsx';
import CommandPanel from './components/CommandPanel.jsx';
import ProgressionTree from './components/ProgressionTree.jsx';
import Workbench from './components/Workbench.jsx';
import GmSession from './components/GmSession.jsx';
import CampaignSelect from './components/CampaignSelect.jsx';
import ActionPanel from './components/ActionPanel.jsx';
import ShipManagement from './components/ShipManagement.jsx';
import ShipStations from './components/ShipStations.jsx';
import TacticalRuntime from './components/TacticalRuntime.jsx';
import ReactionWindow from './components/ReactionWindow.jsx';
import AddCharacter from './components/AddCharacter.jsx';
import './styles/design-tokens.css';
import './styles/component-tokens.css';
import './theme.css';

class Boundary extends React.Component {
  constructor(p) { super(p); this.state = { err: null }; }
  static getDerivedStateFromError(err) { return { err }; }
  render() {
    if (this.state.err) {
      return <div style={{ padding: 30, color: 'var(--red)', fontSize: 'var(--sys-font-size-control)', whiteSpace: 'pre-wrap' }}>
        MODULE FAULT — {String(this.state.err?.message ?? this.state.err)}</div>;
    }
    return this.props.children;
  }
}

export default function App() {
  const { boot, campaignActive, engagement, setEngagement, overlay, source, manifest, select, selected, unresolvedAction, gmCampaign, mountedCampaignId } = useGenesis();
  const cid = mountedCampaignId ?? gmCampaign ?? null; // the campaign every visible region must agree on
  const [err, setErr] = useState(null);
  const [shellMode, setShellMode] = useState('game'); // 'game' | 'data'

  useEffect(() => {
    loadRegistry().then(boot).catch((e) => setErr(String(e)));
    // resync to whatever the bridge has mounted, then load the ONE mounted
    // projection so every panel (D–G) reads command_record/operative from it.
    (async () => {
      const rt = await useGenesis.getState().refreshGmRuntime();
      if (rt?.mounted) useGenesis.getState().mountProjection(rt.mounted);
    })();
  }, [boot]);

  if (err) {
    return <div className="holo-panel" style={{ margin: 60, padding: 30, color: 'var(--red)' }}>
      <div className="holo-title">SYSTEM FAULT</div><div style={{ padding: 16 }}>BOOT FAILURE: {err}</div></div>;
  }

  /* ---------- DATA mode: the old registry browser + forge, for dev ---------- */
  if (shellMode === 'data') {
    return (
      <div className="boot-in" style={{ display: 'grid', gridTemplateColumns: '292px 1fr', gap: 12, height: '100vh', padding: 12 }}>
        <nav className="holo-panel" style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div className="holo-title">Genesis // Data
            <span style={{ flex: 1 }} />
            <span style={{ cursor: 'pointer', color: 'var(--cyan)', fontSize: 'var(--sys-font-size-caption)' }} onClick={() => setShellMode('game')}>▶ GAME</span>
          </div>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {manifest.map((m) => (
              <div key={m.urid} className={`holo-card ${selected === m.urid ? 'sel' : ''}`} onClick={() => select(m.urid)}>
                <div className="n">{m.name ?? m.urid}<span className={`badge ${m.tier === 'wip' ? 'wip' : 'gold'}`}>{(m.tier ?? 'gold').toUpperCase()}</span></div>
                <div className="t">{m.schema} · {m.urid}</div>
              </div>
            ))}
          </div>
        </nav>
        <main className="holo-panel" style={{ minHeight: 0, position: 'relative', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Boundary><CharacterForge /></Boundary>
        </main>
      </div>
    );
  }

  /* ---------- GAME mode: the 3-panel shell ---------- */
  return (
    <div className="boot-in" style={{ display: 'grid', gridTemplateColumns: '250px 1fr 330px', gap: 10, height: '100vh', padding: 10, position: 'relative' }}>
      {/* PANEL 1 — the character anchor */}
      <section className="holo-panel" data-region="operative" data-campaign-id={cid ?? ''} style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div className="holo-title" data-region="campaign-header" data-campaign-id={cid ?? ''}>Operative {cid && <span style={{ fontSize: 'var(--sys-font-size-micro)', color: 'var(--gold)', marginLeft: 6 }}>◈ {cid}</span>}</div>
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }} data-region="party" data-campaign-id={cid ?? ''}><Boundary><CharacterAnchor /></Boundary></div>
        <div data-region="equipment" data-campaign-id={cid ?? ''}><Boundary><ActionPanel /></Boundary></div>
      </section>

      {/* PANEL 2 — active engagement */}
      <main className="holo-panel" data-region="active-engagement" data-campaign-id={cid ?? ''} style={{ minHeight: 0, position: 'relative', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div className="holo-title">
          {campaignActive ? 'Active Engagement' : 'New Game'}
          <span style={{ flex: 1 }} />
          {[['select', 'CAMPAIGNS'], ['dialogue', '◈ NARRATIVE'], ['diorama', 'TACTICAL'], ['ship', 'SHIP']].map(([m, label]) => (
            <span key={m} style={{ cursor: 'pointer', fontSize: 'var(--sys-font-size-caption)', letterSpacing: 2, marginLeft: 12, color: engagement === m ? 'var(--cyan)' : 'var(--dim)' }}
              onClick={() => setEngagement(m)}>{label}</span>
          ))}
          <span style={{ cursor: 'pointer', fontSize: 'var(--sys-font-size-caption)', letterSpacing: 2, marginLeft: 12, color: 'var(--dim)' }}
            onClick={() => setShellMode('data')}>⚙ DATA</span>
        </div>
        {/* the unresolved-action guard: inspect freely, never abandon by accident */}
        {unresolvedAction && engagement !== unresolvedAction.view && (
          <div style={{ padding: '5px 14px', background: 'rgba(255,213,79,.08)', borderBottom: '1px solid var(--amber)', fontSize: 'var(--sys-font-size-caption)', color: 'var(--amber)', letterSpacing: 1 }}>
            ⚠ {unresolvedAction.label}
            <span style={{ cursor: 'pointer', marginLeft: 10, textDecoration: 'underline' }}
              onClick={() => setEngagement(unresolvedAction.view)}>▸ return</span>
          </div>
        )}
        <Boundary key={engagement}>
          {engagement === 'select' && <CampaignSelect />}
          {engagement === 'creator' && <CharacterCreator onCommitted={() => { /* startCampaign flips engagement */ }} />}
          {engagement === 'dialogue' && <DialogueSystem />}
          {engagement === 'diorama' && (gmCampaign ? <TacticalRuntime /> : <LivingDiorama />)}
          {engagement === 'ship' && (gmCampaign ? <ShipStations /> : <ShipManagement />)}
          {/* Living Table merged INTO Narrative — 'gm' routes alias to it */}
          {engagement === 'gm' && <DialogueSystem />}
        </Boundary>
      </main>

      {/* PANEL 3 — command & record */}
      <section className="holo-panel" data-region="command-record" data-campaign-id={cid ?? ''} style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div className="holo-title">Command &amp; Record <span style={{ flex: 1 }} /><span style={{ fontSize: 'var(--sys-font-size-micro)', color: 'var(--dim)' }}>src: {source}</span></div>
        <Boundary><CommandPanel /></Boundary>
      </section>

      {/* frosted-glass overlays */}
      {overlay === 'progression' && <Boundary><ProgressionTree /></Boundary>}
      {overlay === 'workbench' && <Boundary><Workbench /></Boundary>}
      <Boundary><ReactionWindow /></Boundary>
      <Boundary><AddCharacter /></Boundary>
    </div>
  );
}
