import json, importlib, re
import gm_controllers as gmc; importlib.reload(gmc)
import server; importlib.reload(server); server.build_registry(); REG=server.REGISTRY
ckpt=r"E:\StarWars\_readiness_checkpoint_20260720"
# registry name index for evidence-based mapping
name_to_urid={}
for u,d in REG.items():
    nm=(d.get('name') or (d.get('metadata') or {}).get('name'))
    if nm: name_to_urid[str(nm).strip().lower()]=u
def slug(s): return re.sub(r'[^a-z0-9]+','_',str(s).lower()).strip('_')
def mapentry(domain, name):
    if not name: return None
    key=str(name).strip().lower()
    urid=name_to_urid.get(key)
    if urid: return {"domain":domain,"source_name":name,"proposed_urid":urid,"evidence":"exact registry name match","confidence":1.0,"status":"exact"}
    return {"domain":domain,"source_name":name,"proposed_urid":f"{domain}_{slug(name)[:40]}","evidence":"no registry match","confidence":0.0,"status":"unresolved"}
def manifest(cid):
    gmc.mount_campaign(cid)
    rt=gmc.load_runtime(); pcs=rt.get("player_characters") or {}
    pid=rt["metadata"].get("active_player"); sh=pcs.get(pid) or {}
    idn=sh.get("identity") or {}
    rows=[]
    for dom,val in [("species",idn.get("species_name") or idn.get("species")),("class",idn.get("class_name") or idn.get("class")),
                    ("subclass",idn.get("subclass_name") or idn.get("subclass")),("background",idn.get("background_name") or idn.get("background"))]:
        e=mapentry(dom,val)
        if e: rows.append(e)
    for f in (sh.get("features") or []):
        nm=f.get("name") if isinstance(f,dict) else f
        e=mapentry("feature",nm)
        if e: rows.append(e)
    for p in (sh.get("powers") or []):
        nm=p.get("name") if isinstance(p,dict) else p
        e=mapentry("power",nm)
        if e: rows.append(e)
    eq=sh.get("equipment") or {}
    for slot in ("weapons","armor","inventory","gear"):
        for it in (eq.get(slot) or []):
            nm=(it.get("name") or it.get("item")) if isinstance(it,dict) else it
            e=mapentry("item",nm)
            if e: rows.append(e)
    unresolved=[r for r in rows if r["status"]=="unresolved"]
    man={"character_id":pid,"campaign_id":cid,"mappings":rows,
         "exact":sum(1 for r in rows if r["status"]=="exact"),"unresolved":len(unresolved),
         "note":"Only exact/reviewed mappings may be written to canonical runtime. Unresolved => author the registry definition or reviewer assigns URID."}
    json.dump(man, open(ckpt+f"\\runtime_reference_mapping_{cid}.json","w"), indent=1, ensure_ascii=False)
    return man
for cid in ("meridian_reach","shadows_of_empire"):
    m=manifest(cid); print(f"{cid}: {len(m['mappings'])} slots, exact={m['exact']}, unresolved={m['unresolved']}")
    for r in m["mappings"][:6]: print(f"   [{r['status']}] {r['domain']}: {r['source_name']} -> {r['proposed_urid']}")
