import json, importlib, os
import gm_controllers as gmc; importlib.reload(gmc)
import projection as proj; importlib.reload(proj)
import server; importlib.reload(server); server.build_registry(); REG = server.REGISTRY
gmc._MOUNTED["id"] = None; gmc.mount_campaign("meridian_reach")
vis = gmc.player_visible_state(); sh = (vis.get("player_characters") or {}).get(vis["metadata"]["active_player"])
eq = sh.get("equipment") or {}
print("=== Meridian item ids in normalized equipment vs registry ===")
for slot in ("weapons", "armor", "gear"):
    for it in (eq.get(slot) or []):
        iid = it.get("item_id"); inst = it.get("instance_id")
        key = iid or inst
        present = key in REG if key else False
        if not present:
            print(f"  UNRESOLVED [{slot}] name={it.get('name')!r} item_id={iid} instance_id={inst}")
# what item_* urids DOES the lane have?
lane_items = sorted([u for u in REG if u.startswith("item_")])
print("\nlane item_* urids:", lane_items)
inst_urids = sorted([u for u in REG if u.startswith("iteminst")])
print("lane iteminst urids:", inst_urids)
# identity + measure detail
ri = None
p = proj.build_projection(REG, runtime_mode="live")
ri = (p.get("operative") or {}).get("reference_integrity") or {}
print("\nreference_integrity:", json.dumps(ri))
print("missing_domains:", ri.get("missing_domains"))
