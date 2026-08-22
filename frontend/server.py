"""
server.py -- Dynamic backend for the UniHack dashboard.

Replaces the static-only workflow (generate_data.py + serve.py) with a live
one: upload a CSV/XLSX in the browser, the AI pipeline runs on it, and the
dashboard views render the fresh output.

    python frontend/server.py [--port 8000]

API:
    POST /api/process   multipart file=<csv|xlsx>, optional limit=<int>
                        -> runs the pipeline, writes frontend/data/*.json,
                           returns { n_rows, elapsed_s, metrics }
    POST /api/review    json { key, decision: accept|reject|edit,
                        at?, product?: { attributes, descriptions } }
                        -> persists the human decision (and edited fields)
                           into products.json
    GET  /api/progress  -> { running, done, total, elapsed_s } live job state
    GET  /api/status    -> { ready, n_products, has_data }

Static hosting is unchanged: index.html, js/, css/, data/ all served from
this directory, so the existing no-build frontend keeps working.
"""

import json
import os
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Load .env (GROQ_API_KEY etc.) before anything reads os.getenv — without
# this the pipeline silently degrades to "LLM unavailable" mode.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass

FRONTEND = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(FRONTEND, "data")
UPLOAD_DIR = os.path.join(ROOT, "data", "processed", "uploads")
INTERNAL_JSON = os.path.join(ROOT, "data", "processed", "products.json")

MAX_UPLOAD_MB = 50
ALLOWED_EXT = {".csv", ".xlsx", ".xls"}
REVIEW_DECISIONS = {"accept", "reject", "edit"}

from flask import Flask, request, jsonify, send_from_directory

from src.pipeline.batch import process_batch
from src.preprocessing.models import ProductInput
from src.preprocessing.columns import normalize_columns
from src.validation.validator import validate_product
from src.validation.confidence import compute_confidence
from src.entity_resolution.manufacturer import ManufacturerResolver

MASTER = os.path.join(ROOT, "data", "reference", "UniCat_Manufacturer_and_Brand_List.xlsx")
INPUT_CSV = os.path.join(ROOT, "data", "raw", "Unihack_ Sample Dataset - Input.csv")

# Mirrors KNOWN_UOMS in run_pipeline.py / generate_data.py (subset of UOM master).
KNOWN_UOMS = {"V", "A", "W", "kW", "in", "ft", "mm", "cm", "m", "lb", "kg", "oz",
              "g", "dBA", "dB", "%", "psi", "RPM", "CFM", "HP", "BTU", "BTUH",
              "hr", "min", "pc", "ea", "pk", "pr", "set", "kW-hr", "\u00b0F", "\u00b0C"}

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Live job state so the UI can show "row X/N" instead of a frozen spinner.
JOB = {"running": False, "done": 0, "total": 0, "started_at": None}
_JOB_LOCK = threading.Lock()


def _job_update(**kw):
    with _JOB_LOCK:
        JOB.update(kw)


@app.get("/api/progress")
def api_progress():
    with _JOB_LOCK:
        snap = dict(JOB)
    snap["elapsed_s"] = round(time.time() - snap["started_at"], 1) if snap["started_at"] else 0
    return jsonify(snap)


@app.after_request
def no_cache(response):
    # The frontend is a single-file no-build app under active change; cached
    # app.js/index.html (without the Upload view) made the page look broken.
    response.headers["Cache-Control"] = "no-store, must-revalidate"
    # CORS: the same dashboard can be hosted separately (GitHub Pages,
    # file://) and point at this API via window.UNIHACK_BACKEND_URL.
    # No cookies/credentials are involved, so a permissive policy is safe
    # and lets preflights (JSON POST /api/review) succeed.
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


# ---------------------------------------------------------------------------
# Metrics — same computation as frontend/generate_data.py (never hardcoded)
# ---------------------------------------------------------------------------

