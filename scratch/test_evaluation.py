"""
test_evaluation.py -- Y9 Evaluation Framework test.

Tests field_accuracy, full_evaluation, print_report, and structural_completeness.
Deliberately introduces field mismatches to confirm they are NOT silently masked.
"""

import sys
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.evaluation.field_accuracy import field_accuracy, compare_field
from src.evaluation.metrics import full_evaluation, structural_completeness
from src.evaluation.report import print_report

KNOWN_UOMS = {"V", "A", "W", "kW", "in", "ft", "mm", "cm", "m",
              "lb", "kg", "oz", "g", "dBA", "dB", "%", "psi",
              "RPM", "CFM", "HP", "BTU", "BTUH", "hr", "min",
              "pc", "ea", "pk", "pr", "set", "kW-hr"}

# ── Expected (ground truth proxies) ──────────────────────────────────────────
EXPECTED = [
    {
        "MANUFACTURER_NAME":     "Rheem Manufacturing",
        "BRAND_NAME":            "FRIGIDAIRE",
        "Classpath":             "Appliances>Kitchen>Dishwashers",
        "INVOICE_DESC":          "DISHWASHER LEG 5 SST 120V 15A",
        "Material":              "Stainless Steel",
        "Voltage Rating":        "120",
        "Sound Level":           "47",
        "descriptions":          {"INVOICE_DESC": "DISHWASHER LEG 5 SST 120V 15A"},
        "attributes": [
            {"label": "Material", "value": "Stainless Steel", "uom": None, "source": "mfr_page", "lov_matched": True, "needs_review": False},
            {"label": "Voltage Rating", "value": "120", "uom": "V", "source": "spec_sheet", "lov_matched": True, "needs_review": False},
        ],
    },
    {
        "MANUFACTURER_NAME":     "Whirlpool Corporation",
        "BRAND_NAME":            "Whirlpool",
        "Classpath":             "Appliances>Kitchen>Dishwashers",
        "INVOICE_DESC":          "DISHWASHER BLTLN SST SST 120V 10A 41DBA",
        "Material":              "Stainless Steel",
        "Voltage Rating":        "120",
        "Sound Level":           "41",
        "descriptions":          {"INVOICE_DESC": "DISHWASHER BLTLN SST SST 120V 10A 41DBA"},
        "attributes": [
            {"label": "Material", "value": "Stainless Steel", "uom": None, "source": "mfr_page", "lov_matched": True, "needs_review": False},
            {"label": "Voltage Rating", "value": "120", "uom": "V", "source": "spec_sheet", "lov_matched": True, "needs_review": False},
        ],
    },
]

# Predicted — deliberately WRONG on 3 fields
PREDICTED = [
    {
        "MANUFACTURER_NAME":     "Rheem Manufacturing",
        "BRAND_NAME":            "FRIGIDAIRE",
        "Classpath":             "Appliances>Kitchen>Dishwashers",
        "INVOICE_DESC":          "DISHWASHER LEG 5 SST 120V 15A",
        "Material":              "Carbon Fiber",   # WRONG
        "Voltage Rating":        "240",            # WRONG
        "Sound Level":           "47",
        "descriptions":          {"INVOICE_DESC": "DISHWASHER LEG 5 SST 120V 15A"},
        "attributes": [
            {"label": "Material", "value": "Carbon Fiber", "uom": None, "source": "mfr_page", "lov_matched": False, "needs_review": True},
            {"label": "Voltage Rating", "value": "240", "uom": "V", "source": "spec_sheet", "lov_matched": True, "needs_review": False},
        ],
    },
    {
        "MANUFACTURER_NAME":     "Whirlpool Corporation",
        "BRAND_NAME":            "Whirlpool",
        "Classpath":             "Appliances>Kitchen>Dishwashers",
        "INVOICE_DESC":          "DISHWASHER BLTLN SST SST 120V 10A 41DBA",
        "Material":              "Stainless Steel",
        "Voltage Rating":        "120",
        "Sound Level":           "55",             # WRONG
        "descriptions":          {"INVOICE_DESC": "DISHWASHER BLTLN SST SST 120V 10A 41DBA"},
        "attributes": [
            {"label": "Material", "value": "Stainless Steel", "uom": None, "source": "mfr_page", "lov_matched": True, "needs_review": False},
            {"label": "Voltage Rating", "value": "120", "uom": "V", "source": "spec_sheet", "lov_matched": True, "needs_review": False},
        ],
    },
]

