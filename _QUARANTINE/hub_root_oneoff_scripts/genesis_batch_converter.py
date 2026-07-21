import os
import glob
import json
import yaml
import re
import traceback
from typing import List, Dict, Any, Tuple

# === CONFIGURATION ===
BASE_DIR = r"e:\StarWars\SW5e_Data_Hub\SW5e_Data_Hub"
DATA_DIR = os.path.join(BASE_DIR, "data")
FACTIONS_DIR = os.path.join(DATA_DIR, "factions")
EXPANSIONS_DIR = os.path.join(DATA_DIR, "faction_expansions")
# NEW SCHEMA LCOATION
SCHEMAS_DIR = os.path.join(BASE_DIR, "schema")
TAGS_FILE = os.path.join(DATA_DIR, "tags", "master_tags.yml")

# Ensure output directories exist
os.makedirs(FACTIONS_DIR, exist_ok=True)
os.makedirs(EXPANSIONS_DIR, exist_ok=True)

# === LOADERS ===

def load_json_schema(filename: str) -> Dict:
    path = os.path.join(SCHEMAS_DIR, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"CRITICAL: Could not load schema {path}: {e}")
        return {}

# Load specific schemas
CORE_SCHEMA = load_json_schema("Faction_Core.schema.json")
EXPANSION_SCHEMA = load_json_schema("Faction_Expanded.schema.json")


def load_master_tags() -> List[str]:
    try:
        with open(TAGS_FILE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            tags = []
            if data:
                for category in data:
                    if isinstance(data[category], list):
                        for item in data[category]:
                            if isinstance(item, dict) and 'tag_id' in item:
                                tags.append(item['tag_id'])
            return tags
    except Exception as e:
        print(f"CRITICAL: Error loading master tags: {e}")
        return []

MASTER_TAGS = set(load_master_tags()) # Use set for O(1) lookups

# === HELPER PROPERTIES ===

DEFAULT_IMAGE_PROMPT = "Cinematic concept art, Star Wars style, detailed, realistic lighting"

# === UTILITIES ===

def to_snake_case(text: str) -> str:
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9_]', '_', text)
    text = re.sub(r'_+', '_', text)
    return text.strip('_')

def get_slug_from_filename(filename: str) -> str:
    base = os.path.splitext(filename)[0]
    base = base.replace('fac_', '')
    return to_snake_case(base)

def ensure_list(val: Any) -> List:
    if val is None: return []
    if isinstance(val, list): return val
    if isinstance(val, (str, int, float, dict)): return [val]
    return []

# === CORE LOGIC ===

def validate_tag(tag: str) -> str:
    """Returns tag if valid, else None."""
    # Strict check
    if tag in MASTER_TAGS:
        return tag
    return None

def standardize_id(prefix: str, value: str) -> str:
    """Ensures ID starts with prefix_ and is snake_case."""
    if not value:
        return f"{prefix}_todo_missing"
    
    slug = to_snake_case(value)
    if slug.startswith(f"{prefix}_"):
        return slug
    return f"{prefix}_{slug}"

def estimate_atomic_defaults(faction_type: str) -> Dict[str, int]:
    ft = str(faction_type).lower()
    # Protocol C2 defaults
    if 'government' in ft or 'imperial' in ft: 
         return {"wealth": 9, "military": 10, "influence": 9, "tech_level": 8}
    if 'syndicate' in ft or 'crime' in ft or 'criminal' in ft:
         return {"wealth": 7, "military": 5, "influence": 7, "tech_level": 5}
    if 'rebel' in ft or 'cell' in ft:
         return {"wealth": 3, "military": 4, "influence": 5, "tech_level": 4}
    if 'tradition' in ft or 'cult' in ft or 'jedi' in ft or 'sith' in ft:
         return {"wealth": 4, "military": 6, "influence": 3, "tech_level": 4}
    
    # Generic fallback
    return {"wealth": 5, "military": 5, "influence": 5, "tech_level": 5}

