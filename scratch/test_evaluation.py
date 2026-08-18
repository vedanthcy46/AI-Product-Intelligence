"""
test_evaluation.py -- Y9 Evaluation Framework test.

Tests field_accuracy, full_evaluation, print_report, and structural_completeness.
Deliberately introduces field mismatches to confirm they are NOT silently masked.
"""

import sys
import os
sys.path.insert(0, r"C:\Users\Yashas BR\OneDrive\Desktop\Hack2skills")

import pandas as pd
from src.evaluation.field_accuracy import field_accuracy, compare_field
from src.evaluation.metrics import full_evaluation, structural_completeness
from src.evaluation.report import print_report

BULK_CSV = r"C:\Users\Yashas BR\OneDrive\Desktop\Hack2skills\scratch\bulk_1000_delivery_output.csv"

KNOWN_UOMS = {"V", "A", "W", "kW", "in", "ft", "mm", "cm", "m",
              "lb", "kg", "oz", "g", "dBA", "dB", "%", "psi",
              "RPM", "CFM", "HP", "BTU", "BTUH", "hr", "min",
              "pc", "ea", "pk", "pr", "set", "kW-hr"}

# ──────────────────────────────────────────────────────────────────────────────
# 1.  PREDICTED vs EXPECTED — with deliberate mismatches
# ──────────────────────────────────────────────────────────────────────────────
# Expected (ground truth proxies)
EXPECTED = [
    {
        "MANUFACTURER_NAME":     "Rheem Manufacturing",           # correct
        "BRAND_NAME":            "FRIGIDAIRE",                    # correct
        "Classpath":             "Appliances>Kitchen>Dishwashers",
        "INVOICE_DESC":          "DISHWASHER LEG 5 SST 120V 15A",
        "Material":              "Stainless Steel",               # correct
        "Voltage Rating":        "120",                           # correct
        "Sound Level":           "47",                           # correct
        "descriptions":          {"INVOICE_DESC": "DISHWASHER LEG 5 SST 120V 15A"},
        "attributes": [
            {"label": "Material", "value": "Stainless Steel", "uom": None, "source": "mfr_page", "lov_matched": True, "needs_review": False},
            {"label": "Voltage Rating", "value": "120", "uom": "V", "source": "spec_sheet", "lov_matched": True, "needs_review": False},
        ],
    },
    {
        "MANUFACTURER_NAME":     "Whirlpool Corporation",         # correct
        "BRAND_NAME":            "Whirlpool",                    # correct
        "Classpath":             "Appliances>Kitchen>Dishwashers",
        "INVOICE_DESC":          "DISHWASHER BLTLN SST SST 120V 10A 41DBA",
        "Material":              "Stainless Steel",               # correct
        "Voltage Rating":        "120",                           # correct
        "Sound Level":           "41",                           # correct
        "descriptions":          {"INVOICE_DESC": "DISHWASHER BLTLN SST SST 120V 10A 41DBA"},
        "attributes": [
            {"label": "Material", "value": "Stainless Steel", "uom": None, "source": "mfr_page", "lov_matched": True, "needs_review": False},
            {"label": "Voltage Rating", "value": "120", "uom": "V", "source": "spec_sheet", "lov_matched": True, "needs_review": False},
        ],
    },
]

