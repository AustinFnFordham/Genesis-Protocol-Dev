# Consolidated implementation status

Continued from 7ac860a4dce5e75777ab808f1b2c97ff8cbe3f66 on
dev/dice-history-gm-brief-cc9cfc5. The restored acceptance criteria supersede the
earlier missing-prompt limitation. Implementation and tests are isolated. Nothing
in this increment is deployed to the live Claude worker, database or Artifact.

| Increment | Implemented and tested in development | Remaining or untested |
| --- | --- | --- |
| Readiness | 84KB snapshot target, 96KB ceiling, complete paginated history; future original/alternate/selected advantage faces with unchanged draw stream | Native Windows execution and live publication |
| A. Ledger batch | Ordered drafts, generated IDs, earlier-batch causal references, worker lease and expected head/revision, durable acceptance journal, read barrier, exact byte recovery and receipts | Remote lease CAS workflow and hostile writers bypassing the ledger API are not certified |
| B. Processing | Worker-authored stage patch generator, actual timestamps, elapsed and stage duration, stalled worker/retry/publication states, expandable timings near builder and Journal | Requires worker execution of the updated runbook; no live worker/database phase updates exercised |
| C. Scene / Journal | Latest GM narration in Scene; paginated Previous Turns, extractive five-turn Chapters, Events, Objectives, Performance; void-driven rebuilds | Chapters are deterministic excerpts, not model-authored summaries. Real iOS Safari untested |
| D. Contest / repair | Separate dispute request UI; intent/rules/unfavorable categories; declaration and step provenance; dependency closure; explicit adjudication; append-only void/replacement batch using prior rolls | Applying repairs is limited to marked sandbox copies. Legacy missing provenance and broader later-turn dependency issues require GM mapping |
| Relationships | Public observations and six separate evidence dimensions; 176 sourced interaction records at baseline; no hidden-intent inference or recruitment promise | Current ledger has no explicit typed dimension evidence. Psychological ratings and recruitment logic are not implemented |
| SID Q15/Q16 | Provisional decisions and unique ownership boundaries documented | No runtime certification or canonical promotion |
| Campaign Genesis | Isolated CLI accepts era, preferences, worldbuilding choices, canonical endpoints, conditional Chaos templates; validates resolution and connectivity | No playable chronology/card-deck engine, automatic lore certification or canonical promotion |
| Before the Fall | Original user document recovered and fingerprinted, original mechanics preserved as source reference; optional mode binds an unchanged rules file | Card-outcome deck is absent from the source document; chronology execution is not certified |
| Provider interoperability | Two independent client processes read and refresh the same public revision; revision fingerprints and proposed adjudication/commit boundary documented | No Claude/ChatGPT/Gemini adjudication interchangeability claim; external provider and remote commit adapters remain untested |

Read CONSOLIDATED_IMPLEMENTATION.md for measurements, test commands, file mapping
and commit references. Verification JSON contains aggregate data, not hidden
campaign prose or the campaign dice seed.
