# Verification record

The JSON files in verification/ contain aggregate diagnostics from the isolated
checkout. They contain no hidden campaign prose or dice seed.

- RNG audit replayed 225/225 records through an independent JavaScript generator.
- Synthetic sample of 100,000 d20 faces averaged 10.50343. This diagnostic does
  not prove cryptographic unpredictability or future fairness.
- Compact brief benchmark uses five local full replays. See the JSON for measured
  milliseconds and UTF-8 bytes. Token usage and live GM latency are unmeasured.
- Regression suites cover existing roller parity, modifiers, advantage, stream
  replay, altered totals, public dice redaction/history, publication budgets and
  retry ordering, validator/sequencer compatibility, brief field provenance,
  checkpoint tampering and public/GM separation.
- Browser test loads the new history through the existing database mock and
  checks player-visible text on a phone-sized viewport.
- Protected paths and deterministic implementations are compared to the starting
  commit with git diff. No live database or Artifact tools are invoked.

Measured at the verified baseline ledger head evt_0874, with 874 shared ledger
events and public projection revision 705. Public history contains 169 visible
rolls. The bounded snapshot is 95,920 bytes; the dice page is 37,597 bytes.
All pages are within their configured budgets.

The final aggregate run passed 11 Python regression scripts and one mobile
Chromium test. The brief verifier checked all 874 heads, found zero replay
mismatches and zero player leaks, and rejected hidden history retrieval.
