import os, glob, yaml, json, re, importlib
import gm_controllers as gmc; importlib.reload(gmc)
ckpt=r"E:\StarWars\_readiness_checkpoint_20260720"
LANES=[("global_validated",r"E:\StarWars\SW5e_Data_Hub\forge_v3\backend"),
       ("global_validated",r"E:\StarWars\SW5e_Data_Hub\source_data"),
       ("forge_wip",r"E:\StarWars\SW5e_Data_Hub\forge_v3\data\wip"),
       ("campaign_local",r"E:\StarWars\SW5e_Data_Hub\forge_v3\data\campaign_local")]
def norm(s): return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()
# index: normalized_name -> list of (lane, path, kind)
idx={}
def add(nm, lane, path, kind):
    if not nm: return
    idx.setdefault(norm(nm),[]).append({"lane":lane,"path":os.path.relpath(path,r"E:\StarWars"),"kind":kind})
def harvest(doc, lane, path):
    if isinstance(doc,dict):
        nm=doc.get('name') or (doc.get('metadata') or {}).get('name')
        if nm: add(nm,lane,path,'entity')
        for key in ('features','traits','powers','items','actions','weapons','feats','class_features','maneuvers'):
            v=doc.get(key)
            if isinstance(v,list):
                for it in v:
                    if isinstance(it,dict) and (it.get('name')): add(it['name'],lane,path,key)
                    elif isinstance(it,str): add(it,lane,path,key)
        for v in doc.values(): harvest(v,lane,path)
    elif isinstance(doc,list):
        for it in doc: harvest(it,lane,path)
for lane,root in LANES:
    if not os.path.isdir(root): continue
    for f in glob.glob(os.path.join(root,"**","*.yml"),recursive=True)+glob.glob(os.path.join(root,"**","*.yaml"),recursive=True):
        try: harvest(yaml.safe_load(open(f,encoding="utf-8")),lane,f)
        except: pass
print("indexed distinct names:",len(idx))
# resolve the 43 golden-slice slots
def slots_for(cid):
    gmc.mount_campaign(cid); rt=gmc.load_runtime(); pid=rt["metadata"].get("active_player"); sh=(rt.get("player_characters") or {}).get(pid) or {}
    idn=sh.get("identity") or {}; out=[]
    for dom,val in [("species",idn.get("species")),("class",idn.get("class")),("subclass",idn.get("subclass")),("background",idn.get("background"))]:
        if val: out.append((dom,val))
    for f in (sh.get("features") or []): out.append(("feature", f.get("name") if isinstance(f,dict) else f))
    for p in (sh.get("powers") or []): out.append(("power", p.get("name") if isinstance(p,dict) else p))
    eq=sh.get("equipment") or {}
    for s in ("weapons","armor","inventory","gear"):
        for it in (eq.get(s) or []): out.append(("item",(it.get("name") or it.get("item")) if isinstance(it,dict) else it))
    return pid,out
recon={}
for cid in ("meridian_reach","shadows_of_empire"):
    pid,slots=slots_for(cid); rows=[]; ex=0; miss=0
    for dom,nm in slots:
        hits=idx.get(norm(nm),[])
        status="exact_source" if hits else "genuine_missing"
        if hits: ex+=1
        else: miss+=1
        rows.append({"domain":dom,"source_name":nm,"candidates":hits[:3],"status":status})
    recon[cid]={"character_id":pid,"required_slots":len(slots),"exact_source_matches":ex,"genuine_missing":miss,"rows":rows}
    json.dump(recon[cid], open(ckpt+f"\\golden_slice_resolution_{cid}.json","w"), indent=1, ensure_ascii=False)
    print(f"\n== {cid} ({pid}): {len(slots)} slots, resolved={ex}, missing={miss} ==")
    for r in rows: 
        c=r["candidates"][0]["path"] if r["candidates"] else "-"
        print(f"   [{r['status']:14}] {r['domain']:9} {str(r['source_name'])[:34]:34} -> {c}")
tot=sum(recon[c]["required_slots"] for c in recon); res=sum(recon[c]["exact_source_matches"] for c in recon)
print(f"\nGOLDEN-SLICE SOURCE RECONCILIATION: {res}/{tot} resolved from sources, {tot-res} genuine-missing")
