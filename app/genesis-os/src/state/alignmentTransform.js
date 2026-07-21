/* THE ALIGNMENT TRANSFORM ENGINE (Soul family).
 * Implements docs/systems/ALIGNMENT_TRANSFORM_ENGINE.md: when a character's
 * alignment_score crosses a band boundary (dark ≤30 / neutral / light ≥70),
 * scan their owned features for `corruption_transform` data and swap each
 * feature to its mirrored counterpart — redemption and fall arcs without
 * respecing. Mastery persists when `retains_mastery: true`. Swaps are
 * progression_engine envelopes; the ui_transition hint rides in diagnostics
 * so Revelation can animate the card change. Pure data — the engine knows
 * nothing about any specific feature. */
import { useGenesis, getName } from './store.js';

const bandOf = (score) => (score <= 30 ? 'dark' : score >= 70 ? 'light' : 'neutral');

/** Find a Feature entity's transform block, tolerant of shape. */
function transformBlock(featDoc) {
  return featDoc?.corruption_transform ?? featDoc?.mechanics?.corruption_transform ?? null;
}

/** Which counterpart applies when entering `band`? */
function counterpartFor(block, band) {
  if (band === 'dark' && block.can_corrupt && block.corrupts_to_feature_id) return block.corrupts_to_feature_id;
  if (band === 'light' && block.can_purify && block.purifies_to_feature_id) return block.purifies_to_feature_id;
  return null;
}

/** Called after every alignment shift with (urid, oldScore, newScore).
 * Emits feature-swap envelopes on band crossings. Returns swap list. */
export function checkTransforms(urid, oldScore, newScore, intent_id = null) {
  const oldBand = bandOf(oldScore);
  const newBand = bandOf(newScore);
  if (oldBand === newBand) return [];
  const g = useGenesis.getState();
  const char = g.registry.get(urid);
  const owned = char?.features;
  if (!Array.isArray(owned) || owned.length === 0) return [];

  const swaps = [];
  owned.forEach((entry, idx) => {
    const featId = typeof entry === 'string' ? entry : entry?.feature_id ?? entry?.id;
    if (!featId) return;
    const featDoc = g.registry.get(featId);
    const block = featDoc ? transformBlock(featDoc) : null;
    if (!block) return;
    const target = counterpartFor(block, newBand);
    if (!target || target === featId) return;
    const newEntry = typeof entry === 'string'
      ? target
      : { ...entry, feature_id: target, ...(block.retains_mastery ? {} : { mastery: 0, xp_invested: 0 }) };
    const env = g.dispatchEvent({
      event_type: newBand === 'dark' ? 'feature_corrupted' : 'feature_purified',
      authority: 'progression_engine', target: urid, intent_id,
      ops: [{ op: 'replace', path: `/features/${idx}`, value: newEntry }],
      diagnostics: {
        from_feature: featId, to_feature: target,
        band_crossing: `${oldBand}->${newBand}`,
        retains_mastery: block.retains_mastery ?? false,
        ui_transition: featDoc?.ui_transition ?? { animation: 'card_flicker_to_glow' },
      },
    });
    if (env) {
      swaps.push({ from: featId, to: target });
      const toName = getName(g.registry.get(target)) ?? target;
      useGenesis.getState().addJournal('progression',
        newBand === 'dark'
          ? `Something in ${getName(char)} hardens. ${getName(g.registry.get(featId)) ?? featId} has become ${toName}.`
          : `Something in ${getName(char)} eases. ${getName(g.registry.get(featId)) ?? featId} has become ${toName}.`);
    }
  });
  return swaps;
}

/* dev/QA hook */
if (typeof window !== 'undefined') window.__checkTransforms = checkTransforms;
