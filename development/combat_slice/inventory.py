"""Read-only inventory of the existing maneuver drafts (CC-002 §9). Prints a markdown table; changes nothing.
python3 development/combat_slice/inventory.py"""
import glob, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "registry/candidate_builds/cand_powers_541b498235e0dfc6"
USED = {"power_feinting_attack": "reworked → feint (contest, no superiority die)", "power_riposte": "reworked → riposte (Reaction on a missed melee attack)",
        "power_disarming_blow": "reworked → blade_bind (contest; no damage)", "power_parry": "reworked → parry (+2 AC, no superiority die)"}
VALID_POWER_TYPES = {"Force", "Tech"}   # Power.schema.json power_type values used by promoted powers (Maneuver is not one)


def rows():
    out = []
    for f in sorted(glob.glob(str(D / "draft/power_*.json"))):
        d = json.load(open(f)); r = d.get("record", d); v = d.get("validation", {})
        tags = r.get("tags") or []
        text = json.dumps(r).lower()
        out.append({"id": r.get("id"), "type": r.get("power_type"), "time": r.get("casting_time"),
                    "superiority": "superiority" in tags or "superiority die" in text,
                    "starship": any(k in text for k in ("starship", "squadron", "shield", "flyby", "full speed")),
                    "errors": len(v.get("errors") or []), "slice": USED.get(r.get("id"), "")})
    return out


if __name__ == "__main__":
    schema = json.loads((ROOT / "schema/Power.schema.json").read_text())
    enum = schema.get("properties", {}).get("power_type", {}).get("enum")
    rs = rows()
    print(f"Power.schema.json power_type enum: {enum}\n")
    print("| Draft | power_type | Casting time | Needs superiority dice | Starship-scale | Validation errors | Used in slice |")
    print("|---|---|---|---|---|---|---|")
    for r in rs:
        if r["type"] != "Maneuver": continue
        print(f"| `{r['id']}` | {r['type']} | {r['time']} | {'yes' if r['superiority'] else ''} | {'yes' if r['starship'] else ''} | {r['errors']} | {r['slice']} |")
    q = json.load(open(D / "quarantine/maneuvers_comprehensive.json"))
    print(f"\nQuarantined catalog `maneuvers_comprehensive`: errors {q['validation'].get('errors')}")
