import importlib, json, glob, os, yaml
import gm_controllers as gmc; importlib.reload(gmc)
import projection as proj; importlib.reload(proj)
import server; importlib.reload(server); server.build_registry(); REG = server.REGISTRY
# 1) Is there a real Operator CLASS vs subclass?
print("=== class/operator sources ===")
for f in glob.glob(r"E:\StarWars\SW5e_Data_Hub\forge_v3\backend\classes\**\*.yml", recursive=True):
    b = os.path.basename(f).lower()
    if "operator" in b or "operator" in f.lower():
        print("  ", os.path.relpath(f, r"E:\StarWars"))
for f in glob.glob(r"E:\StarWars\SW5e_Data_Hub\forge_v3\backend\**\*operator*.yml", recursive=True):
    print("  match:", os.path.relpath(f, r"E:\StarWars"))
# Aran's campaign_local Character: does it name a class?
ac = glob.glob(r"E:\StarWars\SW5e_Data_Hub\forge_v3\data\campaign_local\Character__char_smuggler*.yml")
if ac:
    d = yaml.safe_load(open(ac[0], encoding="utf-8"))
    print("Aran campaign_local keys:", [k for k in d.keys()][:20])
    print("  class_id:", d.get("class_id"), "class:", d.get("class"), "tags:", (d.get("tags") or [])[:6])
# 2) shadows unresolved ref + party summaries
gmc._MOUNTED["id"] = None; gmc.mount_campaign("shadows_of_empire")
p = proj.build_projection(REG, runtime_mode="live")
print("\nshadows ref_integrity:", json.dumps((p.get("operative") or {}).get("reference_integrity") or {}))
print("party.characters_by_id:")
for pid, v in ((p.get("party") or {}).get("characters_by_id") or {}).items():
    s = v.get("player_visible_runtime_summary") or {}
    print("  ", pid, "species=", s.get("species"), "class=", s.get("class"))
# species_human lane record
sh = REG.get("species_human")
print("\nspecies_human lane: name=", (sh or {}).get("name"), "authority=", (sh or {}).get("authority_lane"), "effect=", bool((sh or {}).get("effect")))
