
import os
import yaml
from pathlib import Path

# Directories to scan
DIRS = [
    Path("SW5e_Data_Hub/data/species"),
    Path("SW5e_Data_Hub/data/classes"),
    Path("SW5e_Data_Hub/data/backgrounds"),
    Path("SW5e_Data_Hub/data/factions")
]

def scrub_tags():
    print("Scrubbing 'platinum' tag from files...")
    count = 0
    total_files = 0
    
    for d in DIRS:
        if not d.exists():
            continue
            
        for root, _, files in os.walk(d):
            for filename in files:
                if filename.endswith(".yml") or filename.endswith(".yaml"):
                    filepath = Path(root) / filename
                    total_files += 1
                    
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f)
                        
                        modified = False
                        if data and "tags" in data and isinstance(data["tags"], list):
                            if "platinum" in data["tags"]:
                                data["tags"].remove("platinum")
                                modified = True
                        
                        if modified:
                            with open(filepath, "w", encoding="utf-8") as f:
                                yaml.dump(data, f, sort_keys=False)
                            print(f"  [CLEAN] {filename}")
                            count += 1
                    except Exception as e:
                        print(f"  [ERROR] {filename}: {e}")
                
    print(f"\nScrub complete. Removed 'platinum' tag from {count} files (out of {total_files} scanned).")

if __name__ == "__main__":
    scrub_tags()
