import json, re
import gm_controllers as gmc
ckpt=r"E:\StarWars\_readiness_checkpoint_20260720"
MERIDIAN=[r"\bilo\b",r"\baero\b",r"\bdax\b",r"\bbesk\b",r"\bmeridian\b",r"\bstillwater\b",r"\btaron\b",r"\bsenn\b",r"\bmaza\b"]
SHADOWS=[r"\breyes\b",r"\byuel\b",r"\bvardos\b",r"\breconciliator",r"\bvoss\b",r"\bzoran\b",r"\btala\b"]
def leaks(text,pats): 
    t=text.lower(); return [p for p in pats if re.search(p,t)]
seq=["meridian_reach","shadows_of_empire","meridian_reach","shadows_of_empire","meridian_reach"]
results=[]; ok=True
for i,cid in enumerate(seq):
    gmc.mount_campaign(cid)
    st=gmc.player_visible_state(); meta=st.get("metadata",{})
    blob=json.dumps(st,ensure_ascii=False)
    foreign = SHADOWS if cid=="meridian_reach" else MERIDIAN
    lk=leaks(blob,foreign)
    cid_ok=(st.get("mounted")==cid and meta.get("campaign_id")==cid)
    npcs=[v.get("name") for v in (st.get("active_npcs") or {}).values()]
    ok = ok and cid_ok and not lk
    results.append({"step":i+1,"mount":cid,"cid_ok":cid_ok,"foreign_leaks":lk,"npcs":npcs})
    print(f"step {i+1}: {cid} cid_ok={cid_ok} leaks={lk} npcs={npcs}")
# also assert hidden_gm_state never in visible
hidden_ok = "hidden_gm_state" not in json.dumps(gmc.player_visible_state())
print("\nhidden_gm_state excluded from visible:", hidden_ok)
print("ISOLATION TEST:", "PASS" if (ok and hidden_ok) else "FAIL")
json.dump({"pass":bool(ok and hidden_ok),"hidden_excluded":hidden_ok,"sequence":seq,"results":results},
          open(ckpt+r"\05_campaign_isolation_test.json","w"),indent=2)
