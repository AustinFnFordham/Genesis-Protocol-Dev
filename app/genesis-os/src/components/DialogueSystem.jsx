/* NARRATIVE DIALOGUE INTERFACE v1.0 — BioWare wheel + Slicer Override.
 * Left: cinematic feed. Right: alpha-masked avatar (ComfyUI slot) with mood
 * states driving rim-light. Bottom: structured, mechanically weighted choices
 * + the free-text LLM override line.
 * Every consequence is an RFC6902 batch on real registry entities:
 * Malice's trust_meter, item damage tags, mood state. The local adjudicator
 * below is the deterministic stand-in for the qwen rules engine — same
 * output contract (patch batches + narration), swappable via Tauri command. */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useGenesis, getName, getId } from '../state/store.js';
import { portraitUrl } from '../state/registry.js';
import { submitIntent } from '../state/intents.js';

function AvatarImage({ urid, aura }) {
  const [ok, setOk] = useState(true);
  if (!ok || !urid) return null; // placeholder silhouette shows through
  return (
    <img src={portraitUrl(urid)} alt="" onError={() => setOk(false)}
      style={{
        position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', zIndex: 2,
        filter: `drop-shadow(0 0 24px ${aura}88)`,
        maskImage: 'linear-gradient(180deg, black 82%, transparent 100%)',
      }} />
  );
}

const MOODS = {
  intense_satisfaction: { aura: '#8b1a2a', label: 'INTENSE SATISFACTION' },
  dark_anger: { aura: '#ff2222', label: 'FLASH OF DARK ANGER' },
  seductive_amusement: { aura: '#c22a6e', label: 'TERRIFYING AMUSEMENT' },
  guarded: { aura: '#4a2a6b', label: 'GUARDED' },
  // live AI GM moods (per-beat, from the Game Master controller)
  calm: { aura: '#2a6b8a', label: 'CALM' },
  amused: { aura: '#c22a6e', label: 'AMUSED' },
  warm: { aura: '#c2802a', label: 'WARM' },
  angry: { aura: '#ff2222', label: 'ANGRY' },
  tense: { aura: '#8a2a6b', label: 'TENSE' },
};

const GM_API = 'http://localhost:8788/api/v1/gm';

