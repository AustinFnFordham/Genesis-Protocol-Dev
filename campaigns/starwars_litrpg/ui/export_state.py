#!/usr/bin/env python3
"""Build the player-visible UI state document from the ledger + Aero's sheet.

Output: JSON for the Artifact db doc `view/state`. Derived ONLY from the public
ledger file (records/events.jsonl, via the ledger's own player_view) and the
player-visible character runtime. Never reads hidden/. The artifact mirrors this;
it never writes it. Usage: export_state.py [--out FILE]
"""
import argparse, json, re, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "api_bridge"))
import litrpg_adapter as la  # noqa: E402

SHEET = ROOT / "api_bridge" / "gm" / "aero_character_runtime.yml"
NON_JOURNAL = {"turn_context", "ruling_void", "gm_narration", "scene_state", "gm_suggestions", "player_declaration", "party_joined", "party_left", "plan_progress"}
ACTIVE_ACTOR = "aero"


def build_roster(ev, aero_name, aero_line):
    """Roster = Aero (default, the active actor) + members whose public ledger events say they joined.
    A runtime file existing never adds anyone. Mechanics are shown only for Aero's authoritative runtime;
    every other member is 'pending' until a validated sheet is explicitly linked by a ledger event."""
    roster = {ACTIVE_ACTOR: {"id": ACTIVE_ACTOR, "name": aero_name, "line": aero_line, "role": "You",
                             "status": "Active", "mechanics": "authoritative", "note": "", "joined_event": None}}
    for e in ev:
        d = e.get("details") or {}
        mid = str(d.get("member_id", "")).strip().lower()
        if e["kind"] == "party_joined" and mid and mid != ACTIVE_ACTOR:
            roster[mid] = {"id": mid, "name": d.get("name", mid), "line": d.get("line", ""), "role": d.get("role", "Companion"),
                           "status": "In party", "mechanics": "pending", "note": d.get("identity_note", ""),
                           "joined_event": e["event_id"]}
        elif e["kind"] == "party_left" and mid in roster and mid != ACTIVE_ACTOR:
            roster.pop(mid)
    return list(roster.values())


def member_journal(ev, mid):
    return [{"event_id": e["event_id"], "time": e["world_time"], "kind": e["kind"], "knowledge": e["knowledge_type"], "text": e["summary"]}
            for e in ev if e["kind"] not in NON_JOURNAL and (e.get("actor") == mid or mid in (e.get("tags") or []) or mid in (e.get("known_to") or []))]


def public_events(campaign_dir):
    """Player-visible events of any campaign run directory (records/ only; hidden/ is never opened)."""
    m = la._ledger()
    return m.player_view(m.read_jsonl(Path(campaign_dir) / "records" / "events.jsonl"))


PLAYER_ROLLERS = {"aero", "player"}


def public_roll(r, rid, purpose, kept):
    """What the Datapad may show of a roll. The player's own rolls show dice, modifier and total; anything rolled for
    another actor (enemies, NPCs, the world, or the GM on anyone's behalf) shows only its purpose and total: no formula,
    no modifier, no die faces, no natural 20/1 and no success/failure (which would reveal a hidden DC or AC).
    Rolls requested --by gm_hidden (GM tables, unperceived stealth, hidden NPC choices) are not shown at all.
    The full roll stays in the authoritative roll log (records/roll_log.jsonl) and the GM's DC ledger."""
    who = r.get("requested_by") or ""
    if who.startswith("gm_hidden"):  # GM tables, hidden NPC decisions, stealth the player has not perceived: never shown
        return None
    if who in PLAYER_ROLLERS:
        summ = r.get("summary") or (f'{r.get("formula")} [{", ".join(kept)}]' + (f' {r["modifiers"]:+d}' if r.get("modifiers") else "") + f' = {r.get("final_total")}' + (" (natural 20)" if r.get("nat20") else " (natural 1)" if r.get("nat1") else ""))
        summ = re.sub(r"\s*\((success|failure)\)\s*$", "", summ)
        return {"roll_id": rid, "purpose": purpose, "summary": summ, "by": who}
    return {"roll_id": rid, "purpose": purpose, "summary": f'total {r.get("final_total")}', "by": "gm", "redacted": True}


