"""Authenticated remote MCP adapter (Streamable HTTP + OAuth 2.1 PKCE) over the Genesis Gateway.

Designed for Google Gemini Custom Connected Apps (https://support.google.com/gemini/answer/17209137)
and Gemini Apps Developer Mode (https://developers.google.com/connected-apps/mcp/dev-mode/usage)
so the player can use the native Gemini mobile app in conversation while Gemini itself acts as the
session GM (`gemini-session`) with the owner's desktop powered off.

Architecture guarantees:
  * Zero duplicated authority: every tool delegates to the existing `Gateway` methods (`public_state`,
    `recovery`, `page`, `action_status`, `submit`, `select_provider`, `reroute`, `claim`, `context`,
    `review`, `fix_tables`, `roll`, `commit`, `publish`, `release`).
  * No backend model API: Gemini in the player's conversation performs all GM reasoning (`kind:
    "agent-session"`, provider `gemini-session`). No `generateContent` / API model call is made.
  * Public / private boundary preservation:
      - Read-only (`genesis:read`) and player (`genesis:player`) scopes never access `hidden/`,
        operation records, GM briefs, private tables, DCs, or seeds.
      - When `read_only=True` (`--read-only` or `GENESIS_MCP_READ_ONLY=1`), only read-only tools are
        exposed and any mutating or GM-private tool call is refused before touching the gateway.
      - GM context (`genesis_gm_context`) requires `genesis:gm` scope and an active lease held by
        `gemini-session`, preserves the gateway's bounded context (`brief.compact` + last 12 private
        events), and attaches an explicit boundary notice; the gateway's `PRIVATE_LEAK` and
        `PURPOSE_LEAK` validators enforce that private data never enters public narration or events.
"""
import base64
import hashlib
import hmac
import html
import json
from pathlib import Path
import secrets
import subprocess
import threading
import time
import urllib.parse

from gateway import Refused
from git_errors import GitFailure
from store import Conflict

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
UI = ROOT / "campaigns/starwars_litrpg/ui/turn_contract.js"

SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
DEFAULT_PROTOCOL = "2025-03-26"
SCOPES_ALL = ("genesis:read", "genesis:player", "genesis:gm")
SCOPES_READ_ONLY = ("genesis:read",)


def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_decode(text: str) -> bytes:
    pad = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode((text + pad).encode("ascii"))


def _pkce_s256(verifier: str) -> str:
    return _b64u_encode(hashlib.sha256(verifier.encode("ascii")).digest())


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


