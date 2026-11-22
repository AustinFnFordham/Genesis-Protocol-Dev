"""Offline-only conformance benchmark. No gateway imports, writes, or random rolls."""
import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import time
import urllib.request

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parent / "GM_GUIDE.md"
SCHEMA = HERE / "move.schema.json"
FIXTURES = HERE / "fixtures.json"
OLLAMA = "http://127.0.0.1:11434"
MODELS = ("qwen2.5:14b", "qwen2.5-coder:32b")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def score(raw, case, validator):
    try:
        move = json.loads(raw, object_pairs_hook=reject_duplicates)
    except (ValueError, TypeError):
        return ["JSON: return exactly one JSON object with unique member names"]
    if not isinstance(move, dict):
        return ["SCHEMA: root must be an object"]
    rules = case["expect"]
    issues = []
    kind = move.get("type")
    if kind != rules["type"]:
        issues.append("PHASE: use " + rules["type"] + " for the committed context")
    for error in sorted(validator.iter_errors(move), key=lambda e: tuple(map(str, e.path))):
        branches = list(error.context)
        matching = [e for e in branches if e.schema_path[0] == {
            "review": 0, "tables": 1, "rolls": 2, "commit": 3
        }.get(kind)] if isinstance(kind, str) else []
        for item in matching or [error]:
            path = ".".join(map(str, item.path)) or "root"
            issues.append(f"SCHEMA: {path} failed {item.validator}")
    # Review is entirely public. Private table contents are intentionally excluded.
    proposal = move.get("proposal")
    public = move.get("review", {})
    if isinstance(proposal, dict):
        events = proposal.get("events", [])
        public = {k: v for k, v in proposal.items() if k != "events"}
        public["events"] = [e for e in events if isinstance(e, dict) and e.get("visibility") != "gm_only"] if isinstance(events, list) else []
    public_text = json.dumps(public, ensure_ascii=False).lower()
    if kind == "rolls" and isinstance(move.get("rolls"), list):
        public_text += json.dumps([r.get("purpose") for r in move["rolls"] if isinstance(r, dict)]).lower()
    for pattern in rules.get("private_patterns", []):
        if re.search(pattern, public_text):
            issues.append("SECRECY: keep private facts out of player-visible fields")
            break
    if any(x.startswith("SCHEMA:") for x in issues) or kind != rules["type"]:
        return list(dict.fromkeys(issues))
    if kind == "review":
        if rules["code"] not in [e["code"] for e in move["review"]["errors"]]:
            issues.append("MECHANICS: review must cite the applicable validation code")
        if move["review"]["alternatives"]:
            issues.append("AGENCY: no authorized alternatives are listed in this context")
    elif kind == "tables":
        stage = move["tables"]
        evaluations = stage["npc_evaluations"]
        if [e["npc"] for e in evaluations] != rules.get("npcs", []):
            issues.append("NPC: evaluate only NPCs with a pending decision")
        for e in evaluations:
            if not set(rules.get("npc_changes", [])) <= set(e["changes"]):
                issues.append("NPC: cite intervening committed events")
            if rules.get("npc_basis") and not re.search(rules["npc_basis"], e["basis"], re.I):
                issues.append("NPC: ground the decision in the recorded motive")
        if rules.get("no_roll") and not re.search(r"no (?:roll|uncertainty|table|dice)|not (?:needed|required)|none|required: no", stage["tables"], re.I):
            issues.append("MECHANICS: routine action requires no roll or table")
        if not re.search(rules["interpretation"], stage["interpretation"], re.I):
            issues.append("FIDELITY: interpretation omits a required action consequence")
    elif kind == "rolls":
        rolls = move["rolls"]
        for roll in rolls:
            if any(roll.get(k) != v for k, v in rules["roll"].items()):
                issues.append("MECHANICS: use only the authorized roll specification")
            if roll["roll_key"] in case["context"]["operation"]["rolls"]:
                issues.append("RECEIPT: accepted roll must not be requested again in this fixture")
        if len(rolls) != 1:
            issues.append("RECEIPT: request exactly one outstanding roll")
    elif kind == "commit":
        events = proposal["events"]
        known = case["context"]["operation"]["rolls"]
        references = Counter(key for event in events for key in event["roll_keys"])
        if references != Counter(known.keys()):
            issues.append("RECEIPT: cite each accepted roll exactly once, with no invented roll keys")
        acted = [e["details"].get("step_id") for e in events if e["actor"] == "zara"]
        if acted != rules["steps"] or any(e["kind"] not in rules["event_kinds"] for e in events):
            issues.append("AGENCY: commit only the declared executable prefix and supported consequences")
        ctx = proposal["turn_context"]
        if ctx.get("context_id") or ctx.get("pending_steps", []) != rules.get("pending", []):
            issues.append("CONTINUITY: preserve the exact pending steps and omit context_id")
        if rules.get("pending") and not ctx.get("pending_reason"):
            issues.append("CONTINUITY: explain the player-visible reason to stop")
        if any(not re.search(p, proposal["narration"], re.I) for p in rules["narration"]):
            issues.append("FIDELITY: narration omits required established facts")
        if any(re.search(p, proposal["narration"], re.I) for p in rules.get("forbidden_narration", [])):
            issues.append("FIDELITY: narration invents an unsupported outcome")
    return list(dict.fromkeys(issues))


