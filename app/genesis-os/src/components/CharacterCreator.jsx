/* THE CHARACTER CREATOR — holo-themed, first playable module.
 * Lineage: KOTOR (identity + light/dark start), Mass Effect (background beat),
 * BG3 (27-point buy, live modifiers). Options are DATA from the Gold registry.
 * Commit: assemble -> Ajv guardrail (same law as the forge) -> registry -> Forge.
 * Schema-exact per Character.schema.json: rarity enum, mode_balanced,
 * moral_compass integer (-100..100), image_generation.contextual_modifiers,
 * ui.image/icon required. */
import React, { useState } from 'react';
import { useGenesis, getName, getId } from '../state/store.js';
import { getCharacterValidator } from '../state/validation.js';

const ABILITIES = ['str', 'dex', 'con', 'int', 'wis', 'cha'];
const LONG = { str: 'strength', dex: 'dexterity', con: 'constitution', int: 'intelligence', wis: 'wisdom', cha: 'charisma' };
const POINT_COST = { 8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9 };
const BUDGET = 27;
const STEPS = ['SPECIES', 'CLASS', 'ABILITIES', 'BACKGROUND', 'MORALITY', 'IDENTITY', 'REVIEW'];

export default function CharacterCreator({ onCommitted }) {
  const { registry, manifest } = useGenesis();
  const [step, setStep] = useState(0);
  const [sel, setSel] = useState({ species: null, klass: null, subclass: null, background: null });
  const [scores, setScores] = useState({ str: 10, dex: 10, con: 10, int: 10, wis: 10, cha: 10 });
  const [morality, setMorality] = useState(0); // schema scale: -100 dark .. +100 light
  const [name, setName] = useState('');
  const [identity, setIdentity] = useState('');
  const [gear, setGear] = useState('worn traveler jacket, holstered blaster');
  const [result, setResult] = useState(null);

  const bySchema = (s) => manifest.filter((m) => m.schema === s).map((m) => registry.get(m.urid));
  const species = bySchema('Species');
  const classes = bySchema('Class');
  const subclasses = bySchema('Subclass');
  const backgrounds = bySchema('Background');

  const spent = ABILITIES.reduce((t, a) => t + (POINT_COST[scores[a]] ?? 99), 0);
  const mod = (v) => { const m = Math.floor((v - 10) / 2); return (m >= 0 ? '+' : '') + m; };
  const bump = (a, d) => {
    const nv = scores[a] + d;
    if (nv < 8 || nv > 15) return;
    if (spent - POINT_COST[scores[a]] + POINT_COST[nv] > BUDGET) return;
    setScores({ ...scores, [a]: nv });
  };

  const quickFill = () => {
    setSel({ species: species[0] ?? null, klass: classes[0] ?? null, subclass: subclasses[0] ?? null, background: backgrounds[0] ?? null });
    setScores({ str: 14, dex: 10, con: 12, int: 10, wis: 12, cha: 10 });
    setMorality(10);
    setName('Rrawrkhal');
    setIdentity('russet fur with silver streaks, scar across left brow, amber eyes');
    setStep(6);
  };

  const assemble = () => {
    const slug = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'unnamed';
    const align = morality >= 33 ? 'light' : morality <= -33 ? 'dark' : 'balanced';
    const gearArr = gear.split(',').map((s) => s.trim()).filter(Boolean);
    const identArr = identity ? identity.split(',').map((s) => s.trim()).filter(Boolean) : [`${getName(sel.species)} of striking bearing`];
    return {
      id: `character_${slug}`,
      name: name.trim() || 'Unnamed Operative',
      era: 'Galactic_Empire',
      rarity: 'legendary',
      narrative: `A ${getName(sel.species)} ${getName(sel.klass)} shaped by a ${getName(sel.background)} past, walking the ${align} path.`,
      description: identity || `A ${getName(sel.species)} ${getName(sel.klass)}.`,
      species_id: getId(sel.species),
      background_id: getId(sel.background),
      game_mode: { mode_id: 'mode_balanced', xp_multiplier: 1, out_of_class_xp_penalty: 1 },
      level: 1,
      xp: 0,
      ability_scores: Object.fromEntries(ABILITIES.map((a) => [LONG[a], scores[a]])),
      moral_compass: morality,
      tags: ['tag_player_character', `tag_species_${String(getId(sel.species)).replace(/^species_/, '')}`],
      features: sel.subclass ? [getId(sel.subclass)] : [],
      equipment: gearArr,
      visual_dna: {
        identity_constants: identArr,
        gear_variables: gearArr,
        environment_context: ['character creation chamber, blue holo-light'],
      },
      llm_guidance: { roleplay_guidance: `Moral compass ${morality} (${align}). Honor the ${getName(sel.background)} background in social scenes.` },
      image_generation: {
        base_prompt: `cinematic portrait of a ${getName(sel.species)} ${getName(sel.klass)}, ${identArr.join(', ')}, ${gearArr.join(', ')}, Star Wars concept art`,
        contextual_modifiers: [
          { target_type: 'Portrait', modifier_text: 'blue holo-light rim lighting, diegetic datapad UI glow' },
          { target_type: 'Action_Shot', modifier_text: 'dynamic pose, motion blur on background, sparks' },
        ],
      },
      ui: {
        image: `/portraits/character_${slug}.png`,
        icon: `/icons/character_${slug}.svg`,
        color: morality <= -33 ? '#8b0000' : '#33E1FF',
      },
    };
  };

  const commit = async () => {
    const doc = assemble();
    let validate;
    try {
      validate = await getCharacterValidator();
    } catch (err) {
      setResult({ pass: false, errors: [`guardrail unavailable: ${err.message} — refusing to commit unvalidated data`] });
      return;
    }
    const pass = validate(doc);
    if (!pass) {
      setResult({ pass: false, errors: (validate.errors || []).map((e2) => `${e2.instancePath || '/'} ${e2.message}`).slice(0, 8) });
      return;
    }
    // CAMPAIGN INITIALIZATION LOOP: register the character, then instantiate
    // a fresh CampaignState with the character injected into /party and the
    // starting node set. The shell flips into game mode automatically.
    useGenesis.getState().registerEntity(doc.id, doc, 'Character', 'wip');
    setResult({ pass: true, id: doc.id });
    setTimeout(() => {
      useGenesis.getState().startCampaign(doc.id);
      onCommitted?.(doc.id);
    }, 900);
  };

  const Card = ({ e, k }) => (
    <div className={`holo-card ${sel[k] === e ? 'sel' : ''}`} style={{ maxWidth: 860 }} onClick={() => setSel({ ...sel, [k]: e })}>
      <div className="n">{getName(e)}</div>
      <div className="t" style={{ fontSize: 'var(--sys-font-size-note)', letterSpacing: 0 }}>{(e.description || e.narrative || '').slice(0, 150)}</div>
    </div>
  );

  const canNext = [!!sel.species, !!sel.klass, spent <= BUDGET, !!sel.background, true, name.trim().length > 0, false];

  return (
    <div style={{ overflowY: 'auto', padding: '16px 24px', flex: 1 }}>
      <div className="step-rail">
        {STEPS.map((s, i) => <span key={s} className={`step-pip ${i === step ? 'on' : i < step ? 'done' : ''}`}>{s}</span>)}
        <span style={{ flex: 1 }} />
        <span className="holo-btn ghost" style={{ fontSize: 'var(--sys-font-size-label)', padding: '4px 10px' }} onClick={quickFill}>⚡ QA quick-start</span>
        <span className="holo-btn ghost" style={{ fontSize: 'var(--sys-font-size-label)', padding: '4px 10px', borderColor: 'var(--amber)' }}
          onClick={() => useGenesis.getState().loadCampaignFromEntity()}>▶ LOAD TEST CAMPAIGN</span>
      </div>

      {step === 0 && (<>
        <div className="sec-h">Choose your species — {species.length} in the Gold registry</div>
        {species.map((e) => <Card key={getId(e)} e={e} k="species" />)}
        {species.length < 3 && <div style={{ color: 'var(--dim)', fontSize: 'var(--sys-font-size-note)', marginTop: 6 }}>more species arrive as the forge promotes them — this list is data, not code</div>}
      </>)}

      {step === 1 && (<>
        <div className="sec-h">Choose your class</div>
        {classes.map((e) => <Card key={getId(e)} e={e} k="klass" />)}
        <div className="sec-h">Subclass — optional</div>
        {subclasses.map((e) => <Card key={getId(e)} e={e} k="subclass" />)}
      </>)}

      {step === 2 && (<>
        <div className="sec-h">Point buy — {BUDGET - spent} points remaining (8–15, BG3 costs)</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 96px)', gap: 10 }}>
          {ABILITIES.map((a) => (
            <div key={a} className="stat-hex">
              <div className="k">{a.toUpperCase()}</div>
              <div className="v">
                <span style={{ cursor: 'pointer', color: 'var(--cyan)', padding: '0 7px' }} onClick={() => bump(a, -1)}>−</span>
                {scores[a]}
                <span style={{ cursor: 'pointer', color: 'var(--cyan)', padding: '0 7px' }} onClick={() => bump(a, +1)}>+</span>
              </div>
              <div className="m">{mod(scores[a])}</div>
            </div>
          ))}
        </div>
      </>)}

      {step === 3 && (<>
        <div className="sec-h">Background — who were you before the war?</div>
        {backgrounds.map((e) => <Card key={getId(e)} e={e} k="background" />)}
      </>)}

      {step === 4 && (<>
        <div className="sec-h">Starting moral compass — the needle moves with every choice</div>
        <input type="range" min="-100" max="100" value={morality} style={{ width: 340, accentColor: morality <= -33 ? '#ff4d5a' : '#33e1ff' }}
          onChange={(ev) => setMorality(+ev.target.value)} />
        <div style={{ color: morality <= -33 ? 'var(--red)' : morality >= 33 ? 'var(--green)' : 'var(--txt)', marginTop: 6 }}>
          {morality > 0 ? '+' : ''}{morality} — {morality >= 33 ? 'the light' : morality <= -33 ? 'the dark side hungers' : 'the grey between'}
        </div>
        <div style={{ fontSize: 'var(--sys-font-size-note)', color: 'var(--dim)', marginTop: 4 }}>below −33 the Forge hologram corrupts and the dataslate palette follows</div>
      </>)}

      {step === 5 && (<>
        <div className="sec-h">Name</div>
        <input className="holo-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Rrawrkhal" />
        <div className="sec-h">Identity constants — comma-separated; these LOCK, the face never drifts</div>
        <input className="holo-input wide" value={identity} onChange={(e) => setIdentity(e.target.value)}
          placeholder="e.g. russet fur with silver streaks, scar across left brow, amber eyes" />
        <div className="sec-h">Starting gear — the inpaint variables</div>
        <input className="holo-input wide" value={gear} onChange={(e) => setGear(e.target.value)} />
      </>)}

      {step === 6 && (<>
        <div className="sec-h">Review — the guardrail decides, not us</div>
        <pre className="holo-panel" style={{ fontSize: 'var(--sys-font-size-note)', color: 'var(--dim)', maxHeight: 250, overflowY: 'auto', padding: 12, margin: 0 }}>
          {JSON.stringify(assemble(), null, 1)}
        </pre>
        <div style={{ marginTop: 12 }}>
          <span className="holo-btn primary" onClick={commit}>Validate &amp; Commit to Registry</span>
        </div>
        {result && !result.pass && (
          <div style={{ color: 'var(--red)', fontSize: 'var(--sys-font-size-meta)', whiteSpace: 'pre-wrap', marginTop: 8 }}>
            SCHEMA REJECTED:{'\n'}{result.errors.join('\n')}
          </div>)}
        {result && result.pass && (
          <div style={{ color: 'var(--green)', fontSize: 'var(--sys-font-size-control)', marginTop: 8, textShadow: '0 0 8px rgba(89,255,163,.5)' }}>
            ✓ Character.schema PASS — {result.id} committed. Opening the Forge…
          </div>)}
      </>)}

      <div style={{ marginTop: 14 }}>
        {step > 0 && <span className="holo-btn ghost" onClick={() => setStep(step - 1)}>◂ Back</span>}
        {step < 6 && <span className={`holo-btn primary ${canNext[step] ? '' : 'disabled'}`} onClick={() => canNext[step] && setStep(step + 1)}>Next ▸</span>}
      </div>
    </div>
  );
}