class OAuthServer:
    """Self-contained OAuth 2.1 Authorization Server with PKCE (S256) and signed stateless tokens."""

    def __init__(self, signing_key: str, *, read_token=None, player_token=None, gm_tokens=None,
                 oauth_secret=None, client_id=None, client_secret=None, read_only=False, clock=time.time):
        self.read_token = read_token
        self.player_token = player_token
        self.gm_tokens = dict(gm_tokens or {})
        self.oauth_secret = oauth_secret
        self.client_id = client_id
        self.client_secret = client_secret
        self.read_only = bool(read_only)
        self.clock = clock
        seed = signing_key or oauth_secret or self.gm_tokens.get("gemini-session") or player_token or read_token or secrets.token_hex(32)
        self._key = hashlib.sha256(("genesis-mcp-oauth:" + seed).encode("utf-8")).digest()
        self._used_codes = {}
        self._lock = threading.Lock()

    def _sign(self, payload: dict) -> str:
        body = _b64u_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        sig = _b64u_encode(hmac.new(self._key, body.encode("ascii"), hashlib.sha256).digest())
        return f"{body}.{sig}"

    def _verify(self, token: str, expected_use: str):
        if not isinstance(token, str) or "." not in token:
            return None
        body, _, sig = token.partition(".")
        expected_sig = _b64u_encode(hmac.new(self._key, body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(sig.encode("ascii"), expected_sig.encode("ascii")):
            return None
        try:
            payload = json.loads(_b64u_decode(body).decode("utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict) or payload.get("use") != expected_use:
            return None
        now = int(self.clock())
        if payload.get("exp", 0) <= now:
            return None
        return payload

    def _allowed_scopes_for_secret(self, supplied: str):
        if not supplied:
            return None
        supplied_bytes = supplied.encode("utf-8")
        gm_tok = self.gm_tokens.get("gemini-session")
        if self.oauth_secret and hmac.compare_digest(supplied_bytes, self.oauth_secret.encode("utf-8")):
            return list(SCOPES_READ_ONLY if self.read_only else SCOPES_ALL)
        if gm_tok and hmac.compare_digest(supplied_bytes, gm_tok.encode("utf-8")):
            return list(SCOPES_READ_ONLY if self.read_only else SCOPES_ALL)
        if self.player_token and hmac.compare_digest(supplied_bytes, self.player_token.encode("utf-8")):
            return ["genesis:read"] if self.read_only else ["genesis:read", "genesis:player"]
        if self.read_token and hmac.compare_digest(supplied_bytes, self.read_token.encode("utf-8")):
            return ["genesis:read"]
        return None

    def authenticate_bearer(self, auth_header: str):
        """Validate `Authorization: Bearer <token>` and return `{scopes, provider, subject}` or None."""
        if not isinstance(auth_header, str) or not auth_header.lower().startswith("bearer "):
            return None
        token = auth_header[7:].strip()
        if not token:
            return None
        # 1. Check direct configured static tokens
        direct_scopes = self._allowed_scopes_for_secret(token)
        if direct_scopes is not None:
            return {
                "scopes": set(direct_scopes),
                "provider": "gemini-session",
                "subject": "static-token",
            }
        # 2. Check OAuth 2.1 signed access token
        claims = self._verify(token, "access")
        if not claims:
            return None
        scopes = set(claims.get("scope", "").split())
        if self.read_only:
            scopes &= set(SCOPES_READ_ONLY)
        else:
            scopes &= set(SCOPES_ALL)
        if not scopes:
            return None
        return {
            "scopes": scopes,
            "provider": claims.get("provider") or "gemini-session",
            "subject": claims.get("sub") or "gemini-connected-app",
        }

    def protected_resource_metadata(self, base_url: str) -> dict:
        scopes = list(SCOPES_READ_ONLY if self.read_only else SCOPES_ALL)
        return {
            "resource": base_url.rstrip("/") + "/mcp",
            "authorization_servers": [base_url.rstrip("/")],
            "bearer_methods_supported": ["header"],
            "scopes_supported": scopes,
            "resource_documentation": "https://github.com/AustinFnFordham/Genesis-Protocol-Dev",
        }

    def authorization_server_metadata(self, base_url: str) -> dict:
        root = base_url.rstrip("/")
        scopes = list(SCOPES_READ_ONLY if self.read_only else SCOPES_ALL)
        return {
            "issuer": root,
            "authorization_endpoint": root + "/oauth/authorize",
            "token_endpoint": root + "/oauth/token",
            "registration_endpoint": root + "/oauth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic", "none"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": scopes,
        }

    def register_client(self, body: bytes):
        try:
            data = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return 400, {"error": "invalid_client_metadata", "error_description": "body must be JSON"}
        if not isinstance(data, dict):
            return 400, {"error": "invalid_client_metadata", "error_description": "body must be a JSON object"}
        uris = data.get("redirect_uris") or []
        if not isinstance(uris, list) or not uris or not all(isinstance(u, str) and self._valid_redirect_uri(u) for u in uris):
            return 400, {"error": "invalid_redirect_uri", "error_description": "redirect_uris must be valid HTTPS or localhost URLs"}
        now = int(self.clock())
        cid = "genesis-client-" + secrets.token_hex(8)
        csecret = self._sign({"use": "client", "cid": cid, "uris": uris, "iat": now, "exp": now + 365 * 86400})
        return 201, {
            "client_id": cid,
            "client_secret": csecret,
            "client_id_issued_at": now,
            "client_secret_expires_at": 0,
            "redirect_uris": uris,
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": data.get("token_endpoint_auth_method", "client_secret_post"),
            "client_name": str(data.get("client_name") or "Gemini Connected App")[:120],
        }

    @staticmethod
    def _valid_redirect_uri(uri: str) -> bool:
        try:
            parsed = urllib.parse.urlparse(uri)
        except Exception:
            return False
        if parsed.scheme == "https" and bool(parsed.netloc):
            return True
        if parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost"):
            return True
        return False

    def authorize_get(self, query: dict) -> tuple:
        check = self._validate_authorize_params(query)
        if check[0] != 200:
            return check
        params = check[1]
        scopes_label = ", ".join(params["requested_scopes"])
        page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Genesis Protocol — Connect Gemini</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 440px; margin: 2rem auto; padding: 1.25rem; background: #0f141c; color: #e8edf5; }}
    .card {{ background: #18202c; border: 1px solid #2b384e; border-radius: 10px; padding: 1.25rem; }}
    label {{ display: block; margin-top: 0.75rem; font-weight: 600; font-size: 0.9rem; }}
    input[type=password], select {{ width: 100%; box-sizing: border-box; margin-top: 0.35rem; padding: 0.6rem; border-radius: 6px; border: 1px solid #3c4d69; background: #0f141c; color: #fff; }}
    button {{ margin-top: 1rem; width: 100%; padding: 0.7rem; border: 0; border-radius: 6px; background: #3b82f6; color: #fff; font-weight: 600; cursor: pointer; }}
    .meta {{ font-size: 0.82rem; color: #94a3b8; margin-top: 0.5rem; word-break: break-all; }}
  </style>
</head>
<body>
  <div class="card">
    <h2>Authorize Gemini Connected App</h2>
    <div class="meta">Client: {html.escape(params["client_id"])}</div>
    <div class="meta">Redirect: {html.escape(params["redirect_uri"])}</div>
    <div class="meta">Requested scopes: {html.escape(scopes_label)}</div>
    <form method="post" action="/oauth/authorize">
      <input type="hidden" name="response_type" value="code">
      <input type="hidden" name="client_id" value="{html.escape(params["client_id"])}">
      <input type="hidden" name="redirect_uri" value="{html.escape(params["redirect_uri"])}">
      <input type="hidden" name="code_challenge" value="{html.escape(params["code_challenge"])}">
      <input type="hidden" name="code_challenge_method" value="S256">
      <input type="hidden" name="state" value="{html.escape(params["state"])}">
      <input type="hidden" name="scope" value="{html.escape(" ".join(params["requested_scopes"]))}">
      <label for="secret">Genesis Authorization Key</label>
      <input id="secret" name="secret" type="password" required autocomplete="off" placeholder="Enter GENESIS_OAUTH_SECRET or token">
      <button type="submit">Approve &amp; Connect</button>
    </form>
  </div>
</body>
</html>"""
        return 200, page.encode("utf-8"), {"content-type": "text/html; charset=utf-8"}

    def authorize_post(self, headers: dict, body: bytes) -> tuple:
        ctype = (headers.get("content-type") or "").lower()
        if "application/json" in ctype:
            try:
                form = json.loads(body or b"{}")
            except json.JSONDecodeError:
                return 400, {"error": "invalid_request", "error_description": "invalid JSON"}
        else:
            parsed = urllib.parse.parse_qs((body or b"").decode("utf-8", "replace"), keep_blank_values=True)
            form = {k: v[0] for k, v in parsed.items()}
        check = self._validate_authorize_params(form)
        if check[0] != 200:
            return check
        params = check[1]
        supplied_secret = form.get("secret") or ""
        if not supplied_secret and headers.get("authorization", "").lower().startswith("bearer "):
            supplied_secret = headers["authorization"][7:].strip()
        allowed = self._allowed_scopes_for_secret(supplied_secret)
        if not allowed:
            return 401, {"error": "access_denied", "error_description": "invalid Genesis authorization key"}
        granted = [s for s in params["requested_scopes"] if s in allowed]
        if not granted:
            granted = ["genesis:read"] if "genesis:read" in allowed else []
        if not granted:
            return 403, {"error": "insufficient_scope", "error_description": "key does not grant the requested scope"}
        now = int(self.clock())
        jti = secrets.token_hex(12)
        code = self._sign({
            "use": "code",
            "jti": jti,
            "cid": params["client_id"],
            "uri": params["redirect_uri"],
            "cc": params["code_challenge"],
            "scope": " ".join(granted),
            "provider": "gemini-session",
            "iat": now,
            "exp": now + 300,
        })
        sep = "&" if "?" in params["redirect_uri"] else "?"
        qs = urllib.parse.urlencode({"code": code, **({"state": params["state"]} if params["state"] else {})})
        location = f"{params['redirect_uri']}{sep}{qs}"
        return 302, {"status": "redirect", "location": location}, {"location": location}

    def _validate_authorize_params(self, raw: dict) -> tuple:
        if raw.get("response_type") != "code":
            return 400, {"error": "unsupported_response_type", "error_description": "response_type must be code"}
        client_id = str(raw.get("client_id") or "").strip()
        if not client_id:
            return 400, {"error": "invalid_request", "error_description": "client_id is required"}
        if self.client_id and client_id != self.client_id and not client_id.startswith("genesis-client-"):
            return 400, {"error": "unauthorized_client", "error_description": "unknown client_id"}
        redirect_uri = str(raw.get("redirect_uri") or "").strip()
        if not self._valid_redirect_uri(redirect_uri):
            return 400, {"error": "invalid_request", "error_description": "redirect_uri must use HTTPS (or localhost for local testing)"}
        code_challenge = str(raw.get("code_challenge") or "").strip()
        method = str(raw.get("code_challenge_method") or "S256").strip()
        if not code_challenge or method != "S256":
            return 400, {"error": "invalid_request", "error_description": "PKCE code_challenge with S256 is required by OAuth 2.1"}
        raw_scope = str(raw.get("scope") or "").strip()
        default_scopes = list(SCOPES_READ_ONLY if self.read_only else SCOPES_ALL)
        requested = [s for s in raw_scope.split() if s in SCOPES_ALL] if raw_scope else default_scopes
        if not requested:
            requested = default_scopes
        return 200, {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "state": str(raw.get("state") or ""),
            "requested_scopes": requested,
        }

    def token(self, headers: dict, body: bytes) -> tuple:
        ctype = (headers.get("content-type") or "").lower()
        if "application/json" in ctype:
            try:
                data = json.loads(body or b"{}")
            except json.JSONDecodeError:
                return 400, {"error": "invalid_request", "error_description": "invalid JSON"}
        else:
            parsed = urllib.parse.parse_qs((body or b"").decode("utf-8", "replace"), keep_blank_values=True)
            data = {k: v[0] for k, v in parsed.items()}
        if not isinstance(data, dict):
            return 400, {"error": "invalid_request", "error_description": "invalid payload"}

        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        auth = headers.get("authorization") or ""
        if auth.lower().startswith("basic "):
            try:
                decoded = base64.b64decode(auth[6:].strip()).decode("utf-8")
                basic_id, _, basic_secret = decoded.partition(":")
                client_id = client_id or urllib.parse.unquote(basic_id)
                client_secret = client_secret or urllib.parse.unquote(basic_secret)
            except Exception:
                return 401, {"error": "invalid_client", "error_description": "malformed Basic authorization header"}

        if self.client_secret and client_id == self.client_id:
            if not client_secret or not hmac.compare_digest(client_secret.encode("utf-8"), self.client_secret.encode("utf-8")):
                return 401, {"error": "invalid_client", "error_description": "invalid client_secret"}

        grant_type = data.get("grant_type")
        now = int(self.clock())
        if grant_type == "authorization_code":
            code = str(data.get("code") or "")
            verifier = str(data.get("code_verifier") or "")
            redirect_uri = str(data.get("redirect_uri") or "")
            if not code or not verifier:
                return 400, {"error": "invalid_request", "error_description": "code and code_verifier are required"}
            claims = self._verify(code, "code")
            if not claims:
                return 400, {"error": "invalid_grant", "error_description": "invalid or expired authorization code"}
            with self._lock:
                self._prune_codes(now)
                if claims["jti"] in self._used_codes:
                    return 400, {"error": "invalid_grant", "error_description": "authorization code already used"}
                self._used_codes[claims["jti"]] = claims["exp"]
            if client_id and claims.get("cid") != client_id:
                return 400, {"error": "invalid_grant", "error_description": "client_id mismatch"}
            if redirect_uri and claims.get("uri") != redirect_uri:
                return 400, {"error": "invalid_grant", "error_description": "redirect_uri mismatch"}
            if not hmac.compare_digest(_pkce_s256(verifier).encode("ascii"), claims.get("cc", "").encode("ascii")):
                return 400, {"error": "invalid_grant", "error_description": "PKCE code_verifier verification failed"}
            scope = claims.get("scope") or "genesis:read"
            if self.read_only:
                scope = "genesis:read"
            return 200, self._issue_tokens(claims["cid"], scope, claims.get("provider", "gemini-session"), now)

        if grant_type == "refresh_token":
            rt = str(data.get("refresh_token") or "")
            claims = self._verify(rt, "refresh")
            if not claims:
                return 400, {"error": "invalid_grant", "error_description": "invalid or expired refresh_token"}
            if client_id and claims.get("cid") != client_id:
                return 400, {"error": "invalid_grant", "error_description": "client_id mismatch"}
            scope = claims.get("scope") or "genesis:read"
            if self.read_only:
                scope = "genesis:read"
            return 200, self._issue_tokens(claims["cid"], scope, claims.get("provider", "gemini-session"), now)

        return 400, {"error": "unsupported_grant_type", "error_description": "grant_type must be authorization_code or refresh_token"}

    def _issue_tokens(self, client_id: str, scope: str, provider: str, now: int) -> dict:
        access = self._sign({
            "use": "access",
            "sub": client_id,
            "scope": scope,
            "provider": provider,
            "iat": now,
            "exp": now + 3600,
            "jti": secrets.token_hex(8),
        })
        refresh = self._sign({
            "use": "refresh",
            "cid": client_id,
            "scope": scope,
            "provider": provider,
            "iat": now,
            "exp": now + 30 * 86400,
            "jti": secrets.token_hex(8),
        })
        return {
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": refresh,
            "scope": scope,
        }

    def _prune_codes(self, now: int):
        expired = [k for k, exp in self._used_codes.items() if exp <= now]
        for k in expired:
            self._used_codes.pop(k, None)


class MCPAdapter:
    """MCP Streamable HTTP adapter backed strictly by `Gateway`."""

    def __init__(self, gateways: dict, oauth: OAuthServer, *, public_base_url=None, read_only=False, gm_provider_id="gemini-session"):
        self.gateways = gateways
        self.oauth = oauth
        self.public_base_url = (public_base_url or "http://127.0.0.1:8787").rstrip("/")
        self.read_only = bool(read_only)
        self.gm_provider_id = gm_provider_id
        self._sessions = {}
        self._lock = threading.Lock()

    def base_url_for(self, headers: dict) -> str:
        if self.public_base_url and not self.public_base_url.startswith("http://127.0.0.1"):
            return self.public_base_url
        proto = headers.get("x-forwarded-proto") or "http"
        host = headers.get("x-forwarded-host") or headers.get("host")
        if host:
            return f"{proto}://{host}".rstrip("/")
        return self.public_base_url

    def www_authenticate(self, headers: dict) -> str:
        base = self.base_url_for(headers)
        return f'Bearer realm="genesis-mcp", resource_metadata="{base}/.well-known/oauth-protected-resource"'

    def _default_campaign_id(self, requested=None) -> str:
        if requested:
            if requested not in self.gateways:
                raise Refused("NO_SUCH_CAMPAIGN", f"unknown campaign {requested}", campaigns=sorted(self.gateways))
            return requested
        if len(self.gateways) == 1:
            return next(iter(self.gateways))
        raise Refused("CAMPAIGN_REQUIRED", "specify campaign_id", campaigns=sorted(self.gateways))

    def _gateway(self, arguments: dict):
        cid = self._default_campaign_id((arguments or {}).get("campaign_id"))
        return cid, self.gateways[cid]

    def tools_for_principal(self, principal: dict) -> list:
        scopes = principal["scopes"]
        tools = [
            {
                "name": "genesis_staging_refresh",
                "title": "Refresh Genesis Staging State (Read-Only)",
                "description": (
                    "Read-only authoritative refresh of the Genesis campaign state and recovery status. "
                    "Returns cursor (revision, ledger_head, context_id, public_sha256), recovery (in_flight action, "
                    "routed provider, phase, mechanical acceptance flags, lease status), provider routing, and "
                    "a bounded summary of scene, character, turn_context options, and recent feed. "
                    "Never opens hidden/ and never mutates campaign or queue state."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "string", "description": "Campaign identifier (optional when only one campaign is hosted, e.g. shared-1)."},
                        "known_revision": {"type": "integer", "description": "Optional previously seen revision number to check if public state changed."},
                        "known_ledger_head": {"type": "string", "description": "Optional previously seen ledger head event ID."},
                        "known_public_sha256": {"type": "string", "description": "Optional previously seen public_sha256 digest."},
                        "include_full_state": {"type": "boolean", "description": "Set true to include the full raw view/state document in addition to the bounded summary."},
                    },
                    "additionalProperties": False,
                },
                "annotations": {
                    "title": "Refresh Genesis Staging State",
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "genesis_get_page",
                "title": "Read Public Campaign History Page",
                "description": "Read one public history page (e.g. feed-0001, journal-0001, chapters-0001, dice-0001) from the published campaign view. Read-only.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "string", "description": "Page name from the state.pages manifest (e.g. feed-0001)."},
                        "campaign_id": {"type": "string", "description": "Optional campaign identifier."},
                    },
                    "required": ["page"],
                    "additionalProperties": False,
                },
                "annotations": {
                    "title": "Read Public History Page",
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "genesis_get_action",
                "title": "Read Action Status & Mechanical Progress",
                "description": "Read the player-safe status and mechanical acceptance flags (tables_fixed, rolls_accepted, batch_accepted, batch_committed, fingerprint) for an action_id. Read-only.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action_id": {"type": "string", "description": "Action identifier (e.g. shared-0001 or shared-0002)."},
                        "campaign_id": {"type": "string", "description": "Optional campaign identifier."},
                    },
                    "required": ["action_id"],
                    "additionalProperties": False,
                },
                "annotations": {
                    "title": "Read Action Status",
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
            {
                "name": "genesis_gm_guide",
                "title": "Read Authoritative Genesis GM Guide & Session Rules",
                "description": "Read the authoritative Genesis GM Guide (GM_GUIDE.md) and Session GM procedure (SESSION_GM.md). Read-only.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                "annotations": {
                    "title": "Read Genesis GM Guide",
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            },
        ]

        if self.read_only:
            return tools

        if "genesis:player" in scopes or "genesis:gm" in scopes:
            tools.extend([
                {
                    "name": "genesis_submit_action",
                    "title": "Submit Player Declaration",
                    "description": (
                        "Validate and queue one player declaration against the current campaign cursor (based_on_revision, "
                        "ledger_head, context_id). Uses turn_contract.js to parse/validate and Gateway.submit to queue. "
                        "Idempotent on action_id; refuses stale revisions or when another turn is in flight."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "action_id": {"type": "string", "description": "Unique idempotency key (6-64 chars, letters/digits/-/_)."},
                            "based_on_revision": {"type": "integer", "description": "Current revision from genesis_staging_refresh.cursor.revision."},
                            "ledger_head": {"type": "string", "description": "Current ledger_head from genesis_staging_refresh.cursor.ledger_head."},
                            "context_id": {"type": "string", "description": "Current context_id from genesis_staging_refresh.cursor.context_id."},
                            "text": {"type": "string", "description": "Player's freeform declaration text."},
                            "steps": {"type": "array", "items": {"type": "object"}, "description": "Optional structured composer steps."},
                            "actor": {"type": "string", "description": "Active player character ID (default: aero)."},
                            "gm_provider": {"type": "string", "description": "Optional target GM provider (e.g. gemini-session)."},
                            "confirmed_warnings": {"type": "boolean", "description": "Set true if player confirmed preflight warnings."},
                            "resolution_settings": {"type": "object", "description": "Optional dice resolution settings."},
                            "campaign_id": {"type": "string", "description": "Optional campaign identifier."},
                        },
                        "required": ["action_id", "based_on_revision", "ledger_head", "context_id"],
                        "additionalProperties": False,
                    },
                    "annotations": {
                        "title": "Submit Player Declaration",
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                    },
                },
                {
                    "name": "genesis_select_provider",
                    "title": "Select Default GM Provider",
                    "description": "Choose the GM provider for future declarations (e.g. gemini-session, gpt-session, claude-session). Does not reroute an in-flight turn.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "provider": {"type": "string", "description": "Provider identifier (e.g. gemini-session)."},
                            "campaign_id": {"type": "string", "description": "Optional campaign identifier."},
                        },
                        "required": ["provider"],
                        "additionalProperties": False,
                    },
                    "annotations": {
                        "title": "Select Default GM Provider",
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                    },
                },
                {
                    "name": "genesis_reroute_action",
                    "title": "Explicitly Reroute In-Flight Action",
                    "description": "Explicitly hand an unfinished in-flight action to another provider. Refused with PROVIDER_BUSY while a live lease is held.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "action_id": {"type": "string", "description": "In-flight action ID."},
                            "provider": {"type": "string", "description": "Target provider ID (e.g. gemini-session)."},
                            "campaign_id": {"type": "string", "description": "Optional campaign identifier."},
                        },
                        "required": ["action_id", "provider"],
                        "additionalProperties": False,
                    },
                    "annotations": {
                        "title": "Reroute In-Flight Action",
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                    },
                },
            ])

        if "genesis:gm" in scopes:
            tools.extend([
                {
                    "name": "genesis_gm_claim",
                    "title": "Claim Routed Turn as Gemini Session GM",
                    "description": (
                        "Claim the campaign lease for the in-flight action routed to `gemini-session`. "
                        "Refuses with NOT_ROUTED_HERE if the action is routed to another provider (such as gpt-session), "
                        "and refuses with PROVIDER_BUSY if another run holds an unexpired lease."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "run": {"type": "string", "description": "Unique run identifier for this GM turn execution (e.g. gemini-session-1)."},
                            "model": {"type": "string", "description": "Truthful model name/version performing GM reasoning in this conversation."},
                            "session": {"type": "string", "description": "Conversation or session identifier for audit attestation."},
                            "campaign_id": {"type": "string", "description": "Optional campaign identifier."},
                        },
                        "required": ["run", "model"],
                        "additionalProperties": False,
                    },
                    "annotations": {
                        "title": "Claim GM Turn Lease",
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "idempotentHint": False,
                        "openWorldHint": False,
                    },
                },
                {
                    "name": "genesis_gm_context",
                    "title": "Read Bounded GM-Private Turn Context",
                    "description": (
                        "Load the bounded GM context (action, preflight validation, public_context, compact GM brief, "
                        "last 12 private events, npc_last_evaluations, resolution settings, and accepted operation state) "
                        "for a turn currently claimed by `gemini-session`. Private fields must never be leaked to the player."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "run": {"type": "string", "description": "Active run ID holding the lease."},
                            "campaign_id": {"type": "string", "description": "Optional campaign identifier."},
                        },
                        "required": ["run"],
                        "additionalProperties": False,
                    },
                    "annotations": {
                        "title": "Read Bounded GM Context",
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                    },
                },
                {
                    "name": "genesis_gm_review",
                    "title": "Return Declaration for Player Revision",
                    "description": "Send a declaration that cannot start back to the player with coded errors and validated alternatives. Only allowed before tables or rolls are accepted.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "run": {"type": "string", "description": "Active run ID holding the lease."},
                            "review": {
                                "type": "object",
                                "description": "Review object {summary, errors: [{code, message}], warnings: [], alternatives: [{label, declaration}]}.",
                            },
                            "campaign_id": {"type": "string", "description": "Optional campaign identifier."},
                        },
                        "required": ["run", "review"],
                        "additionalProperties": False,
                    },
                    "annotations": {
                        "title": "Return Declaration for Revision",
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "idempotentHint": False,
                        "openWorldHint": False,
                    },
                },
                {
                    "name": "genesis_gm_tables",
                    "title": "Fix GM Interpretation, Tables, and NPC Evaluations",
                    "description": "Record the GM's interpretation, odds tables, and npc_evaluations before rolling any die. Immutable once accepted.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "run": {"type": "string", "description": "Active run ID holding the lease."},
                            "tables": {
                                "type": "object",
                                "description": "Object {interpretation: string, tables: string, npc_evaluations: array}.",
                            },
                            "campaign_id": {"type": "string", "description": "Optional campaign identifier."},
                        },
                        "required": ["run", "tables"],
                        "additionalProperties": False,
                    },
                    "annotations": {
                        "title": "Fix GM Tables",
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                    },
                },
                {
                    "name": "genesis_gm_roll",
                    "title": "Request Authoritative Dice Roll",
                    "description": "Request one authoritative roll from the gateway's deterministic dice resolver. Keyed by roll_key; accepted rolls are binding and never rerolled.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "run": {"type": "string", "description": "Active run ID holding the lease."},
                            "roll": {
                                "type": "object",
                                "description": "Roll request {roll_key, step_id, formula, mode, kind, requested_by, purpose, dc, rule_sources}.",
                            },
                            "campaign_id": {"type": "string", "description": "Optional campaign identifier."},
                        },
                        "required": ["run", "roll"],
                        "additionalProperties": False,
                    },
                    "annotations": {
                        "title": "Request Authoritative Dice Roll",
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                    },
                },
                {
                    "name": "genesis_gm_commit",
                    "title": "Validate and Commit GM Turn Proposal",
                    "description": "Validate and commit the GM's turn proposal ({world_time, events, narration, scene_state, turn_context}) through the shared ledger batch and publish the new revision.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "run": {"type": "string", "description": "Active run ID holding the lease."},
                            "proposal": {
                                "type": "object",
                                "description": "Commit proposal {world_time, events, narration, scene_state, turn_context}.",
                            },
                            "campaign_id": {"type": "string", "description": "Optional campaign identifier."},
                        },
                        "required": ["run", "proposal"],
                        "additionalProperties": False,
                    },
                    "annotations": {
                        "title": "Commit GM Turn Proposal",
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                    },
                },
                {
                    "name": "genesis_gm_publish",
                    "title": "Finish Pending Publication",
                    "description": "Finish publishing a resolved action whose ledger batch already committed.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "run": {"type": "string", "description": "Active run ID holding the lease."},
                            "campaign_id": {"type": "string", "description": "Optional campaign identifier."},
                        },
                        "required": ["run"],
                        "additionalProperties": False,
                    },
                    "annotations": {
                        "title": "Finish Pending Publication",
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                    },
                },
                {
                    "name": "genesis_gm_release",
                    "title": "Release GM Lease Without Discarding Accepted Work",
                    "description": "Release the campaign lease cleanly if unable to finish the turn. Any accepted tables or dice rolls remain recorded.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "run": {"type": "string", "description": "Active run ID holding the lease."},
                            "reason": {"type": "string", "description": "Short reason for releasing the lease."},
                            "campaign_id": {"type": "string", "description": "Optional campaign identifier."},
                        },
                        "required": ["run"],
                        "additionalProperties": False,
                    },
                    "annotations": {
                        "title": "Release GM Lease",
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "idempotentHint": True,
                        "openWorldHint": False,
                    },
                },
            ])
        return tools

    def call_tool(self, principal: dict, name: str, arguments: dict) -> dict:
        arguments = arguments if isinstance(arguments, dict) else {}
        scopes = principal["scopes"]
        read_only_tools = {"genesis_staging_refresh", "genesis_get_page", "genesis_get_action", "genesis_gm_guide"}
        player_tools = {"genesis_submit_action", "genesis_select_provider", "genesis_reroute_action"}
        gm_tools = {
            "genesis_gm_claim", "genesis_gm_context", "genesis_gm_review",
            "genesis_gm_tables", "genesis_gm_roll", "genesis_gm_commit",
            "genesis_gm_publish", "genesis_gm_release",
        }

        if name not in (read_only_tools | player_tools | gm_tools):
            raise Refused("UNKNOWN_TOOL", f"unknown MCP tool: {name}")
        if self.read_only and name not in read_only_tools:
            raise Refused("READ_ONLY_MODE", f"tool {name} is disabled because this MCP server is in read-only mode")
        if name in player_tools and not ({"genesis:player", "genesis:gm"} & scopes):
            raise Refused("FORBIDDEN_SCOPE", f"tool {name} requires genesis:player or genesis:gm scope")
        if name in gm_tools and "genesis:gm" not in scopes:
            raise Refused("FORBIDDEN_SCOPE", f"tool {name} requires genesis:gm scope")

        if name == "genesis_gm_guide":
            return {
                "gm_guide": (HERE / "GM_GUIDE.md").read_text(encoding="utf-8"),
                "session_gm": (HERE / "SESSION_GM.md").read_text(encoding="utf-8"),
                "provider_id": self.gm_provider_id,
            }

        campaign_id, gateway = self._gateway(arguments)

        if name == "genesis_staging_refresh":
            pub = gateway.public_state()
            rec = gateway.recovery()
            sha = _public_sha256(pub["state"])
            cursor = dict(pub["cursor"], public_sha256=sha)
            known_rev = arguments.get("known_revision")
            known_head = arguments.get("known_ledger_head")
            known_sha = arguments.get("known_public_sha256")
            if known_rev is not None and known_rev > cursor["revision"]:
                raise Refused("CURSOR_AHEAD", "known_revision is ahead of the authoritative campaign revision",
                              revision=cursor["revision"], ledger_head=cursor["ledger_head"])
            if known_rev is not None and known_rev == cursor["revision"] and known_head and known_head != cursor["ledger_head"]:
                raise Refused("CURSOR_MISMATCH", "known_revision matches but known_ledger_head differs",
                              revision=cursor["revision"], ledger_head=cursor["ledger_head"])
            changed = True
            if known_sha:
                changed = known_sha != sha
            elif known_rev is not None and known_head:
                changed = (known_rev != cursor["revision"]) or (known_head != cursor["ledger_head"])
            result = {
                "campaign_id": campaign_id,
                "read_only": True,
                "changed": changed,
                "cursor": cursor,
                "routing": pub["routing"],
                "recovery": rec,
                "pages": pub["pages"],
                "summary": _compact_state(pub["state"]),
            }
            if arguments.get("include_full_state"):
                result["state"] = pub["state"]
            return result

        if name == "genesis_get_page":
            page_name = str(arguments.get("page") or "").strip()
            if not page_name:
                raise Refused("BAD_PAGE", "page is required")
            return {"campaign_id": campaign_id, "page": page_name, "data": gateway.page(page_name)}

        if name == "genesis_get_action":
            action_id = str(arguments.get("action_id") or "").strip()
            if not action_id:
                raise Refused("BAD_ACTION_ID", "action_id is required")
            return gateway.action_status(action_id)

        if name == "genesis_select_provider":
            return gateway.select_provider(arguments.get("provider"), by="player")

        if name == "genesis_reroute_action":
            return gateway.reroute(arguments.get("action_id"), arguments.get("provider"), by="player")

        if name == "genesis_submit_action":
            return self._submit_action(gateway, arguments)

        # Conversational GM tools (`gemini-session`)
        provider = self.gm_provider_id
        run = str(arguments.get("run") or "").strip()
        if not run:
            raise Refused("BAD_RUN", "run identifier is required")

        if name == "genesis_gm_claim":
            model = str(arguments.get("model") or "").strip()
            if not model:
                raise Refused("BAD_MODEL", "model attestation is required when claiming a GM turn")
            identity = {
                "kind": "agent-session",
                "model": model,
                "session": str(arguments.get("session") or principal.get("subject") or "gemini-mobile-mcp"),
                "mock": False,
            }
            return gateway.claim(provider, run, identity)

        if name == "genesis_gm_context":
            ctx = gateway.context(provider, run)
            return dict(
                ctx,
                _boundary_notice=(
                    "GM-PRIVATE BOUNDARY: `brief`, `recent_private`, hidden NPC positions, DCs, AC, and `operation.tables` "
                    "are strictly GM-only. Use them for your internal adjudication only. Never quote or reveal them in "
                    "player-visible chat messages, `narration`, `turn_context`, public `events`, or roll `purpose` strings."
                ),
            )

        if name == "genesis_gm_review":
            return gateway.review(provider, run, arguments.get("review"))

        if name == "genesis_gm_tables":
            return gateway.fix_tables(provider, run, arguments.get("tables"))

        if name == "genesis_gm_roll":
            return gateway.roll(provider, run, arguments.get("roll"))

        if name == "genesis_gm_commit":
            return gateway.commit(provider, run, arguments.get("proposal"))

        if name == "genesis_gm_publish":
            return gateway.publish(provider, run)

        if name == "genesis_gm_release":
            return gateway.release(provider, run, str(arguments.get("reason") or "released via Gemini MCP session"))

        raise Refused("UNKNOWN_TOOL", f"unhandled tool {name}")

    def _submit_action(self, gateway, arguments: dict) -> dict:
        text = str(arguments.get("text") or "").strip()
        steps = arguments.get("steps")
        if not text and not steps:
            raise Refused("BAD_DECLARATION", "provide text or steps for the declaration")
        pub = gateway.public_state()
        tc = pub["state"].get("turn_context") or {}
        actor = str(arguments.get("actor") or tc.get("actor") or "aero")
        import tempfile
        with tempfile.TemporaryDirectory(prefix="genesis-mcp-decl-") as tmp:
            ctx_path = Path(tmp) / "ctx.json"
            ctx_path.write_text(json.dumps(tc), encoding="utf-8")
            if steps is not None:
                decl = {"actor": actor, "source": "composer", "freeform": text, "unmapped": [], "steps": steps}
                proc = subprocess.run(["node", str(UI), "validate", "-", str(ctx_path)],
                                      input=json.dumps(decl), capture_output=True, text=True, check=True)
                out = json.loads(proc.stdout)
                declaration = out.get("declaration", decl)
            else:
                proc = subprocess.run(["node", str(UI), "parse", text, str(ctx_path)],
                                      capture_output=True, text=True, check=True)
                declaration = json.loads(proc.stdout)["declaration"]
        envelope = {
            "action_id": arguments.get("action_id"),
            "campaign_id": gateway.id,
            "actor": actor,
            "based_on_revision": arguments.get("based_on_revision"),
            "ledger_head": arguments.get("ledger_head"),
            "context_id": arguments.get("context_id"),
            "text": text,
            "declaration": declaration,
            "contract": "turn-contract/3",
            "confirmed_warnings": bool(arguments.get("confirmed_warnings")),
        }
        if arguments.get("gm_provider"):
            envelope["gm_provider"] = arguments["gm_provider"]
        if arguments.get("resolution_settings"):
            envelope["resolution_settings"] = arguments["resolution_settings"]
        return gateway.submit(envelope)

    def handle_http(self, method: str, path: str, query_string: str, headers: dict, body: bytes):
        """Handle OAuth discovery/authorization/token endpoints and Streamable HTTP `/mcp` requests.
        Returns `(status_code, payload_bytes_or_dict, extra_headers)` or `None` if path is not an MCP/OAuth route.
        """
        base = self.base_url_for(headers)

        # 1. RFC 9728 OAuth Protected Resource Metadata
        if method == "GET" and path in (
            "/.well-known/oauth-protected-resource",
            "/.well-known/oauth-protected-resource/mcp",
            "/.well-known/oauth-protected-resource/v1/mcp",
        ):
            return 200, self.oauth.protected_resource_metadata(base), {}

        # 2. RFC 8414 OAuth Authorization Server Metadata / OpenID Configuration
        if method == "GET" and path in (
            "/.well-known/oauth-authorization-server",
            "/.well-known/openid-configuration",
        ):
            return 200, self.oauth.authorization_server_metadata(base), {}

        # 3. RFC 7591 Dynamic Client Registration
        if method == "POST" and path == "/oauth/register":
            code, payload = self.oauth.register_client(body)
            return code, payload, {}

        # 4. OAuth 2.1 Authorization Endpoint (PKCE S256)
        if path == "/oauth/authorize":
            if method == "GET":
                parsed_q = urllib.parse.parse_qs(query_string or "", keep_blank_values=True)
                q = {k: v[0] for k, v in parsed_q.items()}
                result = self.oauth.authorize_get(q)
                if len(result) == 2:
                    return result[0], result[1], {}
                return result
            if method == "POST":
                result = self.oauth.authorize_post(headers, body)
                if len(result) == 2:
                    return result[0], result[1], {}
                return result
            return 405, {"error": "method_not_allowed"}, {"allow": "GET, POST"}

        # 5. OAuth 2.1 Token Endpoint
        if path == "/oauth/token":
            if method != "POST":
                return 405, {"error": "method_not_allowed"}, {"allow": "POST"}
            code, payload = self.oauth.token(headers, body)
            return code, payload, {}

        # 6. Streamable HTTP MCP Endpoint (`/mcp` and `/v1/mcp`)
        if path not in ("/mcp", "/v1/mcp"):
            return None

        principal = self.oauth.authenticate_bearer(headers.get("authorization", ""))
        if not principal:
            return 401, {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32001, "message": "Unauthorized: valid Bearer token required"},
            }, {"www-authenticate": self.www_authenticate(headers)}

        if method == "DELETE":
            sid = headers.get("mcp-session-id")
            if sid:
                with self._lock:
                    self._sessions.pop(sid, None)
            return 204, b"", {}

        if method == "GET":
            # Per MCP Streamable HTTP specification, servers that respond inline via POST
            # return 405 Method Not Allowed when an unsolicited GET SSE stream is requested.
            return 405, {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32600, "message": "Streamable HTTP POST required"},
            }, {"allow": "POST, DELETE, OPTIONS"}

        if method != "POST":
            return 405, {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32600, "message": "Method not allowed"},
            }, {"allow": "POST, DELETE, OPTIONS"}

        try:
            message = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return 400, {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error: body must be valid JSON"},
            }, {}

        extra_headers = {}
        sid = headers.get("mcp-session-id")
        if sid:
            extra_headers["mcp-session-id"] = sid

        if isinstance(message, list):
            if not message:
                return 400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Empty batch"}}, extra_headers
            responses = []
            for item in message:
                resp, new_sid = self._dispatch_rpc(principal, item)
                if new_sid:
                    extra_headers["mcp-session-id"] = new_sid
                if resp is not None:
                    responses.append(resp)
            if not responses:
                return 202, b"", extra_headers
            return 200, responses, extra_headers

        resp, new_sid = self._dispatch_rpc(principal, message)
        if new_sid:
            extra_headers["mcp-session-id"] = new_sid
        if resp is None:
            return 202, b"", extra_headers
        return 200, resp, extra_headers

    def _dispatch_rpc(self, principal: dict, msg) -> tuple:
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
            return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid JSON-RPC 2.0 message"}}, None

        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params") if isinstance(msg.get("params"), dict) else {}

        # JSON-RPC Notifications (no `id` field)
        if "id" not in msg:
            return None, None

        if not isinstance(method, str):
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32600, "message": "Missing method name"}}, None

        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}, None

        if method == "initialize":
            client_proto = str(params.get("protocolVersion") or DEFAULT_PROTOCOL)
            negotiated = client_proto if client_proto in SUPPORTED_PROTOCOLS else DEFAULT_PROTOCOL
            sid = "mcp-" + secrets.token_hex(12)
            with self._lock:
                self._sessions[sid] = {"created": time.time(), "protocol": negotiated, "sub": principal.get("subject")}
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": negotiated,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "prompts": {"listChanged": False},
                        "resources": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": "genesis-protocol-mcp",
                        "title": "Genesis Protocol GM & Staging Gateway",
                        "version": "1.0.0",
                    },
                    "instructions": (
                        "Genesis Protocol MCP Server. Use `genesis_staging_refresh` for read-only campaign "
                        "and recovery inspection. When acting as Game Master in conversation (`gemini-session`), "
                        "read `genesis_gm_guide` first, never invent dice results, never touch actions routed to "
                        "other providers (such as `gpt-session`), and never leak GM-private context (`brief`, "
                        "`recent_private`, DCs, private tables) into player-visible prose."
                    ),
                },
            }, sid

        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.tools_for_principal(principal)}}, None

        if method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "prompts": [
                        {
                            "name": "genesis_mobile_gm",
                            "title": "Genesis Conversational GM & Staging Refresh Instructions",
                            "description": "Instructions for Gemini in the mobile app to refresh staging or adjudicate a `gemini-session` turn.",
                        }
                    ]
                },
            }, None

        if method == "prompts/get":
            pname = params.get("name")
            if pname != "genesis_mobile_gm":
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": f"Unknown prompt: {pname}"}}, None
            guide_text = (HERE / "GM_GUIDE.md").read_text(encoding="utf-8")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "description": "Genesis Protocol GM Guide for Gemini mobile conversation",
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": (
                                    "You are connected to Genesis Protocol via MCP (`gemini-session`). "
                                    "For a staging refresh, call `genesis_staging_refresh` and report the revision, "
                                    "ledger_head, scene summary, and any in-flight action without claiming or modifying "
                                    "turns routed to other providers (e.g. `gpt-session`).\n\n" + guide_text
                                ),
                            },
                        }
                    ],
                },
            }, None

        if method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "resources": [
                        {
                            "uri": "genesis://guide/gm_guide",
                            "name": "Genesis GM Guide",
                            "mimeType": "text/markdown",
                            "description": "Authoritative provider-neutral GM adjudication guide",
                        },
                        {
                            "uri": "genesis://guide/session_gm",
                            "name": "Genesis Session GM Procedure",
                            "mimeType": "text/markdown",
                            "description": "Session GM rules and procedure",
                        },
                    ]
                },
            }, None

        if method == "resources/read":
            uri = params.get("uri")
            if uri == "genesis://guide/gm_guide":
                text = (HERE / "GM_GUIDE.md").read_text(encoding="utf-8")
            elif uri == "genesis://guide/session_gm":
                text = (HERE / "SESSION_GM.md").read_text(encoding="utf-8")
            else:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": f"Unknown resource URI: {uri}"}}, None
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": text}]},
            }, None

        if method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments") or {}
            if not isinstance(tool_name, str) or not tool_name:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": "Tool name is required"}}, None
            try:
                output = self.call_tool(principal, tool_name, tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False)}],
                        "structuredContent": output,
                        "isError": False,
                    },
                }, None
            except Refused as refusal:
                err_payload = refusal.as_dict()
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(err_payload, ensure_ascii=False)}],
                        "structuredContent": err_payload,
                        "isError": True,
                    },
                }, None
            except GitFailure as failure:
                err_payload = failure.as_dict()
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(err_payload, ensure_ascii=False)}],
                        "structuredContent": err_payload,
                        "isError": True,
                    },
                }, None
            except Conflict:
                err_payload = {"error": {"code": "CONFLICT", "message": "changed concurrently; retry"}}
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(err_payload, ensure_ascii=False)}],
                        "structuredContent": err_payload,
                        "isError": True,
                    },
                }, None
            except ValueError:
                err_payload = {"error": {"code": "CAMPAIGN_BUSY", "message": "the record is mid-write; retry shortly"}}
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(err_payload, ensure_ascii=False)}],
                        "structuredContent": err_payload,
                        "isError": True,
                    },
                }, None

        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}, None
