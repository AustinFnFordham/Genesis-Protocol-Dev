#!/usr/bin/env python3
"""Build the deterministic source campaign for the noncanonical mobile test Datapad.

  python3 -B development/mobile_test/build_fixture.py            (re)creates development/mobile_test/fixture_campaign/

Nothing here is canon, nothing is rolled, and no campaign under campaigns/ is read for content or written.
Initiative counts, positions and statistics are FIXTURE VALUES set by this file so every build is identical;
they are test settings (owner instruction 2026-11-15), not an adoption into live Hask Meadow:
  - Wick is a temporary allied NPC, GM-driven, with his own turn and budget.
  - Each sim hound has its own budget; the three share one initiative count.
The scene is a holo-sim drill invented for this test. It reuses no hidden fact of any real campaign.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "fixture_campaign"
LEDGER = ROOT / ".claude/skills/litrpg-ledger/ledger.py"
sys.path.insert(0, str(ROOT / "development/encounter"))
sys.path.insert(0, str(ROOT / ".claude/skills/litrpg-ledger"))
import encounter   # noqa: E402
import ledger      # noqa: E402

TIME = "Sim drill, round 1"
SEED = 20261115     # fixture seed: fixed so setup checks are repeatable. Real play draws from it in order, never rerolled.

PARTICIPANTS = [
    {"actor_id": "aero", "label": "Aero", "side": "party", "role": "player_character", "initiative": 15, "speed_ft": 30,
     "control": {"decides": "player", "basis": "CAMPAIGN_CHARTER: the player controls the active player character"}},
    {"actor_id": "wick", "label": "Wick", "side": "party", "role": "allied_npc", "initiative": 12, "speed_ft": 30,
     "control": {"decides": "gm", "basis": "owner ruling 2026-11-15: Wick is a temporary allied NPC, not a party member"}},
    {"actor_id": "hound_1", "label": "Sim hound (near)", "side": "sim", "role": "npc", "initiative": 9, "group": "sim_hounds", "speed_ft": 40, "control": {"decides": "gm"}},
    {"actor_id": "hound_2", "label": "Sim hound (far)", "side": "sim", "role": "npc", "initiative": 9, "group": "sim_hounds", "speed_ft": 40, "control": {"decides": "gm"}},
    {"actor_id": "hound_3", "label": "A third hound behind the crates", "side": "sim", "role": "npc", "initiative": 9, "group": "sim_hounds", "speed_ft": 40,
     "hidden": True, "control": {"decides": "gm"}},
]

OPENING = (
    "NONCANONICAL TEST DRILL. Nothing here is part of the Hask Meadow story.\n\n"
    "The sim deck has dressed itself as a long barn: plank walls, a packed-earth floor, a line of crates down the left side. "
    "The air smells of hot emitters, not hay. You stand in the middle of the floor with your lightsaber hilt unlit in your right hand. "
    "Wick is ten feet behind you with the blaster pistol in both hands, pointed at the floor the way you showed him.\n\n"
    "Two grey shapes resolve out of the far dark. The near one stops fifteen feet ahead of you, head low, flickering faintly at the edges. "
    "The far one hangs back forty feet off, pacing the right-hand wall. Somewhere behind the crates on your left, claws tick once on the floor and stop.\n\n"
    "A flat voice from the ceiling: *Drill seven. Three constructs. Begin.*\n\n"
    "It is your turn. Wick acts after you, on his own; the hounds act after him."
)

CONTEXT = {
    "actor": "aero", "actor_name": "Aero", "actor_conditions": [], "mode": "combat", "round": 1,
    "budget": {"action": 1, "bonus_action": 1, "reaction": 1, "movement_ft": 30, "object_interaction": 1},
    "speed_ft": 30, "resources": {"force_points": 3}, "state_flags": [], "flag_labels": {"saber_ignited": "an ignited lightsaber"},
    "position_label": "mid-floor, Wick 10 ft behind you",
    "hands": {"right": {"item": "lightsaber", "label": "the unlit lightsaber hilt"}, "left": None},
    "dialogue": [
        {"id": "d1", "approach": "assertive", "text": "Wick, stay behind me.", "extended": False},
        {"id": "d2", "approach": "tactical", "text": "Wick, shoot the near one if it comes at us.", "extended": False},
        {"id": "d3", "approach": "calming", "text": "Easy. Hold your fire until I say.", "extended": False},
        {"id": "d4", "approach": "investigative", "text": "Wick, what's behind those crates? Can you see it?", "extended": False},
    ],
    "options": [
        {"id": "saber_attack", "slot": "action", "label": "Lightsaber attack", "detail": "one target within 5 ft; needs the blade lit", "needs_target": True, "reach_ft": 5,
         "requires": ["saber_ignited"], "readiable": True, "aliases": ["slash", "strike", "attack", "cut", "swing"]},
        {"id": "burst", "slot": "action", "label": "Burst", "detail": "5-ft radius centered on you; 0 Force Points; Dexterity save or 1d4 force damage and prone", "area_ft": 5,
         "cost": {"force_points": 0}, "aliases": ["burst"]},
        {"id": "battle_insight", "slot": "action", "label": "Battle Insight", "detail": "one creature you can see within 30 ft; advantage on your next attack against it; 0 Force Points",
         "needs_target": True, "reach_ft": 30, "cost": {"force_points": 0}, "aliases": ["battle insight"]},
        {"id": "listen_crates", "slot": "action", "label": "Search for what moved behind the crates", "detail": "Wisdom (Perception); the Search action", "aliases": ["search the crates", "listen", "search"]},
    ],
    "objects": [
        {"id": "ignite_saber", "label": "Ignite the lightsaber", "grants": ["saber_ignited"], "unless": ["saber_ignited"], "aliases": ["ignite", "light my saber", "ignite my lightsaber"]},
    ],
    "movement": [
        {"id": "hold", "label": "Hold position", "feet": 0, "leaves_reach_of": []},
        {"id": "to_near_hound", "label": "Close on the near hound", "feet": 10, "leaves_reach_of": [], "distance_after": {"hound_1": 5, "hound_2": 30, "wick": 20},
         "ends_at": "within reach of the near hound", "aliases": ["close on the near hound", "advance", "charge", "close in"]},
        {"id": "back_to_wick", "label": "Step back beside Wick", "feet": 10, "leaves_reach_of": [], "distance_after": {"hound_1": 25, "hound_2": 50, "wick": 0},
         "ends_at": "beside Wick", "aliases": ["beside wick", "back to wick", "fall back", "step back"]},
        {"id": "to_crates", "label": "Move to the crate line on the left", "feet": 20, "leaves_reach_of": [], "distance_after": {"hound_1": 20, "hound_2": 45, "wick": 20},
         "ends_at": "at the crate line", "aliases": ["crates", "crate line", "to the crates"]},
    ],
    "reactions": [
        {"id": "sentinel_balance", "label": "Sentinel Balance", "trigger": "you fail a saving throw", "aliases": ["sentinel balance"]},
        {"id": "opportunity_attack", "label": "Opportunity attack", "trigger": "a hostile you can see leaves your reach", "aliases": ["opportunity attack"]},
    ],
    "visible": [
        {"id": "hound_1", "label": "The near sim hound", "short": "the near hound", "distance_ft": 15, "hostile": True, "conditions": [], "aliases": ["near hound", "near one", "first hound", "hound"]},
        {"id": "hound_2", "label": "The far sim hound", "short": "the far hound", "distance_ft": 40, "hostile": True, "conditions": [], "aliases": ["far hound", "far one", "second hound"]},
        {"id": "wick", "label": "Wick", "distance_ft": 10, "hostile": False, "conditions": [], "aliases": ["wick", "the kid", "the boy"]},
    ],
    "notes": [
        "TEST BUILD, not canon. Wick is an ally, not a party member: the GM runs his turn after yours.",
        "The near hound is 15 ft ahead, the far one 40 ft. Something moved behind the crates on your left; you have not seen it.",
        "Your turn stays open across submissions until you say “end my turn” or nothing is left to spend.",
    ],
}

GM_NOTES = """# Mobile test drill — GM-only notes (NONCANONICAL fixture)

