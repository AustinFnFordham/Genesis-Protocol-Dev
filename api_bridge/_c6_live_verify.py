import json, importlib, os
import gm_controllers as gmc; importlib.reload(gmc)
import projection as proj; importlib.reload(proj)
import server; importlib.reload(server)
server.build_registry()  # now loads golden_slice lane
REG = server.REGISTRY
CKPT = r"E:\StarWars\_readiness_checkpoint_20260720"
out = {"registry_build_id": server.REGISTRY_BUILD_ID, "registry_size": len(REG)}
for cid in ("meridian_reach", "shadows_of_empire"):
    gmc._MOUNTED["id"] = None; gmc.mount_campaign(cid)
    p = proj.build_projection(REG, registry_build_id=server.REGISTRY_BUILD_ID, runtime_mode="live")
    json.dump(p, open(os.path.join(CKPT, f"projection_{cid}.c6live.json"), "w"), indent=1, ensure_ascii=False)
    ri = (p.get("operative") or {}).get("reference_integrity") or {}
    op = (p.get("operative") or {}).get("character_runtime") or {}
    idn = op.get("identity") or {}
    # fidelity spot checks in the live projection
    stacks = (op.get("equipment") or {}).get("item_stacks") or []
    qmap = {s.get("name"): s.get("quantity") for s in stacks}
    out[cid] = {
        "coverage_percent": ri.get("registry_resolution_coverage_percent"),
        "missing_required_references": ri.get("missing_required_references"),
        "unresolved_references": ri.get("unresolved_references"),
        "opening_status": (p.get("campaign") or {}).get("opening_status"),
        "transcript_total": (p.get("active_engagement") or {}).get("transcript", {}).get("latest_sequence"),
        "species_name": (idn.get("species") or {}).get("name"),
        "class_name": (idn.get("class") or {}).get("name"),
        "planned_subclass_present": bool(idn.get("subclass") or op.get("progression", {}).get("class_id")),
        "state_revision": p.get("state_revision"),
    }
c = [out[k]["coverage_percent"] for k in ("meridian_reach", "shadows_of_empire")]
out["LIVE_C6_PASS"] = all((x or 0) >= 100 for x in c) and all(out[k]["missing_required_references"] == 0 for k in ("meridian_reach", "shadows_of_empire"))
json.dump(out, open(os.path.join(CKPT, "c6_live_gate.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
