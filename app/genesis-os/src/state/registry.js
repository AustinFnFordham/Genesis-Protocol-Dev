/* Registry loader — the fetch chain that kills hardcoding.
 * 1. Tauri shell:   invoke('load_registry')            (Rust scans gold dirs)
 * 2. API bridge:    GET http://localhost:8788/api/v1/registry  (FastAPI, live scan)
 * 3. Dev fallback:  /registry.json                     (static export, last resort)
 * Same payload contract at every tier: {registry, manifest, campaign, pipeline}. */
export const API = 'http://localhost:8788/api/v1';

export async function loadRegistry() {
  try {
    const { invoke } = await import('@tauri-apps/api/core');
    const raw = await invoke('load_registry');
    return { ...JSON.parse(raw), source: 'tauri' };
  } catch { /* not in the shell */ }
  try {
    const r = await fetch(`${API}/registry`, { signal: AbortSignal.timeout(2500) });
    if (r.ok) return { ...(await r.json()), source: 'api-bridge' };
  } catch { /* bridge not running */ }
  const r = await fetch('/registry.json');
  if (!r.ok) throw new Error('no Tauri shell, no API bridge at :8788, no static registry.json');
  return { ...(await r.json()), source: 'static-fallback' };
}

/** Persist the live CampaignState (fire-and-forget; the game never blocks on saves). */
export function persistCampaign(state) {
  fetch(`${API}/campaign`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(state),
  }).catch(() => { /* bridge offline — in-memory only this session */ });
}

/** Portrait URL for a character; the <img> onError keeps the placeholder. */
export const portraitUrl = (characterId) => `${API}/portrait/${characterId}`;
