#!/usr/bin/env python3
"""Build the player-visible UI state document from the ledger + Aero's sheet.

Output: JSON for the Artifact db doc `view/state`. Derived ONLY from the public
ledger file (records/events.jsonl, via the ledger's own player_view) and the
player-visible character runtime. Never reads hidden/. The artifact mirrors this;
it never writes it. Usage: export_state.py [--out FILE]
"""
import argparse, json, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "api_bridge"))
import litrpg_adapter as la  # noqa: E402

SHEET = ROOT / "api_bridge" / "gm" / "aero_character_runtime.yml"
NON_JOURNAL = {"gm_narration", "scene_state", "gm_suggestions", "player_declaration"}


def build():
    ev = la.player_events()
    sheet = yaml.safe_load(SHEET.read_text(encoding="utf-8"))["character_runtime"]
    idn, dfn, res, mov = sheet["identity"], sheet["defenses"], sheet["resources"], sheet["movement"]
    ab = sheet["abilities"]
    scene = next((e["details"] for e in reversed(ev) if e["kind"] == "scene_state"), {})
    sugg = next((e["details"].get("items", []) for e in reversed(ev) if e["kind"] == "gm_suggestions"), [])
    last = ev[-1] if ev else {}
    feed = []
    for e in ev:
        if e["kind"] == "gm_narration":
            feed.append({"who": "gm", "event_id": e["event_id"], "time": e["world_time"], "text": e["details"].get("text", e["summary"])})
        elif e["kind"] == "player_declaration":
            feed.append({"who": "player", "event_id": e["event_id"], "time": e["world_time"], "text": e["details"].get("text", e["summary"])})
    journal = [{"event_id": e["event_id"], "time": e["world_time"], "kind": e["kind"],
                "knowledge": e["knowledge_type"], "text": e["summary"]} for e in ev if e["kind"] not in NON_JOURNAL]
    skills = [{"name": k.replace("_", " "), "mod": v["modifier"]} for k, v in sheet["proficiencies"]["skills"].items()]
    return {
        "revision": len(ev), "ledger_head": last.get("event_id"), "turn_no": last.get("turn_no", 0),
        "scene": {"title": scene.get("title"), "location": scene.get("location"), "time": last.get("world_time"),
                  "atmosphere": scene.get("atmosphere", [])},
        "feed": feed, "journal": journal, "suggestions": sugg, "objectives": [],
        "party": [{"name": 'Aeleron "Aero" Do\'ordo', "role": "You", "status": "Active"}],
        "character": {
            "name": idn["name"], "line": f'{idn["species"]} {idn["class"]} · {idn["background"]} · {idn["current_rank"]}',
            "level": idn["level"],
            "hp": [dfn["current_hp"], dfn["maximum_hp"]], "strain": [dfn["current_strain"], dfn["maximum_strain"]],
            "force": [res["current_force_points"], res["maximum_force_points"]],
            "ac": dfn["armor_class"], "speed": mov["speed"], "initiative": mov["initiative"],
            "scores": {k[:3].upper(): [v, ab["modifiers"][k]] for k, v in ab["scores"].items()},
            "passive": {"perception": sheet["senses"]["passive_perception"], "insight": sheet["senses"]["passive_insight"]},
            "conditions": dfn.get("conditions", []), "skills": skills,
            "languages": sheet["proficiencies"]["languages"],
            "powers": [{"name": p["name"], "cost": p["cost"], "effect": p["exact_effect"]} for p in sheet["powers"]],
            "features": [{"name": f["name"], "kind": f["action_type"],
                          "effect": f["exact_effect"] if isinstance(f["exact_effect"], str) else " ".join(map(str, f["exact_effect"].values() if isinstance(f["exact_effect"], dict) else f["exact_effect"]))}
                         for f in sheet["features"]],
            "weapons": [{"name": w["name"], "attack": w["attack_bonus"],
                         "damage": w["damage"] if isinstance(w["damage"], str) else " / ".join(f"{v}" for v in w["damage"].values())}
                        for w in sheet["equipment"]["weapons"]],
            "armor": {"name": sheet["equipment"]["armor"]["name"], "ac": sheet["equipment"]["armor"]["resulting_ac"]},
            "inventory": [{"item": i["item"], "qty": i["quantity"]} for i in sheet["equipment"]["inventory"]],
            "credits": sheet["equipment"]["credits"],
        },
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out")
    a = ap.parse_args()
    out = json.dumps(build(), ensure_ascii=False, indent=1)
    Path(a.out).write_text(out, encoding="utf-8") if a.out else print(out)
