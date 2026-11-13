"""Provider-neutral GM turn gateway: the one boundary every GM provider goes through.

A GM provider (Claude, GPT, Gemini, or a scripted test double) interprets the declaration,
portrays NPCs and proposes consequences. It never touches the ledger, the dice cursor, the
queue or the published pages. Everything mechanical and durable is done here, with the
existing machinery and nothing parallel to it:

  context      brief.py (GM audience) + export_state (public) + turn_contract.js preflight
  dice         .claude/skills/litrpg-dice/roll.py (keyed requests, receipts, no rerolls), or
               development/experimental_resolution/engine.py when the campaign copy carries
               the explicit non-canonical marker (dice modes, narrative axis)
  commit       .claude/skills/litrpg-ledger/batch.py (one ordered batch per action)
  publication  export_state.publish_set: history pages first, snapshot last, under CAS
  lease/queue  the same action-row and lock documents the Datapad worker uses

Operation identity is the action id. One operation record per action lives beside the other
private receipts in the campaign (`hidden/provider_ops/`); it is a journal of what has been
accepted for that action (fixed tables, accepted rolls, the committed batch), never a second
campaign state. A provider that takes over an in-flight action inherits that record verbatim.

In-flight rules (see development/PROVIDER_INTERCHANGE.md §4):
  * only the provider the action is routed to may claim it; routing changes only through
    `reroute`, an explicit player/operator decision, never by a provider or a fallback;
  * a live lease held by another run refuses everyone else (PROVIDER_BUSY);
  * after tables are fixed or a roll is accepted, a successor continues from them: it cannot
    replace the tables, and a roll for the same step/actor/kind returns the accepted result;
  * an accepted ledger batch is finished byte for byte; a resolved action is only published.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
UI = ROOT / "campaigns/starwars_litrpg/ui"
for extra in (HERE, ROOT / ".claude/skills/litrpg-ledger", UI, ROOT / "development/experimental_resolution"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))
import batch            # noqa: E402
import export_state     # noqa: E402
import ledger           # noqa: E402
import policy           # noqa: E402
import npc_review       # noqa: E402
from store import Conflict  # noqa: E402


def _module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


brief = _module("gateway_brief", ".claude/skills/litrpg-process-turn/brief.py")
progress = _module("gateway_progress", ".claude/skills/litrpg-process-turn/progress.py")
roller = _module("gateway_roll", ".claude/skills/litrpg-dice/roll.py")
turn = _module("gateway_turn", ".claude/skills/litrpg-process-turn/turn.py")
engine = _module("gateway_engine", "development/experimental_resolution/engine.py")

SCHEMA = "genesis-gm-operation/1"
PROVIDER_ID = re.compile(r"^[a-z][a-z0-9_-]{1,39}$")
RESERVED_KINDS = {"player_declaration", "owner_ruling", "ruling_void", "gm_narration", "scene_state", "turn_context"}
IN_FLIGHT = ("submitted", "processing", "resolved")
IMMUTABLE = ("actor", "campaign_id", "based_on_revision", "ledger_head", "context_id", "declaration", "text")


class Refused(ValueError):
    """A request the gateway will not perform. `code` is stable and machine-readable."""
    def __init__(self, code, message, **extra):
        super().__init__(f"{code}: {message}")
        self.code, self.message, self.extra = code, message, extra

    def as_dict(self):
        return {"error": {"code": self.code, "message": self.message, **self.extra}}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def now_ms():
    return time.time_ns() // 1_000_000


class Gateway:
    def __init__(self, campaign_dir, campaign_id, store, lease_ms=180000, clock=now_ms, durable=None):
        """`durable(campaign_dir, action_id)` runs after the ledger batch is accepted and before
        anything is published; production passes the fenced git commit+push here. If it raises,
        the action stays resolved-unpublished and nothing reaches the player."""
        self.campaign = Path(campaign_dir).resolve()
        self.id = campaign_id
        self.store = store
        self.lease_ms = lease_ms
        self.clock = clock
        self.durable = durable
        self.entry = {"id": campaign_id, "path": self.campaign, "dir": str(self.campaign)}

    # ------------------------------------------------------------------ helpers
    def _public(self):
        return export_state.build(campaign_dir=self.campaign, campaign_id=self.id)

    def _marker(self):
        path = self.campaign / "experimental_resolution.json"
        if not path.exists():
            return None
        config = json.loads(path.read_text())
        return config if config.get("enabled") is True and config.get("canonical") is False else None

    def _op_path(self, action_id):
        return self.campaign / "hidden/provider_ops" / (digest(action_id) + ".json")

    def _op(self, action_id):
        path = self._op_path(action_id)
        return json.loads(path.read_text()) if path.exists() else None

    def _save_op(self, op):
        path = self._op_path(op["action_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        batch.durable_json(path, op)

    def _rows(self):
        out = []
        for key in self.store.keys("actions/"):
            version, row = self.store.read(key)
            if row and row.get("campaign_id") == self.id:
                out.append((key, version, row))
        return sorted(out, key=lambda item: item[2].get("created_ms", 0))

    def _in_flight(self):
        rows = [item for item in self._rows() if item[2].get("status") in IN_FLIGHT]
        if len(rows) > 1:
            raise Refused("QUEUE_CORRUPT", "more than one action is in flight for this campaign; operator review required")
        return rows[0] if rows else None

    def _identity(self, action):
        return {**{key: action.get(key) for key in IMMUTABLE}, "resolution_settings": policy.settings(action)}

    def _lock(self):
        return self.store.read("locks/" + self.id)

    def _holder(self, provider, run):
        """The caller must hold the live lease for the in-flight action. Renews it."""
        version, lock = self._lock()
        now = self.clock()
        if not lock or lock.get("holder") != run or lock.get("provider") != provider or lock.get("expires_ms", 0) <= now:
            raise Refused("LEASE_LOST", "this run does not hold the campaign lease; stop and write nothing more")
        lock = dict(lock, expires_ms=now + self.lease_ms)
        try:
            self.store.put("locks/" + self.id, lock, version)
        except Conflict:
            raise Refused("LEASE_LOST", "the lease changed hands; stop and write nothing more")
        item = self._in_flight()
        if not item or item[2].get("processing", {}).get("run") != run:
            raise Refused("NOT_CLAIMED", "this run has no claimed action")
        return item, lock

    def _stage(self, item, lock, run, stage, **fields):
        key, version, row = item
        previous = row.get("processing", {})
        if previous.get("run") == run and previous.get("stage") in progress.STAGES and \
                progress.STAGES.index(stage) < progress.STAGES.index(previous["stage"]):
            stage = previous["stage"]          # a repeated read never moves the reported stage backwards
        base = dict(row)
        if "publication" in fields:
            base["publication"] = fields["publication"]
        try:
            patch = progress.patch(base, lock, run, stage, self.clock())
        except ValueError as error:
            raise Refused("LEASE_LOST", str(error))
        row = dict(row, **fields, **patch)
        try:
            version = self.store.put(key, row, version)
        except Conflict:
            raise Refused("LEASE_LOST", "the action row changed under this run; stop and write nothing more")
        return key, version, row

    def _lease_file(self, lock):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=self.campaign / "hidden")
        json.dump(lock, handle)
        handle.close()
        return Path(handle.name)

    # ------------------------------------------------------------------ player side
    def public_state(self):
        """What a player client may see: the published documents and a cursor. Never opens hidden/."""
        state = self._public()
        documents = export_state.publish_set(state)
        item = self._in_flight()
        return {"cursor": {"campaign_id": self.id, "revision": state["revision"], "ledger_head": state["ledger_head"],
                           "context_id": (state.get("turn_context") or {}).get("context_id")},
                "state": documents["state"], "pages": sorted(documents["pages"]),
                "in_flight": self.action_status(item[2]["action_id"]) if item else None,
                "routing": self.routing()}

    def page(self, name):
        documents = export_state.publish_set(self._public())
        if name not in documents["pages"]:
            raise Refused("NO_SUCH_PAGE", "unknown history page")
        return documents["pages"][name]

    def routing(self):
        _, doc = self.store.read("routing/" + self.id)
        return doc or {"provider": None, "history": []}

    def select_provider(self, provider, by="player"):
        """Choose the GM provider for actions submitted from now on. Explicit, recorded, reversible."""
        if not PROVIDER_ID.match(provider or ""):
            raise Refused("BAD_PROVIDER", "provider id must be a short lowercase identifier")
        version, doc = self.store.read("routing/" + self.id)
        doc = doc or {"provider": None, "history": []}
        if doc["provider"] != provider:
            doc = {"provider": provider, "history": (doc["history"] + [{"provider": provider, "by": by, "at_ms": self.clock()}])[-50:]}
            self.store.put("routing/" + self.id, doc, version)
        return doc

    def submit(self, action):
        """Queue one declaration. Idempotent on action_id; stale or conflicting input is refused, never merged."""
        action_id = action.get("action_id")
        if not isinstance(action_id, str) or not re.match(r"^[A-Za-z0-9_-]{6,64}$", action_id):
            raise Refused("BAD_ACTION_ID", "action_id must be 6-64 letters, digits, - or _")
        if action.get("campaign_id") != self.id:
            raise Refused("WRONG_CAMPAIGN", "the action names another campaign")
        try:
            identity = self._identity(action)
        except ValueError as error:
            raise Refused("BAD_SETTINGS", str(error))
        provider = action.get("gm_provider") or self.routing()["provider"]
        if not provider or not PROVIDER_ID.match(provider):
            raise Refused("PROVIDER_NOT_SELECTED", "no GM provider is selected for this campaign; choose one explicitly")
        key = "actions/" + action_id
        version, row = self.store.read(key)
        if row:
            if digest(self._identity(row)) != digest(identity):
                raise Refused("ACTION_ID_REUSED", "this action id was already submitted with different content")
            return self.action_status(action_id, duplicate=True)
        state = self._public()
        context = state.get("turn_context") or {}
        if (action.get("based_on_revision") != state["revision"] or action.get("ledger_head") != state["ledger_head"]
                or action.get("context_id") != context.get("context_id")):
            raise Refused("STALE", "the campaign has moved on; refresh and declare against the current revision",
                          revision=state["revision"], ledger_head=state["ledger_head"])
        if action.get("actor") != state["active_actor"]:
            raise Refused("NOT_ACTIVE_ACTOR", "only the active player character can declare")
        if not self._marker() and identity["resolution_settings"] != policy.DEFAULT:
            raise Refused("UNSUPPORTED_SETTINGS", "dice modes and narrative consequences are not enabled for this campaign")
        if self._in_flight():
            raise Refused("TURN_IN_FLIGHT", "another declaration is still being resolved", action_id=self._in_flight()[2]["action_id"])
        row = {"action_id": action_id, "status": "submitted", "created_ms": self.clock(), "source": action.get("source", "composer"),
               "contract": action.get("contract"), "confirmed_warnings": bool(action.get("confirmed_warnings")),
               **identity, "gm": {"provider": provider, "route": [{"provider": provider, "by": "player", "at_ms": self.clock()}]}}
        try:
            self.store.put(key, row, 0)
        except Conflict:
            return self.submit(action)
        # Two different declarations can pass the in-flight check at the same moment. The earlier one
        # (created_ms, then id) keeps the turn; the other is withdrawn before any GM can claim it.
        racing = sorted((r for r in self._rows() if r[2].get("status") in IN_FLIGHT), key=lambda r: (r[2].get("created_ms", 0), r[2]["action_id"]))
        if racing and racing[0][2]["action_id"] != action_id:
            version, mine = self.store.read(key)
            if mine and mine.get("status") == "submitted":
                self.store.put(key, dict(mine, status="failed", error="another declaration was submitted first; nothing was resolved"), version)
            raise Refused("TURN_IN_FLIGHT", "another declaration was submitted first", action_id=racing[0][2]["action_id"])
        return self.action_status(action_id)

    def action_status(self, action_id, duplicate=False):
        """Player-safe status of one action. No tables, DCs, private rolls or provider reasoning."""
        _, row = self.store.read("actions/" + action_id)
        if not row or row.get("campaign_id") != self.id:
            raise Refused("NO_SUCH_ACTION", "unknown action")
        gm = row.get("gm", {})
        out = {"action_id": action_id, "status": row["status"], "duplicate": duplicate, "provider": gm.get("provider"),
               "stage": row.get("processing", {}).get("stage"), "blocked": gm.get("blocked"), "review": row.get("review"),
               "error": row.get("error"), "published_revision": row.get("published_revision"),
               "publication": row.get("publication")}
        return {key: value for key, value in out.items() if value is not None}

    def reroute(self, action_id, provider, by="player"):
        """Explicitly hand an unfinished action to another provider. Refused while a lease is live."""
        if not PROVIDER_ID.match(provider or ""):
            raise Refused("BAD_PROVIDER", "provider id must be a short lowercase identifier")
        key = "actions/" + action_id
        version, row = self.store.read(key)
        if not row or row.get("campaign_id") != self.id:
            raise Refused("NO_SUCH_ACTION", "unknown action")
        if row["status"] not in ("submitted", "processing"):
            raise Refused("NOT_REROUTABLE", f"an action that is {row['status']} needs no GM; nothing to hand over")
        _, lock = self._lock()
        if row["status"] == "processing" and lock and lock.get("holder") and lock.get("expires_ms", 0) > self.clock():
            raise Refused("PROVIDER_BUSY", "the current provider still holds the lease; wait for it to release or expire")
        gm = dict(row.get("gm", {}))
        if gm.get("provider") != provider:
            gm["route"] = gm.get("route", []) + [{"provider": provider, "by": by, "at_ms": self.clock(), "from": gm.get("provider")}]
            gm["provider"] = provider
            gm.pop("blocked", None)
            self.store.put(key, dict(row, gm=gm), version)
        return self.action_status(action_id)

    def block(self, action_id, provider, code, reason):
        """Record that the routed provider cannot run (no credentials, service down). The action
        stays queued for that provider; nobody else picks it up until the player reroutes."""
        key = "actions/" + action_id
        version, row = self.store.read(key)
        if row and row.get("status") == "submitted" and row.get("gm", {}).get("provider") == provider:
            gm = dict(row["gm"], blocked={"code": code, "provider": provider, "reason": str(reason)[:300], "at_ms": self.clock()})
            self.store.put(key, dict(row, gm=gm), version)
        return self.action_status(action_id)

    # ------------------------------------------------------------------ provider side
    def claim(self, provider, run):
        """Take the lease and the in-flight action for `provider`. Returns the operation phase."""
        if not PROVIDER_ID.match(provider or "") or not isinstance(run, str) or not run:
            raise Refused("BAD_PROVIDER", "provider id and run id are required")
        now = self.clock()
        version, lock = self._lock()
        if lock and lock.get("holder") not in (None, run) and lock.get("expires_ms", 0) > now:
            raise Refused("PROVIDER_BUSY", "another run holds the campaign lease", holder_provider=lock.get("provider"))
        item = self._in_flight()
        if not item:
            raise Refused("NOTHING_TO_DO", "no action is waiting for a GM")
        key, row_version, row = item
        gm = row.get("gm", {})
        if row["status"] != "resolved" and gm.get("provider") != provider:
            raise Refused("NOT_ROUTED_HERE", f"this action is routed to {gm.get('provider')}; a provider never takes another's turn",
                          provider=gm.get("provider"))
        lock = {"holder": run, "provider": provider, "expires_ms": now + self.lease_ms, "acquired_ms": now}
        try:
            self.store.put("locks/" + self.id, lock, version)
        except Conflict:
            raise Refused("PROVIDER_BUSY", "lost the race for the campaign lease")
        action_id = row["action_id"]
        op = self._op(action_id)
        if op is None:
            op = {"schema": SCHEMA, "action_id": action_id, "campaign_id": self.id, "action_hash": digest(self._identity(row)),
                  "runs": [], "tables": None, "rolls": {}, "commit": None}
        elif op["action_hash"] != digest(self._identity(row)):
            raise Refused("ACTION_CHANGED", "the queued action differs from the one this operation accepted; operator review required")
        op["runs"].append({"provider": provider, "run": run, "at_ms": now, "took_over_at": self.phase(op, row)})
        self._save_op(op)
        gm = dict(gm, runs=(gm.get("runs", []) + [{"provider": provider, "run": run, "at_ms": now}])[-20:])
        gm.pop("blocked", None)
        fields = {"gm": gm}
        if row["status"] == "submitted":
            fields["status"] = "processing"
        self._stage((key, row_version, dict(row, processing={} if row.get("processing", {}).get("run") != run else row["processing"])),
                    lock, run, "publishing" if row["status"] == "resolved" else "claimed", **fields)
        return {"action_id": action_id, "phase": self.phase(op, row), "provider": provider, "run": run}

    @staticmethod
    def phase(op, row):
        if row.get("status") == "resolved" or (op and op.get("commit")):
            return "publish"
        if op and (op.get("tables") or op.get("rolls")):
            return "resolve"
        return "interpret"

    def context(self, provider, run):
        """Everything the routed GM provider is permitted to read for this action. GM-private."""
        (key, version, row), lock = self._holder(provider, run)
        op = self._op(row["action_id"])
        state = self._public()
        public_context = state.get("turn_context") or {}
        stale = row["based_on_revision"] != state["revision"] or row["ledger_head"] != state["ledger_head"]
        if stale and not op.get("commit"):
            raise Refused("STALE", "the action was declared against an older revision")
        declaration = row.get("declaration")
        checked = turn.node_validate(declaration, public_context) if declaration else turn.node_parse(row.get("text", ""), public_context)
        _, gm_brief = brief.build(self.entry, action={k: row.get(k) for k in ("campaign_id", "based_on_revision", "ledger_head", "resolution_settings")})
        self._stage((key, version, row), lock, run, "context")
        hidden = [e for e in ledger.load_all(self.campaign) if e["visibility"] == "gm_only"]
        return {"audience": "gm", "campaign_id": self.id, "provider": provider,
                "action": {k: row.get(k) for k in ("action_id", "actor", "text", "declaration", "resolution_settings", "contract", "confirmed_warnings")},
                "validation": checked["validation"], "declaration": checked.get("declaration", declaration),
                "public_context": public_context, "revision": state["revision"], "ledger_head": state["ledger_head"],
                "brief": brief.compact(gm_brief), "recent_private": [{k: e.get(k) for k in ("event_id", "kind", "summary", "details")} for e in hidden[-12:]],
                "npc_last_evaluations": self._npc_last(),
                "resolution": {"engine": "experimental" if self._marker() else "legacy", "settings": policy.settings(row)},
                "operation": {"phase": self.phase(op, row), "tables": op["tables"] and op["tables"]["value"],
                              "rolls": {k: v["result"] for k, v in op["rolls"].items()},
                              "previous_runs": [{"provider": r["provider"], "took_over_at": r["took_over_at"]} for r in op["runs"][:-1]]}}

    def _npc_last(self):
        out = {}
        for e in ledger.load_all(self.campaign):
            for ev in (e.get("details") or {}).get("npc_evaluations", []) or []:
                if isinstance(ev, dict) and ev.get("npc"):
                    out[ev["npc"]] = {"event_id": e["event_id"], "outcome_key": ev.get("outcome_key")}
        return out

    def review(self, provider, run, review):
        """Send the declaration back to the player. Only before anything mechanical was accepted."""
        (key, version, row), lock = self._holder(provider, run)
        op = self._op(row["action_id"])
        if op["tables"] or op["rolls"] or op["commit"]:
            raise Refused("TOO_LATE_FOR_REVIEW", "tables or rolls were already accepted for this action; it must be resolved")
        if not isinstance(review, dict) or not str(review.get("summary") or "").strip() or not isinstance(review.get("errors"), list) or not review["errors"]:
            raise Refused("BAD_REVIEW", "a review needs a summary and at least one coded error")
        state = self._public()
        for alt in review.get("alternatives", []):
            verdict = turn.node_validate(alt.get("declaration") or {}, state.get("turn_context") or {})["validation"]
            if not verdict["legal"]:
                raise Refused("BAD_ALTERNATIVE", "every offered alternative must pass the validator: " + str(alt.get("label")))
        clean = {"summary": review["summary"], "errors": [{"code": str(e.get("code")), "message": str(e.get("message"))} for e in review["errors"]],
                 "warnings": [str(w) for w in review.get("warnings", [])],
                 "alternatives": [{"label": str(a.get("label")), "declaration": a["declaration"]} for a in review.get("alternatives", [])]}
        self._stage((key, version, row), lock, run, "rules", status="needs_revision", review=clean)
        self._release(run)
        return self.action_status(row["action_id"])

    def fix_tables(self, provider, run, tables):
        """Record the GM's interpretation and the tables it fixes before any die. Immutable once accepted."""
        (key, version, row), lock = self._holder(provider, run)
        op = self._op(row["action_id"])
        if op["commit"]:
            raise Refused("ALREADY_COMMITTED", "this action is already committed")
        if not isinstance(tables, dict) or not str(tables.get("interpretation") or "").strip():
            raise Refused("BAD_TABLES", "an interpretation is required")
        value = {"interpretation": tables["interpretation"], "tables": tables.get("tables", ""),
                 "npc_evaluations": tables.get("npc_evaluations", [])}
        if op["tables"]:
            if op["tables"]["fingerprint"] != digest(value):
                raise Refused("TABLES_FIXED", "tables were already fixed for this action; continue from them", tables=op["tables"]["value"])
            return {"tables": op["tables"]["value"], "replayed": True}
        problems = npc_review.check(value["npc_evaluations"], ledger.load_all(self.campaign))
        if problems:
            raise Refused("NPC_EVALUATION", "NPC evaluations must account for what changed", problems=problems)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            code = roller.main(["--advance-turn", "--campaign", str(self.campaign), "--request-id", row["action_id"] + ":advance"])
        if code != 0:
            raise Refused("DICE_UNAVAILABLE", "the dice resolver refused to open the turn: " + err.getvalue().strip()[:300])
        op["tables"] = {"fingerprint": digest(value), "value": value, "by": {"provider": provider, "run": run}}
        self._save_op(op)
        self._stage((key, version, row), lock, run, "rules")
        return {"tables": value, "replayed": False}

    def roll(self, provider, run, request):
        """Ask the authoritative resolver for one roll. Keyed by roll_key; a retry or a successor gets the accepted result."""
        (key, version, row), lock = self._holder(provider, run)
        op = self._op(row["action_id"])
        if not op["tables"]:
            raise Refused("TABLES_FIRST", "fix the tables before the first roll")
        if op["commit"]:
            raise Refused("ALREADY_COMMITTED", "this action is already committed")
        need = ("roll_key", "formula", "kind", "requested_by", "purpose")
        if not isinstance(request, dict) or any(not isinstance(request.get(k), str) or not request[k] for k in need):
            raise Refused("BAD_ROLL", "roll_key, formula, kind, requested_by and purpose are required")
        if not re.match(r"^[A-Za-z0-9_.-]{1,40}$", request["roll_key"]):
            raise Refused("BAD_ROLL", "roll_key must be 1-40 letters, digits, . - or _")
        if request["kind"] not in ("check", "attack", "save", "damage", "other") or request.get("mode", "normal") not in ("normal", "advantage", "disadvantage"):
            raise Refused("BAD_ROLL", "unknown roll kind or mode")
        if request["requested_by"] not in (row["actor"], "gm", "gm_hidden"):
            raise Refused("BAD_ROLL", "requested_by is the player character, gm or gm_hidden")
        if re.search(r"\b(dc|ac|armor class|hit points|hp)\s*\d", request["purpose"], re.I):
            raise Refused("PURPOSE_LEAK", "roll purposes are public: no DC, AC or hit points in them")
        declaration = row.get("declaration") or {}
        steps = engine.step_ids(declaration)
        if request["requested_by"] == row["actor"] and request.get("step_id") not in steps:
            raise Refused("NOT_DECLARED", "the player character rolls only for a step the player declared")
        clean = {k: request[k] for k in ("roll_key", "step_id", "formula", "mode", "kind", "requested_by", "purpose", "dc", "rule_sources") if request.get(k) is not None}
        request_hash = digest(clean)
        slot = digest([clean.get("step_id"), clean["kind"], clean["requested_by"]]) if clean["requested_by"] == row["actor"] else None
        for known_key, known in op["rolls"].items():
            if known_key == clean["roll_key"]:
                if known["request_hash"] != request_hash:
                    raise Refused("ROLL_KEY_REUSED", "this roll key was accepted with a different request")
                return {"roll_key": known_key, "result": known["result"], "replayed": True}
            if slot and known.get("slot") == slot:
                return {"roll_key": known_key, "result": known["result"], "replayed": True, "note": "this step already has its roll; a new key cannot reroll it"}
        self._stage((key, version, row), lock, run, "dice")
        purpose = f"[{row['action_id']}] {clean['purpose']}"
        if self._marker():
            action = dict(self._identity(row), campaign_id=self.id)
            try:
                result = engine.execute(self.campaign, row["action_id"], action, dict(clean, mode=clean.get("mode", "normal"),
                                        rule_sources=clean.get("rule_sources") or ["GM ruling"], step_id=clean.get("step_id") or next(iter(steps), None)))
            except ValueError as error:
                raise Refused("DICE_REFUSED", str(error))
            record, private = result["roll"], result["resolution"]
        else:
            argv = [clean["formula"], "--mode", clean.get("mode", "normal"), "--by", clean["requested_by"], "--purpose", purpose,
                    "--campaign", str(self.campaign), "--request-id", f"{row['action_id']}:{clean['roll_key']}"]
            if clean.get("dc") is not None:
                argv += ["--dc", str(int(clean["dc"]))]
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = roller.main(argv)
            if code != 0:
                raise Refused("DICE_REFUSED", err.getvalue().strip()[:300])
            record, private = json.loads(out.getvalue()), None
        result = {"roll_id": record["roll_id"], "requested_by": record.get("requested_by", clean["requested_by"]), "formula": record.get("formula", clean["formula"]),
                  "dice": record.get("dice"), "final_total": record.get("final_total", record.get("total")),
                  "nat20": record.get("nat20"), "nat1": record.get("nat1"), "resolution": private}
        if clean.get("dc") is not None and private is None and result["final_total"] is not None:
            result["meets_dc"] = result["final_total"] >= int(clean["dc"])
        op = self._op(row["action_id"])
        op["rolls"][clean["roll_key"]] = {"request_hash": request_hash, "slot": slot, "result": result, "by": {"provider": provider, "run": run}}
        self._save_op(op)
        return {"roll_key": clean["roll_key"], "result": result, "replayed": False}

    # ------------------------------------------------------------------ commit and publish
    def _validate_proposal(self, row, op, proposal, state):
        problems = []
        def bad(code, message):
            problems.append({"code": code, "message": message})
        if not isinstance(proposal, dict):
            return [{"code": "BAD_PROPOSAL", "message": "proposal must be an object"}]
        for field in ("world_time", "narration"):
            if not isinstance(proposal.get(field), str) or not proposal[field].strip():
                bad("BAD_PROPOSAL", f"{field} is required")
        context = proposal.get("turn_context")
        if not isinstance(context, dict) or context.get("actor") != row["actor"]:
            bad("BAD_CONTEXT", "turn_context for the player character is required")
        elif any(k not in context for k in ("mode", "budget", "options", "movement", "dialogue", "visible")):
            bad("BAD_CONTEXT", "turn_context must carry mode, budget, options, movement, dialogue and visible")
        elif "context_id" in context:
            bad("BAD_CONTEXT", "context_id is assigned by the ledger, not the provider")
        declaration = row.get("declaration") or {}
        order = list(engine.step_ids(declaration))
        last = -1
        events = proposal.get("events")
        if not isinstance(events, list):
            bad("BAD_PROPOSAL", "events must be a list")
            events = []
        for index, event in enumerate(events, 1):
            if not isinstance(event, dict) or not isinstance(event.get("kind"), str):
                bad("BAD_EVENT", f"event {index} needs a kind")
                continue
            if event["kind"] in RESERVED_KINDS:
                bad("RESERVED_KIND", f"event {index}: {event['kind']} is written by the gateway or the owner, not proposed")
            if event.get("visibility", "player") not in ("player", "gm_only"):
                bad("BAD_EVENT", f"event {index}: visibility is player or gm_only")
            for roll_key in event.get("roll_keys", []):
                if roll_key not in op["rolls"]:
                    bad("UNKNOWN_ROLL", f"event {index} cites roll {roll_key}, which the resolver never accepted")
            if event.get("actor") == row["actor"]:
                step = (event.get("details") or {}).get("step_id")
                if step not in order:
                    bad("ACTS_FOR_PLAYER", f"event {index}: the player character does only what the player declared; cite the declared step")
                else:
                    if order.index(step) < last:
                        bad("STEP_ORDER", f"event {index}: declared steps resolve in the player's order")
                    last = max(last, order.index(step))
        cited = {k for e in events if isinstance(e, dict) for k in e.get("roll_keys", [])}
        for roll_key, known in op["rolls"].items():
            if roll_key not in cited:
                bad("ROLL_UNACCOUNTED", f"accepted roll {roll_key} is binding and must be cited by an event")
        public_text = json.dumps({"n": proposal.get("narration"), "c": context, "s": proposal.get("scene_state"),
                                  "e": [e for e in events if isinstance(e, dict) and e.get("visibility", "player") == "player"]}, ensure_ascii=False)
        hidden = [e for e in ledger.load_all(self.campaign) if e["visibility"] == "gm_only"]
        if brief.player_leaks(public_text, hidden):
            bad("PRIVATE_LEAK", "player-visible text repeats GM-only records")
        tables = (op["tables"] or {}).get("value", {})
        for fragment in (tables.get("tables") or "", tables.get("interpretation") or ""):
            fragment = fragment.strip()[:60]
            if len(fragment) >= 30 and fragment in public_text:
                bad("PRIVATE_LEAK", "player-visible text repeats the GM's private tables")
        if isinstance(context, dict):
            with tempfile.TemporaryDirectory(prefix="genesis-ctx-") as directory:
                path = Path(directory) / "ctx.json"
                path.write_text(json.dumps(context))
                lint = subprocess.run(["node", str(UI / "turn_contract.js"), "lintctx", "-", str(path)], capture_output=True, text=True)
            if lint.returncode != 0:
                bad("CONTEXT_LINT", (lint.stdout.strip() or lint.stderr.strip())[:400])
        text = proposal.get("narration") or ""
        if turn.LASTING.search(text) and not any(e["kind"] == "lasting_injury" for e in export_state.public_events(self.campaign)) \
                and not any(isinstance(e, dict) and e.get("kind") == "lasting_injury" for e in events):
            bad("NARRATION_LINT", "narration describes lasting damage with no lasting_injury event")
        if turn.DEATH.search(text) and "dead" not in [c.lower() for c in state["character"]["conditions"]] \
                and not any(isinstance(e, dict) and e.get("kind") == "condition_change" and "dead" in json.dumps(e.get("details", {})).lower() for e in events):
            bad("NARRATION_LINT", "narration describes a death the events do not contain")
        return problems

    def commit(self, provider, run, proposal):
        """Validate the provider's consequences, commit them as one ledger batch, then publish."""
        (key, version, row), lock = self._holder(provider, run)
        action_id = row["action_id"]
        op = self._op(action_id)
        if not op["commit"]:
            if not op["tables"]:
                raise Refused("TABLES_FIRST", "fix the tables (even with no dice) before committing")
            state = self._public()
            problems = self._validate_proposal(row, op, proposal, state)
            if problems:
                raise Refused("PROPOSAL_REJECTED", "the proposal failed the shared validators; nothing was written", problems=problems)
            all_events = ledger.load_all(self.campaign)
            turn_no = json.loads((self.campaign / "hidden/dice_state.json").read_text())["turn_no"]
            def event(kind, summary, details, visibility="player", actor="gm", causes=None, rolls=None):
                return {"session": all_events[-1].get("session", 1), "turn_no": turn_no, "world_time": proposal["world_time"],
                        "kind": kind, "summary": summary, "actor": actor, "visibility": visibility, "knowledge_type": "fact",
                        "known_to": [], "caused_by": causes or [], "roll_ids": rolls or [], "tags": [], "details": details}
            details = {"action_id": action_id, "text": row.get("text", ""), "declaration": row.get("declaration")}
            if policy.settings(row) != policy.DEFAULT:
                details["resolution_settings"] = policy.settings(row)
            drafts = [event("player_declaration", f"{row['actor']}'s declaration {action_id}", details, actor=row["actor"]),
                      event("gm_ruling", f"Tables fixed before rolling for {action_id}",
                            dict(op["tables"]["value"], gm_provider={"committed_by": provider, "runs": [r["provider"] for r in op["runs"]]}),
                            "gm_only", causes=["$1"])]
            for draft in proposal["events"]:
                rolls = [op["rolls"][k]["result"]["roll_id"] for k in draft.get("roll_keys", [])]
                drafts.append(event(draft["kind"], str(draft.get("summary") or draft["kind"]), draft.get("details") or {},
                                    draft.get("visibility", "player"), draft.get("actor", "gm"), draft.get("caused_by") or ["$1"], rolls))
            count = len(drafts)
            drafts.append(event("gm_narration", f"Narration for {action_id}", {"text": proposal["narration"]}, causes=["$1"]))
            if isinstance(proposal.get("scene_state"), dict):
                drafts.append(event("scene_state", str(proposal["scene_state"].get("summary") or "Scene"), {k: v for k, v in proposal["scene_state"].items() if k != "summary"}, causes=[f"${count+1}"]))
            drafts.append(event("turn_context", f"Turn context after {action_id}", proposal["turn_context"], causes=[f"${count+1}"]))
            request = {"batch_id": action_id, "expected_revision": len(all_events), "expected_head": all_events[-1]["event_id"], "events": drafts}
            op["commit"] = {"request": request, "fingerprint": digest(request), "by": {"provider": provider, "run": run}}
            self._save_op(op)
        key, version, row = self._stage((key, version, row), lock, run, "ledger")
        lease = self._lease_file(lock)
        try:
            result = batch.apply(self.campaign, op["commit"]["request"], lease, run, ledger)
        except ValueError as error:
            raise Refused("COMMIT_REFUSED", str(error))
        finally:
            lease.unlink(missing_ok=True)
        op["commit"]["result"] = result
        self._save_op(op)
        key, version, row = self._stage((key, version, row), lock, run, "narration", status="resolved",
                                        ledger_events=result["events"], publication={"status": "pending"})
        return self._publish((key, version, row), lock, run)

    def publish(self, provider, run):
        """Finish publication of a resolved action. Mechanical: any provider's run may do it; nothing is authored."""
        item, lock = self._holder(provider, run)
        op = self._op(item[2]["action_id"])
        if item[2]["status"] != "resolved":
            if not (op and op.get("commit")):
                raise Refused("NOT_RESOLVED", "nothing is committed for this action yet")
            return self.commit(provider, run, None)
        return self._publish(item, lock, run)

    def _publish(self, item, lock, run):
        key, version, row = item
        try:
            if self.durable:
                self.durable(self.campaign, row["action_id"])
            state = self._public()
            documents = export_state.publish_set(state)
            item = self._stage((key, version, row), lock, run, "publishing")
            for name, page in documents["pages"].items():
                page_version, current = self.store.read("view/" + name)
                if current != page:
                    self.store.put("view/" + name, page, page_version)
            state_version, current = self.store.read("view/state")
            if current and current.get("revision", 0) > documents["state"]["revision"]:
                raise ValueError("the published snapshot is newer than this revision")
            if current != documents["state"]:
                self.store.put("view/state", documents["state"], state_version)
        except (ValueError, OSError, RuntimeError) as error:
            key, version, row = item
            _, row_now = self.store.read(key)
            self.store.put(key, dict(row_now, publication={"status": "pending", "error": str(error)[:300]}), self.store.read(key)[0])
            self._release(run)
            raise Refused("PUBLICATION_PENDING", "resolved and committed; publication will be retried: " + str(error)[:200])
        key, version, row = item
        self._stage((key, version, row), lock, run, "complete", status="committed", publication={"status": "published"},
                    published_revision=documents["state"]["revision"])
        self._release(run)
        return self.action_status(row["action_id"])

    def _release(self, run):
        version, lock = self._lock()
        if lock and lock.get("holder") == run:
            self.store.put("locks/" + self.id, {"holder": None, "provider": lock.get("provider"), "expires_ms": 0, "released_ms": self.clock()}, version)

    def release(self, provider, run, reason=""):
        """Give the lease back without finishing (a clean stop, or the start of a handoff)."""
        (key, version, row), lock = self._holder(provider, run)
        gm = dict(row.get("gm", {}), released={"provider": provider, "reason": str(reason)[:200], "at_ms": self.clock()})
        self.store.put(key, dict(row, gm=gm), version)
        self._release(run)
        return self.action_status(row["action_id"])

    def fail(self, provider, run, reason):
        """Mark a claimed, uncommitted action failed. Lists what was already accepted; never rerolled."""
        (key, version, row), lock = self._holder(provider, run)
        op = self._op(row["action_id"])
        if op.get("commit"):
            raise Refused("ALREADY_COMMITTED", "a committed action cannot fail; publish it")
        self.store.put(key, dict(row, status="failed", error=str(reason)[:300],
                                 rolls=[v["result"]["roll_id"] for v in op["rolls"].values()]), version)
        self._release(run)
        return self.action_status(row["action_id"])
