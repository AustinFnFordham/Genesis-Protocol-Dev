import json, os, importlib
import gm_controllers as gmc
importlib.reload(gmc)
ckpt=r"E:\StarWars\_readiness_checkpoint_20260720"
R=json.load(open(ckpt+r"\06_phase_a_tests.json"))
# fix item enforcement assertion: 3 non-weapons flagged AND blaster (real weapon) NOT flagged
v=R["item_slot_violations"]
R["item_enforcement_ok"]=(sum('non_weapon_in_weapon_slot' in x for x in v)==3 and not any('blaster' in x.lower() for x in v))
# opening: test the PERSISTED CACHE path on shadows (no authored opening.md)
gmc.mount_campaign("shadows_of_empire")
cdir=os.path.dirname(gmc._paths("shadows_of_empire")["runtime"])
authored=os.path.join(cdir,"opening.md"); cache=os.path.join(cdir,"opening.generated.json")
if os.path.exists(authored): os.remove(authored)
json.dump({"cinematic_exposition":"TOKEN_CRAWL_SHADOWS_B2","active_cast":["Captain Dara Reyes"],"mission_summary":"deliver intel"},open(cache,"w"))
o1=gmc.get_opening(); o2=gmc.get_opening()
R["opening_cache_source"]=o1.get("source")
R["opening_stable"]=(o1.get("cinematic_exposition")==o2.get("cinematic_exposition")=="TOKEN_CRAWL_SHADOWS_B2" and o1.get("source")=="persisted")
# meridian authored path
gmc.mount_campaign("meridian_reach"); a1=gmc.get_opening(); a2=gmc.get_opening()
R["opening_authored_stable"]=(a1.get("source")=="authored" and a1.get("cinematic_exposition")==a2.get("cinematic_exposition"))
R["PHASE_A_TESTS_PASS"]=all([R["item_classify_ok"],R["item_enforcement_ok"],R["opening_stable"],R["opening_authored_stable"],R["roundtrip_ok"],R["restart_ok"],R["hidden_ok"]])
json.dump(R,open(ckpt+r"\06_phase_a_tests.json","w"),indent=2)
for k in ["item_enforcement_ok","opening_cache_source","opening_stable","opening_authored_stable","roundtrip_ok","restart_ok","hidden_ok","PHASE_A_TESTS_PASS"]:
    print(k,"=",R[k])