export default function DialogueSystem() {
  const { registry, manifest, gmCampaign, gmRuntime, actionPrefill } = useGenesis();
  // LIVE MODE: when a campaign is mounted, the AI GM drives this view.
  // The visual identity — portraits, mood, cinematic feed, structured
  // choices, Slicer Override — is preserved exactly; only the brain changes.
  const live = !!gmCampaign;
  // H: the scripted Malice demo is DEV-ONLY and opt-in. It can NEVER render in a
  // production build, while a campaign is mounted (live), or during loading/API
  // failure (which present as !live) — those show an honest empty state instead.
  const SCRIPTED_DEMO = import.meta.env.DEV && false;
  // CHECKPOINT ONE: in live mode this component OWNS NOTHING. The transcript,
  // options, focus NPC, and draft all live in the shared session store —
  // server-owned truth, projected here. Tab switches change nothing.
  const gmFeed = useGenesis((s) => s.gmFeed);
  const gmOptions = useGenesis((s) => s.gmOptions);
  const gmBusy = useGenesis((s) => s.gmBusy);
  const focusNpc = useGenesis((s) => s.gmFocusNpc);
  const narrativeDraft = useGenesis((s) => s.narrativeDraft);
  // The Malice companion's gold id is companion_sith_assassin (darth_malice source).
  const maliceUrid = useMemo(() => {
    const byName = manifest.find((m) => (m.name || '').toLowerCase().includes('malice'));
    if (byName) return byName.urid;
    const companions = manifest.filter((m) => m.schema === 'Companion' && !m.urid.includes('nexu'));
    return companions[0]?.urid;
  }, [manifest]);
  const malice = registry.get(maliceUrid);
  const trust = malice?.trust_meter ?? malice?.relationship?.trust ?? 25;

  // Seed a trust_meter on the entity so the gauge is a live, patchable value.
  // (delta 0 through the relationship engine adds the baseline 25 if absent.)
  useEffect(() => {
    if (maliceUrid && malice && malice.trust_meter === undefined) {
      submitIntent('scene_action', { target: maliceUrid, delta: 0 });
    }
  }, [maliceUrid]); // eslint-disable-line

  const [log, setLog] = useState([
    { who: 'SYSTEM', text: 'Coruscant Level 1313 — the cache is open. The holocron hums in your hands.' },
    { who: 'Darth Malice', mood: 'intense_satisfaction', text: '“The text was accurate. The relic is real… and the power radiating from it belongs to the strong. Hand it to me, apprentice. Let us see if your spirit can endure the truths it holds.”' },
  ]);
  const [mood, setMood] = useState('intense_satisfaction');
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const feedRef = useRef();
  const [unread, setUnread] = useState(false);
  const nearBottom = () => { const el = feedRef.current; return !el || (el.scrollHeight - el.scrollTop - el.clientHeight) < 90; };
  // J: auto-follow ONLY when near the bottom; otherwise preserve scroll + flag unread.
  useEffect(() => {
    if (nearBottom()) { feedRef.current?.scrollTo(0, 99999); setUnread(false); }
    else setUnread(true);
  }, [gmFeed, log]);
  // campaign switch resets transcript view to bottom of the mounted campaign
  useEffect(() => { setUnread(false); requestAnimationFrame(() => feedRef.current?.scrollTo(0, 99999)); }, [gmCampaign]);

  const player = useMemo(() => {
    const m = manifest.find((x) => x.schema === 'Character' && x.urid !== 'character_shadowstalker_nexu_alpha');
    return registry.get(m?.urid) ?? registry.get('character_shadowstalker_nexu_alpha');
  }, [registry, manifest]);
  const playerStr = player?.ability_scores?.strength ?? 10;

  const say = (who, text, moodKey) => setLog((l) => [...l, { who, text, mood: moodKey }]);
  // GEN-REL-001: a scene action can carry a moral ripple (influence) and a
  // romance beat — the engines decide who is moved; the UI only proposes.
  const patchTrust = (delta, influence = null, romance = null) => {
    if (!maliceUrid) return;
    submitIntent('scene_action', { target: maliceUrid, delta, influence, romance });
  };

  /* ---------- THE OPENING CRAWL — a PERSISTED, per-campaign projection.
   * store.opening is loaded on mount/switch (server opening contract: authored
   * or persisted, generated once). It belongs to gmCampaign, never changes
   * across ordinary mounts, and replays on restart. Rendered as a distinct
   * crawl above the cinematic feed — NOT injected into the transcript. ---------- */
  const opening = useGenesis((s) => s.opening);
  const [crawlOpen, setCrawlOpen] = useState(true);
  useEffect(() => { setCrawlOpen(true); }, [gmCampaign]); // re-show on campaign switch/restart
  useEffect(() => { if (live && !opening) useGenesis.getState().loadOpening(); }, [live, gmCampaign]); // eslint-disable-line
  const crawlText = opening?.cinematic_exposition;
  const showCrawl = live && crawlOpen && !!crawlText;

  useEffect(() => {
    if (live && actionPrefill) { useGenesis.getState().setNarrativeDraft(actionPrefill); useGenesis.getState().setActionPrefill(''); }
  }, [live, actionPrefill]);

  // THE SINGLE PIPELINE: every view declares through the store; none owns it.
  const declareLive = (text) => useGenesis.getState().declareToGm(text);

  // SPOKEN-LINE CONTRACT projection: shared-store suggestions → choice cards.
  const liveChoices = gmOptions.slice(0, 4).map((o, i) => {
    const line = o.spoken_line || o.label || '';
    const it = typeof o.intent === 'object' ? o.intent : { topic: o.intent };
    return {
      key: `live_${i}`, label: line, tag: (it?.tone ?? o.category ?? 'SAY').toUpperCase(),
      weight: [it?.topic, it?.goal].filter(Boolean).join(' · ') || (o.visible_basis ?? ''),
      // J: clicking a suggestion POPULATES the composer for review — it does NOT submit.
      run: () => useGenesis.getState().setNarrativeDraft(line),
    };
  });

  /* -------- structured, mechanically weighted choices -------- */
  const choices = [
    {
      key: 'loyal', label: '“It is yours, Master. Instruct me.”', tag: 'LOYAL', weight: 'Trust +5 · Sith training sub-routine',
      run: () => {
        patchTrust(+5, { alignment: 'dark', magnitude: 3 }); setMood('seductive_amusement');
        say('YOU', '“It is yours, Master. Instruct me.”');
        say('Darth Malice', '“Good. Obedience before power — power before mercy. Your first lesson begins at the next system.” (trust rises)', 'seductive_amusement');
      },
    },
    {
      key: 'defiant', label: '“I bled for this holocron. We study it together, or no one does.”', tag: `DEFIANT · STR ${playerStr >= 16 ? '✓' : '✗ req 16'}`, weight: 'Intimidation check vs her pride',
      disabled: playerStr < 16,
      run: () => {
        patchTrust(+3, { alignment: 'neutral', magnitude: 3 }, { delta: +5, event: 'Bared teeth at a Sith' }); setMood('seductive_amusement');
        say('YOU', '“I bled for this holocron. We study it together, or no one does.”');
        say('Darth Malice', '“…You bare your teeth at a Sith. Either magnificent or suicidal.” She laughs — low, dangerous. “Together, then. For now.” (grudging respect: trust +3)', 'seductive_amusement');
      },
    },
    {
      key: 'protective', label: '“This power will shatter the crew’s minds. Keep it away from them.”', tag: 'PROTECTIVE', weight: 'Guardian narrative flag',
      run: () => {
        patchTrust(-2, { alignment: 'light', magnitude: 4 }); setMood('guarded');
        say('YOU', '“This power will shatter the crew’s minds. Keep it away from them.”');
        say('Darth Malice', '“Sentiment. It will get them killed faster than any holocron.” Her eyes narrow — she files your weakness away. (trust −2, protective flag logged)', 'guarded');
      },
    },
  ];

  /* -------- Slicer Override: deterministic local adjudicator --------
   * Contract identical to the qwen rules engine: input = free text +
   * scene state; output = { patches[], narration, mood }.        */
  const adjudicate = (text) => {
    const t = text.toLowerCase();
    const itemPatches = [];
    let narration, moodKey = 'guarded', trustDelta = 0, escalate = false, influence = null, romance = null;
    if (/(smash|crack|break|shatter|destroy).*(holocron|relic|it)/.test(t) || /holocron.*(smash|crack|break)/.test(t)) {
      itemPatches.push({ target: maliceUrid, flags: { holocron_state: 'itm_sith_holocron_cracked', last_override: text.slice(0, 120) } });
      trustDelta = +4; moodKey = 'dark_anger';
      influence = { alignment: 'neutral', magnitude: 3 }; romance = { delta: +4, event: 'Cracked an ancient holocron to prove a point' };
      narration = ['“Madness! You dare damage an artifact of the ancients just to prove a point?!”',
        'She steps forward, hand hovering at her lightsaber — then a terrifying, seductive grin breaks through the anger.',
        '“Bold… reckless… and completely unfiltered. You have fire in you, Guardian. Most would have knelt. Let us see if that blade can back up your petulance.” (item cracked · trust +4 · she will remember this)'].join('\n');
    } else if (/(kneel|bow|kneel before|submit)/.test(t)) {
      trustDelta = +2; moodKey = 'seductive_amusement'; influence = { alignment: 'dark', magnitude: 2 };
      narration = '“Kneeling suits you less than defiance. But it will do.” (trust +2)';
    } else if (/(attack|ignite my (saber|blade|lightsaber)|strike her|draw.*blaster|shoot her|open fire)/.test(t) && !/holocron/.test(t)) {
      trustDelta = -10; moodKey = 'dark_anger'; escalate = true; influence = { alignment: 'dark', magnitude: 6 };
      narration = '“So THAT is your answer.” Crimson light floods the chamber as her blade snaps alive. INITIATIVE — the scene escalates to the holotable. (trust −10 · combat initiated)';
    } else if (/(thermal detonator|detonator)/.test(t)) {
      trustDelta = +6; moodKey = 'seductive_amusement'; influence = { alignment: 'dark', magnitude: 4 }; romance = { delta: +6, event: 'Negotiated with a live thermal detonator' };
      narration = 'A slow, delighted smile. “A negotiator after my own heart. Put the toy away — you have made your point.” (trust +6 · her respect for audacity is noted)';
    } else {
      trustDelta = 0; moodKey = 'guarded';
      narration = 'She watches you, unreadable, cataloguing every twitch. “Interesting choice of words, Guardian. Go on.” (the GM engine logs your action for the scene state)';
    }
    return { itemPatches, trustDelta, moodKey, narration, escalate, influence, romance };
  };

  const submitOverride = () => {
    if (live) { declareLive(narrativeDraft); return; }
    const text = input.trim();
    if (!text || busy) return;
    setBusy(true); setInput('');
    say('YOU (override)', `“${text}”`);
    setTimeout(() => {
      const r = adjudicate(text);
      r.itemPatches.forEach((p) => submitIntent('scene_flag', { target: p.target, flags: p.flags }));
      if (r.trustDelta) patchTrust(r.trustDelta, r.influence, r.romance);
      setMood(r.moodKey);
      say('Darth Malice', r.narration, r.moodKey);
      setBusy(false);
      if (r.escalate) {
        // SEAMLESS SWAP: narrative dissolves into the tactical holotable.
        const g = useGenesis.getState();
        g.addJournal('combat', 'Negotiations have ended. Initiative rolls — the holotable takes over.');
        setTimeout(() => g.setEngagement('diorama'), 1400);
      }
    }, 650);
  };

  const aura = MOODS[mood]?.aura ?? '#8b1a2a';

  // H: no live campaign + not the dev demo -> honest empty state (never Malice)
  if (!live && !SCRIPTED_DEMO) {
    return (
      <div data-region="active-engagement" data-campaign-id="" style={{ padding: 24, color: 'var(--sem-text-secondary)', fontSize: 'var(--sys-font-size-body)' }}>
        No campaign mounted — select a campaign to begin.
      </div>
    );
  }

  return (
    <div data-region="active-engagement" data-campaign-id={gmCampaign ?? ''} style={{ position: 'relative', flex: 1, minHeight: 0, display: 'grid', gridTemplateColumns: '1fr 400px', overflow: 'hidden' }}>
      {/* blurred holotable backdrop suggestion */}
      <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(900px 500px at 70% 40%, rgba(139,26,42,.12), transparent 60%)', pointerEvents: 'none' }} />

      {/* left: cinematic feed + input terminal */}
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, padding: '14px 18px' }}>
        {showCrawl && (
          <div className="holo-panel" style={{ marginBottom: 10, padding: '14px 18px', maxHeight: '46%', overflowY: 'auto', borderColor: 'var(--gold)' }}>
            <div style={{ fontSize: 'var(--sys-font-size-micro)', letterSpacing: 3, color: 'var(--gold)' }}>
              OPENING CRAWL · {opening?.campaign_id ?? gmCampaign} · {opening?.source ?? 'persisted'}
            </div>
            <div style={{ fontSize: 'var(--sys-font-size-body)', lineHeight: 1.7, whiteSpace: 'pre-wrap', color: 'var(--txt)', marginTop: 8, textAlign: 'justify' }}>
              {crawlText}
            </div>
            {opening?.scene_transition && <div style={{ fontSize: 'var(--sys-font-size-control)', color: 'var(--cyan)', marginTop: 8, fontStyle: 'italic' }}>{opening.scene_transition}</div>}
            {opening?.mission_summary && <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--dim)', marginTop: 8 }}>MISSION: {opening.mission_summary}</div>}
            {opening?.active_cast?.length > 0 && <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--dim)', marginTop: 2 }}>PRESENT: {opening.active_cast.join(' · ')}</div>}
            <div style={{ marginTop: 10, textAlign: 'right' }}>
              <span className="holo-btn primary" style={{ fontSize: 'var(--sys-font-size-caption)', padding: '5px 14px' }} onClick={() => setCrawlOpen(false)}>
                {opening?.action_window ?? 'Begin ▾'}
              </span>
            </div>
          </div>
        )}
        <div className="sec-h">
          {live
            ? `Cinematic Feed — ${gmRuntime?.metadata?.scene_id ?? 'scene'} · four-controller GM live`
            : `Cinematic Feed — Level 1313 · trust ${trust} (${trust < 30 ? 'seeking apprentice' : trust < 60 ? 'testing you' : 'bonded'})`}
        </div>
        <div ref={feedRef} onScroll={() => { if (nearBottom()) setUnread(false); }} data-region="cinematic-feed" data-campaign-id={gmCampaign ?? ''} style={{ flex: 1, overflowY: 'auto', paddingRight: 8 }}>
          {(live ? gmFeed : log).map((l, i) => (
            <div key={i} style={{ margin: '10px 0', animation: 'bootIn .5s ease-out' }}>
              <div style={{ fontSize: 'var(--sys-font-size-caption)', letterSpacing: 2, color: l.who === 'YOU' || l.who.startsWith('YOU') ? 'var(--cyan)' : l.who === 'SYSTEM' ? 'var(--dim)' : '#ff8899' }}>
                {l.who}{l.mood && MOODS[l.mood] ? ` · ${MOODS[l.mood].label}` : ''}
              </div>
              <div style={{ fontSize: 'var(--sys-font-size-body)', lineHeight: 1.65, whiteSpace: 'pre-wrap', color: l.who === 'SYSTEM' ? 'var(--dim)' : 'var(--txt)' }}>{l.text}</div>
            </div>
          ))}
          {(live ? gmBusy : busy) && <div style={{ color: 'var(--dim)', fontSize: 'var(--sys-font-size-meta)' }}>…the GM engine adjudicates…</div>}
        </div>
        {unread && (
          <div className="holo-btn primary" style={{ alignSelf: 'center', fontSize: 'var(--sys-font-size-caption)', padding: '3px 14px', margin: '2px 0' }}
            onClick={() => { feedRef.current?.scrollTo(0, 99999); setUnread(false); }}>New messages ↓</div>
        )}

        {/* choice wheel — live: GM suggestions (never rails); scripted: the Malice scene */}
        <div className="sec-h">{live ? 'Suggested Responses — click to draft (does not send)' : 'Structured Choices — mechanically weighted'}</div>
        <div style={live ? { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, flex: '0 0 auto' } : undefined}>
        {(live ? liveChoices : choices).map((c) => (
          <div key={c.key} className="holo-card" style={{ opacity: c.disabled ? 0.4 : 1, pointerEvents: c.disabled ? 'none' : 'auto', margin: 0 }}
            onClick={c.run}>
            <div className="n" style={{ fontSize: 'var(--sys-font-size-control)' }}>
              <span style={{ color: 'var(--amber)', fontSize: 'var(--sys-font-size-caption)', letterSpacing: 1, marginRight: 8 }}>[{c.tag}]</span>
              {c.label}
            </div>
            <div className="t" style={{ letterSpacing: 0 }}>{c.weight}</div>
          </div>
        ))}
        </div>

        {/* Slicer Override */}
        <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center' }}>
          <span style={{ color: 'var(--cyan)', fontSize: 'var(--sys-font-size-control)', animation: 'stripePulse 1.4s infinite' }}>▮</span>
          <input className="holo-input" style={{ flex: 1, width: 'auto' }} value={live ? narrativeDraft : input}
            placeholder="…or type a custom action / statement (Slicer Override)"
            onChange={(e) => live ? useGenesis.getState().setNarrativeDraft(e.target.value) : setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submitOverride()} />
          <span className={`holo-btn ${(live ? narrativeDraft : input).trim() ? 'primary' : 'disabled'}`} style={{ fontSize: 'var(--sys-font-size-caption)', padding: '6px 14px' }} onClick={submitOverride}>Transmit</span>
        </div>
        <div style={{ fontSize: 'var(--sys-font-size-label)', color: 'var(--dim)', marginTop: 3 }}>
          override → rules engine → RFC6902 patch batch → O(1) state update → scene re-render (local adjudicator; qwen engine swaps in via Tauri)
        </div>
      </div>

      {/* right: the avatar */}
      <div style={{ borderLeft: '1px solid var(--line)', position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(340px 500px at 50% 62%, ${aura}44, transparent 70%)`, transition: 'background 0.8s ease' }} />
        {/* alpha-masked portrait slot — real ComfyUI anchor when generated */}
        <div style={{ position: 'relative', width: 300, height: 430, marginBottom: 0 }}>
          <AvatarImage urid={live ? focusNpc?.id : getId(malice)} aura={aura} />
          <div style={{
            position: 'absolute', inset: 0,
            background: `linear-gradient(180deg, transparent 4%, ${aura}22 40%, #05080d 96%)`,
            clipPath: 'polygon(30% 2%, 70% 2%, 78% 14%, 74% 30%, 88% 55%, 82% 100%, 18% 100%, 12% 55%, 26% 30%, 22% 14%)',
            border: 'none', filter: `drop-shadow(0 0 22px ${aura}66)`, transition: 'all 0.8s ease',
          }} />
          <div style={{ position: 'absolute', top: '11%', left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: 26 }}>
            <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#ffb300', boxShadow: '0 0 12px #ffb300, 0 0 26px #ffb30088', transition: 'all .5s' }} />
            <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#ffb300', boxShadow: '0 0 12px #ffb300, 0 0 26px #ffb30088' }} />
          </div>
          <div style={{ position: 'absolute', bottom: 8, left: 0, right: 0, textAlign: 'center', fontSize: 'var(--sys-font-size-label)', letterSpacing: 2, color: 'var(--dim)' }}>
            ALPHA-MASKED PORTRAIT — ComfyUI `load_portrait` slot
          </div>
        </div>
        <div className="holo-panel" style={{ width: '92%', margin: '0 0 12px', padding: '8px 12px' }}>
          <div style={{ fontSize: 'var(--sys-font-size-control)', color: '#ff8899', letterSpacing: 1 }}>{live ? (focusNpc?.name ?? '—') : (getName(malice) ?? 'Darth Malice')}
            <span style={{ fontSize: 'var(--sys-font-size-label)', color: 'var(--dim)', marginLeft: 8 }}>{live ? (focusNpc?.id ?? '') : (getId(malice) ?? '')}</span>
          </div>
          <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--amber)', letterSpacing: 1.5, marginTop: 2 }}>MOOD: {MOODS[mood]?.label ?? '—'}</div>
          {live ? (
            <div style={{ fontSize: 'var(--sys-font-size-label)', color: 'var(--dim)', marginTop: 6 }}>
              {gmRuntime?.active_npcs?.[focusNpc?.id]?.disposition ?? ''}
            </div>
          ) : (<>
            <div className="gauge amber" style={{ width: '100%', marginTop: 6 }}><i style={{ width: `${trust}%` }} /></div>
            <div style={{ fontSize: 'var(--sys-font-size-label)', color: 'var(--dim)', marginTop: 2 }}>trust_meter {trust}/100 — live registry value, patched by your choices</div>
          </>)}
        </div>
      </div>
    </div>
  );
}
