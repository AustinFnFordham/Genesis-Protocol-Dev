"""Local MCP/HTTP tests. Scripted GM fixtures, never an actual shared staging turn."""
import asyncio
import copy
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

import httpx
from starlette.testclient import TestClient
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mcp_adapter as adapter
from git_errors import GitFailure, diagnostic
from service import App
from test_gateway import Base, INSPECT, HOLSTER, script, fingerprints, ledger
import test_shared_store as shared_fixture
import staging

ISSUER = "https://identity.example.invalid"
RESOURCE = "https://genesis.example.invalid/mcp"
SUBJECT = "owner-staging-subject"


def access(scopes=None, subject=SUBJECT):
    return AccessToken(token="test-oauth-token", client_id="test-chatgpt-client", subject=subject,
                       resource=RESOURCE, scopes=[adapter.READ, adapter.GM] if scopes is None else scopes,
                       expires_at=int(time.time()) + 300, claims={"provider":"gpt-session"})


class Verifier:
    async def verify_token(self, token):
        return access() if token == "test-oauth-token" else None


def tools(gateway, writes=True):
    app = App({gateway.id: gateway}, {}, None, gm_tokens={adapter.PROVIDER: "test-server-only-gm-token"})
    return adapter.GatewayTools(app, gateway.id, SUBJECT, writes=writes)


# OAuth validity, issuer outage and URL tests now live in test_mobile_reconciliation.py


