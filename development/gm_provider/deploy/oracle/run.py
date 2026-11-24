"""Launch the existing shared staging adapter on the persistent Oracle volume."""
import argparse
import json
import os
from pathlib import Path
import shlex
import sys
from urllib.parse import urlsplit
import uuid

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE), str(HERE.parent)]
from start import BRANCH, REPOSITORY, git, prepare
from git_errors import GitFailure
from worktree_guard import WorktreeGuard

DATA_ROOT = Path("/var/data")
CAMPAIGN_ID = "shared-1"
PROVIDERS = {"gpt-session", "gemini-session", "codex-session"}  # codex-session is opt-in, never impersonates GPT/Gemini


def configure(env):
    mode = env.get("GENESIS_MCP_ENABLE_WRITES", "0")
    if mode not in {"0", "1"}:
        raise ValueError("GENESIS_MCP_ENABLE_WRITES must be 0 or 1")
    if not DATA_ROOT.is_mount():
        raise ValueError("Persistent volume must be mounted")
    resource = urlsplit(env["GENESIS_MCP_RESOURCE"])
    if (resource.scheme != "https" or not (resource.hostname or "").endswith(".duckdns.org")
            or resource.path != "/mcp" or resource.port or resource.username or resource.password
            or resource.query or resource.fragment):
        raise ValueError("Use the registered DuckDNS HTTPS resource")
    if mode == "1":
        validate_write_config(env)
    helper = "!" + shlex.join([sys.executable, str(HERE / "git_credential.py")])
    env.update(
        GENESIS_MCP_ENABLE_WRITES=mode, GENESIS_MCP_HOST="127.0.0.1", GENESIS_MCP_PORT="8789",
        GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never", GIT_CONFIG_COUNT="3",
        GIT_CONFIG_KEY_0="credential.helper", GIT_CONFIG_VALUE_0="",
        GIT_CONFIG_KEY_1="credential.helper", GIT_CONFIG_VALUE_1=helper,
        GIT_CONFIG_KEY_2="credential.useHttpPath", GIT_CONFIG_VALUE_2="true",
    )
    return mode == "1"


def validate_write_config(env):
    generation = env.get("GENESIS_STORAGE_GENERATION", "")
    try:
        if str(uuid.UUID(generation)) != generation:
            raise ValueError
    except ValueError:
        raise ValueError("A verified storage generation is required") from None
    token = env.get("GENESIS_GITHUB_TOKEN", "")
    if not token or any(c.isspace() for c in token):
        raise ValueError("A server-held GitHub credential is required")
    try:
        tokens = json.loads(env.get("GENESIS_GM_TOKENS", ""))
    except ValueError:
        raise ValueError("Server-held GM tokens must be a JSON object") from None
    if (not isinstance(tokens, dict) or not tokens or not tokens.keys() <= PROVIDERS
            or any(not isinstance(value, str) or not value or any(c.isspace() for c in value)
                   for value in tokens.values())
            or len(set(tokens.values())) != len(tokens)):
        raise ValueError("Provide distinct server-held GM tokens for the enabled providers")


def verify_write_startup(repo, env):
    # Same repository-scoped helper and service identity as GitStore. Use a
    # unique diagnostic ref and dry-run so no remote state is updated.
    ref = f"refs/heads/ops/oracle-gm-check-{uuid.uuid4().hex}"
    with WorktreeGuard(repo / ".git/genesis-operation.lock", env["GENESIS_STORAGE_GENERATION"],
                       initialize=False) as guard:
        if guard.recovery_required:
            return guard.recovery_reason
        git(["push", "--dry-run", "--porcelain", "origin", f"HEAD:{ref}"], repo, env)
    return None


def existing_authority(repo, env):
    """Validate local authority while holding its existing operation lock."""
    import staging

    if not (repo / ".git").is_dir():
        raise ValueError("Existing authority checkout required")
    guard = WorktreeGuard(repo / ".git/genesis-operation.lock",
                          env.get("GENESIS_STORAGE_GENERATION"),
                          initialize=False, require_lock=True)
    readonly_git = dict(env, GIT_OPTIONAL_LOCKS="0")
    with guard:
        if guard.recovery_required:
            return None, guard.recovery_reason
        if git(["symbolic-ref", "--short", "HEAD"], repo, readonly_git) != BRANCH:
            raise ValueError("Unexpected authority branch")
        if git(["remote", "get-url", "origin"], repo, readonly_git) != REPOSITORY:
            raise ValueError("Unexpected authority origin")
        if git(["status", "--porcelain", "--untracked-files=all"], repo, readonly_git):
            raise ValueError("Authority checkout is dirty")
        head = git(["rev-parse", "HEAD"], repo, readonly_git)
        upstream = git(["rev-parse", "--verify", f"refs/remotes/origin/{BRANCH}"], repo, readonly_git)
        if head != upstream:
            raise ValueError("Authority needs explicit reconciliation")
        scope = repo / "staging" / CAMPAIGN_ID
        gateway = staging.open_shared(scope)
        if gateway.id != CAMPAIGN_ID or gateway.store.repo != repo.resolve():
            raise ValueError("Unexpected campaign authority")
        with gateway.store.local_snapshot():
            if gateway.recovery()["record_mid_write"]:
                return None, "record_mid_write"
        return scope, None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_mutually_exclusive_group()
    operations.add_argument("--check", action="store_true", help="Validate existing authority without serving")
    operations.add_argument("--reconcile", action="store_true",
                            help="Explicitly prepare and synchronize authority without serving")
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        write_requested = configure(os.environ)
        repo = DATA_ROOT / "authority"
        if args.reconcile:
            if write_requested:
                recovery = verify_storage(repo, os.environ, require_lock=True)
                if recovery:
                    return storage_blocked(recovery)
            prepare(DATA_ROOT, initialize_storage=not write_requested)
            if write_requested:
                recovery = verify_write_startup(repo, os.environ)
                if recovery:
                    return storage_blocked(recovery)
            print("Authority reconciliation completed.")
            return 0
        scope, recovery = existing_authority(repo, os.environ)
        if recovery:
            return storage_blocked(recovery)
        from mcp_adapter import build
        server = build(scope, local_reads=True)
    except GitFailure as error:
        print(json.dumps(error.as_dict()), file=sys.stderr)
        return 2
    except Exception:
        print("Startup refused: check mounted volume, clean authority and protected configuration",
              file=sys.stderr)
        return 2
    if args.check:
        print("Existing authority and configuration checked.")
        return 0
    server.run(transport="streamable-http")
    return 0


def verify_storage(repo, env, *, require_lock=False):
    with WorktreeGuard(repo / ".git/genesis-operation.lock", env["GENESIS_STORAGE_GENERATION"],
                       initialize=False, require_lock=require_lock) as guard:
        return guard.recovery_reason


def storage_blocked(reason):
    print(json.dumps({"error": {"code": "STORAGE_RECOVERY_REQUIRED", "reason": reason}}),
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
