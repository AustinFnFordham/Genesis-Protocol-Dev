
import os
import yaml
import json
import re
from pathlib import Path
from jsonschema import validate, ValidationError

# --- CONFIGURATION ---
DATA_DIR = Path("SW5e_Data_Hub/data")
FACTIONS_DIR = DATA_DIR / "factions"
EXPANSIONS_DIR = DATA_DIR / "faction_expansions"
SCHEMAS_DIR = DATA_DIR / "schemas"
CORE_SCHEMA_PATH = SCHEMAS_DIR / "faction_core.schema.json"
EXPANSION_SCHEMA_PATH = SCHEMAS_DIR / "faction_expansion.schema.json"
TAGS_PATH = DATA_DIR / "tags/master_tags.yml"

# Ensure directories exist
EXPANSIONS_DIR.mkdir(parents=True, exist_ok=True)

# LOAD SCHEMAS & TAGS
with open(CORE_SCHEMA_PATH, "r", encoding="utf-8") as f:
    CORE_SCHEMA = json.load(f)
with open(EXPANSION_SCHEMA_PATH, "r", encoding="utf-8") as f:
    EXPANSION_SCHEMA = json.load(f)

# Get allowed tags from Core Schema Enum
ALLOWED_TAGS = set(CORE_SCHEMA["properties"]["tags"]["items"]["enum"])

# --- CONSTANTS ---
ALLOWED_ERAS = [
    "Old_Republic", "High_Republic", "Fall_of_the_Jedi", 
    "Reign_of_the_Empire", "Rebellion", "New_Republic", 
    "Rise_of_the_First_Order", "Legacy", "All_Eras"
]

DEFAULT_RENOWN_COSTS = [0, 15, 35, 75, 150]

# --- HELPER FUNCTIONS ---

def clean_slug(text):
    if not text: return "unknown"
    return re.sub(r'[^a-z0-9_]', '', text.lower().replace(" ", "_").replace("-", "_"))

def clean_id(raw_id, prefix="fac_"):
    if not raw_id: return f"{prefix}todo_unknown"
    if not isinstance(raw_id, str):
        return f"{prefix}todo_bad_format_{str(raw_id)[:10]}"
        
    # Pre-clean the raw input
    cleaned_input = clean_slug(raw_id)
    
    # If it already has the prefix, ensure it's clean
    if raw_id.startswith(prefix):
        # We still need to ensure the REST of it is clean
        suffix = raw_id[len(prefix):]
        return f"{prefix}{clean_slug(suffix)}"
        
    return f"{prefix}{cleaned_input}"

def validate_tag(tag):
    if tag in ALLOWED_TAGS:
        return tag
    # Try basic normalization
    norm = tag.lower().replace(" ", "_").replace("-", "_")
    if norm in ALLOWED_TAGS:
        return norm
    return None

def map_era(raw_era):
    if isinstance(raw_era, list):
        valid = [e for e in raw_era if e in ALLOWED_ERAS]
        return valid if valid else ["All_Eras"]
    if raw_era in ALLOWED_ERAS:
        return [raw_era]
    return ["All_Eras"]

# --- MIGRATION LOGIC ---

