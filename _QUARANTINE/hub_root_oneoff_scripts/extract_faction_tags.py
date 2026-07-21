import os
import glob
import yaml
import re

# Config
BASE_DIR = r"e:\StarWars\SW5e_Data_Hub\SW5e_Data_Hub"
DATA_DIR = os.path.join(BASE_DIR, "data")
FACTIONS_DIR = os.path.join(DATA_DIR, "factions")
OUTPUT_FILE = os.path.join(DATA_DIR, "tags", "faction_tags.yml")

# Initial Content from User Spec
INITIAL_DATA = {
    "version": 1,
    "domain": "factions",
    "tags": [
        {"tag_id": "government", "kind": "type", "description": "A recognized governing body with territorial sovereignty.", "implies": ["politics"], "excludes": ["criminal_syndicate"]},
        {"tag_id": "criminal_syndicate", "kind": "type", "description": "An organized underworld power with illicit revenue streams.", "implies": ["underworld"], "excludes": ["government"]},
        {"tag_id": "religious_order", "kind": "type", "description": "A faith/creed-driven institution with ritual or doctrine."},
        {"tag_id": "military", "kind": "type", "description": "A primarily martial organization with command structure."},
        {"tag_id": "rebellion", "kind": "type", "description": "An insurgent movement opposing a state or occupier."},
        {"tag_id": "underworld", "kind": "domain", "description": "Smuggling, spice, piracy, black markets, corruption."},
        {"tag_id": "politics", "kind": "domain", "description": "Influence, governance, bureaucracy, diplomacy."},
        {"tag_id": "ruthless", "kind": "vibe", "description": "Wins by fear, coercion, and brutality.", "polarity_default": "complex"},
        {"tag_id": "honor_bound", "kind": "vibe", "description": "Adheres to codes, oaths, and reputation.", "polarity_default": "complex"}
    ],
    "selection_policy": {
        "min_tags": 2,
        "max_tags": 6,
        "require_one_of_kinds": ["type"]
    }
}

def to_snake_case(text):
    if not isinstance(text, str): return str(text)
    text = text.lower()
    text = re.sub(r'[^a-z0-9_]', '_', text)
    text = re.sub(r'_+', '_', text)
    return text.strip('_')

def run_extraction():
    print("Starting tag extraction...")
    
    # 1. Load existing/initial tags
    existing_tags = {t['tag_id']: t for t in INITIAL_DATA['tags']}
    
    # 2. Scan faction files
    files = glob.glob(os.path.join(FACTIONS_DIR, "*.yml"))
    count = 0
    scraped_count = 0
    
    for p in files:
        fname = os.path.basename(p)
        # Skip output files to avoid double counting or processing processed files
        # We want the SOURCE tags.
        if fname.startswith("fac_"): continue
        if fname in ["master_tags.yml", "factions_rules.yml"]: continue
        
        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            if isinstance(data, dict):
                file_tags = data.get('tags', [])
                if isinstance(file_tags, list):
                    for raw_tag in file_tags:
                        tid = to_snake_case(str(raw_tag))
                        if tid and tid not in existing_tags:
                            # Add new tag
                            new_tag = {
                                "tag_id": tid,
                                "kind": "scraped",
                                "description": f"Auto-extracted from {fname}"
                            }
                            existing_tags[tid] = new_tag
                            scraped_count += 1
            count += 1
        except Exception as e:
            print(f"Error reading {fname}: {e}")

    # 3. Convert back to list
    final_tags_list = list(existing_tags.values())
    INITIAL_DATA['tags'] = final_tags_list
    
    # 4. Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(INITIAL_DATA, f, sort_keys=False, indent=2)
        
    print(f"Processed {count} files.")
    print(f"Extracted {scraped_count} new tags.")
    print(f"Total tags: {len(final_tags_list)}")
    print(f"Written to {OUTPUT_FILE}")

if __name__ == "__main__":
    run_extraction()
