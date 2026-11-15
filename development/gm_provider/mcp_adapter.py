"""OAuth-protected ChatGPT tools for the existing shared staging gateway.

No model execution, new store, or alternate commit path. Run on the persistence
host; Git credentials and provider tokens stay there. Writes default to disabled.
"""
import argparse
import hmac
import json
import os
from pathlib import Path
import re
import threading
import time
from urllib.parse import urlsplit

import httpx
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent, ToolAnnotations

from gateway import Refused
from git_errors import GitFailure
from service import App

READ = "genesis:read"
GM = "genesis:gm"
PROVIDER = "gpt-session"
ROOT = Path(__file__).resolve().parents[2]
REFERENCES = {
    "gm_guide": "development/gm_provider/GM_GUIDE.md",
    "turn_contract": "campaigns/starwars_litrpg/creator/TURN_CONTRACT.md",
    "consequence_authority": "Contracts/CHAOS_ENGINE_CONSEQUENCE_TRIAD_COMPLETE.md",
    "soul_contract": "Contracts/soul_essence_contract.md",
    "chaos_doctrine": "Contracts/CHAOS_ORIGIN_AND_DESIGN_DOCTRINE.md",
}


def https_url(value):
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("Configure a credential-free HTTPS URL without query or fragment")
    return value


class IntrospectionVerifier:
    """RFC7662 verification at an explicitly configured trusted OAuth issuer.

    ChatGPT tokens are audience-bound to MCP, never forwarded to Git or used as
    the internal GM token. An issuer outage fails closed; no token is cached.
    """
    def __init__(self, issuer, resource, endpoint, client_id, client_secret, subject, transport=None):
        self.issuer, self.resource, self.endpoint = map(https_url, (issuer, resource, endpoint))
        if not all(isinstance(v, str) and v for v in (client_id, client_secret, subject)):
            raise ValueError("OAuth introspection client credentials and allowed subject are required")
        self.client_id, self.client_secret, self.subject = client_id, client_secret, subject
        self.transport = transport

    async def verify_token(self, token):
        try:
            async with httpx.AsyncClient(timeout=5, follow_redirects=False, transport=self.transport) as client:
                response = await client.post(self.endpoint, data={"token": token, "token_type_hint": "access_token"},
                                             auth=httpx.BasicAuth(self.client_id, self.client_secret))
            if response.status_code != 200 or len(response.content) > 65536:
                return None
            data = response.json()
            audience = data.get("aud")
            audiences = [audience] if isinstance(audience, str) else audience
            expires = data.get("exp")
            scopes = data.get("scope")
            subject = data.get("sub")
            if (data.get("active") is not True or data.get("iss") != self.issuer
                    or not isinstance(audiences, list) or self.resource not in audiences
                    or type(expires) is not int or expires <= time.time()
                    or not isinstance(subject, str) or not hmac.compare_digest(subject.encode(), self.subject.encode())
                    or not isinstance(scopes, str) or READ not in scopes.split()
                    or not isinstance(data.get("client_id"), str) or not data["client_id"]):
                return None
            return AccessToken(token=token, client_id=data["client_id"], scopes=scopes.split(),
                               expires_at=expires, resource=self.resource, subject=subject)
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return None


