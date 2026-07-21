/* ADD CHARACTER — campaign-level entry point (Phase A).
 * Establishes the ROLE selection, the campaign association, and the canonical
 * party-state interface contract. It intentionally does NOT write a character:
 * the full conversational creation flow is Phase C (character_creation_
 * interview_standard.yml + varon_* fixtures). The Phase C route is shown as
 * explicitly unfinished rather than silently committing an incomplete sheet. */
import React from 'react';
import { useGenesis } from '../state/store.js';

const ROLES = [
  ['primary_player_character', 'Primary Player Character', 'A full protagonist. Complete conversational creation + runtime.'],
  ['secondary_player_controlled_character', 'Second Player Character', 'A second player-controlled hero — full creation, not a supporting profile.'],
  ['companion', 'Companion', 'An allied NPC with independent motivation, loyalty, and refusal conditions.'],
  ['temporary_party_member', 'Temporary Party Member', 'A short-term ally scoped to the current arc.'],
  ['imported_character', 'Imported Character', 'Load an existing validated character sheet into this campaign.'],
];

export default function AddCharacter() {
  const { addCharacter, gmCampaign, closeAddCharacter, setAddCharacterRole } = useGenesis();
  if (!addCharacter?.open) return null;
  const role = addCharacter.role;

  return (
    <div style={{ position: 'absolute', inset: 0, background: 'rgba(3,6,12,.86)', backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 60 }}
      onClick={closeAddCharacter}>
      <div className="holo-panel" style={{ width: 560, maxHeight: '84%', overflowY: 'auto', padding: 20 }} onClick={(e) => e.stopPropagation()}>
        <div className="holo-title">Add Character
          <span style={{ flex: 1 }} />
          <span style={{ cursor: 'pointer', color: 'var(--dim)', fontSize: 'var(--sys-font-size-meta)' }} onClick={closeAddCharacter}>✕</span>
        </div>
        <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--dim)', margin: '4px 0 12px' }}>
          campaign: <span style={{ color: 'var(--gold)' }}>{gmCampaign ?? '(none mounted)'}</span> · choose the intended role — the interview adapts to it
        </div>

        {ROLES.map(([id, label, desc]) => (
          <div key={id} className={`holo-card ${role === id ? 'sel' : ''}`} style={{ cursor: 'pointer' }}
            onClick={() => setAddCharacterRole(id)}>
            <div className="n" style={{ fontSize: 'var(--sys-font-size-control)', color: role === id ? 'var(--cyan)' : undefined }}>{label}</div>
            <div className="t">{desc}</div>
          </div>
        ))}

        {role && (
          <div className="holo-panel" style={{ marginTop: 14, padding: 14, borderColor: 'var(--amber)' }}>
            <div style={{ fontSize: 'var(--sys-font-size-note)', color: 'var(--amber)', letterSpacing: 1 }}>◈ PHASE C ROUTE — CONVERSATIONAL CHARACTER CREATOR (not yet implemented)</div>
            <div style={{ fontSize: 'var(--sys-font-size-note)', color: 'var(--txt)', marginTop: 8, lineHeight: 1.6 }}>
              Selected role: <b>{role}</b> · target campaign: <b>{gmCampaign}</b>.<br />
              The full guided interview (one decision at a time, clickable + freeform, rules-aware
              negotiation, hidden GM ledger, portrait pack) lands in Phase C using the uploaded
              fixtures (character_creation_interview_standard, varon_character_runtime,
              varon_hidden_gm_ledger, relationship_maneuvers_framework, adaptive_countermovement,
              varon_avatar_prompts).
            </div>
            <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--dim)', marginTop: 10 }}>
              CANONICAL PARTY-STATE INTERFACE (contract this route will call on completion):<br />
              <code style={{ color: 'var(--cyan)' }}>POST /api/v1/gm/party/add {'{'} campaign_id, role, character_runtime {'}'}</code><br />
              → registers the validated CharacterRuntime into the mounted campaign's participant
              registry, turn/round model, party, narrative, journal, relationship, and event systems.
            </div>
            <div style={{ fontSize: 'var(--sys-font-size-caption)', color: 'var(--red)', marginTop: 8 }}>
              No character is written to campaign state from here — Phase A establishes the route only.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