def compute_metrics(products):
    n = len(products)
    if n == 0:
        return {
            "n_products": 0, "high_confidence": 0, "needs_review": 0,
            "validation_failures": 0, "grounding_rate": 0.0,
            "lov_compliance_rate": 0.0, "uom_compliance_rate": 0.0,
            "avg_confidence": 0.0, "field_accuracy": None,
        }

    high = review = val_failures = 0
    grounding = lov = uom = 0.0
    confs = []

    for p in products:
        val = validate_product(p, KNOWN_UOMS)
        conf = compute_confidence(p, val, p.get("manufacturer_confidence", 1.0),
                                  p.get("classification_confidence", 1.0))
        if conf["status"] == "HIGH":
            high += 1
        if conf["needs_review"]:
            review += 1
        if not val["valid"]:
            val_failures += 1
        grounding += val["grounding_rate"]
        lov += val["lov_compliance_rate"]
        uom += val["uom_compliance_rate"]
        confs.append(conf["overall_confidence"])

    return {
        "n_products": n,
        "high_confidence": high,
        "needs_review": review,
        "validation_failures": val_failures,
        "grounding_rate": round(grounding / n, 4),
        "lov_compliance_rate": round(lov / n, 4),
        "uom_compliance_rate": round(uom / n, 4),
        "avg_confidence": round(sum(confs) / n, 4),
        "field_accuracy": None,  # requires the labelled 200-row evaluation
    }


def _load_input(path):
    import pandas as pd
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.read_csv(path, encoding="utf-8")
    # Map arbitrary real-world headers ("Part Number", "Description", ...)
    # onto the canonical six-field schema. Raises ValueError when nothing
    # recognizable exists — surfaced to the user by the caller.
    normalized, report = normalize_columns(df)
    normalized.attrs["column_map"] = report
    return normalized


