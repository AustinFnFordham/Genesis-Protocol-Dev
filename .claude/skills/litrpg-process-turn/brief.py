#!/usr/bin/env python3
"""READ-ONLY context brief for the Datapad GM (PROTOTYPE, step 1, sandbox evaluation only).

Not used by the live processor. Nothing here writes the ledger, rolls dice, edits a campaign or
touches the Artifact database. It replays the authoritative ledger and emits a versioned bundle.

  brief.py brief   <campaign_id> [--head evt_N] [--audience gm|player] [--expect-head evt_N]
                                 [--checkpoint FILE] [--save-checkpoint FILE] [--out FILE]
  brief.py history <campaign_id> <evt_id>... [--audience gm|player]
  brief.py verify  <campaign_id>             incremental == full replay at every head, rejection and leak tests

Principles (owner rulings 2026-11-07):
  * The ledger is the only authority. The checkpoint is derived and is never trusted unchecked.
  * A field is "typed" only when an event's structured `details` (or the character sheet) states it.
    Prose is never parsed into a value: it is carried as a reference with status missing/uncertain.
  * The player audience is built from public events only; hidden ids and text never enter it.
Exit codes: 0 ok, 3 stale/rejected, 2 usage or ledger error.
"""
import argparse, copy, hashlib, importlib.util, json, re, subprocess, sys, time, tempfile
from pathlib import Path

SCHEMA = "genesis-brief/0.1"
REDUCER = "reduce/0.4"
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REGISTRY = REPO / "campaigns" / "starwars_litrpg" / "runs" / "registry.json"
SHEET = REPO / "api_bridge" / "gm" / "aero_character_runtime.yml"
sys.path.insert(0, str(REPO / "development/experimental_resolution"))
import policy as resolution_policy
ID = re.compile(r"^evt_(\d+)$")
PRESENT = {"gm_narration", "scene_state", "turn_context", "gm_suggestions"}
JOURNAL_SKIP = PRESENT | {"player_declaration", "ruling_void", "party_joined", "party_left"}
RULE_FILES = ["campaigns/starwars_litrpg/CAMPAIGN_CHARTER.md", "campaigns/starwars_litrpg/creator/TURN_CONTRACT.md",
              "campaigns/starwars_litrpg/creator/NARRATIVE_SPEC.md", "campaigns/starwars_litrpg/creator/continuity_rule.json"]
# Prototype relevance config: scene entity -> words that mark an event as about it. A real build reads
# this from the roster / registry; until then it is campaign config, not inference.
ALIASES = {"wick": ("wick",), "ruddick": ("ruddick",), "pack": ("drover_pack", "pack", " dog", "dogs", "biscuit", "voice-dog"),
           "tolliver": ("tolliver", "marga", "warden"), "missing_mother": ("daria", "woman's voice", "his mother")}
MINUTES = re.compile(r"\b(\d+)\s*minutes?\b", re.I)


class Rejected(Exception):
    pass


def seq(eid):
    m = ID.match(eid or "")
    if not m:
        raise Rejected(f"bad event id {eid!r}")
    return int(m.group(1))


def ledger_mod():
    spec = importlib.util.spec_from_file_location("litrpg_ledger_brief", REPO / ".claude" / "skills" / "litrpg-ledger" / "ledger.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def run_entry(cid):
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))["runs"]
    if cid not in reg:
        raise Rejected(f"unknown campaign id {cid!r}")
    e = dict(reg[cid]); e["id"] = cid; e["path"] = REPO / e["dir"]
    return e


def load_events(run_dir):
    """All events in id order. Duplicate ids or gaps in the shared sequence are rejected, never repaired."""
    led = ledger_mod()
    ev = led.load_all(Path(run_dir))
    ids = [seq(e["event_id"]) for e in ev]
    if len(set(ids)) != len(ids):
        raise Rejected("duplicate event ids in the ledger")
    if ids and ids != list(range(1, ids[-1] + 1)):
        raise Rejected("gap in the event sequence")
    return ev


def text_of(e):
    return (e.get("summary") or "") + " " + json.dumps(e.get("details") or {}, ensure_ascii=False)


