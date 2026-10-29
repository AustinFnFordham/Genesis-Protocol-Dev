#!/usr/bin/env python3
"""Regenerate the status tables in CREATOR_SHORTLIST_*.md. Usage: python3 -I shortlist_status.py"""
import json, sys, yaml
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import validate_candidates as V
CB = V.CB
SP = CB/"cand_species_f0919a09ca17ebcf/draft"; CL = CB/"cand_classes_861acd817b14421e"; BG = CB/"cand_backgrounds_516841038a6595a7/draft"
PICKS = {
 "Species": [(n, SP/f"{n}.json") for n in "human twilek zabrak wookiee echani chiss togruta miraluka cathar bothan".split()],
 "Class": [(n, CL/f"validated_candidate/{n}.json") for n in "guardian sentinel consular soldier scout scoundrel smuggler bounty_hunter engineer spy".split()],
 "Subclass": [("sentry", None)] + [(n, CL/f"draft/{n}.json") for n in "guardian_force_warrior soresu_defender niman_disciple sage assassin survivalist mercenary_soldier slicer fringer".split()],
 "Background": [(n, BG/f"background_{n}.json") for n in "jedi soldier smuggler scoundrel outlaw bounty_hunter scholar explorer mechanic diplomat".split()],
}
out = ["# Creator shortlist (2026-10-27, status refreshed by shortlist_status.py)", "",
       "Era: hidden (GM-chosen). Picks are era-neutral. Status = schema validation with envelope stripped and cross-file refs resolved.", ""]
for kind, items in PICKS.items():
    out += [f"## {kind}", "", "| Pick | Status | Missing required | Other errors |", "|---|---|---|---|"]
    for n, p in items:
        r = yaml.safe_load((V.GOLD/f"subclass_{n}.yml").read_text()) if p is None else json.loads(p.read_text()).get("record")
        errs = V.check(r, kind)
        req = [e.split("'")[1] for e in errs if e.startswith("(root)") and "required property" in e]
        other = len(errs) - len(req)
        out.append(f"| {n} | {'PASS' if not errs else 'gaps'} | {', '.join(req) or '-'} | {other} |")
    out.append("")
out += ["Variants kept with parent species: `zabrak_dathomirian`, `togruta_nightsister`.", "",
        "## Structural findings", "1. ~~Class schema required `level_progression`~~ Fixed 2026-10-29: `progression_tree` added, one of the two is required.",
        "2. Golden-slice records use `urid` + an envelope instead of `id`. Rule proposed: `urid = <entity_type>_<id>`, derived, never hand-written.",
        "3. The 63 class drafts are specializations (`class_id` parent) mislabeled `kind: class`. Target schema is Subclass.",
        "4. Backgrounds embed a `feature` that must satisfy CharacterClassFeature; all drafts are lighter than required.",
        "5. Era is almost never set on species."]
(Path(__file__).parent/"CREATOR_SHORTLIST_2026-10-27.md").write_text("\n".join(out)+"\n")
print("\n".join(l for l in out if l.startswith("|") and ("PASS" in l)))
