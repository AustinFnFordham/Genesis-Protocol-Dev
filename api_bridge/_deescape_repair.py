import re, os, glob, io
XESC=re.compile(r'\\x([0-9A-Fa-f]{2})')
def fix(s): return XESC.sub(lambda m: chr(int(m.group(1),16)), s)
targets=[]
targets += glob.glob("gm/*.yml") + glob.glob("gm/*.yaml")
targets += glob.glob("gm/campaigns/**/*.json", recursive=True)
targets += glob.glob("gm/campaigns/**/*.jsonl", recursive=True)
changed=[]
for t in targets:
    raw=open(t,encoding="utf-8").read()
    if "\\x" in raw:
        new=fix(raw)
        if new!=raw:
            open(t,"w",encoding="utf-8").write(new); changed.append((t, raw.count("\\x")))
print("repaired files:", len(changed))
for t,c in changed[:20]: print(f"  {c:4} escapes -> {t}")
# verify aero name now clean
import yaml
d=yaml.safe_load(open("gm/aero_character_runtime.yml",encoding="utf-8"))
cr=d.get("character_runtime",d)
print("AERO NAME NOW:", repr((cr.get("identity") or {}).get("name")))