def interpolate_ranks(legacy_ranks: List[Dict]) -> List[Dict]:
    """Ensures exactly 5 ranks with valid IDs."""
    clean_titles = []
    
    if legacy_ranks:
        for r in legacy_ranks:
            if not isinstance(r, dict): continue
            # Attempt to find title
            title = r.get('title') or r.get('Rank Name') or r.get('rank_name')
            if not title and len(r) > 0:
                # heuristic: first value likely title
                title = list(r.values())[0]
            if title:
                clean_titles.append(str(title))
    
    if not clean_titles:
        clean_titles = ["Initiate", "Member", "Veteran", "Officer", "Leader"]
    
    # Interpolation logic
    # If < 5, insert intermediates
    while len(clean_titles) < 5:
        # insert before last
        clean_titles.insert(len(clean_titles)-1, f"Senior {clean_titles[-2]}")
    
    # If > 5, truncate (or keep top 5? usually keep first 4 and last 1? Let's keep first 5)
    if len(clean_titles) > 5:
        clean_titles = clean_titles[:5]
        
    final_ranks = []
    costs = [0, 10, 25, 60, 100] # Monotonic increase
    
    for i, title in enumerate(clean_titles):
        # Generate meaningful snake_case ID
        rid = to_snake_case(title)
        if not rid: rid = f"rank_{i+1}"
        
        final_ranks.append({
            "rank_id": rid,
            "rank_level": i + 1,
            "title": title,
            "renown_cost": costs[i]
        })
    return final_ranks

def parse_mechanic_rule(legacy_text: str, context: str) -> Tuple[Dict, str]:
    """
    Returns (StrictRuleObject, LegacyDumpString).
    If strict parsing impossible, returns (SafeRule, OriginalText).
    """
    # Very basic heuristic parsing could go here.
    # For now, default to safe rule + dump.
    
    safe_rule = {
        "type": "skill_bonus",
        "target": "skill_insight", # Valid namespace
        "value": 1,
        "condition": "interacting_with_faction"
    }
    
    return safe_rule, legacy_text

# === AUDIT CONSTANTS ===
AUDIT_LOG = {
    "todo_refs": [],
    "defaulted_tags": [],
    "fixed_image_prompts": [],
    "validation_failures": []
}

