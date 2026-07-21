import json, os, shutil, time, importlib
import gm_controllers as gmc; importlib.reload(gmc)
import projection as proj; importlib.reload(proj)
import server; importlib.reload(server); server.build_registry(); REG=server.REGISTRY
ckpt=r"E:\StarWars\_readiness_checkpoint_20260720"
# rebuild BOTH runtimes so the new identity taxonomy + structured equipment take effect
stamp=time.strftime("%Y%m%d_%H%M%S")
for cid in ("meridian_reach","shadows_of_empire"):
    rp=gmc._paths(cid)["runtime"]
    if os.path.exists(rp):
        bak=os.path.join("gm","_c5_rebuild_backup",f"{cid}_{stamp}"); os.makedirs(bak,exist_ok=True)
        shutil.move(rp, os.path.join(bak,"runtime_state.json"))
    gmc._MOUNTED["id"]=None; gmc.mount_campaign(cid)   # rebuilds fresh
GATE_KEYS=["projection_emitted","schema_valid","semantic_valid","malformed_equipment_entries",
  "identity_taxonomy_errors","duplicate_character_sources","unresolved_required_progression_refs",
  "live_fixture_hits","hidden_state_leaks","journal_is_structured","starship_taxonomy_valid"]
allpass=True
for cid in ("meridian_reach","shadows_of_empire"):
    gmc.mount_campaign(cid)
    p=proj.build_projection(REG, registry_build_id=f"reg_{len(REG)}", runtime_mode="live")
    json.dump(p, open(ckpt+f"\\projection_{cid}.c5.json","w"), indent=1, ensure_ascii=False)
    v=p.get("validation",{}); op=(p.get("operative") or {}).get("character_runtime") or {}; eq=op.get("equipment") or {}; idn=op.get("identity") or {}
    ff=(p.get("provenance") or {}).get("fixture_filter",{})
    g={"projection_emitted":p.get("projection_emitted"),"schema_valid":v.get("schema_valid"),"semantic_valid":v.get("semantic_valid"),
       "malformed_equipment_entries":v.get("malformed_equipment_entries"),
       "identity_taxonomy_errors":sum(1 for e in v.get("errors",[]) if e.startswith("identity:")),
       "duplicate_character_sources":v.get("duplicate_character_sources"),
       "unresolved_required_progression_refs":(p.get("provenance") or {}).get("unresolved_progression_refs"),
       "live_fixture_hits":ff.get("live_projection_fixture_hits"),
       "hidden_state_leaks":sum(1 for e in v.get("errors",[]) if e.startswith("hidden_state_leaks")),
       "journal_is_structured":(p.get("command_record") or {}).get("journal",{}).get("is_structured"),
       "starship_taxonomy_valid": all(it.get("item_type")!="Starship" for it in (eq.get("vehicles") or []))}
    ok=(g["projection_emitted"] and g["schema_valid"] and g["semantic_valid"] and g["malformed_equipment_entries"]==0
        and g["identity_taxonomy_errors"]==0 and g["duplicate_character_sources"]==0 and (g["unresolved_required_progression_refs"] or 0)==0
        and g["live_fixture_hits"]==0 and g["hidden_state_leaks"]==0 and g["journal_is_structured"] and g["starship_taxonomy_valid"])
    allpass=allpass and ok
    json.dump(g, open(ckpt+f"\\projection_gate_{cid}.json","w"), indent=1)
    print(f"\n== {cid} == GATE {'PASS' if ok else 'FAIL'}")
    for k in GATE_KEYS: print(f"   {k}: {g[k]}")
    print("   identity.class:", json.dumps(idn.get('class')), " identity.species:", json.dumps(idn.get('species')))
    print("   starships:", [i.get('name') for i in (eq.get('starships') or [])], " warnings:", v.get('warnings',[])[:3])
print("\nC5 PROJECTION GATE (both campaigns):", "PASS" if allpass else "FAIL")