def request(path, payload=None, timeout=180):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA + path, data=body, headers={"Content-Type": "application/json"})
    # The only network target is the loopback Ollama service, with no proxy or credentials.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout) as response:
        return json.load(response)


def fixture_phase(context):
    """Select a move from synthetic authority state, never from the grading oracle."""
    operation = context["operation"]
    if not context["validation"]["legal"]:
        if operation["tables"] is not None or operation["rolls"]:
            raise ValueError("Review is unavailable after mechanical acceptance")
        return "review"
    required = set(context["resolution"].get("fixture_required_roll_keys", []))
    accepted = set(operation["rolls"])
    if operation["tables"] is None:
        if accepted:
            raise ValueError("Receipts require accepted tables")
        return "tables"
    return "rolls" if required - accepted else "commit"


def phase_schema(schema, phase):
    return next(branch for branch in schema["oneOf"]
                if branch["properties"]["type"]["const"] == phase)


def run_case(case, generate, guide, schema, validator, mode, repairs):
    context = copy.deepcopy(case["context"])
    messages = [{"role": "system", "content": guide + "\nUse only the supplied synthetic context. No tools are available."},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)}]
    output_format = schema if mode == "schema" else "json"
    if mode == "phase":
        phase = fixture_phase(context)
        output_format = phase_schema(schema, phase)
        messages.append({"role": "user", "content": f"The authorized next move is {phase}."})
        if phase == "tables" and context["resolution"].get("fixture_routine"):
            messages[-1]["content"] += ' Use the exact tables text "No roll required."'
    attempts = []
    for index in range(repairs + 1):
        start = time.perf_counter()
        reply = generate(messages, output_format)
        raw = reply["message"]["content"]
        errors = score(raw, case, validator)
        attempts.append({"errors": errors, "wall_ms": round((time.perf_counter() - start) * 1000, 1),
                         "load_ms": round(reply.get("load_duration", 0) / 1e6, 1),
                         "generated_tokens": reply.get("eval_count"), "done_reason": reply.get("done_reason")})
        if not errors or index == repairs:
            break
        messages += [{"role": "assistant", "content": raw},
                     {"role": "user", "content": json.dumps({"feedback": errors, "instruction":
                        "Return the corrected move only. The original declaration and receipts are immutable."})}]
    return {"fixture": case["id"], "attempts": attempts}


def summarize(rows):
    initial = sum(not row["attempts"][0]["errors"] for row in rows)
    final = sum(not row["attempts"][-1]["errors"] for row in rows)
    repaired = final - initial
    attempts = [a for row in rows for a in row["attempts"]]
    wall = sorted(a["wall_ms"] for a in attempts)
    def counts(samples):
        return dict(Counter(code for a in samples for code in
                            {e.split(":", 1)[0] for e in a["errors"]}))
    return {"cases": len(rows), "first_pass": initial, "final_pass": final,
            "repaired": repaired, "repair_candidates": len(rows) - initial,
            "first_error_categories": counts(row["attempts"][0] for row in rows),
            "final_error_categories": counts(row["attempts"][-1] for row in rows),
            "attempts": len(attempts), "wall_p50_ms": statistics.median(wall),
            "wall_p95_ms": wall[math.ceil(0.95 * len(wall)) - 1],
            "first_load_ms": attempts[0]["load_ms"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", choices=MODELS, required=True)
    parser.add_argument("--mode", action="append", choices=("json", "schema", "phase"), default=None)
    parser.add_argument("--repeats", type=int, choices=range(1, 6), default=1)
    parser.add_argument("--repairs", type=int, choices=range(3), default=1)
    parser.add_argument("--fixture", action="append")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = load(FIXTURES)
    if args.fixture:
        cases = [case for case in cases if case["id"] in args.fixture]
        if len(cases) != len(set(args.fixture)):
            parser.error("unknown fixture")
    schema = load(SCHEMA)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    models = {item["name"]: item for item in request("/api/tags")["models"]}
    report = {"ollama_version": request("/api/version")["version"],
              "inputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (GUIDE, SCHEMA, FIXTURES, Path(__file__))},
              "temperature": 0, "seed": 22, "num_predict": 900, "num_ctx": 4096,
              "repeats": args.repeats, "repairs": args.repairs, "groups": []}
    for model in args.model:
        if model not in models:
            parser.error(f"{model} must already be installed; no model pull is performed")
        def generate(messages, output_format):
            return request("/api/chat", {"model": model, "messages": messages,
                       "format": output_format, "stream": False, "keep_alive": "5m",
                       "options": {"temperature": 0, "seed": 22, "num_predict": 900, "num_ctx": 4096}})
        for mode in args.mode or ["json"]:
            rows = [run_case(case, generate, GUIDE.read_text(encoding="utf-8"), schema,
                             validator, mode, args.repairs) for _ in range(args.repeats) for case in cases]
            group = {"model": model, "digest": models[model]["digest"], "mode": mode,
                     "summary": summarize(rows), "rows": rows}
            report["groups"].append(group)
            # Preserve completed models/configurations if the next load fails.
            if args.output:
                args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({k: v for k, v in group.items() if k != "rows"}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