class GatewayTools:
    def __init__(self, app, campaign_id, subject, writes=False):
        if set(app.gateways) != {campaign_id} or not app.gm_tokens.get(PROVIDER):
            raise ValueError("Bind one staging campaign and the server-held gpt-session GM token")
        self.app, self.campaign_id, self.subject, self.writes = app, campaign_id, subject, writes
        self.guard = threading.RLock()

    def authorize(self, write=False):
        token = get_access_token()
        if (not token or token.subject != self.subject or READ not in token.scopes
                or not token.expires_at or token.expires_at <= time.time()):
            raise Refused("UNAUTHORIZED", "An authorized Genesis account is required")
        if write and not self.writes:
            raise Refused("WRITES_DISABLED", "GM writes require explicit host opt-in")
        if write and GM not in token.scopes:
            raise Refused("INSUFFICIENT_SCOPE", "GM writes require genesis:gm scope")

    def read(self, kind, value=None):
        self.authorize()
        with self.guard:
            gateway = self.app.gateways[self.campaign_id]
            if kind == "refresh":
                # No claim, renewal, table acceptance, recovery mutation or publication.
                sync = getattr(gateway.store, "sync", None)
                if sync:
                    sync(force=True)
                public = gateway.public_state()
                recovery = gateway.recovery()
                if (public["cursor"]["revision"], public["cursor"]["ledger_head"]) != (recovery["revision"], recovery["ledger_head"]):
                    raise Refused("REFRESH_MOVED", "Campaign moved during refresh; repeat the read")
                return {"audience": "player", "public": public, "recovery": recovery}
            if kind == "page":
                if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
                    raise Refused("BAD_PAGE", "Use a page ID advertised by refresh")
                return {"audience": "player", "page": gateway.page(value)}
            if kind == "reference" and value in REFERENCES:
                return {"reference": value, "path": REFERENCES[value], "text": (ROOT / REFERENCES[value]).read_text()}
            raise Refused("BAD_REFERENCE", "Use an advertised reference name")

    def gm(self, verb, run, body=None, model=None, session=None):
        self.authorize(write=True)
        if verb not in {"claim", "context", "tables", "roll", "review", "commit", "publish", "release"}:
            raise Refused("BAD_VERB", "Unsupported GM operation")
        if not isinstance(run, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run):
            raise Refused("BAD_RUN", "Use one stable run ID per authorized GM attempt")
        with self.guard:
            # Reuse the exact existing token-scoped HTTP transport handler.
            status, payload = self.app.gm("POST", self.campaign_id, PROVIDER, verb,
                {"authorization": "Bearer " + self.app.gm_tokens[PROVIDER]},
                json.dumps({"run": run, "body": body, "model": model, "session": session}).encode())
            return {"http_status": status, "audience": "gm", "result": payload}


def result(call):
    metadata = None
    try:
        data = call()
        failed = data.get("http_status", 200) >= 400
    except GitFailure as error:
        data, failed = error.as_dict(), True
    except Refused as error:
        data, failed = error.as_dict(), True
        if error.code in {"UNAUTHORIZED", "INSUFFICIENT_SCOPE"}:
            scopes = READ if error.code == "UNAUTHORIZED" else READ + " " + GM
            metadata = {"mcp/www_authenticate": [f'Bearer error="insufficient_scope", scope="{scopes}"']}
    except Exception:
        # SDK error formatting must not echo paths, private context or credentials.
        data, failed = {"error": {"code": "GATEWAY_UNAVAILABLE", "message": "Stop and inspect server-side recovery; do not reroll"}}, True
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(data, ensure_ascii=False))],
                          structuredContent=data, isError=failed, _meta=metadata)


