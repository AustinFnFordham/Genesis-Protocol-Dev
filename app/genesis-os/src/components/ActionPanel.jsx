/* OPERATIVE CONTAINER — contextual actions + tabbed equipment/powers body.
 * Fixed: Available Actions. Tab bar: Weapons | Gear | Powers | Conditions.
 * Only the active tab body scrolls (bounded height — long lists never grow the
 * page). Character-scoped: the selected tab resets when the mounted character
 * changes. Reads the mounted runtime; handles migrated item_stacks/instances. */
import React, { useEffect, useState } from 'react';
import { useGenesis } from '../state/store.js';
import { submitIntent } from '../state/intents.js';

const SHIP_RE = /\b(yt-?\d{3,4}|freighter|shuttle|starfighter|x-?wing|fighter|cruiser|corvette|frigate|transport|speeder|swoop|walker)\b/i;
const WEAPON_RE = /\b(blaster|rifle|pistol|saber|lightsaber|vibro|carbine|cannon|bowcaster|disruptor|sword|blade|dagger|staff|whip|grenade|detonator)\b/i;
const ARMOR_RE = /\b(armor|armour|plate|vest|helmet|greaves|gauntlet|beskar)\b/i;
const APPAREL_RE = /\b(jacket|coat|cloak|robe|tunic|boots|gloves|hat|clothes|clothing|garb|outfit)\b/i;
const ITEM_TYPES = ['Weapon', 'Armor', 'Gear', 'Consumable', 'Artifact', 'Droid_Part', 'Starship', 'Starship_Component', 'Trade_Good', 'Other'];
function asArray(v) { return v == null ? [] : Array.isArray(v) ? v : [v]; }
function itemType(it) {
  if (it && typeof it === 'object' && ITEM_TYPES.includes(it.item_type)) return it.item_type;
  const name = String(it?.name ?? it ?? '');
  if (SHIP_RE.test(name)) return 'Starship';
  if (it?.damage || WEAPON_RE.test(name)) return 'Weapon';
  if (it?.armor_class || (ARMOR_RE.test(name) && !APPAREL_RE.test(name))) return 'Armor';
  return 'Gear';
}
const META = { fontSize: 'var(--sys-font-size-meta)', letterSpacing: 1.5, color: 'var(--sem-text-secondary)' };
const ROW = { fontSize: 'var(--sys-font-size-control)', padding: '4px 8px', marginBottom: 3, display: 'block' };
const TABS = [['weapons', 'Weapons'], ['gear', 'Gear'], ['powers', 'Powers'], ['conditions', 'Conditions']];

