import re, json, yaml
LINE=re.compile(r"^(\s*[\w-]+:\s*)'(.*)'\s*$")
def fix_file(path):
    out=[]; fixed=0
    for ln in open(path,encoding="utf-8").read().split("\n"):
        m=LINE.match(ln)
        if m and ("'" in m.group(2) or '"' in m.group(2)):
            out.append(m.group(1)+json.dumps(m.group(2))); fixed+=1
        else:
            out.append(ln)
    open(path,"w",encoding="utf-8").write("\n".join(out))
    return fixed
for f in ["gm/aero_character_runtime.yml","gm/aero_hidden_gm_ledger.yml"]:
    n=fix_file(f)
    try:
        d=yaml.safe_load(open(f,encoding="utf-8")); print(f"{f}: re-quoted {n} lines -> PARSES OK")
    except Exception as e:
        print(f"{f}: re-quoted {n} -> STILL BROKEN: {str(e)[:160]}")
d=yaml.safe_load(open("gm/aero_character_runtime.yml",encoding="utf-8")); cr=d.get("character_runtime",d)
print("AERO NAME:", repr((cr.get("identity") or {}).get("name")))
print("EQUIP armor type:", type((cr.get("equipment") or {}).get("armor")).__name__)
