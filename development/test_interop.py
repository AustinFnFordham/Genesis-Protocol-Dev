import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
client = ROOT / "development/interop/public_client.py"

def read(campaign,name,cursor=None):
    command=[sys.executable,"-B",str(client),str(campaign),"isolated","--client",name]
    if cursor: command += ["--cursor",str(cursor)]
    return json.loads(subprocess.check_output(command,text=True))

with tempfile.TemporaryDirectory() as directory:
    campaign=Path(directory)/"campaign"
    shutil.copytree(ROOT/"campaigns/starwars_litrpg/runs/sandbox",campaign)
    a=read(campaign,"client-A")
    b=read(campaign,"client-B")
    assert a["cursor"]==b["cursor"] and a["public"]==b["public"]
    cursor=Path(directory)/"cursor.json"
    cursor.write_text(json.dumps(a["cursor"]))
    assert not read(campaign,"client-B",cursor)["changed"]
    path=campaign/"records/events.jsonl"
    lines=[json.loads(line) for line in path.read_text().splitlines()]
    # Event id must follow both streams; only append to the isolated public copy.
    hidden=[json.loads(line) for line in (campaign/"hidden/events.jsonl").read_text().splitlines()]
    seq=max(int(e["event_id"].split("_")[1]) for e in lines+hidden)+1
    event=dict(lines[-1],event_id=f"evt_{seq:04d}",kind="observation",summary="Isolated public change",
               details={},caused_by=[],roll_ids=[],idempotency_key="interop:1")
    with path.open("a") as handle: handle.write(json.dumps(event)+"\n")
    a=read(campaign,"client-A",cursor)
    b=read(campaign,"client-B",cursor)
    assert a["cursor"]==b["cursor"] and a["changed"] and b["changed"]
    assert "PRIVATE_CANARY" not in json.dumps(a["public"])
print("PASS independent client processes read and refresh the same authoritative public revision")