def _run_pipeline(input_path, limit):
    """Run the pipeline on an input file and refresh frontend/data/*.json."""
    raw = _load_input(input_path)
    col_report = raw.attrs.get("column_map") or {}
    master_path = MASTER if os.path.exists(MASTER) else None

    delivery_csv = os.path.join(
        UPLOAD_DIR, os.path.splitext(os.path.basename(input_path))[0] + "_enriched.csv"
    )

    start = time.time()
    process_batch(
        input_df=raw,
        master_path=master_path,
        output_path=delivery_csv,
        limit=limit,
        internal_json_path=INTERNAL_JSON,
        progress_cb=lambda done, total: _job_update(done=done, total=total),
    )
    elapsed = time.time() - start

    with open(INTERNAL_JSON, encoding="utf-8") as f:
        products = json.load(f)

    # Guardrail: if EVERY row came back with no part number AND no
    # description, the input columns were not recognized — fail loudly and
    # keep the previous dashboard snapshot instead of overwriting it with
    # an empty catalogue.
    identity_empty = sum(
        1 for p in products if not (p.get("mfg_part_num") or "").strip()
        and not (p.get("part_desc") or "").strip()
    )
    if products and identity_empty == len(products):
        raise ValueError(
            f"All {len(products)} processed rows came back empty — the uploaded "
            "file's columns were not recognized. Expected headers like "
            "'Part Number'/'MPN', 'Description', 'Brand', 'Manufacturer'."
        )

    metrics = compute_metrics(products)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "products.json"), "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2, default=str)
    with open(os.path.join(DATA_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    return len(products), elapsed, metrics, delivery_csv, col_report


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.post("/api/process")
def api_process():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify(error="No file uploaded. Attach a CSV or XLSX as 'file'."), 400

    ext = os.path.splitext(upload.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify(error=f"Unsupported file type '{ext}'. Allowed: .csv, .xlsx, .xls"), 400

    limit_raw = (request.form.get("limit") or "").strip()
    if limit_raw:
        if not limit_raw.isdigit():
            return jsonify(error="'limit' must be a positive integer."), 400
        limit = int(limit_raw)
    else:
        limit = None

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(UPLOAD_DIR, f"{int(time.time())}_{os.path.basename(upload.filename)}")
    upload.save(save_path)

    # Validate it parses before running the whole pipeline.
    try:
        df = _load_input(save_path)
    except Exception as e:
        os.remove(save_path)
        return jsonify(error=f"Could not parse file: {e}"), 400

    if df.empty:
        os.remove(save_path)
        return jsonify(error="The uploaded file has no rows."), 400

    _job_update(running=True, done=0, total=limit or len(df), started_at=time.time())
    try:
        n_rows, elapsed, metrics, csv_path, col_report = _run_pipeline(save_path, limit)
    except ValueError as e:
        # Unrecognizable header schema — a 4xx, not a server fault.
        app.logger.warning("Rejected upload '%s': %s", upload.filename, e)
        return jsonify(error=str(e)), 400
    except Exception as e:
        app.logger.exception("Pipeline failed")
        return jsonify(error=f"Pipeline failed: {e}"), 500
    finally:
        _job_update(running=False)

    return jsonify(
        ok=True,
        n_rows=n_rows,
        total_in_file=len(df),
        elapsed_s=round(elapsed, 1),
        metrics=metrics,
        enriched_csv=os.path.relpath(csv_path, ROOT),
        column_map=col_report,
    )


@app.get("/api/health")
def api_health():
    """
    Ultra-light liveness probe for uptime pingers and Render's health check.

    Deliberately does NOT touch products.json or any disk state — pingers hit
    this every few minutes and must stay cheap enough to keep a free-tier
    instance awake without doing real work.
    """
    return jsonify(ok=True, ts=round(time.time(), 3))


@app.get("/api/status")
def api_status():
    has_data = os.path.exists(os.path.join(DATA_DIR, "products.json"))
    n = 0
    if has_data:
        try:
            with open(os.path.join(DATA_DIR, "products.json"), encoding="utf-8") as f:
                n = len(json.load(f))
        except Exception:
            pass
    master_ready = os.path.exists(MASTER)
    try:
        import groq  # noqa: F401
        groq_installed = True
    except ImportError:
        groq_installed = False
    # llm_ready must reflect reality: key present AND the client installed,
    # otherwise the pipeline silently runs without enrichment.
    llm_ready = bool(os.getenv("GROQ_API_KEY")) and groq_installed
    return jsonify(ready=has_data, n_products=n, master_ready=master_ready,
                   llm_ready=llm_ready, groq_installed=groq_installed,
                   flexible_headers=True)


def _product_key(p):
    """Mirrors productKey() in frontend/js/app.js — single identity rule."""
    for field in ("row_id", "mfg_part_num", "part_desc"):
        if p.get(field) is not None:
            return str(p[field])
    return "row"


def _write_products(products):
    with open(INTERNAL_JSON, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2, default=str)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "products.json"), "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2, default=str)


@app.post("/api/review")
def api_review():
    payload = request.get_json(silent=True) or {}
    key = str(payload.get("key") or "")
    decision = payload.get("decision")
    if not key or decision not in REVIEW_DECISIONS:
        return jsonify(error="'key' and decision (accept|reject|edit) are required."), 400
    if not os.path.exists(INTERNAL_JSON):
        return jsonify(error="No pipeline output to attach the review to yet."), 400

    with open(INTERNAL_JSON, encoding="utf-8") as f:
        products = json.load(f)
    target = next((p for p in products if _product_key(p) == key), None)
    if target is None:
        return jsonify(error=f"Product '{key}' not found in the current snapshot."), 404

    target["review"] = {
        "decision": decision,
        "at": str(payload.get("at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
    }

    # Edit decisions may carry corrected fields — merge only the whitelisted
    # ones so a rogue client cannot rewrite identity/confidence fields.
    if decision == "edit" and isinstance(payload.get("product"), dict):
        edited = payload["product"]
        if isinstance(edited.get("attributes"), list):
            target["attributes"] = edited["attributes"]
        if isinstance(edited.get("descriptions"), dict):
            target["descriptions"] = edited["descriptions"]

    _write_products(products)
    return jsonify(ok=True, key=key, decision=decision)


# ---------------------------------------------------------------------------
# Static hosting (index.html + js/ + css/ + data/)
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.get("/<path:path>")
def static_files(path):
    full = os.path.join(FRONTEND, path)
    if not os.path.isfile(full):
        return send_from_directory(FRONTEND, "index.html")  # SPA-style fallback
    return send_from_directory(FRONTEND, path)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    # First-run convenience: seed from the sample dataset when nothing exists yet.
    if not os.path.exists(os.path.join(DATA_DIR, "products.json")) and os.path.exists(INPUT_CSV):
        print("No frontend/data snapshot found — processing the sample input once...")
        try:
            n, elapsed, _, _, _ = _run_pipeline(INPUT_CSV, limit=25)
            print(f"Seeded {n} products in {elapsed:.1f}s")
        except Exception as e:
            print(f"Seeding failed ({e}); start via Upload instead.")

    url = f"http://127.0.0.1:{args.port}"
    print(f"UniHack dashboard + API at {url}   (upload endpoint: POST /api/process)")
    # threaded=True is required: /api/progress must be answerable while a
    # long /api/process run is still occupying a request thread.
    app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
