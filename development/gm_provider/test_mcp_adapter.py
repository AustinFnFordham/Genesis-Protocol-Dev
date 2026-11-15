"""Tests for the Genesis MCP Streamable HTTP + OAuth 2.1 PKCE adapter (`mcp_adapter.py`).

Distinguishes:
  1. Local deterministic tests over isolated staging copies (`staging.make`) and read-only inspection
     of `staging/shared-1` (with strict before/after byte-identity checks on all protected files).
  2. Scripted GM mocks used only to exercise the `gemini-session` MCP tool sequence on an isolated
     sandbox copy (labelled `mock` in test assertions; never touches `staging/shared-1`).
  3. Local loopback HTTP transport tests (`ThreadingHTTPServer` on `127.0.0.1`) when socket binding
     is permitted by the OS environment.
  4. Actual remote deployment and native Gemini mobile app execution are NOT faked here; they require
     an external HTTPS host and a personal Google account in Gemini web/mobile.

Run: python3 -B development/gm_provider/test_mcp_adapter.py
"""
import base64
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import gateway as gateway_module       # noqa: E402
from mcp_adapter import _pkce_s256     # noqa: E402
import providers as provider_module    # noqa: E402
import service                         # noqa: E402
import staging                         # noqa: E402
from store import GitStore             # noqa: E402
from test_gateway import script, QA, INSPECT, HOLSTER, fingerprints  # noqa: E402


def _can_bind_loopback() -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            s.listen(1)
            addr = s.getsockname()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as c:
                c.settimeout(0.2)
                c.connect(addr)
        return True
    except OSError:
        return False


