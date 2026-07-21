
import json
import os
from pathlib import Path
from collections import Counter

FACTIONS_DIR = Path("SW5e_Data_Hub/data/factions")
EXPANSIONS_DIR = Path("SW5e_Data_Hub/data/faction_expansions")
REPORT_PATH = Path("audit_report.md")

def audit():
    print("Auditing migrated factions...")
    
    total_factions = 0
    todo_ids = 0
    todo_descriptions = 0
    tag_counts = Counter()
    era_counts = Counter()
    missing_expansions = 0
    
    report_lines = []
    report_lines.append("# Faction Migration Audit Report")
    report_lines.append("")
    report_lines.append("| Metric | Count |")
    report_lines.append("|---|---|")
    
    warnings = []

    for filename in os.listdir(FACTIONS_DIR):
        if not filename.endswith(".json") or filename.startswith("faction_core"): continue
        
        filepath = FACTIONS_DIR / filename
        total_factions += 1
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Check ID
        if "todo" in data["id"]:
            todo_ids += 1
            warnings.append(f"- **ID Warning**: `{data['id']}` contains 'todo'")
            
        # Check Description
        if data["soul"]["description"] == "No description provided.":
            todo_descriptions += 1
            
        # Count Tags
        for t in data["tags"]:
            tag_counts[t] += 1
            
        # Count Eras
        for e in data["era"]:
            era_counts[e] += 1
            
        # Check Expansion Existence
        exp_filename = filename.replace(".json", ".expansion.json")
        exp_path = EXPANSIONS_DIR / exp_filename
        if not exp_path.exists():
            missing_expansions += 1
            warnings.append(f"- **Expansion Missing**: `{exp_filename}` for `{filename}`")

    # Summary Stats
    report_lines.append(f"| Total Factions | {total_factions} |")
    report_lines.append(f"| Placeholder IDs | {todo_ids} |")
    report_lines.append(f"| Missing Descriptions | {todo_descriptions} |")
    report_lines.append(f"| Missing Expansions | {missing_expansions} |")
    
    report_lines.append("")
    report_lines.append("## Tag Distribution")
    for tag, count in tag_counts.most_common(10):
        report_lines.append(f"- {tag}: {count}")

    report_lines.append("")
    report_lines.append("## Era Distribution")
    for era, count in era_counts.most_common():
        report_lines.append(f"- {era}: {count}")
        
    report_lines.append("")
    report_lines.append("## Warnings")
    if warnings:
        report_lines.extend(warnings)
    else:
        report_lines.append("No specific warnings found.")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"Audit complete. Report written to {REPORT_PATH}")

if __name__ == "__main__":
    audit()
