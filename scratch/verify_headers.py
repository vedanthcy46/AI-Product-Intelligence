import os
import sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

EXPECTED_OUTPUT_PATH = os.path.join(ROOT, "data", "reference", "Unihack_ Expected Output - Delivery Format.csv")
BULK_OUTPUT_PATH = os.path.join(ROOT, "scratch", "bulk_1000_delivery_output.csv")
REGRESSION_OUTPUT_PATH = os.path.join(ROOT, "scratch", "ground_truth_regression_output.csv")

print("=" * 74)
print("  CRITICAL HEADER INTEGRITY & COLUMN ORDER VERIFICATION")
print("=" * 74)

if not os.path.exists(EXPECTED_OUTPUT_PATH):
    print(f"  [SKIP] Expected output reference file not found: {EXPECTED_OUTPUT_PATH}")
    print("  Place the delivery format CSV at data/reference/ to run this check.")
    sys.exit(0)

expected_cols = list(pd.read_csv(EXPECTED_OUTPUT_PATH, nrows=0, encoding="utf-8").columns)
print(f"  Expected Column Count : {len(expected_cols)}")

for label, path in [("Bulk Export", BULK_OUTPUT_PATH), ("Regression Export", REGRESSION_OUTPUT_PATH)]:
    if not os.path.exists(path):
        print(f"  [SKIP] {label} file not found: {path}")
        continue
    df = pd.read_csv(path, nrows=0, encoding="utf-8")
    cols = list(df.columns)
    match = cols == expected_cols
    print(f"  {label} Column Count : {len(cols)}  |  Match: {match}")
    if not match:
        missing = set(expected_cols) - set(cols)
        extra = set(cols) - set(expected_cols)
        if missing:
            print(f"    Missing cols: {list(missing)[:5]}")
        if extra:
            print(f"    Extra cols:   {list(extra)[:5]}")
        sys.exit(1)

print("=" * 74)
print("  HEADER INTEGRITY CHECK PASSED [OK]")
print("=" * 74)
