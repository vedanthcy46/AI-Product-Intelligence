"""E2E: upload 2 rows, poll /api/progress in parallel, verify pacing works."""
import json
import sys
import threading
import time
import urllib.request

BASE = "http://127.0.0.1:8000"
CSV = r"data\raw\Unihack_ Sample Dataset - Input.csv"

progress_seen = []


def poll():
    while not done.is_set():
        try:
            with urllib.request.urlopen(BASE + "/api/progress", timeout=5) as r:
                p = json.load(r)
                progress_seen.append(p)
                print(f"  [progress] running={p['running']} done={p['done']}/{p['total']} elapsed={p['elapsed_s']}s", flush=True)
        except Exception as e:
            print(f"  [progress poll error] {e}", flush=True)
        time.sleep(2)


done = threading.Event()

# multipart upload via boundary (no requests dependency)
boundary = "----pyboundary42"
with open(CSV, "rb") as f:
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"limit\"\r\n\r\n2\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"input.csv\"\r\n"
        f"Content-Type: text/csv\r\n\r\n"
    ).encode() + f.read() + f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(
    BASE + "/api/process",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST",
)

t = threading.Thread(target=poll, daemon=True)
t.start()
start = time.time()
with urllib.request.urlopen(req, timeout=1800) as r:
    result = json.load(r)
done.set()
elapsed = time.time() - start

print("\n=== RESULT ===")
print(json.dumps(result, indent=2)[:1500])
assert result.get("ok"), "upload failed"
assert any(p.get("running") for p in progress_seen), "progress endpoint never reported running"
print(f"\nPASS: 2 rows in {elapsed:.0f}s, {len(progress_seen)} progress polls, live updates confirmed")
