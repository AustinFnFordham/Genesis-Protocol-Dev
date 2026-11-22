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
    first = adapter.for_gateway(gateway)
    guard = adapter.for_gateway(gateway, first.generation)
    return adapter.GatewayTools(app, gateway.id, SUBJECT, writes=writes, guard=guard)


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

    def test_gm_scope_probe_never_mutates_and_requests_step_up(self):
        self.act(HOLSTER, provider=adapter.PROVIDER)
        before = self.gw.recovery()
        with patch.object(self.tools.app, "gm", side_effect=AssertionError("probe called GM write")):
            with patch("mcp_adapter.get_access_token", return_value=access(scopes=[adapter.READ])):
                out = adapter.result(lambda: self.tools.gm_scope_probe())
                self.assertTrue(out.isError)
                self.assertEqual(out.structuredContent["error"]["code"], "INSUFFICIENT_SCOPE")
                challenge = out.meta["mcp/www_authenticate"][0]
                self.assertIn("error_description=", challenge)
                self.assertIn("genesis:gm", challenge)
            with patch("mcp_adapter.get_access_token", return_value=access()):
                result = self.tools.gm_scope_probe()
                self.assertTrue(result["gm_scope_granted"])
                self.assertEqual(result["connection_provider"], "gpt-session")
                self.assertTrue(result["gm_write_ready"])
                self.assertEqual(result["gm_write_blockers"], [])
        after = self.gw.recovery()
        self.assertEqual(before["in_flight"], after["in_flight"])
        self.assertEqual(before["lease"], after["lease"])

    def test_gm_scope_probe_is_readonly_tool_with_gm_security_scheme(self):
        class ReadVerifier:
            async def verify_token(self, token):
                return access(scopes=[adapter.READ]) if token == "test-oauth-token" else None

        server = adapter.create_server(self.tools, ReadVerifier(), ISSUER, RESOURCE)
        with TestClient(server.streamable_http_app(), base_url="https://genesis.example.invalid") as client:
            headers = {"accept": "application/json, text/event-stream",
                       "mcp-protocol-version": "2025-11-25",
                       "authorization": "Bearer test-oauth-token"}
            envelope = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
            listed = client.post("/mcp", headers=headers, json=envelope)
            self.assertEqual(listed.status_code, 200)
            tool = next(t for t in listed.json()["result"]["tools"] if t["name"] == "genesis_gm_scope_probe")
            self.assertTrue(tool["annotations"]["readOnlyHint"])
            self.assertIn(adapter.GM, tool["_meta"]["securitySchemes"][0]["scopes"])
            envelope["method"] = "tools/call"
            envelope["params"] = {"name": "genesis_gm_scope_probe", "arguments": {}}
            blocked = client.post("/mcp", headers=headers, json=envelope)
            self.assertEqual(blocked.status_code, 200)
            payload = blocked.json()["result"]
            self.assertTrue(payload["isError"])
            self.assertEqual(payload["structuredContent"]["error"]["code"], "INSUFFICIENT_SCOPE")
            self.assertIn("error_description=", payload["_meta"]["mcp/www_authenticate"][0])

    def test_disappearing_generation_blocks_an_already_started_worker(self):
        self.act(HOLSTER, provider=adapter.PROVIDER)
        self.assertFalse(self.tools.read("refresh")["read_only"])
        self.tools.guard.marker.unlink()
        with patch.object(self.tools.app, "gm") as handler:
            outcome = adapter.result(lambda: self.tools.gm("claim", "run"))
            self.assertEqual(outcome.structuredContent["error"]["code"], "STORAGE_RECOVERY_REQUIRED")
            handler.assert_not_called()
        status = self.tools.read("refresh")
        self.assertTrue(status["read_only"])
        self.assertEqual(status["storage_recovery_reason"], "marker_missing")
        self.assertEqual(status["gm_write_blockers"], ["STORAGE_RECOVERY_REQUIRED"])
        self.assertFalse(self.tools.guard.marker.exists())
        self.assertFalse(self.gw.recovery()["lease"]["held"])

    def test_refresh_distinguishes_all_write_blockers(self):
        self.tools.guard = adapter.for_gateway(self.gw, "wrong-generation")
        self.tools.writes = False
        self.tools.app.gm_tokens.clear()
        with patch("mcp_adapter.get_access_token", return_value=access(scopes=[adapter.READ])):
            status = self.tools.read("refresh")
        self.assertEqual(status["storage_recovery_reason"], "generation_mismatch")
        self.assertEqual(status["gm_write_blockers"], [
            "STORAGE_RECOVERY_REQUIRED", "WRITES_DISABLED", "INSUFFICIENT_SCOPE", "PROVIDER_NOT_CONFIGURED",
        ])

    def test_readonly_oauth_token_can_read_but_cannot_run_gm(self):
        self.act(HOLSTER, provider=adapter.PROVIDER)
        class ReadVerifier:
            async def verify_token(self, token):
                return access(scopes=[adapter.READ]) if token == "test-oauth-token" else None

        server = adapter.create_server(self.tools, ReadVerifier(), ISSUER, RESOURCE)
        with TestClient(server.streamable_http_app(), base_url="https://genesis.example.invalid") as client:
            metadata = client.get("/.well-known/oauth-protected-resource/mcp")
            self.assertEqual(metadata.status_code, 200)
            self.assertEqual(metadata.json()["scopes_supported"], [adapter.READ, adapter.GM])
            headers = {
                "accept": "application/json, text/event-stream",
                "mcp-protocol-version": "2025-11-25",
                "authorization": "Bearer test-oauth-token",
            }
            payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": "genesis_refresh", "arguments": {}}}
            read = client.post("/mcp", headers=headers, json=payload)
            self.assertEqual(read.status_code, 200)
            self.assertFalse(read.json()["result"].get("isError", False))
            payload["params"] = {"name": "genesis_claim",
                                 "arguments": {"run": "non-mutating-test", "model": "fixture", "session": "fixture"}}
            blocked = client.post("/mcp", headers=headers, json=payload)
            self.assertEqual(blocked.status_code, 200)
            self.assertEqual(blocked.json()["result"]["structuredContent"]["error"]["code"], "INSUFFICIENT_SCOPE")
            self.assertFalse(self.gw.recovery()["lease"]["held"])

    def test_scope_metadata_replacement_preserves_sdk_route_invariants(self):
        server = adapter.create_server(self.tools, Verifier(), ISSUER, RESOURCE)
        self.assertEqual(server.settings.auth.required_scopes, [adapter.READ])
        expected_path = "/.well-known/oauth-protected-resource/mcp"
        for app in (server.streamable_http_app(), server.streamable_http_app()):
            routes = [route for route in app.router.routes if getattr(route, "path", None) == expected_path]
            self.assertEqual(len(routes), 1)
            self.assertEqual(routes[0].methods, {"GET", "OPTIONS", "HEAD"})

        no_metadata = adapter.GenesisFastMCP("No protected resource metadata", token_verifier=Verifier(),
            auth=adapter.AuthSettings(issuer_url=ISSUER, resource_server_url=None,
                                      required_scopes=[adapter.READ]))
        app = no_metadata.streamable_http_app()
        self.assertNotIn(expected_path, [getattr(route, "path", None) for route in app.router.routes])

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
            self.assertEqual(metadata.json()["scopes_supported"], [adapter.READ, adapter.GM])
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
