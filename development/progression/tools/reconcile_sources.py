#!/usr/bin/env python3
"""CC-008.2 source reconciliation workbench (read-only).

Reads the quarantined SW5e_Data_Hub archive, the registry candidate builds and the golden-slice definitions, and writes
machine-readable reconciliation reports to development/progression/reconciliation/ for the Progression Forge.
Never writes to a source, a character sheet, campaign data or the registry. Every source it reads is recorded with its sha256.
Nothing produced here is canonical: every proposal is status "candidate" and carries an unsigned decision slot.

Run with an isolated interpreter:  python3 -I development/progression/tools/reconcile_sources.py
"""
import hashlib, json, os, re, sys, zipfile

import yaml

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
ZIP = os.path.join(REPO, "_QUARANTINE", "hub_root_debris", "SW5e_Data_Hub.zip")
OUT = os.environ.get("RECON_OUT") or os.path.join(REPO, "development", "progression", "reconciliation")
SCHEMA = "genesis-progression-reconciliation/0.1"
GENERATOR = "development/progression/tools/reconcile_sources.py"
GENESIS_ARCHETYPE_CADENCE = [3, 6, 9, 12, 15, 18]

sha = lambda b: hashlib.sha256(b).hexdigest()


class Sources:
    def __init__(self):
        with open(ZIP, "rb") as f:
            self.zip_sha = sha(f.read())
        self.z = zipfile.ZipFile(ZIP)
        self.read = {}

    def hub(self, member):
        b = self.z.read("SW5e_Data_Hub/" + member)
        self.read["hub:" + member] = {"path": "_QUARANTINE/hub_root_debris/SW5e_Data_Hub.zip!SW5e_Data_Hub/" + member, "sha256": sha(b)}
        return b

    def hub_yaml(self, member):
        return yaml.safe_load(self.hub(member))

    def has(self, member):
        try:
            self.z.getinfo("SW5e_Data_Hub/" + member)
            return True
        except KeyError:
            return False

    def repo(self, rel):
        with open(os.path.join(REPO, rel), "rb") as f:
            b = f.read()
        self.read["repo:" + rel] = {"path": rel, "sha256": sha(b)}
        return b

    def manifest(self):
        return {"archive": {"path": "_QUARANTINE/hub_root_debris/SW5e_Data_Hub.zip", "sha256": self.zip_sha},
                "files": sorted(self.read.values(), key=lambda x: x["path"])}


def header(src, kind, extra=None):
    h = {"schema": SCHEMA, "kind": kind, "generator": GENERATOR, "canonical": False, "status": "candidate",
         "note": "Reconciliation material for the Progression Forge. Nothing here is approved, promoted or executable."}
    h.update(extra or {})
    h["sources"] = src.manifest()
    return h


# ---------------------------------------------------------------- 1. Echani field-by-field
MECHANICAL_KEYS = {"ability_score_increases", "speed", "size", "base_hp", "base_strain", "languages", "innate_traits", "mechanics",
                   "effect", "rules", "value", "action_type", "species_progression", "mechanical_benefit", "starting_xp", "uses",
                   "recharge", "damage", "bonus", "proficiencies", "resistances", "senses", "level", "prerequisites", "cost"}


def keyed(lst):
    """Lists of dicts with ids/names are compared by identity, not position."""
    if isinstance(lst, list) and lst and all(isinstance(x, dict) for x in lst):
        for k in ("id", "name", "ability", "effect"):
            ks = [x.get(k) for x in lst]
            if all(v is not None for v in ks) and len(set(map(str, ks))) == len(ks):
                return k, {str(x[k]): x for x in lst}
    return None, None


