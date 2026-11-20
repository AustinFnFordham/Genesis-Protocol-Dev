"""Real HTTP and Linux launcher checks against isolated preview output; no campaign writes."""
import concurrent.futures
import hashlib
import http.server
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_preview
from serve_preview import handler_for


class PreviewHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.temp.name)
        build_preview.build(out=cls.out)
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler_for(cls.out))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.temp.cleanup()

    def test_html_get_head_and_local_assets(self):
        for path in ['/', '/index.html', '/diagnostics.html']:
            with urllib.request.urlopen(self.url + path) as r:
                body = r.read()
                self.assertEqual(r.status, 200)
                self.assertIn('text/html', r.headers['Content-Type'])
                self.assertEqual(r.headers['Content-Disposition'], 'inline')
                self.assertEqual(r.headers['Cache-Control'], 'no-store')
                self.assertGreater(len(body), 1000)
                self.assertEqual(int(r.headers['Content-Length']), len(body))
                self.assertIn(b'Genesis', body)
            with urllib.request.urlopen(urllib.request.Request(self.url + path, method='HEAD')) as r:
                self.assertEqual(r.read(), b'')
                self.assertGreater(int(r.headers['Content-Length']), 1000)
        for path, ct in [('/manifest.webmanifest','application/manifest+json'),('/icon.svg','image/svg+xml'),('/build.json','application/json')]:
            with urllib.request.urlopen(self.url + path) as r:
                self.assertIn(ct, r.headers['Content-Type']); self.assertTrue(r.read())
        with urllib.request.urlopen(self.url + '/manifest.webmanifest') as r:
            self.assertEqual(json.load(r)['display'], 'browser')

    def test_health_is_fixture_only(self):
        with urllib.request.urlopen(self.url + '/healthz') as r:
            h = json.load(r)
        self.assertEqual(h['fixture'], 'mobile-test-1')
        self.assertIs(h['canonical'], False)
        self.assertNotIn('hidden', json.dumps(h))

    def test_routes_do_not_expose_checkout_or_directory(self):
        for path in ['/hidden/ledger.jsonl', '/../.git/config', '/.building-test', '/unknown', '/%2e%2e/.git/config']:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(self.url + path)
            self.assertEqual(caught.exception.code, 404)

    def test_rebuild_never_serves_empty_output(self):
        def rebuild():
            for _ in range(4):
                build_preview.build(out=self.out)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            work = pool.submit(rebuild)
            for _ in range(30):
                with urllib.request.urlopen(self.url + '/') as r:
                    b = r.read()
                self.assertTrue(b.startswith(b'<!doctype html>'))
                self.assertTrue(b.endswith(b'</html>'))
            work.result()
        with self.assertRaises(ValueError):
            build_preview.atomic_text(self.out / 'index.html', '')
        self.assertTrue((self.out / 'index.html').stat().st_size)

    def test_missing_build_returns_html_503(self):
        index = self.out / 'index.html'; old = index.read_bytes(); index.unlink()
        try:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(self.url + '/')
            self.assertEqual(caught.exception.code, 503)
            self.assertIn('text/html', caught.exception.headers['Content-Type'])
            self.assertIn(b'Preview build missing', caught.exception.read())
        finally:
            index.write_bytes(old)


@unittest.skipIf(sys.platform == 'win32', 'Launcher runs in Linux Codespaces; Windows is a browser client')
class Launcher(unittest.TestCase):
    def test_parallel_idempotence_restart_and_occupied_port(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); port = sock.getsockname()[1]
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, 'TMPDIR':temp}
            cmd=[sys.executable,'-B',str(HERE / 'manage_preview.py'),'start','--port',str(port)]
            try:
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result=list(pool.map(lambda _:subprocess.run(cmd,env=env,capture_output=True,text=True),range(4)))
                self.assertTrue(all(r.returncode==0 for r in result),result)
                logs=list(Path(temp).glob('genesis-preview-*/server.log'))
                self.assertEqual(len(logs),1)
                self.assertEqual(logs[0].read_text().count('Genesis dev preview:'),1)
                pidfile=logs[0].with_name('pid.json'); pid=json.loads(pidfile.read_text())['pid']
                os.kill(pid,signal.SIGTERM)
                for _ in range(40):
                    import time
                    time.sleep(.05)
                    try: urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz',timeout=.2)
                    except OSError: break
                result=subprocess.run(cmd,env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz') as r: self.assertEqual(json.load(r)['service'],'genesis-dev-preview')
            finally:
                for p in Path(temp).glob('genesis-preview-*/pid.json'):
                    try: os.kill(json.loads(p.read_text())['pid'],signal.SIGTERM)
                    except ProcessLookupError: pass
        occupied=http.server.ThreadingHTTPServer(('127.0.0.1',0),http.server.SimpleHTTPRequestHandler)
        worker=threading.Thread(target=occupied.serve_forever,daemon=True); worker.start()
        try:
            r=subprocess.run([*cmd[:-1],str(occupied.server_port)],capture_output=True,text=True)
            self.assertEqual(r.returncode,2); self.assertIn('no process was killed',r.stderr)
        finally: occupied.shutdown(); occupied.server_close(); worker.join()


if __name__=='__main__': unittest.main()
