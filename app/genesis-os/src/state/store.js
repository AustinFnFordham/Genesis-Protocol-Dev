/* GENESIS//OS global state — Phase One (governed engine architecture).
 * Single tree, slice ownership. ALL mutations flow through dispatchEvent:
 * event envelope → authority matrix (fail-closed) → RFC6902 validate-before-
 * apply → append-only ledger → Chaos matcher. Revelation (the UI) never calls
 * this directly for gameplay — it submits intents (intents.js, GEN-RULE-001). */
import { create } from 'zustand';
import { applyPatch, validate } from 'fast-json-patch';
import { persistCampaign } from './registry.js';
import { checkAuthority } from './authority.js';
import { makeEnvelope, appendLedger, ledgerRejection } from './events.js';

export const useGenesis = create((set, get) => ({
  registry: new Map(),
  manifest: [],
  campaign: null,          // live CampaignState (mutable save state)
  campaignActive: false,   // false until New Game commits
  journal: [],             // STRUCTURED campaign record — projection of the server chronicle ONLY
  diagnostics: [],         // operational/API-bridge messages (dev channel, NOT the Journal)
  mountEpoch: 0,           // campaign mount transaction id — stale hydration responses are discarded
  mountedCampaignId: null, // the campaign every visible projection must agree on
  patchLog: [],
  selected: null,
  gmView: false,
  engagement: 'dialogue',  // 'select' | 'dialogue' | 'gm' | 'diorama' | 'ship' | 'creator'
  overlay: null,           // 'progression' | 'workbench' | null
  source: 'unknown',       // where the registry came from (tauri/api/static)
  gmCampaign: null,        // mounted GM campaign id (one at a time — campaign isolation)
  unresolvedAction: null,  // {view, label} — guard against abandoning an open interaction
  actionPrefill: '',       // contextual action panel → declaration input

  gmRuntime: null,         // player-visible slice of the MOUNTED runtime — the truth layer
  setGmCampaign: (id) => set({ gmCampaign: id }),
  /** Refresh the mounted runtime slice. ALL player-facing views resolve the
   * active character through gmRuntime → metadata.active_player. The client
   * store caches display state; it never decides who is active. */
  refreshGmRuntime: async () => {
    try {
      const rt = await (await fetch('http://localhost:8788/api/v1/gm/state')).json();
      const prev = get().gmCampaign;
      const epoch = rt.mount_epoch ?? 0;
      // The mount transaction: every visible projection must agree on this
      // campaign_id + epoch. Stale async responses are discarded downstream.
      set({ gmRuntime: rt.mounted ? rt : null, gmCampaign: rt.mounted ?? null,
            mountedCampaignId: rt.campaign_id ?? rt.mounted ?? null, mountEpoch: epoch });
      // CAMPAIGN ISOLATION: switching campaigns replaces EVERY campaign-scoped
      // projection ATOMICALLY. Nothing from the previous world may survive —
      // narrative, journal, dice, opening are cleared, then rebuilt from the
      // newly-mounted campaign's server-owned records under this epoch.
      if (rt.mounted && (rt.mounted !== prev || get().gmFeed.length === 0)) {
        if (rt.mounted !== prev) {
          set({ diceEvents: [], reactionWindow: null, unresolvedAction: null,
                narrativeDraft: '', journal: [], opening: null, patchLog: [], gmFeed: [] });
        }
        get().hydrateSession(rt);
        get().hydrateJournalFromChronicle(epoch, rt.mounted);
        get().loadOpening(epoch, rt.mounted);
      }
      if (!rt.mounted) set({ gmFeed: [], gmOptions: [], gmFocusNpc: null, journal: [], opening: null });
      return rt;
    } catch { set({ gmRuntime: null }); return null; }
  },
  setUnresolvedAction: (ua) => set({ unresolvedAction: ua }),
  setActionPrefill: (t) => set({ actionPrefill: t }),
  diceEvents: [],          // verified GM rolls for the Command & Record dice feed
  addDiceRolls: (rolls, context) => set((s) => ({
    diceEvents: [...s.diceEvents, ...rolls.map((r) => ({ ...r, context, t: Date.now() }))].slice(-40),
  })),
  reactionWindow: null,    // §17.8 quick-time prompt {prompt, options, timer_seconds}
  setReactionWindow: (rw) => set({ reactionWindow: rw }),

  /* ---- THE SHARED MOUNTED SESSION (Checkpoint One) ----
   * The transcript is SERVER-OWNED; this is its projection. No tab component
   * owns conversation state — Narrative, Living Table, Tactical, and Ship
   * all read here, and all declarations flow through declareToGm. Tab
   * switches change the lens, never the session. */
  gmFeed: [],              // projection of runtime.transcript
  gmOptions: [],           // pending suggestions (survive navigation)
  gmBusy: false,
  gmFocusNpc: null,        // {id, name} active speaker
  narrativeDraft: '',      // unsubmitted text survives view changes
  setNarrativeDraft: (t) => set({ narrativeDraft: t }),
  _lastCommandId: null,    // duplicate prevention

  /** Hydrate the session projection from the server transcript (mount,
   * refresh recovery, campaign switch). Canonical truth wins. */
  hydrateSession: (rt) => {
    const feed = (rt?.transcript ?? []).map((e) => ({
      who: e.type === 'player' ? 'YOU' : e.type === 'mechanics' ? 'SYSTEM'
        : e.type === 'narrator' ? 'NARRATOR' : (rt?.active_npcs?.[e.speaker_id]?.name ?? e.speaker_id ?? 'npc').toUpperCase(),
      npcId: e.type === 'npc' ? e.speaker_id : null,
      text: e.type === 'mechanics' ? `⚂ ${e.text}` : [e.text && (e.type === 'npc' ? `“${e.text}”` : e.text), e.narration, e.behavior].filter(Boolean).join('\n'),
      mood: e.mood, entryId: e.entry_id, commandId: e.source_command_id,
    }));
    const lastNpc = [...(rt?.transcript ?? [])].reverse().find((e) => e.type === 'npc');
    set({
      gmFeed: feed,
      gmOptions: rt?.conversation?.suggestions ?? [],
      gmFocusNpc: lastNpc ? { id: lastNpc.speaker_id, name: rt?.active_npcs?.[lastNpc.speaker_id]?.name ?? lastNpc.speaker_id } : null,
    });
    if (rt?.conversation?.unresolved) {
      set({ unresolvedAction: { view: 'dialogue', label: 'You are in an unresolved conversation on the Narrative View.' } });
    }
  },

  /* ---- THE ONE MOUNTED PROJECTION (UX/UI Contract Rev 1.1, steps B+C) ----
   * Committed in a SINGLE atomic set(). Panels select from mounted.projection;
   * no sequential per-field hydration -> no transient cross-panel mixtures. */
  mounted: { context: { campaign_id: null, mount_epoch: 0, state_revision: 0 }, projection: null, status: 'uninitialized' },
  selectedCharacterId: null,   // explicit character binding (Rev 1.1 §1) — replaces implicit active_player
  /** CampaignMountCoordinator: fetch the whole projection, verify epoch/campaign,
   * commit ONCE. Stale responses (a switch during the await) are discarded. */
  mountProjection: async (cid) => {
    const targetEpoch = get().mountEpoch + 1;
    set({ mountEpoch: targetEpoch, mountedCampaignId: cid, mounted: { ...get().mounted, status: 'mounting' } });
    try {
      const r = await fetch('http://localhost:8788/api/v1/gm/mount', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ campaign_id: cid }),
      });
      if (!r.ok) throw new Error((await r.json()).detail ?? 'mount failed');
      const p = await (await fetch('http://localhost:8788/api/v1/gm/projection')).json();
      // ATOMIC COMMIT GUARD: only apply if this is still the current mount and campaign.
      if (get().mountedCampaignId !== cid) return { discarded: true };
      if (p.campaign_id && p.campaign_id !== cid) return { discarded: true };
      // C.5 FAIL-SAFE: never commit a projection that failed server validation.
      if (p.projection_emitted === false || (p.validation && p.validation.semantic_valid === false)) {
        set({ mounted: { ...get().mounted, status: 'error', projection: null } });
        return { ok: false, error: 'projection failed validation', validation: p.validation };
      }
      set({
        mounted: {
          context: { campaign_id: p.campaign_id, mount_epoch: p.mount_epoch, state_revision: p.state_revision },
          projection: p, status: p.mounted ? 'ready' : 'empty',
        },
        selectedCharacterId: p.selected_character_id ?? null,
        mountEpoch: p.mount_epoch ?? targetEpoch,
      });
      // legacy mirror (until panels D–L re-point): keep gm-based projections in sync
      await get().refreshGmRuntime();
      return { ok: true, projection: p };
    } catch (e) {
      set({ mounted: { ...get().mounted, status: 'error' } });
      return { ok: false, error: String(e.message) };
    }
  },
  selectCharacter: (characterId) => set({ selectedCharacterId: characterId }),

  /* ---- CAMPAIGN-SCOPED PROJECTIONS (Phase A isolation; legacy mirror pending D–L) ---- */
  opening: null,           // per-campaign opening crawl (server-owned, replayed)
  /** Load the mounted campaign's opening crawl. Generated once from the
   * campaign seed and persisted server-side (authored opening.md is gold,
   * else GM-generated under the opening contract); replayed on mount/restart.
   * It is NOT regenerated as a substitute for state isolation. */
  loadOpening: async (epoch, cid) => {
    epoch = epoch ?? get().mountEpoch; cid = cid ?? get().mountedCampaignId;
    try {
      const o = await (await fetch('http://localhost:8788/api/v1/gm/opening')).json();
      // STALE-RESPONSE GUARD: a campaign switch during the await invalidates this.
      if (get().mountEpoch !== epoch) return null;
      if (o.campaign_id && cid && o.campaign_id !== cid) return null;
      set({ opening: o }); return o;
    } catch { return null; }
  },
  /** THE STRUCTURED JOURNAL — a per-campaign projection of the server
   * chronicle (major events, decisions, outcomes), NOT a transcript copy.
   * Fully isolated: cleared on switch, rebuilt under the current mount epoch. */
  hydrateJournalFromChronicle: async (epoch, cid) => {
    epoch = epoch ?? get().mountEpoch; cid = cid ?? get().mountedCampaignId;
    try {
      const r = await (await fetch('http://localhost:8788/api/v1/gm/chronicle?n=200')).json();
      // STALE-RESPONSE GUARD: discard if the mount changed while awaiting, or if
      // the response belongs to a different campaign/epoch than the live one.
      if (get().mountEpoch !== epoch) return [];
      if (r.campaign_id && cid && r.campaign_id !== cid) return [];
      if (r.mount_epoch != null && r.mount_epoch !== get().mountEpoch) return [];
      const entries = (r.entries ?? []).map((e) => ({
        t: e.timestamp ? Date.parse(e.timestamp) : Date.now(),
        kind: e.source_resolution === 'combat_master' ? 'combat' : 'event',
        text: e.objective_event ?? '', location: e.location,
        participants: e.participants, eventId: e.event_id,
      }));
      set({ journal: entries }); return entries;
    } catch { return []; }
  },

  /** THE SINGLE DECLARATION PIPELINE. Every view calls this; no view owns it. */
  declareToGm: async (text) => {
    const t0 = get();
    const decl = (text ?? '').trim();
    if (!decl || t0.gmBusy) return { accepted: false };
    // durable idempotency: the SERVER enforces exactly-one-commit per key
    const idem = `idem_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
    set({ gmBusy: true, narrativeDraft: '', gmOptions: [], gmFeed: [...t0.gmFeed, { who: 'YOU', text: decl }] });
    try {
      const r = await fetch('http://localhost:8788/api/v1/gm/turn', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ declaration: decl, idempotency_key: idem }),
      });
      const t = await r.json();
      if (t.status === 'duplicate') { set({ gmBusy: false }); return { accepted: false, duplicate: true }; }
      if (t.status !== 'ok') {
        set((s) => ({ gmFeed: [...s.gmFeed, { who: 'SYSTEM', text: `STEWARD BLOCKED: ${t.reason ?? 'invalid turn'}` }], gmBusy: false }));
        return { accepted: false };
      }
      if (t.command_id && t.command_id === get()._lastCommandId) { set({ gmBusy: false }); return { accepted: false, duplicate: true }; }
      set({ _lastCommandId: t.command_id });
      if (t.mechanics?.dice?.length) {
        get().addDiceRolls(t.mechanics.dice.map((d) => ({ roll_id: d.roll_id, formula: d.formula, individual_dice: d.dice, final_total: d.total, purpose: d.purpose, mode: 'normal', modifiers: 0 })), t.mechanics.classification);
      }
      if (t.reaction_window) get().setReactionWindow(t.reaction_window);
      // canonical truth: rehydrate feed + journal + anchor from the committed
      // runtime. The Journal is refreshed from the SERVER chronicle (Record
      // Keeper wrote it) — the client never hand-appends journal entries.
      const rt = await get().refreshGmRuntime();
      if (rt?.mounted) { get().hydrateSession(rt); get().hydrateJournalFromChronicle(); }
      set({ gmBusy: false });
      // mode routing
      if (t.combat_active) {
        get().setUnresolvedAction({ view: 'diorama', label: 'A combat turn is unresolved on the Tactical View.' });
        setTimeout(() => get().setEngagement('diorama'), 1600);
      }
      return { accepted: true, turn: t };
    } catch (e) {
      set((s) => ({ gmFeed: [...s.gmFeed, { who: 'SYSTEM', text: `GM link lost: ${e.message}` }], gmBusy: false }));
      return { accepted: false };
    }
  },

  boot: ({ registry, manifest, campaign, source }) => {
    const map = new Map(Object.entries(registry));
    let man = manifest;
    const hasSave = campaign && campaign.campaign_id && campaign.party?.length;
    // Rehydrate player-created entities that ride inside the save file
    // (created characters, spawned nemeses) back into the O(1) registry.
    if (hasSave && campaign.characters) {
      for (const [urid, doc] of Object.entries(campaign.characters)) {
        if (!map.has(urid)) {
          map.set(urid, doc);
          man = [...man, { urid, schema: doc.classification === 'shadow_node' || doc.grudge_origin ? 'Nemesis' : 'Character', tier: 'wip', name: doc.name ?? urid }];
        }
      }
    }
    set({
      registry: map, manifest: man, source: source ?? 'unknown',
      campaign: campaign ?? null,
      campaignActive: !!hasSave,
      selected: man[0]?.urid ?? null,
      engagement: 'select', // the campaign-selection layer is the front door
      _bootCampaign: hasSave ? structuredClone(campaign) : null,
    });
    if (hasSave) get().addDiagnostic('bridge', `Save state loaded — ${campaign.name ?? campaign.campaign_id}.`);
  },

  select: (urid) => set({ selected: urid }),
  toggleGm: () => set((s) => ({ gmView: !s.gmView })),
  setEngagement: (m) => set({ engagement: m }),
  setOverlay: (o) => set({ overlay: o }),

  /* ---- RESTART CAMPAIGN FROM OPENING (Phase A) ----
   * Server backs up all state as a regression fixture, clears session state,
   * preserves the persisted opening crawl + foundation, rebuilds a fresh
   * session, then the client re-hydrates every campaign-scoped projection. */
  restartBusy: false,
  restartCampaign: async (cid) => {
    const id = cid ?? get().gmCampaign;
    if (!id || get().restartBusy) return { ok: false };
    set({ restartBusy: true });
    try {
      const r = await fetch('http://localhost:8788/api/v1/gm/restart', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ campaign_id: id, confirm: true }),
      });
      const res = await r.json();
      // force a full projection rebuild: drop the mounted id so refresh detects a switch
      set({ gmCampaign: null, journal: [], opening: null, gmFeed: [], diceEvents: [], restartBusy: false });
      await get().refreshGmRuntime();
      return { ok: true, ...res };
    } catch (e) { set({ restartBusy: false }); return { ok: false, error: String(e.message) }; }
  },

  /* ---- ADD CHARACTER entry point (Phase A route; Phase C fills the flow) ---- */
  addCharacter: { open: false, role: null },
  openAddCharacter: () => set({ addCharacter: { open: true, role: null } }),
  closeAddCharacter: () => set({ addCharacter: { open: false, role: null } }),
  setAddCharacterRole: (role) => set((s) => ({ addCharacter: { ...s.addCharacter, role } })),

  // The Journal is the chronicle projection ONLY. Client-authored operational
  // messages must NOT enter it — they go to the diagnostics channel.
  addJournal: (kind, text) =>
    set((s) => ({ journal: [...s.journal, { t: Date.now(), kind, text }] })),
  addDiagnostic: (kind, text) =>
    set((s) => ({ diagnostics: [...s.diagnostics, { t: Date.now(), kind, text }].slice(-100) })),

  /** THE CAMPAIGN INITIALIZATION LOOP.
   * Called by the creator after the guardrail passes. Instantiates a fresh
   * CampaignState, injects the character into party, sets the starting node,
   * persists through the API bridge, and flips the shell into game mode. */
  startCampaign: (characterUrid) => {
    const s = get();
    const char = s.registry.get(characterUrid);
    const state = {
      campaign_id: `campaign_${Date.now().toString(36)}`,
      name: `The ${char?.name ?? 'Unknown'} Chronicle`,
      created_at: new Date().toISOString(),
      current_location_id: 'node_coruscant',
      party: [characterUrid],
      characters: { [characterUrid]: char },   // created entities live in the save
      ffg_pools: { duty: 0, obligation: 10, morality: char?.moral_compass ?? 0 },
      wanted_level: 0,
      flags: { holocron_state: 'intact' },
      world_phase: 0,
      seed: Date.now() % 2147483647, // GEN-TEST-002: campaign RNG root
    };
    set({ campaign: state, campaignActive: true, engagement: 'dialogue', selected: characterUrid, _bootCampaign: structuredClone(state) });
    get().addDiagnostic('bridge', `NEW CAMPAIGN — ${state.name}.`);
    persistCampaign(state);
    return state;
  },

  /** GEN-TEST-001 — LOAD THE TEST CAMPAIGN.
   * Instantiates a live campaign from a CampaignState registry entity whose
   * party members are REAL entities (referential integrity is a hard gate:
   * missing members abort the load). Deterministic seed derives from the
   * campaign_id so replays are reproducible. */
  loadCampaignFromEntity: (stateUrid) => {
    const s = get();
    const cs = s.registry.get(stateUrid ?? s.manifest.find((m) => m.schema === 'CampaignState')?.urid);
    if (!cs) { console.error('LOAD REJECTED: no CampaignState entity'); return false; }
    const wanted = cs.party?.character_ids ?? [];
    const missing = wanted.filter((u) => !s.registry.get(u));
    if (missing.length) {
      console.error('LOAD REJECTED (referential integrity):', missing);
      get().addDiagnostic('bridge', `CAMPAIGN LOAD REFUSED — phantom party members: ${missing.join(', ')}. Run the forge.`);
      return false;
    }
    let seed = 0;
    for (const ch of (cs.campaign_id ?? 'genesis')) seed = (seed * 31 + ch.charCodeAt(0)) % 2147483647;
    const characters = Object.fromEntries(wanted.map((u) => [u, s.registry.get(u)]));
    const state = {
      campaign_id: cs.campaign_id ?? `campaign_${Date.now().toString(36)}`,
      name: cs.campaign_name ?? 'Unnamed Campaign',
      created_at: new Date().toISOString(),
      current_location_id: 'node_coruscant',
      party: wanted,
      characters,
      ffg_pools: { duty: 0, obligation: 10, morality: 0 },
      wanted_level: 0,
      flags: {},
      world_phase: 0,
      seed,
      party_meta: { party_name: cs.party?.party_name, party_level: cs.party?.party_level, party_xp: cs.party?.party_xp },
      session_context: cs.current_session ?? null,
    };
    set({ campaign: state, campaignActive: true, engagement: 'dialogue', selected: wanted[0] ?? null, _bootCampaign: structuredClone(state) });
    get().addDiagnostic('bridge', `CAMPAIGN LOADED — ${state.name}. ${cs.party?.party_name ?? 'The party'} stands ready.`);
    persistCampaign(state);
    return state;
  },

  /** GEN-TEST-002 — DETERMINISM REPLAY CHECK.
   * Re-applies every accepted campaign-target envelope from the session
   * ledger onto the boot snapshot and compares with the live campaign.
   * Same seed + same events ⇒ identical state, or the law is broken. */
  _bootCampaign: null,
  replayCheck: () => {
    const s = get();
    if (!s._bootCampaign || !s.campaign) return { ok: false, reason: 'no boot snapshot' };
    const { ledgerTail } = window.__ledger ? { ledgerTail: window.__ledger.tail } : {};
    const events = (ledgerTail ? ledgerTail(Infinity) : []).filter(
      (e) => e.target === 'campaign' && !e.diagnostics?.rejected && !e.event_type.startsWith('REJECTED:')
    );
    let doc = structuredClone(s._bootCampaign);
    for (const env of events) {
      try { doc = applyPatch(doc, env.operations, true, false).newDocument; }
      catch (err) { return { ok: false, reason: `replay diverged at ${env.event_id}: ${err.message}`, events: events.length }; }
    }
    // campaign.characters is a DERIVED save-sync of entity state (entity
    // envelopes own that truth) — compare the campaign-authoritative slice.
    const strip = ({ characters, ...rest }) => rest;
    const ok = JSON.stringify(strip(doc)) === JSON.stringify(strip(s.campaign));
    return { ok, events: events.length, reason: ok ? 'ledger replay reproduces live campaign state exactly' : 'MISMATCH — replay does not reproduce live state' };
  },

  /** GEN-ARCH-002/003 — THE ONLY LEGAL MUTATION PATH.
   * Wraps ops in an event envelope, enforces the authority matrix
   * (fail-closed), applies via RFC6902 with validate-before-apply,
   * ledgers the result, and runs the Chaos matcher on acceptance.
   * Returns the accepted envelope or false. */
  dispatchEvent: ({ event_type, authority, target, ops, actor_id, intent_id, caused_by, visibility, journal_payload, diagnostics }) => {
    const s = get();
    const env = makeEnvelope({
      campaign: s.campaign, event_type, authority, target, operations: ops,
      actor_id, intent_id, caused_by, visibility, journal_payload, diagnostics,
    });
    // 1. AUTHORITY GATE — fail closed
    const denial = checkAuthority(authority, target, ops);
    if (denial) {
      ledgerRejection(env, denial);
      console.error('EVENT REJECTED (authority):', denial, env);
      return false;
    }
    // 2. APPLY (legacy applier: validate-before-apply guardrail)
    const ok = get()._applyPatches(target, ops);
    if (!ok) { ledgerRejection(env, 'patch guardrail rejection'); return false; }
    // 3. LEDGER + JOURNAL
    appendLedger(env);
    if (journal_payload?.text) get().addJournal(journal_payload.kind ?? 'system', journal_payload.text);
    // 4. CHAOS — matcher consumes accepted envelopes (lazy import breaks cycle)
    if (get()._chaosMatch) get()._chaosMatch(env);
    return env;
  },
  _chaosMatch: null, // installed by chaos.js at module init

  /** INTERNAL RFC6902 applier. Do not call from modules/UI — use
   * dispatchEvent (engines) or submitIntent (Revelation). */
  _applyPatches: (target, ops) => {
    const s = get();
    if (target === 'campaign') {
      if (!s.campaign) { console.error('PATCH REJECTED: no active campaign'); return false; }
      const err = validate(ops, s.campaign);
      if (err) { console.error('PATCH REJECTED (guardrail):', err); return false; }
      const next = applyPatch(structuredClone(s.campaign), ops, true, false).newDocument;
      set({ campaign: next, patchLog: [...s.patchLog, { target, ops, t: Date.now() }] });
      persistCampaign(next);
      return true;
    }
    const entity = s.registry.get(target);
    if (!entity) { console.error('PATCH REJECTED: unknown URID', target); return false; }
    const err = validate(ops, entity);
    if (err) { console.error('PATCH REJECTED (guardrail):', err); return false; }
    const next = applyPatch(structuredClone(entity), ops, true, false).newDocument;
    const registry = new Map(s.registry);
    registry.set(target, next);
    // If this entity rides in the save file (created char / spawned nemesis),
    // keep the persisted copy in sync so reloads see the patched state.
    let campaign = s.campaign;
    if (campaign?.characters?.[target]) {
      campaign = { ...campaign, characters: { ...campaign.characters, [target]: next } };
      persistCampaign(campaign);
    }
    set({ registry, campaign, patchLog: [...s.patchLog, { target, ops, t: Date.now() }] });
    return true;
  },

  /** Register a brand-new entity (creator output) into the O(1) map. */
  registerEntity: (urid, doc, schema, tier = 'wip') => {
    const s = get();
    const registry = new Map(s.registry);
    registry.set(urid, doc);
    set({ registry, manifest: [...s.manifest, { urid, schema, tier, name: doc.name ?? urid }] });
  },
}));

/* dev/QA hook: drive the store from the console (window.__genesis) */
if (typeof window !== 'undefined') window.__genesis = useGenesis;

/* ---- schema-shape-tolerant accessors ---- */
export const getId = (e) => e?.metadata?.id ?? e?.id ?? 'unknown';
export const getName = (e) => e?.metadata?.name ?? e?.name ?? getId(e);
export const getTags = (e) =>
  e?.taxonomy?.tags ?? e?.narrative_tags ?? e?.tags ?? e?._legacy?.tags ?? [];
export const getHex = (e) => e?.ui?.color ?? e?.ui?.color_hex ?? '#33e1ff';
export const getStats = (e) => {
  if (e?.stats) return e.stats;
  if (e?.base_metrics?.sw5e_stats) return e.base_metrics.sw5e_stats;
  const a = e?.ability_scores;
  if (a) return { str: a.strength, dex: a.dexterity, con: a.constitution, int: a.intelligence, wis: a.wisdom, cha: a.charisma };
  return e?._legacy?.stats ?? null;
};
export const getVisualDna = (e) =>
  e?.visual_dna ?? e?.character_sheet?.visual_dna ?? {
    identity_constants: [], gear_variables: e?.equipment ?? [], environment_context: [],
  };
export const getMorality = (e) =>
  e?.moral_compass?.morality ?? (typeof e?.moral_compass === 'number' ? e.moral_compass : null)
  ?? e?.psychological_profile?.ffg_morality ?? e?.morality ?? 0;
