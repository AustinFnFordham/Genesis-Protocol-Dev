#!/usr/bin/env python3
"""Assemble the Genesis Datapad page from its sources (single published HTML file).

  src/head.html      styles + markup (unchanged look)
  turn_contract.js   the composite-turn contract, shared with the GM processor (inlined verbatim)
  src/core.js        state, character / gear / record renderers
  src/composer.js    turn composer, submission states, automatic GM start

Usage: build_datapad.py [--title "Genesis Datapad"] [--out genesis_datapad.html]
"""
import argparse
from pathlib import Path
H = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument("--title", default="Genesis Datapad"); ap.add_argument("--out", default=str(H / "genesis_datapad.html"))
a = ap.parse_args()
head = (H / "src" / "head.html").read_text(encoding="utf-8").replace("<title>Genesis Datapad</title>", f"<title>{a.title}</title>", 1)
page = (head + "<script>\n" + (H / "turn_contract.js").read_text(encoding="utf-8").split("/* node CLI:")[0] + "\n</script>\n<script>\n"
        + (H / "src" / "core.js").read_text(encoding="utf-8") + (H / "src" / "composer.js").read_text(encoding="utf-8"))
Path(a.out).write_text(page, encoding="utf-8")
print(a.out, len(page))
