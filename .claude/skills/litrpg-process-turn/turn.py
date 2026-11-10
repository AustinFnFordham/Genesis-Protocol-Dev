#!/usr/bin/env python3
"""Deterministic helpers for the Datapad turn processor (see SKILL.md in this folder).

  turn.py info     <campaign_id>                       registry entry + current revision + turn context
  turn.py check    <campaign_id> <action.json>         stale check + contract validation (no dice)
  turn.py recover  <campaign_id> <action_id>           ledger state for an action: none | partial | complete
  turn.py lint     <campaign_id> <narration.txt> [--target aero]   horror-narration integrity (Test F)
  turn.py export   <campaign_id> --out FILE [--budget N]   the view/state snapshot alone, under its byte budget (exit 5, nothing written, if it cannot fit)
  turn.py publish  <campaign_id> --current <view_state.json|none> --outdir DIR
                                                       plan the Datapad publication of the committed revision: history pages
                                                       (view/feed-NNNN, view/journal-NNNN) then the view/state snapshot, every
                                                       document under a byte budget; repeatable; exit 6 = stale or not pushed
  turn.py progress <campaign_id> <action.json> <outcome.json>   contract-3 plan progress against the published context
  turn.py lintctx  <campaign_id> <ctx.json>            context lint before publishing a turn_context (warn / defer, never guess)
  turn.py run new  <campaign_id>                       new run identity in /tmp/turn_run.env (START, RUN, LEASE_MS); prints it
  turn.py doc <kind> --out FILE [...]                  write an ArtifactData document from the run identity and the clock:
                                                       lock | renew | release | claim | heartbeat | resolved | pubfail | committed | failed
  turn.py lockcheck <lock.json|none>                   free | mine | busy | expired (exit 3 only when busy)
  turn.py stale    <action_row.json>                   is a processing row's worker gone? (lease, not a fixed 20 minutes)
  turn.py push     <campaign_id> <lock.json>           fenced git push: only while this run holds the lease; never rebases over
                                                       another worker's commit for the same run (exit 4: stand down)
Identity, timestamps and lock holders are always generated here, never typed by hand.

Exit codes: 0 ok, 3 needs revision / lint failure, 2 usage or registry error, 5 a document over its byte budget,
6 publish refused (stale, or not committed and pushed).
Nothing here rolls dice, writes the ledger, or touches the Artifact database; those stay with the
dice skill, the ledger skill and the ArtifactData tool, in the order the runbook gives.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
REGISTRY = REPO / "campaigns" / "starwars_litrpg" / "runs" / "registry.json"
UI = REPO / "campaigns" / "starwars_litrpg" / "ui"
sys.path.insert(0, str(UI))
import export_state  # noqa: E402

# Words that describe lasting damage. Narration may use them only when a committed public
# `lasting_injury` event exists for the target (NARRATIVE_SPEC §B, Test F).
LASTING = re.compile(r"\b(sever(?:ed|s)?|amputat\w*|shatter(?:ed|s)?\s+(?:bone|femur|knee|leg|arm|skull|spine)|"
                     r"(?:broken|snapped|splintered)\s+(?:bone|femur|tibia|knee|leg|arm|spine|ribs?)|"
                     r"bit(?:ten)?\s+(?:clean\s+)?off|torn\s+off|crippled|paralys\w+|blinded|lost\s+(?:his|her|their)\s+(?:leg|arm|hand|eye))\b", re.I)
DEATH = re.compile(r"\b(is dead|dies\b|died\b|killed\b|his death)\b", re.I)


def run_entry(cid):
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))["runs"]
    if cid not in reg:
        sys.exit(f"unknown campaign id {cid!r}; registry has {sorted(reg)}")
    e = dict(reg[cid]); e["id"] = cid; e["path"] = REPO / e["dir"]
    return e


def events(entry):
    return export_state.public_events(entry["path"])


def state(entry):
    return export_state.build(campaign_dir=entry["path"], campaign_id=entry["id"])


def node_validate(decl, ctx):
    tmp = Path("/tmp") / f"ctx_{abs(hash(json.dumps(ctx, sort_keys=True)))}.json"
    tmp.write_text(json.dumps(ctx), encoding="utf-8")
    p = subprocess.run(["node", str(UI / "turn_contract.js"), "validate", "-", str(tmp)], input=json.dumps(decl), capture_output=True, text=True)
    if p.returncode not in (0, 3):
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


def node_parse(text, ctx):
    tmp = Path("/tmp") / f"ctx_{abs(hash(json.dumps(ctx, sort_keys=True)))}.json"
    tmp.write_text(json.dumps(ctx), encoding="utf-8")
    p = subprocess.run(["node", str(UI / "turn_contract.js"), "parse", text, str(tmp)], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


def cmd_info(a):
    e = run_entry(a.campaign); st = state(e)
    print(json.dumps({"campaign_id": e["id"], "dir": e["dir"], "artifact_url": e["artifact_url"], "status": e["status"], "canon": e["canon"],
                      "revision": st["revision"], "ledger_head": st["ledger_head"], "turn_context": st["turn_context"]}, indent=1))


def cmd_check(a):
    e = run_entry(a.campaign)
    if e["status"] != "active":
        print(json.dumps({"verdict": "failed", "reason": f"campaign {e['id']} is {e['status']}; it is not processed"})); return 3
    act = json.loads(Path(a.action).read_text(encoding="utf-8"))
    act = act.get("data", act)  # accept a raw ArtifactData document or its data
    st = state(e)
    out = {"campaign_id": e["id"], "current_revision": st["revision"], "based_on_revision": act.get("based_on_revision")}
    if act.get("campaign_id") not in (None, e["id"]):
        out.update(verdict="needs_revision", reason=f"action belongs to campaign {act.get('campaign_id')}")
    elif act.get("based_on_revision") != st["revision"]:
        out.update(verdict="needs_revision", reason="The story moved on after this action was written (revision "
                   f"{act.get('based_on_revision')} vs {st['revision']}). Review the latest scene and resubmit.")
    elif not st["turn_context"]:
        out.update(verdict="gm_judgment", reason="No turn context is published; the GM interprets the text freely under the charter.")
    else:
        ctx = st["turn_context"]
        decl = act.get("declaration")
        if decl:
            r = node_validate(decl, ctx); out.update(declaration=decl, validation=r["validation"], summary=r["summary"])
        else:
            r = node_parse(act.get("text", ""), ctx); out.update(declaration=r["declaration"], validation=r["validation"], summary=r["summary"],
                                                               note="Parsed from free text; the GM may correct the reading but must re-validate it.")
        v = out["validation"]
        if not v["legal"]:
            out["verdict"] = "needs_revision"
        elif v.get("needs_confirmation", bool(v["warnings"])) and not act.get("confirmed_warnings"):  # contract 3: advisory scene risks need no tick
            out.update(verdict="needs_revision", reason="Known risks were not confirmed by the player.")
        else:
            out["verdict"] = "legal"
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0 if out["verdict"] in ("legal", "gm_judgment") else 3


def cmd_recover(a):
    e = run_entry(a.campaign)
    led = export_state.la._ledger()
    allev = led.load_all(e["path"])
    mine = [x for x in allev if str(x.get("idempotency_key") or "").startswith(a.action_id + ":")]
    rolls = [r["roll_id"] for r in led.read_jsonl(e["path"] / "records" / "roll_log.jsonl") if str(r.get("purpose", "")).startswith("[" + a.action_id + "]")]
    kinds = [x["kind"] for x in mine]
    status = "complete" if "gm_narration" in kinds and "turn_context" in kinds else ("none" if not mine and not rolls else "partial")
    print(json.dumps({"action_id": a.action_id, "status": status, "events": [x["event_id"] + ":" + x["kind"] for x in mine], "rolls": rolls}, indent=1))


def cmd_lint(a):
    e = run_entry(a.campaign)
    text = Path(a.narration).read_text(encoding="utf-8")
    ev = events(e)
    problems = []
    lasting = [x for x in ev if x["kind"] == "lasting_injury" and x["details"].get("target") == a.target]
    for m in LASTING.finditer(text):
        if not lasting:
            problems.append(f"'{m.group(0)}' describes lasting damage but no committed lasting_injury event exists for {a.target}")
    st = export_state.build(ev, campaign_id=e["id"]) if ev else None
    dead = st and "dead" in [c.lower() for c in st["character"]["conditions"]]
    for m in DEATH.finditer(text):
        if not dead:
            problems.append(f"'{m.group(0)}' narrates death but {a.target} is not dead in the ledger")
    print(json.dumps({"ok": not problems, "problems": problems}, indent=1))
    return 0 if not problems else 3


def _git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO)


def _publish_state(e):
    st = state(e)
    st["artifact_url"] = e["artifact_url"]
    proc = json.loads(REGISTRY.read_text(encoding="utf-8")).get("processor")
    # a run marked "no_processor" (sandbox previews) never gets a GM-start link, whatever the registry's processor is
    st["processor"] = {"server": proc["server"], "trigger_id": proc["trigger_id"]} if proc and e["status"] == "active" and not e.get("no_processor") else None
    return st


def cmd_export(a):
    """The view/state snapshot alone (preview, tests). The processor publishes with `turn.py publish`."""
    e = run_entry(a.campaign)
    try:  # byte budget checked before anything is written: the database refuses documents over 262,144 bytes
        st = export_state.publish_set(_publish_state(e), state_budget=a.budget or export_state.STATE_BUDGET)["state"]
    except ValueError as err:
        print(json.dumps({"out": None, "error": str(err)})); return 5
    Path(a.out).write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    h = st["history"]
    print(json.dumps({"out": a.out, "revision": st["revision"], "ledger_head": st["ledger_head"], "has_turn_context": bool(st["turn_context"]),
                      "bytes": h["bytes"], "budget": h["budget_bytes"], "feed_omitted": h["feed"]["omitted"], "journal_omitted": h["journal"]["omitted"]}))


def cmd_publish(a):
    """Plan the Datapad publication of the committed revision. Independent of resolution and safe to repeat:
    it reads only what git holds, writes files only, and names the ArtifactData writes in order
    (history pages first, view/state last, so the player keeps the previous complete revision until the end).
    Exit 5: a document cannot meet its byte budget. Exit 6: not a committed, pushed revision, or the Datapad
    already shows a newer one (an old retry must never overwrite it)."""
    e = run_entry(a.campaign); rel = str(e["path"].relative_to(REPO))
    if _git("status", "--porcelain", "--", rel).stdout.strip():
        print(json.dumps({"ok": False, "reason": "the run directory has uncommitted changes; publish only what git holds"})); return 6
    branch = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if not a.allow_unpushed and _git("merge-base", "--is-ancestor", "HEAD", "origin/" + branch).returncode != 0:
        print(json.dumps({"ok": False, "reason": "HEAD is not on origin/" + branch + "; push first (git before Datapad)"})); return 6
    commit = _git("log", "-1", "--format=%h", "--", rel).stdout.strip()
    st = _publish_state(e)
    try:
        ps = export_state.publish_set(st, published={"revision": st["revision"], "ledger_head": st["ledger_head"], "commit": commit})
    except ValueError as err:
        print(json.dumps({"ok": False, "reason": str(err)})); return 5
    cur = load_doc(a.current) or {}
    if cur.get("campaign_id") in (None, e["id"]) and (cur.get("revision") or 0) > st["revision"]:
        print(json.dumps({"ok": False, "reason": "the Datapad already shows a newer revision; this publish is stale", "published_revision": cur.get("revision"), "revision": st["revision"]})); return 6
    have = {}
    if cur.get("campaign_id") == e["id"]:
        for kind in ("feed", "journal"):
            for pg in ((cur.get("history") or {}).get(kind) or {}).get("pages") or []:
                have[pg["id"]] = pg["hash"]
    out = Path(a.outdir) / "view"; out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.json"):
        old.unlink()
    writes = []
    for pid, doc in ps["pages"].items():
        if have.get(pid) == doc["hash"]:
            continue  # already published with exactly this content under the current manifest
        f = out / (pid + ".json"); f.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        writes.append({"collection": "view", "doc_id": pid, "file": str(f), "bytes": export_state.doc_bytes(doc)})
    snap = ps["state"]; same = cur.get("campaign_id") == e["id"] and cur.get("revision") == snap["revision"] and (cur.get("history") or {}) == snap["history"] and not writes
    f = out / "state.json"; f.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    h = snap["history"]
    print(json.dumps({"ok": True, "revision": snap["revision"], "ledger_head": snap["ledger_head"], "commit": commit, "already_published": same,
                      "pages": writes, "state": {"collection": "view", "doc_id": "state", "file": str(f), "bytes": h["bytes"], "budget": h["budget_bytes"]},
                      "preview": {"feed": h["feed"]["shown"], "journal": h["journal"]["shown"]},
                      "order": "write every page (if_version when it exists), then view/state with the if_version you read"}, indent=1))


def cmd_progress(a):
    e = run_entry(a.campaign); st = state(e)
    act = json.loads(Path(a.action).read_text(encoding="utf-8")); act = act.get("data", act)
    tmp = Path("/tmp") / f"ctx_progress_{e['id']}.json"; tmp.write_text(json.dumps(st["turn_context"] or {}), encoding="utf-8")
    p = subprocess.run(["node", str(UI / "turn_contract.js"), "progress", "-", str(tmp), a.outcome], input=json.dumps(act["declaration"]), capture_output=True, text=True)
    print(p.stdout.strip() or p.stderr.strip())
    return 0 if p.returncode == 0 else 3


def cmd_lintctx(a):
    p = subprocess.run(["node", str(UI / "turn_contract.js"), "lintctx", "-", a.ctx], capture_output=True, text=True)
    print(p.stdout.strip() or p.stderr.strip())
    return 0 if p.returncode == 0 else 3


# ---------- run identity, lease and fenced writes (branch litrpg/turn-builder) ----------
import os, secrets, time
RUN_ENV = Path(os.environ.get("TURN_RUN_ENV", "/tmp/turn_run.env"))
DEFAULT_LEASE_MS = 180000  # 3 min, renewed at every phase; recovery waits for the lease, not a fixed 20 minutes


def now_ms():
    return time.time_ns() // 1_000_000


def run_env():
    if not RUN_ENV.exists():
        sys.exit("no run identity: run `turn.py run new <campaign_id>` first")
    env = dict(kv.split("=", 1) for kv in RUN_ENV.read_text().split())
    env["START"] = int(env["START"]); env["LEASE_MS"] = int(env.get("LEASE_MS", DEFAULT_LEASE_MS))
    if "CLAIM_MS" in env: env["CLAIM_MS"] = int(env["CLAIM_MS"])
    return env


def save_env(env):
    RUN_ENV.write_text(" ".join(f"{k}={v}" for k, v in env.items()) + "\n")


def cmd_run(a):
    e = run_entry(a.campaign)
    start = now_ms()
    env = {"START": start, "RUN": f"run-{start}-{secrets.token_hex(3)}", "CAMPAIGN": e["id"], "LEASE_MS": int(e.get("lease_ms", DEFAULT_LEASE_MS))}
    save_env(env); print(json.dumps(env))


def load_doc(path):
    if path in (None, "none", "-") or not Path(path).exists():
        return None
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return d.get("data", d)


def cmd_doc(a):
    env = run_env(); t = now_ms(); k = a.kind
    if k == "lock":
        doc = {"holder": env["RUN"], "expires_ms": t + env["LEASE_MS"], "acquired_ms": t}
    elif k == "renew":
        doc = {"holder": env["RUN"], "expires_ms": t + env["LEASE_MS"]}
    elif k == "release":
        doc = {"holder": env["RUN"], "expires_ms": 0, "released_ms": t}
    elif k == "claim":
        env["CLAIM_MS"] = t; save_env(env)
        doc = {"status": "processing", "processing": {"started_ms": t, "heartbeat_ms": t, "run": env["RUN"]}}
    elif k == "heartbeat":
        doc = {"processing": {"started_ms": env.get("CLAIM_MS", t), "heartbeat_ms": t, "run": env["RUN"]}}
    elif k in ("committed", "resolved"):
        if not a.event and a.action:  # the declaration event id comes from the ledger, never typed
            e = run_entry(env["CAMPAIGN"]); led = export_state.la._ledger()
            mine = [x for x in led.load_all(e["path"]) if x.get("idempotency_key") == a.action + ":1" and x["kind"] == "player_declaration"]
            if not mine:
                sys.exit("no committed player_declaration for " + a.action)
            a.event = mine[0]["event_id"]
        commit = a.commit or subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO).stdout.strip()
        if k == "resolved":  # resolution is durable in git; the Datapad has not been advanced yet
            doc = {"status": "resolved", "event_id": a.event, "commit": commit, "resolved_ms": t,
                   "publication": {"status": "pending", "last_error": None}}
        else:
            doc = {"status": "committed", "event_id": a.event, "commit": commit, "committed_ms": t,
                   "publication": {"status": "published", "revision": a.revision, "published_ms": t, "last_error": None}}
            if a.recovered: doc["recovered"] = True
    elif k == "pubfail":  # the turn stays resolved; only the publication is pending
        doc = {"status": "resolved", "publication": {"status": "pending", "last_error": a.error or "publication failed", "failed_ms": t}}
    elif k == "failed":
        doc = {"status": "failed", "error": a.error or "processing failed", "ledger_events": a.events or [], "rolls": a.rolls or [], "failed_ms": t}
    else:
        sys.exit(f"unknown doc kind {k}")
    Path(a.out).write_text(json.dumps(doc), encoding="utf-8")
    print(json.dumps({"out": a.out, "doc": doc}))


def cmd_lockcheck(a):
    env = run_env(); lock = load_doc(a.lock); t = now_ms()
    if not lock or not lock.get("holder"):
        v = "free"
    elif lock.get("holder") == env["RUN"]:
        v = "mine" if lock.get("expires_ms", 0) > t else "expired"
    else:
        v = "busy" if lock.get("expires_ms", 0) > t else "expired"
    out = {"verdict": v, "holder": (lock or {}).get("holder"), "expires_in_ms": (lock or {}).get("expires_ms", 0) - t, "now_ms": t}
    print(json.dumps(out)); return 3 if v == "busy" else 0


def cmd_stale(a):
    env = run_env(); row = load_doc(a.row) or {}; t = now_ms()
    p = row.get("processing") or {}
    last = max(p.get("heartbeat_ms") or 0, p.get("started_ms") or 0)
    stale = row.get("status") == "processing" and t - last > env["LEASE_MS"]
    print(json.dumps({"stale": stale, "status": row.get("status"), "idle_ms": t - last if last else None, "lease_ms": env["LEASE_MS"], "worker": p.get("run")}))
    return 0 if stale else 3


def cmd_push(a):
    """Fenced push. The caller has just re-read the lock (ArtifactData get) into <lock.json>."""
    env = run_env(); e = run_entry(a.campaign); lock = load_doc(a.lock); t = now_ms()
    if not lock or lock.get("holder") != env["RUN"] or lock.get("expires_ms", 0) <= t:
        print(json.dumps({"pushed": False, "reason": "this run no longer holds the lease; stand down without pushing", "holder": (lock or {}).get("holder")})); return 4
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, cwd=REPO).stdout.strip()
    p = subprocess.run(["git", "push", "origin", branch], capture_output=True, text=True, cwd=REPO)
    if p.returncode == 0:
        print(json.dumps({"pushed": True, "branch": branch})); return 0
    subprocess.run(["git", "fetch", "origin", branch], capture_output=True, cwd=REPO)
    theirs = subprocess.run(["git", "log", "--format=%H %s", f"HEAD..origin/{branch}", "--", e["dir"]], capture_output=True, text=True, cwd=REPO).stdout.strip()
    if theirs:
        print(json.dumps({"pushed": False, "reason": "another worker already wrote this run; stand down (do not rebase over it)", "their_commits": theirs.splitlines()})); return 4
    r = subprocess.run(["git", "pull", "--rebase", "origin", branch], capture_output=True, text=True, cwd=REPO)
    p = subprocess.run(["git", "push", "origin", branch], capture_output=True, text=True, cwd=REPO)
    print(json.dumps({"pushed": p.returncode == 0, "rebased_over_other_runs": True, "stderr": p.stderr[-300:] if p.returncode else ""})); return 0 if p.returncode == 0 else 4


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("info"); s.add_argument("campaign")
    s = sub.add_parser("check"); s.add_argument("campaign"); s.add_argument("action")
    s = sub.add_parser("recover"); s.add_argument("campaign"); s.add_argument("action_id")
    s = sub.add_parser("lint"); s.add_argument("campaign"); s.add_argument("narration"); s.add_argument("--target", default="aero")
    s = sub.add_parser("export"); s.add_argument("campaign"); s.add_argument("--out", required=True); s.add_argument("--budget", type=int)
    s = sub.add_parser("publish"); s.add_argument("campaign"); s.add_argument("--current", default="none"); s.add_argument("--outdir", required=True); s.add_argument("--allow-unpushed", action="store_true")
    s = sub.add_parser("progress"); s.add_argument("campaign"); s.add_argument("action"); s.add_argument("outcome")
    s = sub.add_parser("lintctx"); s.add_argument("campaign"); s.add_argument("ctx")
    s = sub.add_parser("run"); s.add_argument("what", choices=["new"]); s.add_argument("campaign")
    s = sub.add_parser("doc"); s.add_argument("kind"); s.add_argument("--out", required=True); s.add_argument("--event"); s.add_argument("--commit")
    s.add_argument("--error"); s.add_argument("--events", nargs="*"); s.add_argument("--rolls", nargs="*"); s.add_argument("--recovered", action="store_true"); s.add_argument("--action"); s.add_argument("--revision", type=int)
    s = sub.add_parser("lockcheck"); s.add_argument("lock")
    s = sub.add_parser("stale"); s.add_argument("row")
    s = sub.add_parser("push"); s.add_argument("campaign"); s.add_argument("lock")
    a = ap.parse_args()
    return {"info": cmd_info, "check": cmd_check, "recover": cmd_recover, "lint": cmd_lint, "export": cmd_export,
            "publish": cmd_publish, "progress": cmd_progress, "lintctx": cmd_lintctx, "run": cmd_run, "doc": cmd_doc, "lockcheck": cmd_lockcheck, "stale": cmd_stale,
            "push": cmd_push}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
