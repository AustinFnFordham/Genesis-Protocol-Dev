"""Six equal-seed scripted scene workloads. Not a model or entertainment benchmark."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine
import policy
from fixtures import campaign_copy, action_for, request_for


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, engine.ROOT/relative)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


brief = load("comparison_brief", ".claude/skills/litrpg-process-turn/brief.py")
client = load("comparison_client", "development/interop/public_client.py")


def complete_turn(campaign, action_id, action, result, narrative_text, after_stream=None):
    events = engine.ledger.load_all(campaign)
    previous = engine.export_state.build(campaign_dir=campaign, campaign_id=action["campaign_id"])
    context = copy.deepcopy(previous["turn_context"])
    context.pop("context_id", None)
    number = events[-1]["turn_no"]+1
    def event(kind, text, details, visibility="player", causes=None, rolls=None):
        return {"session":1,"turn_no":number,"world_time":"Isolated experiment", "kind":kind,"summary":text,
                "actor":"aero","visibility":visibility,"knowledge_type":"fact","known_to":[],
                "caused_by":causes or [],"roll_ids":rolls or [],"details":details}
    public = policy.public_resolution(result["resolution"])
    drafts = [event("player_declaration", action["text"], {"action_id":action_id,"text":action["text"],
        "declaration":action["declaration"],"resolution_settings":policy.settings(action)}),
        event("skill_check", "Aero studies the remote's visible housing", {"skill":"technology","resolution":public},
              causes=["$1"],rolls=[result["roll"]["roll_id"]]),
        event("gm_ruling", "PRIVATE_RESOLUTION_CANARY", {"resolution":result["resolution"]}, "gm_only", ["$2"]),
        event("gm_narration", "Inspection ends at a player decision", {"text":narrative_text}, causes=["$2"]),
        event("turn_context", "The conditional pickup remains pending", context, causes=["$4"])]
    request = {"batch_id":action_id,"expected_revision":len(events),"expected_head":events[-1]["event_id"],"events":drafts}
    lease = campaign / "hidden/comparison_lease.json"
    lease.write_text(json.dumps({"holder":"comparison","expires_ms":time.time_ns()//1_000_000+60000}))
    outcome = engine.batch.apply(campaign, request, lease, "comparison", engine.ledger, after_stream=after_stream)
    assert engine.batch.apply(campaign, request, lease, "comparison", engine.ledger) == outcome
    return engine.export_state.build(campaign_dir=campaign, campaign_id=action["campaign_id"])


def run():
    qa = engine.ROOT / "development/.qa"
    qa.mkdir(exist_ok=True)
    reports, baselines = [], []
    for temperature in policy.TEMPERATURES:
        for enabled in (False, True):
            with tempfile.TemporaryDirectory(dir=qa) as root:
                campaign = campaign_copy(root)
                mechanical = 0
                axes = {"advantage":0,"threat":0,"neutral":0,"off":0}
                raw_faces, latencies, retrieval_ms, settings_seen = [], [], [], []
                for scene in range(6):
                    start = time.perf_counter()
                    action = action_for(campaign, temperature, enabled)
                    entry = {"id":action["campaign_id"],"path":campaign,"dir":str(campaign.relative_to(engine.ROOT))}
                    get = time.perf_counter()
                    _, bundle = brief.build(entry, action=action)
                    compact = brief.compact(bundle)
                    retrieval_ms.append((time.perf_counter()-get)*1000)
                    result = engine.execute(campaign, f"equal-scene-{scene}", action, request_for())
                    resolution = policy.assess_causal(result["resolution"], [], lambda _: False)
                    mechanical += resolution["task"]["result"] == "success"
                    axis = resolution["narrative"]
                    axes["off" if axis is None else "advantage" if axis["advantage"] else "threat" if axis["threat"] else "neutral"] += 1
                    raw_faces.append(resolution["roll"]["selected_raw_d20"])
                    # Authored mechanical test fixture, not a claim about hidden sim truth.
                    narration = "You finish studying the remote's exterior. The inspection does not operate the device or authorize the pending pickup. Your next decision is still yours."
                    state = complete_turn(campaign, f"equal-scene-{scene}", action, result, narration)
                    documents = engine.export_state.publish_set(state)
                    refreshed = client.refresh(campaign, action["campaign_id"])
                    for value in (documents, refreshed, brief.build(entry, audience="player")[1]):
                        text = json.dumps(value)
                        assert "PRIVATE_RESOLUTION_CANARY" not in text and '"target"' not in json.dumps(value.get("rolls",[]))
                    assert state["turn_context"]["pending_steps"] == engine.export_state.build(campaign_dir=campaign)["turn_context"]["pending_steps"]
                    settings_seen.append(compact["submitted_resolution_settings"])
                    latencies.append((time.perf_counter()-start)*1000)
                assert engine.replay(campaign)["ok"]
                baselines.append(raw_faces)
                reports.append({"temperature":temperature,"narrative_consequences":enabled,"scenes":6,"mechanical_successes":mechanical,
                    "narrative_outcomes":axes,"eligible_effects":0,"committed_effects":0,"decision_points":6,
                    "public_revision":state["revision"],"public_scene_progression":"six completed public inspection turns; pending pickup preserved",
                    "local_total_ms":round(sum(latencies),2),"context_retrieval_ms":round(sum(retrieval_ms),2),
                    "model_calls":0,"tokens":None,"publication":"local document generation only","snapshot_bytes":engine.export_state.doc_bytes(documents["state"])})
    assert all(faces == baselines[0] for faces in baselines)
    return {"same_ordinary_draws_across_all_six":True,"seed_exported":False,"workloads":reports,
        "limits":"Scripted diagnostic workloads, not remote staging, model-latency or entertainment quality evidence. Private margins and targets omitted."}


if __name__ == "__main__":
    report = run()
    (engine.ROOT/"development/.qa/resolution_comparison.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