class Adapter(Base):
    def setUp(self):
        super().setUp()
        self.tools = tools(self.gw)
        self.auth = auth_context_var.set(AuthenticatedUser(access()))
        self.addCleanup(auth_context_var.reset, self.auth)

    def test_refresh_is_readonly_and_public_with_pending_action(self):
        action, _ = self.act(INSPECT, provider=adapter.PROVIDER)
        before = {p.relative_to(self.gw.campaign): p.read_bytes() for p in self.gw.campaign.rglob('*') if p.is_file()}
        with patch.object(self.gw.store, "put", side_effect=AssertionError("refresh wrote")):
            out = self.tools.read("refresh")
        after = {p.relative_to(self.gw.campaign): p.read_bytes() for p in self.gw.campaign.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(out["recovery"]["in_flight"]["action_id"], action["action_id"])
        self.assertFalse(out["recovery"]["lease"]["held"])
        for secret in ("CANARY", "recent_private", "interpretation", "test-server-only-gm-token"):
            self.assertNotIn(secret, json.dumps(out))

    def test_owner_scopes_and_host_write_switch_enforced_before_gateway(self):
        self.act(HOLSTER, provider=adapter.PROVIDER)
        with patch.object(self.tools.app, "gm") as handler:
            with patch("mcp_adapter.get_access_token", return_value=access(subject="other-user")):
                self.assertTrue(adapter.result(lambda: self.tools.read("refresh")).isError)
            with patch("mcp_adapter.get_access_token", return_value=access(scopes=[adapter.READ])):
                out = adapter.result(lambda: self.tools.gm("claim", "run"))
                self.assertEqual(out.structuredContent["error"]["code"], "INSUFFICIENT_SCOPE")
                self.assertIn("mcp/www_authenticate", out.meta)
            self.tools.writes = False
            self.assertEqual(adapter.result(lambda: self.tools.gm("claim", "run")).structuredContent["error"]["code"], "WRITES_DISABLED")
            handler.assert_not_called()

    def test_existing_provider_routing_and_lease_controls_are_used(self):
        self.act(HOLSTER, provider="gemini-session")
        out = self.tools.gm("claim", "run")
        self.assertEqual(out["result"]["error"]["code"], "NOT_ROUTED_HERE")
        self.assertEqual(out["http_status"], 409)
        with self.assertRaises(adapter.Refused):
            self.tools.gm("reroute", "run")

    def test_scripted_round_trip_retry_and_public_boundary(self):
        action, _ = self.act(INSPECT, provider=adapter.PROVIDER)
        self.assertEqual(self.tools.gm("claim", "test-run")["http_status"], 200)
        scripted = script(adapter.PROVIDER)
        private = []
        for _ in range(8):
            ctx = self.tools.gm("context", "test-run")["result"]
            private.append(ctx)
            move = scripted.step(ctx)
            verb = {"tables": "tables", "rolls": "roll", "commit": "commit"}[move["type"]]
            bodies = move["rolls"] if verb == "roll" else [move.get("tables") or move.get("proposal")]
            for body in bodies:
                out = self.tools.gm(verb, "test-run", body)
                self.assertEqual(out["http_status"], 200, out)
                if verb == "roll":
                    duplicate = self.tools.gm(verb, "test-run", copy.deepcopy(body))
                    self.assertEqual(out["result"]["result"], duplicate["result"]["result"])
            if verb == "commit":
                break
        self.assertEqual(out["result"]["status"], "committed")
        public = self.tools.read("refresh")
        self.assertIsNone(public["recovery"]["in_flight"])
        for name in public["public"]["pages"]:
            page = self.tools.read("page", name)
            for canary in ("CANARY", "private table", "recent_private", "test-server-only-gm-token"):
                self.assertNotIn(canary, json.dumps(page))
        rolls = [r for r in ledger.read_jsonl(self.gw.campaign / "records/roll_log.jsonl") if action["action_id"] in r["purpose"]]
        self.assertEqual(len(rolls), 1)
        self.assertFalse(ledger.validate_all(self.gw.campaign)[1])

    def test_git_failure_is_preserved_without_alternative_commits_or_raw_errors(self):
        self.act(HOLSTER, provider=adapter.PROVIDER)
        failure = GitFailure(diagnostic("push", 128, "fatal: Authentication failed for 'https://u:secret@host/repo'\nPRIVATE_CANARY"))
        with patch.object(self.gw.store, "put", side_effect=failure):
            out = adapter.result(lambda: self.tools.gm("claim", "run"))
        self.assertTrue(out.isError)
        self.assertEqual(out.structuredContent["result"]["error"]["git"]["exit_code"], 128)
        self.assertNotIn("secret", out.model_dump_json())
        self.assertNotIn("PRIVATE_CANARY", out.model_dump_json())
        out = adapter.result(lambda: (_ for _ in ()).throw(RuntimeError("private hidden context test-server-only-gm-token")))
        self.assertNotIn("hidden context", out.model_dump_json())

    def test_references_bounded_and_unknown_pages_rejected(self):
        for name in adapter.REFERENCES:
            self.assertTrue(self.tools.read("reference", name)["text"])
        for name in ("../../hidden", "gm_guide/../secret"):
            self.assertTrue(adapter.result(lambda: self.tools.read("reference", name)).isError)
            self.assertTrue(adapter.result(lambda: self.tools.read("page", name)).isError)

    def test_real_mcp_auth_discovery_tools_and_readonly_refresh(self):
        self.act(HOLSTER, provider=adapter.PROVIDER)
        self.tools.writes = False
        server = adapter.create_server(self.tools, Verifier(), ISSUER, RESOURCE)
        with TestClient(server.streamable_http_app(), base_url="https://genesis.example.invalid") as client:
            headers = {"accept": "application/json, text/event-stream", "mcp-protocol-version": "2025-11-25"}
            envelope = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
            r = client.post("/mcp", headers=headers, json=envelope)
            self.assertEqual(r.status_code, 401)
            self.assertIn("oauth-protected-resource", r.headers["www-authenticate"])
            metadata = client.get("/.well-known/oauth-protected-resource/mcp")
            self.assertEqual(metadata.status_code, 200)
            self.assertEqual(metadata.json()["authorization_servers"], [ISSUER + "/"])
            headers["authorization"] = "Bearer test-oauth-token"
            r = client.post("/mcp", headers=headers, json=envelope)
            self.assertEqual(r.status_code, 200, r.text)
            descriptions = {t["name"]: t for t in r.json()["result"]["tools"]}
            self.assertTrue(descriptions["genesis_refresh"]["annotations"]["readOnlyHint"])
            self.assertNotIn("genesis_context", descriptions)
            self.assertNotIn("genesis_commit", descriptions)
            self.assertIn("oauth2", json.dumps(descriptions["genesis_refresh"]["_meta"]))
            for name, args in (("genesis_refresh", {}), ("genesis_claim", {"run": "run", "model": "gpt-session", "session": "local-test"})):
                payload = dict(envelope, method="tools/call", params={"name": name, "arguments": args})
                r = client.post("/mcp", headers=headers, json=payload)
                self.assertEqual(r.status_code, 200)
                result = r.json()["result"]
                self.assertEqual(result.get("isError", False), name == "genesis_claim")
                self.assertNotIn("test-server-only-gm-token", r.text)
            self.assertEqual(self.gw._in_flight()[2]["status"], "submitted")


class GitAdapter(unittest.TestCase):
    # Reuse fixture setup, not its separately executed regression tests.
    setUp = shared_fixture.Shared.setUp
    tearDown = shared_fixture.Shared.tearDown
    clone = shared_fixture.Shared.clone
    session = shared_fixture.Shared.session
    def test_mcp_refresh_and_claim_share_real_git_cas_and_server_store(self):
        action = staging.declare(self.player, "adapter-0001", text=HOLSTER, provider=adapter.PROVIDER)
        self.player.submit(action)
        gateway = self.session("adapter-server")
        tool = tools(gateway)
        token = auth_context_var.set(AuthenticatedUser(access()))
        try:
            before = gateway.store._git("rev-parse", "HEAD")
            refreshed = tool.read("refresh")
            self.assertEqual(gateway.store._git("rev-parse", "HEAD"), before)
            self.assertEqual(refreshed["recovery"]["in_flight"]["action_id"], action["action_id"])
            self.assertEqual(tool.gm("claim", "mcp-run")["http_status"], 200)
            self.assertNotEqual(gateway.store._git("rev-parse", "HEAD"), before)
            observed = self.player.recovery()
            self.assertTrue(observed["lease"]["held"])
            self.assertEqual(observed["lease"]["provider"], adapter.PROVIDER)
            self.assertEqual(observed["in_flight"]["status"], "processing")
        finally:
            auth_context_var.reset(token)


if __name__ == "__main__":
    unittest.main()
