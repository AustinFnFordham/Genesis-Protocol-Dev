# GENESIS PROTOCOL — LIVE UI ACCEPTANCE TESTS

Run against the REAL application (vite dev :1420 + api_bridge :8788) with
tokenized campaign fixtures. Use exact identifiers — never substring matching
(`Ilo` must not match `pilot`). Implement as Playwright specs under
`app/genesis-os/e2e/`.

## Gate requirements (GATE_PASS forbidden unless ALL are true)
```yaml
gate_requirements:
  static_build: pass
  integration_tests: pass
  live_runtime_started: pass
  rendered_ui_test: pass
  persistence_restart_test: pass
  console_errors: 0
  error_boundary_activations: 0
  cross_campaign_leaks: 0
  cross_character_leaks: 0
  fixture_fallbacks_detected: 0
```

## T1 — Campaign coherence (every panel one campaign)
```
mount Meridian Reach
  assert data-campaign-id == "meridian_reach" on EVERY region:
    campaign-header, operative, party, equipment, active-engagement,
    cinematic-feed, command-record  (and data-mount-epoch/data-state-revision equal)
  assert Map = only Meridian-established nodes OR "No mapped campaign locations…"
  assert Nemesis = only player-visible Meridian data OR "No known nemesis information"
  assert Ship = only Meridian-registered ship OR "No ship registered to this campaign"
  assert NO Coruscant/Mustafar/Falleen, NO Millennium Falcon, NO Sandbox Entity
switch to Shadows of Empire
  assert every region data-campaign-id == "shadows_of_empire" atomically
  assert zero Meridian location/character/journal/transcript/nemesis/ship remain
switch back to Meridian
  assert exact Meridian state returns; zero Shadows remnants
```

## T2 — Character coherence (every character panel one character)
```
fixtures: char_aero (Echani/Sentinel/Sentry L1), char_aran (Human/Guardian L5)
select Aero  -> Operative=Aero, equipment=Aero's, DNA Record=Sentinel/Sentry progression
             -> assert NO Aran, NO Guardian-only nodes, NO Sandbox Entity
             -> assert data-character-id == char_aero on operative + DNA Record + party row
select Aran  -> Operative=Aran, DNA Record=Guardian; assert NO Aero/Sentry content
switch repeatedly -> panels change atomically, no stale character data
```

## T3 — Name serialization
```
assert Operative name renders exactly:  Aeleron "Aero" Do'ordo
assert NO "\x27" anywhere in DOM or /gm/state payload
round-trip: save -> GET /gm/state -> reload app -> still Do'ordo
```

## T4 — Crawl lifecycle (no remount from unrelated actions)
```
enter live scene (opening acknowledged -> collapsed)
click a weapon  -> ONLY inventory-selection state changes
                -> crawl stays collapsed, transcript scroll position stable,
                   Active Engagement NOT remounted, runtime NOT reloaded
open a modal / change a side tab -> crawl stays collapsed
click "View Opening Crawl" -> expands; close -> collapses
restart from opening -> crawl active again, old transcript/journal gone (backed up)
```

## T5 — Narrative scroll ownership
```
at bottom + new GM message -> auto-follows
scrolled up + new message  -> position preserved + "New messages ↓" appears
composer remains visible/usable throughout
```

## T6 — Suggestions
```
4 suggestions render as 2x2 grid (or 4-col wide), each: intent label + response + 1 context line
click suggestion -> populates composer; NOTHING transmits until explicit submit
[Regenerate Suggestions] and [Hide Suggestions] present
reject candidates: generic / repeat-of-taken-action / stale-context / illegal / off-voice / hidden-info-dependent
```

## T7 — Narrative consistency regressions (from observed defects)
```yaml
narrative_consistency:
  speaker_identity_valid: true
  pronouns_match_character_profile: true    # Ilo must not change pronouns across turns
  no_duplicate_utterance: true              # a player line must not reappear as Besk's dialogue
  no_duplicate_completed_action: true       # handshake narrated once
  response_targets_latest_turn: true
  scene_location_consistent: true
  visible_knowledge_only: true
```

## T8 — Persistence across restart
```
close app -> reopen -> both campaigns restore independently, correct state each
```

## Instrumentation the app must expose
- data-campaign-id, data-mount-epoch, data-state-revision on every region
- data-character-id on character-facing regions
- window.__genesis store snapshot for assertions
- console error listener asserting 0 errors / 0 error-boundary MODULE FAULT