# Predicted (pipeline output) — deliberately WRONG on 3 fields:
#   Row 0:  Material="Carbon Fiber" (wrong),  Voltage Rating="240" (wrong)
#   Row 1:  Sound Level="55" (wrong)
PREDICTED = [
    {
        "MANUFACTURER_NAME":     "Rheem Manufacturing",           # correct
        "BRAND_NAME":            "FRIGIDAIRE",                    # correct
        "Classpath":             "Appliances>Kitchen>Dishwashers",
        "INVOICE_DESC":          "DISHWASHER LEG 5 SST 120V 15A",
        "Material":              "Carbon Fiber",   # <<< WRONG — mismatch 1
        "Voltage Rating":        "240",            # <<< WRONG — mismatch 2
        "Sound Level":           "47",             # correct
        "descriptions":          {"INVOICE_DESC": "DISHWASHER LEG 5 SST 120V 15A"},
        "attributes": [
            {"label": "Material", "value": "Carbon Fiber", "uom": None, "source": "mfr_page", "lov_matched": False, "needs_review": True},
            {"label": "Voltage Rating", "value": "240", "uom": "V", "source": "spec_sheet", "lov_matched": True, "needs_review": False},
        ],
    },
    {
        "MANUFACTURER_NAME":     "Whirlpool Corporation",         # correct
        "BRAND_NAME":            "Whirlpool",                    # correct
        "Classpath":             "Appliances>Kitchen>Dishwashers",
        "INVOICE_DESC":          "DISHWASHER BLTLN SST SST 120V 10A 41DBA",
        "Material":              "Stainless Steel",               # correct
        "Voltage Rating":        "120",                           # correct
        "Sound Level":           "55",             # <<< WRONG — mismatch 3
        "descriptions":          {"INVOICE_DESC": "DISHWASHER BLTLN SST SST 120V 10A 41DBA"},
        "attributes": [
            {"label": "Material", "value": "Stainless Steel", "uom": None, "source": "mfr_page", "lov_matched": True, "needs_review": False},
            {"label": "Voltage Rating", "value": "120", "uom": "V", "source": "spec_sheet", "lov_matched": True, "needs_review": False},
        ],
    },
]

EVAL_FIELDS = [
    "MANUFACTURER_NAME",
    "BRAND_NAME",
    "Classpath",
    "INVOICE_DESC",
    "Material",
    "Voltage Rating",
    "Sound Level",
]

# ──────────────────────────────────────────────────────────────────────────────
# 2.  field_accuracy()
# ──────────────────────────────────────────────────────────────────────────────
print("=" * 68)
print("  Y9 TEST 1: field_accuracy() with 3 deliberate mismatches")
print("=" * 68)

fa_result = field_accuracy(PREDICTED, EXPECTED, EVAL_FIELDS)
print(f"  n_rows  : {fa_result['n_rows']}")
print(f"  overall : {fa_result['overall']:.1%}")
print(f"  warning : {fa_result.get('warning', 'none')}")
print("\n  Per-Field Accuracy:")
for field, acc in fa_result["per_field"].items():
    hit = "(MATCH)" if acc == 1.0 else "(MISMATCH DETECTED)"
    print(f"    - {field:<24} : {acc:.1%}  {hit}")

# ──────────────────────────────────────────────────────────────────────────────
# 3.  Assertions on field_accuracy
# ──────────────────────────────────────────────────────────────────────────────
all_pass = True
def check(desc, got, expected):
    global all_pass
    ok = (got == expected)
    if not ok:
        all_pass = False
    print(f"  {'PASS' if ok else 'FAIL'}  {desc}")
    if not ok:
        print(f"         expected: {expected!r}")
        print(f"         got:      {got!r}")
    return ok

print("\n  field_accuracy() assertions:")
# 3 of 7 fields should show mismatch (0.5 or 0.0 accuracy, not 1.0)
check("Material mismatch detected (acc < 1.0)",
      fa_result["per_field"]["Material"] < 1.0, True)
check("Voltage Rating mismatch detected (acc < 1.0)",
      fa_result["per_field"]["Voltage Rating"] < 1.0, True)
check("Sound Level mismatch detected (acc < 1.0)",
      fa_result["per_field"]["Sound Level"] < 1.0, True)
# Correct fields should be 1.0
check("MANUFACTURER_NAME matches (acc == 1.0)",
      fa_result["per_field"]["MANUFACTURER_NAME"], 1.0)
check("BRAND_NAME matches (acc == 1.0)",
      fa_result["per_field"]["BRAND_NAME"], 1.0)
check("INVOICE_DESC matches (acc == 1.0)",
      fa_result["per_field"]["INVOICE_DESC"], 1.0)
# Overall should be <1.0 (3/7 mismatches = 4/7 correct = 0.5714)
check("overall < 1.0 (not silently masked)",
      fa_result["overall"] < 1.0, True)
