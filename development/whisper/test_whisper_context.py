"""WHISPER M3 boundaries: TB4-10, -11, -12 (data side), -18, -26 (no imposed feeling), -28 (emotion alone)."""
import json, subprocess, sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import whisper as W  # noqa: E402
UI = H.parents[1] / "campaigns/starwars_litrpg/ui"

def js(sel):
    code = "const W=require(process.argv[1]);console.log(JSON.stringify(W.context(JSON.parse(process.argv[2]))))"
    return json.loads(subprocess.check_output(["node", "-e", code, str(UI / "src/whisper.js"), json.dumps(sel)]))

# TB4-10 unspecified is not calm: an empty panel produces no context at all
assert js({}) is None, "blank WHISPER is unspecified: no context, no inference"
assert W.interpretations(None) == {"moral_change": None, "diagnosis": None, "alignment_delta": None, "felt": "unspecified"}
# TB4-11 private fear + controlled expression
c = js({"whisper": {"felt": ["fear"], "feltOther": "", "expression": "controlled", "expressionText": "steady voice, saber low", "motive": "protect Wick", "reflection": "If it gets past me it gets him."}})
assert W.validate(c) == [], W.validate(c)
assert c["felt_emotion"] == ["fear"] and c["visibility"] == "pc_private" and c["source"] == "player_explicit"
seen = W.observer_view(c)
assert seen == {"expression": {"style": "controlled", "text": "steady voice, saber low"}}, seen
assert "fear" not in json.dumps(seen) and "Wick" not in json.dumps(seen), "private fear and motive never reach an observer"
assert W.observer_view(c, perceives=False) == {}, "an observer who cannot perceive Aero learns nothing"
# open expression is the player's own choice to show it
o = js({"whisper": {"felt": ["anger"], "expression": "open"}})
assert W.observer_view(o)["expression"]["visible_emotion"] == ["anger"]
# TB4-18 a generic public projection carries no WHISPER at all
decl = {"actor": "aero", "actions": [{"option": "dodge"}], "whisper": c}
assert "whisper" not in W.public_declaration(decl) and decl["whisper"] is c, "public copy drops it; the original is untouched"
# TB4-12 a What-if prompt is not a context until the player explicitly adopts it as reflection
assert js({"whisper": {"felt": [], "expression": "", "motive": "", "reflection": ""}}) is None
# TB4-26 / -28 nothing here imposes or scores a feeling
assert W.interpretations(c)["moral_change"] is None and W.interpretations(c)["alignment_delta"] is None
for bad in [dict(c, source="model"), dict(c, visibility="public"), dict(c, felt_emotion=[]), dict(c, expression={"style": "calm"})]:
    assert W.validate(bad), bad
print("whisper context tests ok")
