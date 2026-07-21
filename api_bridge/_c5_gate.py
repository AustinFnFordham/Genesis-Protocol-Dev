import json, importlib
import gm_controllers as gmc; importlib.reload(gmc)
import projection as proj; importlib.reload(proj)
import server; importlib.reload(server); server.build_registry(); REG=server.REGISTRY
ckpt=r"E:\StarWars\_readiness_checkpoint_20260720"
def gate(cid):
    gmc.mount_campaign(cid)
    p=proj.build_projection(REG, registry_build_id=f"reg_{len(REG)}", runtime_mode="live")
    json.dump(p, open(ckpt+f"\\projection_{cid}.c5.json","w"), indent=1, ensure_ascii=False)
    v=p.get("validation",{})
    op=(p.get("operative") or {}).get("character_runtime") or {}
    eq=op.get("equipment") or {}
    idn=op.get("identity") or {}
    # count malformed equipment names
    mal=sum(1 for s in ("weapons","armor","gear","vehicles","starships") for it in (eq.get(s) or []) if str((it or {}).get("name","")).startswith("{") or "'item'" in str((it or {}).get("name","")))
    dfn=p.get("definitions") or {}
    dup=sum(1 for d in dfn.values() if isinstance(d,dict) and (d.get("ability_scores") or d.get("character_sheet")))
    ff=(p.get("provenance") or {}).get("fixture_filter",{})
    g={
      "projection_emitted": p.get("projection_emitted"),
      "schema_valid": v.get("schema_valid"),
      "semantic_valid": v.get("semantic_valid"),
      "malformed_equipment_entries": mal,
      "identity_taxonomy_errors": sum(1 for e in v.get("errors",[]) if e.startswith("identity:") and "unresolved" not in e),
      "duplicate_character_sources": dup,
      "unresolved_required_progression_refs": (p.get("provenance") or {}).get("unresolved_progression_refs"),
      "live_fixture_hits": ff.get("live_projection_fixture_hits"),
      "hidden_state_leaks": sum(1 for e in v.get("errors",[]) if e.startswith("hidden_state_leaks")),
      "journal_is_structured": (p.get("command_record") or {}).get("journal",{}).get("is_structured"),
      "starship_taxonomy_valid": (len((eq.get("vehicles") or []))==0 or all(it.get("item_type")!="Starship" for it in (eq.get("vehicles") or []))),
      "errors": v.get("errors",[]), "warnings": v.get("warnings",[])[:4],
      "identity_class": idn.get("class"), "identity_species": idn.get("species"),
      "gear_sample": [it.get("name") for it in (eq.get("gear") or [])][:3],
      "starships": [it.get("name") for it in (eq.get("starships") or [])],
      "vehicles": [it.get("name") for it in (eq.get("vehicles") or [])],
      "journal_count": len((p.get("command_record") or {}).get("journal",{}).get("entries",[])),
      "definitions_keys": list(dfn.keys())[:6],
      "fixture_filter": ff,
    }
    return g
for cid in ("meridian_reach","shadows_of_empire"):
    g=gate(cid); print(f"\n===== {cid} ====="); [print(f"  {k}: {json.dumps(v) if isinstance(v,(list,dict)) else v}") for k,v in g.items()]