export default function ActionPanel() {
  const { engagement, gmRuntime, setActionPrefill, setEngagement } = useGenesis();
  const activeId = gmRuntime?.metadata?.active_player;
  const sheet = gmRuntime?.player_characters?.[activeId] ?? null;
  const [tab, setTab] = useState('weapons');
  // character-scoped: reset the selected tab when the mounted character changes
  useEffect(() => { setTab('weapons'); }, [activeId]);

  const declareVia = (t) => { setActionPrefill(t); if (engagement !== 'dialogue') setEngagement('dialogue'); };
  const mode = engagement === 'diorama' ? 'combat' : (engagement === 'ship' ? 'ship' : 'scene');

  const eq = sheet?.equipment ?? {};
  const allItems = [...asArray(eq.weapons), ...asArray(eq.item_stacks), ...asArray(eq.item_instances),
    ...asArray(eq.gear), ...asArray(eq.trinkets), ...asArray(eq.inventory), ...asArray(eq.armor)];
  const weapons = allItems.filter((w) => itemType(w) === 'Weapon');
  const gear = allItems.filter((w) => !['Weapon', 'Starship', 'Starship_Component'].includes(itemType(w)));
  const powers = asArray(sheet?.powers);
  const conditions = asArray(sheet?.defenses?.conditions ?? sheet?.conditions);

  const base = mode === 'combat'
    ? [['Attack', 'I attack '], ['Move', 'I move to '], ['Guard', 'I take a defensive stance and guard '], ['Use Item', 'I use my '], ['End Turn', null]]
    : [['Speak', 'I say: "'], ['Interrupt', 'Before they finish, I '], ['Inspect', 'I inspect '], ['Move', 'I move to '], ['Use Item', 'I use my ']];

  const Empty = ({ children }) => <div style={{ fontSize: 'var(--sys-font-size-control)', color: 'var(--sem-text-secondary)', padding: '6px 2px' }}>{children}</div>;

  return (
    <div className="operative-panel" data-region="operative-actions" style={{ borderTop: '1px solid var(--sys-color-line)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      {/* FIXED: Available Actions */}
      <div className="panel-fixed" style={{ padding: '8px 10px 4px' }}>
        <div style={{ ...META, marginBottom: 6 }}>AVAILABLE ACTIONS — {mode.toUpperCase()}</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {base.map(([label, tpl]) => (
            <span key={label} className="holo-btn ghost" style={{ fontSize: 'var(--sys-font-size-control)', padding: '3px 8px' }}
              onClick={() => tpl == null ? submitIntent('end_turn') : declareVia(tpl)}>{label}</span>
          ))}
        </div>
      </div>
      {/* FIXED: tab bar */}
      <div className="panel-fixed" style={{ display: 'flex', gap: 2, padding: '6px 8px 4px', borderBottom: '1px solid var(--sys-color-line)' }}>
        {TABS.map(([k, label]) => (
          <span key={k} className={`holo-btn ${tab === k ? 'primary' : 'ghost'}`} style={{ fontSize: 'var(--sys-font-size-control)', padding: '3px 8px' }}
            onClick={() => setTab(k)}>{label}</span>
        ))}
      </div>
      {/* SCROLLABLE: only the active tab body (bounded so long lists never grow the page) */}
      <div className="panel-scroll-body" style={{ padding: '6px 10px', maxHeight: '38vh' }}>
        {tab === 'weapons' && (weapons.length ? weapons.map((w, i) => (
          <div key={i} className="holo-btn ghost" style={ROW}
            onClick={() => declareVia(`I ${mode === 'combat' ? 'attack with' : 'draw'} my ${w.name} `)}
            title={w.exact_effect ?? ''}>▸ {w.name} {w.attack_bonus != null && <span style={{ color: 'var(--sys-color-gold)' }}>+{w.attack_bonus}</span>}
            {w.quantity > 1 && <span style={{ color: 'var(--sem-text-secondary)' }}> ×{w.quantity}</span>}</div>
        )) : <Empty>No weapons equipped.</Empty>)}

        {tab === 'gear' && (gear.length ? gear.map((g, i) => (
          <div key={i} className="holo-btn ghost" style={ROW} onClick={() => declareVia(`I use my ${g.name} `)} title={g.exact_effect ?? ''}>
            ◇ {g.name} {g.quantity > 1 && <span style={{ color: 'var(--sem-text-secondary)' }}>×{g.quantity}</span>}</div>
        )) : <Empty>No gear carried.</Empty>)}

        {tab === 'powers' && (powers.length ? powers.map((p, i) => (
          <div key={i} className="holo-btn ghost" style={ROW} onClick={() => declareVia(`I use ${p.name} on `)} title={p.exact_effect ?? ''}>
            ◈ {p.name} <span style={{ color: 'var(--sys-color-gold)' }}>{p.cost === 0 ? 'free' : p.cost ?? ''}</span></div>
        )) : <Empty>No powers available.</Empty>)}

        {tab === 'conditions' && (conditions.length ? conditions.map((c, i) => (
          <div key={i} style={{ fontSize: 'var(--sys-font-size-control)', color: 'var(--sys-color-warning)', marginBottom: 3 }}>⚠ {c.name ?? String(c)}</div>
        )) : <Empty>No active conditions or effects.</Empty>)}
      </div>
    </div>
  );
}
