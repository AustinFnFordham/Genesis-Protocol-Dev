"""Owner-proposed experimental resolution v1. No RNG or campaign mutation."""
import copy

VERSION = "genesis-experimental-resolution/1"
TEMPERATURES = ("regular", "heroic", "legendary")
DEFAULT = {"temperature": "regular", "narrative_consequences": False}


def settings(action):
    value = action.get("resolution_settings", DEFAULT)
    if not isinstance(value, dict) or set(value)-set(DEFAULT):
        raise ValueError("invalid resolution settings")
    result = {**DEFAULT, **value}
    if result["temperature"] not in TEMPERATURES or type(result["narrative_consequences"]) is not bool:
        raise ValueError("invalid resolution settings")
    return result


def effective(raw, temperature):
    if type(raw) is not int or not 1 <= raw <= 20 or temperature not in TEMPERATURES:
        raise ValueError("d20 face or temperature invalid")
    return raw if temperature == "regular" else 11+(raw-1)//2 if temperature == "heroic" else 16+(raw-1)//4


def degree(margin):
    if type(margin) is not int:
        raise ValueError("margin must be integer")
    return ("severe_failure" if margin <= -10 else "hard_failure" if margin <= -5 else
            "narrow_failure" if margin < 0 else "narrow_success" if margin < 5 else
            "strong_success" if margin < 10 else "exceptional_success")


def narrative(face):
    if type(face) is not int or not 1 <= face <= 6:
        raise ValueError("narrative d6 face invalid")
    return {"face": face, "advantage": max(0, face-4), "threat": max(0, 3-face) if face <= 2 else 0}


def resolve(raw_record, selected, kind, player_controlled, target=None, narrative_face=None):
    """Complete private resolution. Public serialization must use public_resolution.

    Ordinary dice fields remain raw and replay-compatible. Only the secondary
    effective-total field is used by the experimental adjudication lane.
    Critical semantics are attack-specific; checks/saves use total versus target.
    A domain rule may constrain eligibility before calling this resolver.
    """
    dice = raw_record["dice"]
    d20_terms = [d for d in dice if d["sides"] == 20]
    single_d20 = len(d20_terms) == 1 and d20_terms[0]["sign"] == 1 and len(d20_terms[0]["rolled"]) == 1
    eligible = (player_controlled is True and kind in ("check", "attack", "save") and
                single_d20)
    die = d20_terms[0] if eligible else None
    temperature = selected["temperature"] if eligible else "regular"
    raw = die["rolled"][0] if eligible else None
    transformed = effective(raw, temperature) if eligible else None
    total = raw_record["final_total"]+transformed-raw if eligible else raw_record["final_total"]
    if target is not None and type(target) is not int:
        raise ValueError("target must be integer or null")
    attack_face = d20_terms[0]["rolled"][0] if single_d20 and kind == "attack" else None
    auto_miss = attack_face == 1 and temperature == "regular"
    critical = attack_face == 20
    task = None
    if target is not None:
        margin = total-target
        success = critical or (not auto_miss and total >= target)
        task = {"result": "success" if success else "failure", "degree": degree(margin),
                "margin": margin, "target": target, "degree_basis": "numeric_margin_only",
                "mechanical_override": "original_20_attack_hit" if critical else "original_1_attack_miss" if auto_miss else None}
    axis = narrative(narrative_face) if eligible and selected["narrative_consequences"] and narrative_face is not None else None
    return {"schema": VERSION, "settings": copy.deepcopy(selected), "eligible": eligible, "kind": kind,
            "task": task, "narrative": axis, "causal": {"eligible_effects": [], "committed_effects": []},
            "roll": {"temperature": temperature, "raw_original": die.get("original") if eligible else None,
                     "raw_alternate": raw_record.get("alt_dice") if eligible else None,
                     "selected_raw_d20": raw, "effective_d20": transformed, "modifier": raw_record["modifiers"],
                     "other_dice_total": raw_record["raw_total"]-raw if eligible else raw_record["raw_total"],
                     "total": total, "attack_critical": critical, "automatic_attack_miss": auto_miss,
                     "critical_policy": "original_faces_attack_only/1"}}


def public_resolution(value):
    """Explicit allowlist. Hidden DC, margin, causal candidates and GM metadata stay private."""
    r = value["roll"]
    keys = ("selected_raw_d20", "effective_d20", "modifier", "other_dice_total", "total", "attack_critical", "automatic_attack_miss")
    if any(r.get(k) is not None and type(r[k]) not in (int, bool) for k in keys):
        raise ValueError("invalid public resolution numeric fields")
    faces = {}
    for key in ("raw_original", "raw_alternate"):
        x = r.get(key)
        if x is not None and (not isinstance(x, list) or any(type(n) is not int or not 1 <= n <= 20 for n in x)):
            raise ValueError("invalid original d20 faces")
        faces[key] = copy.deepcopy(x)
    return {"schema": VERSION, "settings": settings({"resolution_settings": value["settings"]}),
            "eligible": value["eligible"] is True, "kind": value["kind"] if value["kind"] in ("check", "attack", "save", "damage", "other") else "other",
            "roll": {**{key: r.get(key) for key in keys}, **faces,
                     "temperature": r["temperature"] if r["temperature"] in TEMPERATURES else "regular",
                     "critical_policy": "original_faces_attack_only/1"},
            "narrative": narrative(value["narrative"]["face"]) if value.get("narrative") else None}


def assess_causal(value, candidates, validate):
    """Chaos candidates require external domain validation; assessment never commits.

    No candidate generation, budget spending, implicit player actions, or automatic
    recruitment. Atomic must separately validate and append any selected effect.
    """
    out = copy.deepcopy(value)
    axis = out.get("narrative")
    eligible = []
    if axis:
        for candidate in candidates:
            if (isinstance(candidate, dict) and candidate.get("effect_id") and candidate.get("rule_source") and
                candidate.get("event_ids") and candidate.get("axis") in ("advantage", "threat") and
                type(candidate.get("cost")) is int and 0 < candidate["cost"] <= axis[candidate["axis"]] and
                validate(candidate) is True):
                eligible.append(copy.deepcopy(candidate))
    out["causal"] = {"eligible_effects": eligible, "committed_effects": []}
    return out
