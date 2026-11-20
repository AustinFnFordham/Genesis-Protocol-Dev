"""Serve only the existing noncanonical preview output; Codespaces must keep 8080 private."""
import argparse
import http.server
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

import build_preview

TYPES = {'.html': 'text/html; charset=utf-8', '.json': 'application/json; charset=utf-8',
         '.webmanifest': 'application/manifest+json; charset=utf-8', '.svg': 'image/svg+xml'}
ROUTES = {'/': 'index.html', '/index.html': 'index.html', '/diagnostics.html': 'diagnostics.html',
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
    page = build_preview.build()
    srv = http.server.ThreadingHTTPServer((a.host, a.port), handler_for(Path(page).parent))
    print(f'Genesis dev preview: http://{a.host}:{srv.server_port}/ (fixture only; keep forwarding private)', flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
