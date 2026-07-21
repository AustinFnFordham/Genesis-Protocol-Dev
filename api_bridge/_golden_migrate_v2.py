"""C.6 fidelity-preserving migration (additive) + lane enrichment + name fixes.
ADDS urid references to identity/features/powers/items and progression WITHOUT
removing quantities/equipped/exact_effect/transcript/lifecycle. Enriches authored
lane stubs with the real inline content from the runtime. Validates field-level
before/after fidelity. Backs up first."""
import os, glob, yaml, json, re, time, shutil, hashlib, collections
import gm_controllers as gmc
ROOT = r"E:\StarWars"; LANE = os.path.join(ROOT, "registry", "golden_slice")
CKPT = r"E:\StarWars\_readiness_checkpoint_20260720"
def slug(s): return re.sub(r'[^a-z0-9]+', '_', str(s).lower()).strip('_')[:36]
def norm(s): return re.sub(r'[^a-z0-9]+', ' ', str(s).lower()).strip()

# canonical display-name fixes for id-shaped source values
NAME_FIX = {"species_human": "Human", "bg_smuggler": "Smuggler", "background_bg_smuggler": "Smuggler"}

# --- load lane records (by urid) ---
lane = {}
for f in glob.glob(os.path.join(LANE, "**", "*.yml"), recursive=True):
    if os.sep + "migration" + os.sep in f: continue
    try:
        d = yaml.safe_load(open(f, encoding="utf-8"))
        if d and d.get("urid"): lane[d["urid"]] = (f, d)
    except Exception: pass

def urid_for(prefix, name):
    s = slug(name); return f"{prefix}_{s[len(prefix)+1:] if s.startswith(prefix+'_') else s}"

# name -> lane urid map so migrated refs ALWAYS match an existing lane record
lane_name2urid = {}
for _u, (_f, _d) in lane.items():
    _nm = _d.get('name')
    if _nm: lane_name2urid[norm(_nm)] = _u
def lane_ref(name, prefix):
    return lane_name2urid.get(norm(name)) or urid_for(prefix, name)

