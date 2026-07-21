import os, glob, yaml, json, re, hashlib, importlib
import gm_controllers as gmc; importlib.reload(gmc)
ckpt=r"E:\StarWars\_readiness_checkpoint_20260720"
ROOT=r"E:\StarWars"
def norm(s): return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()
def slug(s): return re.sub(r'[^a-z0-9]+','_',str(s).lower()).strip('_')[:48]

# ---- deep source index: normalized_name -> [{lane,path}] incl. nested features ----
LANES=[("global_validated",r"E:\StarWars\SW5e_Data_Hub\forge_v3\backend"),
       ("global_validated",r"E:\StarWars\SW5e_Data_Hub\source_data"),
       ("campaign_local",r"E:\StarWars\SW5e_Data_Hub\forge_v3\data\campaign_local")]
idx={}
def add(nm,lane,path):
    if nm: idx.setdefault(norm(nm),[]).append({"lane":lane,"path":os.path.relpath(path,ROOT)})
def harvest(o,lane,path):
    if isinstance(o,dict):
        if o.get('name'): add(o['name'],lane,path)
        for v in o.values(): harvest(v,lane,path)
    elif isinstance(o,list):
        for v in o: harvest(v,lane,path)
for lane,root in LANES:
    if not os.path.isdir(root): continue
    for f in glob.glob(os.path.join(root,"**","*.yml"),recursive=True)+glob.glob(os.path.join(root,"**","*.yaml"),recursive=True):
        try: harvest(yaml.safe_load(open(f,encoding="utf-8")),lane,f)
        except: pass

UNIVERSAL_ACTIONS={"unarmed strike","grapple","shove","dodge","dash","disengage","help","hide","ready","search"}
def is_instance(nm):  # unique/personalized -> character_instance
    n=nm.lower()
    return any(k in n for k in ("taron-forged","taron","personal","modular indigo","custom","-forged","master ")) or "'s " in nm.lower()

# ---- corrected extractor ----
def slots_for(cid):
    gmc.mount_campaign(cid); rt=gmc.load_runtime(); pid=rt["metadata"].get("active_player"); sh=(rt.get("player_characters") or {}).get(pid) or {}
    idn=sh.get("identity") or {}; slots=[]
    def add_slot(dom,name,src=None,extra=None): slots.append({"domain":dom,"source_name":name,"cited_source":src,**(extra or {})})
    for dom in ("species","class","subclass","background"):
        v=idn.get(dom) or idn.get(dom+"_name")
        if v: add_slot(dom,v)
    for f in (sh.get("features") or []):
        if isinstance(f,dict) and f.get("name"): add_slot("feature",f["name"],f.get("source"))
    for p in (sh.get("powers") or []):
        if isinstance(p,dict) and p.get("name"): add_slot("power",p["name"],p.get("source"))
    eq=sh.get("equipment") or {}
    for w in (eq.get("weapons") or []):
        nm=w.get("name") if isinstance(w,dict) else w
        if nm and norm(nm) in UNIVERSAL_ACTIONS: add_slot("action",nm)
        elif nm: add_slot("item_instance" if is_instance(nm) else "item_definition",nm,(w.get("source") if isinstance(w,dict) else None))
    ar=eq.get("armor")
    if isinstance(ar,dict) and ar.get("name"): add_slot("item_instance" if is_instance(ar["name"]) else "item_definition",ar["name"])   # SINGLETON -> ONE item
    elif isinstance(ar,list):
        for a in ar:
            nm=a.get("name") if isinstance(a,dict) else a
            if nm: add_slot("item_definition",nm)
    for it in (eq.get("inventory") or [])+(eq.get("gear") or []):
        nm=(it.get("item") or it.get("name")) if isinstance(it,dict) else it
        if nm and norm(nm) in UNIVERSAL_ACTIONS: add_slot("action",nm)
        elif nm: add_slot("item_definition",nm)
    return pid,slots

# ---- resolve each slot ----
def resolve(slot):
    nm=slot["source_name"]; dom=slot["domain"]
    # 1) cited source path (exact_path)
    cited=slot.get("cited_source")
    if cited:
        base=os.path.basename(cited)
        hit=glob.glob(os.path.join(ROOT,"**",base),recursive=True)
        hit=[h for h in hit if "node_modules" not in h and ".venv" not in h]
        if hit:
            return {"resolution_status":"exact_validated","authority_lane":"global_validated","proposed_urid":f"{dom.split('_')[0]}_{slug(nm)}","source_path":os.path.relpath(hit[0],ROOT),"method":"exact_path"}
    # 2) name index
    hits=idx.get(norm(nm),[])
    if hits:
        lane=hits[0]["lane"]
        return {"resolution_status":"exact_validated" if lane=="global_validated" else "campaign_local_adaptation","authority_lane":lane,"proposed_urid":f"{dom.split('_')[0]}_{slug(nm)}","source_path":hits[0]["path"],"method":"exact_name"}
    # 3) domain-specific classification
    if dom=="action": return {"resolution_status":"reviewed_alias","authority_lane":"global_validated","proposed_urid":f"action_{slug(nm)}","source_path":None,"method":"universal_action"}
    if dom=="item_instance": return {"resolution_status":"character_instance","authority_lane":"character_instance","proposed_urid":f"iteminst_{slug(nm)}","source_path":None,"method":"unique_instance"}
    if "master" in nm.lower() or "network" in nm.lower(): return {"resolution_status":"relationship_edge","authority_lane":"relationship_edge","proposed_urid":f"rel_{slug(nm)}","source_path":None,"method":"relationship"}
    return {"resolution_status":"genuine_missing","authority_lane":"unresolved","proposed_urid":f"{dom.split('_')[0]}_{slug(nm)}","source_path":None,"method":"none"}

import collections
inv=collections.Counter(); report={}
for cid in ("meridian_reach","shadows_of_empire"):
    pid,slots=slots_for(cid); rows=[]
    for s in slots:
        r=resolve(s); rows.append({**s,**r}); inv[(cid,s["domain"])]+=1; inv[("STATUS",r["resolution_status"])]+=1
    report[cid]={"character_id":pid,"slots":rows}
    json.dump(report[cid], open(ckpt+f"\\golden_source_candidates_{cid}.json","w"), indent=1, ensure_ascii=False)
# authoritative inventory
mslots=len(report["meridian_reach"]["slots"]); sslots=len(report["shadows_of_empire"]["slots"])
dom_counts=collections.Counter(r["domain"] for c in report for r in report[c]["slots"])
status_counts=collections.Counter(r["resolution_status"] for c in report for r in report[c]["slots"])
inventory={"total_reference_slots":mslots+sslots,"meridian_slots":mslots,"shadows_slots":sslots,
  "false_slots_removed":"armor singleton keys + property fields no longer counted",
  "domains":dict(dom_counts),"resolution_status":dict(status_counts)}
json.dump(inventory, open(ckpt+r"\golden_slice_reference_inventory.json","w"), indent=1)
print("AUTHORITATIVE INVENTORY:", json.dumps(inventory,indent=1))
print("\nRESOLUTION by status:", json.dumps(dict(status_counts)))
for cid in report:
    print(f"\n-- {cid} --")
    for r in report[cid]["slots"]: print(f"   [{r['resolution_status']:22}] {r['domain']:15} {str(r['source_name'])[:30]:30} -> {r['proposed_urid']}")
