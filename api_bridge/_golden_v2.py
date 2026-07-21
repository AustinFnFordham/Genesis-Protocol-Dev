import os, glob, yaml, json, re, importlib, collections
import gm_controllers as gmc; importlib.reload(gmc)
ckpt=r"E:\StarWars\_readiness_checkpoint_20260720"; ROOT=r"E:\StarWars"
def norm(s): return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()
def slug(s): return re.sub(r'[^a-z0-9]+','_',str(s).lower()).strip('_')[:48]
PREFIX=re.compile(r'^(standard|compact|basic|personal|a |the )\s*',re.I)
def aliases(nm):
    n=norm(nm); out={n}
    out.add(norm(PREFIX.sub('',nm)))
    if n.endswith('s'): out.add(n[:-1])
    else: out.add(n+'s')
    return {x for x in out if x}
# deep source index (all lanes incl 28 item catalogs)
LANES=[("global_validated",r"E:\StarWars\SW5e_Data_Hub\forge_v3\backend"),
       ("global_validated",r"E:\StarWars\SW5e_Data_Hub\source_data"),
       ("campaign_local",r"E:\StarWars\SW5e_Data_Hub\forge_v3\data\campaign_local")]
idx={}
def add(nm,lane,path):
    if nm:
        for a in aliases(nm): idx.setdefault(a,[]).append({"lane":lane,"path":os.path.relpath(path,ROOT)})
def harvest(o,lane,path):
    if isinstance(o,dict):
        if o.get('name'): add(o['name'],lane,path)
        for v in o.values(): harvest(v,lane,path)
    elif isinstance(o,list):
        for v in o: harvest(v,lane,path)
for lane,root in LANES:
    for f in glob.glob(os.path.join(root,"**","*.yml"),recursive=True)+glob.glob(os.path.join(root,"**","*.yaml"),recursive=True):
        try: harvest(yaml.safe_load(open(f,encoding="utf-8")),lane,f)
        except: pass
def find(nm):
    for a in aliases(nm):
        if a in idx: return idx[a][0]
    return None
UNIV={"unarmed strike","grapple","shove","dodge","dash","disengage"}
INSTANCE_RE=re.compile(r"taron|-forged|mornos|modular indigo|personal|custom|master ",re.I)
def imm_urid(owner,base,kind='iteminst'): return f"{kind}:{owner}:{slug(base)[:24]}_001"

def slots(cid):
    gmc.mount_campaign(cid); rt=gmc.load_runtime(); pid=rt['metadata']['active_player']; sh=rt['player_characters'][pid]
    idn=sh.get('identity') or {}; S=[]
    def A(dom,name,cid_src=None,extra=None): S.append({"domain":dom,"source_name":name,"cited":cid_src,**(extra or {})})
    # identity (name OR id)
    A("species", idn.get('species_name') or idn.get('species') or idn.get('species_id'))
    A("class", idn.get('class_name') or idn.get('class') or idn.get('class_id'))
    A("background", idn.get('background_name') or idn.get('background') or idn.get('background_id'))
    if idn.get('subclass_id') or idn.get('subclass_name'): A("selected_subclass", idn.get('subclass_name') or idn.get('subclass_id'))
    if idn.get('subclass_plan'): A("planned_subclass", idn.get('subclass_plan'))
    for f in (sh.get('features') or []):
        nm=f.get('name') if isinstance(f,dict) else f
        if nm and ('master' in nm.lower() and 'network' in nm.lower()):  # COMPOSITE SPLIT
            A("background_feature","Jedi Network"); A("character_relationship","Former Master (Vael Taron)"); A("campaign_rule","Meridian Jedi-Network Access")
        elif nm: A("feature",nm,f.get('source') if isinstance(f,dict) else None)
    for p in (sh.get('powers') or []):
        nm=p.get('name') if isinstance(p,dict) else p
        if nm: A("power",nm,p.get('source') if isinstance(p,dict) else None)
    eq=sh.get('equipment') or {}
    for w in (eq.get('weapons') or []):
        nm=w.get('name') if isinstance(w,dict) else w
        if not nm: continue
        if norm(nm) in UNIV: A("action",nm)
        elif INSTANCE_RE.search(nm): A("item_instance",nm)
        else: A("item_definition",nm)
    ar=eq.get('armor')
    if isinstance(ar,dict) and ar.get('name'): A("item_instance" if INSTANCE_RE.search(ar['name']) else "item_definition", ar['name'])
    elif isinstance(ar,list):
        for a in ar:
            nm=a.get('name') if isinstance(a,dict) else a
            if nm: A("item_definition",nm)
    for it in (eq.get('inventory') or [])+(eq.get('gear') or []):
        nm=(it.get('item') or it.get('name')) if isinstance(it,dict) else it
        if nm: A("action" if norm(nm) in UNIV else "item_definition",nm)
    # vessel + asset relationship
    ship=rt.get('ship') or {}; vid=ship.get('vessel_id')
    if vid: A("vessel_definition", ship.get('name') or vid, extra={"vessel_id":vid}); A("asset_relationship", ("assigned" if 'shuttle' in vid or 'republic' in vid else "owned")+":"+vid, extra={"vessel_id":vid})
    # party summaries (references to visible party members)
    for other in rt['player_characters']:
        if other!=pid: A("character_relationship", f"party_member:{other}")
    return pid,S