check("n_rows == 2",
      fa_result["n_rows"], 2)
check("small-sample warning present",
      "warning" in fa_result, True)

# ──────────────────────────────────────────────────────────────────────────────
# 4.  full_evaluation()
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("  Y9 TEST 2: full_evaluation() complete result")
print("=" * 68)

eval_result = full_evaluation(PREDICTED, EXPECTED, KNOWN_UOMS, EVAL_FIELDS)
print(f"  n_evaluated          : {eval_result.get('n_evaluated')}")
print(f"  field_accuracy.overall : {eval_result['field_accuracy']['overall']:.1%}")
print(f"  lov_compliance_rate  : {eval_result.get('lov_compliance_rate', 0.0):.1%}")
print(f"  uom_compliance_rate  : {eval_result.get('uom_compliance_rate', 0.0):.1%}")
print(f"  grounding_rate       : {eval_result.get('grounding_rate', 0.0):.1%}")
print(f"  review_rate          : {eval_result.get('review_rate', 0.0):.1%}")
print(f"  warning              : {eval_result.get('warning', 'none')}")

check("full_eval: small-sample warning present",
      "warning" in eval_result, True)
check("full_eval: n_evaluated == 2",
      eval_result.get("n_evaluated"), 2)
check("full_eval: review_rate > 0 (Row 0 has LOV mismatch)",
      eval_result.get("review_rate", 0.0) > 0.0, True)

# ──────────────────────────────────────────────────────────────────────────────
# 5.  print_report()
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("  Y9 TEST 3: print_report() console output (must show small-sample warning)")
print("=" * 68)
print_report(eval_result, label="Y9 Ground Truth Evaluation (n=2)")

# ──────────────────────────────────────────────────────────────────────────────
# 6.  structural_completeness() on 1000-row bulk output
# ──────────────────────────────────────────────────────────────────────────────
print("=" * 68)
print("  Y9 TEST 4: structural_completeness() on 1000-row bulk CSV")
print("=" * 68)

if not os.path.exists(BULK_CSV):
    print(f"  [!] Bulk CSV not found: {BULK_CSV}")
    print("  [!] Re-running 1000-row structural evaluation...")
    import subprocess
    subprocess.run([sys.executable, "scratch/run_1000_row_structural_evaluation.py"], check=True)

bulk_df = pd.read_csv(BULK_CSV, keep_default_na=False)

# Convert rows to product-like dicts for structural_completeness()
# structural_completeness looks for: Classpath, MANUFACTURER_NAME, BRAND_NAME, attributes, needs_review
bulk_products = []
for _, row in bulk_df.iterrows():
    bulk_products.append({
        "Classpath":         row.get("Classpath", ""),
        "MANUFACTURER_NAME": row.get("MANUFACTURER_NAME", ""),
        "BRAND_NAME":        row.get("BRAND_NAME", ""),
        "attributes":        [],   # flat CSV: no nested attributes; omit for completeness check
        "needs_review":      False,
    })

sc_result = structural_completeness(bulk_products)
print_report(sc_result, label="1000-Row Bulk Structural Completeness")

print("  Raw result dict:")
for k, v in sc_result.items():
    print(f"    {k}: {v}")

# Sanity checks
check("structural: n_products == 1000",
      sc_result["n_products"], 1000)
check("structural: classpath_populated_pct > 0.50 and < 1.0 (not near 0 or 100%)",
      0.50 < sc_result["classpath_populated_pct"] < 1.0, True)
check("structural: manufacturer_populated_pct > 0.50",
      sc_result["manufacturer_populated_pct"] > 0.50, True)

# ──────────────────────────────────────────────────────────────────────────────
# Final summary
# ──────────────────────────────────────────────────────────────────────────────
print("=" * 68)
if all_pass:
    print("  Y9 EVALUATION FRAMEWORK: All assertions passed (OK)")
else:
    print("  Y9 EVALUATION FRAMEWORK: SOME ASSERTIONS FAILED -- see above")
print("=" * 68)

sys.exit(0 if all_pass else 1)
