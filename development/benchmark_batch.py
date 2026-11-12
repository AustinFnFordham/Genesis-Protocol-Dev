"""Compare equivalent event workloads using existing single-event CLI versus batch."""
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / ".claude/skills/litrpg-ledger/ledger.py"

def workload(root, mode, count):
    campaign = Path(root) / mode
    (campaign / "hidden").mkdir(parents=True)
    lock = campaign / "lease.json"
    lock.write_text(json.dumps({"holder":"benchmark","expires_ms":int(time.time()*1000)+120000}))
    drafts = [{"session":1,"turn_no":1,"world_time":"test","kind":"ruling","summary":"equivalent consequence",
               "actor":"gm","visibility":"player" if i%2==0 else "gm_only","knowledge_type":"fact",
               "tags":[],"known_to":[],"caused_by":[],"roll_ids":[],"details":{}} for i in range(count)]
    start = time.perf_counter()
    if mode == "single":
        for i,event in enumerate(drafts):
            subprocess.run([sys.executable,"-B",str(LEDGER),"--campaign",str(campaign),"add",
                            "--kind",event["kind"],"--summary",event["summary"],"--world-time","test",
                            "--turn","1","--visibility",event["visibility"],"--idem",f"single:{i}"],
                           check=True,capture_output=True)
    else:
        request = campaign / "batch.json"
        request.write_text(json.dumps({"batch_id":"benchmark","expected_revision":0,"expected_head":None,"events":drafts}))
        subprocess.run([sys.executable,"-B",str(LEDGER),"--campaign",str(campaign),"batch",str(request),
                        "--lock",str(lock),"--run","benchmark"],check=True,capture_output=True)
    elapsed = (time.perf_counter()-start)*1000
    events = []
    for prefix in ("records","hidden"):
        events += [json.loads(line) for line in (campaign/prefix/"events.jsonl").read_text().splitlines()]
    for event in events:
        event.pop("idempotency_key",None)
    return elapsed, sorted(events,key=lambda e:e["event_id"])

results = {"single":[],"batch":[]}
for _ in range(5):
    with tempfile.TemporaryDirectory(prefix="genesis-benchmark-") as root:
        one, events = workload(root,"single",20)
        many, batched = workload(root,"batch",20)
        assert events == batched
        results["single"].append(one)
        results["batch"].append(many)
print(json.dumps({"events_per_workload":20,"repeats":5,"equivalent_events":True,
                  "single_median_ms":round(statistics.median(results["single"]),2),
                  "batch_median_ms":round(statistics.median(results["batch"]),2),
                  "process_invocations":{"single":20,"batch":1},
                  "limits":"Local CLI wall time, not measured remote tool latency. No dice requests in either workload."},indent=2))
