# Independent GM contract conformance

This harness measures synthetic, noncanonical next GM moves. It uses the existing
GM_GUIDE.md and a strict Draft 2020-12 fixture schema. It makes no MCP calls and
cannot claim, roll, publish or write a campaign. Its scorer is independent of the
gateway. A pass is evidence about these fixtures only.

## Reproduce

From the repository root, use a Python environment with the pinned dependency and
an already running local Ollama server. The runner only uses loopback and only
allows the two named installed, local models. It will not download models.

```sh
python -m pip install -r development/gm_provider/conformance/requirements.txt
python -m unittest discover -s development/gm_provider/conformance -v
python development/gm_provider/conformance/harness.py --model qwen2.5:14b --model qwen2.5-coder:32b --mode json --mode schema --repeats 1 --repairs 1 --output results.json
```

Seven independent contexts exercise routine holstering, unknown power, reaction
ownership, NPC motive and provenance, the one allowed roll request, stopping at an
unresolved player choice, and a commit with a binding receipt and hidden fact.
The same inputs and grader can be used with other clients by passing a callable
to run_case, or by validating raw output via score. Feed only the synthetic
context and GM guide to a model. Keep the expect field in the grader.

The benchmark uses temperature 0, seed 22 and an explicit 900-token reply cap.
JSON mode asks for a JSON object, while schema mode enforces the output grammar
in Ollama. Both are graded independently with the same schema and semantic
checks. Each failed first attempt gets at most one repair with error categories
and the original context; no state advance occurs during repair.

Reports contain model digests, fixture input hashes, per-attempt error categories,
wall/load durations, token counts and completion reasons. First-load time is an
Ollama measurement and timings can mix cold and warm calls. The percentile values
describe these calls, not general hardware performance. Repeats support measuring
a larger sample. Narration grading uses targeted regex checks for required and
forbidden facts and is not a substitute for human prose review. This fixture
schema is deliberately strict and is not the authoritative gateway production
schema. A healthy gateway remains mandatory even for a provider that passes.

## Authoritative staging handoff

Acquire actual provider scope, verify the authenticated identity and match
revision, ledger head, public digest, storage health and pending action across
clients before asking for the player's approval. GPT may only process the
existing GPT-routed request after specific approval. Gemini and then a separately
authorized local provider each require a new player-approved action and the
previous published cursor. The local inference runtime has no gateway credentials
or provider identity. An approved broker and separate binding must be designed
and reviewed before any local-model staging write. Compare accepted receipts and
Git ancestry after every approved turn. On timeout consult accepted state first.

## Phase-restricted comparison

Use `--mode phase --repeats 2 --repairs 1` with the same models to reproduce
the intervened benchmark. This mode exposes the move authorized by synthetic
preflight and accepted operation state, then gives the model only that JSON
Schema branch. It fixes the no-roll text for routine fixtures. It still grades
the resulting move using the existing independent checks. These results measure
scaffolded decisions. Use `--mode schema` or `--mode json` to retain free phase selection.

`acceptance.py` checks redacted refresh pairs and accepted receipt equality.
For real tests, use independently observed authenticated tool payloads rather
than model-authored summaries. It does not implement recovery, authenticate
any client, grant permissions or replace the existing authoritative gateway.
