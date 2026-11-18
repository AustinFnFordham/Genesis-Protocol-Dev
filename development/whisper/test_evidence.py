"""Algorithm A tests on CMP-001 (TB4-16, -17, -18, -19 + leak and retraction checks)."""
import copy, json, sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import evidence as A  # noqa: E402

fx = json.loads((H / "fixtures/cmp001_ten_missing_crates.json").read_text())
events = fx["events"]; before = copy.deepcopy(events)
envs = A.envelopes(events, fx["entities"])
assert events == before, "derivation never mutates accepted events"
assert all(x["type"] in A.TYPES and x["source_event"] for x in envs), "every envelope is typed and cites its event"
# TB4-16: heard by twelve, still a claim
truth = A.world_truth(envs)
assert not any(x["content"].get("subject") == "dockworker_1" and x["content"].get("predicate") == "took" for x in truth), "a claim never becomes a fact"
heard = A.knows(envs, "dockworker_7")
claims = [x for x in heard if x["type"] == "claim" and x["source_event"] == "evt_0003"]
assert len(claims) == 1 and claims[0]["provenance"] == "speaker:dockmaster_orren", "the listener holds a claim, attributed to its speaker"
# TB4-17: Neri was not present: no memory, no claim
assert A.knows(envs, "neri") == [], "an absent observer knows nothing of it"
# TB4-18: private emotion is not NPC knowledge, nor player-visible GM truth
for who in ("sera", "dockmaster_orren", "dockworker_3"):
    assert not any(x["type"] == "intention" for x in A.knows(envs, who)), "PC-private context never reaches an NPC"
player = A.retrieve(envs, "player")
assert any(x["type"] == "intention" for x in player), "the player sees their own private context"
assert not any(x["source_event"] == "evt_0002" for x in player), "GM-only truth never reaches the player view"
assert "smuggler_kesh" not in json.dumps(player), "no hidden name leaks through any player-visible field"
assert any(x["source_event"] == "evt_0002" for x in A.retrieve(envs, "gm")), "the GM sees everything"
# Kesh knows what he did (he is in known_to of the GM-only event) — but only as the GM lets him act on it
assert any(x["source_event"] == "evt_0002" for x in A.knows(envs, "smuggler_kesh"))
# retraction: Orren's claim is marked retracted for those who heard the retraction, kept for those who did not
for_aero = [x for x in A.retrieve(envs, ("pc", "aero"), types=["claim"]) if x["source_event"] == "evt_0003"]
assert for_aero and for_aero[0].get("retracted") is True, "Aero heard the retraction"
for_dw = [x for x in A.knows(envs, "dockworker_7") if x["type"] == "claim" and x["source_event"] == "evt_0003"]
assert not for_dw[0].get("retracted"), "dockworkers did not hear it: still an unretracted claim for them"
# TB4-19: ghost entity refused
ghost = copy.deepcopy(events); ghost[0]["details"]["subject"] = "crate_ghost"
try:
    A.envelopes(ghost, fx["entities"])
except A.Ghost:
    pass
else:
    raise AssertionError("unknown entity must be refused")
# determinism
assert A.retrieve(envs, "player") == A.retrieve(A.envelopes(events, fx["entities"]), "player")
print("evidence tests ok")