EVAL_FIELDS = [
    "MANUFACTURER_NAME", "BRAND_NAME", "Classpath",
    "INVOICE_DESC", "Material", "Voltage Rating", "Sound Level",
]

# ── 1. field_accuracy() ───────────────────────────────────────────────────────
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

# ── Assertions ────────────────────────────────────────────────────────────────
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
check("Material mismatch detected (acc < 1.0)",      fa_result["per_field"]["Material"] < 1.0, True)
check("Voltage Rating mismatch detected (acc < 1.0)", fa_result["per_field"]["Voltage Rating"] < 1.0, True)
check("Sound Level mismatch detected (acc < 1.0)",   fa_result["per_field"]["Sound Level"] < 1.0, True)
check("MANUFACTURER_NAME matches (acc == 1.0)",      fa_result["per_field"]["MANUFACTURER_NAME"], 1.0)
check("BRAND_NAME matches (acc == 1.0)",             fa_result["per_field"]["BRAND_NAME"], 1.0)
check("INVOICE_DESC matches (acc == 1.0)",           fa_result["per_field"]["INVOICE_DESC"], 1.0)
check("overall < 1.0 (not silently masked)",         fa_result["overall"] < 1.0, True)
check("n_rows == 2",                                 fa_result["n_rows"], 2)
check("small-sample warning present",                "warning" in fa_result, True)

# ── 2. full_evaluation() ──────────────────────────────────────────────────────
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

check("full_eval: small-sample warning present",     "warning" in eval_result, True)
check("full_eval: n_evaluated == 2",                 eval_result.get("n_evaluated"), 2)
check("full_eval: review_rate > 0 (Row 0 has LOV mismatch)", eval_result.get("review_rate", 0.0) > 0.0, True)

# ── 3. print_report() ─────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("  Y9 TEST 3: print_report() console output")
print("=" * 68)
print_report(eval_result, label="Y9 Ground Truth Evaluation (n=2)")

# ── 4. structural_completeness() ─────────────────────────────────────────────
print("=" * 68)
print("  Y9 TEST 4: structural_completeness() on mock products")
print("=" * 68)

BULK_CSV = os.path.join(ROOT, "scratch", "bulk_1000_delivery_output.csv")
if os.path.exists(BULK_CSV):
    import pandas as pd
    bulk_df = pd.read_csv(BULK_CSV, keep_default_na=False)
    bulk_products = [
        {
            "Classpath":         row.get("Classpath", ""),
            "MANUFACTURER_NAME": row.get("MANUFACTURER_NAME", ""),
            "BRAND_NAME":        row.get("BRAND_NAME", ""),
            "attributes":        [],
            "needs_review":      False,
        }
        for _, row in bulk_df.iterrows()
    ]
    sc_result = structural_completeness(bulk_products)
    print_report(sc_result, label="Bulk Structural Completeness")
    check("structural: n_products == 1000", sc_result["n_products"], 1000)
else:
    # Run on the mock PREDICTED data instead
    sc_result = structural_completeness(PREDICTED)
    print_report(sc_result, label="Mock Structural Completeness (no bulk CSV)")
    check("structural: n_products == 2", sc_result["n_products"], 2)
    print("  [INFO] Place bulk_1000_delivery_output.csv in scratch/ for full 1000-row test.")

# ── Final summary ─────────────────────────────────────────────────────────────
print("=" * 68)
if all_pass:
    print("  Y9 EVALUATION FRAMEWORK: All assertions passed (OK)")
else:
    print("  Y9 EVALUATION FRAMEWORK: SOME ASSERTIONS FAILED -- see above")
print("=" * 68)

sys.exit(0 if all_pass else 1)
