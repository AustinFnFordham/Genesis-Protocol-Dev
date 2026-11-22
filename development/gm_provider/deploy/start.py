"""Render entrypoint: preserve an existing worktree, never reset it on boot."""
import json
import os
from pathlib import Path
import subprocess
import sys

REPOSITORY = 'https://github.com/AustinFnFordham/Genesis-Protocol-Dev.git'
BRANCH = 'staging/provider-shared'
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from git_errors import GitFailure, diagnostic
from worktree_guard import WorktreeGuard


def git(args, cwd, env):
    result = subprocess.run(['git', *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise GitFailure(diagnostic(args[0], result.returncode, result.stderr, result.stdout))
    return result.stdout.strip()


def prepare(data_root, env=None, repository=REPOSITORY, branch=BRANCH,
            scope_relative='staging/shared-1', campaign_id='shared-1', *, initialize_storage=True):
    env = dict(os.environ if env is None else env)
    root = Path(data_root); root.mkdir(parents=True, exist_ok=True)
    repo = root / 'authority'
    env.update(GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never')
    if not repo.exists():
        if not initialize_storage:
            raise ValueError("Existing authority checkout required for write opt-in")
        # Clone only into a missing directory. Never overwrite an old checkout.
        git(['clone','--quiet','--single-branch','--branch',branch,repository,str(repo)], root, env)
    with WorktreeGuard(repo / '.git/genesis-operation.lock', initialize=initialize_storage):
        if git(['rev-parse','--abbrev-ref','HEAD'],repo,env) != branch:
            raise ValueError('Authority checkout branch does not match staging')
        if git(['remote','get-url','origin'],repo,env) != repository:
            raise ValueError('Authority origin does not match the approved repository')
        if git(['status','--porcelain'],repo,env):
            raise ValueError('Uncommitted work preserved: operator recovery required; no reset performed')
        git(['fetch','--quiet','origin',branch],repo,env)
        if git(['rev-list','--count',f'origin/{branch}..HEAD'],repo,env) != '0':
            raise ValueError('Unconfirmed local commits preserved: operator reconciliation required')
        git(['merge','--ff-only','--quiet',f'origin/{branch}'],repo,env)
        scope = repo / scope_relative
        state = json.loads((scope/'environment.json').read_text())
        if state.get('canonical') is not False or state.get('campaign_id') != campaign_id:
            raise ValueError('Only the existing noncanonical shared-1 scope may be served')
        return scope



def main():
    if os.geteuid() == 0:
        # The mounted Render disk starts root-owned. Application/Git run as uid 10001.
        root = Path(os.environ.get('GENESIS_DATA_ROOT','/var/data'))
        root.mkdir(parents=True, exist_ok=True)
        os.chown(root,10001,10001)
        os.setgroups([])
        os.setgid(10001)
        os.setuid(10001)
    # Helper is a fixed executable; its token is read only by Git via stdin/stdout.
    os.environ.update(GIT_CONFIG_COUNT='2', GIT_CONFIG_KEY_0='credential.helper',
        GIT_CONFIG_VALUE_0='!python3 ' + str(Path(__file__).with_name('git_credential.py')),
        GIT_CONFIG_KEY_1='credential.useHttpPath', GIT_CONFIG_VALUE_1='true')
    if not os.environ.get('GENESIS_MCP_RESOURCE'):
        os.environ['GENESIS_MCP_RESOURCE'] = os.environ['RENDER_EXTERNAL_URL'].rstrip('/') + '/mcp'
    os.environ['GENESIS_MCP_HOST'] = '0.0.0.0'
    os.environ['GENESIS_MCP_PORT'] = os.environ.get('PORT','10000')
    try:
        scope = prepare(os.environ.get('GENESIS_DATA_ROOT','/var/data'))
        from mcp_adapter import build
        server = build(scope)
    except GitFailure as error:
        print(json.dumps(error.as_dict()), file=sys.stderr)
        return 2
    except Exception:
        print('Startup refused: preserve disk and inspect authority/configuration; no reset or cleanup performed',file=sys.stderr)
        return 2
    server.run(transport='streamable-http')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