def create_server(tools, verifier, issuer, resource, host="127.0.0.1", port=8789):
    resource, issuer = https_url(resource), https_url(issuer)
    if urlsplit(resource).path != "/mcp":
        raise ValueError("The MCP resource URL must end in /mcp at the origin root")
    mcp = FastMCP("Genesis shared staging", instructions=(
        "You are the GM; this service does not call a model. Start with genesis_refresh and the reference tools. "
        "Claim only a player-authorized pending gpt-session staging request. Use one run ID, accepted tables and rolls. "
        "Never reroll, change player intent or bypass validation. Context is GM-private; narrate only committed public results. "
        "On Git errors stop; use refresh for recovery. Do not publish private tool output to the player."),
        host=host, port=port, stateless_http=True, json_response=True, max_request_body_size=262144,
        token_verifier=verifier, auth=AuthSettings(issuer_url=issuer, resource_server_url=resource, required_scopes=[READ]),
        transport_security=TransportSecuritySettings(allowed_hosts=[urlsplit(resource).netloc, "127.0.0.1:*", "localhost:*"],
                                                     allowed_origins=["https://chatgpt.com", resource.rsplit("/", 1)[0]]))

    def register(name, function, description, readonly=False, destructive=False):
        scopes = [READ] if readonly else [READ, GM]
        mcp.tool(name=name, description=description, annotations=ToolAnnotations(readOnlyHint=readonly,
                 destructiveHint=destructive, openWorldHint=False),
                 meta={"securitySchemes": [{"type": "oauth2", "scopes": scopes}]})(function)

    def refresh() -> CallToolResult:
        return result(lambda: tools.read("refresh"))
    def page(page_id: str) -> CallToolResult:
        return result(lambda: tools.read("page", page_id))
    def reference(name: str) -> CallToolResult:
        return result(lambda: tools.read("reference", name))
    def claim(run: str, model: str, session: str) -> CallToolResult:
        return result(lambda: tools.gm("claim", run, model=model, session=session))
    def context(run: str) -> CallToolResult:
        return result(lambda: tools.gm("context", run))
    def tables(run: str, body: dict) -> CallToolResult:
        return result(lambda: tools.gm("tables", run, body))
    def roll(run: str, body: dict) -> CallToolResult:
        return result(lambda: tools.gm("roll", run, body))
    def review(run: str, body: dict) -> CallToolResult:
        return result(lambda: tools.gm("review", run, body))
    def commit(run: str, body: dict) -> CallToolResult:
        return result(lambda: tools.gm("commit", run, body))
    def publish(run: str) -> CallToolResult:
        return result(lambda: tools.gm("publish", run))
    def release(run: str) -> CallToolResult:
        return result(lambda: tools.gm("release", run))
    register("genesis_refresh", refresh, "Read public staging state, request status and recovery flags. No lease or turn mutation.", True)
    register("genesis_page", page, "Read a public history page ID advertised by genesis_refresh.", True)
    register("genesis_reference", reference, "Read authoritative guidance: " + ", ".join(REFERENCES) + ". No arbitrary file access.", True)
    register("genesis_claim", claim, "Claim the existing player-authorized gpt-session request. Persists a lease; no replacement declaration.")
    register("genesis_context", context, "Get GM-private context for the held run. Renews lease and records processing stage; this is a write.")
    register("genesis_tables", tables, "Accept the session GM's interpretation and tables once, before dice. Reuse accepted work.")
    register("genesis_roll", roll, "Ask the deterministic gateway roller for one roll. Repeat identical requests after uncertainty; never choose faces.")
    register("genesis_review", review, "Return a declaration for player clarification before mechanical work is accepted.")
    register("genesis_commit", commit, "Validate and atomically commit the session GM's proposal. Append-only authoritative consequences.", destructive=True)
    register("genesis_publish", publish, "Finish accepted work and paginated public publication; never author a replacement turn.")
    register("genesis_release", release, "Release this run's lease, preserving all accepted tables, dice and recovery records.")
    return mcp


def build(shared, env=None):
    import staging
    env = os.environ if env is None else env
    # This entry point can only open an existing explicitly noncanonical scope.
    environment = json.loads((Path(shared) / "environment.json").read_text())
    if environment.get("canonical") is not False:
        raise ValueError("Only explicitly noncanonical shared staging is supported")
    gateway = staging.open_shared(shared)
    if gateway.store.branch != "staging/provider-shared":
        raise ValueError("The authoritative checkout must be on staging/provider-shared; code lives in a separate checkout")
    issuer, resource = env["GENESIS_MCP_ISSUER"], env["GENESIS_MCP_RESOURCE"]
    verifier = IntrospectionVerifier(issuer, resource, env["GENESIS_MCP_INTROSPECTION_URL"],
        env["GENESIS_MCP_CLIENT_ID"], env["GENESIS_MCP_CLIENT_SECRET"], env["GENESIS_MCP_SUBJECT"])
    tokens = json.loads(env["GENESIS_GM_TOKENS"])
    app = App({gateway.id: gateway}, {}, None, gm_tokens={PROVIDER: tokens[PROVIDER]})
    tools = GatewayTools(app, gateway.id, env["GENESIS_MCP_SUBJECT"], writes=env.get("GENESIS_MCP_ENABLE_WRITES") == "1")
    return create_server(tools, verifier, issuer, resource, host=env.get("GENESIS_MCP_HOST", "127.0.0.1"),
                         port=int(env.get("GENESIS_MCP_PORT", "8789")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared", required=True, type=Path)
    args = parser.parse_args()
    try:
        server = build(args.shared)
    except Exception:
        parser.exit(2, "MCP startup refused: verify staging scope, branch and server-only OAuth/GM configuration\n")
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
