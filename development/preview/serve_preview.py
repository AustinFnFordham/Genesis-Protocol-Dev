"""Build and serve the development preview. Private by default: Codespaces forwards the port privately.
python3 development/preview/serve_preview.py [--port 8080] [--host 0.0.0.0]"""
import argparse
import functools
import http.server
from pathlib import Path

import build_preview

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8080)
ap.add_argument("--host", default="127.0.0.1")
a = ap.parse_args()
page = build_preview.build()
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(Path(page).parent))
print(f"Genesis dev preview: http://{a.host}:{a.port}/  (built {page})", flush=True)
http.server.ThreadingHTTPServer((a.host, a.port), handler).serve_forever()
