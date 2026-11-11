#!/usr/bin/env python3
"""Isolated Campaign Genesis draft builder. Never promotes content or edits runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

RELATIONSHIPS = {"synergy", "antagonism", "inhibition", "catalysis", "dependency", "consumption", "production",
                 "conversion", "resistance", "vulnerability", "amplification", "suppression", "containment",
                 "contamination", "compatibility", "incompatibility", "trigger", "counter"}


def foundation(request, registry, before_fall=None, source_manifest=None):
    if not isinstance(request.get("era"), str) or not request["era"].strip():
        raise ValueError("select an era")
    if not isinstance(request.get("preferences"), dict) or not isinstance(request.get("worldbuilding"), dict):
        raise ValueError("campaign preferences and worldbuilding choices are required")
    ids = request.get("entities", [])
    if not isinstance(ids, list) or len(set(ids)) != len(ids) or len(ids) < 2:
        raise ValueError("select at least two distinct canonical endpoints")
    with sqlite3.connect(Path(registry).resolve().as_uri() + "?mode=ro", uri=True) as db:
        entities = {}
        for entity_id in ids:
            record = db.execute("SELECT proposed_urid,entity_name,entity_type,source_pointer,authority_lane FROM canonical WHERE proposed_urid=?", (entity_id,)).fetchone()
            if not record:
                raise ValueError("unresolved canonical endpoint: " + entity_id)
            entities[entity_id] = dict(zip(("id", "name", "type", "source", "authority"), record))
    connections = request.get("connections", [])
    if not isinstance(connections, list) or not connections:
        raise ValueError("select causal relationship templates")
    edges = []
    neighbours = {key: set() for key in ids}
    for index, template in enumerate(connections):
        source, target, relation = template.get("source"), template.get("target"), template.get("type")
        if source not in entities or target not in entities or source == target or relation not in RELATIONSHIPS:
            raise ValueError("Chaos connection requires resolved, distinct endpoints and a known type")
        if not isinstance(template.get("condition"), str) or not template["condition"].strip():
            raise ValueError("future possibilities need an explicit condition")
        if "mandatory_outcome" in template or "canonical" in template:
            raise ValueError("draft composition cannot dictate or canonize outcomes")
        neighbours[source].add(target)
        neighbours[target].add(source)
        edges.append({"id": "candidate_edge_" + str(index+1), "source": source, "target": target, "type": relation,
                      "condition": template["condition"], "status": "candidate", "authority": "Chaos",
                      "provenance": "player-selected campaign foundation"})
    reached, frontier = set(), [ids[0]]
    while frontier:
        entity = frontier.pop()
        if entity not in reached:
            reached.add(entity)
            frontier.extend(neighbours[entity] - reached)
    if reached != set(ids):
        raise ValueError("campaign foundation has disconnected endpoints")
    chronicle = {"mode": "disabled"}
    if request.get("before_the_fall"):
        if before_fall is None:
            raise ValueError("Before the Fall mode requires the original rules document; no substitute algorithm is generated")
        raw = Path(before_fall).read_bytes()
        pinned = source_manifest or json.loads(Path(__file__).with_name("before_fall_source.json").read_text())
        actual_hash = hashlib.sha256(raw).hexdigest()
        if pinned.get("source", {}).get("sha256") != actual_hash:
            raise ValueError("Before the Fall rules differ from the pinned original source")
        chronicle = {"mode": "original_rules_passthrough", "source": str(before_fall),
                     "sha256": actual_hash, "mechanics_modified": False,
                     "source_identity": pinned["source"]}
    return {"schema": "campaign-genesis-draft/1", "status": "proposed", "era": request["era"],
            "era_certification": "requires source validation", "preferences": request["preferences"],
            "worldbuilding": request["worldbuilding"], "entities": list(entities.values()), "relationships": edges,
            "chronology": chronicle, "promotion": "requires rules, lore, chronology and authority review",
            "design": {"SID-Q15": "provisional", "SID-Q16": "provisional"}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path); parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--before-fall-rules", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(foundation(json.loads(args.request.read_text()), args.registry, args.before_fall_rules), indent=2))
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(3, str(error)+"\n")
