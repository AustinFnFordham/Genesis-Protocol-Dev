import os, json, glob, shutil, time, importlib
stamp=time.strftime("%Y%m%d_%H%M%S")
for cd in glob.glob("gm/campaigns/*"):
    if not os.path.isdir(cd): continue
    broken=False
    for jf in glob.glob(os.path.join(cd,"*.json")):
        try: json.load(open(jf,encoding="utf-8"))
        except Exception: broken=True
    for jl in glob.glob(os.path.join(cd,"*.jsonl")):
        for ln in open(jl,encoding="utf-8"):
            if ln.strip():
                try: json.loads(ln)
                except Exception: broken=True; break
    if broken:
        bak=os.path.join("gm","_corruption_backup",os.path.basename(cd)+"_"+stamp)
        os.makedirs(bak,exist_ok=True)
        for sf in ("runtime_state.json","transcript_archive.jsonl","chronicle.jsonl","turn_log.jsonl"):
            p=os.path.join(cd,sf)
            if os.path.exists(p): shutil.move(p, os.path.join(bak,sf))
        print(f"{os.path.basename(cd)}: session files backed up to {bak} (will rebuild clean)")
    else:
        print(f"{os.path.basename(cd)}: clean")
# now rebuild + verify boundary
import gm_controllers as gmc; importlib.reload(gmc)
gmc.mount_campaign("meridian_reach")
st=gmc.player_visible_state()
name=(st.get("player_characters") or {}).get("aero",{}).get("identity",{}).get("name")
eq=(st.get("player_characters") or {}).get("aero",{}).get("equipment",{})
print("NAME:",repr(name)," has_x:", "\\x" in json.dumps(st))
print("all_slots_lists:", all(isinstance(eq.get(s),list) for s in ("weapons","armor","gear","vehicles","trinkets","starships")))
print("epoch:", st.get("mount_epoch"), "cid:", st.get("campaign_id"))
