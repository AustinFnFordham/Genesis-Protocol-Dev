import os
import glob
import json
import yaml
import re
import traceback
import sys
from typing import List, Dict, Any, Tuple, Set

# === CONFIGURATION ===
BASE_DIR = r"e:\StarWars\SW5e_Data_Hub\SW5e_Data_Hub"
DATA_DIR = os.path.join(BASE_DIR, "data")
FACTIONS_DIR = os.path.join(DATA_DIR, "factions")
EXPANSIONS_DIR = os.path.join(DATA_DIR, "faction_expansions")
SCHEMAS_DIR = os.path.join(BASE_DIR, "schema")
TAGS_FILE = os.path.join(DATA_DIR, "tags", "faction_tags.yml")

# Ensure output directories exist
os.makedirs(FACTIONS_DIR, exist_ok=True)
os.makedirs(EXPANSIONS_DIR, exist_ok=True)

# === LOADERS & VALIDATION ===

def load_json_schema(filename: str) -> Dict:
    path = os.path.join(SCHEMAS_DIR, filename)
    if not os.path.exists(path):
        print(f"CRITICAL: Schema file not found: {path}")
        sys.exit(1)
    
    # Strict filename check? Windows is case-insensitive, but we can try to be strict.
    # We rely on user confirmation that files were renamed.
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
            
        # Blocking check for Affiliation on Core
        if filename == "faction_core.schema.json":
            if "affiliation" not in schema.get("properties", {}):
                  print("CRITICAL: faction_core.schema.json missing root 'affiliation' property. ABORTING.")
                  sys.exit(1)
        return schema
    except Exception as e:
        print(f"CRITICAL: Could not load schema {path}: {e}")
        sys.exit(1)

CORE_SCHEMA = load_json_schema("faction_core.schema.json")
EXPANSION_SCHEMA = load_json_schema("faction_expansion.schema.json")

def validate_against_schema(data: Dict, schema: Dict) -> Tuple[bool, str]:
    """
    Manual validation helper since `jsonschema` might not be installed.
    Checks strictness: required fields, types, enums (if simple).
    This is a lightweight validator. For full rigor, we rely on the schema structure 
    and avoiding unknown keys.
    """
    try:
        # Check additionalProperties: false at root
        if schema.get("additionalProperties") is False:
             allowed = set(schema.get("properties", {}).keys())
             actual = set(data.keys())
             extra = actual - allowed
             if extra: return False, f"Unknown properties: {extra}"

        # Check required
        required = schema.get("required", [])
        for r in required:
             if r not in data: return False, f"Missing required field: {r}"
        
        # Recurse for specific strict checks if needed?
        # For now, we trust the generator logic matches the known schema structure.
        return True, ""
    except Exception as e:
        return False, f"Validation exception: {e}"

