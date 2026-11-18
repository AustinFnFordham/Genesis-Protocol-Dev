"""Algorithm C — typed causal dependency resolution (TB4-WHISPER-001 §4.C; CIS-001 as a *proposal*). Pure, read-only.

accepted event -> rules eligible by event type -> predicate filtering (with a trace) -> owning-domain proposal ->
dependency order -> authority/invariant checks -> proposals for the existing gateway. Nothing is committed here and no
second ledger exists: callers hand accepted proposals to the gateway like any other GM proposal.

Rules: a relationship or tag can make a rule *eligible*; only predicates over accepted facts make it *apply*. Missing
evidence is an explicit no-effect with the failed predicates. A proposal never triggers further rules until it has been
accepted as an event (no chains on unaccepted proposals). Work is bounded by max_fanout and max_depth.
"""
RELATIONS = ("observes", "communicates", "believes", "protects", "threatens", "depends_on", "trusts", "contains")
# owning domain -> transitions it may request (others are rejected as forbidden domain writes)
DOMAINS = {"relationship_engine": {"evaluate_observer_reaction"},
           "material_environment": {"ignite", "evaluate_pressure_failure"},
           "knowledge": {"record_exposure"}}
MAX_DEPTH = 3


class Refused(ValueError):
    pass


def check_graph(relationships, entities):
    """Every edge must be a registered relation type between registered entities (no ghost edges)."""
    known = set(entities)
    for r in relationships:
        if r["type"] not in RELATIONS:
            raise Refused(f"unregistered relation type {r['type']!r}")
        for end in ("source", "target"):
            if r[end] not in known:
                raise Refused(f"ghost edge: {end} {r[end]!r} is not a registered entity")


# Predicate library: named, deterministic, over accepted facts only. Each returns (ok, reason).
def _related(snap, src, typ, dst):
    return any(r["source"] == src and r["type"] == typ and r["target"] == dst for r in snap["relationships"])


def _fact(snap, subject, key, value=True):
    return snap["facts"].get(subject, {}).get(key) == value


PREDICATES = {
    "observer_witnessed": lambda ev, snap, b: (b["observer"] in (ev.get("known_to") or []), "the observer did not perceive the event"),
    "observer_holds_relevant_conviction": lambda ev, snap, b: (bool(snap["facts"].get(b["observer"], {}).get("convictions")), "no established conviction for the observer"),
    "ruled_morally_salient": lambda ev, snap, b: ((ev.get("details") or {}).get("moral_finding") in ("unjustified_harm", "attempted_unjustified_harm"), "no GM moral finding on the event"),
    "ignition_source_present": lambda ev, snap, b: ((ev.get("details") or {}).get("ignition") is True, "no ignition source in the event"),
    "target_combustible": lambda ev, snap, b: (_fact(snap, b["target"], "combustible"), "the target is not established as combustible"),
    "target_burning": lambda ev, snap, b: (_fact(snap, b["target"], "burning"), "the target is not burning (accepted status)"),
    "target_sealed": lambda ev, snap, b: (_fact(snap, b["target"], "sealed"), "the container is not sealed"),
    "volatile_contents": lambda ev, snap, b: (any(_fact(snap, r["target"], "volatile") for r in snap["relationships"] if r["source"] == b["target"] and r["type"] == "contains"), "no volatile contents established"),
    "suppressed": lambda ev, snap, b: (_fact(snap, b["target"], "suppressed"), "not suppressed"),
}


def _bind(rule, event):
    d = event.get("details") or {}
    out = {}
    for role, ref in (rule.get("bind") or {}).items():
        if ref.startswith("$details."):
            out[role] = d.get(ref[len("$details."):])
        elif ref == "$each_witness":
            out[role] = "$each"
        else:
            out[role] = ref
    return out


def resolve(event, snapshot, rules, applied_keys=(), depth=0):
    """Return {proposals, no_effect, rejected}. Deterministic order. Never mutates inputs; never commits."""
    if depth > MAX_DEPTH:
        raise Refused("max_depth exceeded")
    if not event.get("accepted"):
        return {"proposals": [], "no_effect": [{"rule_id": None, "reason": "event is not accepted; nothing propagates from a proposal"}], "rejected": []}
    proposals, no_effect, rejected, seen = [], [], [], set(applied_keys)
    for rule in sorted(rules, key=lambda r: (r.get("precedence", 50), r["rule_id"])):
        if rule.get("status") != "candidate_enabled" and rule.get("status") != "approved":
            continue
        if rule["trigger"] != event["kind"]:
            continue
        base = _bind(rule, event)
        bindings = [dict(base, observer=w) for w in sorted(event.get("known_to") or []) if w != event.get("actor")] if base.get("observer") == "$each" else [base]
        made = 0
        for b in bindings:
            failed = []
            for name in rule.get("all", []):
                ok, why = PREDICATES[name](event, snapshot, b)
                if not ok:
                    failed.append({"predicate": name, "reason": why})
            for name in rule.get("none", []):
                ok, why = PREDICATES[name](event, snapshot, b)
                if ok:
                    failed.append({"predicate": "not " + name, "reason": "excluded by " + name})
            if failed:
                no_effect.append({"rule_id": rule["rule_id"], "binding": b, "failed": failed})
                continue
            c = rule["candidate"]
            if c["requested_transition"] not in DOMAINS.get(c["owning_domain"], set()):
                rejected.append({"rule_id": rule["rule_id"], "reason": f"forbidden domain write: {c['owning_domain']} cannot {c['requested_transition']}"})
                continue
            target = b.get(c.get("target_role", "target"))
            key = f"{rule['rule_id']}:{event['event_id']}:{target}"
            if key in seen:
                no_effect.append({"rule_id": rule["rule_id"], "binding": b, "failed": [{"predicate": "idempotency", "reason": "already proposed or applied"}]})
                continue
            if made >= rule.get("max_fanout", 6):
                rejected.append({"rule_id": rule["rule_id"], "reason": "max_fanout reached"})
                break
            seen.add(key); made += 1
            proposals.append({"idempotency_key": key, "rule_id": rule["rule_id"], "owning_domain": c["owning_domain"],
                              "requested_transition": c["requested_transition"], "target": target,
                              "caused_by": [event["event_id"]], "depth": depth, "status": "proposed", "commits": False})
    return {"proposals": proposals, "no_effect": no_effect, "rejected": rejected}