def migrate_faction(filepath):
    filename = filepath.name
    print(f"Processing {filename}...")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"  [ERROR] Failed to parse YAML: {e}")
        return False

    if not data:
        return False

    # 1. PREPARE CORE OBJECT
    core = {}
    legacy_dump = {} # Anything not strict properties goes here

    # --- A. META ---
    # ID
    raw_id = data.get("id", "").replace("fac_", "")
    if not raw_id: raw_id = clean_slug(data.get("name", "unknown"))
    fid = clean_id(raw_id, "fac_") # Ensure strict format
    core["id"] = fid
    
    # Name
    core["name"] = data.get("name", "Unnamed Faction")
    
    # Source
    src = data.get("source", "Canon")
    if src not in ["Canon", "Legends", "Homebrew"]: src = "Canon" # Default
    core["source"] = src
    
    # Era
    core["era"] = map_era(data.get("era", []))
    
    # Tags
    raw_tags = data.get("tags", [])
    valid_tags = []
    
    # Ensure at least one type tag if possible
    ftype = data.get("faction_type", "").lower()
    if ftype:
        mapped_type = validate_tag(ftype)
        if mapped_type: valid_tags.append(mapped_type)
        else:
            # Map legacy types
            if "syndicate" in ftype: valid_tags.append("criminal_syndicate")
            elif "government" in ftype: valid_tags.append("government")
            elif "religious" in ftype: valid_tags.append("religious")
    
    for t in raw_tags:
        vt = validate_tag(t)
        if vt and vt not in valid_tags:
            valid_tags.append(vt)
            
    if not valid_tags: valid_tags.append("neutral") # Fallback
    core["tags"] = sorted(list(set(valid_tags)))

    # --- B. ATOMIC ---
    assets = data.get("assets", {})
    atomic = {}
    atomic["wealth"] = min(10, max(1, int(assets.get("wealth", 5))))
    atomic["military"] = min(10, max(1, int(assets.get("military", 5))))
    atomic["influence"] = min(10, max(1, int(assets.get("influence_tier", 5))))
    atomic["tech_level"] = 5 # Default, not in old schema
    
    # Ranks
    old_ranks = data.get("organization_engine", {}).get("ranks", [])
    new_ranks = []
    for i in range(5):
        if i < len(old_ranks):
            r = old_ranks[i]
            if isinstance(r, str): # Simple list
                new_ranks.append({
                    "rank_id": f"rank_{i+1}_{clean_slug(r)}",
                    "rank_level": i+1,
                    "title": r,
                    "renown_cost": DEFAULT_RENOWN_COSTS[i]
                })
            elif isinstance(r, dict): # Old object
                 new_ranks.append({
                    "rank_id": f"rank_{i+1}_{clean_slug(r.get('Rank Name', 'Unknown'))}",
                    "rank_level": i+1,
                    "title": r.get('Rank Name', 'Unknown'),
                    "renown_cost": DEFAULT_RENOWN_COSTS[i]
                })
        else:
             new_ranks.append({
                    "rank_id": f"rank_{i+1}_placeholder",
                    "rank_level": i+1,
                    "title": f"Rank {i+1}",
                    "renown_cost": DEFAULT_RENOWN_COSTS[i]
                })
    atomic["ranks"] = new_ranks
    core["atomic"] = atomic

    # --- C. SOUL ---
    soul = {}
    soul["description"] = data.get("description", "No description provided.")
    soul["ideology"] = "Survival" # Default
    
    # Extract Guidelines from llm_guidance
    guidance = data.get("llm_guidance", {})
    soul["style_guide"] = {
        "tone": str(guidance.get("tone", "Neutral")),
        "key_phrases": ["For the cause!", "Watch your back."], # Defaults
        "image_prompt_base": str(data.get("image_generation", {}).get("base_prompt", ""))
    }
    
    # Rank Flavor
    soul["rank_flavor"] = {}
    for r in new_ranks:
         soul["rank_flavor"][r["rank_id"]] = f"A {r['title']} commands respect."
         
    core["soul"] = soul

    # --- D. SYNERGY ---
    synergy = {}
    
    # HQ
    hq_raw = assets.get("headquarters_id", "Unknown")
    synergy["headquarters_id"] = clean_id(hq_raw, "pla_")
    
    # KPIs
    roster = data.get("roster", {})
    kpis = roster.get("key_npc_ids", [])
    synergy["key_npc_ids"] = [clean_id(k, "npc_") for k in kpis]
    
    # Relationships
    rels = []
    old_rels = data.get("relationships", [])
    for old_r in old_rels:
        status_map = {
            "allied": "Allied", "friendly": "Friendly", "neutral": "Neutral",
            "unfriendly": "Unfriendly", "hostile": "Hostile", "war": "War"
        }
        raw_status = old_r.get("relationship_type", "Neutral").lower()
        strict_status = status_map.get(raw_status, "Neutral")
        
        rels.append({
            "target_faction_id": clean_id(old_r.get("faction_id", ""), "fac_"),
            "status": strict_status, 
            "narrative": old_r.get("narrative", "")
        })
    synergy["relationships"] = rels
    
    synergy["player_perks"] = [] # Start empty
    core["synergy"] = synergy

    # --- E. UI ---
    core["ui"] = {
        "color_hex": "#CCCCCC",
        "icon_path": "icons/default.png"
    }
    
    # --- F. LEGACY ---
    # Dump everything else
    legacy_keys = ["organization_engine", "quest_engine", "mechanics", "class_synergies", "species_synergies", "faction_raw_data"]
    for k in legacy_keys:
        if k in data:
            legacy_dump[k] = data[k]
    
    if legacy_dump:
        core["_legacy"] = legacy_dump

    # 2. VALIDATE CORE
    try:
        validate(instance=core, schema=CORE_SCHEMA)
    except ValidationError as e:
        error_msg = f"{filename}: {e.message} at {e.path}"
        print(f"  [INVALID CORE] {error_msg}")
        with open("validation_errors.txt", "a") as errf:
            errf.write(f"[CORE] {error_msg}\n")
        
        # Simplistic fix for common relationship status errors
        for r in core["synergy"]["relationships"]:
             if r["status"] not in ["Allied", "Friendly", "Neutral", "Unfriendly", "Hostile", "War"]:
                  r["status"] = "Neutral"
        
        # Retry validation
        try:
             validate(instance=core, schema=CORE_SCHEMA)
        except ValidationError as e2:
             error_msg_2 = f"{filename}: {e2.message} at {e2.path}"
             print(f"  [FATAL CORE] {error_msg_2}")
             with open("validation_errors.txt", "a") as errf:
                errf.write(f"[FATAL CORE] {error_msg_2}\n")
             return False

    # 3. EXPANSION FILE
    expansion = {}
    expansion["parent_faction_id"] = fid
    expansion["items_expanded"] = {
        "weapons": [],
        "armor": [],
        "gear": [] 
    }
    expansion["cultural_features"] = []
    expansion["environmental_adaptations"] = []
    expansion["customization_options"] = {}
    expansion["testing_scaffolding"] = {
        "power_level_target": "5",
        "balance_notes": "Auto-migrated."
    }
    
    # Move minion table to legacy in expansion? No, schema says legacy is allowed.
    expansion["_legacy"] = {"minion_table": roster.get("minion_table", [])}

    try:
        validate(instance=expansion, schema=EXPANSION_SCHEMA)
    except ValidationError as e:
        print(f"  [FATAL EXPANSION] {filename}: {e.message}")
        return False
        
    # 4. WRITE OUTPUTS
    core_out_path = FACTIONS_DIR / f"{fid}.json"
    exp_out_path = EXPANSIONS_DIR / f"{fid}.expansion.json"
    
    with open(core_out_path, "w", encoding="utf-8") as f:
        json.dump(core, f, indent=2)
        
    with open(exp_out_path, "w", encoding="utf-8") as f:
        json.dump(expansion, f, indent=2)
        
    print(f"  [SUCCESS] Migrated -> {fid}.json & {fid}.expansion.json")
    return True

def batch_migration():
    print("Starting Batch Migration...")
    count = 0
    failures = 0
    
    for filename in os.listdir(FACTIONS_DIR):
        if filename.endswith(".yml") or filename.endswith(".yaml"):
            # Exclude rules/direction files
            if filename in ["factions_rules.yml", "unified_development_direction.yml"]: continue
            
            filepath = FACTIONS_DIR / filename
            if migrate_faction(filepath):
                count += 1
            else:
                failures += 1
                
    print(f"\nMigration Complete. Success: {count}, Failures: {failures}")

if __name__ == "__main__":
    batch_migration()