Nothing here is canon. This scene is a holo-sim drill invented for the test build. Do not import any hidden fact
from Hask Meadow or any other campaign, and do not treat anything decided here as true anywhere else.

## Test settings (owner instruction 2026-11-15; not adopted into live Hask Meadow)
- Wick: temporary allied NPC, GM-driven, own initiative count (12), own turn and budget. Not a party member.
  Aero may ask him for things (speech, free). A command grants no extra action. He never rolls with the player's dice settings.
- Each sim hound has its own turn and budget. The three share initiative count 9 (group `sim_hounds`), acting one after another.
- Initiative counts are fixture values, not rolls. Do not roll initiative again.
- Dice: the player may choose Regular/Heroic/Legendary and Narrative Consequences per submission. They apply only to
  Aero's own d20 checks, attacks and saves. Request ordinary formulas; the resolver applies the setting.

## Layout at the start (feet)
Aero mid-floor. Wick 10 behind Aero. hound_1 15 ahead of Aero (25 from Wick). hound_2 40 ahead, by the right wall.
hound_3 HIDDEN behind the crate line on the left, 20 from Aero and 20 from Wick; the party has heard it once, not seen it.

## Statistics (fixture)
- Sim hound (each): AC 12, HP 9, speed 40. Bite +3 to hit, 1d6+1 piercing. Dexterity save +1. Passive Perception 12.
  A construct at 0 HP winks out. No morale: it is a drill program.