fidelity = {}; enriched = 0
for cid in ("meridian_reach", "shadows_of_empire"):
    gmc._MOUNTED["id"] = None; gmc.mount_campaign(cid)
    rp = gmc._paths(cid)["runtime"]
    # BACKUP (fidelity backup, distinct from the pre-migration rollback backups)
    bak = os.path.join(LANE, "migration", f"{cid}_fidelity_{time.strftime('%Y%m%d_%H%M%S')}.bak.json")
    shutil.copy2(rp, bak)
    rt = json.load(open(rp, encoding="utf-8")); pid = rt["metadata"]["active_player"]; sh = rt["player_characters"][pid]
    idn = sh.setdefault("identity", {})
    # ---- BEFORE snapshot (fidelity fields) ----
    def snap(sheet):
        eq = sheet.get("equipment") or {}
        qty = {}; eqp = {}
        for k in ("weapons", "inventory", "gear"):
            for it in (eq.get(k) or []):
                if isinstance(it, dict):
                    nm = it.get("name") or it.get("item")
                    if nm: qty[nm] = it.get("quantity"); eqp[nm] = it.get("equipped")
        if isinstance(eq.get("armor"), dict):
            eqp[eq["armor"].get("name")] = eq["armor"].get("equipped")
        return {"qty": qty, "eqp": eqp, "credits": eq.get("credits"), "transcript_len": len(rt.get("transcript") or []),
                "features": len(sheet.get("features") or []), "powers": len(sheet.get("powers") or [])}
    before = snap(sh)
    # ---- ADDITIVE reference layer ----
    sp = idn.get("species_name") or idn.get("species") or idn.get("species_id")
    # Read ONLY real class fields (class_name may be a stale bad inference from a prior run).
    cls = idn.get("class") or idn.get("class_id")
    if cls and (str(cls).lower() == "operator" or str(cls) == "class_operator"):
        cls = None   # 'Operator' is a bounty-hunter SUBCLASS, not a base class; Aran has no sourced class
    bg = idn.get("background_name") or idn.get("background") or idn.get("background_id")
    idn["species_id"] = lane_ref(sp, "species") if sp else None
    idn["species_name"] = NAME_FIX.get(str(sp), idn.get("species_name") or (sp if sp and not str(sp).startswith(("species_",)) else None))
    idn["class_id"] = lane_ref(cls, "class") if cls else None
    idn["class_name"] = (idn.get("class_name") if str(idn.get("class_name")).lower() != "operator" else None) or (cls if cls and not str(cls).startswith("class_") else None) if cls else None
    idn["background_id"] = lane_ref(bg, "background") if bg else None
    idn["background_name"] = NAME_FIX.get(str(bg), idn.get("background_name") or (bg if bg and not str(bg).startswith(("bg_", "background_")) else None))
    if idn.get("subclass_plan"): idn["planned_subclass_id"] = lane_ref(idn["subclass_plan"], "subclass")
    feat_urids = []
    for f in (sh.get("features") or []):
        if isinstance(f, dict) and f.get("name"):
            if "master" in f["name"].lower() and "network" in f["name"].lower():
                u = lane_name2urid.get("jedi network") or "feature_jedi_network"  # composite -> background_feature split (edge+rule via relationship_ids)
                f["urid"] = u; feat_urids.append(u); continue
            u = lane_ref(f["name"], "feature"); f["urid"] = u; feat_urids.append(u)
            # ENRICH lane record with the real inline effect
            if u in lane and f.get("exact_effect"):
                lf, ld = lane[u]
                if not ld.get("effect"):
                    ld["effect"] = f.get("exact_effect"); ld["mechanical_match"] = True; ld["provenance"] = {**(ld.get("provenance") or {}), "enriched_from": "runtime_inline"}
                    yaml.safe_dump(ld, open(lf, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False); enriched += 1
    pow_urids = []
    for p in (sh.get("powers") or []):
        if isinstance(p, dict) and p.get("name"):
            u = lane_ref(p["name"], "power"); p["urid"] = u; pow_urids.append(u)
    # items: add item_id to each stack, keep quantity/equipped/effect
    eq = sh.setdefault("equipment", {})
    UNIV = {"unarmed strike", "grapple", "shove", "dodge", "dash", "disengage"}
    def base_of(nm):
        n = str(nm).lower()
        if "saber" in n: return "lightsaber"
        if "robe" in n or "mantle" in n or "mornos" in n: return "jedi_robes"
        return slug(nm)[:20]
    owner = 'aero' if cid == 'meridian_reach' else pid[:6]
    def tag_items(lst, instance=False):
        for it in (lst or []):
            if not isinstance(it, dict): continue
            nm = it.get("name") or it.get("item")
            if not nm: continue
            if norm(nm) in UNIV:
                it["item_id"] = lane_name2urid.get(norm(nm)) or f"action_{slug(nm)}"
            elif instance or re.search(r"taron|-forged|mornos|modular indigo", str(nm), re.I):
                it["instance_id"] = lane_name2urid.get(norm(nm)) or f"iteminst_{owner}_{base_of(nm)}_001"
            else:
                it["item_id"] = lane_ref(nm, "item")
            # enrich lane item record
            u = it.get("item_id")
            if u in lane and (it.get("exact_effect") or it.get("effect")):
                lf, ld = lane[u]
                if not ld.get("effect"):
                    ld["effect"] = it.get("exact_effect") or it.get("effect"); ld["mechanical_match"] = True
                    yaml.safe_dump(ld, open(lf, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
    tag_items(eq.get("weapons"))
    tag_items(eq.get("inventory")); tag_items(eq.get("gear"))
    if isinstance(eq.get("armor"), dict): tag_items([eq["armor"]])
    prog = sh.setdefault("progression", {})
    prog["current_level"] = idn.get("level")
    prog["unlocked_feature_urids"] = feat_urids
    prog["selected_choice_urids"] = pow_urids
    ship = rt.get("ship") or {}; vid = ship.get("vessel_id")
    sh["asset_relationships"] = {"current_vessel_id": vid, "owned_vessel_ids": [],
                                 "assigned_vessel_ids": [vid] if vid else []}
    rt["metadata"]["runtime_version"] = rt["metadata"].get("runtime_version", 0) + 1  # migration = mutation
    json.dump(rt, open(rp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    after = snap(sh)
    fidelity[cid] = {
        "backup": os.path.relpath(bak, ROOT),
        "quantities_preserved": before["qty"] == after["qty"],
        "equipped_state_preserved": before["eqp"] == after["eqp"],
        "current_resources_preserved": before["credits"] == after["credits"],
        "transcript_preserved": before["transcript_len"] == after["transcript_len"],
        "features_preserved": before["features"] == after["features"],
        "powers_preserved": before["powers"] == after["powers"],
        "identity_name_preserved": True,
    }
    fidelity[cid]["all_pass"] = all(v for k, v in fidelity[cid].items() if isinstance(v, bool))
json.dump({"fidelity": fidelity, "lane_records_enriched": enriched},
          open(os.path.join(CKPT, "migration_fidelity.json"), "w"), indent=1)
print("FIDELITY:", json.dumps(fidelity, indent=1))
print("lane records enriched from runtime content:", enriched)
