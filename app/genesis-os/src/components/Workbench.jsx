/* THE HOLOGRAPHIC WORKBENCH — drag-and-drop modding overlay.
 * Left: the cargo pool (Item + Modification gold entities from the registry).
 * Right: the operative's active loadout with hardpoint sockets.
 * Dragging a modification chip onto a socket dispatches an RFC6902 patch to
 * the character's equipment — encumbrance in the Anchor reacts instantly. */
import React, { useMemo, useState } from 'react';
import { useGenesis, getName, getId } from '../state/store.js';
import { submitIntent } from '../state/intents.js';

export default function Workbench() {
  const { registry, manifest, campaign, setOverlay, addJournal } = useGenesis();
  const charUrid = campaign?.party?.[0];
  const c = registry.get(charUrid);
  const [dragging, setDragging] = useState(null);
  const [hoverSocket, setHoverSocket] = useState(null);

  const pool = useMemo(() => {
    const items = manifest.filter((m) => m.schema === 'Item').map((m) => registry.get(m.urid));
    const mods = manifest.filter((m) => m.schema === 'Modification').map((m) => registry.get(m.urid));
    return { items: items.filter(Boolean), mods: mods.filter(Boolean) };
  }, [manifest, registry]);

  if (!c) return null;
  const gear = c.equipment ?? [];
  const SOCKETS = ['primary weapon', 'armor', 'utility 1', 'utility 2', 'mod slot'];

  const equip = (label, socket) => {
    const entry = socket === 'mod slot' ? `[MOD] ${label}` : `${label} (${socket})`;
    if (gear.some((g) => String(g).includes(label))) {
      addJournal('system', `${label} is already fitted.`);
      return;
    }
    const outcome = submitIntent('equip_item', { character: charUrid, entry });
    if (outcome.accepted) addJournal('system', `Workbench: fitted ${label} → ${socket}. Encumbrance recalculated.`);
  };

  const unequip = (idx) => {
    const label = gear[idx];
    const outcome = submitIntent('unequip_item', { character: charUrid, index: idx });
    if (outcome.accepted) addJournal('system', `Workbench: removed ${label}. Weight off your shoulders.`);
  };

  const Chip = ({ e, kind }) => (
    <div
      draggable
      onDragStart={() => setDragging({ label: getName(e), kind })}
      onDragEnd={() => setDragging(null)}
      className="holo-card"
      style={{ cursor: 'grab', maxWidth: 320, borderLeftColor: kind === 'mod' ? 'var(--amber)' : undefined }}
    >
      <div className="n" style={{ fontSize: 'var(--sys-font-size-meta)' }}>
        {kind === 'mod' ? '⬡ ' : '▣ '}{getName(e)}
      </div>
      <div className="t" style={{ letterSpacing: 0 }}>{(e.description ?? '').slice(0, 80)}</div>
    </div>
  );

  return (
    <div style={{
      position: 'absolute', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(4,7,13,0.72)', backdropFilter: 'blur(7px)',
    }}>
      <div className="holo-panel boot-in" style={{ width: 'min(96%, 900px)', maxHeight: '90%', display: 'flex', flexDirection: 'column' }}>
        <div className="holo-title">Holographic Workbench — {getName(c)}
          <span style={{ flex: 1 }} />
          <span style={{ cursor: 'pointer', color: 'var(--dim)' }} onClick={() => setOverlay(null)}>✕ CLOSE</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0, minHeight: 0, overflow: 'hidden' }}>
          {/* cargo pool */}
          <div style={{ padding: 12, overflowY: 'auto', maxHeight: 460, borderRight: '1px solid var(--line)' }}>
            <div className="sec-h">Cargo Pool — drag to a socket</div>
            {pool.items.map((e) => <Chip key={getId(e)} e={e} kind="item" />)}
            <div className="sec-h">Modification Chips</div>
            {pool.mods.map((e) => <Chip key={getId(e)} e={e} kind="mod" />)}
            {pool.items.length + pool.mods.length === 0 && <div style={{ color: 'var(--dim)', fontSize: 'var(--sys-font-size-note)' }}>cargo hold empty — the forge will provide</div>}
          </div>
          {/* loadout + sockets */}
          <div style={{ padding: 12, overflowY: 'auto', maxHeight: 460 }}>
            <div className="sec-h">Hardpoint Sockets</div>
            {SOCKETS.map((s) => (
              <div key={s}
                onDragOver={(ev) => { ev.preventDefault(); setHoverSocket(s); }}
                onDragLeave={() => setHoverSocket(null)}
                onDrop={() => { if (dragging) equip(dragging.label, s); setHoverSocket(null); setDragging(null); }}
                style={{
                  border: `1px dashed ${hoverSocket === s ? 'var(--amber)' : 'var(--line)'}`,
                  background: hoverSocket === s ? 'rgba(255,179,0,0.08)' : 'rgba(10,20,32,0.5)',
                  padding: '10px 12px', margin: '6px 0', fontSize: 'var(--sys-font-size-note)', letterSpacing: 2,
                  color: hoverSocket === s ? 'var(--amber)' : 'var(--dim)', textTransform: 'uppercase',
                  transition: 'all .12s',
                }}>
                ⬢ {s} {hoverSocket === s && dragging ? `— fit ${dragging.label}?` : ''}
              </div>
            ))}
            <div className="sec-h">Current Loadout — click to strip</div>
            {gear.map((g, i) => (
              <div key={i} className="holo-card" style={{ cursor: 'pointer' }} onClick={() => unequip(i)}
                title="click to remove">
                <div className="n" style={{ fontSize: 'var(--sys-font-size-meta)' }}>{String(g)} <span style={{ color: 'var(--red)', fontSize: 'var(--sys-font-size-micro)' }}>✕</span></div>
              </div>
            ))}
            <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--dim)', marginTop: 8 }}>
              every fit/strip is an RFC6902 patch on /equipment — the Anchor's encumbrance tracker reacts live
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
