"""
evaluate_200.py -- Run the complete pipeline over the 200 labelled rows and
score every metric against the ground-truth delivery output.

Metrics: field accuracy, LOV/UOM compliance, grounding rate, review rate.
See docs/evaluation.md for formulas.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DATA = os.path.join(ROOT, "data", "reference")
INPUT_CSV = os.path.join(ROOT, "data", "raw", "Unihack_ Sample Dataset - Input.csv")
GT_XLSX = os.path.join(DATA, "Unilog-Sample_200_Items-Input-vs-Output.xlsx")
MASTER = os.path.join(DATA, "UniCat_Manufacturer_and_Brand_List.xlsx")


def _require(path, label, fatal=True):
    if not os.path.exists(path):
        if fatal:
            sys.exit(f"[evaluate_200] Missing required file {label}: {path}\n"
                     f"Data files are supplied locally (gitignored). Add them under data/.")
        print(f"[evaluate_200] Warning: {label} not found at {path} — "
              f"running in pass-through mode (manufacturer/brand unmatched, low confidence).")
        return False
    return True


def main():
    _require(INPUT_CSV, "200/1000-row input")
    _require(GT_XLSX, "ground-truth evaluation set")
    _require(MASTER, "manufacturer/brand master", fatal=False)

    import pandas as pd
    from src.pipeline.batch import process_batch
    from src.evaluation.metrics import full_evaluation

    # Ground truth: read expected columns for the 200 rows.
    gt = pd.read_excel(GT_XLSX, dtype=str).fillna("")
    gt_records = gt.to_dict("records")

    # Pipeline prediction over the same 200 rows (first 200 of the full input,
    # matched by Mfg_Part_Num when the labelled file aligns).
    raw = pd.read_csv(INPUT_CSV, encoding="utf-8")
    if len(raw) < 200:
        sys.exit(f"[evaluate_200] Input has {len(raw)} rows; expected >= 200.")

    predicted_csv = os.path.join(ROOT, "data", "processed", "evaluation_200_output.csv")
    predicted_df = process_batch(raw, master_path=MASTER, output_path=predicted_csv, limit=200)
    predicted_records = predicted_df.to_dict("records")

    known_uoms = {"V", "A", "W", "kW", "in", "ft", "mm", "cm", "m", "lb", "kg",
                  "oz", "g", "dBA", "dB", "%", "psi", "RPM", "CFM", "HP", "BTU",
                  "BTUH", "hr", "min", "pc", "ea", "pk", "pr", "set", "kW-hr",
                  "\u00b0F", "\u00b0C"}

    report = full_evaluation(
        predicted_products=predicted_records,
        expected_products=gt_records,
        known_uoms=known_uoms,
    )

    print("\n===================== 200-ROW EVALUATION =====================")
    print(f"n_evaluated:            {report['n_evaluated']}")
    fa = report["field_accuracy"]
    print(f"field_accuracy:         {fa.get('accuracy', 'n/a')}")
    print(f"  per-field:            {fa.get('field_accuracy', {})}")
    print(f"LOV compliance rate:    {report['lov_compliance_rate']:.2%}")
    print(f"UOM compliance rate:    {report['uom_compliance_rate']:.2%}")
    print(f"grounding rate:         {report['grounding_rate']:.2%}")
    print(f"review rate:            {report['review_rate']:.2%}")
    if report.get("warning"):
        print(f"warning:                {report['warning']}")
    print("===============================================================")

    import json
    report_path = os.path.join(ROOT, "data", "processed", "evaluation_200_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()