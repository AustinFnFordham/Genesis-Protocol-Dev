import json, importlib
import gm_controllers as gmc; importlib.reload(gmc)
import projection as proj; importlib.reload(proj)
import server; importlib.reload(server)
server.build_registry()
REG=server.REGISTRY
ckpt=r"E:\StarWars\_readiness_checkpoint_20260720"
def summ(cid):
    gmc.mount_campaign(cid)
    p=proj.build_projection(REG, registry_build_id=f"reg_{len(REG)}", runtime_mode="live")
    json.dump(p, open(ckpt+f"\\projection_{cid}.json","w"), indent=1, ensure_ascii=False)
    op=p["operative"]["character_runtime"]
    eq=op.get("equipment",{})
    blob=json.dumps(p, ensure_ascii=False)
    return {
      "campaign_id":p["campaign_id"],"mount_epoch":p["mount_epoch"],"state_revision":p["state_revision"],
      "runtime_mode":p["runtime_mode"],"selected_character_id":p["selected_character_id"],
      "operative_name":(op.get("identity") or {}).get("name"),
      "equip_all_arrays":all(isinstance(eq.get(s),list) for s in ("weapons","armor","gear","vehicles")),
      "ship_present":bool(p["command_record"]["ship"]),
      "map_nodes":len(p["command_record"]["map"]["visible_nodes"]),
      "nemesis":len(p["command_record"]["player_visible_nemesis"]),
      "journal_entries":len(p["command_record"]["journal"]["entries"]),
      "transcript_total":p["active_engagement"]["transcript"]["latest_sequence"],
      "provenance":p["provenance"],
      "has_backslash_x":"\\x" in blob,
      "sandbox_in_blob":"sandbox" in blob.lower(),
      "party":p["party"]["participant_ids"],
    }
for cid in ("meridian_reach","shadows_of_empire"):
    s=summ(cid); print(f"\n=== {cid} ==="); [print(f"  {k}: {v}") for k,v in s.items()]
