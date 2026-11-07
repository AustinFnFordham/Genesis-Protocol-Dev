#!/usr/bin/env python3
"""Phase timing for the Datapad turn processor (instrumentation only).

Never changes adjudication, dice, ledger or publishing. Every command exits 0 and
prints a short line even when something is missing, so a timing failure can never
fail a turn. Marks are appended to an EXISTING shell call (no extra tool round trip).

  timing.py mark <phase>            record now for <phase> (run id from /tmp/turn_run.env)
  timing.py usage --campaign C --outcome O [--action A] [--submit-ms N]
                  [--rolls N] [--events N] [--out /tmp/usage.json]
                                    build the usage record (with timings) for ArtifactData set

Phases, in runbook order (mark each at the start of the next shell call after it happens):
  run_start      §0.4, run identity created
  claimed        §1.4 claim write returned
  preflight_done §2 check verdict known
  context_loaded §3 reading done, before reasoning about the turn
  rules_done     tables/interpretation committed, before the first roll
  dice_done      after the last roll
  ledger_done    after the last consequence event, before writing narration
  narration_done narration, scene_state and turn_context committed, validate passed
  git_done       push succeeded
  projected      view/state written
Durations are reported for the nine owner-requested categories. Session-level numbers
(delivery time, model vs tool time, passes in this session) come from this session's
own transcript, read for timestamps only.
"""
import glob, json, os, sys, time

MARKS = "/tmp/turn_timing.jsonl"
ENV = "/tmp/turn_run.env"


def now_ms():
    return int(time.time() * 1000)


def run_id():
    try:
        for tok in open(ENV).read().split():
            if tok.startswith("RUN="):
                return tok[4:]
    except OSError:
        pass
    return None


def marks(run):
    out = {}
    try:
        for line in open(MARKS):
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if m.get("run") != run:
                continue
            if m.get("phase") == "run_start":
                out = {}  # a reused run id starts a fresh pass
            out.setdefault(m.get("phase"), m.get("t_ms"))
    except OSError:
        pass
    return out


def passes_in_session():
    runs = []
    try:
        for line in open(MARKS):
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if m.get("phase") == "run_start" and m.get("run") not in runs:
                runs.append(m.get("run"))
    except OSError:
        pass
    return runs


def iso_ms(s):
    from datetime import datetime
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)


def transcript_stats(since_ms):
    """Delivery time of this session's first message, and model vs tool time since `since_ms`."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sid:
        return {}
    paths = glob.glob(os.path.expanduser("~/.claude/projects/*/%s.jsonl" % sid))
    if not paths:
        return {"session": sid}
    first = None
    pending, tool_ms, calls, last = {}, 0, 0, None
    for line in open(paths[0]):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        ts = e.get("timestamp")
        if not ts or e.get("type") not in ("user", "assistant"):
            continue
        t = iso_ms(ts)
        if first is None and e.get("type") == "user":
            first = t
        if since_ms and t < since_ms:
            continue
        last = t
        content = (e.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for x in content:
            if x.get("type") == "tool_use":
                pending[x.get("id")] = t
                calls += 1
            elif x.get("type") == "tool_result" and x.get("tool_use_id") in pending:
                tool_ms += t - pending.pop(x.get("tool_use_id"))
    out = {"session": sid, "session_first_message_ms": first}
    if since_ms and last:
        out.update({"tool_calls": calls, "tool_ms": tool_ms, "model_ms": max(0, last - since_ms - tool_ms)})
    return out


def span(m, a, b):
    if a in m and b in m and m[b] >= m[a]:
        return m[b] - m[a]
    return None


def add(*xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) if xs else None


def timings(run, submit_ms):
    m = marks(run)
    start = m.get("run_start")
    ts = transcript_stats(start)
    first = ts.get("session_first_message_ms")
    runs = passes_in_session()
    t = {
        # None when this session predates the submission (e.g. a reused session)
        "1_submit_to_worker_start_ms": (first - submit_ms) if (first and submit_ms and first >= submit_ms) else None,
        "2_session_init_ms": (start - first) if (first and start and (not submit_ms or first >= submit_ms)) else None,
        "3_context_loading_ms": span(m, "preflight_done", "context_loaded"),
        "4_preflight_and_rules_ms": add(span(m, "run_start", "claimed"), span(m, "claimed", "preflight_done"),
                                        span(m, "context_loaded", "rules_done")),
        "4a_lock_and_claim_ms": span(m, "run_start", "claimed"),
        "5_dice_ms": span(m, "rules_done", "dice_done"),
        "6_ledger_ms": span(m, "dice_done", "ledger_done"),
        "7_narration_ms": span(m, "ledger_done", "narration_done"),
        "8_projection_ms": span(m, "git_done", "projected"),
        "9_git_sync_ms": span(m, "narration_done", "git_done"),
        "submit_to_visible_ms": (m["projected"] - submit_ms) if ("projected" in m and submit_ms) else None,
        "pass_in_session": (runs.index(run) + 1) if run in runs else None,
        "earlier_passes_in_session": [r for r in runs if r != run][:5],
        "marks": m,
    }
    for k in ("tool_calls", "tool_ms", "model_ms"):
        if k in ts:
            t[k] = ts[k]
    return t, ts.get("session")


def main(argv):
    if len(argv) >= 2 and argv[0] == "mark":
        run = run_id()
        try:
            with open(MARKS, "a") as f:
                f.write(json.dumps({"run": run, "phase": argv[1], "t_ms": now_ms()}) + "\n")
            print("timing:", argv[1])
        except OSError as e:
            print("timing: mark skipped (%s)" % e)
        return 0
    if argv and argv[0] == "usage":
        import argparse
        p = argparse.ArgumentParser(prog="timing.py usage")
        p.add_argument("--campaign", required=True)
        p.add_argument("--outcome", required=True)
        p.add_argument("--action")
        p.add_argument("--submit-ms", type=int)
        p.add_argument("--rolls", type=int, default=0)
        p.add_argument("--events", type=int, default=0)
        p.add_argument("--out", default="/tmp/usage.json")
        a = p.parse_args(argv[1:])
        run = run_id()
        start = None
        try:
            for tok in open(ENV).read().split():
                if tok.startswith("START="):
                    start = int(tok[6:])
        except (OSError, ValueError):
            pass
        try:
            t, session = timings(run, a.submit_ms)
        except Exception as e:  # instrumentation must never fail a turn
            t, session = {"error": str(e)[:200]}, os.environ.get("CLAUDE_CODE_SESSION_ID")
        doc = {"campaign_id": a.campaign, "action_id": a.action, "outcome": a.outcome,
               "started_ms": start, "finished_ms": now_ms(), "rolls": a.rolls, "events": a.events,
               "session": session, "submit_ms": a.submit_ms, "timings": t}
        with open(a.out, "w") as f:
            json.dump(doc, f)
        print(json.dumps({"run": run, "out": a.out, "submit_to_visible_ms": t.get("submit_to_visible_ms")}))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:
        print("timing: skipped (%s)" % e)
        sys.exit(0)
