import glob, os, yaml
LANE = r"E:\StarWars\registry\golden_slice"
CAMPAIGN_LOCAL_FEATURES = {"feature_operator_archetype", "feature_smuggler_s_cunning", "feature_daring_pilot"}
# Aran campaign_local source (for provenance)
ARAN = glob.glob(r"E:\StarWars\SW5e_Data_Hub\forge_v3\data\campaign_local\Character__char_smuggler*.yml")
aran_src = os.path.relpath(ARAN[0], r"E:\StarWars") if ARAN else None
for f in glob.glob(os.path.join(LANE, "**", "*.yml"), recursive=True):
    if os.sep + "migration" + os.sep in f:
        continue
    try:
        d = yaml.safe_load(open(f, encoding="utf-8"))
    except Exception:
        continue
    if not isinstance(d, dict) or not d.get("urid"):
        continue
    u = d["urid"]; changed = False
    if u == "species_human" and d.get("name") != "Human":
        d["name"] = "Human"; changed = True                          # canonical display, URID retained
    if u == "class_operator":
        os.remove(f); print("removed false class_operator lane record"); continue
    if u in CAMPAIGN_LOCAL_FEATURES:
        d["authority_lane"] = "campaign_local"; d["resolution_status"] = "campaign_local_adaptation"
        d["validation_status"] = "provisional"; d["campaign_scope"] = "shadows_of_empire"
        d["provenance"] = {**(d.get("provenance") or {}), "source": aran_src, "note": "player-defined archetype feature; not a global definition"}
        changed = True
    if changed:
        yaml.safe_dump(d, open(f, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
        print("fixed lane record:", u)
print("lane fix done")