def build(ev=None, campaign_dir=None, campaign_id=None):
    if ev is None:
        ev = public_events(campaign_dir) if campaign_dir else la.player_events()
    ev_all = ev
    # Owner/GM rulings can void earlier events (append-only: the ledger keeps them, the live view ignores them).
    voided = {v for e in ev_all if e["kind"] == "ruling_void" for v in e["details"].get("voids", [])}
    ev = [e for e in ev_all if e["event_id"] not in voided]
    sheet = yaml.safe_load(SHEET.read_text(encoding="utf-8"))["character_runtime"]
    idn, dfn, res, mov = sheet["identity"], sheet["defenses"], sheet["resources"], sheet["movement"]
    ab = sheet["abilities"]
    scene = next((e["details"] for e in reversed(ev) if e["kind"] == "scene_state"), {})
    sugg = next((e["details"].get("items", []) for e in reversed(ev) if e["kind"] == "gm_suggestions"), [])
    last = ev_all[-1] if ev_all else {}
    feed = []
    for e in ev:
        if e["kind"] == "gm_narration":
            if not (e["details"] or {}).get("text"):
                continue  # committed empty by a processing error and superseded (erratum); never show its summary as story
            feed.append({"who": "gm", "event_id": e["event_id"], "time": e["world_time"], "text": e["details"].get("text", e["summary"])})
        elif e["kind"] == "ruling_void":
            # the page renders only *italics*; flatten markdown headings/bullets from ruling text
            t = e["details"].get("text", e["summary"]).replace("**", "")
            t = "\n".join(("\u2022 " + ln[2:]) if ln.startswith("- ") else ln for ln in t.split("\n"))
            feed.append({"who": "gm", "event_id": e["event_id"], "time": e["world_time"], "text": t})
        elif e["kind"] == "player_declaration":
            feed.append({"who": "player", "event_id": e["event_id"], "time": e["world_time"], "text": e["details"].get("text", e["summary"])})
    journal = [{"event_id": e["event_id"], "time": e["world_time"], "kind": e["kind"],
                "knowledge": e["knowledge_type"], "text": e["summary"]} for e in ev if e["kind"] not in NON_JOURNAL]
    skills = [{"name": k.replace("_", " "), "mod": v["modifier"]} for k, v in sheet["proficiencies"]["skills"].items()]
    # Ledger overlay: the sheet runtime is static, so Aero's current HP is max + sum of public hp_change deltas (clamped).
    hp_max = dfn["maximum_hp"]
    hp_now = max(0, min(hp_max, dfn["current_hp"] + sum(e["details"].get("delta", 0) for e in ev
                 if e["kind"] == "hp_change" and e["details"].get("target") == ACTIVE_ACTOR)))
    cond_ev = [e for e in ev if e["kind"] == "condition_change" and e["details"].get("target") == ACTIVE_ACTOR]
    conditions = cond_ev[-1]["details"].get("conditions", []) if cond_ev else dfn.get("conditions", [])
    roster = build_roster(ev, idn["name"], f'{idn["species"]} {idn["class"]} · {idn["background"]} · {idn["current_rank"]}')
    # Turn context for the composer: the latest public turn_context event, only if nothing newer
    # than it has been committed except presentation events (otherwise it is stale and omitted).
    PRESENT = {"gm_narration", "scene_state", "gm_suggestions", "turn_context"}
    tc_idx = max((i for i, e in enumerate(ev) if e["kind"] == "turn_context"), default=None)
    turn_context = None
    if tc_idx is not None and all(e["kind"] in PRESENT for e in ev[tc_idx + 1:]):
        turn_context = dict(ev[tc_idx]["details"]); turn_context["context_id"] = ev[tc_idx]["event_id"]
        if turn_context.get("equipment_from_ledger"):  # contract 3: gear whereabouts from the sheet + committed events, never typed by hand
            import equipment as _eqm
            turn_context["equipment"] = _eqm.derive(ev)
    # Dice shown for the latest resolved turn: public roll log entries cited by events after the
    # last player declaration (the public log never stores DCs).
    rolls = []
    try:
        led = la._ledger()
        rdir = Path(campaign_dir) if campaign_dir else Path(la.CAMPAIGN_DIR)
        log = {r["roll_id"]: r for r in led.read_jsonl(rdir / "records" / "roll_log.jsonl")}
        last_decl = max((i for i, e in enumerate(ev) if e["kind"] == "player_declaration"), default=None)
        if last_decl is not None:
            for e in ev[last_decl:]:
                for rid in e.get("roll_ids") or []:
                    r = log.get(rid)
                    if r and rid not in [x["roll_id"] for x in rolls]:
                        purpose = re.sub(r"^\[[^\]]+\]\s*", "", r.get("purpose", ""))
                        kept = [str(k) for d in r.get("dice", []) for k in d.get("kept", [])]
                        pr = public_roll(r, rid, purpose, kept)
                        if pr:
                            rolls.append(pr)
    except Exception:  # noqa: BLE001 - dice display is best-effort; the ledger stays authoritative
        rolls = []
    # Protagonist Continuity status (campaign rule) from the rule file + public events.
    continuity = None
    try:
        rule = json.loads((Path(__file__).resolve().parents[1] / "creator" / "continuity_rule.json").read_text(encoding="utf-8"))
        if rule["status"].startswith("approved") and (campaign_id or "starwars_litrpg") != "starwars_litrpg":
            kinds = [e["kind"] for e in ev if (e.get("details") or {}).get("target") in (None, ACTIVE_ACTOR)]
            continuity = {"status": "expired" if "continuity_expired" in kinds else "expiring" if "continuity_expiring" in kinds else "active",
                          "marks": sum(1 for e in ev if e["kind"] == "continuity_invoked" and e["details"].get("target") == ACTIVE_ACTOR),
                          "ends": "after Hask Meadow is complete and level 3 is reached, at the end of the next long rest"}
    except Exception:  # noqa: BLE001
        continuity = None
    return {
        "continuity": continuity,
        "campaign_id": campaign_id or "starwars_litrpg",
        "rolls": rolls,
        "turn_context": turn_context,
        "revision": len(ev_all), "ledger_head": last.get("event_id"), "turn_no": last.get("turn_no", 0),
        "scene": {"title": scene.get("title"), "location": scene.get("location"), "time": last.get("world_time"),
                  "atmosphere": scene.get("atmosphere", [])},
        "feed": feed, "journal": journal, "suggestions": sugg, "objectives": [],
        "active_actor": ACTIVE_ACTOR,
        "roster": roster,
        "member_journals": {m["id"]: member_journal(ev, m["id"]) for m in roster if m["id"] != ACTIVE_ACTOR},
        "party": [{"name": m["name"], "role": m["role"], "status": m["status"]} for m in roster],
        "character": {
            "name": idn["name"], "line": f'{idn["species"]} {idn["class"]} · {idn["background"]} · {idn["current_rank"]}',
            "level": idn["level"],
            "hp": [hp_now, hp_max], "strain": [dfn["current_strain"], dfn["maximum_strain"]],
            "force": [res["current_force_points"], res["maximum_force_points"]],
            "ac": dfn["armor_class"], "speed": mov["speed"], "initiative": mov["initiative"],
            "scores": {k[:3].upper(): [v, ab["modifiers"][k]] for k, v in ab["scores"].items()},
            "passive": {"perception": sheet["senses"]["passive_perception"], "insight": sheet["senses"]["passive_insight"]},
            "conditions": conditions, "skills": skills,
            "languages": sheet["proficiencies"]["languages"],
            "powers": [{"name": p["name"], "cost": p["cost"], "effect": p["exact_effect"] + (" Range: " + p["range"] + "." if p.get("range") else "")} for p in sheet["powers"]],
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
    ap.add_argument("--campaign-dir", help="run directory with records/ (default: the original UAT run)")
    ap.add_argument("--campaign-id")
    a = ap.parse_args()
    out = json.dumps(build(campaign_dir=a.campaign_dir, campaign_id=a.campaign_id), ensure_ascii=False, indent=1)
    Path(a.out).write_text(out, encoding="utf-8") if a.out else print(out)
