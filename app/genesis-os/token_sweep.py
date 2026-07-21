#!/usr/bin/env python3
"""K — token standardization sweep.
Replaces every raw `fontSize: <num>` literal in src/**/*.jsx with a
`fontSize: 'var(--sys-font-size-XXX)'` token per the snap map. Produces a
measurable before/after report. Non-destructive to any non-fontSize code."""
import re, os, json, sys, collections

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")

# raw px value -> token name (must match design-tokens.css ramp)
SNAP = {
    "7": "micro", "7.5": "micro", "8": "micro",
    "8.5": "label",
    "9": "caption", "9.5": "caption",
    "10": "note", "10.5": "note",
    "11": "meta", "11.5": "meta",
    "12": "control", "12.5": "control",
    "13": "body", "14": "body",
    "16": "narrative",
    "17": "title",
    "20": "heading", "21": "heading", "22": "heading",
    "30": "display",
}

PAT = re.compile(r"fontSize:\s*(\d+(?:\.\d+)?)")

def jsx_files(root):
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.endswith(".jsx"):
                yield os.path.join(dp, fn)

before = collections.Counter()
after_unmapped = []
per_file = {}

for path in sorted(jsx_files(ROOT)):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    hits = PAT.findall(src)
    if not hits:
        continue
    for v in hits:
        before[v] += 1
    def repl(m):
        v = m.group(1)
        tok = SNAP.get(v)
        if tok is None:
            after_unmapped.append((os.path.relpath(path, ROOT), v))
            return m.group(0)  # leave untouched, flag it
        return f"fontSize: 'var(--sys-font-size-{tok})'"
    new, n = PAT.subn(repl, src)
    if new != src:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
    per_file[os.path.relpath(path, ROOT)] = n

# verify: no raw fontSize literals remain
remaining = []
for path in sorted(jsx_files(ROOT)):
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            for m in PAT.finditer(line):
                remaining.append((os.path.relpath(path, ROOT), i, m.group(0)))

report = {
    "literals_before_total": sum(before.values()),
    "distinct_values_before": dict(sorted(before.items(), key=lambda kv: float(kv[0]))),
    "files_touched": {k: v for k, v in sorted(per_file.items()) if v},
    "replacements_total": sum(per_file.values()),
    "unmapped_values": after_unmapped,
    "raw_literals_remaining": remaining,
}
print(json.dumps(report, indent=2))
