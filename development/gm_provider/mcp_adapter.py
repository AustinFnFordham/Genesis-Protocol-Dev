"""OAuth-protected multi-provider GM tools for the existing shared staging gateway.

No model execution, new store, or alternate commit path. Run on the persistence
host; Git credentials and provider tokens stay there. Writes default to disabled.
"""
import argparse
from contextlib import nullcontext
import hmac
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlsplit

import anyio
import jwt
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent, ToolAnnotations

from gateway import Refused
from git_errors import GitFailure
from service import App
from worktree_guard import for_gateway

READ = "genesis:read"
GM = "genesis:gm"
PROVIDER = "gpt-session"
BASE_PROVIDERS = frozenset({"gpt-session", "gemini-session"})
SUPPORTED_PROVIDERS = BASE_PROVIDERS | {"codex-session"}
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


# Public projection helpers selectively ported from Gemini commit 2a1e324.
def _public_sha256(state_doc: dict) -> str:
    return hashlib.sha256(json.dumps(state_doc, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

def _compact_state(state_doc: dict) -> dict:
    """Bounded, mobile-friendly summary of the public `view/state` document.

    Preserves all actionable player & GM turn_context fields (cursor/revision, scene, character
    vital state, options, dialogue, objects, movement, hands, pending_steps, notes, recent feed)
    while keeping payload size small for mobile conversation refresh.
    """
    scene = state_doc.get("scene") or {}
    character = state_doc.get("character") or {}
    tc = state_doc.get("turn_context") or {}
    feed = state_doc.get("feed") or []
    journal = state_doc.get("journal") or []
    return {
        "revision": state_doc.get("revision"),
        "ledger_head": state_doc.get("ledger_head"),
        "active_actor": state_doc.get("active_actor"),
        "scene": {
            "title": scene.get("title"),
            "location": scene.get("location"),
            "summary": scene.get("summary"),
            "atmosphere": (scene.get("atmosphere") or [])[:6],
        },
        "character": {
            "id": character.get("id") or tc.get("actor"),
            "name": character.get("name") or tc.get("actor_name"),
            "hp": character.get("hp"),
            "conditions": character.get("conditions") or [],
            "hands": tc.get("hands") or character.get("hands") or {},
        },
        "turn_context": {
            "context_id": tc.get("context_id"),
            "actor": tc.get("actor"),
            "actor_name": tc.get("actor_name"),
            "mode": tc.get("mode"),
            "round": tc.get("round"),
            "budget": tc.get("budget"),
            "speed_ft": tc.get("speed_ft"),
            "resources": tc.get("resources"),
            "hands": tc.get("hands"),
            "options": tc.get("options") or [],
            "dialogue": tc.get("dialogue") or [],
            "objects": tc.get("objects") or [],
            "movement": tc.get("movement") or [],
            "reactions": tc.get("reactions") or [],
            "visible": tc.get("visible") or [],
            "notes": tc.get("notes") or [],
            "pending_steps": tc.get("pending_steps") or [],
            "pending_reason": tc.get("pending_reason"),
        },
        "recent_feed": feed[-3:],
        "recent_journal": journal[-2:],
    }

class GenesisFastMCP(FastMCP):
    """Advertise optional GM scope without requiring it for every MCP read.

    The pinned MCP SDK uses AuthSettings.required_scopes for BOTH the global
    BearerAuthMiddleware check and OAuth protected-resource metadata. Genesis
    requires genesis:read globally; genesis:gm is only required by GM tools.
    Replace the SDK-generated metadata route with the same SDK helper so the
    advertised scope catalog can include both without weakening authentication.
    """

    def streamable_http_app(self):
        app = super().streamable_http_app()
        if self.settings.auth is None or self.settings.auth.resource_server_url is None:
            return app
        from mcp.server.auth.routes import create_protected_resource_routes

        replacements = create_protected_resource_routes(
            resource_url=self.settings.auth.resource_server_url,
            authorization_servers=[self.settings.auth.issuer_url],
            scopes_supported=[READ, GM],
        )
        for replacement in replacements:
            matches = [
                index for index, route in enumerate(app.router.routes)
                if getattr(route, "path", None) == replacement.path
            ]
            if len(matches) != 1:
                raise RuntimeError("Expected one OAuth protected-resource metadata route")
            app.router.routes[matches[0]] = replacement
        return app


class JWTVerifier:
    """Auth0 is the authorization server. This resource server only verifies JWTs.

    Codes, login passwords, signing keys and replay state never live here.
    The verified OAuth client (azp) is pinned to exactly one GM provider.
    """
    def __init__(self, issuer, resource, clients, subject, key_client=None):
        self.issuer, self.resource = https_url(issuer), https_url(resource)
        if not self.issuer.endswith('/') or urlsplit(self.issuer).path != '/':
            raise ValueError('Use the exact Auth0 tenant issuer, including its final slash')
        # GPT/Gemini stay mandatory and independent; Codex is an opt-in THIRD client.
        # Each Auth0 azp must map to one and only one server-authorized provider.
        if (not subject or not isinstance(clients, dict) or not clients
                or any(not isinstance(k, str) or not k or not isinstance(v, str)
                       or v not in SUPPORTED_PROVIDERS for k, v in clients.items())
                or len(set(clients.values())) != len(clients)
                or set(clients.values()) not in (BASE_PROVIDERS, SUPPORTED_PROVIDERS)):
            raise ValueError('Pin distinct OAuth client IDs to GPT and Gemini, optionally Codex')
        self.clients, self.subject = dict(clients), subject
        self.keys = key_client or jwt.PyJWKClient(self.issuer + '.well-known/jwks.json', timeout=5)

    async def verify_token(self, token):
        try:
            if len(token) > 16384: return None
            key = await anyio.to_thread.run_sync(self.keys.get_signing_key_from_jwt, token)
            data = jwt.decode(token, key.key, algorithms=['RS256'], audience=self.resource,
                issuer=self.issuer, options={'require': ['exp','iat','iss','sub','aud','azp']})
            scopes, subject, client = data.get('scope'), data.get('sub'), data.get('azp')
            if (not isinstance(subject, str) or not hmac.compare_digest(subject.encode(), self.subject.encode())
                    or client not in self.clients or not isinstance(scopes, str) or READ not in scopes.split()):
                return None
            return AccessToken(token=token, client_id=client, scopes=scopes.split(), expires_at=data['exp'],
                subject=subject, resource=self.resource, claims={'provider': self.clients[client]})
        except (jwt.PyJWTError, ValueError, TypeError, OSError):
            return None


class GatewayTools:
    def __init__(self, app, campaign_id, subject, writes=False, guard=None, *, local_reads=False):
        if set(app.gateways) != {campaign_id} or not subject:
            raise ValueError("Bind one staging campaign and an authorized owner subject")
        self.app, self.campaign_id, self.subject, self.writes = app, campaign_id, subject, writes
        self.local_reads = local_reads
        self.guard = guard or for_gateway(app.gateways[campaign_id])

    def authorize(self, write=False):
        token = get_access_token()
        if (not token or token.subject != self.subject or READ not in token.scopes
                or not token.expires_at or token.expires_at <= time.time()
                or (token.claims or {}).get("provider") not in SUPPORTED_PROVIDERS):
            raise Refused("UNAUTHORIZED", "An authorized Genesis account is required")
        if write and not self.writes:
            raise Refused("WRITES_DISABLED", "GM writes require explicit host opt-in")
        if write and GM not in token.scopes:
            raise Refused("INSUFFICIENT_SCOPE", "GM writes require genesis:gm scope")
        return token

    def gm_scope_probe(self):
        """Read-only OAuth step-up probe; never lease, roll or access GM context."""
        token = self.authorize()
        if GM not in token.scopes:
            raise Refused("INSUFFICIENT_SCOPE", "GM authorization requires genesis:gm")
        blockers = self.write_blockers(token, self.guard.recovery_reason)
        return {"connection_provider": token.claims["provider"], "gm_scope_granted": True,
                "gm_write_ready": not bool(blockers), "gm_write_blockers": blockers}

    def write_blockers(self, token, recovery_reason):
        blockers = []
        if recovery_reason:
            blockers.append("STORAGE_RECOVERY_REQUIRED")
        if not self.writes:
            blockers.append("WRITES_DISABLED")
        if GM not in token.scopes:
            blockers.append("INSUFFICIENT_SCOPE")
        if not self.app.gm_tokens.get(token.claims["provider"]):
            blockers.append("PROVIDER_NOT_CONFIGURED")
        return blockers

    def read(self, kind, value=None, *, include_full_state=False, known_revision=None, known_ledger_head=None, known_public_sha256=None):
        token = self.authorize()
        gateway = self.app.gateways[self.campaign_id]
        snapshot = gateway.store.local_snapshot() if self.local_reads else nullcontext()
        with self.guard, snapshot:
            if kind == "refresh":
                # No claim, renewal, table acceptance, recovery mutation or publication.
                sync = getattr(gateway.store, "sync", None)
                if sync:
                    sync(force=True)
                public = gateway.public_state()
                recovery = gateway.recovery()
                if (public["cursor"]["revision"], public["cursor"]["ledger_head"]) != (recovery["revision"], recovery["ledger_head"]):
                    raise Refused("REFRESH_MOVED", "Campaign moved during refresh; repeat the read")
                sha = _public_sha256(public['state'])
                cursor = dict(public['cursor'], public_sha256=sha)
                if known_revision is not None and known_revision > cursor['revision']:
                    raise Refused('CURSOR_AHEAD', 'Refresh cursor is ahead of authority')
                if known_revision == cursor['revision'] and known_ledger_head and known_ledger_head != cursor['ledger_head']:
                    raise Refused('CURSOR_MISMATCH', 'Refresh revision and ledger head disagree')
                if known_public_sha256:
                    changed = known_public_sha256 != sha
                elif known_revision is not None and known_ledger_head:
                    changed = (known_revision, known_ledger_head) != (cursor['revision'], cursor['ledger_head'])
                else: changed = True
                view = {k: public[k] for k in ('pages','routing','in_flight')}
                view.update(cursor=cursor, summary=_compact_state(public['state']))
                if include_full_state: view['state'] = public['state']
                recovery_reason = self.guard.recovery_reason
                blockers = self.write_blockers(token, recovery_reason)
                return {'audience':'player', 'public':view, 'recovery':recovery, 'changed':changed,
                    'connection_provider':token.claims['provider'], 'read_only':bool(blockers),
                    'storage_generation':self.guard.generation, 'storage_recovery_required':recovery_reason is not None,
                    'storage_recovery_reason':recovery_reason, 'gm_write_blockers':blockers}
            if kind == "page":
                if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
                    raise Refused("BAD_PAGE", "Use a page ID advertised by refresh")
                return {"audience": "player", "page": gateway.page(value)}
            if kind == "reference" and value in REFERENCES:
                return {"reference": value, "path": REFERENCES[value], "text": (ROOT / REFERENCES[value]).read_text()}
            raise Refused("BAD_REFERENCE", "Use an advertised reference name")

    def gm(self, verb, run, body=None, model=None, session=None):
        token = self.authorize(write=True)
        provider = token.claims["provider"]
        if not self.app.gm_tokens.get(provider):
            raise Refused("PROVIDER_NOT_CONFIGURED", "Server-held GM token is not configured for this authorized client")
        if verb not in {"claim", "context", "tables", "roll", "review", "commit", "publish", "release"}:
            raise Refused("BAD_VERB", "Unsupported GM operation")
        if not isinstance(run, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run):
            raise Refused("BAD_RUN", "Use one stable run ID per authorized GM attempt")
        with self.guard:
            if self.guard.recovery_required:
                raise Refused("STORAGE_RECOVERY_REQUIRED", "Stop and have the operator reconcile the authority worktree generation")
            # Reuse the exact existing token-scoped HTTP transport handler.
            status, payload = self.app.gm("POST", self.campaign_id, provider, verb,
                {"authorization": "Bearer " + self.app.gm_tokens[provider]},
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
            metadata = {"mcp/www_authenticate": [f'Bearer error="insufficient_scope", error_description="Genesis authorization needs these scopes", scope="{scopes}"']}
    except Exception:
        # SDK error formatting must not echo paths, private context or credentials.
        data, failed = {"error": {"code": "GATEWAY_UNAVAILABLE", "message": "Stop and inspect server-side recovery; do not reroll"}}, True
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(data, ensure_ascii=False))],
                          structuredContent=data, isError=failed, _meta=metadata)


