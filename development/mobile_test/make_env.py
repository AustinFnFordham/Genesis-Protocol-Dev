#!/usr/bin/env python3
"""Create the shared, noncanonical mobile test environment from the deterministic fixture and push it.

  python3 -B development/mobile_test/make_env.py --code-commit SHA [--artifact-url URL --trigger-id ID]

Run once, on branch staging/mobile-test (a branch off the integration code commit that only ever receives this
environment's data). Refuses to reuse an existing environment. `set` later fills in the Artifact URL and the worker.
  python3 -B development/mobile_test/make_env.py set --artifact-url URL --trigger-id ID
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "development/gm_provider"))
import staging   # noqa: E402

SCOPE = ROOT / "staging/mobile-test-1"
CAMPAIGN_ID = "mobile-test-1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", nargs="?", default="create", choices=["create", "set"])
    parser.add_argument("--code-commit")
    parser.add_argument("--artifact-url")
    parser.add_argument("--trigger-id")
    a = parser.parse_args()
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, text=True).strip()
    if branch != "staging/mobile-test":
        parser.exit(2, f"run this on branch staging/mobile-test (now on {branch})\n")
    if a.mode == "create":
        subprocess.run([sys.executable, "-B", str(HERE / "build_fixture.py")], check=True, capture_output=True)
        gateway = staging.make_shared(SCOPE, CAMPAIGN_ID, experimental=True, source=HERE / "fixture_campaign",
                                      note="Noncanonical mobile test drill. Isolated copy of a deterministic fixture. Not a canonical campaign. Safe to delete.")
        gateway.select_provider("claude-session", by="operator")
    path = SCOPE / "environment.json"
    env = json.loads(path.read_text())
    if a.code_commit:
        env["code_commit"] = a.code_commit
    if a.artifact_url:
        env["artifact_url"] = a.artifact_url
    if a.trigger_id:
        env["worker"] = {"server": "Claude Code Remote", "tool": "fire_trigger", "trigger_id": a.trigger_id,
                         "runbook": "development/mobile_test/WORKER.md", "branch": "staging/mobile-test"}
    env["test_settings"] = {"wick": "allied_npc, GM-driven, own turn and budget", "enemies": "separate per-creature budgets, shared initiative count",
                            "dice": "Regular/Heroic/Legendary and Narrative Consequences per submission, player character's own d20s only",
                            "adopted_into_live": False}
    path.write_text(json.dumps(env, indent=1))
    staging.open_shared(SCOPE, min_sync_s=0).store.checkpoint("environment settings")
    print(json.dumps(env, indent=1))


if __name__ == "__main__":
    main()
