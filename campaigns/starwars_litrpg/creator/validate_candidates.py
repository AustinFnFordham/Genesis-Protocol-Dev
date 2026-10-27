#!/usr/bin/env python3
"""Validate Forge candidate records and golden_slice YAML against schema/*.schema.json.

Resolves cross-file $refs (e.g. Background -> CharacterClassFeature.schema.json) from the schema folder.
Usage: python3 -I validate_candidates.py [--json out.json]
"""
import argparse, glob, json, sys
from pathlib import Path
import jsonschema, yaml
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = {p.name: json.loads(p.read_text()) for p in (ROOT / "schema").glob("*.schema.json")}
REG = Registry().with_resources([(n, Resource.from_contents(s, default_specification=DRAFT7)) for n, s in SCHEMAS.items()])
CB = ROOT / "registry" / "candidate_builds"
SETS = {
    "species":   (CB / "cand_species_f0919a09ca17ebcf" / "draft", "Species"),
    "class":     (CB / "cand_classes_861acd817b14421e" / "draft", "Class"),
    "validated": (CB / "cand_classes_861acd817b14421e" / "validated_candidate", None),  # Class or Subclass by kind
    "background":(CB / "cand_backgrounds_516841038a6595a7" / "draft", "Background"),
}
GOLD = ROOT / "registry" / "golden_slice" / "global_definitions"

def check(record, schema_name):
    v = jsonschema.Draft7Validator(SCHEMAS[f"{schema_name}.schema.json"], registry=REG)
    return sorted({f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message[:90]}" for e in v.iter_errors(record)})

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--json"); a = ap.parse_args()
    out = {}
    for name, (d, schema) in SETS.items():
        for f in sorted(d.glob("*.json")):
            j = json.loads(f.read_text()); r = j.get("record", j)
            s = schema or ("Subclass" if "class_id" in r else "Class")
            out[f"{name}/{f.stem}"] = {"schema": s, "errors": check(r, s)}
    for f in sorted(GOLD.glob("*.yml")):
        r = yaml.safe_load(f.read_text())
        kind = f.stem.split("_")[0]
        s = {"species": "Species", "class": "Class", "subclass": "Subclass", "background": "Background"}.get(kind)
        if s:
            out[f"golden/{f.stem}"] = {"schema": s, "errors": check(r.get("record", r) if isinstance(r, dict) else r, s)}
    if a.json: Path(a.json).write_text(json.dumps(out, indent=1))
    for grp in sorted({k.split("/")[0] for k in out}):
        items = {k: v for k, v in out.items() if k.startswith(grp + "/")}
        ok = sum(1 for v in items.values() if not v["errors"])
        print(f"{grp}: {ok}/{len(items)} valid")
    return out

if __name__ == "__main__":
    main()
