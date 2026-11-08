#!/usr/bin/env python3
"""Aero's equipment for the turn context, derived from the record only (contract 3).

Source of truth, in order:
  1. the authoritative character sheet (api_bridge/gm/aero_character_runtime.yml: weapons, armor, inventory),
  2. committed public ledger events that change where an item is:
       equipment_change {item, to, where?, at?}      held | holstered | worn | stored | attached | transported | placed | dropped
       item_created     {id, label, state, where?, at?, made_from: [...], limits?}   only after the GM ruled it was made
       item_consumed / item_destroyed {item}
     and hand snapshots already committed by object interactions (details.hands).
Nothing here invents an item, a capacity or a weight: bulk/weight appear only when the sheet or an event states them.
An item whose state a later hand snapshot contradicts without an equipment_change becomes `uncertain`.
"""
import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]
SHEET = ROOT / "api_bridge" / "gm" / "aero_character_runtime.yml"
HAND_ALIASES = {"blaster_pistol": "blaster", "indigo_lightsaber": "lightsaber"}
STATES = {"held", "holstered", "worn", "stored", "attached", "transported", "placed", "dropped"}


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def from_sheet(sheet=None):
    doc = sheet or yaml.safe_load(SHEET.read_text(encoding="utf-8"))
    ch = doc.get("character_runtime") or doc.get("character") or doc
    eqp = (ch.get("equipment") or {}) if isinstance(ch, dict) else {}
    out = []
    for w in eqp.get("weapons") or []:
        name = w.get("name", "")
        if "Unarmed" in name:
            continue
        if "Lightsaber" in name:
            out.append({"id": "lightsaber", "label": "the indigo lightsaber", "state": "holstered", "home_state": "holstered", "home": w.get("carry", "hip"),
                        "where": w.get("carry", "hip"), "hands": 1, "active_when": "saber_ignited", "aliases": ["lightsaber", "saber", "blade"],
                        "established": ["energy blade, range 5 feet", "lit: light source"]})
        elif "Blaster" in name:
            out.append({"id": "blaster", "label": "the blaster pistol", "state": "holstered", "home_state": "holstered", "home": w.get("carry", "hip"),
                        "where": w.get("carry", "hip"), "hands": 1, "aliases": ["blaster", "pistol"]})
    arm = eqp.get("armor")
    if arm:
        out.append({"id": "robes", "label": "robes and synthweave mantle", "state": "worn", "fixed": True, "aliases": ["robes", "mantle"]})
    for it in eqp.get("inventory") or []:
        name = it.get("item", "")
        e = {"id": slug(name), "label": name[0].lower() + name[1:] if name else name, "state": "stored", "home_state": "stored", "home": "backpack",
             "where": "backpack", "quantity": it.get("quantity", 1), "note": it.get("exact_effect", ""), "aliases": [name.lower()]}
        if "glowrod" in name.lower():
            e.update(state="attached", home_state="attached", where="belt clip", home="belt clip")
        if name.lower() == "backpack":
            e.update(state="worn", home_state="worn", where="on Aero's back", home="on Aero's back", hands=2)
        if "syntherope" in name.lower() or "synthrope" in name.lower():
            e["aliases"] += ["synthrope", "syntherope", "rope"]
        out.append(e)
    return out


def apply_events(items, events):
    by = {e["id"]: e for e in items}
    for ev in events:
        d = ev.get("details") or {}
        k = ev.get("kind")
        if k == "equipment_change" and d.get("item") in by and d.get("to") in STATES:
            e = by[d["item"]]; e["state"] = d["to"]; e.pop("uncertain", None)
            for f in ("where", "at"):
                if d.get(f) is not None:
                    e[f] = d[f]
            e["evt"] = ev["event_id"]
        elif k == "item_created" and d.get("id"):
            e = {"id": d["id"], "label": d.get("label", d["id"]), "state": d.get("state", "placed"), "where": d.get("where", ""), "made_from": d.get("made_from", []),
                 "limits": d.get("limits", ""), "hands": d.get("hands", 1), "aliases": d.get("aliases", []), "evt": ev["event_id"], "improvised": True}
            if d.get("at"):
                e["at"] = d["at"]
            by[e["id"]] = e; items.append(e)
        elif k in ("item_consumed", "item_destroyed") and d.get("item") in by:
            items.remove(by.pop(d["item"]))
        elif isinstance(d.get("hands"), dict):
            held = set()
            for h in ("right", "left"):
                v = d["hands"].get(h)
                item = (v.get("item") if isinstance(v, dict) else v) if v else None
                item = HAND_ALIASES.get(item, item)
                if item in by:
                    by[item]["state"] = "held"; held.add(item); by[item].pop("uncertain", None)
            for e in items:
                if e["state"] == "held" and e["id"] not in held:
                    e["state"] = e.get("home_state", "stored"); e["uncertain"] = True
    return items


def derive(events, sheet=None):
    return apply_events(from_sheet(sheet), events)
