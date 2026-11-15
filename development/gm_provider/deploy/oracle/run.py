"""Oracle pilot launcher. Existing adapter, authority and recovery are unchanged."""
import os,sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(HERE),str(HERE.parent)]
from start import prepare
from git_errors import GitFailure

def configure(env):
    if env.get('GENESIS_MCP_ENABLE_WRITES','0')!='0':raise ValueError('Pilot is read-only')
    if not Path('/var/data').is_mount():raise ValueError('Persistent volume must be mounted')
    from urllib.parse import urlsplit
    u=urlsplit(env['GENESIS_MCP_RESOURCE'])
    if u.scheme!='https' or not (u.hostname or '').endswith('.duckdns.org') or u.path!='/mcp' or u.port or u.username or u.password or u.query or u.fragment:raise ValueError('Use the registered DuckDNS HTTPS resource')
    env.update(GENESIS_MCP_ENABLE_WRITES='0',GENESIS_MCP_HOST='127.0.0.1',GENESIS_MCP_PORT='8789',GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never',GIT_CONFIG_COUNT='2',GIT_CONFIG_KEY_0='credential.helper',GIT_CONFIG_VALUE_0='!python3 '+str(HERE/'git_credential.py'),GIT_CONFIG_KEY_1='credential.useHttpPath',GIT_CONFIG_VALUE_1='true')

def main():
    os.umask(0o077)
    try:
        configure(os.environ)
        scope=prepare('/var/data')
        from mcp_adapter import build
        server=build(scope)
    except GitFailure as e:print(json.dumps(e.as_dict()),file=sys.stderr);return 2
    except Exception:print('Startup refused: check mounted volume and protected configuration; no reset performed',file=sys.stderr);return 2
    server.run(transport='streamable-http');return 0
if __name__=='__main__':raise SystemExit(main())