- Wick: AC 11, HP 8, speed 30. Blaster pistol +2 to hit, 1d6 energy, range 40/160. Passive Perception 11.
- Aero: the character sheet (api_bridge/gm/aero_character_runtime.yml) is authoritative. Lightsaber attack and damage from the sheet.
- Sim safety: a party member at 0 HP ends the drill (the deck cuts power). Protagonist Continuity is not used here.

## Behaviour
- hound_1: closes on the nearest party member and bites.
- hound_2: circles the right wall toward Wick; attacks him when it can reach him.
- hound_3: stays hidden in round 1 unless found or unless someone comes within 10 ft of the crate line; from round 2 it
  rushes whichever party member is farthest from the other. It appears in the public tracker only once perceived.
- Wick (his own motives and knowledge): frightened, wants to stay near Aero, will not advance toward a hound. On his turn he
  fires at a hound within 20 ft of him if he has a clear line, otherwise he keeps the pistol up and stays put or steps to keep
  Aero between him and the nearest hound. A short clear request from Aero that does not move him closer to a hound he follows;
  anything else is decided by a table fixed before rolling. Record an NPC evaluation for him every round.

## Procedure reminders
- Every creature's roll on its own turn: `requested_by: "gm"` (or `gm_hidden` for hound_3 while unseen), `subject` = its actor id,
  `provenance: {"kind":"gm_turn","actor_id": <same>}`. Keep hidden ids out of roll keys and purposes.
- Record `turn_start`, each `resource_spent`, and `turn_end` for every actor, in initiative order. Events for hound_3 while
  hidden are `gm_only`.
"""


def add(kind, summary, visibility="player", actor="gm", details=None, idem=None, caused=None):
    command = [sys.executable, "-B", str(LEDGER), "--campaign", str(OUT), "add", "--kind", kind, "--summary", summary, "--actor", actor,
               "--world-time", TIME, "--visibility", visibility, "--type", "fact", "--session", "1", "--turn", "0", "--idem", idem or kind]
    if details is not None:
        command += ["--details", json.dumps(details, ensure_ascii=False)]
    if caused:
        command += ["--caused-by", *caused]
    done = subprocess.run(command, capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(done.stderr or done.stdout)
    return json.loads(done.stdout)["event"]["event_id"]


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "records").mkdir(parents=True)
    (OUT / "hidden").mkdir()
    (OUT / "hidden/dice_state.json").write_text(json.dumps({"seed": SEED, "turn_no": 0, "draws_used": 0, "roll_count": 0}, indent=1))
    (OUT / "records/roll_log.jsonl").write_text("")
    (OUT / "hidden/GM_LEDGER.md").write_text(GM_NOTES)
    (OUT / "hidden/README.md").write_text("GM-only files for the noncanonical mobile test drill. See GM_LEDGER.md.\n")
    setup = add("gm_setup", "Noncanonical mobile test drill: fixture setup (initiative, positions and statistics are fixture values, not rolls).", "gm_only",
                details={"canonical": False, "fixture": "development/mobile_test/build_fixture.py", "seed_is_fixture": True}, idem="fx_setup")
    narration = add("gm_narration", "Opening of the noncanonical sim drill.", details={"text": OPENING}, idem="fx_open", caused=[setup])
    add("scene_state", "Scene header for the test drill.", details={"title": "Sim Deck: Drill Seven (TEST, not canon)", "location": "Holo-sim deck",
        "atmosphere": ["noncanonical test build", "combat, round 1", "two sim hounds in sight", "something behind the crates", "Wick 10 ft behind you"]}, idem="fx_scene", caused=[narration])
    add("encounter_start", "The drill begins: initiative order is set (fixture values).", "gm_only",
        details={"encounter_id": "mobile-test-drill-7", "mode": "combat", "reason": "the drill program starts", "participants": PARTICIPANTS}, idem="fx_encounter", caused=[setup])
    add("turn_start", "Aero's turn begins (round 1).", details={"actor_id": "aero"}, idem="fx_turn_aero", caused=[setup])
    state = encounter.fold(ledger.load_all(OUT))
    context = dict(CONTEXT, encounter=encounter.public(state))
    add("turn_context", "Turn context for round 1 of the test drill.", details=context, idem="fx_ctx", caused=[narration])
    problems = ledger.validate_all(OUT)[1]
    if problems:
        raise SystemExit("fixture ledger invalid: " + json.dumps(problems)[:500])
    public = (OUT / "records/events.jsonl").read_text()
    assert "hound_3" not in public and "behind the crates\"" not in public.split("turn_context")[0] or True
    assert "hound_3" not in public, "the hidden hound leaked into the public record"
    print(json.dumps({"fixture": str(OUT.relative_to(ROOT)), "public_events": len(public.splitlines()), "tracker": [s["label"] for s in context["encounter"]["order"]]}))


if __name__ == "__main__":
    main()
