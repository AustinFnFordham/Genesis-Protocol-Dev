import importlib, json
import gm_controllers as gmc; importlib.reload(gmc)
import projection as proj; importlib.reload(proj)
import server; importlib.reload(server); server.build_registry(); REG = server.REGISTRY
for cid in ("meridian_reach", "shadows_of_empire"):
    gmc._MOUNTED["id"] = None; gmc.mount_campaign(cid)
    vis = gmc.player_visible_state(); pid = vis["metadata"]["active_player"]; sh = (vis.get("player_characters") or {}).get(pid) or {}
    idn = sh.get("identity") or {}; eq = sh.get("equipment") or {}
    print(f"\n=== {cid} ===")
    for k in ("species_id", "class_id", "background_id", "planned_subclass_id", "subclass_id"):
        v = idn.get(k)
        if v is not None:
            print(f"  identity.{k}={v}  in_reg={v in REG}")
    for f in (sh.get("features") or []):
        u = f.get("urid")
        if u and u not in REG: print(f"  FEATURE UNRESOLVED urid={u} name={f.get('name')}")
    for p in (sh.get("powers") or []):
        u = p.get("urid")
        if u and u not in REG: print(f"  POWER UNRESOLVED urid={u} name={p.get('name')}")
    for slot in ("weapons", "armor", "gear"):
        for it in (eq.get(slot) or []):
            key = it.get("item_id") or it.get("instance_id")
            if key and key not in REG: print(f"  ITEM UNRESOLVED [{slot}] key={key} name={it.get('name')}")
