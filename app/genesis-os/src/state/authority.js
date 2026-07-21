/* GEN-ARCH-003 — THE AUTHORITY MATRIX, enforced.
 * Write permission = (authority, target, path-prefix). Anything not granted
 * fails closed. Mirrors RUNTIME_AUTHORITY.md §2 — keep them in sync. */

const CAMPAIGN_RULES = {
  campaign_engine: ['/campaign_id', '/name', '/created_at', '/party', '/characters', '/flags', '/scene', '/current_location_id'],
  exploration_engine: ['/current_location_id'], // via travel outcome only
  providence_engine: ['/world_phase', '/ffg_pools', '/flags', '/characters', '/scheduled'],
  starship_engine: ['/ship'],
  faction_engine: ['/flags/investigations'],
  relationship_engine: ['/characters'], // synced copies of patched entities
  combat_engine: ['/flags', '/characters'],
  inventory_engine: ['/characters'],
  progression_engine: ['/characters'],
  campaign_sync: ['/characters'], // internal save-sync writes
};

const ENTITY_RULES = {
  combat_engine: ['/grid_state', '/hit_points', '/conditions', '/strain', '/wounds'],
  relationship_engine: ['/trust_meter', '/relationships', '/_scene_flags', '/alignment_tracking', '/romance_relationships'],
  companion_engine: ['/goals', '/decisions'],
  faction_engine: ['/nodes', '/resources', '/plans', '/investigations'],
  nemesis_engine: ['/progression_stage', '/revealed', '/threat_level', '/name', '/plans', '/grudge_origin', '/tracking_target'],
  inventory_engine: ['/equipment'],
  progression_engine: ['/level', '/xp', '/features'],
  social_engine: ['/_scene_flags', '/mood_state'],
  creator_engine: ['/'], // may ADD whole new entities (registerEntity path), never edit existing — enforced in store
  data_inspector: ['/'], // DATA-mode dev inspector (Forge browser QA probes) — not a gameplay surface
};

function allowed(rules, authority, path) {
  const prefixes = rules[authority];
  if (!prefixes) return false;
  return prefixes.some((p) => p === '/' || path === p || path.startsWith(p + '/') || path.startsWith(p));
}

/** Returns null if authorized; otherwise a rejection reason string. */
export function checkAuthority(authority, target, ops) {
  if (!authority) return 'no authority declared — Revelation may not mutate authoritative state';
  if (authority === 'revelation' || authority === 'ai_gm') {
    return `${authority} may never mutate authoritative state (submit an intent)`;
  }
  const rules = target === 'campaign' ? CAMPAIGN_RULES : ENTITY_RULES;
  for (const op of ops) {
    if (!allowed(rules, authority, op.path)) {
      return `authority '${authority}' has no write permission for ${target}:${op.path}`;
    }
  }
  return null;
}

export const AUTHORITIES = [...new Set([...Object.keys(CAMPAIGN_RULES), ...Object.keys(ENTITY_RULES)])];
