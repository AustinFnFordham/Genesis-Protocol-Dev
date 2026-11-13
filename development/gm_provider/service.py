"""Player-facing HTTP API for a Genesis campaign, plus the GM worker that runs beside it.

Three separate concerns, three separate places:
  UI hosting        anywhere (the Datapad artifact, a Gemini-hosted app, a static page). It only
                    calls this API with the player token. It never holds a model key.
  model execution   this process's worker (or an agent session using gmctl). Provider keys live in
                    this process's environment only.
  canonical record  the campaign directory in git. The store holds the queue, lease and the
                    published public pages, as the Datapad database does today.

Player routes carry nothing built from hidden/ or from an operation record. GM-session routes exist
only when GENESIS_GM_TOKENS is set and are a transport for the same gateway calls gmctl makes: a
session that can make HTTPS calls but cannot run a shell or git (a hosted assistant with an HTTP
tool) is a GM provider through them. Each provider id has its own token; the player token is never
accepted there and a GM token is never accepted on player routes.

  GET  /v1/health
  GET  /v1/providers
  GET  /v1/campaigns/{id}/state
  GET  /v1/campaigns/{id}/pages/{page}
  POST /v1/campaigns/{id}/provider                 {"provider": "gemini"}
  POST /v1/campaigns/{id}/actions                  the action envelope (see GEMINI_CONNECTION_CONTRACT.md)
  GET  /v1/campaigns/{id}/actions/{action_id}
  POST /v1/campaigns/{id}/actions/{action_id}/reroute   {"provider": "gpt"}
  GET  /v1/campaigns/{id}/recovery                 what is in flight, what was accepted, what may happen next

  POST /v1/gm/{id}/{provider}/claim                {"run", "model", "session"}      (GM token)
  POST /v1/gm/{id}/{provider}/context|publish|release   {"run"}
  POST /v1/gm/{id}/{provider}/tables|roll|review|commit {"run", "body": {...}}

Run:  GENESIS_PLAYER_TOKEN=... python3 service.py serve --campaign DIR --id ID --store FILE [--port 8787] [--autorun]
      python3 service.py work --campaign DIR --id ID --store FILE         (one worker pass)
"""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sys
import threading

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gateway import Gateway, Refused   # noqa: E402
import providers as provider_module    # noqa: E402
from runner import run_turn            # noqa: E402
from store import SqliteStore, Conflict  # noqa: E402

STATUS = {"STALE": 409, "TURN_IN_FLIGHT": 409, "ACTION_ID_REUSED": 409, "PROVIDER_BUSY": 409, "NOT_REROUTABLE": 409,
          "NO_SUCH_ACTION": 404, "NO_SUCH_PAGE": 404, "PROVIDER_NOT_SELECTED": 422, "UNSUPPORTED_SETTINGS": 422}
MAX_BODY = 262144


