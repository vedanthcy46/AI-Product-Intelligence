"""
report.py -- Human-readable reporting of evaluation metrics.
"""

from typing import Dict, Any


def print_report(metrics: Dict[str, Any], label: str = "Ground Truth Evaluation") -> None:
    """
    Print a cleanly formatted console report for evaluation metrics.
    """
    print()
    print("=" * 68)
    print(f"  === {label.upper()} ===")
    print("=" * 68)

    # Check for warning (e.g. small sample size)
    warning = metrics.get("warning")
    if warning:
        print(f"  [!] NOTE: {warning.upper()}")
        print("-" * 68)

    # 1. Ground Truth Full Evaluation Structure
    if "field_accuracy" in metrics:
        fa = metrics["field_accuracy"]
        print(f"  Evaluated Rows       : {metrics.get('n_evaluated', fa.get('n_rows', '?'))}")
        print(f"  Overall Field Acc    : {fa.get('overall', 0.0):.1%}")
        print(f"  LOV Compliance Rate  : {metrics.get('lov_compliance_rate', 0.0):.1%}")
        print(f"  UOM Compliance Rate  : {metrics.get('uom_compliance_rate', 0.0):.1%}")
        print(f"  Grounding Rate       : {metrics.get('grounding_rate', 0.0):.1%}")
        print(f"  Human Review Rate    : {metrics.get('review_rate', 0.0):.1%}")

        if "per_field" in fa and fa["per_field"]:
            print("\n  Per-Field Accuracy Breakdown:")
            for field, acc in fa["per_field"].items():
                print(f"    - {field:<24} : {acc:>6.1%}")

    # 2. Structural Completeness Report (for Bulk runs)
    elif "avg_attributes_per_product" in metrics:
        print(f"  Total Products Processed  : {metrics.get('n_products', 0)}")
        print(f"  Classpath Populated       : {metrics.get('classpath_populated_pct', 0.0):.1%}")
        print(f"  Manufacturer Populated    : {metrics.get('manufacturer_populated_pct', 0.0):.1%}")
        print(f"  Brand Name Populated      : {metrics.get('brand_populated_pct', 0.0):.1%}")
        print(f"  Avg Attributes / Product  : {metrics.get('avg_attributes_per_product', 0.0)}")
        print(f"  Needs Human Review        : {metrics.get('needs_review_pct', 0.0):.1%}")

    print("=" * 68)
    print()
