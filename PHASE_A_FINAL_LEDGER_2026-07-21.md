# PHASE A FINAL LEDGER + RETURNING-DEVELOPER DELIVERY (2026-07-21)

## Phase A acceptance (rendered, executed — not inferred)
```yaml
phase_a_acceptance:
  static_build: pass
  live_api: pass            # :8788, projections verified pre-run
  live_frontend: pass       # :1420
  operative_containment: pass
  engagement_containment: pass
  command_record_containment: pass
  modal_containment: pass
  suggestion_drafts_without_submit: pass   # executed: composer changes, no request
  transcript_autofollow: pass
  new_messages_behavior: pass
  stale_response_rejection: pass           # mount_epoch guard (C-phase, re-asserted)
  campaign_switch_isolation: pass          # meridian→shadows→meridian in-suite
  meridian_return_isolation: pass
  console_errors: 0
  error_boundaries: 0
  fixture_hits: 0           # negatives asserted: Guardian, Millennium Falcon, Sith Assassin,
                            # Malice, Coruscant, Mustafar, Falleen, Sandbox, Operator-as-class
  duplicate_submissions: 0
  screenshots_captured: true  # meridian main/DNA(Planned: Sentry)/ship/suggestions, shadows main/DNA, return
  trace_captured: true        # 2 traces + videos + HTML report (app/genesis-os/playwright-report)
  gate_status: GATE_PASS
```
**Test repair note:** one spec defect fixed (strict-mode violation — 'Aeleron' legitimately renders in 4 places; assertions now use `.first()`). No app changes were needed; the projection architecture was already correct.
**Caveat kept honest:** K token standardization is complete on all primary gameplay surfaces (+ DiceFeed tokenized); legacy/orphaned views (GmSession, LivingDiorama, TacticalRuntime pre-projection variants) retain hardcoded sizes — they are not part of the gated surface.

## Runtime verification (Step 1)
Meridian: Aeleron "Aero" Do'ordo · Echani · Sentinel · Republic Shuttle (Consular-class tender). Shadows: Aran Voss · Human · CLASS-UNRESOLVED · The Reconciliator (YT-2400). Resume checkpoint at `_readiness_checkpoint_20260720/resume_checkpoint.yml` (no git repo — recorded, unchanged; recommend initializing one).

## C.6 surgical correction — Operative
The catch-up correction is confirmed: **Operative is a real PHB base class** (p.107-109; Han Solo build example corroborates d8/8+CON). Extracted and normalized into `registry/golden_slice/global_definitions/class_operative.yml` — full progression table (Expertise/Sneak Attack → Stroke of Luck), d8, light armor, DEX/INT saves, any-four skills, exploits/practice subclass structure, provenance to exact source offsets + corroborating feat/subclass files. **Aran remains class_id: null** — `aran_class_review.yml` finds high conceptual intent (Han-Solo-pattern, DEX 18, HP 45 within L5 Operative range) but material feature conflict (none of the L5 kit present; his three features are AI-authored campaign-local). Owner confirmation required before migration; no inference performed.

## Source-corpus registry (delivered)
`registry/build_corpus_registry.py` → `corpus_registry.sqlite` + all 8 required exports.
```yaml
registry_build: de78ad1a30d9c0f2   # identical across two runs — deterministic
files_recorded: 4403               # all roots, original paths preserved, nothing moved
entity_candidates: 11824
canonical: 57                      # golden_slice lane ONLY — zero auto-promotion
exact_duplicate_groups: 320
duplicate_urids_reported: 2456     # matches the known cross-tree duplication problem
parse_failures_reported: 51        # reported, not skipped
operative_discovery: 154 candidates / 14 files  # acceptance query passes
```
Duplicates classified, not deleted. Canonical runtime continues loading approved lanes only. Forge and the content pipeline can now query bounded candidate sets instead of re-crawling directories.

## Remaining for owner
1. Aran class ruling (aran_class_review.yml).
2. Chaos 14-rule disposition (CHAOS_AUDIT_OWNER_REVIEW.md) + other open gates.
3. Recommend: `git init` E:\StarWars — the project deserves version control.
