"""Build the private development preview of the Genesis Datapad (TB4 + WHISPER initiative).

python3 development/preview/build_preview.py [--milestone M0] [--out development/preview/out]
python3 development/preview/serve_preview.py            # builds, then serves on http://127.0.0.1:8080

The page is the real Datapad build (campaigns/starwars_litrpg/ui/genesis_datapad.html) with two things added in front:
a "Genesis Development / Test Environment" banner and an in-browser stand-in for the artifact database, seeded with the
public state of the noncanonical fixture campaign (development/mobile_test/fixture_campaign, "Sim Deck: Drill Seven").

What it is not: there is no GM, no gateway, no dice and no network. A submitted turn is stored in the page and marked
"preview: no GM attached". Nothing here can reach Hask Meadow, the artifact database or any credential: the fixture's
public state is the only data embedded, and the GM-only ledger is never read (export_state publishes public state only).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "campaigns/starwars_litrpg/ui"))
import export_state  # noqa: E402

FIXTURE = ROOT / "development/mobile_test/fixture_campaign"
FIXTURE_ID = "mobile-test-1"
PAGE = ROOT / "campaigns/starwars_litrpg/ui/genesis_datapad.html"

# Features and their switches are listed in features.json (one place, read by banner and tests).
FEATURES = Path(__file__).with_name("features.json")

MOCK = r"""
(function(){
  var KEY = "genesis-preview-store-v1";
  var seed = __SEED__;
  var store;
  try { store = JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) { store = null; }
  if (!store || !store["view/state"] || store["view/state"].__seed !== seed["view/state"].__seed) store = JSON.parse(JSON.stringify(seed));
  window.__store = store;
  var subs = [];
  function save(){ try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) {} }
  function notify(){ save(); subs.forEach(function(s){ s(); }); }
  window.__notify = notify;
  window.__resetPreview = function(){ try { localStorage.removeItem(KEY); } catch (e) {} location.reload(); };
  function snap(p){ return { exists: p in store, data: function(){ return JSON.parse(JSON.stringify(store[p])); }, id: p.split("/").pop() }; }
  function ref(p){ return { id: p.split("/").pop(), path: p,
    get: function(){ return Promise.resolve(snap(p)); },
    set: function(d){ store[p] = JSON.parse(JSON.stringify(d)); if (p.indexOf("actions/") === 0) previewGm(p); setTimeout(notify, 5); return Promise.resolve(); },
    update: function(d){ if (!(p in store)) return Promise.reject({ code: "invalid_argument" }); Object.assign(store[p], d); setTimeout(notify, 5); return Promise.resolve(); },
    delete: function(){ delete store[p]; setTimeout(notify, 5); return Promise.resolve(); },
    onSnapshot: function(next){ var f = function(){ next(snap(p)); }; subs.push(f); setTimeout(f, 5); return function(){}; } }; }
  function coll(c){ var q = { orderBy: function(){ return q; }, limit: function(){ return q; }, where: function(){ return q; },
    onSnapshot: function(next){ var f = function(){ next({ docs: Object.keys(store).filter(function(k){ return k.indexOf(c + "/") === 0 && k.slice(c.length + 1).indexOf("/") < 0; })
      .map(function(k){ return { id: k.slice(c.length + 1), data: function(){ return JSON.parse(JSON.stringify(store[k])); } }; })
      .sort(function(a, b){ return (b.data().created_ms || 0) - (a.data().created_ms || 0); }) }); }; subs.push(f); setTimeout(f, 5); return function(){}; },
    doc: function(id){ return ref(c + "/" + (id || Math.random().toString(36).slice(2))); } }; return q; }
  function previewGm(p){ setTimeout(function(){ var a = store[p]; if (!a || a.status !== "submitted") return;
    if (a.kind === "whisper_response") { var v = store["view/state"], w = a.whisper, pend = v.whisper && v.whisper.pending;
      if (pend) { if (["accept", "edit", "custom"].indexOf(w.choice) >= 0) { var c = pend.candidates.filter(function(x){ return x.candidate_id === w.candidate_id; })[0];
          v.whisper.history.push({ text: w.text || (c && c.proposed), theme: c ? c.theme : "custom", player_confirmed: true }); }
        if (w.choice !== "defer") pend.candidates = pend.candidates.filter(function(x){ return w.candidate_id && x.candidate_id !== w.candidate_id; });
        if (!pend.candidates.length) v.whisper.pending = null; }
      a.status = "committed"; a.preview = true; notify(); return; }
    a.status = "failed"; a.error = "Preview only: no GM is attached to this page. Your declaration was kept exactly as submitted."; a.preview = true; notify(); }, 400); }
  var db = { doc: ref, collection: coll };
  var mcp = { callTool: function(){ return Promise.reject({ code: "preview_no_gm", message: "Development preview: no GM attached" }); } };
  window.claude = { use: function(n){ return Promise.resolve(n === "db" ? db : n === "mcp" ? mcp : null); } };
})();
"""

BANNER = """<div id="devEnvBanner" role="note" style="position:sticky;top:0;z-index:50;background:#3b2f00;color:#ffe9a8;border-bottom:2px solid #ffcf40;
padding:8px max(16px,env(safe-area-inset-left,0px));font:13px/1.4 system-ui,sans-serif">
<b>Genesis Development / Test Environment</b> · milestone <b>__MILESTONE__</b> · code <code>__SHA__</code> · fixture <b>__FIXTURE__</b> (noncanonical)
<details style="margin-top:4px"><summary>Features and limits</summary><div>__FEATURES__</div>
<div style="margin-top:4px"><button type="button" onclick="window.__resetPreview()" style="font:inherit">Reset preview state</button>
 · <a href="diagnostics.html" style="color:inherit">WHISPER / evidence / causal diagnostics</a></div></details></div>"""


def git_sha():
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def features_html(features):
    rows = []
    for f in features["features"]:
        state = "on" if f["enabled"] else "off"
        rows.append(f"<li><b>{f['name']}</b> — {state}. {f['note']}</li>")
    rows.append("<li><b>Not available here</b> — " + "; ".join(features["unavailable"]) + ".</li>")
    return "<ul style='margin:4px 0;padding-left:18px'>" + "".join(rows) + "</ul>"


def diagnostics_page(sha, milestone):
    """Static read-out of the pure evaluators (M4–M6) on their noncanonical fixtures. No model calls."""
    import html as H
    sys.path.insert(0, str(ROOT / "development/whisper")); sys.path.insert(0, str(ROOT / "development/causal"))
    import evidence, appraisal, causal  # noqa: E402
    W = ROOT / "development/whisper/fixtures"
    cmp = json.loads((W / "cmp001_ten_missing_crates.json").read_text())
    envs = evidence.envelopes(cmp["events"], cmp["entities"])
    rows = []
    for who in ("player", ("npc", "dockworker_7"), ("npc", "neri"), ("npc", "smuggler_kesh")):
        got = evidence.retrieve(envs, who)
        rows.append(f"<h3>{H.escape(str(who))}</h3><ul>" + "".join(
            f"<li><code>{x['source_event']}</code> <b>{x['type']}</b>{' (retracted)' if x.get('retracted') else ''} — {H.escape(x['summary'] or '')}</li>" for x in got) + ("</ul>" if got else "<li>nothing</li></ul>"))
    moral = json.loads((W / "tb4_moral_001.json").read_text())["cases"]
    mrows = "".join(f"<tr><td>{H.escape(k)}</td><td>{H.escape(appraisal.moral(v)['finding'])}</td><td>{H.escape(appraisal.psychological(v)[0]['candidate'])}</td></tr>" for k, v in moral.items())
    cf = json.loads((ROOT / "development/causal/fixtures/causal_fixture.json").read_text())
    snap = {"relationships": cf["relationships"], "facts": cf["facts"]}
    ev = {"event_id": "evt_0900", "kind": "attack_resolved", "accepted": True, "actor": "aero", "known_to": ["aero", "wick", "mira"],
          "details": {"attacker": "aero", "target": "thug", "moral_finding": "unjustified_harm"}}
    r = causal.resolve(ev, snap, cf["rules"])
    crow = "<pre style='white-space:pre-wrap'>" + H.escape(json.dumps(r, indent=1)) + "</pre>"
    return ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Genesis diagnostics</title>"
            "<body style='font:15px/1.5 system-ui,sans-serif;max-width:860px;margin:auto;padding:16px'>"
            f"<p style='background:#3b2f00;color:#ffe9a8;padding:8px'><b>Genesis Development / Test Environment</b> · {milestone} · code <code>{sha}</code> · noncanonical fixtures · pure evaluators, nothing is committed</p>"
            "<p><a href='./'>← back to the preview Datapad</a></p><h2>Algorithm A — who knows what (CMP-001 Ten Missing Crates)</h2>" + "".join(rows) +
            "<h2>Algorithm B — appraisal candidates (TB4-MORAL-001)</h2><table border=1 cellpadding=4 style='border-collapse:collapse'><tr><th>case</th><th>moral finding</th><th>PC candidate (proposed)</th></tr>" + mrows + "</table>"
            "<h2>Algorithm C — causal proposals (Aero strikes a surrendered thug; Wick and Mira watch)</h2>" + crow + "</body>")


def build(milestone=None, out=None):
    features = json.loads(FEATURES.read_text())
    milestone = milestone or features["milestone"]
    sha = git_sha()
    state = export_state.build(campaign_dir=FIXTURE, campaign_id=FIXTURE_ID)
    state["__seed"] = sha + ":" + milestone
    state["test_build"] = {"canonical": False, "code_commit": sha,
                           "note": "Development preview: fixture data only, no GM attached, nothing is canonical."}
    state["processor"] = None
    state["preview_features"] = {f["id"]: f["enabled"] for f in features["features"]}
    state["features"] = {f["id"]: f["enabled"] for f in features["features"] if f["id"] in export_state.FEATURE_SWITCHES}
    if state["features"].get("whisper_review"):   # sample review from the TB4-MORAL-001 fixture (noncanonical)
        sys.path.insert(0, str(ROOT / "development/whisper"))
        import post_turn
        cases = json.loads((ROOT / "development/whisper/fixtures/tb4_moral_001.json").read_text())["cases"]
        review = post_turn.propose(cases["failed_rescue"], [])
        state["whisper"] = {"pending": {"review_id": "preview_review", "action_id": review["action_id"], "candidates": review["candidates"],
                                        "note": review["note"] + " (Preview sample from a test fixture.)"}, "history": []}
    seed = {"view/state": state}
    html = PAGE.read_text()
    title_end = html.index("</title>") + len("</title>")
    banner = (BANNER.replace("__MILESTONE__", milestone).replace("__SHA__", sha)
              .replace("__FIXTURE__", "Sim Deck: Drill Seven (mobile-test-1)").replace("__FEATURES__", features_html(features)))
    mock = MOCK.replace("__SEED__", json.dumps(seed).replace("</", "<\\/"))
    page = ("<!doctype html><html><head><meta charset=utf-8><meta name=viewport content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
            + html[:title_end].replace("<title>Genesis Datapad</title>", "<title>Genesis Dev Preview</title>")
            + "<script>" + mock + "</script></head><body>" + banner + html[title_end:] + "</body></html>")
    out = Path(out or Path(__file__).with_name("out"))
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page)
    (out / "diagnostics.html").write_text(diagnostics_page(sha, milestone))
    (out / "build.json").write_text(json.dumps({"milestone": milestone, "code_commit": sha, "fixture": FIXTURE_ID}, indent=1))
    return out / "index.html"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--milestone")
    ap.add_argument("--out")
    a = ap.parse_args()
    print(build(a.milestone, a.out))
