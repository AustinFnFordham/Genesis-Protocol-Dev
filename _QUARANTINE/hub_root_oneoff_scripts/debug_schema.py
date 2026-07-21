import json
import yaml
import jsonschema
import os

def load(path):
    if path.endswith(".yml"):
        return yaml.safe_load(open(path, 'r', encoding='utf-8'))
    return json.load(open(path, 'r', encoding='utf-8'))

schema = load(r"e:\StarWars\SW5e_Data_Hub\SW5e_Data_Hub\schema\Faction_Core.schema.json")
candidate = load(r"e:\StarWars\SW5e_Data_Hub\logs\forge\fac_black_sun\final_fail_candidate.yml")

with open("debug_out.txt", "w", encoding="utf-8") as out:
    try:
        cult_schema_props = schema['properties']['essence']['properties']['culture']['properties']
        out.write(f"SCHEMA EXPECTS: {list(cult_schema_props.keys())}\n")
    except KeyError as e:
        out.write(f"SCHEMA MISSING PATH: {e}\n")

    try:
        cult_cand_keys = candidate['essence']['culture'].keys()
        out.write(f"CANDIDATE HAS: {list(cult_cand_keys)}\n")
    except KeyError as e:
        out.write(f"CANDIDATE MISSING PATH: {e}\n")
    
    out.write("\nValidating...\n")
    try:
        jsonschema.validate(instance=candidate, schema=schema)
        out.write("SUCCESS\n")
    except Exception as e:
        out.write(f"FAIL: {e}\n")
        # Inspect
        v = jsonschema.Draft7Validator(schema)
        for err in v.iter_errors(candidate):
            out.write("\n--- ERROR ---\n")
            out.write(f"Path: {list(err.path)}\n")
            out.write(f"Message: {err.message}\n")
            out.write(f"Validator: {err.validator}\n")
            out.write(f"Schema Path: {list(err.schema_path)}\n")
