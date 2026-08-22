"""Offline contract test: /api/process is asynchronous (accepts instantly,
runs in background thread, /api/progress carries status done|error + result).
_run_pipeline is stubbed so no LLM/network calls happen."""
import sys, os, time, io, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import frontend.server as srv
from src.preprocessing.columns import normalize_columns  # noqa: F401 (import sanity)

CSV = b"Mfg_Part_Num,Part_Desc\nABC-1,Widget bearing\nABC-2,Flange 2 in\n"

# ── 1. Success path ────────────────────────────────────────────────────────
def fake_run_ok(path, limit):
    time.sleep(1.0)  # simulate work AFTER the HTTP response must have returned
    df = srv._load_input(path)
    metrics = {"n_products": len(df), "high_confidence": len(df), "needs_review": 0,
               "validation_failures": 0, "grounding_rate": 0.5, "lov_compliance_rate": 1.0,
               "uom_compliance_rate": 1.0, "avg_confidence": 0.9, "field_accuracy": None}
    return len(df), 1.0, metrics, path + ".out.csv", {"mapped": {"Mfg_Part_Num": "Mfg_Part_Num"}, "missing": [], "ignored": []}

srv._run_pipeline = fake_run_ok
c = srv.app.test_client()

t0 = time.monotonic()
r = c.post("/api/process", data={"file": (io.BytesIO(CSV), "t.csv")},
           content_type="multipart/form-data")
accept_s = time.monotonic() - t0
assert r.status_code == 200 and r.get_json()["started"] is True and r.get_json()["total"] == 2, r.get_json()
assert accept_s < 0.9, f"accept took {accept_s:.2f}s — not async!"
print(f"1 OK accepted in {accept_s*1000:.0f}ms (before pipeline finished)")

deadline = time.time() + 10
prog = None
while time.time() < deadline:
    prog = c.get("/api/progress").get_json()
    if prog["status"] in ("done", "error"):
        break
    time.sleep(0.3)
assert prog["status"] == "done", prog
res = prog["result"]
assert res["n_rows"] == 2 and res["elapsed_s"] >= 1.0
assert res["metrics"]["n_products"] == 2 and res["column_map"]["mapped"]
print("2 OK done:", {k: res[k] for k in ("n_rows", "elapsed_s")}, "| metrics+column_map present")

# ── 2. ValueError path -> friendly error in progress feed ──────────────────
def fake_run_bad(path, limit):
    raise ValueError("Could not find a part-number or description column.")
srv._run_pipeline = fake_run_bad

r = c.post("/api/process", data={"file": (io.BytesIO(CSV), "t2.csv")},
           content_type="multipart/form-data")
assert r.status_code == 200 and r.get_json()["started"] is True
deadline = time.time() + 5
while time.time() < deadline:
    prog = c.get("/api/progress").get_json()
    if prog["status"] in ("done", "error"):
        break
    time.sleep(0.2)
assert prog["status"] == "error" and "part-number" in prog["error"], prog
print("3 OK error surfaced:", prog["error"][:60], "...")

# ── 3. Input validation still synchronous 400s ─────────────────────────────
r = c.post("/api/process", data={"file": (io.BytesIO(b"Foo,Bar\n1,2\n"), "junk.csv")},
           content_type="multipart/form-data")
assert r.status_code == 400 and "part-number or description" in r.get_json()["error"], r.get_json()
print("4 OK junk rejected synchronously:", r.get_json()["error"][:50], "...")

print("\nASYNC UPLOAD CONTRACT PASS")