# ------------------------------------------------------------------ reducer (pure, one event at a time)
def empty(campaign):
    return {"schema": SCHEMA, "reducer": REDUCER, "campaign": campaign, "head": None, "events": 0, "public": 0,
            "chain": "0" * 64, "public_head": None, "turn_no": 0, "world_time": None, "last_action": None, "voided": [],
            "flags_obj": [], "flags_obj_evt": None, "turn_context": None, "scene": None, "narration": None,
            "resolution_settings": dict(resolution_policy.DEFAULT),
            "hands": None, "hand_touch_after": [], "position": None, "comm": None,
            "clock_ruddick": None, "clock_mentions_after": [], "hp_delta": 0, "conditions": None, "cond_evt": None,
            "npc_public": {}, "plans": {}, "positions_refs": [], "replay_refs": [], "standing": [], "tables": [],
            "hidden_facts": [], "insight": {}, "entity_index": {}, "lines": {}, "journal": [], "rolls": []}


def reduce(s, e, public_projection=False):
    n = seq(e["event_id"])
    if not public_projection and s["head"] is None and n != 1:
        raise Rejected(f"out of order: {e['event_id']} applied to an empty state")
    if s["head"] is not None and (n <= seq(s["head"]) or (not public_projection and n != seq(s["head"]) + 1)):
        raise Rejected(f"out of order or duplicate: {e['event_id']} after {s['head']}")
    if not public_projection and e["visibility"] != "gm_only":
        s["_player"] = reduce(s.get("_player", empty(s["campaign"])), e, public_projection=True)
    s["head"] = e["event_id"]; s["events"] += 1
    s["chain"] = hashlib.sha256((s["chain"] + json.dumps(e, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()
    hid = e["visibility"] == "gm_only"
    if not hid:
        s["public"] += 1; s["public_head"] = e["event_id"]
    s["turn_no"] = e.get("turn_no", s["turn_no"]); s["world_time"] = e.get("world_time") or s["world_time"]
    k, d, a, eid = e["kind"], e.get("details") or {}, e.get("actor"), e["event_id"]
    summary = e["summary"]
    if public_projection:
        summary = re.sub(r"\s*\([^)]*\btable\s+evt_\d+[^)]*\)", "", summary)
        summary = re.sub(r"evt_\d+", "[event reference]", summary)
    s["lines"][eid] = {"kind": k, "vis": e["visibility"], "line": summary[:160]}
    if k == "ruling_void":
        s["voided"] += d.get("voids", [])
    if k == "player_declaration":
        s["last_action"] = {"action_id": d.get("action_id"), "evt": eid}; s["rolls"] = []
        s["resolution_settings"] = resolution_policy.settings(d)
    if not hid:
        s["rolls"] += [r for r in e.get("roll_ids") or [] if r not in s["rolls"]]
    # typed: equipment flags from object interactions (grants/removes)
    if k == "object_interaction" and a in (None, "aero"):
        for f in d.get("grants") or []:
            if f not in s["flags_obj"]:
                s["flags_obj"].append(f)
        for f in d.get("removes") or []:
            if f in s["flags_obj"]:
                s["flags_obj"].remove(f)
        if d.get("grants") or d.get("removes"):
            s["flags_obj_evt"] = eid
    # typed: hands (only when an event states them); later item events make them uncertain
    if isinstance(d.get("hands"), dict) and a in (None, "aero"):
        s["hands"] = {"value": d["hands"], "evt": eid}; s["hand_touch_after"] = []
    elif s["hands"] and a in (None, "aero") and (k == "object_interaction" or "hand" in d):
        s["hand_touch_after"].append(eid)
    if k == "turn_context":
        s["turn_context"] = {**d, "context_id": eid}
    elif k == "scene_state":
        s["scene"] = {**d, "evt": eid}
    elif k == "gm_narration":
        s["narration"] = {"evt": eid, "text": d.get("text", "")}
    if k == "movement" and a == "aero":
        s["position"] = {"value": d.get("position") or d.get("to"), "distance_after": d.get("distance_after"), "evt": eid}
    if k == "comm_call" and "channel" in d:
        s["comm"] = {"channel": d["channel"], "with": d.get("with"), "evt": eid}
    if k == "hp_change" and d.get("target") == "aero":
        s["hp_delta"] += d.get("delta", 0)
    if k == "condition_change" and d.get("target") == "aero":
        s["conditions"] = d.get("conditions", []); s["cond_evt"] = eid
    # typed clock: only explicit structured keys count; prose minutes are recorded as mentions, never as values
    if "clock_minutes_left" in d or "deadline" in d:
        s["clock_ruddick"] = {"value": {x: d[x] for x in ("clock_minutes_left", "deadline") if x in d}, "evt": eid, "vis": e["visibility"]}
        s["clock_mentions_after"] = []
    elif s["clock_ruddick"] and MINUTES.search(text_of(e)) and ("ruddick" in text_of(e).lower() or "lift" in text_of(e).lower()):
        s["clock_mentions_after"].append({"evt": eid, "vis": e["visibility"]})
    if hid:
        if k == "npc_plan":
            s["plans"].setdefault(a or "gm", []).append(eid)
        elif k == "world_fact" and e["summary"].startswith("Positions after"):
            s["positions_refs"].append(eid)
        elif "verbatim replay" in e["summary"]:
            s["replay_refs"].append(eid)
        elif k in ("npc_profile", "system_origin", "gm_setup", "npc_belief") or e.get("turn_no") == 0:
            s["standing"].append(eid)
        elif k == "gm_ruling":
            s["tables"].append(eid)
        else:
            s["hidden_facts"].append(eid)
    elif k in ("npc_dialogue", "npc_reaction") and a:
        s["npc_public"][a] = eid
    if k == "skill_check" and (d.get("skill") == "insight" or "insight" in e["summary"].lower()) and not hid:
        for ent, al in ALIASES.items():
            if any(x in e["summary"].lower() for x in al):
                s["insight"].setdefault(ent, []).append(eid)
    if k not in PRESENT and k != "player_declaration":
        low = (e["summary"] + " " + (a or "")).lower()
        for ent, al in ALIASES.items():
            if any(x in low for x in al):
                s["entity_index"].setdefault(ent, []).append(eid)
    if not hid and k not in JOURNAL_SKIP:
        s["journal"].append({"id": eid, "kind": k, "k": e["knowledge_type"], "known_to": e.get("known_to") or [], "t": e["world_time"]})
    return s


def fold(s, events):
    for e in events:
        s = reduce(s, e)
    return s


def chain_upto(events, head):
    c = "0" * 64
    for e in events:
        if seq(e["event_id"]) > seq(head):
            break
        c = hashlib.sha256((c + json.dumps(e, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()
    return c


# ------------------------------------------------------------------ fields with status and provenance
def F(value, status, src=None, note=None, refs=None):
    out = {"value": value, "status": status}
    if src:
        out["source"] = src
    if note:
        out["note"] = note
    if refs:
        out["refs"] = refs
    return out


def fields(s, sheet, audience):
    pub = audience == "player"
    vis_ok = lambda ref: not pub or s["lines"].get(ref, {}).get("vis") != "gm_only"
    out = {}
    tc = s["turn_context"] or {}
    # flags: two typed sources must agree
    tc_flags = sorted(tc.get("state_flags") or [])
    obj_flags = sorted(s["flags_obj"])
    if tc and tc_flags != obj_flags:
        out["aero.flags"] = F(None, "conflict", note=f"turn_context {tc.get('context_id')} says {tc_flags}; object interactions (last {s['flags_obj_evt']}) say {obj_flags}")
    else:
        out["aero.flags"] = F(obj_flags, "typed", src=[x for x in (s["flags_obj_evt"], tc.get("context_id")) if x])
    if s["hands"]:
        hv = s["hands"]["value"]
        if s["hand_touch_after"]:
            out["aero.hands"] = F(hv, "uncertain", src=s["hands"]["evt"], refs=s["hand_touch_after"],
                                  note="hands were last stated at the source event; later events touched held items without restating the hands")
        else:
            out["aero.hands"] = F(hv, "typed", src=s["hands"]["evt"])
    else:
        out["aero.hands"] = F(None, "missing", note="no event states hand occupancy")
    out["aero.position"] = F(s["position"]["value"], "typed", src=s["position"]["evt"], note="distance_after: " + json.dumps(s["position"]["distance_after"])) if s["position"] else F(None, "missing")
    hp_max = sheet["defenses"]["maximum_hp"]
    out["aero.hp"] = F([max(0, min(hp_max, sheet["defenses"]["current_hp"] + s["hp_delta"])), hp_max], "typed", src="sheet + hp_change events")
    out["aero.conditions"] = F(s["conditions"] if s["conditions"] is not None else sheet["defenses"].get("conditions", []), "typed", src=s["cond_evt"] or "sheet")
    out["aero.equipment"] = F({"weapons": [w["name"] for w in sheet["equipment"]["weapons"]], "inventory": [i["item"] for i in sheet["equipment"]["inventory"]]},
                              "typed_static", src="api_bridge/gm/aero_character_runtime.yml",
                              note="static sheet; the ledger has no typed item transfers, so drops or losses would not appear here")
    out["scene.light_and_visibility"] = F(None, "missing", note="light, darkness and sight lines are stated only in turn-context notes (prose)",
                                          refs=[tc["context_id"]] if tc else None)
    out["comm.channel"] = F(s["comm"]["channel"], "typed", src=s["comm"]["evt"], note=f"with {s['comm']['with']}") if s["comm"] else F(None, "missing")
    c = s["clock_ruddick"]
    if c and vis_ok(c["evt"]):
        later = [m["evt"] for m in s["clock_mentions_after"] if not pub or m["vis"] != "gm_only"]
        if later:
            out["clock.ruddick_lift"] = F(c["value"], "stale_suspect", src=c["evt"], refs=later,
                                          note="later events mention minutes in prose only; the typed value is not updated and prose is not parsed into a value. Read the refs.")
        else:
            out["clock.ruddick_lift"] = F(c["value"], "typed", src=c["evt"])
    else:
        out["clock.ruddick_lift"] = F(None, "missing")
    if not pub:
        out["clock.pack_review"] = F(None, "missing", note="stated in prose only", refs=[x for x in s["standing"] + s["plans"].get("gm", [])[:1] if x == "evt_0005"] or None)
    # Wick's private intentions: never typed. Player sees Aero's own reads; GM also gets hidden refs.
    ins = [x for x in s["insight"].get("wick", []) if vis_ok(x)]
    if pub:
        out["npc.wick.intent"] = F(None, "missing", note="private; Aero has only his own Insight reads (observations, not facts about intent)", refs=ins or None)
    else:
        hrefs = [x for x in s["entity_index"].get("wick", []) if s["lines"][x]["vis"] == "gm_only"][-8:]
        out["npc.wick.intent"] = F(None, "missing", note="no typed intent field; seed in hidden/GM_LEDGER.md; read refs", refs=(ins + hrefs) or None)
    if pub:
        obs = [j["id"] for j in s["journal"] if j["kind"] == "observation"]
        out["creatures.positions"] = F(None, "unknown_to_player", note="Aero cannot see them; his latest observations are the refs",
                                       refs=obs[-4:] or None)
    else:
        pr = s["positions_refs"]
        out["creatures.positions"] = F(None, "uncertain", src=pr[-1] if pr else None, refs=pr[-3:] or None,
                                       note="prose world_fact; 'latest wins' is a heuristic because events carry no supersedes field")
    return out


# ------------------------------------------------------------------ bundle
def sha(path):
    p = REPO / path
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else None


def git_info(run_dir):
    def g(*a):
        r = subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    rel = str(Path(run_dir).relative_to(REPO))
    dirty = g("status", "--porcelain", "--", rel)
    return {"commit": g("rev-parse", "--short", "HEAD"), "branch": g("rev-parse", "--abbrev-ref", "HEAD"),
            "ledger_files_committed": dirty == "", "ahead_of_upstream": g("rev-list", "--count", "@{u}..HEAD")}


def bundle(s, entry, audience, sheet, validation):
    pub = audience == "player"
    if pub:
        s = s.get("_player", empty(s["campaign"]))
    voided = set(s["voided"])
    hidden_ids = {i for i, l in s["lines"].items() if l["vis"] == "gm_only"}
    line = lambda i: [i, s["lines"][i]["kind"] + ": " + s["lines"][i]["line"]]
    tc = s["turn_context"] or {}
    scene_ents = {"wick", "ruddick", "pack", "missing_mother"} & set(s["entity_index"])  # prototype cast; real: from visible + comm + plans
    ent_hist = {}
    for ent in sorted(scene_ents):
        ids = [i for i in s["entity_index"][ent] if i not in voided and (not pub or i not in hidden_ids)]
        ent_hist[ent] = [line(i) for i in ids]
    journal = [j for j in s["journal"] if j["id"] not in voided]
    b = {
        "meta": {"schema": SCHEMA, "reducer": REDUCER, "audience": audience, "campaign_id": entry["id"], "run_dir": entry["dir"],
                 # the player audience never sees the global head (it may be a hidden event id) or the chain
                 "ledger": ({"public_head": s["public_head"], "public_events": s["public"]} if pub else
                            {"head": s["head"], "events": s["events"], "public_head": s["public_head"], "public_events": s["public"],
                             "chain": s["chain"], "valid": validation["valid"], "problems": validation["problems"]}),
                 "git": git_info(entry["path"]),
                 "ruleset": {p.split("/")[-1]: sha(p) for p in RULE_FILES},
                 "turn_no": s["turn_no"], "world_time": s["world_time"], "last_action": s["last_action"]},
        "fields": fields(s, sheet, audience),
        "scene": s["scene"], "turn_context": tc or None,
        "last_narration": s["narration"],
        "last_rolls": s["rolls"],
        "resolution_settings": s["resolution_settings"],
        "journal_recent": [line(j["id"]) + [j["k"]] for j in journal[-12:]],
        "journal_reports_beliefs": [line(j["id"]) + [j["k"], j["known_to"]] for j in journal if j["k"] in ("report", "belief")],
        "entity_history": ent_hist,
        "retrieval": "Full text of any listed event: brief.py history <campaign_id> <evt_id> (player audience cannot fetch hidden events).",
    }
    if not pub:
        b["meta"]["ruleset"].update({"GM_LEDGER.md": sha(entry["dir"] + "/hidden/GM_LEDGER.md"), "PACK_PROFILE.md": sha(entry["dir"] + "/hidden/PACK_PROFILE.md")})
        b["hidden"] = {"plans": {a: [line(i) for i in ids[-3:]] for a, ids in s["plans"].items()},
                       "positions": [line(i) for i in s["positions_refs"][-2:]],
                       "replay_available": [line(i) for i in s["replay_refs"]],
                       "standing": [line(i) for i in s["standing"]],
                       "tables_recent": s["tables"][-3:],
                       "hidden_facts_recent": [line(i) for i in s["hidden_facts"][-6:]]}
    b["self_check"] = {st: sorted(k for k, v in b["fields"].items() if v["status"] == st)
                       for st in sorted({v["status"] for v in b["fields"].values()})}
    return b


def compact(bundle):
    """Bound retrieval previews, retaining exact ledger references for omitted history."""
    out = copy.deepcopy(bundle)
    omitted = {}
    for entity, rows in out["entity_history"].items():
        if len(rows) > 8:
            omitted["entity." + entity] = [row[0] for row in rows[:-8]]
            out["entity_history"][entity] = rows[-8:]
    if "hidden" in out:
        for key in ("replay_available", "standing"):
            rows = out["hidden"][key]
            if len(rows) > 8:
                omitted["hidden." + key] = [row[0] for row in rows[:-8]]
                out["hidden"][key] = rows[-8:]
    out["retrieval_omitted"] = omitted
    out["meta"]["format"] = "compact/1"
    return out


def load_sheet():
    import yaml
    return yaml.safe_load(SHEET.read_text(encoding="utf-8"))["character_runtime"]


def build(entry, head=None, audience="gm", checkpoint=None, action=None):
    t0 = time.perf_counter()
    led = ledger_mod()
    _, problems = led.validate_all(Path(entry["path"]))
    if problems:
        raise Rejected("ledger validation failed")
    ev = load_events(entry["path"])
    if not ev:
        raise Rejected("empty ledger")
    if head:
        ev = [e for e in ev if seq(e["event_id"]) <= seq(head)]
        if not ev or ev[-1]["event_id"] != head:
            raise Rejected(f"head {head} not in the ledger")
    mode = "full_replay"
    if checkpoint:
        cp = json.loads(Path(checkpoint).read_text(encoding="utf-8"))
        if cp.get("schema") != SCHEMA or cp.get("reducer") != REDUCER:
            mode = "full_replay (checkpoint version mismatch)"
        elif cp["head"] is None or seq(cp["head"]) > seq(ev[-1]["event_id"]):
            raise Rejected(f"checkpoint head {cp['head']} is ahead of the ledger head {ev[-1]['event_id']}")
        elif cp.get("campaign") != entry["id"]:
            mode = "full_replay (checkpoint campaign mismatch)"
        elif cp != fold(empty(entry["id"]), [e for e in ev if seq(e["event_id"]) <= seq(cp["head"])]):
            mode = "full_replay (checkpoint state does not match replay)"
        elif chain_upto(ev, cp["head"]) != cp["chain"]:
            mode = "full_replay (checkpoint chain does not match the ledger: history differs)"
        elif any(e["kind"] == "ruling_void" for e in ev if seq(e["event_id"]) > seq(cp["head"])):
            mode = "full_replay (a ruling_void follows the checkpoint)"
        else:
            mode = f"incremental from {cp['head']}"
            s = fold(cp, [e for e in ev if seq(e["event_id"]) > seq(cp["head"])])
    if mode.startswith("full_replay"):
        s = fold(empty(entry["id"]), ev)
    sheet = load_sheet()
    b = bundle(s, entry, audience, sheet, {"valid": not problems, "problems": len(problems)})
    if action is not None:
        public = s.get("_player", empty(entry["id"]))
        if (action.get("campaign_id") != entry["id"] or action.get("based_on_revision") != public["public"] or
            action.get("ledger_head") != public["public_head"]):
            raise Rejected("submitted action does not match the authoritative public revision")
        b["submitted_resolution_settings"] = resolution_policy.settings(action)
    b["meta"]["build"] = {"mode": mode, "ms": round((time.perf_counter() - t0) * 1000, 1)}
    return s, b


# ------------------------------------------------------------------ commands
def cmd_brief(a):
    entry = run_entry(a.campaign)
    action = json.loads(Path(a.action).read_text()) if getattr(a, "action", None) else None
    s, b = build(entry, a.head, a.audience, a.checkpoint, action=action)
    if a.expect_head and a.expect_head != s["head"]:
        print(json.dumps({"verdict": "stale", "expected_head": a.expect_head, "ledger_head": s["head"]})); return 3
    if a.save_checkpoint:
        Path(a.save_checkpoint).write_text(json.dumps(s, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    if getattr(a, "compact", False):
        b = compact(b)
    out = json.dumps(b, ensure_ascii=False, sort_keys=True, indent=0)
    if a.out:
        Path(a.out).write_text(out, encoding="utf-8")
        print(json.dumps({"out": a.out, "head": s["head"], "audience": a.audience, "chars": len(out), "build": b["meta"]["build"], "self_check": b["self_check"]}))
    else:
        print(out)
    return 0


def cmd_history(a):
    entry = run_entry(a.campaign)
    by = {e["event_id"]: e for e in load_events(entry["path"])}
    out = []
    for i in a.ids:
        e = by.get(i)
        if not e:
            out.append({"id": i, "error": "not found"})
        elif a.audience == "player" and e["visibility"] == "gm_only":
            out.append({"id": i, "error": "not available to the player audience"})
        else:
            out.append(e)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def player_leaks(bundle_text, hidden_events):
    leaks = []
    for e in hidden_events:
        if re.search(r"\b" + re.escape(e["event_id"]) + r"\b", bundle_text):
            leaks.append(("id", e["event_id"]))
        frag = e["summary"].strip()[:48]
        if len(frag) >= 24 and frag in bundle_text:
            leaks.append(("text", e["event_id"]))
    return leaks


def cmd_verify(a):
    entry = run_entry(a.campaign)
    ev = load_events(entry["path"])
    sheet = load_sheet()
    report = {"campaign_id": entry["id"], "events": len(ev), "checks": {}}
    t0 = time.perf_counter()
    # 1. incremental (via a JSON-serialised checkpoint) == full replay at every head
    mism, s_inc = [], empty(entry["id"])
    for i, e in enumerate(ev):
        s_inc = reduce(json.loads(json.dumps(s_inc)), e)
        s_full = fold(empty(entry["id"]), ev[: i + 1])
        if json.dumps(s_inc, sort_keys=True) != json.dumps(s_full, sort_keys=True):
            mism.append(e["event_id"])
    report["checks"]["incremental_equals_full_replay"] = {"heads_checked": len(ev), "mismatches": mism, "ms": round((time.perf_counter() - t0) * 1000)}
    # 2. rejections
    s = fold(empty(entry["id"]), ev[:-3])
    rej = {}
    for name, evt in (("duplicate", ev[-4]), ("out_of_order", ev[-1]), ("bad_start", None)):
        try:
            if evt is None:
                reduce(empty(entry["id"]), ev[5])
            else:
                reduce(copy.deepcopy(s), evt)
            rej[name] = "NOT REJECTED"
        except Rejected as x:
            rej[name] = "rejected: " + str(x)
    temporary = tempfile.TemporaryDirectory(prefix="genesis-brief-")
    tmp = Path(temporary.name) / "checkpoint.json"
    tampered = copy.deepcopy(s); tampered["chain"] = "f" * 64
    tmp.write_text(json.dumps(tampered))
    _, b = build(entry, None, "gm", str(tmp))
    rej["tampered_checkpoint"] = b["meta"]["build"]["mode"]
    tmp.write_text(json.dumps(fold(empty(entry["id"]), ev)))
    try:
        build(entry, ev[-2]["event_id"], "gm", str(tmp)); rej["checkpoint_ahead_of_ledger"] = "NOT REJECTED"
    except Rejected as x:
        rej["checkpoint_ahead_of_ledger"] = "rejected: " + str(x)
    tmp.write_text(json.dumps(fold(empty(entry["id"]), ev[:-3])))
    _, b = build(entry, None, "gm", str(tmp))
    rej["valid_checkpoint"] = b["meta"]["build"]["mode"]
    report["checks"]["rejections"] = rej
    # 3. leak tests: every head, player bundle carries no hidden id or hidden text; plus a canary
    hidden = [e for e in ev if e["visibility"] == "gm_only"]
    leaks, s = [], empty(entry["id"])
    for e in ev:
        s = reduce(s, e)
        txt = json.dumps(bundle(s, entry, "player", sheet, {"valid": True, "problems": 0}), ensure_ascii=False)
        hid_sofar = [h for h in hidden if seq(h["event_id"]) <= seq(e["event_id"])]
        leaks += [(e["event_id"],) + l for l in player_leaks(txt, hid_sofar)]
    canary = {"event_id": f"evt_{len(ev) + 1:04d}", "session": 1, "turn_no": ev[-1]["turn_no"], "world_time": ev[-1]["world_time"],
              "actor": "drover_pack", "kind": "npc_plan", "summary": "CANARY-7f3a the pack means to circle Wick at the ditch",
              "visibility": "gm_only", "knowledge_type": "fact", "known_to": [], "caused_by": [], "roll_ids": [], "details": {"note": "CANARY-7f3a"}}
    s2 = reduce(copy.deepcopy(s), canary)
    p_txt = json.dumps(bundle(s2, entry, "player", sheet, {"valid": True, "problems": 0}))
    g_txt = json.dumps(bundle(s2, entry, "gm", sheet, {"valid": True, "problems": 0}))
    report["checks"]["leaks"] = {"heads_checked": len(ev), "player_leaks": leaks[:10], "leak_count": len(leaks),
                                 "canary_in_player": "CANARY-7f3a" in p_txt, "canary_in_gm": "CANARY-7f3a" in g_txt}
    hist_block = []
    for i in [h["event_id"] for h in hidden[:3]]:
        ns = argparse.Namespace(campaign=entry["id"], ids=[i], audience="player")
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_history(ns)
        hist_block.append("not available" in buf.getvalue())
    report["checks"]["history_refuses_hidden_to_player"] = all(hist_block)
    ok = (not mism and not leaks and not report["checks"]["leaks"]["canary_in_player"] and report["checks"]["leaks"]["canary_in_gm"]
          and all(v.startswith(("rejected", "full_replay (checkpoint chain", "full_replay (checkpoint state", "incremental")) for v in rej.values()) and all(hist_block))
    report["ok"] = ok
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0 if ok else 3


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("brief"); b.add_argument("campaign"); b.add_argument("--head"); b.add_argument("--audience", choices=["gm", "player"], default="gm")
    b.add_argument("--compact", action="store_true"); b.add_argument("--expect-head"); b.add_argument("--checkpoint"); b.add_argument("--save-checkpoint"); b.add_argument("--out")
    b.add_argument("--action", help="optional submitted action; binds per-turn resolution settings to its public revision")
    h = sp.add_parser("history"); h.add_argument("campaign"); h.add_argument("ids", nargs="+"); h.add_argument("--audience", choices=["gm", "player"], default="gm")
    v = sp.add_parser("verify"); v.add_argument("campaign")
    a = ap.parse_args()
    try:
        return {"brief": cmd_brief, "history": cmd_history, "verify": cmd_verify}[a.cmd](a)
    except Rejected as x:
        print(json.dumps({"verdict": "rejected", "reason": str(x)})); return 3


if __name__ == "__main__":
    sys.exit(main())