class App:
    def __init__(self, gateways, providers, token, origin=None, autorun=False, gm_tokens=None):
        self.gateways, self.providers, self.token, self.origin, self.autorun = gateways, providers, token, origin, autorun
        self.gm_tokens = dict(gm_tokens or {})
        self.working = threading.Lock()

    def work(self):
        """One worker pass: run the routed provider for each campaign's in-flight action. Never substitutes."""
        results = []
        with self.working:
            for campaign_id, gateway in self.gateways.items():
                try:
                    item = gateway._in_flight()
                except (Refused, ValueError) as error:
                    results.append({"campaign_id": campaign_id, "outcome": "refused", "error": str(error)[:200]})
                    continue
                if not item:
                    continue
                routed = item[2].get("gm", {}).get("provider")
                provider = self.providers.get(routed)
                if item[2]["status"] == "resolved":
                    provider = provider or next((p for p in self.providers.values() if p.kind != "agent-session"), None)
                if provider is None:
                    if item[2]["status"] == "submitted":
                        gateway.block(item[2]["action_id"], routed, "PROVIDER_NOT_CONFIGURED", f"this worker has no provider named {routed}")
                    results.append({"campaign_id": campaign_id, "outcome": "blocked", "provider": routed})
                    continue
                if provider.kind == "agent-session" and item[2]["status"] != "resolved":
                    results.append({"campaign_id": campaign_id, "outcome": "waiting_for_session", "provider": routed})
                    continue
                results.append(dict(run_turn(gateway, provider), campaign_id=campaign_id, provider=provider.id))
        return results

    def matrix(self):
        return [{k: v for k, v in row.items() if k != "endpoint"} for row in provider_module.matrix(self.providers)]

    def handle(self, method, path, headers, body):
        if method == "GET" and path == "/v1/health":
            return 200, {"ok": True}
        if method == "GET" and path == "/v1/providers":
            return 200, {"providers": self.matrix()}
        gm = re.match(r"^/v1/gm/([A-Za-z0-9_-]{1,64})/([a-z][a-z0-9_-]{1,39})/(claim|context|tables|roll|review|commit|publish|release)$", path)
        if gm:
            return self.gm(method, gm.group(1), gm.group(2), gm.group(3), headers, body)
        match = re.match(r"^/v1/campaigns/([A-Za-z0-9_-]{1,64})(/.*)?$", path)
        if not match:
            return 404, {"error": {"code": "NOT_FOUND", "message": "unknown path"}}
        supplied = headers.get("authorization", "")
        if not self.token or not hmac.compare_digest(supplied.encode(), ("Bearer " + self.token).encode()):
            return 401, {"error": {"code": "UNAUTHORIZED", "message": "player token required"}}
        gateway = self.gateways.get(match.group(1))
        if gateway is None:
            return 404, {"error": {"code": "NO_SUCH_CAMPAIGN", "message": "unknown campaign"}}
        rest = match.group(2) or ""
        try:
            if method == "GET" and rest == "/state":
                return 200, gateway.public_state()
            if method == "GET" and rest == "/recovery":
                return 200, gateway.recovery()
            page = re.match(r"^/pages/([A-Za-z0-9_-]{1,64})$", rest)
            if method == "GET" and page:
                return 200, gateway.page(page.group(1))
            action = re.match(r"^/actions/([A-Za-z0-9_-]{6,64})(/reroute)?$", rest)
            if method == "GET" and action and not action.group(2):
                return 200, gateway.action_status(action.group(1))
            if method != "POST":
                return 404, {"error": {"code": "NOT_FOUND", "message": "unknown path"}}
            try:
                data = json.loads(body or b"{}")
            except json.JSONDecodeError:
                return 400, {"error": {"code": "BAD_JSON", "message": "body must be JSON"}}
            if not isinstance(data, dict):
                return 400, {"error": {"code": "BAD_JSON", "message": "body must be a JSON object"}}
            if rest == "/provider":
                self.known(data.get("provider"))
                return 200, gateway.select_provider(data.get("provider"))
            if rest == "/actions":
                if data.get("gm_provider"):
                    self.known(data["gm_provider"])
                status = gateway.submit(data)
                if self.autorun:
                    threading.Thread(target=self.work, daemon=True).start()
                return 202 if status["status"] == "submitted" else 200, status
            if action and action.group(2):
                self.known(data.get("provider"))
                status = gateway.reroute(action.group(1), data.get("provider"))
                if self.autorun:
                    threading.Thread(target=self.work, daemon=True).start()
                return 200, status
            return 404, {"error": {"code": "NOT_FOUND", "message": "unknown path"}}
        except Refused as refusal:
            return STATUS.get(refusal.code, 400), refusal.as_dict()
        except Conflict:
            return 409, {"error": {"code": "CONFLICT", "message": "changed concurrently; retry"}}
        except ValueError as error:
            return 503, {"error": {"code": "CAMPAIGN_BUSY", "message": "the record is mid-write; retry shortly"}}

    def gm(self, method, campaign_id, provider, verb, headers, body):
        """GM-session transport: the gmctl verbs over HTTPS for the one provider this token belongs to."""
        expected = self.gm_tokens.get(provider)
        supplied = headers.get("authorization", "")
        if not expected or not hmac.compare_digest(supplied.encode(), ("Bearer " + expected).encode()):
            return 401, {"error": {"code": "UNAUTHORIZED", "message": "GM session token for this provider required"}}
        gateway = self.gateways.get(campaign_id)
        if gateway is None or method != "POST":
            return 404, {"error": {"code": "NOT_FOUND", "message": "unknown campaign or method"}}
        try:
            data = json.loads(body or b"{}")
            run, payload = data.get("run"), data.get("body")
            if not isinstance(run, str) or not run:
                return 400, {"error": {"code": "BAD_RUN", "message": "run is required"}}
            calls = {"claim": lambda: gateway.claim(provider, run, {"kind": "agent-session", "model": data.get("model"), "session": data.get("session"), "mock": False}),
                     "context": lambda: gateway.context(provider, run), "publish": lambda: gateway.publish(provider, run),
                     "release": lambda: gateway.release(provider, run, "released by the GM session"),
                     "tables": lambda: gateway.fix_tables(provider, run, payload), "roll": lambda: gateway.roll(provider, run, payload),
                     "review": lambda: gateway.review(provider, run, payload), "commit": lambda: gateway.commit(provider, run, payload)}
            return 200, calls[verb]()
        except json.JSONDecodeError:
            return 400, {"error": {"code": "BAD_JSON", "message": "body must be JSON"}}
        except Refused as refusal:
            return STATUS.get(refusal.code, 409 if refusal.code in ("LEASE_LOST", "NOT_ROUTED_HERE", "TABLES_FIXED", "ALREADY_COMMITTED") else 400), refusal.as_dict()
        except Conflict:
            return 409, {"error": {"code": "CONFLICT", "message": "changed concurrently; re-read and continue"}}

    def known(self, provider):
        if provider not in self.providers:
            raise Refused("UNKNOWN_PROVIDER", "this service has no such GM provider", providers=sorted(self.providers))