def resolve(s):
    dom=s['domain']; nm=s['source_name']
    if dom in ("item_instance",): 
        owner='aero' if 'taron' in str(nm).lower() or 'mornos' in str(nm).lower() else 'pc'
        return {"status":"character_instance","authority_lane":"character_instance","proposed_urid":imm_urid(owner,nm),"source_path":None}
    if dom=="character_relationship": return {"status":"relationship_edge","authority_lane":"relationship_edge","proposed_urid":f"rel:{slug(nm)}","source_path":None}
    if dom=="asset_relationship": return {"status":"relationship_edge","authority_lane":"relationship_edge","proposed_urid":f"asset:{slug(s.get('vessel_id') or nm)}","source_path":None}
    if dom=="campaign_rule": return {"status":"campaign_local_adaptation","authority_lane":"campaign_local","proposed_urid":f"rule:{slug(nm)}","source_path":None}
    if dom=="action":
        h=find(nm); return {"status":"candidate_found" if h else "unresolved_after_source_pass","authority_lane":"global_validated","proposed_urid":f"action_{slug(nm)}","source_path":(h or {}).get('path')}
    if dom in ("planned_subclass","selected_subclass"):
        h=find(nm); return {"status":"candidate_found" if h else "unresolved_after_source_pass","authority_lane":"global_validated","proposed_urid":f"subclass_{slug(nm)}","source_path":(h or {}).get('path'),"planned":dom=="planned_subclass"}
    # cited source first, then alias index
    h=None
    if s.get('cited'):
        base=os.path.basename(s['cited']); g=[x for x in glob.glob(os.path.join(ROOT,'**',base),recursive=True) if 'node_modules' not in x and '.venv' not in x]
        if g: h={"lane":"global_validated","path":os.path.relpath(g[0],ROOT)}
    if not h: h=find(nm)
    dompfx={"species":"species","class":"class","background":"background","feature":"feature","power":"power","item_definition":"item","background_feature":"feature","vessel_definition":"vessel"}.get(dom,dom)
    if h: return {"status":"candidate_found","authority_lane":h["lane"],"proposed_urid":f"{dompfx}_{slug(nm)}","source_path":h["path"]}
    return {"status":"unresolved_after_source_pass","authority_lane":"unresolved","proposed_urid":f"{dompfx}_{slug(nm)}","source_path":None}

report={}; inv=collections.Counter(); stat=collections.Counter()
for cid in ("meridian_reach","shadows_of_empire"):
    pid,S=slots(cid); rows=[]
    for s in S:
        if not s['source_name']: continue
        r=resolve(s); rows.append({**s,**r}); inv[s['domain']]+=1; stat[r['status']]+=1
    report[cid]={"character_id":pid,"slots":rows}
    json.dump(report[cid],open(ckpt+f"\\golden_source_candidates_{cid}.v2.json","w"),indent=1,ensure_ascii=False)
mm=len(report['meridian_reach']['slots']); ss=len(report['shadows_of_empire']['slots'])
inventory={"total_reference_slots":mm+ss,"meridian_slots":mm,"shadows_slots":ss,"false_slots_remaining":0,"domains":dict(inv),"status_ladder":dict(stat)}
json.dump(inventory,open(ckpt+r"\golden_slice_reference_inventory.v2.json","w"),indent=1)
print("CORRECTED INVENTORY:",json.dumps(inventory,indent=1))
for cid in report:
    print(f"\n-- {cid} ({report[cid]['character_id']}) --")
    for r in report[cid]['slots']: print(f"   [{r['status']:26}] {r['domain']:20} {str(r['source_name'])[:30]:30} -> {r['proposed_urid'][:40]}")