def convert_file(filepath: str):
    filename = os.path.basename(filepath)
    # Skip non-legacy files if possible, or process all. 
    # Protocol says "Convert legacy faction data".
    print(f"Processing {filename}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            legacy = yaml.safe_load(f)
        
        if not isinstance(legacy, dict):
            print(f"Skipping {filename}: Not a dict.")
            return

        slug = get_slug_from_filename(filename)
        new_id = f"fac_{slug}"
        
        # Meta
        name = legacy.get('name', slug.replace('_', ' ').title())
        source = legacy.get('source', 'Canon')
        if source not in ["Canon", "Legends", "Homebrew"]: source = "Canon"
        
        raw_era = ensure_list(legacy.get('era', ['Rebellion']))
        valid_eras = ["Old_Republic", "High_Republic", "Fall_of_the_Jedi", "Reign_of_the_Empire", "Rebellion", "New_Republic", "Rise_of_the_First_Order", "Legacy", "All_Eras"]
        era = [e for e in raw_era if e in valid_eras]
        if not era: era = ["Rebellion"]
        
        # Tags - Strict Lexicon
        raw_tags = ensure_list(legacy.get('tags'))
        final_tags = []
        for t in raw_tags:
            vt = validate_tag(str(t).lower()) # IDs usually lowercase
            if vt: 
                final_tags.append(vt)
            else:
                # Tag not in lexicon. 
                pass
        
        if not final_tags:
            # Protocol: "Defaulted tags" to be audited
            AUDIT_LOG["defaulted_tags"].append(new_id)
            # We must check if we can add a generic valid tag or if we fail schemas minItems 1
            # I need at least one valid tag.
            # I'll check if 'organization' is valid? 
            # I checked the file, 'organization' was NOT a tag_id in the view. 'government', 'criminal_syndicate' were in 'faction_types' category but the tool view didn't show if they are tags.
            # Wait, Step 61 showed "faction_types" category at the end. Tag IDs: government, criminal_syndicate, neutral, religious, military.
            # So 'government' IS a valid tag_id.
            
            ft_lower = str(legacy.get('faction_type', '')).lower()
            if 'government' in ft_lower: final_tags.append('government')
            elif 'syndicate' in ft_lower or 'crime' in ft_lower: final_tags.append('criminal_syndicate')
            elif 'religious' in ft_lower: final_tags.append('religious')
            elif 'military' in ft_lower: final_tags.append('military')
            else: final_tags.append('neutral') # fallback
            
        # Legacy Dump
        legacy_dump = {} # Raw dump for non-compliant data
        
        # Atomic
        defaults = estimate_atomic_defaults(legacy.get('faction_type', ''))
        assets = legacy.get('assets', {})
        atomic = {
            "wealth": int(assets.get('wealth', defaults['wealth'])),
            "military": int(assets.get('military', defaults['military'])),
            "influence": int(assets.get('influence', assets.get('influence_tier', defaults['influence']))),
            "tech_level": int(assets.get('tech_level', defaults['tech_level'])),
            "ranks": interpolate_ranks(legacy.get('organization_engine', {}).get('ranks', []))
        }
        
        # Soul
        desc = legacy.get('description', 'Faction description unavailable.')
        soul = {
            "description": str(desc),
            "ideology": str(legacy.get('ideology', "Survival and prosperity.")), # Distinct default
            "style_guide": {
                "tone": "Serious",
                "key_phrases": ["For the cause"], # Placeholder
                "image_prompt_base": legacy.get('image_generation', {}).get('base_prompt', DEFAULT_IMAGE_PROMPT)
            },
            "rank_flavor": {}
        }
        
        if not soul['style_guide']['image_prompt_base']:
            soul['style_guide']['image_prompt_base'] = DEFAULT_IMAGE_PROMPT
            AUDIT_LOG['fixed_image_prompts'].append(new_id)
            
        for r in atomic['ranks']:
            soul['rank_flavor'][r['rank_id']] = f"Rank {r['title']} flavor text placeholder."

        # Synergy
        synergy = {
            "headquarters_id": standardize_id("pla", assets.get('headquarters_id') or "todo_hq"),
            "key_npc_ids": [],
            "relationships": [],
            "player_perks": []
        }
        
        if "todo" in synergy["headquarters_id"]:
            AUDIT_LOG["todo_refs"].append(f"{new_id}: {synergy['headquarters_id']}")

        roster = legacy.get('roster', {})
        for npc in ensure_list(roster.get('leader_ids', [])):
             nid = standardize_id("npc", str(npc))
             synergy['key_npc_ids'].append(nid)
             if "todo" in nid: AUDIT_LOG["todo_refs"].append(f"{new_id}: {nid}")
             
        # Relationship Rules
        for rel in ensure_list(legacy.get('relationships', [])):
            target = standardize_id("fac", rel.get('faction_id', 'unknown'))
            status = rel.get('relationship_type', 'Neutral')
            if status not in ["Allied", "Friendly", "Neutral", "Unfriendly", "Hostile", "War"]: status = "Neutral"
            
            narrative = rel.get('narrative', 'Relationship details pending.')
            
            mech_text = rel.get('mechanical_modifier')
            if mech_text:
                legacy_dump[f"rel_{target}_legacy_rule"] = mech_text
                rule = {
                     "type": "interaction_bonus",
                     "target": "skill_insight",
                     "value": 1,
                     "condition": "interacting_with_faction"
                }
            else:
                rule = {
                     "type": "interaction_bonus",
                     "target": "skill_insight",
                     "value": 1
                }
            
            synergy["relationships"].append({
                "target_faction_id": target,
                "status": status,
                "narrative": str(narrative),
                "mechanical_rule": rule
            })

        # Affiliation
        # Check Core Schema for affiliation property
        has_affiliation_in_schema = 'affiliation' in CORE_SCHEMA.get('properties', {})
        
        # Generate Affiliation Surface (either for root or legacy)
        reputation_axes = [
            {"axis": "loyalty", "polarity": "positive", "description": "Dedication to the faction."},
            {"axis": "competence", "polarity": "positive", "description": "Ability to get results."},
            {"axis": "discretion", "polarity": "positive", "description": "Ability to keep secrets."}
        ]
        renown_scale = {"min": 0, "max": 200}
        
        affiliation_surface = {
            "renown_scale": renown_scale,
            "reputation_axes": reputation_axes
        }
        
        # Construct Core Object
        core_obj = {
            "id": new_id,
            "name": str(name),
            "source": source,
            "era": era,
            "tags": final_tags,
            "_legacy": legacy_dump,
            "atomic": atomic,
            "soul": soul,
            "synergy": synergy,
            "ui": {
                "color_hex": "#CCCCCC",
                "icon_path": f"icons/{slug}.png"
            }
        }
        
        if has_affiliation_in_schema:
            core_obj['affiliation'] = affiliation_surface
        else:
            core_obj['_legacy']['affiliation_surface'] = affiliation_surface

        # Dump unhandled
        handled_keys = ['id', 'name', 'faction_type', 'era', 'source', 'description', 'organization_engine', 'assets', 'roster', 'relationships', 'tags', 'image_generation', 'ideology']
        for k, v in legacy.items():
            if k not in handled_keys:
                legacy_dump[k] = v
        
        # Write Core
        core_path = os.path.join(FACTIONS_DIR, f"{new_id}.json")
        with open(core_path, 'w', encoding='utf-8') as f:
            json.dump(core_obj, f, indent=2)
            
        # Expansion
        exp_obj = {
            "parent_faction_id": new_id,
            "items_expanded": {"weapons": [], "armor": [], "gear": []},
            "cultural_features": [],
            "environmental_adaptations": [],
            "customization_options": {"appearance": [], "equipment": []},
            "testing_scaffolding": {
                "power_level_target": "Mid",
                "balance_notes": "Automated migration via Genesis Protocol v2.1"
            }
        }
        exp_path = os.path.join(EXPANSIONS_DIR, f"{new_id}.expansion.json")
        with open(exp_path, 'w', encoding='utf-8') as f:
            json.dump(exp_obj, f, indent=2)
            
        print(f"Generated {core_path}")

    except Exception:
        print(f"FAILED to process {filepath}")
        traceback.print_exc()

def run_audit():
    print("\n=== GENESIS BATCH CONVERTER AUDIT REPORT ===")
    print(f"Schema Source: {SCHEMAS_DIR}")
    print(f"Core Schema Loaded: {'Yes' if CORE_SCHEMA else 'NO'}")
    
    print(f"\nDefaulted Tags: {len(AUDIT_LOG['defaulted_tags'])}")
    for f in AUDIT_LOG['defaulted_tags']: print(f"  - {f}")
    
    print(f"\nFixed Image Prompts: {len(AUDIT_LOG['fixed_image_prompts'])}")
    
    print(f"\nTODO References: {len(AUDIT_LOG['todo_refs'])}")
    # limit output
    for r in AUDIT_LOG['todo_refs'][:10]: print(f"  - {r}")
    if len(AUDIT_LOG['todo_refs']) > 10: print("  ...and more.")

def run_batch():
    files = glob.glob(os.path.join(FACTIONS_DIR, "*.yml"))
    # Filtering: Only process original YAMLs. fac_ prefixes are usually outputs or intermediate.
    # But user asked to process "legacy faction data".
    for p in files:
        fname = os.path.basename(p)
        if fname.startswith('fac_') and fname.endswith('.json'): continue # Skip JSONs obviously
        if fname == 'master_tags.yml': continue
        if fname == 'factions_rules.yml': continue
        
        # We process 'fac_black_sun.yml' if it exists as legacy input? 
        # The user said "Convert all legacy faction files".
        # If 'children_watch.yml' exists, use it.
        # If 'fac_black_sun.yml' exists, use it.
        # We'll trust the loop.
        convert_file(p)
        
    run_audit()

if __name__ == "__main__":
    run_batch()