def _shared_fingerprints() -> dict:
    out = dict(fingerprints())
    shared_dir = ROOT / "staging/shared-1"
    if shared_dir.exists():
        for p in sorted(shared_dir.rglob("*")):
            if p.is_file():
                out[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


class MCPAdapterTest(unittest.TestCase):
    def setUp(self):
        self.protected = _shared_fingerprints()
        QA.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="mcp-", dir=QA)
        self.addCleanup(self.tmp.cleanup)
        self.gw, _ = staging.make(self.tmp.name)
        self.addCleanup(self.gw.store.close)
        self.registry = provider_module.registry({})
        self.registry["gemini-session"] = provider_module.SessionProvider("gemini-session")
        self.registry["gpt-session"] = provider_module.SessionProvider("gpt-session")
        self.registry["claude-session"] = provider_module.SessionProvider("claude-session")
        self.app = service.App(
            {self.gw.id: self.gw},
            self.registry,
            token="player-secret-token",
            origin="https://gemini.google.com",
            gm_tokens={"gemini-session": "gm-gemini-secret", "gpt-session": "gm-gpt-secret"},
            read_token="read-only-secret-token",
            oauth_secret="owner-oauth-master-secret",
            public_base_url="https://genesis-mcp.example.test",
            read_only=False,
        )
        self.public_bodies = []

    def tearDown(self):
        self.assertEqual(_shared_fingerprints(), self.protected)

    def http(self, method, path, body=None, headers=None, app=None, record_public=True):
        target = app or self.app
        hdrs = {"host": "genesis-mcp.example.test", **(headers or {})}
        if isinstance(body, (dict, list)):
            raw_body = json.dumps(body).encode("utf-8")
            hdrs.setdefault("content-type", "application/json")
        elif isinstance(body, str):
            raw_body = body.encode("utf-8")
        elif isinstance(body, bytes):
            raw_body = body
        else:
            raw_body = b""
        code, payload, extra = target.handle_http(method, path, hdrs, raw_body)
        if record_public:
            text = payload.decode("utf-8", "replace") if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False)
            self.public_bodies.append(text)
        return code, payload, extra

    def rpc(self, method, params=None, token="read-only-secret-token", req_id=1, session_id=None, app=None, record_public=True):
        hdrs = {}
        if token:
            hdrs["authorization"] = f"Bearer {token}"
        if session_id:
            hdrs["mcp-session-id"] = session_id
        msg = {"jsonrpc": "2.0", "method": method}
        if req_id is not None:
            msg["id"] = req_id
        if params is not None:
            msg["params"] = params
        return self.http("POST", "/mcp", msg, headers=hdrs, app=app, record_public=record_public)

    def test_oauth21_discovery_dcr_pkce_and_refresh_flow(self):
        # 1. Unauthenticated MCP request returns 401 with RFC 9728 WWW-Authenticate header
        code, payload, extra = self.rpc("initialize", {"protocolVersion": "2025-03-26"}, token=None)
        self.assertEqual(code, 401)
        self.assertIn('resource_metadata="https://genesis-mcp.example.test/.well-known/oauth-protected-resource"', extra["www-authenticate"])

        # 2. Protected Resource Metadata (RFC 9728) & Authorization Server Metadata (RFC 8414)
        code, prm, _ = self.http("GET", "/.well-known/oauth-protected-resource")
        self.assertEqual(code, 200)
        self.assertEqual(prm["resource"], "https://genesis-mcp.example.test/mcp")
        self.assertEqual(prm["authorization_servers"], ["https://genesis-mcp.example.test"])
        self.assertIn("genesis:read", prm["scopes_supported"])

        code, asm, _ = self.http("GET", "/.well-known/oauth-authorization-server")
        self.assertEqual(code, 200)
        self.assertEqual(asm["authorization_endpoint"], "https://genesis-mcp.example.test/oauth/authorize")
        self.assertEqual(asm["token_endpoint"], "https://genesis-mcp.example.test/oauth/token")
        self.assertEqual(asm["code_challenge_methods_supported"], ["S256"])

        # 3. Dynamic Client Registration (RFC 7591)
        code, client, _ = self.http("POST", "/oauth/register", {
            "client_name": "Google Gemini Connected App",
            "redirect_uris": ["https://oauth-redirect.googleusercontent.com/r/genesis"],
        })
        self.assertEqual(code, 201)
        client_id = client["client_id"]
        self.assertTrue(client_id.startswith("genesis-client-"))

        # 4. OAuth 2.1 Authorization Code + PKCE (S256)
        verifier = "gemini-mobile-pkce-verifier-0123456789abcdef0123456789"
        challenge = _pkce_s256(verifier)
        query = urllib.parse.urlencode({
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": "https://oauth-redirect.googleusercontent.com/r/genesis",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "xyz-state-123",
            "scope": "genesis:read",
        })
        code, html_bytes, extra = self.http("GET", f"/oauth/authorize?{query}", record_public=False)
        self.assertEqual(code, 200)
        self.assertIn("text/html", extra["content-type"])
        self.assertIn(b"Authorize Gemini Connected App", html_bytes)

        # Reject plain or missing PKCE
        bad_q = urllib.parse.urlencode({
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": "https://oauth-redirect.googleusercontent.com/r/genesis",
            "code_challenge": verifier,
            "code_challenge_method": "plain",
        })
        self.assertEqual(self.http("GET", f"/oauth/authorize?{bad_q}")[0], 400)

        # Approve consent form with read-only secret -> grants only genesis:read
        form = urllib.parse.urlencode({
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": "https://oauth-redirect.googleusercontent.com/r/genesis",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "xyz-state-123",
            "scope": "genesis:read genesis:gm",
            "secret": "read-only-secret-token",
        })
        code, _, extra = self.http(
            "POST",
            "/oauth/authorize",
            form,
            headers={"content-type": "application/x-www-form-urlencoded"},
            record_public=False,
        )
        self.assertEqual(code, 302)
        redirected = urllib.parse.urlparse(extra["location"])
        qs = urllib.parse.parse_qs(redirected.query)
        self.assertEqual(qs["state"][0], "xyz-state-123")
        auth_code = qs["code"][0]

        # Wrong PKCE verifier fails
        bad_tok = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": client_id,
            "redirect_uri": "https://oauth-redirect.googleusercontent.com/r/genesis",
            "code_verifier": "wrong-verifier",
        })
        # Note: single-use code is consumed on first token attempt after signature check, so mint a fresh code for wrong verifier check
        code2, _, extra2 = self.http(
            "POST",
            "/oauth/authorize",
            form,
            headers={"content-type": "application/x-www-form-urlencoded"},
            record_public=False,
        )
        auth_code_bad = urllib.parse.parse_qs(urllib.parse.urlparse(extra2["location"]).query)["code"][0]
        self.assertEqual(
            self.http(
                "POST",
                "/oauth/token",
                urllib.parse.urlencode({
                    "grant_type": "authorization_code",
                    "code": auth_code_bad,
                    "client_id": client_id,
                    "redirect_uri": "https://oauth-redirect.googleusercontent.com/r/genesis",
                    "code_verifier": "wrong-verifier",
                }),
                headers={"content-type": "application/x-www-form-urlencoded"},
                record_public=False,
            )[0],
            400,
        )

        # Valid PKCE verifier exchanges for access_token + refresh_token
        tok_req = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": client_id,
            "redirect_uri": "https://oauth-redirect.googleusercontent.com/r/genesis",
            "code_verifier": verifier,
        })
        code, tokens, _ = self.http(
            "POST",
            "/oauth/token",
            tok_req,
            headers={"content-type": "application/x-www-form-urlencoded"},
            record_public=False,
        )
        self.assertEqual(code, 200)
        self.assertEqual(tokens["scope"], "genesis:read")
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # Replaying the same authorization_code is rejected
        self.assertEqual(
            self.http(
                "POST",
                "/oauth/token",
                tok_req,
                headers={"content-type": "application/x-www-form-urlencoded"},
                record_public=False,
            )[0],
            400,
        )

        # Refresh token issues a new access token (for persistent mobile linking)
        code, refreshed, _ = self.http(
            "POST",
            "/oauth/token",
            urllib.parse.urlencode({
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
            }),
            headers={"content-type": "application/x-www-form-urlencoded"},
            record_public=False,
        )
        self.assertEqual(code, 200)
        self.assertEqual(refreshed["scope"], "genesis:read")

        # Use OAuth access_token to initialize MCP and call genesis_staging_refresh
        code, init_resp, extra = self.rpc("initialize", {"protocolVersion": "2025-03-26"}, token=access_token)
        self.assertEqual(code, 200)
        sid = extra["mcp-session-id"]
        self.assertTrue(sid.startswith("mcp-"))
        self.assertEqual(init_resp["result"]["serverInfo"]["name"], "genesis-protocol-mcp")

        # Notification returns 202 Accepted
        code, notif_resp, _ = self.rpc("notifications/initialized", token=access_token, req_id=None, session_id=sid)
        self.assertEqual((code, notif_resp), (202, b""))

        # tools/list for genesis:read scope returns ONLY the 4 read-only tools
        code, tools_resp, _ = self.rpc("tools/list", {}, token=access_token, session_id=sid)
        tool_names = [t["name"] for t in tools_resp["result"]["tools"]]
        self.assertEqual(tool_names, [
            "genesis_staging_refresh",
            "genesis_get_page",
            "genesis_get_action",
            "genesis_gm_guide",
        ])
        self.assertTrue(all(t["annotations"]["readOnlyHint"] is True for t in tools_resp["result"]["tools"]))

        # Calling a write/GM tool with a read-only token is refused with FORBIDDEN_SCOPE
        code, denied, _ = self.rpc("tools/call", {"name": "genesis_gm_claim", "arguments": {"run": "r1", "model": "gemini"}}, token=access_token)
        self.assertEqual(code, 200)
        self.assertTrue(denied["result"]["isError"])
        self.assertEqual(denied["result"]["structuredContent"]["error"]["code"], "FORBIDDEN_SCOPE")

    def test_read_only_staging_refresh_on_shared_1_preserves_gpt_shared_0002(self):
        """First deliverable: authenticated, read-only staging refresh against `staging/shared-1`.

        Verifies that Gemini mobile can refresh the real `shared-1` staging state and recovery view
        without network git fetches, without claiming or rerouting `shared-0002`, and without
        modifying a single byte of `staging/shared-1`.
        """
        shared_scope = ROOT / "staging/shared-1"
        gw = staging.open_shared(shared_scope)
        # Prevent any network git fetch during local read-only inspection; read the committed local checkout
        with patch.object(GitStore, "sync", return_value=None):
            ro_app = service.App(
                {gw.id: gw},
                self.registry,
                token="player-secret",
                read_token="gemini-mobile-read-token",
                oauth_secret="gemini-mobile-oauth-secret",
                public_base_url="https://genesis-mcp.example.test",
                read_only=True,
            )
            # Even with the master gm/oauth token, --read-only mode exposes only read-only tools
            code, listed, _ = self.rpc("tools/list", {}, token="gemini-mobile-oauth-secret", app=ro_app)
            self.assertEqual([t["name"] for t in listed["result"]["tools"]], [
                "genesis_staging_refresh",
                "genesis_get_page",
                "genesis_get_action",
                "genesis_gm_guide",
            ])

            # Execute genesis_staging_refresh
            code, refresh_call, _ = self.rpc(
                "tools/call",
                {"name": "genesis_staging_refresh", "arguments": {"campaign_id": "shared-1"}},
                token="gemini-mobile-read-token",
                app=ro_app,
            )
            self.assertEqual(code, 200)
            self.assertFalse(refresh_call["result"]["isError"])
            data = refresh_call["result"]["structuredContent"]
            self.assertEqual(data["campaign_id"], "shared-1")
            self.assertTrue(data["read_only"])
            self.assertTrue(data["changed"])
            self.assertEqual(data["cursor"]["revision"], 40)
            self.assertEqual(data["cursor"]["ledger_head"], "evt_0043")
            self.assertEqual(data["cursor"]["context_id"], "evt_0043")
            self.assertEqual(len(data["cursor"]["public_sha256"]), 64)

            # Verify shared-0002 is reported accurately in recovery and remains assigned to gpt-session
            in_flight = data["recovery"]["in_flight"]
            self.assertEqual(in_flight["action_id"], "shared-0002")
            self.assertEqual(in_flight["status"], "submitted")
            self.assertEqual(in_flight["provider"], "gpt-session")
            self.assertEqual(in_flight["phase"], "interpret")
            self.assertEqual(
                in_flight["mechanical"],
                {"tables_fixed": False, "rolls_accepted": 0, "batch_accepted": False, "batch_committed": False, "fingerprint": None},
            )
            self.assertEqual(data["recovery"]["lease"], {"held": False, "provider": None, "expires_in_ms": 0})

            # Repeat refresh with known cursor -> changed is False
            code, second_call, _ = self.rpc(
                "tools/call",
                {
                    "name": "genesis_staging_refresh",
                    "arguments": {
                        "campaign_id": "shared-1",
                        "known_revision": 40,
                        "known_ledger_head": "evt_0043",
                        "known_public_sha256": data["cursor"]["public_sha256"],
                    },
                },
                token="gemini-mobile-read-token",
                app=ro_app,
            )
            self.assertFalse(second_call["result"]["structuredContent"]["changed"])

            # Read public page and action status
            code, page_call, _ = self.rpc(
                "tools/call",
                {"name": "genesis_get_page", "arguments": {"page": data["pages"][0]}},
                token="gemini-mobile-read-token",
                app=ro_app,
            )
            self.assertFalse(page_call["result"]["isError"])

            code, act_call, _ = self.rpc(
                "tools/call",
                {"name": "genesis_get_action", "arguments": {"action_id": "shared-0002"}},
                token="gemini-mobile-read-token",
                app=ro_app,
            )
            self.assertEqual(act_call["result"]["structuredContent"]["provider"], "gpt-session")

            # Verify any attempt to claim or reroute shared-0002 in read-only mode is blocked with READ_ONLY_MODE
            for forbidden_tool, args in (
                ("genesis_gm_claim", {"run": "gemini-attempt", "model": "gemini"}),
                ("genesis_reroute_action", {"action_id": "shared-0002", "provider": "gemini-session"}),
                ("genesis_select_provider", {"provider": "gemini-session"}),
            ):
                _, blocked, _ = self.rpc(
                    "tools/call",
                    {"name": forbidden_tool, "arguments": args},
                    token="gemini-mobile-oauth-secret",
                    app=ro_app,
                )
                self.assertTrue(blocked["result"]["isError"])
                self.assertEqual(blocked["result"]["structuredContent"]["error"]["code"], "READ_ONLY_MODE")

            # Verify zero private leaks in any public MCP response
            combined = "\n".join(self.public_bodies)
            for secret in ("CANARY", "private table", "recent_private", "gemini-mobile-read-token", "gemini-mobile-oauth-secret"):
                self.assertNotIn(secret, combined)

    def test_conversational_gm_turn_on_isolated_sandbox_and_routing_guard(self):
        """Exercises `gemini-session` MCP tools on an isolated sandbox copy (`self.gw`).

        Note: Uses the deterministic `script("gemini-session")` test double to produce the move JSON
        that Gemini in the mobile conversation would produce. Proves the MCP adapter boundary,
        routing protection for `gpt-session`, bounded GM context, dice resolution, and commit.
        """
        # 1. Queue an action routed to `gpt-session` on the isolated sandbox copy and verify `gemini-session` cannot claim it
        gpt_action = staging.declare(self.gw, "mcp-gpt-0001", text=HOLSTER, provider="gpt-session")
        self.gw.submit(gpt_action)
        _, refused_claim, _ = self.rpc(
            "tools/call",
            {"name": "genesis_gm_claim", "arguments": {"run": "gem-run-1", "model": "gemini-mobile-conversation"}},
            token="gm-gemini-secret",
            record_public=False,
        )
        self.assertTrue(refused_claim["result"]["isError"])
        self.assertEqual(refused_claim["result"]["structuredContent"]["error"]["code"], "NOT_ROUTED_HERE")
        self.assertEqual(refused_claim["result"]["structuredContent"]["error"]["provider"], "gpt-session")

        # 2. Explicitly reroute the isolated sandbox test action to `gemini-session` via MCP
        _, rerouted, _ = self.rpc(
            "tools/call",
            {"name": "genesis_reroute_action", "arguments": {"action_id": "mcp-gpt-0001", "provider": "gemini-session"}},
            token="gm-gemini-secret",
        )
        self.assertFalse(rerouted["result"]["isError"])
        self.assertEqual(rerouted["result"]["structuredContent"]["provider"], "gemini-session")

        # 3. Claim and complete the turn as `gemini-session` via MCP tools
        _, claimed, _ = self.rpc(
            "tools/call",
            {
                "name": "genesis_gm_claim",
                "arguments": {
                    "run": "gem-run-1",
                    "model": "gemini-mobile-mock-test",
                    "session": "test://mcp-adapter/isolated-1",
                },
            },
            token="gm-gemini-secret",
            record_public=False,
        )
        self.assertFalse(claimed["result"]["isError"])
        self.assertEqual(claimed["result"]["structuredContent"]["phase"], "interpret")

        # 4. Step through context -> tables -> commit using the scripted double on the isolated copy
        gm = script("gemini-session")
        while True:
            _, ctx_resp, _ = self.rpc(
                "tools/call",
                {"name": "genesis_gm_context", "arguments": {"run": "gem-run-1"}},
                token="gm-gemini-secret",
                record_public=False,
            )
            self.assertFalse(ctx_resp["result"]["isError"])
            context = ctx_resp["result"]["structuredContent"]
            self.assertIn("_boundary_notice", context)
            move = gm.step(context)
            if move["type"] == "tables":
                _, step_resp, _ = self.rpc(
                    "tools/call",
                    {"name": "genesis_gm_tables", "arguments": {"run": "gem-run-1", "tables": move["tables"]}},
                    token="gm-gemini-secret",
                    record_public=False,
                )
                self.assertFalse(step_resp["result"]["isError"], step_resp)
            elif move["type"] == "rolls":
                for roll_req in move["rolls"]:
                    _, step_resp, _ = self.rpc(
                        "tools/call",
                        {"name": "genesis_gm_roll", "arguments": {"run": "gem-run-1", "roll": roll_req}},
                        token="gm-gemini-secret",
                        record_public=False,
                    )
                    self.assertFalse(step_resp["result"]["isError"], step_resp)
            elif move["type"] == "commit":
                _, step_resp, _ = self.rpc(
                    "tools/call",
                    {"name": "genesis_gm_commit", "arguments": {"run": "gem-run-1", "proposal": move["proposal"]}},
                    token="gm-gemini-secret",
                    record_public=False,
                )
                self.assertFalse(step_resp["result"]["isError"], step_resp)
                self.assertEqual(step_resp["result"]["structuredContent"]["status"], "committed")
                break

        # 5. Submit a second action requiring a dice roll (INSPECT) directly through `genesis_submit_action`
        _, ref_resp, _ = self.rpc("tools/call", {"name": "genesis_staging_refresh", "arguments": {}}, token="read-only-secret-token")
        cursor = ref_resp["result"]["structuredContent"]["cursor"]
        _, sub_resp, _ = self.rpc(
            "tools/call",
            {
                "name": "genesis_submit_action",
                "arguments": {
                    "action_id": "mcp-gem-0002",
                    "based_on_revision": cursor["revision"],
                    "ledger_head": cursor["ledger_head"],
                    "context_id": cursor["context_id"],
                    "text": INSPECT,
                    "gm_provider": "gemini-session",
                },
            },
            token="gm-gemini-secret",
        )
        self.assertFalse(sub_resp["result"]["isError"], sub_resp)
        self.assertEqual(sub_resp["result"]["structuredContent"]["status"], "submitted")

        _, claimed2, _ = self.rpc(
            "tools/call",
            {"name": "genesis_gm_claim", "arguments": {"run": "gem-run-2", "model": "gemini-mobile-mock-test", "session": "test://mcp-adapter/isolated-2"}},
            token="gm-gemini-secret",
            record_public=False,
        )
        self.assertFalse(claimed2["result"]["isError"])

        while True:
            _, ctx_resp, _ = self.rpc(
                "tools/call",
                {"name": "genesis_gm_context", "arguments": {"run": "gem-run-2"}},
                token="gm-gemini-secret",
                record_public=False,
            )
            context = ctx_resp["result"]["structuredContent"]
            move = gm.step(context)
            if move["type"] == "tables":
                self.rpc("tools/call", {"name": "genesis_gm_tables", "arguments": {"run": "gem-run-2", "tables": move["tables"]}}, token="gm-gemini-secret", record_public=False)
            elif move["type"] == "rolls":
                for roll_req in move["rolls"]:
                    _, r_resp, _ = self.rpc("tools/call", {"name": "genesis_gm_roll", "arguments": {"run": "gem-run-2", "roll": roll_req}}, token="gm-gemini-secret", record_public=False)
                    self.assertFalse(r_resp["result"]["isError"], r_resp)
            elif move["type"] == "commit":
                _, c_resp, _ = self.rpc("tools/call", {"name": "genesis_gm_commit", "arguments": {"run": "gem-run-2", "proposal": move["proposal"]}}, token="gm-gemini-secret", record_public=False)
                self.assertEqual(c_resp["result"]["structuredContent"]["status"], "committed")
                break

        # Verify ledger recorded the gemini-session identity attestation and zero private leaks reached public responses
        ruling = [e for e in gateway_module.ledger.load_all(self.gw.campaign) if e["kind"] == "gm_ruling" and "gm_provider" in e.get("details", {})][-1]
        self.assertEqual(ruling["details"]["gm_provider"]["committed_by"], "gemini-session")
        self.assertEqual(ruling["details"]["gm_provider"]["identities"][0]["model"], "gemini-mobile-mock-test")

        combined = "\n".join(self.public_bodies)
        for secret in ("CANARY", "private table", "interpretation", "recent_private", "gm-gemini-secret", "_boundary_notice"):
            self.assertNotIn(secret, combined)

    def test_http_handler_framing_headers_and_cors(self):
        """Exercises `service.handler(self.app)` HTTP wire framing (GET, POST, DELETE, OPTIONS, CORS, Mcp-Session-Id)."""
        import io
        Handler = service.handler(self.app)

        def wire(raw_request: bytes) -> bytes:
            inp = io.BytesIO(raw_request)
            out = io.BytesIO()

            class DummySocket:
                def makefile(self, mode, *args, **kwargs):
                    return inp if "r" in mode else out

                def sendall(self, data):
                    out.write(data)

                def close(self):
                    pass

            Handler(DummySocket(), ("127.0.0.1", 55555), None)
            return out.getvalue()

        # 1. OPTIONS preflight for /mcp
        opt_raw = wire(b"OPTIONS /mcp HTTP/1.1\r\nHost: genesis-mcp.example.test\r\nOrigin: https://gemini.google.com\r\n\r\n")
        self.assertIn(b"204", opt_raw.splitlines()[0])
        self.assertIn(b"access-control-allow-origin: https://gemini.google.com", opt_raw.lower())
        self.assertIn(b"mcp-session-id", opt_raw.lower())

        # 2. POST /mcp initialize -> returns Mcp-Session-Id header
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}}).encode("utf-8")
        post_raw = wire(
            b"POST /mcp HTTP/1.1\r\n"
            b"Host: genesis-mcp.example.test\r\n"
            b"Authorization: Bearer read-only-secret-token\r\n"
            b"Content-Type: application/json\r\n"
            + f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
            + body
        )
        header_block, _, resp_body = post_raw.partition(b"\r\n\r\n")
        self.assertIn(b"200", header_block.splitlines()[0])
        self.assertIn(b"mcp-session-id: mcp-", header_block.lower())
        parsed = json.loads(resp_body.decode("utf-8"))
        self.assertEqual(parsed["result"]["protocolVersion"], "2025-03-26")

        # 3. GET /mcp with valid token returns 405 Method Not Allowed with Allow: POST, DELETE, OPTIONS
        get_raw = wire(
            b"GET /mcp HTTP/1.1\r\n"
            b"Host: genesis-mcp.example.test\r\n"
            b"Authorization: Bearer read-only-secret-token\r\n\r\n"
        )
        self.assertIn(b"405", get_raw.splitlines()[0])
        self.assertIn(b"allow: post, delete, options", get_raw.lower())

        # 4. DELETE /mcp closes session and returns 204
        del_raw = wire(
            b"DELETE /mcp HTTP/1.1\r\n"
            b"Host: genesis-mcp.example.test\r\n"
            b"Authorization: Bearer read-only-secret-token\r\n"
            b"Mcp-Session-Id: mcp-test\r\n\r\n"
        )
        self.assertIn(b"204", del_raw.splitlines()[0])

    @unittest.skipUnless(_can_bind_loopback(), "loopback TCP socket connections are blocked by this sandbox")
    def test_live_http_server_mcp_roundtrip(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), service.handler(self.app))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_address[1]}"

        # 1. Fetch protected resource metadata over real HTTP
        with urllib.request.urlopen(base + "/.well-known/oauth-protected-resource") as resp:
            self.assertEqual(resp.status, 200)
            prm = json.loads(resp.read().decode("utf-8"))
            self.assertIn("genesis:read", prm["scopes_supported"])

        # 2. Call MCP genesis_staging_refresh over real HTTP POST
        req = urllib.request.Request(
            base + "/mcp",
            method="POST",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 42,
                "method": "tools/call",
                "params": {"name": "genesis_staging_refresh", "arguments": {}},
            }).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "authorization": "Bearer read-only-secret-token",
            },
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            body = json.loads(resp.read().decode("utf-8"))
            self.assertFalse(body["result"]["isError"])
            self.assertEqual(body["result"]["structuredContent"]["campaign_id"], self.gw.id)


if __name__ == "__main__":
    unittest.main(verbosity=1)
