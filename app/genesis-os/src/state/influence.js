/* GEN-REL-001 — THE INTER-PARTY INFLUENCE ENGINE (Soul family).
 * Implements docs/systems/INTER_PARTY_INFLUENCE_ENGINE.md deterministically:
 * a tagged action ripples through the party — the actor's alignment shifts
 * directly, every other member makes a seeded Wisdom (Discipline) resistance
 * check (DC 10 + magnitude + actor CHA mod), failures drift magnitude/2
 * toward the influencing alignment. All shifts are relationship_engine
 * envelopes; every check's roll is ledgered in diagnostics. The AI GM may
 * narrate the ripple; it may never decide it.
 *
 * alignment_score: 0 (Pure Dark) … 100 (Pure Light), bands per the
 * Alignment Transform Engine: dark ≤30, neutral 31–69, light ≥70. */
import { useGenesis, getMorality, getName, getStats } from './store.js';
import { seededRng, derivedSeed } from './events.js';
import { checkTransforms } from './alignmentTransform.js';

export const bandOf = (score) => (score <= 30 ? 'dark' : score >= 70 ? 'light' : 'neutral');

/** Tolerant read: alignment_tracking if seeded, else map moral_compass
 * (−100..100) / ffg_morality onto 0..100. */
export function getAlignmentScore(e) {
  const t = e?.alignment_tracking?.alignment_score;
  if (typeof t === 'number') return t;
  const ffg = e?.psychological_profile?.ffg_morality;
  if (typeof ffg === 'number') return Math.max(0, Math.min(100, ffg)); // already 0..100
  const m = getMorality(e); // moral_compass −100..100
  if (m === null || m === undefined) return 50;
  return Math.max(0, Math.min(100, Math.round((m + 100) / 2)));
}

const chaMod = (e) => Math.floor(((getStats(e)?.cha ?? e?.ability_scores?.charisma ?? 10) - 10) / 2);
const wisMod = (e) => Math.floor(((getStats(e)?.wis ?? e?.ability_scores?.wisdom ?? 10) - 10) / 2);

/** Party + companions currently in play (mirrors the ship crew pool). */
function partyPool(g) {
  const ids = [
    ...(g.campaign?.party ?? []),
    ...g.manifest.filter((m) => m.schema === 'Companion').map((m) => m.urid),
  ];
  return [...new Set(ids)].filter((u) => g.registry.get(u));
}

function shiftEnvelope(g, urid, newScore, why, iid, extraDiag = {}) {
  const e = g.registry.get(urid);
  const has = e?.alignment_tracking !== undefined;
  const block = {
    ...(e?.alignment_tracking ?? {}),
    alignment_score: newScore,
    alignment_descriptor: bandOf(newScore),
  };
  return g.dispatchEvent({
    event_type: 'alignment_shifted', authority: 'relationship_engine', target: urid, intent_id: iid,
    ops: [{ op: has ? 'replace' : 'add', path: '/alignment_tracking', value: block }],
    visibility: 'gm_only',
    diagnostics: { why, ...extraDiag },
  });
}

const FEEDBACK = {
  light: {
    fail: (n) => `${n} sees the mercy in it. Something in them wavers toward the light.`,
    save: (n) => `${n} looks away, unmoved — but not, perhaps, untouched.`,
  },
  dark: {
    fail: (n) => `${n} watches the ruthlessness with something that is not quite disapproval.`,
    save: (n) => `${n} holds fast. "There must be another way," their silence insists.`,
  },
  neutral: {
    fail: (n) => `${n} weighs the pragmatism of it, and finds it persuasive.`,
    save: (n) => `${n} remains exactly who they were.`,
  },
};

/** THE RIPPLE. Called by resolvers with an influence_effect payload.
 * { actor, alignment: 'light'|'dark'|'neutral', magnitude 1-10, radius } */
export function applyInfluence({ actor, alignment, magnitude = 3, radius = 'party', intent_id = null }) {
  const g = useGenesis.getState();
  if (!g.campaignActive || !alignment) return { applied: false };
  const dir = alignment === 'light' ? +1 : alignment === 'dark' ? -1 : 0;
  const actorDoc = g.registry.get(actor);
  const results = [];

  // 1. The actor's own alignment shifts directly (full magnitude).
  if (actorDoc && dir !== 0) {
    const cur = getAlignmentScore(actorDoc);
    const next = Math.max(0, Math.min(100, cur + dir * magnitude));
    if (next !== cur) {
      shiftEnvelope(g, actor, next, 'own_action', intent_id, { magnitude, alignment });
      results.push({ urid: actor, from: cur, to: next, self: true });
      checkTransforms(actor, cur, next, intent_id);
    }
  }
  if (radius === 'self') return { applied: true, results };

  // 2. Every other member resists — seeded d20, fully ledgered.
  const dc = 10 + magnitude + (actorDoc ? chaMod(actorDoc) : 0);
  const rng = seededRng(derivedSeed(g.campaign));
  for (const urid of partyPool(g)) {
    if (urid === actor) continue;
    const member = g.registry.get(urid);
    const roll = 1 + Math.floor(rng() * 20);
    const total = roll + wisMod(member);
    const resisted = total >= dc;
    const cur = getAlignmentScore(member);
    let next = cur;
    if (!resisted && dir !== 0) next = Math.max(0, Math.min(100, cur + dir * Math.ceil(magnitude / 2)));
    if (next !== cur) {
      shiftEnvelope(g, urid, next, 'party_influence', intent_id, { dc, roll, total, resisted, magnitude, alignment, actor });
      checkTransforms(urid, cur, next, intent_id);
    }
    const fb = FEEDBACK[dir === 0 ? 'neutral' : alignment];
    useGenesis.getState().addJournal('influence', (resisted ? fb.save : fb.fail)(getName(member)));
    results.push({ urid, dc, roll, total, resisted, from: cur, to: next });
  }
  return { applied: true, dc, results };
}

/* dev/QA hook */
if (typeof window !== 'undefined') window.__influence = applyInfluence;
