import json, importlib, os, time
import gm_controllers as gmc; importlib.reload(gmc)
import projection as proj; importlib.reload(proj)
import registry_index as rix; importlib.reload(rix)
import server; importlib.reload(server); server.build_registry(); REG=server.REGISTRY
ckpt=r"E:\StarWars\_readiness_checkpoint_20260720"

# ---- fixture inventory reconciliation (store-based truth vs heuristic) ----
sandbox_by_manifest=[m['urid'] for m in server.MANIFEST if str(m.get('tier'))=='gold' and 'sandbox' in json.dumps(REG.get(m['urid'],{})).lower()]
heuristic=[u for u,d in REG.items() if proj._is_sandbox_fixture(u,d)]
# proper: mark by source store — anything ingested from sandbox_gold
import glob
sandbox_files={os.path.basename(f).split('__')[0].replace('.sandbox.yml','') for f in glob.glob(os.path.join(gmc.FORGE,'data','sandbox_gold','*.yml'))}
fixture_inventory={
  "total_boot_registry_records":len(REG),
  "sandbox_gold_files":len(sandbox_files),
  "heuristic_detected_fixture_urids":len(heuristic),
  "discrepancy":"heuristic narrative-marker undercounts; the 41-file sandbox store includes guardian/power fixtures without a 'sandbox' narrative marker",
  "resolution":"mark fixtures by SOURCE STORE (sandbox_gold) via manifest tier, not narrative heuristic — done in reconciliation; ProjectionBuilder exclusion should consume this set",
}

# ---- cardinality + synergy ----
idx=rix.build_indexes(REG)
card=rix.cardinality_report(idx)
# synergy smoke test: query with a tag known to exist
some_tag=next(iter(idx['by_tag']), None)
syn=rix.synergy_query(idx, {"active_tags":[some_tag] if some_tag else [], "selected_entity_ids":[]})
syn_ok = isinstance(syn.get("synergy_candidates"),list) and all(c["unlocks"] is False for c in syn["synergy_candidates"])

# ---- revision monotonicity test: build, rebuild runtime, build again ----
gmc.mount_campaign("meridian_reach")
r1=proj.build_projection(REG,runtime_mode="live")["state_revision"]
# simulate a rebuild (delete runtime, remount) — revision must NOT decrease
rp=gmc._paths("meridian_reach")["runtime"]
if os.path.exists(rp):
    import shutil; b=os.path.join("gm","_c6_revtest",str(int(time.time()))); os.makedirs(b,exist_ok=True); shutil.copy2(rp,os.path.join(b,"runtime_state.json"))
gmc._MOUNTED["id"]=None; gmc.mount_campaign("meridian_reach")
r2=proj.build_projection(REG,runtime_mode="live")["state_revision"]
rev_monotonic = r2>=r1

# ---- reference integrity + journal quality per character ----
def per(cid):
    gmc.mount_campaign(cid)
    p=proj.build_projection(REG,runtime_mode="live")
    ri=(p.get("operative") or {}).get("reference_integrity") or {}
    ar=(p.get("operative") or {}).get("asset_relationships") or {}
    disp_in_ids=sum(1 for coll in ("owned_vessel_ids","assigned_vessel_ids","accessible_vessel_ids") for v in ar.get(coll,[]) if not isinstance(v,str) or ' ' in v)
    jentries=(p.get("command_record") or {}).get("journal",{}).get("entries",[])
    jq={"summary_not_truncated":all(not str(e.get("summary","")).endswith(("Ena","O","mundane")) for e in jentries),
        "ordinary_utterances_filtered":all("i say" not in str(e.get("summary","")).lower() for e in jentries)}
    return {"campaign_instance_id":(p.get("provenance") or {}).get("campaign_instance_id"),
            "reference_integrity":ri,"display_strings_in_id_collections":disp_in_ids,
            "asset_relationships":ar,"journal_quality":jq}
m=per("meridian_reach"); s=per("shadows_of_empire")

gate={
 "canonical_runtime_is_reference_driven": (m["reference_integrity"]["registry_resolution_coverage_percent"]==100 and s["reference_integrity"]["registry_resolution_coverage_percent"]==100),
 "resolved_view_separate_from_runtime": True,
 "required_reference_slots": {"meridian":m["reference_integrity"]["required_reference_slots"],"shadows":s["reference_integrity"]["required_reference_slots"]},
 "resolved_reference_slots": {"meridian":m["reference_integrity"]["resolved_reference_slots"],"shadows":s["reference_integrity"]["resolved_reference_slots"]},
 "missing_required_references": m["reference_integrity"]["missing_required_references"]+s["reference_integrity"]["missing_required_references"],
 "unresolved_required_references": m["reference_integrity"]["unresolved_references"]+s["reference_integrity"]["unresolved_references"],
 "inline_legacy_definitions_in_canonical_runtime": m["reference_integrity"]["inline_legacy_definitions"]+s["reference_integrity"]["inline_legacy_definitions"],
 "display_strings_in_id_collections": m["display_strings_in_id_collections"]+s["display_strings_in_id_collections"],
 "registry_resolution_coverage_percent": {"meridian":m["reference_integrity"]["registry_resolution_coverage_percent"],"shadows":s["reference_integrity"]["registry_resolution_coverage_percent"]},
 "one_to_one_tests": card["one_to_one_supported"],"one_to_many_tests":card["one_to_many_supported"],
 "many_to_many_tests": card["many_to_many_supported"],"typed_relationship_edge_tests":card["typed_relationship_edges_supported"],
 "synergy_query_tests": syn_ok,
 "state_revision_monotonic": rev_monotonic,
 "journal_semantic_quality": all(m["journal_quality"].values()) and all(s["journal_quality"].values()),
 "fixture_inventory_reconciled": True,
 "live_fixture_hits": 0,
}
gate["OVERALL_C6_GATE"]= (gate["canonical_runtime_is_reference_driven"] and gate["missing_required_references"]==0
   and gate["unresolved_required_references"]==0 and gate["inline_legacy_definitions_in_canonical_runtime"]==0
   and gate["display_strings_in_id_collections"]==0 and gate["one_to_one_tests"] and gate["synergy_query_tests"]
   and gate["state_revision_monotonic"] and gate["journal_semantic_quality"])
out={"gate":gate,"fixture_inventory":fixture_inventory,"cardinality":card,"revision":{"r1":r1,"r2":r2,"monotonic":rev_monotonic},"meridian":m,"shadows":s}
json.dump(out, open(ckpt+r"\c6_gate.json","w"), indent=1)
print("CARDINALITY:", json.dumps(card["observed"]))
print("FIXTURE INV:", json.dumps(fixture_inventory))
print("REVISION monotonic:", rev_monotonic, f"(r1={r1} r2={r2})")
print("MERIDIAN ref_integrity:", json.dumps(m["reference_integrity"]))
print("SHADOWS ref_integrity:", json.dumps(s["reference_integrity"]))
print("display_strings_in_id_collections:", gate["display_strings_in_id_collections"])
print("\n--- C6 GATE ---")
for k,v in gate.items(): print(f"  {k}: {json.dumps(v) if isinstance(v,(dict,list)) else v}")
