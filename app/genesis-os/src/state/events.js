/* GEN-ARCH-002 — THE EVENT ENVELOPE + APPEND-ONLY LEDGER.
 * Every accepted mutation is an envelope wrapping an RFC6902 batch.
 * A raw patch without an envelope is illegal (enforced in store.dispatchEvent).
 * Ledger: in-memory tail here + persisted server-side (event_ledger.jsonl). */

let _seq = 0;
const _ledger = []; // in-memory tail (rebuildable; server file is the record)

function ulid() {
  // monotonic-enough local id: time + seq (deterministic ordering, not crypto)
  return `${Date.now().toString(36)}_${(_seq++).toString(36).padStart(4, '0')}`;
}

/** Deterministic RNG per RUNTIME_AUTHORITY §6: seed derived from
 * (campaign.seed, ledger length). Mulberry32. */
export function derivedSeed(campaign) {
  const base = (campaign?.seed ?? 0) >>> 0;
  return (base ^ ((ledgerLength() + 1) * 0x9e3779b9)) >>> 0;
}
export function seededRng(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Envelope factory. `operations` is an RFC6902 batch against `target`. */
export function makeEnvelope({
  campaign, event_type, authority, target, operations,
  actor_id = 'system', intent_id = null, caused_by = [],
  visibility = 'public', journal_payload = null, rng_seed = null, diagnostics = {},
}) {
  return {
    event_id: `evt_${ulid()}`,
    campaign_id: campaign?.campaign_id ?? null,
    event_type,
    world_phase: campaign?.world_phase ?? 0,
    world_time: new Date().toISOString(),
    actor_id,
    authority,
    intent_id,
    caused_by,
    visibility,
    schema_version: '1.0.0',
    ruleset_version: '1.0.0',
    rng_seed: rng_seed ?? derivedSeed(campaign),
    target,
    operations,
    journal_payload,
    diagnostics,
  };
}

export function ledgerLength() { return _ledger.length; }
export function ledgerTail(n = 20) { return _ledger.slice(-n); }

/** Append an ACCEPTED (or rejection-record) envelope. Fire-and-forget persist
 * to the bridge; the in-memory tail powers the Chaos matcher + journal. */
export function appendLedger(envelope) {
  _ledger.push(envelope);
  persistLedger(envelope);
  return envelope;
}

/** Rejections are ledgered too — the law records its refusals. */
export function ledgerRejection(envelope, reason) {
  const rec = { ...envelope, event_type: `REJECTED:${envelope.event_type}`, diagnostics: { ...envelope.diagnostics, rejected: true, reason } };
  _ledger.push(rec);
  persistLedger(rec);
  return rec;
}

async function persistLedger(envelope) {
  try {
    await fetch('http://localhost:8788/api/v1/ledger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(envelope),
    });
  } catch { /* bridge offline — in-memory tail still serves the session */ }
}

/* dev/QA hook */
if (typeof window !== 'undefined') window.__ledger = { tail: ledgerTail, length: ledgerLength };