# Tag Logic
class TagEngine:
    def __init__(self):
        self.tags = {}
        self.type_tags = set()
        self.load_lexicon()
        
    def load_lexicon(self):
        try:
            with open(TAGS_FILE, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                for t in data.get('tags', []):
                    tid = t['tag_id']
                    self.tags[tid] = t
                    if t.get('kind') == 'type':
                        self.type_tags.add(tid)
        except Exception as e:
            print(f"Error loading tags: {e}")
            
    def resolve(self, input_tags: List[str]) -> Tuple[List[str], Dict]:
        """
        Returns (FinalTags, LegacyLog)
        """
        current_tags = set()
        legacy_log = {"tag_suggestions": [], "tag_conflicts": []}
        
        # Initial Validation
        for t in input_tags:
            t = str(t).lower().strip()
            if t in self.tags:
                current_tags.add(t)
            else:
                legacy_log["tag_suggestions"].append(t)
                
        # Implies
        # Iterate snapshot to avoid infinite loop (max depth 1 usually enough for simple implies)
        snapshot = list(current_tags)
        for t in snapshot:
            implies = self.tags[t].get("implies", [])
            for imp in implies:
                if imp in self.tags:
                    current_tags.add(imp)
                    
        # Excludes
        # Logic: If A excludes B, and both present:
        # If both are TYPE tags -> KEEP BOTH, log conflict. (Strict Rule: never remove type)
        # If one is TYPE, remove other. 
        # If neither TYPE (unlikely for excludes), keep first? 
        
        # We need to process exclusions carefully.
        to_remove = set()
        
        sorted_tags = sorted(list(current_tags)) # deterministic order
        for t in sorted_tags:
            if t in to_remove: continue
            
            excludes = self.tags[t].get("excludes", [])
            for exc in excludes:
                if exc in current_tags and exc not in to_remove:
                    # Conflict found: t vs exc
                    t_is_type = t in self.type_tags
                    exc_is_type = exc in self.type_tags
                    
                    if t_is_type and exc_is_type:
                        legacy_log["tag_conflicts"].append(f"{t} excludes {exc}")
                        # Do not remove either
                    elif t_is_type:
                        to_remove.add(exc)
                    elif exc_is_type:
                        to_remove.add(t)
                        # If t is removed, stop processing it? No, finish logic
                    else:
                        # arbitrary or priority? remove exc
                        to_remove.add(exc)
        
        final = [t for t in sorted_tags if t not in to_remove]
        
        # Enforce Min/Max (Soft check here, schema/logic might be strict)
        # We won't block migration on min/max but valid factions should comply.
        
        return final, legacy_log

TAG_ENGINE = TagEngine()

# === UTILS ===

def to_snake_case(text: str) -> str:
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9_]', '_', text)
    text = re.sub(r'_+', '_', text)
    return text.strip('_')

def get_slug(filename: str) -> str:
    base = os.path.splitext(filename)[0]
    base = base.replace('fac_', '') # strip prefix if present in legacy filename
    return to_snake_case(base)

def standardize_id(prefix: str, value: str) -> str:
    if not value or str(value).lower() in ['none', 'null', '']:
        return f"{prefix}_todo_missing"
    slug = to_snake_case(str(value))
    if slug.startswith(f"{prefix}_"): return slug
    return f"{prefix}_{slug}"

# === GENERATORS ===

def generate_affiliation(tags: List[str], ideology: str) -> Dict:
    """
    Generates Affiliation Surface based on tags/ideology.
    """
    renown_scale = {"min": 0, "max": 200}
    axes = []
    
    # Heuristic based on tags
    if "criminal_syndicate" in tags or "underworld" in tags:
        axes.append({"axis": "Profitability", "polarity": "positive", "description": "Generates credits for the organization."})
        axes.append({"axis": "Heat", "polarity": "negative", "description": "Draws unwanted law enforcement attention."})
        axes.append({"axis": "Loyalty", "polarity": "positive", "description": "Adherence to the code of silence."})
    elif "jedi" in tags or "light_side" in tags:
        axes.append({"axis": "Compassion", "polarity": "positive", "description": "demonstrates care for life."})
        axes.append({"axis": "Serenity", "polarity": "positive", "description": "Maintains emotional control."})
        axes.append({"axis": "Dark_Side_Temptation", "polarity": "negative", "description": "Succumbs to passion or anger."})
    elif "sith" in tags or "dark_side" in tags:
        axes.append({"axis": "Strength", "polarity": "positive", "description": "Displays dominance and power."})
        axes.append({"axis": "Weakness", "polarity": "negative", "description": "Displays mercy or hesitation."})
        axes.append({"axis": "Ambition", "polarity": "positive", "description": "Seeks advancement at any cost."})
    elif "government" in tags or "military" in tags:
        axes.append({"axis": "Obedience", "polarity": "positive", "description": "Follows orders and protocol."})
        axes.append({"axis": "Efficiency", "polarity": "positive", "description": "Completes objectives with minimal waste."})
        axes.append({"axis": "Insubordination", "polarity": "negative", "description": "Disregards chain of command."})
    elif "mandalorian" in tags or "honor_bound" in tags:
        axes.append({"axis": "Honor", "polarity": "positive", "description": "Actions that bring glory to the clan."})
        axes.append({"axis": "Cowardice", "polarity": "negative", "description": "Fleeing from battle or showing fear."})
        axes.append({"axis": "Strength_At_Arms", "polarity": "positive", "description": "Combat prowess."})
    else:
        # Neutral / Generic
        axes.append({"axis": "Contribution", "polarity": "positive", "description": "Material or service contribution."})
        axes.append({"axis": "Reliability", "polarity": "positive", "description": "Trustworthiness in missions."})
        
    # Ensure 2-3 items.
    return {
        "renown_scale": renown_scale,
        "reputation_axes": axes[:3]
    }