def handler(app):
    class Handler(BaseHTTPRequestHandler):
        def respond(self):
            length = int(self.headers.get("content-length") or 0)
            if length > MAX_BODY:
                code, payload = 413, {"error": {"code": "TOO_LARGE", "message": "body too large"}}
            else:
                code, payload = app.handle(self.command, self.path.split("?")[0], {k.lower(): v for k, v in self.headers.items()},
                                           self.rfile.read(length) if length else b"")
            data = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(data)))
            self.send_header("cache-control", "no-store")
            if app.origin:
                self.send_header("access-control-allow-origin", app.origin)
                self.send_header("access-control-allow-headers", "authorization, content-type")
                self.send_header("access-control-allow-methods", "GET, POST, OPTIONS")
                self.send_header("vary", "origin")
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = respond

        def do_OPTIONS(self):
            self.send_response(204)
            if app.origin:
                self.send_header("access-control-allow-origin", app.origin)
                self.send_header("access-control-allow-headers", "authorization, content-type")
                self.send_header("access-control-allow-methods", "GET, POST, OPTIONS")
            self.end_headers()

        def log_message(self, *args):
            pass
    return Handler


def build(args, env=None):
    env = os.environ if env is None else env
    if getattr(args, "shared", None):
        import staging
        gateway = staging.open_shared(args.shared)
        args.id = gateway.id
    else:
        gateway = Gateway(args.campaign, args.id, SqliteStore(args.store))
    registry = provider_module.registry(env)
    for name in filter(None, (env.get("GENESIS_SESSION_PROVIDERS") or "").split(",")):
        registry[name.strip()] = provider_module.SessionProvider(name.strip())
    gm_tokens = json.loads(env.get("GENESIS_GM_TOKENS") or "{}")
    for name in gm_tokens:
        registry.setdefault(name, provider_module.SessionProvider(name))
    return App({args.id: gateway}, registry, env.get("GENESIS_PLAYER_TOKEN"), env.get("GENESIS_ALLOWED_ORIGIN"), getattr(args, "autorun", False), gm_tokens)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("serve", "work"):
        s = sub.add_parser(name)
        s.add_argument("--campaign", type=Path); s.add_argument("--id"); s.add_argument("--store", type=Path)
        s.add_argument("--shared", type=Path, help="a shared staging environment directory in a git clone (replaces the three above)")
    sub.choices["serve"].add_argument("--port", type=int, default=8787)
    sub.choices["serve"].add_argument("--host", default="127.0.0.1")
    sub.choices["serve"].add_argument("--autorun", action="store_true")
    args = parser.parse_args(argv)
    app = build(args)
    if args.command == "work":
        print(json.dumps(app.work(), indent=1))
        return 0
    if not app.token:
        parser.exit(2, "GENESIS_PLAYER_TOKEN is required to serve\n")
    ThreadingHTTPServer((args.host, args.port), handler(app)).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
