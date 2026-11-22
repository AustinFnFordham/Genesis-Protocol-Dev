"""Build the CC-002/CC-003 combat playtest page (Tactical Composer) (noncanonical, self-contained, no network).
python3 development/combat_slice/build_playtest.py [--out DIR]   -> DIR/combat.html (default development/combat_slice/out)
The dev preview server also serves it at /combat.html (development/preview)."""
import argparse
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def page(sha=None):
    if sha is None:
        try:
            sha = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True).strip()
        except Exception:  # noqa: BLE001
            sha = "unknown"
    src = (HERE / "playtest_src.html").read_text()
    data = lambda name: json.dumps(json.loads((HERE / name).read_text()), separators=(",", ":")).replace("</", "<\\/")
    js = lambda name: (HERE / name).read_text().replace("</script", "<\\/script")
    return (src.replace("/*ENGINE*/", js("engine.js")).replace("/*PREDICT*/", js("predict.js")).replace("/*SOUL*/", js("soul.js"))
               .replace("/*CATALOG*/", data("catalog.json")).replace("/*SCENARIOS*/", data("scenarios.json"))
               .replace("__SHA__", sha))


def build(out=None, sha=None, wrap=True):
    out = Path(out or HERE / "out")
    out.mkdir(parents=True, exist_ok=True)
    body = page(sha)
    html = ("<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
            "</head><body>" + body + "</body></html>") if wrap else body
    (out / "combat.html").write_text(html)
    return out / "combat.html"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--artifact", action="store_true", help="write the unwrapped page body for an Artifact publish")
    a = ap.parse_args()
    print(build(a.out, wrap=not a.artifact))