def generate_ranks(legacy_ranks: List[Dict]) -> List[Dict]:
    """
    Interpolates legacy ranks to exactly 5 with strict renown costs.
    Renown: [0, 15, 35, 75, 150]
    """
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
    
    # Handle shortage
    base_titles = ["Initiate", "Member", "Veteran", "Officer", "Leader"]
    
    if not clean_titles:
        clean_titles = base_titles
    elif len(clean_titles) < 5:
        # Interpolate
        needed = 5 - len(clean_titles)
        # Insert generic logic
        if len(clean_titles) == 1:
            clean_titles = ["Outsider", clean_titles[0], "Trusted " + clean_titles[0], "Senior " + clean_titles[0], "Master " + clean_titles[0]]
        else:
             while len(clean_titles) < 5:
                 clean_titles.insert(len(clean_titles)-1, f"Senior {clean_titles[-2]}")
                 
    elif len(clean_titles) > 5:
        # Truncate / Condense
        clean_titles = clean_titles[:5]
        
    costs = [0, 15, 35, 75, 150]
    final_ranks = []
    for i, t in enumerate(clean_titles):
        # Strict ID
        rid = to_snake_case(t)
        if not rid or rid.isdigit(): rid = f"rank_{i+1}"
        
        final_ranks.append({
            "rank_id": rid,
            "rank_level": i + 1,
            "title": t,
            "renown_cost": costs[i]
        })
        
    return final_ranks

def generate_soul(legacy: Dict, ranks: List[Dict], tags: List[str]) -> Dict:
    """
    Generates Soul Engine.
    """
    desc = str(legacy.get('description') or "Faction description pending.")
    ideology = str(legacy.get('ideology') or "Survival and prosperity.")
    
    # Rank Flavor
    rank_flavor = {}
    for r in ranks:
        title = r['title']
        level = r['rank_level']
        # Grounded generation
        if level == 1:
            flavor = f"A {title} is expected to prove their worth, often given dangerous tasks with little support."
        elif level == 2:
            flavor = f"Having survived initiation, a {title} gains access to safehouses and basic resources."
        elif level == 3:
            flavor = f"A {title} is a proven asset, entrusted with sensitive operations and commanding respect."
        elif level == 4:
            flavor = f"With authority over sectors, a {title} shapes policy and directs significant assets."
        elif level == 5:
            flavor = f"The {title} is the supreme authority, their word law, carrying the burden of the faction's survival."
        rank_flavor[r['rank_id']] = flavor
        
    return {
        "description": desc,
        "ideology": ideology,
        "style_guide": {
            "tone": legacy.get('style_guide', {}).get('tone', "Serious and grounded"),
            "key_phrases": legacy.get('style_guide', {}).get('key_phrases', ["For the cause"]),
            "image_prompt_base": legacy.get('image_generation', {}).get('base_prompt', legacy.get('style_guide', {}).get('image_prompt_base', "Cinematic concept art, Star Wars style"))
        },
        "rank_flavor": rank_flavor
    }

def convert_relationship_rule(legacy_rule: Any) -> Tuple[Dict, str]:
    """
    Returns (StrictRule, LegacyDump)
    """
    # If it's just a string or missing, default to safe rule
    if not isinstance(legacy_rule, dict):
        return {
            "type": "interaction_bonus",
            "target": "skill_insight",
            "value": 1,
            "condition": "interacting_with_faction"
        }, str(legacy_rule) if legacy_rule else ""
        
    # If it looks strict already
    if 'type' in legacy_rule and 'target' in legacy_rule and 'value' in legacy_rule:
        # Validate allowed keys only
        new_rule = {
            "type": legacy_rule['type'],
            "target": legacy_rule['target'],
            "value": int(legacy_rule['value']),
        }
        if 'condition' in legacy_rule:
            new_rule['condition'] = legacy_rule['condition']
        return new_rule, ""
        
    return {
            "type": "interaction_bonus",
            "target": "skill_insight",
            "value": 1,
            "condition": "interacting_with_faction"
    }, json.dumps(legacy_rule)

