"""Player API, worker and model-adapter wire tests.

The three model adapters (Anthropic, OpenAI, Google) run their real HTTP code against a LOCAL
FAKE model server that speaks each vendor's request/response shape and answers with the scripted
GM from test_gateway. This verifies request shaping, credential headers, response parsing and the
privacy boundary of the player API. It is NOT a call to Claude, GPT or Gemini.
Run: python3 -B development/gm_provider/test_service.py
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import providers as provider_module   # noqa: E402
import service                        # noqa: E402
import staging                        # noqa: E402
from test_gateway import script, QA, INSPECT, HOLSTER, fingerprints   # noqa: E402

KEYS = {"claude": "sk-ant-test-CLAUDEKEY", "gpt": "sk-test-GPTKEY", "gemini": "test-GEMINIKEY"}


class FakeModels:
    """One local server impersonating the three vendors' completion endpoints."""
    def __init__(self):
        self.calls, self.fail = [], {}
        outer = self
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["content-length"])))
                headers = {k.lower(): v for k, v in self.headers.items()}
                if self.path == "/v1/messages":
                    name, ok = "claude", headers.get("x-api-key") == KEYS["claude"] and headers.get("anthropic-version")
                    system, user = body["system"], body["messages"][0]["content"]
                    wrap = lambda text: {"content": [{"type": "text", "text": text}]}
                elif self.path == "/v1/chat/completions":
                    name, ok = "gpt", headers.get("authorization") == "Bearer " + KEYS["gpt"]
                    system, user = body["messages"][0]["content"], body["messages"][1]["content"]
                    wrap = lambda text: {"choices": [{"message": {"content": text}}]}
                elif self.path.startswith("/v1beta/models/") and self.path.endswith(":generateContent"):
                    name, ok = "gemini", headers.get("x-goog-api-key") == KEYS["gemini"]
                    system, user = body["systemInstruction"]["parts"][0]["text"], body["contents"][0]["parts"][0]["text"]
                    wrap = lambda text: {"candidates": [{"content": {"parts": [{"text": text}]}}]}
                else:
                    name, ok = None, False
                outer.calls.append({"provider": name, "path": self.path, "model": body.get("model"), "system_has_guide": "Genesis GM guide" in (system if ok else "")})
                if not ok:
                    code, payload = 401, {"error": "bad credential"}
                elif outer.fail.get(name):
                    code, payload = outer.fail[name], {"error": "injected"}
                else:
                    move = script(name).step(json.loads(user))
                    code, payload = 200, wrap("```json\n" + json.dumps(move) + "\n```" if name == "claude" else json.dumps(move))
                data = json.dumps(payload).encode()
                self.send_response(code); self.send_header("content-length", str(len(data))); self.end_headers(); self.wfile.write(data)
            def log_message(self, *args):
                pass
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.protected = fingerprints()
        QA.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="service-", dir=QA)
        self.addCleanup(self.tmp.cleanup)
        self.gw, _ = staging.make(self.tmp.name)
        self.addCleanup(self.gw.store.close)
        self.models = FakeModels()
        self.addCleanup(self.models.server.server_close); self.addCleanup(self.models.server.shutdown)
        self.env = {"ANTHROPIC_API_KEY": KEYS["claude"], "GENESIS_CLAUDE_MODEL": "fake-claude", "GENESIS_CLAUDE_BASE_URL": self.models.url,
                    "OPENAI_API_KEY": KEYS["gpt"], "GENESIS_GPT_MODEL": "fake-gpt", "GENESIS_GPT_BASE_URL": self.models.url,
                    "GEMINI_API_KEY": KEYS["gemini"], "GENESIS_GEMINI_MODEL": "fake-gemini", "GENESIS_GEMINI_BASE_URL": self.models.url}
        self.app = service.App({self.gw.id: self.gw}, provider_module.registry(self.env), "player-secret", origin="https://app.example")
        self.http = ThreadingHTTPServer(("127.0.0.1", 0), service.handler(self.app))
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        self.addCleanup(self.http.server_close); self.addCleanup(self.http.shutdown)
        self.base = f"http://127.0.0.1:{self.http.server_address[1]}"
        self.bodies = []

    def tearDown(self):
        self.assertEqual(fingerprints(), self.protected)

    def call(self, method, path, body=None, token="player-secret"):
        request = urllib.request.Request(self.base + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                         headers={"content-type": "application/json", **({"authorization": "Bearer " + token} if token else {})})
        try:
            with urllib.request.urlopen(request) as response:
                raw, code, headers = response.read().decode(), response.status, response.headers
        except urllib.error.HTTPError as error:
            raw, code, headers = error.read().decode(), error.code, error.headers
        self.bodies.append(raw)
        return code, json.loads(raw), headers

    def declare(self, n, text, provider=None):
        return staging.declare(self.gw, f"http-{n:04d}", text=text, provider=provider)

    def test_player_api_three_providers_and_return(self):
        root = f"/v1/campaigns/{self.gw.id}"
        self.assertEqual(self.call("GET", root + "/state", token=None)[0], 401)
        self.assertEqual(self.call("GET", root + "/state", token="wrong")[0], 401)
        self.assertEqual(self.call("GET", "/v1/campaigns/other/state")[0], 404)
        code, matrix, _ = self.call("GET", "/v1/providers", token=None)
        self.assertEqual([(p["id"], p["available"], p["mock"]) for p in matrix["providers"]],
                         [("claude", True, False), ("gemini", True, False), ("gpt", True, False)])
        code, state, headers = self.call("GET", root + "/state")
        self.assertEqual((code, headers["access-control-allow-origin"], headers["cache-control"]), (200, "https://app.example", "no-store"))
        self.assertEqual(self.call("POST", root + "/actions", self.declare(0, HOLSTER))[1]["error"]["code"], "PROVIDER_NOT_SELECTED")
        self.assertEqual(self.call("POST", root + "/provider", {"provider": "grok"})[1]["error"]["code"], "UNKNOWN_PROVIDER")
        self.assertEqual(self.call("POST", root + "/provider", {"provider": "claude"})[0], 200)
        previous = state["cursor"]
        for n, name in enumerate(["claude", "gpt", "gemini", "claude"], 1):
            action = self.declare(n, HOLSTER if n == 1 else INSPECT, provider=name)
            code, status, _ = self.call("POST", root + "/actions", action)
            self.assertEqual((code, status["status"], status["provider"]), (202, "submitted", name))
            self.assertEqual(self.call("POST", root + "/actions", action)[1]["duplicate"], True)
            results = self.app.work()
            self.assertEqual([(r["outcome"], r["provider"]) for r in results], [("committed", name)], results)
            code, status, _ = self.call("GET", f"{root}/actions/{action['action_id']}")
            self.assertEqual((status["status"], status["stage"]), ("committed", "complete"))
            code, state, _ = self.call("GET", root + "/state")
            self.assertGreater(state["cursor"]["revision"], previous["revision"])
            self.assertTrue(state["state"]["feed"][-1]["text"].startswith(f"[{name}]"))
            self.assertIn(f"Head was {previous['ledger_head']}", state["state"]["feed"][-1]["text"])
            stale = dict(action, action_id=f"late-{n:04d}")
            self.assertEqual(self.call("POST", root + "/actions", stale)[0:1], (409,))
            previous = state["cursor"]
        for page in state["pages"]:
            self.assertEqual(self.call("GET", f"{root}/pages/{page}")[0], 200)
        self.assertEqual(self.call("GET", f"{root}/pages/nope")[0], 404)
        self.assertEqual(sorted({c["provider"] for c in self.models.calls}), ["claude", "gemini", "gpt"])
        self.assertTrue(all(c["system_has_guide"] for c in self.models.calls))
        everything = "\n".join(self.bodies)
        for secret in list(KEYS.values()) + ["CANARY", "private table", "interpretation", "seed", "x-api-key", "recent_private", self.models.url]:
            self.assertNotIn(secret, everything, secret)

    def test_missing_credential_blocks_and_reroute_is_explicit(self):
        root = f"/v1/campaigns/{self.gw.id}"
        env = dict(self.env)
        del env["GEMINI_API_KEY"]
        self.app.providers = provider_module.registry(env)
        matrix = {p["id"]: p for p in self.call("GET", "/v1/providers")[1]["providers"]}
        self.assertEqual((matrix["gemini"]["available"], matrix["gemini"]["reason"]), (False, "missing GEMINI_API_KEY"))
        action = self.declare(1, HOLSTER, provider="gemini")
        self.call("POST", root + "/actions", action)
        self.assertEqual(self.app.work()[0]["outcome"], "blocked")
        self.assertEqual(self.app.work()[0]["outcome"], "blocked")           # still nobody else takes it
        status = self.call("GET", f"{root}/actions/{action['action_id']}")[1]
        self.assertEqual((status["status"], status["blocked"]["code"]), ("submitted", "PROVIDER_UNAVAILABLE"))
        self.assertEqual(self.models.calls, [])
        self.assertEqual(self.call("POST", f"{root}/actions/{action['action_id']}/reroute", {"provider": "gpt"})[1]["provider"], "gpt")
        self.assertEqual([(r["outcome"], r["provider"]) for r in self.app.work()], [("committed", "gpt")])
        self.assertEqual({c["provider"] for c in self.models.calls}, {"gpt"})

    def test_model_outage_mid_turn_then_same_provider_resumes(self):
        root = f"/v1/campaigns/{self.gw.id}"
        action = self.declare(1, INSPECT, provider="gpt")
        self.call("POST", root + "/actions", action)
        original = provider_module.OpenAIProvider.complete
        count = {"n": 0}
        def third_call_fails(provider, system, user, capability):
            count["n"] += 1
            if count["n"] == 3:
                self.models.fail["gpt"] = 503
            return original(provider, system, user, capability)
        provider_module.OpenAIProvider.complete = third_call_fails
        try:
            first = self.app.work()[0]
        finally:
            provider_module.OpenAIProvider.complete = original
        self.assertEqual((first["outcome"], first["moves"]), ("blocked", ["tables", "rolls"]))
        self.assertEqual(self.app.work()[0]["outcome"], "blocked")
        self.models.fail.clear()
        second = self.app.work()[0]
        self.assertEqual((second["outcome"], second["moves"]), ("committed", ["commit"]))
        import gateway as gateway_module
        rolls = [r for r in gateway_module.ledger.read_jsonl(self.gw.campaign / "records/roll_log.jsonl") if action["action_id"] in r["purpose"]]
        self.assertEqual(len(rolls), 1)

    def test_session_provider_waits_for_its_session(self):
        root = f"/v1/campaigns/{self.gw.id}"
        self.app.providers["claude-session"] = provider_module.SessionProvider("claude-session")
        action = self.declare(1, HOLSTER, provider="claude-session")
        self.call("POST", root + "/actions", action)
        self.assertEqual(self.app.work()[0]["outcome"], "waiting_for_session")
        self.assertEqual(self.models.calls, [])
        self.assertEqual(self.call("GET", f"{root}/actions/{action['action_id']}")[1]["status"], "submitted")


if __name__ == "__main__":
    unittest.main(verbosity=1)