def diff(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            p = path + [str(k)]
            if k not in b:
                out.append({"path": p, "status": "official_only", "official": a[k]})
            elif k not in a:
                out.append({"path": p, "status": "backend_only", "backend": b[k]})
            else:
                diff(a[k], b[k], p, out)
        return
    ka, ma = keyed(a)
    kb, mb = keyed(b)
    if ka and ka == kb:
        for k in sorted(set(ma) | set(mb)):
            p = path + ["[%s=%s]" % (ka, k)]
            if k not in mb:
                out.append({"path": p, "status": "official_only", "official": ma[k]})
            elif k not in ma:
                out.append({"path": p, "status": "backend_only", "backend": mb[k]})
            else:
                diff(ma[k], mb[k], p, out)
        return
    out.append({"path": path, "status": "same" if a == b else "differs", "official": a, "backend": b} if a != b else {"path": path, "status": "same"})


NARRATIVE_KEYS = {"narrative_progression", "narrative", "flavor_text", "description", "llm_guidance"}


def is_mechanical(path):
    if any(seg in NARRATIVE_KEYS for seg in path):
        return False
    return any(re.sub(r"^\[.*$", "", seg) in MECHANICAL_KEYS or seg.startswith("level_") for seg in path)


def echani(src):
    off_m, back_m = "official_species_playable/echani.yml", "backend/species/echani.yml"
    off, back = src.hub_yaml(off_m), src.hub_yaml(back_m)
    sheet = src.repo("api_bridge/gm/aero_character_runtime.yml").decode("utf8", "replace")
    cited = {"official": off_m in sheet or "official_species_playable" in sheet, "backend": back_m in sheet}
    rows = []
    diff(off, back, [], rows)
    fields = []
    for r in rows:
        if r["status"] == "same":
            continue
        mech = is_mechanical(r["path"])
        disp = {"official_only": "baseline_keeps", "backend_only": "retain_for_review", "differs": "baseline_preferred_backend_retained"}[r["status"]]
        r.update({"field": ".".join(r["path"]), "mechanical": mech, "proposed_disposition": disp, "decision": None})
        if r["path"][-1] == "corruption_transform":
            r["note"] = "backend-only dark-side corruption hook (trait swaps to %s); a mechanic the official baseline lacks" % (r["backend"] or {}).get("corrupts_to_feature_id")
        if r["path"] == ["rarity"]:
            r["note"] = "conflicts with the official copy's 'uncommon' tag" if "uncommon" in (off.get("tags") or []) else None
        fields.append(r)
    same = sum(1 for r in rows if r["status"] == "same")
    count = lambda st, mech=None: sum(1 for f in fields if f["status"] == st and (mech is None or f["mechanical"] == mech))
    return header(src, "echani_species_copy_comparison", {
        "baseline": {"copy": "official", "member": off_m, "reason": "cited by Aero's sheet (api_bridge/gm/aero_character_runtime.yml)", "promoted": False},
        "copies": {"official": {"member": off_m, "sha256": src.read["hub:" + off_m]["sha256"], "cited_by_sheet": cited["official"]},
                   "backend": {"member": back_m, "sha256": src.read["hub:" + back_m]["sha256"], "cited_by_sheet": cited["backend"]}},
        "dispositions": {"baseline_keeps": "present only in the official copy; kept in the baseline",
                         "retain_for_review": "present only in the backend copy; NOT discarded — kept for an owner/Forge decision",
                         "baseline_preferred_backend_retained": "values differ; official value is the proposed baseline, backend value preserved verbatim"},
        "summary": {"identical_leaves": same, "differing_fields": len(fields),
                    "differs": count("differs"), "official_only": count("official_only"), "backend_only": count("backend_only"),
                    "mechanical_values_identical_where_both_define": count("differs", True) == 0,
                    "mechanical": {"differs": count("differs", True), "official_only": count("official_only", True), "backend_only": count("backend_only", True)}},
        "fields": fields})


# ---------------------------------------------------------------- 2. Sentinel L3 / L7 candidate repairs
def sentinel(src):
    audit = json.loads(src.repo("development/progression/legacy/legacy_prereq_audit.json"))
    cand_rel = "registry/candidate_builds/cand_classes_861acd817b14421e/validated_candidate/sentinel.json"
    cand = json.loads(src.repo(cand_rel))["record"]
    hub = src.hub_yaml("backend/classes/sentinel.yml")
    trees = {"candidate_build": cand["progression_tree"], "hub_archive": hub["progression_tree"]}
    repairs = []
    for rec in audit["records"]:
        if rec["id"] != "sentinel":
            continue
        tree = trees[rec["family"]]
        for q in rec["reinterpreted"]:
            node = next(n for n in tree if n["node_id"] == q["node"])
            group = q["groups"][0]
            members = sorted(n["node_id"] for n in tree if n.get("choice_group") == group)
            repairs.append({
                "id": "repair:sentinel:%s:%s" % (rec["family"], q["node"]), "family": rec["family"], "source": rec["source"], "source_sha256": rec["source_sha256"],
                "node": q["node"], "level": int(node["level_requirement"]),
                "original_prerequisites": node.get("prerequisites"), "original_record": node,
                "group": group, "group_members": members, "group_is_exclusive_choice": all(n.get("type") == "choice" for n in tree if n.get("choice_group") == group),
                "proposed_requires": {"all": [{"any_of_group": group}]},
                "evidence": ["the listed prerequisites are exactly the full membership of choice group '%s'" % group,
                             "the group is a pick-one choice, so a literal ALL can never be satisfied",
                             "SW5e PHB Sentinel table gates Calling features on level only (3rd Sentinel Calling, 7th Calling feature)"],
                "status": "candidate",
                "legacy_validation": {"by": None, "on": None, "decision": None},   # unsigned: the framework treats this node as unvalidated
            })
    others = sorted({r["family"] + ":" + r["id"] for r in audit["records"] if r["reinterpreted"] and r["id"] != "sentinel"})
    return header(src, "sentinel_exclusive_choice_repairs", {
        "scope": "Sentinel levels 3 and 7 only", "repairs": repairs,
        "not_in_scope": {"reinterpreted_trees_not_repaired": others, "count": len(others),
                         "note": "Left exactly as the CC-008.1 audit reports them; no approval implied."}})


# ---------------------------------------------------------------- 3. Scoundrel evasion_7 trace
def scoundrel(src):
    hub = src.hub_yaml("backend/classes/scoundrel.yml")
    cand_rel = "registry/candidate_builds/cand_classes_861acd817b14421e/validated_candidate/scoundrel.json"
    cand = json.loads(src.repo(cand_rel))["record"]
    looked = []
    def scan_tree(label, tree):
        ids = [n.get("node_id") for n in tree]
        looked.append({"source": label, "defines_evasion_7": "evasion_7" in ids,
                       "evasion_like_nodes": [i for i in ids if i and "evasion" in i.lower()],
                       "level_7_nodes": [n.get("node_id") for n in tree if str(n.get("level_requirement")) == "7"]})
    scan_tree("hub:backend/classes/scoundrel.yml", hub["progression_tree"])
    scan_tree("repo:" + cand_rel, cand["progression_tree"])
    subs = sorted(n[len("SW5e_Data_Hub/"):] for n in src.z.namelist() if re.match(r"SW5e_Data_Hub/backend/subclasses/(scoundrel_subclasses|smuggler_subclasses)/.*scoundrel.*\.yml$|SW5e_Data_Hub/backend/subclasses/scoundrel_subclasses/.*\.yml$", n))
    for m in subs:
        d = src.hub_yaml(m) or {}
        scan_tree("hub:" + m, d.get("progression_tree") or [])
    for c in ("smuggler", "spy"):
        d = src.hub_yaml("backend/classes/%s.yml" % c)
        scan_tree("hub:backend/classes/%s.yml (sibling class)" % c, d["progression_tree"])
    fr = json.loads(src.hub("backend/feature_registry.json"))
    fr_ev = [f for f in fr if "evasion" in (str(f.get("id")) + str(f.get("name"))).lower()]
    fr_ref = [{"id": f.get("id"), "source_id": f.get("source_id"), "level": f.get("level")} for f in fr if "evasion_7" in (f.get("prerequisites") or [])]
    looked.append({"source": "hub:backend/feature_registry.json", "defines_evasion_feature": bool(fr_ev), "evasion_features": [{"id": f.get("id"), "source_id": f.get("source_id")} for f in fr_ev],
                   "references_to_evasion_7": fr_ref})
    ev = src.hub_yaml("backend/features/smuggler/evasion_expertise.yml")
    looked.append({"source": "hub:backend/features/smuggler/evasion_expertise.yml", "id": ev.get("id"), "mechanics": ev.get("mechanics"),
                   "relevance": "a Smuggler feature named Evasion Expertise; placeholder grant_ability mechanics; not a Scoundrel level-7 feature"})
    phb = src.hub("backend/clean_source/SW5e_PHB.txt").decode("utf8", "replace")
    op = re.search(r"5th \+3 Uncanny Dodge.{0,40}?7th \+3 Evasion.{0,40}?8th \+3 Ability Score Improvement", phb)
    ev_txt = re.search(r"EVASION\nWhen you are subjected to an e.{0,4}ect that allows you to make a Dexterity saving throw to take only half damage, you instead take no damage.{0,160}", phb, re.S)
    gs = src.repo("registry/golden_slice/global_definitions/class_operative.yml").decode()
    gs7 = re.search(r"level_7: \{[^}]*\}", gs)
    l7 = next(n for n in hub["progression_tree"] if n["node_id"] == "uncanny_dodge_7")
    return header(src, "scoundrel_dangling_prerequisite_trace", {
        "finding": {"node": "ability_score_improvement_8", "dangling_prerequisite": "evasion_7",
                    "verdict": "genuine source gap: no available Scoundrel class or subclass source defines evasion_7 or any Evasion node",
                    "searched": looked},
        "external_evidence": [
            {"source": "hub:backend/clean_source/SW5e_PHB.txt (Operative table)", "excerpt": op.group(0) if op else None,
             "reading": "SW5e's rogue-analogue Operative has Uncanny Dodge at 5, Evasion at 7, ASI at 8 — the pattern the Scoundrel tree appears to copy"},
            {"source": "hub:backend/clean_source/SW5e_PHB.txt (Evasion text)", "excerpt": re.sub(r"\s+", " ", ev_txt.group(0))[:400] if ev_txt else None},
            {"source": "repo:registry/golden_slice/global_definitions/class_operative.yml", "excerpt": gs7.group(0) if gs7 else None},
            {"source": "Scoundrel tree itself", "excerpt": {"uncanny_dodge_7": {k: l7.get(k) for k in ("level_requirement", "type", "prerequisites")}},
             "reading": "Scoundrel moved Uncanny Dodge to 7, so the slot the Operative pattern gives to Evasion is occupied"}],
        "alternatives": [
            {"id": "A_point_at_level_7_node", "proposed_requires": {"all": ["uncanny_dodge_7"]},
             "evidence": "every other Scoundrel core node requires the node at the previous level; uncanny_dodge_7 is the only level-7 node",
             "consequence": "no new content; restores the chain. Evasion is simply absent from Scoundrel", "status": "candidate"},
            {"id": "B_add_evasion_7_node", "proposed_node": {"node_id": "evasion_7", "level_requirement": 7, "type": "core", "prerequisites": ["enhanced_stealth_6", "enhanced_deception_6"],
                                                             "mechanics": None, "placeholder": True},
             "evidence": "the prerequisite names it; SW5e Operative grants Evasion at 7",
             "consequence": "adds a second level-7 core feature (Scoundrel has no source text for it); inherits the same L6 exclusive-choice ambiguity; Evasion mechanics must be authored and implemented before it can execute",
             "status": "candidate"},
            {"id": "C_leave_unrepaired", "consequence": "tree stays invalid (validator rejects it); Scoundrel unusable until decided", "status": "current"}],
        "decision": None})


# ---------------------------------------------------------------- 4. Sentry packet
DESC_KEYWORDS = {"ability_modification": ["bonus", "advantage", "+"], "ability_trigger": ["reaction", "when"]}


def as_list(v):
    if isinstance(v, str):
        try:
            return yaml.safe_load(v.replace("'", '"'))
        except Exception:
            return v
    return v


def sentry(src):
    m = "backend/subclasses/sentinel_subclasses/sentinel_sentry.yml"
    d = src.hub_yaml(m)
    feats = []
    for fid in d.get("specialization_features") or []:
        fm = "backend/features/sentinel/sentry/%s.yml" % fid
        if not src.has(fm):
            feats.append({"id": fid, "file": None, "defined": False})
            continue
        f = src.hub_yaml(fm)
        mech = f.get("mechanics") or []
        placeholder = not mech or all(x.get("effect") == "grant_ability" and "special ability" in str(x.get("description", "")).lower() for x in mech)
        feats.append({"id": fid, "file": fm, "defined": True, "name": f.get("name"), "level": f.get("level"), "xp_cost": f.get("xp_cost"),
                      "mechanics": mech, "placeholder": placeholder, "has_level": f.get("level") is not None})
    nodes = []
    spec_names = {(x.get("name") or "").lower() for x in feats} | {x["id"] for x in feats}
    for n in d.get("progression_tree") or []:
        eff = as_list(n.get("effects"))
        issues = []
        desc = (n.get("description") or "").lower()
        for e in (eff if isinstance(eff, list) else []):
            v = str(e.get("value", "")).lower()
            if e.get("type") == "ability_modification" and "advantage" in desc and "advantage" not in v:
                issues.append({"code": "EFFECT_CONTRADICTS_DESCRIPTION", "detail": "description grants advantage; effect is a numeric modification '%s'" % e.get("value")})
            if e.get("type") == "ability_trigger" and "when you take damage" in v and "friendly" in desc:
                issues.append({"code": "EFFECT_CONTRADICTS_DESCRIPTION", "detail": "description protects an ally; trigger is 'when you take damage'"})
            if e.get("type") == "ability_trigger" and "when you take damage" in v and "barrier" in desc:
                issues.append({"code": "TRIGGER_UNSPECIFIED_FOR_DESCRIBED_EFFECT", "detail": "trigger copied verbatim from Guardianship; barrier needs its own trigger, size and duration"})
        if not isinstance(eff, list):
            issues.append({"code": "EFFECTS_UNPARSEABLE", "raw": n.get("effects")})
        issues.append({"code": "NO_STRUCTURED_MECHANICS", "detail": "no target, range, duration, uses or resource; not executable as written"})
        if (n.get("feature_id") or "").lower() not in spec_names:
            issues.append({"code": "NOT_IN_SPECIALIZATION_FEATURES"})
        nodes.append({"node_id": n.get("node_id"), "feature_id": n.get("feature_id"), "level": int(n.get("level_requirement")), "type": n.get("type"),
                      "description": n.get("description"), "effects": eff, "issues": issues})
    tree_ids = {(x["feature_id"] or "").lower() for x in nodes}
    for f in feats:
        f["issues"] = ([{"code": "PLACEHOLDER_MECHANICS", "detail": "grant_ability 'Grants a special ability'"}] if f.get("placeholder") else []) + \
                      ([{"code": "NO_LEVEL"}] if not f.get("has_level") else []) + \
                      ([{"code": "NOT_IN_PROGRESSION_TREE"}] if (f.get("name") or "").lower() not in tree_ids and f["id"] not in tree_ids else [])
    cls = json.loads(src.repo("registry/candidate_builds/cand_classes_861acd817b14421e/validated_candidate/sentinel.json"))["record"]["progression_tree"]
    phb = src.hub("backend/clean_source/SW5e_PHB.txt").decode("utf8", "replace")
    tbl = phb[phb.find("THE SENTINEL\nPro"):phb.find("CLASS FEATURES", phb.find("THE SENTINEL\nPro"))]
    phb_lv = sorted({3} | {int(x) for x in re.findall(r"(\d+)(?:st|nd|rd|th) \+\d Calling feature", tbl)})
    tree_lv = sorted(x["level"] for x in nodes)
    class_lv = sorted({int(n["level_requirement"]) for n in cls if n["node_id"].startswith(("subclass_feature_", "sentinel_specialization_"))})
    allv = sorted(set(tree_lv) | set(phb_lv) | set(class_lv) | set(GENESIS_ARCHETYPE_CADENCE))
    gs = src.repo("registry/golden_slice/global_definitions/subclass_sentry.yml").decode()
    return header(src, "sentry_reconciliation_packet", {
        "subclass": {"member": m, "id": d.get("id"), "class": d.get("class_id"), "registry": {"urid": "subclass_sentry", "golden_slice_tags": re.findall(r"- (\w+)", gs.split("tags:")[1].split("prerequisites")[0]),
                     "golden_slice_source_path": re.search(r"source_path: (.*)", gs).group(1), "note": "golden slice cites a forge_v3 path that is not in the archive; its 'mechanical_match: true' is not evidence of mechanics"}},
        "specialization_features": feats, "progression_tree": nodes,
        "cross_reference": {"specialization_features_without_tree_node": [f["id"] for f in feats if any(i["code"] == "NOT_IN_PROGRESSION_TREE" for i in f["issues"])],
                            "tree_nodes_without_feature_file": [x["node_id"] for x in nodes if any(i["code"] == "NOT_IN_SPECIALIZATION_FEATURES" for i in x["issues"])],
                            "overlap": sorted(tree_ids & spec_names)},
        "missing_mechanical_definitions": [x["node_id"] for x in nodes] + [f["id"] for f in feats if f.get("placeholder") or not f.get("defined")],
        "cadence": {"levels": allv, "rows": [{"level": L, "sentry_progression_tree": L in tree_lv, "sentinel_class_subclass_slot": L in class_lv,
                                               "sw5e_phb_calling_feature": L in phb_lv, "genesis_archetype_cadence": L in GENESIS_ARCHETYPE_CADENCE} for L in allv],
                    "sentry_progression_tree": tree_lv, "sentinel_class_subclass_slots": class_lv, "sw5e_phb_calling_features": phb_lv, "genesis_archetype_cadence": GENESIS_ARCHETYPE_CADENCE,
                    "aligned_with_genesis": sorted(set(tree_lv) & set(GENESIS_ARCHETYPE_CADENCE)),
                    "source_levels_off_genesis_cadence": sorted(set(tree_lv) - set(GENESIS_ARCHETYPE_CADENCE)),
                    "genesis_milestones_without_source_feature": sorted(set(GENESIS_ARCHETYPE_CADENCE) - set(tree_lv))},
        "design_session_inputs": {"chooses_final_abilities": False, "note": "Forge design session decides abilities; this packet only lists the evidence and gaps."}})


def main():
    os.makedirs(OUT, exist_ok=True)
    reports = {}
    for name, fn in (("echani_copy_comparison", echani), ("sentinel_prereq_repairs", sentinel), ("scoundrel_evasion_trace", scoundrel), ("sentry_reconciliation", sentry)):
        src = Sources()
        rep = fn(src)
        path = os.path.join(OUT, name + ".json")
        with open(path, "w", encoding="utf8") as f:
            json.dump(rep, f, indent=1, ensure_ascii=False, sort_keys=False, default=str)
            f.write("\n")
        reports[name] = rep
        print(name, json.dumps(rep.get("summary") or rep.get("finding", {}).get("verdict") or len(rep.get("repairs", rep.get("progression_tree", []))))[:200])
    return reports


if __name__ == "__main__":
    main()
