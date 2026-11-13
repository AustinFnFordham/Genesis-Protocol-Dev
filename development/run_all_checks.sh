#!/bin/bash
# Full local verification for the provider-interchange candidate. Writes development/.qa/check_results.json.
# No network, no Artifact database, no campaign source writes. Usage: bash development/run_all_checks.sh
cd "$(dirname "$0")/.." || exit 2
export PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/development/.qa/tmp"
mkdir -p "$TMPDIR"
python3 -B development/prepare_browser_fixtures.py >/dev/null || exit 2
U=campaigns/starwars_litrpg/ui; P=$U/genesis_datapad.html; Q=development/.qa
results=(); fail=0
record(){ results+=("{\"suite\":\"$1\",\"passed\":$2,\"elapsed_ms\":$3}"); [ "$2" = true ] || { fail=$((fail+1)); echo "FAIL $1"; tail -8 "$Q/last.out"; }; }
timed(){ name=$1; shift; s=$(date +%s%3N); if timeout 900 "$@" >"$Q/last.out" 2>&1; then ok=true; else ok=false; fi; record "$name" $ok $(( $(date +%s%3N)-s )); }
for t in $(git ls-files -co --exclude-standard | grep -E '(^|/)test_[a-z_]+\.py$' | grep -E '^\.claude|^campaigns/starwars_litrpg|^development' | sort); do timed "$t" python3 -B "$t"; done
timed "$U/test_datapad_ui.cjs" node $U/test_datapad_ui.cjs $P $Q/state_round1.json $Q/shots
timed "$U/test_datapad_sequencer_ui.cjs" node $U/test_datapad_sequencer_ui.cjs $P $Q/state_hask.json $Q/shots
timed "$U/test_datapad_scene_ui.cjs" node $U/test_datapad_scene_ui.cjs $P $Q/state_hask.json $Q/shots
timed "$U/test_datapad_iphone.cjs" node $U/test_datapad_iphone.cjs $P $Q/state_hask.json $Q/shots
timed "$U/test_datapad_history.cjs" node $U/test_datapad_history.cjs $P $Q/ui
timed "$U/test_datapad_review_options.cjs" node $U/test_datapad_review_options.cjs $P $U/fixtures/needs_revision/state.json $U/fixtures/needs_revision/actions
timed "development/test_player_experience.cjs" node development/test_player_experience.cjs
timed "development/test_dice_history_ui.cjs" node development/test_dice_history_ui.cjs $P $Q/dice_ui
timed "development/experimental_resolution/test_controls.cjs" node development/experimental_resolution/test_controls.cjs
timed "rng_audit hask_meadow_r2" python3 -B .claude/skills/litrpg-dice/audit_rng.py campaigns/starwars_litrpg/runs/hask_meadow_r2
timed "rng_audit sandbox" python3 -B .claude/skills/litrpg-dice/audit_rng.py campaigns/starwars_litrpg/runs/sandbox
timed "page is the built page" bash -c "python3 $U/build_datapad.py --out $Q/rebuilt.html >/dev/null && cmp $Q/rebuilt.html $P"
( IFS=,; echo "{\"commit\":\"$(git rev-parse --short HEAD)\",\"dirty\":$( [ -n "$(git status --porcelain)" ] && echo true || echo false ),\"failed\":$fail,\"suites\":[${results[*]}]}" ) > "$Q/check_results.json"
echo "suites=${#results[@]} failed=$fail"
exit $fail
