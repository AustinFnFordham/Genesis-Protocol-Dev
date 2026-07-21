
import os
import yaml
from pathlib import Path

DATA_DIR = Path("SW5e_Data_Hub/data/factions")

def cleanup():
    print("Cleaning up faction files...")
    count = 0
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".yml") or filename.endswith(".yaml"):
            filepath = DATA_DIR / filename
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                
                if data and "faction_raw_data" in data:
                    del data["faction_raw_data"]
                    with open(filepath, "w", encoding="utf-8") as f:
                        yaml.dump(data, f, sort_keys=False)
                    print(f"  [CLEAN] {filename}")
                    count += 1
            except Exception as e:
                print(f"  [ERROR] {filename}: {e}")
                
    print(f"Cleanup complete. Modified {count} files.")

if __name__ == "__main__":
    cleanup()
