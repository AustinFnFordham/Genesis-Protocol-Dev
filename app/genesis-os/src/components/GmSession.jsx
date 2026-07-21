/* THE LIVING TABLE — four-controller AI GM session (GENESIS_GM_ARCHITECTURE.md).
 * Dialogue is not a cutscene: every beat renders with its interruption window,
 * the four suggestions are chips (never rails), and the free-action line is
 * always live. Mechanics arrive as a verified dice readout — the Combat
 * Master resolved them, the Steward audited them, the GM narrated them.
 * This component only ever SUBMITS DECLARATIONS. It mutates nothing. */
import React, { useEffect, useRef, useState } from 'react';
import { useGenesis } from '../state/store.js';

const GM_API = 'http://localhost:8788/api/v1/gm';

function DiceChip({ d }) {
  return (
    <span style={{ display: 'inline-block', margin: '0 6px 4px 0', padding: '2px 8px', border: '1px solid var(--amber)', borderRadius: 3, fontSize: 'var(--sys-font-size-label)', color: 'var(--amber)' }}>
      ⚂ {d.formula} → [{(d.dice ?? []).join(',')}] = {d.total} <span style={{ color: 'var(--dim)' }}>{d.purpose}</span>
    </span>
  );
}

function Beat({ b, npcNames }) {
  const speaker = (b.speaker ?? 'narrator').replace(/^npc_id\|/, '');
  const display = npcNames[speaker] ?? (speaker === 'narrator' ? null : speaker);
  return (
    <div style={{ marginBottom: 10, paddingLeft: display ? 0 : 8, borderLeft: display ? 'none' : '2px solid var(--line)' }}>
      {display && <div style={{ color: 'var(--cyan)', fontSize: 'var(--sys-font-size-caption)', letterSpacing: 1.5 }}>{display.toUpperCase()}
        {b.interruption_window === 'open' && <span style={{ color: 'var(--dim)', marginLeft: 8, fontSize: 'var(--sys-font-size-micro)' }}>▸ interruptible</span>}
      </div>}
      {b.spoken_text && <div style={{ fontSize: 'var(--sys-font-size-meta)', margin: '2px 0' }}>“{b.spoken_text}”</div>}
      {b.narration && <div style={{ fontSize: 'var(--sys-font-size-note)', color: '#9fc4d8', fontStyle: 'italic' }}>{b.narration}</div>}
      {b.physical_behavior && <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--dim)' }}>{b.physical_behavior}</div>}
      {b.environmental_change && <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--amber)' }}>{b.environmental_change}</div>}
    </div>
  );
}

