"""Algorithm C tests (TB4-19, -20, -21, -22; CIS-001 §4 and §5 cases)."""
import copy, json, sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import causal as C  # noqa: E402

fx = json.loads((H / "fixtures/causal_fixture.json").read_text())
snap = {"relationships": fx["relationships"], "facts": fx["facts"]}
rules = fx["rules"]
frozen = copy.deepcopy((snap, rules))
C.check_graph(fx["relationships"], fx["entities"])
for bad in ({"source": "wick", "type": "trusts", "target": "ghost"}, {"source": "wick", "type": "loves", "target": "aero"}):
    try:
        C.check_graph(fx["relationships"] + [bad], fx["entities"])
    except C.Refused:
        pass
    else:
        raise AssertionError("TB4-19 ghost edge or unregistered relation accepted")

cruel = {"event_id": "evt_0900", "kind": "attack_resolved", "accepted": True, "actor": "aero", "known_to": ["aero", "wick", "mira"],
         "details": {"attacker": "aero", "target": "thug", "moral_finding": "unjustified_harm"}}
r = C.resolve(cruel, snap, rules)
assert [p["target"] for p in r["proposals"] if p["rule_id"] == "rule_companion_moral_reassessment"] == ["wick"], r
assert any(n["binding"].get("observer") == "mira" and n["failed"][0]["predicate"] == "observer_holds_relevant_conviction" for n in r["no_effect"]), "mira has no conviction: no effect, with reason"
assert any("forbidden domain write" in x["reason"] for x in r["rejected"]), "spawn_nemesis is not a transition the domain owns"
assert not any(p["rule_id"] == "rule_unratified" for p in r["proposals"]), "unratified (status candidate) rules never fire"
assert all(p["commits"] is False and p["status"] == "proposed" for p in r["proposals"])
# no witness / rumor-free: nobody saw it
unseen = dict(cruel, event_id="evt_0901", known_to=["aero"])
assert not [p for p in C.resolve(unseen, snap, rules)["proposals"] if p["rule_id"] == "rule_companion_moral_reassessment"], "no witness, no reassessment"
# TB4-20 predicates lacking: no GM moral finding -> no effect with the reason
plain = dict(cruel, event_id="evt_0902", details={"attacker": "aero", "target": "thug"})
r2 = C.resolve(plain, snap, rules)
assert not [p for p in r2["proposals"] if p["rule_id"] == "rule_companion_moral_reassessment"]
assert any(f["predicate"] == "ruled_morally_salient" for n in r2["no_effect"] for f in n["failed"]), r2
# TB4-22 duplicate delivery: same key, never twice
keys = [p["idempotency_key"] for p in r["proposals"]]
again = C.resolve(cruel, snap, rules, applied_keys=keys)
assert again["proposals"] == [] and all(f["predicate"] == "idempotency" for n in again["no_effect"] if n["rule_id"] == "rule_companion_moral_reassessment" and n["binding"].get("observer") == "wick" for f in n["failed"])
assert C.resolve(cruel, snap, rules) == r, "deterministic"
# §5 barrel: ignition proposes ignite; burning alone never implies explosion
fire = {"event_id": "evt_0910", "kind": "fire_exposure", "accepted": True, "actor": "gm", "known_to": [], "details": {"target": "barrel_2", "ignition": True}}
assert [p["requested_transition"] for p in C.resolve(fire, snap, rules)["proposals"]] == ["ignite"]
nosrc = dict(fire, event_id="evt_0911", details={"target": "barrel_2", "ignition": False})
assert C.resolve(nosrc, snap, rules)["proposals"] == [], "flammable but no source"
burning_open = {"event_id": "evt_0912", "kind": "status_burning", "accepted": True, "actor": "gm", "known_to": [], "details": {"target": "barrel_2"}}
snap_b = copy.deepcopy(snap); snap_b["facts"]["barrel_2"]["burning"] = True
assert C.resolve(burning_open, snap_b, rules)["proposals"] == [], "burning but open, water inside: no pressure failure"
snap_c = copy.deepcopy(snap); snap_c["facts"]["barrel_1"]["burning"] = True
sealed = dict(burning_open, event_id="evt_0913", details={"target": "barrel_1"})
assert [p["requested_transition"] for p in C.resolve(sealed, snap_c, rules)["proposals"]] == ["evaluate_pressure_failure"], "only an evaluation is proposed, never an explosion"
# TB4-21 no propagation from a proposal: the ignite proposal is not an accepted burning status
proposal_as_event = {"event_id": "prop_1", "kind": "status_burning", "accepted": False, "details": {"target": "barrel_1"}}
assert C.resolve(proposal_as_event, snap_c, rules)["proposals"] == [], "chains wait for acceptance"
# suppression excludes
snap_s = copy.deepcopy(snap); snap_s["facts"]["barrel_2"]["suppressed"] = True
assert C.resolve(fire, snap_s, rules)["proposals"] == []
# bounded
try:
    C.resolve(cruel, snap, rules, depth=C.MAX_DEPTH + 1)
except C.Refused:
    pass
else:
    raise AssertionError("depth bound")
assert (snap, rules) == frozen, "inputs never mutated"
print("causal tests ok")
