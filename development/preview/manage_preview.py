"""Linux/Codespaces idempotent launcher; never changes Git, forwarding, billing, or campaign data."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def health(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=1) as r:
            h = json.load(r)
        return h if h.get('service') == 'genesis-dev-preview' and h.get('canonical') is False else None
    except (OSError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['start', 'status'])
    ap.add_argument('--port', type=int, default=8080)
    a = ap.parse_args()
    key = hashlib.sha256(str(ROOT).encode()).hexdigest()[:12]
    folder = Path(tempfile.gettempdir()) / f'genesis-preview-{os.getuid()}-{key}-{a.port}'
    folder.mkdir(mode=0o700, exist_ok=True)
    with (folder / 'start.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        h = health(a.port)
        if h and h.get('workspace_id') == key:
            # Refresh static output atomically; don't spawn a duplicate or drop the connection.
            if a.command == 'start':
                subprocess.run([sys.executable, '-B', str(HERE / 'build_preview.py')], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
            print('READY: Genesis fixture preview on port', a.port, '(keep Private).')
            return 0
        if a.command == 'status':
            print('NOT READY: run Tasks: Run Task → Genesis: Start or check private preview.')
            return 1
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1', a.port)) == 0:
                print('REFUSED: port occupied by an unrecognized/legacy server. Inspect it; no process was killed.', file=sys.stderr)
                return 2
        log = folder / 'server.log'
        with log.open('ab') as stream:
            proc = subprocess.Popen([sys.executable, '-B', str(HERE / 'serve_preview.py'), '--host', '0.0.0.0', '--port', str(a.port)],
                                    cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                                    start_new_session=True, close_fds=True)
        (folder / 'pid.json').write_text(json.dumps({'pid': proc.pid}))
        for _ in range(80):
            if health(a.port):
                print('READY: Genesis fixture preview on port', a.port, '(keep Private).')
                return 0
            if proc.poll() is not None:
                break
            time.sleep(.1)
        print('FAILED: preview did not become healthy. Inspect', log, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
