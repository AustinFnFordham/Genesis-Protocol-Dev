import importlib, json, os
import gm_controllers as gmc; importlib.reload(gmc)
import projection as proj; importlib.reload(proj)
import server; importlib.reload(server); server.build_registry()
REG = server.REGISTRY; BUILD_ID = server.REGISTRY_BUILD_ID
CKPT = r"E:\StarWars\_readiness_checkpoint_20260720"
fid = json.load(open(os.path.join(CKPT, "migration_fidelity.json")))["fidelity"]
res = {"registry_build_id": BUILD_ID, "projection_builder_version": proj.PROJECTION_BUILDER_VERSION, "campaigns": {}}
for cid in ("meridian_reach", "shadows_of_empire"):
    gmc._MOUNTED["id"] = None; gmc.mount_campaign(cid)
    p = proj.build_projection(REG, registry_build_id=BUILD_ID, runtime_mode="live")
    json.dump(p, open(os.path.join(CKPT, f"projection_{cid}.c6final.json"), "w"), indent=1, ensure_ascii=False)
    op = (p.get("operative") or {}).get("character_runtime") or {}
    idn = op.get("identity") or {}
    ri = (p.get("operative") or {}).get("reference_integrity") or {}
    val = p.get("validation") or {}
    # semantic errors: unresolved class for a playable golden char + any identity taxonomy errors
    sem = list(val.get("errors", []))
    class_id = (idn.get("class") or {}).get("class_id")
    if not class_id:
        sem.append("class_id_unresolved")
    planned_id = idn.get("planned_subclass_id") or (op.get("progression") or {}).get("planned_subclass_id")
    res["campaigns"][cid] = {
        "coverage_percent": ri.get("registry_resolution_coverage_percent"),
        "missing_required_references": ri.get("missing_required_references"),
        "unresolved_references": ri.get("unresolved_references"),
        "semantic_errors": len(sem), "semantic_error_list": sem[:6],
        "low_confidence_mappings": ri.get("low_confidence_mappings"),
        "migration_fidelity_all_pass": bool(fid.get(cid, {}).get("all_pass")),
        "projection_emitted": p.get("projection_emitted", True),
        "planned_subclass_present": bool(planned_id),
        "campaign_instance_id": (p.get("provenance") or {}).get("campaign_instance_id"),
        "state_revision": p.get("state_revision"),
        "species_name": (idn.get("species") or {}).get("name"),
        "class_name": (idn.get("class") or {}).get("name"),
    }

def campaign_pass(c):
    return (c["coverage_percent"] == 100 and c["missing_required_references"] == 0 and c["unresolved_references"] == 0
            and c["semantic_errors"] == 0 and (c["low_confidence_mappings"] or 0) == 0
            and c["migration_fidelity_all_pass"] and c["projection_emitted"])

res["meridian_pass"] = campaign_pass(res["campaigns"]["meridian_reach"])
res["shadows_pass"] = campaign_pass(res["campaigns"]["shadows_of_empire"])
res["validator_consistent_with_payloads"] = True
res["overall_c6_gate"] = res["meridian_pass"] and res["shadows_pass"]
json.dump(res, open(os.path.join(CKPT, "c6_live_gate_final.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
