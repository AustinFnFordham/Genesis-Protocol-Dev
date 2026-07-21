import json, os, importlib
import gm_controllers as gmc
importlib.reload(gmc)
ckpt=r"E:\StarWars\_readiness_checkpoint_20260720"
R={}

# 1. ITEM TAXONOMY
items={"YT-2400 light freighter":"Starship","Flight jacket":"Gear","Lucky sabacc chip":"Trade_Good",
       "DL-44 heavy blaster pistol":"Weapon","Beskar chestplate":"Armor"}
R["item_classify"]={k:gmc.classify_item(k) for k in items}
R["item_classify_ok"]=all(gmc.classify_item(k)==v for k,v in items.items())
bad_sheet={"equipment":{"weapons":[{"name":"YT-2400 freighter"},{"name":"Flight jacket"},{"name":"Lucky sabacc chip"},{"name":"DL-44 blaster","damage":8}]}}
R["item_slot_violations"]=gmc.validate_item_slots(bad_sheet)
R["item_enforcement_ok"]=len(R["item_slot_violations"])==3  # 3 non-weapons flagged, blaster passes
good=gmc.route_equipment(["YT-2400 freighter","Flight jacket","Lucky sabacc chip","DL-44 blaster"])
R["routed"]={k:[i["name"] for i in v] for k,v in good.items()}

# 2. OPENING PERSISTENCE (seed a cache to avoid LLM; verify stable + source)
gmc.mount_campaign("meridian_reach")
cdir=os.path.dirname(gmc._paths("meridian_reach")["runtime"])
cache=os.path.join(cdir,"opening.generated.json")
json.dump({"cinematic_exposition":"TOKEN_CRAWL_MERIDIAN_A1","active_cast":["Ilo Reeth"],"mission_summary":"escort"},open(cache,"w"))
o1=gmc.get_opening(); o2=gmc.get_opening()
R["opening_source"]=o1.get("source"); R["opening_stable"]=(o1.get("cinematic_exposition")==o2.get("cinematic_exposition")=="TOKEN_CRAWL_MERIDIAN_A1")

# 4. TOKENIZED ISOLATION ROUND-TRIP (append exact tokens directly to per-campaign files)
def append(cid, tok):
    p=gmc._paths(cid)
    open(p["transcript"],"a",encoding="utf-8").write(json.dumps({"entry_id":tok,"type":"narrator","text":tok})+"\n")
    open(p["chronicle"],"a",encoding="utf-8").write(json.dumps({"event_id":tok,"objective_event":tok})+"\n")
gmc.mount_campaign("meridian_reach"); append("meridian_reach","TOKEN_MERIDIAN_7X")
gmc.mount_campaign("shadows_of_empire"); append("shadows_of_empire","TOKEN_SHADOWS_9Y")
def toks(cid):
    gmc.mount_campaign(cid)
    tr=json.dumps(gmc.read_transcript(0,500)); ch=json.dumps(gmc.tail_chronicle(500))
    return ("TOKEN_MERIDIAN_7X" in tr or "TOKEN_MERIDIAN_7X" in ch, "TOKEN_SHADOWS_9Y" in tr or "TOKEN_SHADOWS_9Y" in ch)
m_has_m,m_has_s=toks("meridian_reach"); s_has_m,s_has_s=toks("shadows_of_empire"); m2_has_m,m2_has_s=toks("meridian_reach")
R["roundtrip"]={"meridian_sees_own":m_has_m,"meridian_sees_shadows":m_has_s,"shadows_sees_meridian":s_has_m,"shadows_sees_own":s_has_s,"return_meridian_own":m2_has_m,"return_meridian_shadows":m2_has_s}
R["roundtrip_ok"]=(m_has_m and not m_has_s and s_has_s and not s_has_m and m2_has_m and not m2_has_s)

# 3. RESTART BACKUP (meridian has token in transcript now)
res=gmc.restart_campaign_from_opening("meridian_reach",confirm=True)
gmc.mount_campaign("meridian_reach")
after=json.dumps(gmc.read_transcript(0,500))
R["restart"]={"backup_made":os.path.isdir(res["backup_dir"]),"opening_preserved":res["opening_preserved"],"cleared":res["cleared"][:6],"retained":res["retained"],"token_gone_after_restart":"TOKEN_MERIDIAN_7X" not in after,"backup_has_token":os.path.exists(os.path.join(res["backup_dir"],"transcript_archive.jsonl"))}
R["restart_ok"]=R["restart"]["backup_made"] and R["restart"]["opening_preserved"] and R["restart"]["token_gone_after_restart"]

# 5. HIDDEN-STATE CHANNELS
gmc.mount_campaign("meridian_reach")
vis=json.dumps(gmc.player_visible_state()); tr=json.dumps(gmc.read_transcript(0,500))
R["hidden"]={"not_in_visible_state":"hidden_gm_state" not in vis,"not_in_transcript":"hidden_gm_state" not in tr}
R["hidden_ok"]=all(R["hidden"].values())

# 8. TURN/ROUND ACTION MODEL STATUS
rt=gmc.load_runtime(); comb=rt.get("combat",{})
R["action_model"]={"combat_has_round":"round" in comb,"combat_has_turn":"turn" in comb,"combat_has_initiative":"initiative" in comb,
  "has_participants_registry":"participants" in rt,"has_active_participant":"active_participant" in rt or bool(rt.get("metadata",{}).get("active_player")),
  "has_action_owner":"action_owner" in rt,"has_actions_remaining":"actions_remaining" in rt,"has_out_of_combat_turn_model":"out_of_combat_action_state" in rt}

R["PHASE_A_TESTS_PASS"]=all([R["item_classify_ok"],R["item_enforcement_ok"],R["opening_stable"],R["roundtrip_ok"],R["restart_ok"],R["hidden_ok"]])
json.dump(R,open(ckpt+r"\06_phase_a_tests.json","w"),indent=2)
for k in ["item_classify","item_classify_ok","item_slot_violations","item_enforcement_ok","routed","opening_source","opening_stable","roundtrip_ok","restart_ok","hidden_ok","action_model","PHASE_A_TESTS_PASS"]:
    print(k,"=",json.dumps(R[k]) if not isinstance(R[k],(bool,str,int)) else R[k])
