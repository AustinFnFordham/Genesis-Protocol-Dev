"""WHISPER post-turn review (owner decisions 1–2): candidates, answers, history, long-term only on repetition."""
import copy, json, sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import post_turn as P  # noqa: E402

cases = json.loads((H / "fixtures/tb4_moral_001.json").read_text())["cases"]
rescue = cases["failed_rescue"]
r = P.propose(rescue, [])
assert r and r["canonical"] is False and r["candidates"][0]["theme"] == "loss_after_trying", r
c = r["candidates"][0]
assert c["evidence"] == ["evt_0202"] and "save Wick" in c["explanation"] and c["uses_player_context"] == ["motive"]
assert P.propose(cases["anger_spares"], []) is None, "no outcome, not consequential: no review"
harm = P.propose(cases["attempted_harm_missed"], [])
assert harm["candidates"][0]["kind"] == "prompt" and harm["candidates"][0]["proposed"] is None, "no moral verdict; the player answers in his own words"
# answers
rev = {"event_id": "evt_0900", "kind": P.REVIEW, "details": r}
for bad in [("accept", None, harm and None)]:
    pass
try:
    P.response(rev, c["candidate_id"], "edit", "  ")
except ValueError:
    pass
else:
    raise AssertionError("edit needs words")
try:
    P.response({"event_id": "evt_0901", "kind": P.REVIEW, "details": harm}, harm["candidates"][0]["candidate_id"], "accept")
except ValueError:
    pass
else:
    raise AssertionError("a prompt cannot be accepted blindly")
acc = P.response(rev, c["candidate_id"], "accept")
assert acc["text"] == c["proposed"] and acc["source"] == "player_explicit" and acc["visibility"] == "pc_private"
custom = P.response(rev, None, "custom", "Numb. He keeps moving because stopping means thinking.")
assert custom["candidate_id"] is None and custom["theme"] == "custom"
# history and pending
ev = [dict(e) for e in rescue] + [{"event_id": "evt_0900", "kind": P.REVIEW, "details": r}]
assert P.pending(ev)["review_id"] == "evt_0900"
ev_def = ev + [{"event_id": "evt_0901", "kind": P.RESPONSE, "details": P.response(rev, c["candidate_id"], "defer")}]
assert P.pending(ev_def) is not None and P.history(ev_def) == [], "defer keeps it open and records nothing in history"
ev_rej = ev + [{"event_id": "evt_0902", "kind": P.RESPONSE, "details": P.response(rev, c["candidate_id"], "reject")}]
assert P.pending(ev_rej) is None and P.history(ev_rej) == [], "reject closes it; nothing enters history"
ev_acc = ev + [{"event_id": "evt_0903", "kind": P.RESPONSE, "details": acc}]
h = P.history(ev_acc)
assert len(h) == 1 and h[0]["player_confirmed"] and h[0]["sources"] == ["evt_0202"] and h[0]["kind"] == "temporary"
# long-term: only after two confirmed experiences of the same theme, and still only a candidate
prior = []
for i in range(2):
    prior += [{"event_id": f"evt_09{i}0", "kind": P.RESPONSE, "details": dict(acc, review_id=f"evt_08{i}0")}]
lt = P.propose(rescue, prior)
kinds = [x["kind"] for x in lt["candidates"]]
assert kinds == ["temporary", "long_term"] and lt["candidates"][1]["evidence"][:2] == ["evt_0900", "evt_0910"], lt
assert P.propose(rescue, prior[:1])["candidates"][-1]["kind"] == "temporary", "one confirmation is not a pattern"
def numbers(o):
    if isinstance(o, bool): return []
    if isinstance(o, (int, float)): return [o]
    if isinstance(o, dict): return [n for v in o.values() for n in numbers(v)]
    if isinstance(o, list): return [n for v in o for n in numbers(v)]
    return []
assert numbers(lt) == [], "no scores"
print("post-turn tests ok")