export default function GmSession() {
  const addJournal = useGenesis((s) => s.addJournal);
  const gmCampaign = useGenesis((s) => s.gmCampaign);
  const actionPrefill = useGenesis((s) => s.actionPrefill);
  const [feed, setFeed] = useState([]);       // [{kind:'beats'|'player'|'mechanics', ...}]
  const [options, setOptions] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [online, setOnline] = useState(null);
  const [npcNames, setNpcNames] = useState({});
  const [combatActive, setCombatActive] = useState(false);
  const feedRef = useRef();
  useEffect(() => { feedRef.current?.scrollTo(0, 999999); }, [feed, busy]);

  // Session boot: pull the MOUNTED campaign's visible runtime, open the scene.
  useEffect(() => {
    (async () => {
      try {
        const rt = await useGenesis.getState().refreshGmRuntime();
        if (!rt?.mounted) { setOnline('unmounted'); return; }
        const names = Object.fromEntries(Object.entries(rt.active_npcs ?? {}).map(([k, v]) => [k, v.name ?? k]));
        setNpcNames(names);
        setOnline(true);
        setCombatActive(!!rt.combat?.active);
        setFeed([{ kind: 'system', text: `${rt.campaign?.era} — ${rt.campaign?.current_location}. Objectives: ${(rt.campaign?.active_objectives ?? []).join('; ')}` }]);
      } catch { setOnline(false); }
    })();
  }, [gmCampaign]);

  // Contextual action panel prefills land here.
  useEffect(() => {
    if (actionPrefill) { setInput(actionPrefill); useGenesis.getState().setActionPrefill(''); }
  }, [actionPrefill]);

  const declare = async (text) => {
    const decl = text.trim();
    if (!decl || busy) return;
    setBusy(true); setInput(''); setOptions([]);
    setFeed((f) => [...f, { kind: 'player', text: decl }]);
    try {
      const r = await fetch(`${GM_API}/turn`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ declaration: decl }),
      });
      const t = await r.json();
      if (t.status !== 'ok') {
        setFeed((f) => [...f, { kind: 'system', text: `STEWARD BLOCKED THE TURN: ${t.reason ?? 'unknown'}` }]);
      } else {
        if (t.mechanics) setFeed((f) => [...f, { kind: 'mechanics', m: t.mechanics }]);
        setFeed((f) => [...f, { kind: 'beats', beats: t.beats ?? [] }]);
        setOptions(t.suggested_actions ?? []);
        setCombatActive(!!t.combat_active);
        if (t.mechanics?.summary) addJournal('gm', t.mechanics.summary);
        if (t.mechanics?.dice?.length) {
          useGenesis.getState().addDiceRolls(
            t.mechanics.dice.map((d) => ({ roll_id: d.roll_id, formula: d.formula, individual_dice: d.dice, final_total: d.total, purpose: d.purpose, mode: 'normal', modifiers: 0 })),
            t.mechanics.classification,
          );
        }
        if (t.reaction_window) useGenesis.getState().setReactionWindow(t.reaction_window);
        if (t.audit?.violations?.length) console.warn('STEWARD AUDIT:', t.audit.violations);
        useGenesis.getState().refreshGmRuntime(); // anchor/actions track committed truth
        // MODE ROUTER: the controllers don't care which screen is visible —
        // the UI moves the player to the view that represents the mode.
        const g = useGenesis.getState();
        if (t.combat_active) {
          g.setUnresolvedAction({ view: 'diorama', label: 'A combat turn is unresolved on the Tactical View.' });
          setTimeout(() => useGenesis.getState().setEngagement('diorama'), 1600);
        } else if ((t.suggested_actions ?? []).length > 0) {
          g.setUnresolvedAction({ view: 'gm', label: 'You are in an unresolved conversation on the Living Table.' });
        } else {
          g.setUnresolvedAction(null);
        }
      }
    } catch (e) {
      setFeed((f) => [...f, { kind: 'system', text: `GM link lost: ${e.message}` }]);
    }
    setBusy(false);
  };

  if (online === false) {
    return <div style={{ padding: 30, color: 'var(--dim)', fontSize: 'var(--sys-font-size-meta)' }}>
      THE LIVING TABLE requires the API bridge + Ollama.<br />
      Start <code>api_bridge/server.py</code> and try again — the scripted Malice scene remains available under NARRATIVE.
    </div>;
  }
  if (online === 'unmounted') {
    return <div style={{ padding: 30, color: 'var(--dim)', fontSize: 'var(--sys-font-size-meta)', textAlign: 'center' }}>
      No campaign is mounted in the controller stack.<br /><br />
      <span className="holo-btn primary" style={{ fontSize: 'var(--sys-font-size-caption)', padding: '6px 14px' }}
        onClick={() => useGenesis.getState().setEngagement('select')}>▸ CAMPAIGN SELECT</span>
    </div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      {combatActive && <div className="wip-stripe" style={{ background: 'rgba(255,77,90,.15)', color: '#ff4d5a' }}>⚔ COMBAT ACTIVE — the Combat Master has the table</div>}
      <div ref={feedRef} style={{ flex: 1, overflowY: 'auto', padding: '12px 18px' }}>
        {feed.map((e, i) => {
          if (e.kind === 'system') return <div key={i} style={{ color: 'var(--dim)', fontSize: 'var(--sys-font-size-caption)', margin: '8px 0', letterSpacing: 1 }}>◈ {e.text}</div>;
          if (e.kind === 'player') return <div key={i} style={{ color: 'var(--gold)', fontSize: 'var(--sys-font-size-meta)', margin: '10px 0', textAlign: 'right' }}>YOU — {e.text}</div>;
          if (e.kind === 'mechanics') return (
            <div key={i} className="holo-panel" style={{ padding: '6px 10px', margin: '6px 0', borderColor: 'var(--amber)' }}>
              <div style={{ fontSize: 'var(--sys-font-size-micro)', color: 'var(--amber)', letterSpacing: 2 }}>COMBAT MASTER · {e.m.classification} · steward-verified</div>
              {(e.m.dice ?? []).map((d) => <DiceChip key={d.roll_id} d={d} />)}
              <div style={{ fontSize: 'var(--sys-font-size-caption)', color: '#cfe8f5' }}>{e.m.summary}</div>
            </div>
          );
          return <div key={i}>{(e.beats ?? []).map((b, j) => <Beat key={j} b={b} npcNames={npcNames} />)}</div>;
        })}
        {busy && <div style={{ color: 'var(--dim)', fontSize: 'var(--sys-font-size-note)' }}>the table considers…</div>}
      </div>

      {/* suggestions — chips, never rails */}
      {options.length > 0 && !busy && (
        <div style={{ padding: '4px 14px', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {options.map((o, i) => {
            const line = o.spoken_line || o.label || '';
            return <span key={i} className="holo-btn" style={{ fontSize: 'var(--sys-font-size-caption)', padding: '5px 12px' }} title={o.visible_basis}
              onClick={() => declare(line)}>{line}</span>;
          })}
        </div>
      )}

      {/* the free-action line — ALWAYS live (custom_action_allowed) */}
      <div style={{ display: 'flex', gap: 8, padding: '8px 14px 12px' }}>
        <input
          value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && declare(input)}
          placeholder="attempt anything plausible…"
          style={{ flex: 1, background: 'rgba(10,20,31,.8)', border: '1px solid var(--line)', color: '#cfe8f5', padding: '8px 12px', fontSize: 'var(--sys-font-size-meta)', fontFamily: 'inherit' }}
        />
        <span className="holo-btn primary" style={{ fontSize: 'var(--sys-font-size-caption)', padding: '8px 16px' }} onClick={() => declare(input)}>DECLARE ▸</span>
      </div>
    </div>
  );
}
