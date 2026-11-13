"""GM providers behind one small boundary: `step(context) -> next move`.

A provider is stateless between calls. Each call receives the gateway's GM context for the
claimed action (including what was already accepted for it: tables, rolls) and returns ONE move:

  {"type": "review", "review": {summary, errors[{code,message}], warnings[], alternatives[{label, declaration}]}}
  {"type": "tables", "tables": {interpretation, tables, npc_evaluations[]}}
  {"type": "rolls",  "rolls": [{roll_key, step_id, formula, mode, kind, requested_by, purpose, dc, rule_sources}]}
  {"type": "commit", "proposal": {world_time, events[], narration, scene_state, turn_context}}

Because a move depends only on the context, any provider can continue an action another one
started: the successor sees the accepted tables and rolls and proposes the next move. Nothing
here writes anything; the gateway validates and performs every move.

Model-backed adapters (Anthropic, OpenAI, Google) use only the standard library and read their
credentials and model id from the environment of the process that runs them (the GM worker,
never a player's browser). An adapter that lacks a credential or a model id reports itself
unavailable; the runner then blocks the action for that provider and stops. No adapter ever
falls back to a different provider or model.
"""
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
MOVES = ("review", "tables", "rolls", "commit")


class Unavailable(RuntimeError):
    """The provider cannot run at all right now (missing credential, service unreachable)."""


class BadMove(ValueError):
    """The provider answered, but not with a usable move."""


def guide():
    return (HERE / "GM_GUIDE.md").read_text(encoding="utf-8")


def parse_move(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.index("\n")+1:] if "\n" in text else text
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise BadMove("the provider did not return a JSON object")
    try:
        move = json.loads(text[start:end+1])
    except json.JSONDecodeError as error:
        raise BadMove(f"the provider returned invalid JSON: {error}")
    if not isinstance(move, dict) or move.get("type") not in MOVES:
        raise BadMove("a move needs type review, tables, rolls or commit")
    return move


class Provider:
    id = None
    kind = "abstract"
    mock = False

    def capabilities(self):
        return {"id": self.id, "kind": self.kind, "mock": self.mock, "available": True, "reason": None, "model": None}

    def step(self, context):
        raise NotImplementedError


class ScriptedProvider(Provider):
    """Deterministic test double. `script(context) -> move`. Always reported as a mock."""
    kind, mock = "scripted", True

    def __init__(self, provider_id, script, available=True, reason=None):
        self.id, self.script, self.available, self.reason = provider_id, script, available, reason

    def capabilities(self):
        return dict(super().capabilities(), available=self.available, reason=self.reason)

    def step(self, context):
        if not self.available:
            raise Unavailable(self.reason or "scripted provider switched off")
        return self.script(context)


class ModelProvider(Provider):
    """Shared prompt assembly and HTTP plumbing for hosted models."""
    kind = "model-api"
    key_env = model_env = base_env = default_base = None
    timeout = 180

    def __init__(self, provider_id=None, env=None):
        self.env = os.environ if env is None else env
        if provider_id:
            self.id = provider_id

    def capabilities(self):
        missing = [name for name in (self.key_env, self.model_env) if not self.env.get(name)]
        return {"id": self.id, "kind": self.kind, "mock": False, "available": not missing,
                "reason": ("missing " + ", ".join(missing)) if missing else None, "model": self.env.get(self.model_env),
                "endpoint": self.env.get(self.base_env) or self.default_base}

    def prompt(self, context):
        return guide(), json.dumps(context, ensure_ascii=False)

    def post(self, url, headers, body):
        request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                         headers={"content-type": "application/json", **headers})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:300]
            if error.code in (401, 403, 404, 408, 429) or error.code >= 500:
                raise Unavailable(f"{self.id}: HTTP {error.code}: {detail}")
            raise BadMove(f"{self.id}: HTTP {error.code}: {detail}")
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise Unavailable(f"{self.id}: cannot reach the model service: {error}")

    def step(self, context):
        capability = self.capabilities()
        if not capability["available"]:
            raise Unavailable(f"{self.id}: {capability['reason']}")
        system, user = self.prompt(context)
        return parse_move(self.complete(system, user, capability))


class AnthropicProvider(ModelProvider):
    id = "claude"
    key_env, model_env, base_env, default_base = "ANTHROPIC_API_KEY", "GENESIS_CLAUDE_MODEL", "GENESIS_CLAUDE_BASE_URL", "https://api.anthropic.com"

    def complete(self, system, user, capability):
        data = self.post(capability["endpoint"].rstrip("/") + "/v1/messages",
                         {"x-api-key": self.env[self.key_env], "anthropic-version": "2023-06-01"},
                         {"model": capability["model"], "max_tokens": int(self.env.get("GENESIS_MAX_OUTPUT_TOKENS", "16000")),
                          "system": system, "messages": [{"role": "user", "content": user}]})
        return "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")


class OpenAIProvider(ModelProvider):
    id = "gpt"
    key_env, model_env, base_env, default_base = "OPENAI_API_KEY", "GENESIS_GPT_MODEL", "GENESIS_GPT_BASE_URL", "https://api.openai.com"

    def complete(self, system, user, capability):
        data = self.post(capability["endpoint"].rstrip("/") + "/v1/chat/completions",
                         {"authorization": "Bearer " + self.env[self.key_env]},
                         {"model": capability["model"], "response_format": {"type": "json_object"},
                          "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        return data["choices"][0]["message"]["content"]


class GeminiProvider(ModelProvider):
    id = "gemini"
    key_env, model_env, base_env, default_base = "GEMINI_API_KEY", "GENESIS_GEMINI_MODEL", "GENESIS_GEMINI_BASE_URL", "https://generativelanguage.googleapis.com"

    def complete(self, system, user, capability):
        data = self.post(f"{capability['endpoint'].rstrip('/')}/v1beta/models/{capability['model']}:generateContent",
                         {"x-goog-api-key": self.env[self.key_env]},
                         {"systemInstruction": {"parts": [{"text": system}]},
                          "contents": [{"role": "user", "parts": [{"text": user}]}],
                          "generationConfig": {"responseMimeType": "application/json"}})
        candidates = data.get("candidates") or []
        if not candidates:
            raise BadMove("gemini returned no candidate (blocked or empty)")
        return "".join(part.get("text", "") for part in candidates[0].get("content", {}).get("parts", []))


class SessionProvider(Provider):
    """An agent session that performs the GM work through gmctl (today: the Claude cloud worker
    that already runs the Datapad). It is driven from outside, so `step` is never called."""
    kind = "agent-session"

    def __init__(self, provider_id):
        self.id = provider_id

    def capabilities(self):
        return dict(super().capabilities(), reason="driven by an agent session through gmctl; no API key in the gateway")

    def step(self, context):
        raise Unavailable(f"{self.id} is an agent-session provider: it claims and commits through gmctl itself")


def registry(env=None):
    """The providers this process could run. Order carries no meaning: nothing is ever chosen by position."""
    return {p.id: p for p in (AnthropicProvider(env=env), OpenAIProvider(env=env), GeminiProvider(env=env))}


def matrix(providers):
    return [providers[name].capabilities() for name in sorted(providers)]