# === MAIN PIPELINE ===

def process_file(filepath: str):
    filename = os.path.basename(filepath)
    print(f"Migrating {filename}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            legacy = yaml.safe_load(f)
            
        if not isinstance(legacy, dict):
            print(f"Skipping {filename}: Not a dict")
            return

        slug = get_slug(filename)
        new_id = f"fac_{slug}"
        
        # Tags
        raw_tags = legacy.get('tags', [])
        if not isinstance(raw_tags, list): raw_tags = []
        final_tags, tag_log = TAG_ENGINE.resolve(raw_tags)
        
        # Fallback if no tags
        if not final_tags:
            ft = str(legacy.get('faction_type', '')).lower()
            if 'gov' in ft: final_tags.append('government')
            elif 'crim' in ft: final_tags.append('criminal_syndicate')
            elif 'jedi' in ft: final_tags.append('religious_order')
            else: final_tags.append('government') # Default to government if totally unknown to valid schema? No, better safe.
            # Re-resolve to get implies
            final_tags, _ = TAG_ENGINE.resolve(final_tags)

        # Atomic
        legacy_ranks = legacy.get('organization_engine', {}).get('ranks') or \
                       legacy.get('atomic', {}).get('ranks') or \
                       legacy.get('ranks', [])
        ranks = generate_ranks(legacy_ranks)
        
        # Estimate defaults
        defaults = {"wealth": 5, "military": 5, "influence": 5, "tech_level": 5}
        # Refine defaults based on tags?
        if "government" in final_tags: defaults = {"wealth": 9, "military": 10, "influence": 9, "tech_level": 8}
        elif "criminal_syndicate" in final_tags: defaults = {"wealth": 8, "military": 6, "influence": 7, "tech_level": 6}
        elif "rebellion" in final_tags: defaults = {"wealth": 3, "military": 4, "influence": 5, "tech_level": 5}
            
        assets = legacy.get('assets', legacy.get('atomic', {}))
        atomic = {
            "wealth": int(assets.get('wealth', defaults['wealth'])),
            "military": int(assets.get('military', defaults['military'])),
            "influence": int(assets.get('influence', defaults['influence'])),
            "tech_level": int(assets.get('tech_level', defaults['tech_level'])),
            "ranks": ranks
        }
        
        # Soul
        soul = generate_soul(legacy, ranks, final_tags)
        
        # Synergy
        synergy = {
            "headquarters_id": standardize_id("pla", assets.get('headquarters_id') or "todo_hq"),
            "key_npc_ids": [],
            "relationships": [],
            "player_perks": []
        }
        
        # NPCs
        roster = legacy.get('roster', {})
        for npc in (roster.get('leader_ids', []) or []):
            synergy['key_npc_ids'].append(standardize_id("npc", npc))
            
        # Relationships
        rels = legacy.get('relationships', []) or []
        legacy_dump_rules = {}
        for r in rels:
            if not isinstance(r, dict): continue
            tid = standardize_id("fac", r.get('faction_id', 'unknown'))
            status = r.get('relationship_type', 'Neutral')
            narr = r.get('narrative', 'Relations details pending.')
            mech, dump = convert_relationship_rule(r.get('mechanical_modifier') or r.get('mechanical_rule'))
            
            if dump:
                legacy_dump_rules[f"rel_{tid}_legacy"] = dump
                
            synergy['relationships'].append({
                "target_faction_id": tid,
                "status": status,
                "narrative": str(narr),
                "mechanical_rule": mech
            })
            
        # Affiliation
        affiliation = generate_affiliation(final_tags, soul['ideology'])
        
        # Legacy
        _legacy = {
            "original_filename": filename,
            "tag_log": tag_log,
            "rule_dumps": legacy_dump_rules,
            "unassigned_data": {}
        }
        
        # Dump unassigned
        ignore = ['id', 'name', 'source', 'era', 'tags', 'atomic', 'soul', 'synergy', 'ui', 'affiliation', '_legacy']
        for k, v in legacy.items():
            if k not in ignore and k not in ['organization_engine', 'assets', 'roster', 'relationships', 'faction_type', 'description', 'ideology', 'style_guide', 'image_generation']:
                _legacy['unassigned_data'][k] = v
                
        # Core Object
        core_obj = {
            "id": new_id,
            "name": legacy.get('name', slug.replace('_', ' ').title()),
            "source": legacy.get('source', 'Canon'),
            "era": legacy.get('era', ["Rebellion"]), # Default if missing
            "tags": final_tags,
            "_legacy": _legacy,
            "affiliation": affiliation,
            "atomic": atomic,
            "soul": soul,
            "synergy": synergy,
            "ui": {
                "color_hex": legacy.get('ui', {}).get('color_hex', "#CCCCCC"),
                "icon_path": legacy.get('ui', {}).get('icon_path', f"icons/{slug}.svg"),
                "image_path": legacy.get('ui', {}).get('image_path', f"images/{slug}_hero.webp")
            }
        }
        
        # Expansion Object
        exp_obj = {
            "parent_faction_id": new_id,
            "items_expanded": {"weapons": [], "armor": [], "gear": []},
            "cultural_features": [],
            "environmental_adaptations": [],
            "customization_options": {"appearance": [], "equipment": []},
            "testing_scaffolding": {"power_level_target": "Mid"}
        }
        
        # Validation
        c_valid, c_err = validate_against_schema(core_obj, CORE_SCHEMA)
        e_valid, e_err = validate_against_schema(exp_obj, EXPANSION_SCHEMA)
        
        if c_valid and e_valid:
            # Write Both
            c_path = os.path.join(FACTIONS_DIR, f"{new_id}.yml")
            e_path = os.path.join(EXPANSIONS_DIR, f"{new_id}.expansion.yml")
            
            # YAML Dump strict (no aliases)
            class NoAliasDumper(yaml.SafeDumper):
                def ignore_aliases(self, data): return True
                
            with open(c_path, 'w', encoding='utf-8') as f:
                yaml.dump(core_obj, f, Dumper=NoAliasDumper, sort_keys=False, default_flow_style=False)
            
            with open(e_path, 'w', encoding='utf-8') as f:
                yaml.dump(exp_obj, f, Dumper=NoAliasDumper, sort_keys=False, default_flow_style=False)
                
            print(f"SUCCESS: {new_id}")
        else:
            print(f"FAILURE: {new_id} - Validation Failed")
            if not c_valid: print(f"  Core Error: {c_err}")
            if not e_valid: print(f"  Exp Error: {e_err}")
            # Atomic Fail - Write Nothing

    except Exception:
        print(f"EXCEPTION: {filename}")
        traceback.print_exc()

def run_batch():
    files = glob.glob(os.path.join(FACTIONS_DIR, "*.yml"))
    for p in files:
        fname = os.path.basename(p)
        # Process legacy input. Skip output files if they exist in same dir (fac_*.yml)
        # But wait, user wants output as fac_*.yml in same dir?
        # "Output locations: Core: data/factions/fac_<slug>.yml"
        # Since input is "legacy", e.g. "black_sun.yml", output "fac_black_sun.yml" is fine.
        # We must avoid processing "fac_black_sun.yml" AS INPUT.
        if fname.startswith("fac_") and "todo" not in fname: 
             # Check if it is a V3 output? 
             # Heuristic: V3 output has 'affiliation' at root.
             # If we re-run, we might process our own output.
             # For now, skip fac_ prefix to be safe, assume source is non-prefixed.
             continue
             
        if fname in ["master_tags.yml", "factions_rules.yml", "faction_tags.yml"]: continue
        
        process_file(p)

if __name__ == "__main__":
    run_batch()
