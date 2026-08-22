"""
generate_data.py -- Produce the frontend data contract from real pipeline output.

Reads the internal Product JSON produced by `run_pipeline.py --internal-json`
(or re-runs the pipeline when it is absent) and writes:

    frontend/data/products.json   -> rich internal product models (V1)
    frontend/data/metrics.json    -> aggregate metrics COMPUTED from that
                                     output (never hardcoded)

Usage:
    python frontend/generate_data.py [--limit 50]
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

FRONTEND_DATA = os.path.join(ROOT, "frontend", "data")
INTERNAL_JSON = os.path.join(ROOT, "data", "processed", "products.json")
INPUT_CSV = os.path.join(ROOT, "data", "raw", "Unihack_ Sample Dataset - Input.csv")
MASTER = os.path.join(ROOT, "data", "reference", "UniCat_Manufacturer_and_Brand_List.xlsx")

KNOWN_UOMS = {"V", "A", "W", "kW", "in", "ft", "mm", "cm", "m", "lb", "kg", "oz",
              "g", "dBA", "dB", "%", "psi", "RPM", "CFM", "HP", "BTU", "BTUH",
              "hr", "min", "pc", "ea", "pk", "pr", "set", "kW-hr", "\u00b0F", "\u00b0C"}


def _load_internal_products(limit: int):
    if os.path.exists(INTERNAL_JSON):
        with open(INTERNAL_JSON, encoding="utf-8") as f:
            products = json.load(f)
        print(f"Using existing internal products JSON: {INTERNAL_JSON} ({len(products)} rows)")
        return products[:limit] if limit else products

    if not os.path.exists(INPUT_CSV):
        sys.exit(f"[generate_data] Missing input: {INPUT_CSV}. Supply the data/ files or run "
                 f"`python run_pipeline.py --internal-json data/processed/products.json` first.")
    if not os.path.exists(MASTER):
        print(f"[generate_data] Warning: master not found at {MASTER} — running in pass-through mode.")

    print("No internal JSON found — running the pipeline to generate it...")
    import pandas as pd
    from src.pipeline.batch import process_batch

    raw = pd.read_csv(INPUT_CSV, encoding="utf-8")
    process_batch(
        input_df=raw,
        master_path=MASTER if os.path.exists(MASTER) else None,
        output_path=os.path.join(ROOT, "data", "processed", "delivery_output.csv"),
        limit=limit,
        internal_json_path=INTERNAL_JSON,
    )
    with open(INTERNAL_JSON, encoding="utf-8") as f:
        return json.load(f)


def _compute_metrics(products):
    n = len(products)
    if n == 0:
        return {
            "n_products": 0, "high_confidence": 0, "needs_review": 0,
            "validation_failures": 0, "grounding_rate": 0.0,
            "lov_compliance_rate": 0.0, "uom_compliance_rate": 0.0,
            "avg_confidence": 0.0, "field_accuracy": None,
        }

    from src.validation.validator import validate_product
    from src.validation.confidence import compute_confidence

    high = 0
    review = 0
    val_failures = 0
    grounding = 0.0
    lov = 0.0
    uom = 0.0
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
        "field_accuracy": None,  # requires the 200-row labelled evaluation (scripts/evaluate_200.py)
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    products = _load_internal_products(args.limit)
    metrics = _compute_metrics(products)

    os.makedirs(FRONTEND_DATA, exist_ok=True)
    with open(os.path.join(FRONTEND_DATA, "products.json"), "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2, default=str)
    with open(os.path.join(FRONTEND_DATA, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(products)} products -> {os.path.join(FRONTEND_DATA, 'products.json')}")
    print(f"Wrote metrics -> {os.path.join(FRONTEND_DATA, 'metrics.json')}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()