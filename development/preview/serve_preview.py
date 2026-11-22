"""Serve only the existing noncanonical preview output; Codespaces must keep 8080 private."""
import argparse
import http.server
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

import build_preview
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'combat_slice'))
import atomic_service  # sandbox dice authority for /combat.html (noncanonical; journals under combat_slice/out/atomic)

ATOMIC = None

TYPES = {'.html': 'text/html; charset=utf-8', '.json': 'application/json; charset=utf-8',
         '.webmanifest': 'application/manifest+json; charset=utf-8', '.svg': 'image/svg+xml'}
ROUTES = {'/': 'index.html', '/index.html': 'index.html', '/diagnostics.html': 'diagnostics.html', '/combat.html': 'combat.html', '/play.html': 'play.html',
          '/build.json': 'build.json', '/manifest.webmanifest': 'manifest.webmanifest', '/icon.svg': 'icon.svg'}


def handler_for(directory):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Never log paths/query strings: private-port redirects can contain auth parameters.
            pass

        def do_HEAD(self):
            self.respond(False)

        def do_GET(self):
            self.respond(True)

        def do_POST(self):
            path = urlsplit(self.path).path
            if not path.startswith('/atomic/'):
                return self._json(404, {'error': 'NO_ROUTE'})
            # JSON only: a cross-site page can't send application/json without a CORS preflight, which this server never grants.
            if (self.headers.get('Content-Type') or '').split(';')[0].strip().lower() != 'application/json':
                return self._json(415, {'error': 'JSON_ONLY'})
            try:
                n = int(self.headers.get('Content-Length') or 0)
                if n > 65536:
                    return self._json(413, {'error': 'TOO_LARGE'})
                body = json.loads(self.rfile.read(n) or b'{}')
            except (ValueError, OSError):
                return self._json(400, {'error': 'BAD_JSON'})
            status, data = atomic_service.handle(ATOMIC, path, body)
            self._json(status, data)

        def _json(self, status, obj):
            data = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header('Content-Type', TYPES['.json'])
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)

        def respond(self, body):
            path = urlsplit(self.path).path
            status, ct = 200, TYPES['.html']
            if path == '/healthz':
                meta = json.loads((directory / 'build.json').read_text())
                wid = hashlib.sha256(str(build_preview.ROOT).encode()).hexdigest()[:12]
                data = json.dumps({'service': 'genesis-dev-preview', 'workspace_id': wid, 'canonical': False, **meta}).encode()
                ct = TYPES['.json']
            elif path in ROUTES:
                file = directory / ROUTES[path]
                try:
                    data = file.read_bytes()
                    if not data:
                        raise OSError('empty output')
                    ct = TYPES[file.suffix]
                except OSError:
                    status, data = 503, b'<!doctype html><title>Preview unavailable</title><p>Preview build missing. Run the Genesis preview task.</p>'
            else:
                status, data = 404, b'<!doctype html><title>Not found</title><p>No preview route here. <a href="/">Open Genesis</a></p>'
            self.send_response(status)
            self.send_header('Content-Type', ct)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Content-Disposition', 'inline')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            if body:
                self.wfile.write(data)
    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--host', default='127.0.0.1')
    a = ap.parse_args()
    global ATOMIC
    ATOMIC = atomic_service.AtomicDice(engine=atomic_service.EngineWorker(), require_tokens=True)
    page = build_preview.build()
    srv = http.server.ThreadingHTTPServer((a.host, a.port), handler_for(Path(page).parent))
    print(f'Genesis dev preview: http://{a.host}:{srv.server_port}/ (fixture only; keep forwarding private)', flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
