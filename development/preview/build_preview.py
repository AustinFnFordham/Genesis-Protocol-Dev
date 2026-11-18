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
<div style="margin-top:4px"><button type="button" onclick="window.__resetPreview()" style="font:inherit">Reset preview state</button></div></details></div>"""


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
    (out / "build.json").write_text(json.dumps({"milestone": milestone, "code_commit": sha, "fixture": FIXTURE_ID}, indent=1))
    return out / "index.html"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--milestone")
    ap.add_argument("--out")
    a = ap.parse_args()
    print(build(a.milestone, a.out))