def create_server(tools, verifier, issuer, resource, host="127.0.0.1", port=8789):
    resource, issuer = https_url(resource), https_url(issuer)
    if urlsplit(resource).path != "/mcp":
        raise ValueError("The MCP resource URL must end in /mcp at the origin root")
    mcp = GenesisFastMCP("Genesis shared mobile staging", instructions=(
        "You are the GM; this service does not call a model. Start with genesis_refresh and the reference tools. "
        "Claim only a player-authorized pending request routed to your authenticated provider. Use one run ID, accepted tables and rolls. "
        "Never reroll, change player intent or bypass validation. Context is GM-private; narrate only committed public results. "
        "On Git errors stop; use refresh for recovery. Do not publish private tool output to the player."),
        host=host, port=port, stateless_http=True, json_response=True, max_request_body_size=262144,
        token_verifier=verifier, auth=AuthSettings(issuer_url=issuer, resource_server_url=resource, required_scopes=[READ]),
        transport_security=TransportSecuritySettings(allowed_hosts=[urlsplit(resource).netloc, "127.0.0.1:*", "localhost:*"],
                                                     allowed_origins=["https://chatgpt.com", "https://gemini.google.com", resource.rsplit("/", 1)[0]]))

    def register(name, function, description, readonly=False, destructive=False, require_gm=False):
        scopes = [READ, GM] if require_gm or not readonly else [READ]
        mcp.tool(name=name, description=description, annotations=ToolAnnotations(readOnlyHint=readonly,
                 destructiveHint=destructive, openWorldHint=False),
                 meta={"securitySchemes": [{"type": "oauth2", "scopes": scopes}]})(function)

    def gm_scope_probe() -> CallToolResult:
        return result(lambda: tools.gm_scope_probe())
    def refresh(include_full_state: bool = False, known_revision: int | None = None,
                known_ledger_head: str | None = None, known_public_sha256: str | None = None) -> CallToolResult:
        return result(lambda: tools.read('refresh', include_full_state=include_full_state, known_revision=known_revision,
            known_ledger_head=known_ledger_head, known_public_sha256=known_public_sha256))
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
    register("genesis_gm_scope_probe", gm_scope_probe, "Read-only check of GM scope and write blockers. Triggers OAuth step-up if genesis:gm is missing. No lease, dice, or campaign write.", True, require_gm=True)
    register("genesis_refresh", refresh, "Read public staging state, request status and recovery flags. No lease or turn mutation.", True)
    register("genesis_staging_refresh", refresh, "Same read-only refresh, with public digest and cursor checks for Gemini clients.", True)
    register("genesis_page", page, "Read a public history page ID advertised by genesis_refresh.", True)
    register("genesis_reference", reference, "Read authoritative guidance: " + ", ".join(REFERENCES) + ". No arbitrary file access.", True)
    if tools.writes and not tools.guard.recovery_required:
        register("genesis_claim", claim, "Claim the existing player-authorized request routed to the authenticated client. Persists a lease; no replacement declaration.")
        register("genesis_context", context, "Get GM-private context for the held run. Renews lease and records processing stage; this is a write.")
        register("genesis_tables", tables, "Accept the session GM's interpretation and tables once, before dice. Reuse accepted work.")
        register("genesis_roll", roll, "Ask the deterministic gateway roller for one roll. Repeat identical requests after uncertainty; never choose faces.")
        register("genesis_review", review, "Return a declaration for player clarification before mechanical work is accepted.")
        register("genesis_commit", commit, "Validate and atomically commit the session GM's proposal. Append-only authoritative consequences.", destructive=True)
        register("genesis_publish", publish, "Finish accepted work and paginated public publication; never author a replacement turn.")
        register("genesis_release", release, "Release this run's lease, preserving all accepted tables, dice and recovery records.")
    return mcp


def build(shared, env=None, *, local_reads=False):
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
    verifier = JWTVerifier(issuer, resource, json.loads(env['GENESIS_MCP_CLIENT_PROVIDERS']), env['GENESIS_MCP_SUBJECT'])
    tokens = json.loads(env.get('GENESIS_GM_TOKENS') or '{}')
    app = App({gateway.id: gateway}, {}, None, gm_tokens=tokens)
    writes = env.get('GENESIS_MCP_ENABLE_WRITES') == '1'
    guard = for_gateway(gateway, env.get('GENESIS_STORAGE_GENERATION'),
                        initialize=not writes and not local_reads, require_lock=local_reads)
    tools = GatewayTools(app, gateway.id, env['GENESIS_MCP_SUBJECT'], writes=writes,
                         guard=guard, local_reads=local_reads)
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
