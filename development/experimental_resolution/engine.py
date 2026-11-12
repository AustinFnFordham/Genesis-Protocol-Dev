"""Sandbox-only transactional front end to the unchanged Genesis deterministic roller.

An accepted write-ahead plan contains exact log suffixes and state replacements.
Recovery completes those bytes; it never calls RNG again. Not a live worker.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / ".claude/skills/litrpg-ledger"))
sys.path.insert(0, str(ROOT / "campaigns/starwars_litrpg/ui"))
import batch
import ledger
import export_state
import policy

spec = importlib.util.spec_from_file_location("original_genesis_roll", ROOT / ".claude/skills/litrpg-dice/roll.py")
roller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(roller)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def identity(action):
    fields = ("actor", "campaign_id", "based_on_revision", "ledger_head", "context_id", "declaration", "text")
    return {**{key: action.get(key) for key in fields}, "resolution_settings": policy.settings(action)}


def sandbox(campaign, action):
    config = json.loads((campaign / "experimental_resolution.json").read_text())
    if config.get("enabled") is not True or config.get("canonical") is not False or config.get("campaign_id") != action.get("campaign_id"):
        raise ValueError("explicit noncanonical experimental campaign configuration required")
    if campaign.resolve().is_relative_to((ROOT / "campaigns/starwars_litrpg/runs").resolve()):
        raise ValueError("original campaign directories are forbidden; use an isolated copy")
    return config


def preflight(campaign, action):
    state = export_state.build(campaign_dir=campaign, campaign_id=action["campaign_id"])
    if action.get("based_on_revision") != state["revision"] or action.get("ledger_head") != state["ledger_head"]:
        raise ValueError("stale action revision or public ledger head")
    context = state.get("turn_context")
    if not context or action.get("context_id") != context.get("context_id"):
        raise ValueError("stale or absent action context")
    if action.get("actor") != state["active_actor"] or action.get("declaration", {}).get("actor", action.get("actor")) != state["active_actor"]:
        raise ValueError("action actor does not match the active player character")
    # Scratch context is within the isolated campaign and removed on every exit.
    path = campaign / "hidden/experimental_preflight.json"
    path.write_text(json.dumps(context))
    try:
        command = ["node", str(ROOT / "campaigns/starwars_litrpg/ui/turn_contract.js")]
        if action.get("declaration"):
            command += ["validate", "-", str(path)]
            value = subprocess.run(command, input=json.dumps(action["declaration"]), capture_output=True, text=True)
        else:
            value = subprocess.run(command+["parse", action.get("text", ""), str(path)], capture_output=True, text=True)
        if value.returncode not in (0, 3):
            raise ValueError("validator unavailable")
        result = json.loads(value.stdout)
        check = result["validation"]
        if not check["legal"] or check.get("crashed") or (check.get("needs_confirmation") and not action.get("confirmed_warnings")):
            raise ValueError("player declaration failed the existing rules validator")
        return result.get("declaration", action.get("declaration"))
    finally:
        path.unlink(missing_ok=True)


def step_ids(declaration):
    def walk(steps):
        for step in steps:
            yield step
            for case in step.get("cases", []):
                yield from walk(case.get("steps", []))
    return {step.get("id"): step for step in walk(declaration.get("steps", []))}


def narrative_face(seed, turn_no, action_id, roll_key):
    material = f"genesis:narrative:v1:{seed}:{turn_no}:{action_id}:{roll_key}"
    domain_seed = int.from_bytes(hashlib.sha256(material.encode()).digest()[:4], "little")
    return 1+int(roller.mulberry(domain_seed)()*6)


def generate(campaign, action_id, action, request, config):
    declaration = preflight(campaign, action)
    step = step_ids(declaration).get(request.get("step_id"))
    if not step or (step.get("pending") and (not step.get("authorized") or step.get("authorized_ctx") != action.get("context_id"))):
        raise ValueError("roll must reference an explicitly authorized declaration step")
    if request.get("kind") not in ("check", "attack", "save", "damage", "other"):
        raise ValueError("roll kind required")
    if request.get("mode", "normal") not in ("normal", "advantage", "disadvantage"):
        raise ValueError("invalid advantage mode")
    if not request.get("rule_sources") or not all(isinstance(x, str) and x for x in request["rule_sources"]):
        raise ValueError("GM roll plan must cite governing rules")
    before = (campaign / "hidden/dice_state.json").read_bytes()
    state = json.loads(before)
    rows = ledger.read_jsonl(campaign / "records/roll_log.jsonl")
    expected_draws = sum(sum(term[2] for term in roller.parse(row["formula"]) if term[0] == "dice") *
                         (2 if row["mode"] != "normal" else 1) for row in rows if row["turn_no"] == state["turn_no"])
    if (len(rows) != state["roll_count"] or len({row["roll_id"] for row in rows}) != len(rows) or
        state["draws_used"] != expected_draws):
        raise ValueError("legacy dice log/cursor mismatch; manual reconciliation required before new rolls")
    stream = roller.mulberry((state["seed"] ^ (state["turn_no"]*0x9E3779B9)) & 0xFFFFFFFF)
    for _ in range(state["draws_used"]):
        stream()
    used = 0
    def counted():
        nonlocal used
        used += 1
        return stream()
    dice, alt, raw, mods, d20 = roller.do_roll(request["formula"], request.get("mode", "normal"), counted)
    state["draws_used"] += used
    state["roll_count"] += 1
    actor = request.get("requested_by", action.get("actor"))
    record = {"roll_id": f"roll_t{state['turn_no']}_{state['roll_count']}", "turn_no": state["turn_no"],
              "requested_by": actor, "purpose": f"[{action_id}] {request.get('purpose', 'experimental roll')}",
              "formula": request["formula"], "mode": request.get("mode", "normal"), "dice": dice, "alt_dice": alt,
              "raw_total": raw, "modifiers": mods, "final_total": raw+mods,
              "nat20": d20 and dice[0]["rolled"][0] == 20, "nat1": d20 and dice[0]["rolled"][0] == 1}
    selected = policy.settings(action)
    controlled = actor == action.get("actor") and actor in config.get("controlled_actors", [])
    resolution = policy.resolve(record, selected, request["kind"], controlled, request.get("dc"))
    if resolution["eligible"] and selected["narrative_consequences"]:
        # Domain-separated per-request stream. Zero ordinary draws consumed.
        face = narrative_face(state["seed"], state["turn_no"], action_id, request["roll_key"])
        resolution = policy.resolve(record, selected, request["kind"], controlled, request.get("dc"), face)
        resolution["narrative_stream"] = {"domain": "genesis:narrative:v1", "algorithm": "mulberry32",
                                          "request": request["roll_key"], "draw_index": 0}
    record["resolution"] = policy.public_resolution(resolution)
    record["resolution_provenance"] = {"action_id":action_id,"step_id":request["step_id"],"roll_key":request["roll_key"]}
    logs = {"records/roll_log.jsonl": record,
            "hidden/experimental_resolution_log.jsonl": {"roll_id": record["roll_id"], "action_id": action_id,
                "ordinary_draw_start": state["draws_used"]-used, "ordinary_draw_end": state["draws_used"],
                "request": request, "resolution": resolution}}
    if request.get("dc") is not None:
        logs["hidden/roll_dcs.jsonl"] = {"roll_id": record["roll_id"], "dc": request["dc"], "outcome": resolution["task"]["result"]}
    streams = {}
    for relative, row in logs.items():
        path = campaign / relative
        original = path.read_bytes() if path.exists() else b""
        if original and not original.endswith(b"\n"):
            raise ValueError("incomplete prior roll log; reconcile it before rolling")
        streams[relative] = {"size": len(original), "hash": batch.digest(original), "tail": json.dumps(row)+"\n"}
    return {"streams": streams, "state": {"before": before.decode(), "after": json.dumps(state, indent=1)},
            "result": {"roll": record, "resolution": resolution}}


def execute(campaign, action_id, action, request, after_write=None):
    campaign = Path(campaign)
    config = sandbox(campaign, action)
    policy.settings(action)
    if not isinstance(action_id, str) or not action_id or not isinstance(request.get("roll_key"), str) or not request["roll_key"]:
        raise ValueError("stable action ID and roll_key required")
    request_hash = fingerprint({"action": identity(action), "request": request, "action_id": action_id})
    key = fingerprint([action_id, request["roll_key"]])
    pending = campaign / "hidden/experimental_dice_pending.json"
    receipts = campaign / "hidden/experimental_dice_receipts"
    bindings = campaign / "hidden/experimental_action_bindings"
    def checkpoint(name):
        if after_write:
            after_write(name)
    with batch.writer_lock(campaign):
        if (campaign / "hidden/ledger_batch_pending.json").exists():
            raise ValueError("recover the accepted ledger batch before rolling")
        receipts.mkdir(exist_ok=True)
        bindings.mkdir(exist_ok=True)
        binding = bindings / (fingerprint(action_id)+".json")
        value = {"action_hash": fingerprint(identity(action)), "campaign_id": action["campaign_id"]}
        if binding.exists() and json.loads(binding.read_text()) != value:
            raise ValueError("immutable action or selected resolution settings changed")
        slot = bindings / ("slot-"+fingerprint([action_id, request.get("step_id"), request.get("kind"),
                                               request.get("requested_by", action.get("actor"))])+".json")
        slot_value = {"request_hash":request_hash}
        if slot.exists() and json.loads(slot.read_text()) != slot_value:
            raise ValueError("this step/actor/roll-kind already has an accepted roll; a new key cannot reroll it")
        receipt = receipts / (key+".json")
        if receipt.exists() and not pending.exists():
            done = json.loads(receipt.read_text())
            if done["fingerprint"] != request_hash:
                raise ValueError("roll retry differs from the accepted request")
            return done["result"]
        if pending.exists():
            plan = json.loads(pending.read_text())
            if plan["fingerprint"] != request_hash:
                raise ValueError("another dice request needs recovery first")
        else:
            plan = generate(campaign, action_id, action, request, config)
            if not binding.exists():
                batch.durable_json(binding, value)
            if not slot.exists():
                batch.durable_json(slot, slot_value)
            plan["fingerprint"] = request_hash
            batch.durable_json(pending, plan)
            checkpoint("accepted")
        # Validate ALL paths before resuming any suffix. Never truncate originals.
        for relative, stream in plan["streams"].items():
            path = campaign / relative
            current = path.read_bytes() if path.exists() else b""
            prefix, tail = current[:stream["size"]], current[stream["size"]:]
            if len(prefix) != stream["size"] or batch.digest(prefix) != stream["hash"] or not stream["tail"].encode().startswith(tail):
                raise ValueError("dice log bytes diverged from the accepted plan")
        state_path = campaign / "hidden/dice_state.json"
        if state_path.read_bytes().decode() not in (plan["state"]["before"], plan["state"]["after"]):
            raise ValueError("dice cursor diverged; manual review required")
        for relative, stream in plan["streams"].items():
            path = campaign / relative
            offset = path.stat().st_size-stream["size"] if path.exists() else 0
            with path.open("ab") as handle:
                handle.write(stream["tail"].encode()[offset:])
                handle.flush()
                os.fsync(handle.fileno())
            checkpoint("append:"+relative)
        temporary = state_path.with_suffix(".experimental.tmp")
        with temporary.open("wb") as handle:
            handle.write(plan["state"]["after"].encode())
            handle.flush()
            os.fsync(handle.fileno())
        checkpoint("state:temporary")
        os.replace(temporary, state_path)
        batch.sync_directory(state_path.parent)
        checkpoint("state:replaced")
        batch.durable_json(receipt, {"fingerprint": request_hash, "result": plan["result"]})
        checkpoint("receipt")
        pending.unlink()
        batch.sync_directory(pending.parent)
        return plan["result"]


def replay(campaign):
    """Recompute both axes from immutable raw records and private seed; read-only."""
    campaign = Path(campaign)
    state = json.loads((campaign / "hidden/dice_state.json").read_text())
    records = {row["roll_id"]: row for row in ledger.read_jsonl(campaign / "records/roll_log.jsonl")}
    rows = ledger.read_jsonl(campaign / "hidden/experimental_resolution_log.jsonl")
    config = json.loads((campaign / "experimental_resolution.json").read_text())
    errors = []
    for row in rows:
        raw, resolution, request = records[row["roll_id"]], row["resolution"], row["request"]
        axis = resolution.get("narrative")
        face = narrative_face(state["seed"], raw["turn_no"], row["action_id"], request["roll_key"]) if axis else None
        expected = policy.resolve(raw, resolution["settings"], request["kind"], raw["requested_by"] in config["controlled_actors"], request.get("dc"), face)
        if axis:
            expected["narrative_stream"] = {"domain":"genesis:narrative:v1","algorithm":"mulberry32","request":request["roll_key"],"draw_index":0}
        if expected != resolution or policy.public_resolution(expected) != raw["resolution"]:
            errors.append(row["roll_id"])
    return {"ok":not errors,"records":len(rows),"mismatched_rolls":errors}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("action_id")
    parser.add_argument("action", type=Path)
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(execute(args.campaign, args.action_id, json.loads(args.action.read_text()), json.loads(args.request.read_text()))))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(3, str(error)+"\n")
