"""
evaluate_1000.py -- Run the pipeline over the 1,000-row working dataset and
produce a structural completeness report (no labels available).

Report: total processing time, success rate, review rate, validation failures,
missing sources, average confidence, and structural completeness metrics.
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

INPUT_CSV = os.path.join(ROOT, "data", "raw", "Unihack_ Sample Dataset - Input.csv")
MASTER = os.path.join(ROOT, "data", "reference", "UniCat_Manufacturer_and_Brand_List.xlsx")


def _require(path, label, fatal=True):
    if not os.path.exists(path):
        if fatal:
            sys.exit(f"[evaluate_1000] Missing required file {label}: {path}")
        print(f"[evaluate_1000] Warning: {label} not found at {path} — running in pass-through mode "
              f"(manufacturer/brand unmatched, low confidence).")
        return False
    return True


def main():
    _require(INPUT_CSV, "1000-row input")
    _require(MASTER, "manufacturer/brand master", fatal=False)

    import pandas as pd
    from src.pipeline.batch import process_batch
    from src.evaluation.metrics import structural_completeness
    from src.validation.validator import validate_product
    from src.validation.confidence import compute_confidence

    raw = pd.read_csv(INPUT_CSV, encoding="utf-8")
    out_csv = os.path.join(ROOT, "data", "processed", "delivery_1000_output.csv")

    print(f"Processing {len(raw)} rows...")
    start = time.time()
    predicted_df = process_batch(raw, master_path=MASTER, output_path=out_csv)
    elapsed = time.time() - start

    records = predicted_df.to_dict("records")

    # Validation & confidence over the delivered rows
    known_uoms = {"V", "A", "W", "kW", "in", "ft", "mm", "cm", "m", "lb", "kg",
                  "oz", "g", "dBA", "dB", "%", "psi", "RPM", "CFM", "HP", "BTU",
                  "BTUH", "hr", "min", "pc", "ea", "pk", "pr", "set", "kW-hr",
                  "\u00b0F", "\u00b0C"}
    review_count = 0
    valid_count = 0
    missing_source_products = 0
    confidences = []

    for r in records:
        attrs = []
        # Reconstruct attribute list from the 50 attribute slots
        for i in range(1, 51):
            label = r.get(f"ATTRIBUTE_LABEL {i}") or ""
            if not label:
                continue
            attrs.append({
                "label": label,
                "value": r.get(f"ATTRIBUTE_VALUE {i}") or None,
                "uom": r.get(f"ATTRIBUTE_UOM {i}") or None,
                "source": None,  # source provenance is an internal field, not in delivery
            })
        product = {
            "attributes": attrs,
            "descriptions": {
                f: r.get(f) or "" for f in [
                    "MOBILE_DESC", "INVOICE_DESC", "SHORT_DESC",
                    "LONG_DESC1", "RETAIL_DESC", "MARKETING_DESCRIPTION",
                ]
            },
            "classpath": r.get("Classpath") or "",
            "manufacturer_name": r.get("MANUFACTURER_NAME") or "",
            "brand_name": r.get("BRAND_NAME") or "",
        }
        val = validate_product(product, known_uoms)
        conf = compute_confidence(product, val)
        if val["valid"]:
            valid_count += 1
        if conf["needs_review"]:
            review_count += 1
        grounded = [a for a in attrs if a.get("value")]
        if grounded and not any(a.get("source") for a in grounded):
            missing_source_products += 1
        confidences.append(conf["overall_confidence"])

    structural = structural_completeness(records)

    print("\n=================== 1000-ROW SCALE REPORT ====================")
    print(f"total processing time:     {elapsed:.1f}s")
    print(f"rows processed:            {len(records)}")
    print(f"success rate (valid):      {valid_count / max(len(records), 1):.2%}")
    print(f"review rate:               {review_count / max(len(records), 1):.2%}")
    print(f"validation failures:       {len(records) - valid_count}")
    print(f"products missing sources:  {missing_source_products}")
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    print(f"average confidence:        {avg_conf:.2%}")
    print("--- structural completeness ---")
    for k, v in structural.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2%}" if v <= 1 else f"  {k}: {v:.2f}")
        else:
            print(f"  {k}: {v}")
    print(f"output written to:         {out_csv}")
    print("===============================================================")


if __name__ == "__main__":
    main()