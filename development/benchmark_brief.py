"""Read-only benchmark. Emits aggregate measurements without campaign contents."""
import importlib.util
import json
from pathlib import Path
import statistics
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("brief", ROOT / ".claude/skills/litrpg-process-turn/brief.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
entry = B.run_entry("hask_meadow_r2")
def size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode())
times = []
for _ in range(5):
    start = time.perf_counter()
    state, full = B.build(entry)
    times.append((time.perf_counter() - start) * 1000)
with tempfile.TemporaryDirectory() as directory:
    cp = Path(directory) / "checkpoint.json"
    cp.write_text(json.dumps(state))
    start = time.perf_counter()
    _, incremental = B.build(entry, checkpoint=cp)
    incremental_ms = (time.perf_counter() - start) * 1000
compact = B.compact(full)
raw_bytes = sum((entry["path"] / name).stat().st_size for name in ("records/events.jsonl", "hidden/events.jsonl"))
print(json.dumps({"head": state["head"], "events": state["events"], "ledger_bytes": raw_bytes,
                  "full_bundle_bytes": size(full), "compact_bundle_bytes": size(compact),
                  "compact_vs_full_reduction_percent": round(100 * (1 - size(compact) / size(full)), 2),
                  "full_replay_median_ms": round(statistics.median(times), 2),
                  "verified_checkpoint_ms": round(incremental_ms, 2),
                  "same_fields": compact["fields"] == full["fields"] == incremental["fields"],
                  "limits": "Timing is local; bytes are not model token measurements. Checkpoint payload verification replays the prefix; no runtime speedup claimed."}, indent=2))
