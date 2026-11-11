"""Derived player projections. Input must be public, effective ledger events only.
No inferred NPC intent, relationship score, or canonical writes.
"""
DIMENSIONS = ("trust", "respect", "fear", "reliance", "obligation", "affection")
SIGNIFICANT = {"world_event", "world_fact", "discovery", "observation", "scene_change",
               "objective_set", "objective_completed", "objective_failed", "ruling", "ruling_void"}


def project(events):
    if any(event["visibility"] == "gm_only" for event in events):
        raise ValueError("private event passed to player projection")
    turns, current = [], []
    def finish(group):
        kinds = {event["kind"] for event in group}
        if {"player_declaration", "gm_narration", "turn_context"} <= kinds:
            turns.append(group[:])
    for event in events:
        if event["kind"] == "player_declaration":
            finish(current)
            current = []
        current.append(event)
    finish(current)
    chapters = []
    for offset in range(0, len(turns)-4, 5):
        group = turns[offset:offset+5]
        references = [event["event_id"] for turn in group for event in turn
                      if event["kind"] in ("player_declaration", "gm_narration", "turn_context")]
        summaries = [next((event.get("details", {}).get("text") or event["summary"])[:280] for event in reversed(turn) if event["kind"] == "gm_narration")
                     for turn in group]
        chapters.append({"event_id": references[-1], "title": f"Turns {offset+1}–{offset+5}",
                         "text": " ".join(summaries), "sources": references, "derived": True})
    developments = [{"event_id": event["event_id"], "text": event["summary"],
                     "knowledge": event["knowledge_type"], "time": event["world_time"]}
                    for event in events if event["kind"] in SIGNIFICANT]
    objectives = {}
    for event in events:
        details = event.get("details", {})
        if event["kind"] == "objective_set" and details.get("id") and details.get("label"):
            objectives[details["id"]] = {"label": details["label"], "source": event["event_id"]}
        elif event["kind"] in ("objective_completed", "objective_failed"):
            objectives.pop(details.get("id"), None)
    return {"chapters": chapters, "events": developments,
            "objectives": [item["label"] for item in objectives.values()],
            "objective_sources": objectives, "completed_turns": len(turns)}

