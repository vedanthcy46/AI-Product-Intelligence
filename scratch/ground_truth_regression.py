"""
Ground-Truth Regression Test
Reconstructs both real ground-truth products (Frigidaire & Whirlpool),
runs them through the complete pipeline, exports to CSV, and performs a
field-by-field diff across all 252 columns against the official reference CSV.
"""

import os
import sys
import pandas as pd

ROOT = r"C:\Users\Yashas BR\OneDrive\Desktop\Hack2skills"
sys.path.insert(0, ROOT)

from schema import Product
from src.attributes.mapper import normalize_candidate_attribute
from src.validation.validator import validate_product
from src.validation.confidence import compute_confidence
from src.output.mapper import product_to_row, get_expected_headers
from src.output.exporter import export_to_csv

KNOWN_UOMS = {"V", "A", "W", "kW", "in", "ft", "mm", "cm", "m",
              "lb", "kg", "oz", "g", "dBA", "dB", "%", "psi",
              "RPM", "CFM", "HP", "BTU", "BTUH", "hr", "min",
              "pc", "ea", "pk", "pr", "set", "kW-hr", "°F", "°C"}

EXPECTED_CSV = os.path.join(ROOT, "data", "reference", "Unihack_ Expected Output - Delivery Format.csv")
REGRESSION_EXPORT_CSV = os.path.join(ROOT, "scratch", "ground_truth_regression_output.csv")

print("=" * 74)
print("  STEP 1: ISOLATED FRACTION & WHOLE-NUMBER CONVERSION CHECKS")
print("=" * 74)

# --- ISOLATED FRACTION-CONVERSION CHECK (not part of ground-truth row export) ---
isolated_test_candidates = [
    {
        "label": "Test Fraction Conversion",
        "candidate_value": "50.25",
        "candidate_uom": "inches",
        "source": "spec_sheet",
        "confidence": 0.90,
    },
    {
        "label": "Test Whole Number Passthrough",
        "candidate_value": "24.0",
        "candidate_uom": "in",
        "source": "spec_sheet",
        "confidence": 0.90,
    },
]

isolated_test_attrs = [
    normalize_candidate_attribute("Appliances", c)
    for c in isolated_test_candidates
]

print("Fraction conversion test ->", [a for a in isolated_test_attrs if a.label == "Test Fraction Conversion"])
print("Whole number test        ->", [a for a in isolated_test_attrs if a.label == "Test Whole Number Passthrough"])

frac_test_attr = next(a for a in isolated_test_attrs if a.label == "Test Fraction Conversion")
assert frac_test_attr.value == "50-1/4", (
    f"Assertion Failed: 'Test Fraction Conversion' value expected '50-1/4', got {frac_test_attr.value!r}"
)
assert frac_test_attr.uom == "in", (
    f"Assertion Failed: 'Test Fraction Conversion' uom expected 'in', got {frac_test_attr.uom!r}"
)

whole_test_attr = next(a for a in isolated_test_attrs if a.label == "Test Whole Number Passthrough")
assert whole_test_attr.value == "24", (
    f"Assertion Failed: 'Test Whole Number Passthrough' value expected '24', got {whole_test_attr.value!r}"
)
assert whole_test_attr.uom == "in", (
    f"Assertion Failed: 'Test Whole Number Passthrough' uom expected 'in', got {whole_test_attr.uom!r}"
)

print("\n  [PASS] Isolated Fraction & Whole-Number Normalization Assertions Passed.")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Construct Candidate Representations for Ground Truth Row 0 (Frigidaire)
# ─────────────────────────────────────────────────────────────────────────────
row0_candidates = [
    {"label": "Series", "candidate_value": "Professional Series", "candidate_uom": None, "source": "mfr_page", "confidence": 0.95},
    {"label": "Model", "candidate_value": None, "candidate_uom": None, "source": None, "confidence": 0.50},
    {"label": "Number of Wash Cycles", "candidate_value": "5", "candidate_uom": None, "source": "mfr_page", "confidence": 0.95},
    {"label": "Voltage Rating", "candidate_value": "120", "candidate_uom": "volts", "source": "spec_sheet", "confidence": 0.95},
    {"label": "Amperage Rating", "candidate_value": "15", "candidate_uom": "amps", "source": "spec_sheet", "confidence": 0.95},
    {"label": "Mounting Type", "candidate_value": "Leg", "candidate_uom": None, "source": "spec_sheet", "confidence": 0.90},
    {"label": "Plug Type", "candidate_value": None, "candidate_uom": None, "source": None, "confidence": 0.50},
    {"label": "Size", "candidate_value": "24 in W x 24-1/4 in D", "candidate_uom": None, "source": "spec_sheet", "confidence": 0.90},
    {"label": "Depth With Door Open", "candidate_value": "50-1/4", "candidate_uom": "inches", "source": "spec_sheet", "confidence": 0.90},
    {"label": "Minimum Height", "candidate_value": "8-1/2 in Upper Rack, 11-1/4 in Lower Rack", "candidate_uom": None, "source": "spec_sheet", "confidence": 0.90},
    {"label": "Maximum Height", "candidate_value": "10-3/8 in Upper Rack, 13-1/4 in Lower Rack", "candidate_uom": None, "source": "spec_sheet", "confidence": 0.90},
    {"label": "Sound Level", "candidate_value": "47", "candidate_uom": "dBA", "source": "mfr_page", "confidence": 0.95},
    {"label": "Material", "candidate_value": "SS", "candidate_uom": None, "source": "mfr_page", "confidence": 0.95}, # tests LOV normalization -> Stainless Steel
    {"label": "Color", "candidate_value": None, "candidate_uom": None, "source": None, "confidence": 0.50},
    {"label": "Additional Information", "candidate_value": "240 kW-hr Annual Energy, 1 to 12 hr Delay Start Hours", "candidate_uom": None, "source": "spec_sheet", "confidence": 0.90},
]

row0_norm_attrs = [
    normalize_candidate_attribute("Appliances", c).model_dump()
    for c in row0_candidates
]

row0_product = {
    "MFR URL": "https://www.frigidaire.com/en/p/owner-center/product-support/PDSH4816AF",
    "PART_NUMBER": "20887830",
    "Dept": "Appliances",
    "Class": "Large Appliances",
    "Fine": "Dishwashers",
    "SKU - MY_PART_NUMBER": "1515863",
    "Mfg_Part_Num": "PDSH4816AF",
    "Part_Desc": "PDSH4816AF Dishwasher SS - Display Only",
    "E1_Brand": "-- Unbranded --",
    "Unilog_Brand": "-- No Unilog Brand --",
    "DIB_Brand": "-- No DIB Brand --",
    "Part_Manuf": "Appliance Dealers Cooperative (APPDE)",
    "MANUFACTURER_NAME": "Rheem Manufacturing",
    "BRAND_NAME": "FRIGIDAIRE®",
    "MANUFACTURER_PART_NUMBER": "PDSH4816AF",
    "Classpath": "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers",
    "With": "With CleanBoost™",
    "Standard/Approvals": "ASSE 1006|CEE Tier 2 Qualified|cUL Listed|ENERGY STAR Certified|NSF Certified|UL Listed",
    "Product Name": "Dishwasher",
    "Warranty": "1 Year Manufacturer, 1 Year Labor and Parts",
    "Alternate Image 1": "FRIGIDAIRE_PDSH4816AF_1.jpg",
    "Alternate Image 2": "FRIGIDAIRE_PDSH4816AF_2.jpg",
    "Alternate Image 3": "FRIGIDAIRE_PDSH4816AF_3.jpg",
    "Alternate Image 4": "FRIGIDAIRE_PDSH4816AF_4.jpg",
    "descriptions": {
        "MOBILE_DESC": "Rheem Manufacturing FRIGIDAIRE, Dishwasher, Professional Series, PDSH4816AF",
        "INVOICE_DESC": "DISHWASHER LEG 5 SST 120V 15A 50-1/4IN",
        "SHORT_DESC": "FRIGIDAIRE® Professional Series PDSH4816AF Dishwasher With CleanBoost™, Leg Mounting, 5-Wash Cycle, Stainless Steel",
        "LONG_DESC1": "FRIGIDAIRE® Dishwasher With CleanBoost™, Professional Series, 5 Wash Cycles, 120 V, 15 A, Leg Mounting, 24 in W x 24-1/4 in D, 50-1/4 in Depth With Door Open, 8-1/2 in Upper Rack, 11-1/4 in Lower Rack Minimum Height, 10-3/8 in Upper Rack, 13-1/4 in Lower Rack Maximum Height, 47 dBA Sound Level, Stainless Steel, Additional Information: 240 kW-hr Annual Energy, 1 to 12 hr Delay Start Hours",
        "RETAIL_DESC": "Professional Series Dishwasher, Leg Mounting, 5-Wash Cycle, Stainless Steel",
    },
    "attributes": row0_norm_attrs,
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. Construct Candidate Representations for Ground Truth Row 1 (Whirlpool)
# ─────────────────────────────────────────────────────────────────────────────
row1_candidates = [
    {"label": "Series", "candidate_value": "Eco Series", "candidate_uom": None, "source": "mfr_page", "confidence": 0.95},
    {"label": "Model", "candidate_value": None, "candidate_uom": None, "source": None, "confidence": 0.50},
    {"label": "Number of Wash Cycles", "candidate_value": None, "candidate_uom": None, "source": None, "confidence": 0.50},
    {"label": "Voltage Rating", "candidate_value": "120", "candidate_uom": "V", "source": "spec_sheet", "confidence": 0.95},
    {"label": "Amperage Rating", "candidate_value": "10", "candidate_uom": "A", "source": "spec_sheet", "confidence": 0.95},
    {"label": "Mounting Type", "candidate_value": "Built-in", "candidate_uom": None, "source": "spec_sheet", "confidence": 0.90},
    {"label": "Plug Type", "candidate_value": None, "candidate_uom": None, "source": None, "confidence": 0.50},
    {"label": "Size", "candidate_value": "33-7/16 in H x 23-7/8 in W x 22-5/8 in D", "candidate_uom": None, "source": "spec_sheet", "confidence": 0.90},
    {"label": "Depth With Door Open", "candidate_value": "50-3/16", "candidate_uom": "in", "source": "spec_sheet", "confidence": 0.90},
    {"label": "Minimum Height", "candidate_value": "33-7/16", "candidate_uom": "in", "source": "spec_sheet", "confidence": 0.90},
    {"label": "Maximum Height", "candidate_value": None, "candidate_uom": None, "source": None, "confidence": 0.50},
    {"label": "Sound Level", "candidate_value": "41", "candidate_uom": "dBA", "source": "mfr_page", "confidence": 0.95},
    {"label": "Material", "candidate_value": "Stainless Steel", "candidate_uom": None, "source": "mfr_page", "confidence": 0.95},
    {"label": "Color", "candidate_value": "Stainless Steel", "candidate_uom": None, "source": "mfr_page", "confidence": 0.95},
    {"label": "Additional Information", "candidate_value": "Folding Tines, Leak Detection System, Moisture Repellent Silverware Basket, Normal Cycle, Quick Wash Cycle, Sani Rinse Option, Sensor Cycle, Triple Wash Spray", "candidate_uom": None, "source": "spec_sheet", "confidence": 0.90},
]

row1_norm_attrs = [
    normalize_candidate_attribute("Appliances", c).model_dump()
    for c in row1_candidates
]

row1_features = [
    "3rd rack with extra wash action",
    "Adjustable 2nd Rack",
    "41 dBA",
    "Moisture Repellent Silverware Basket",
    "Sensor cycle",
    "Sani Rinse Option",
    "Leak Detection System",
    "Folding Tines",
    "Normal cycle",
    "Triple Wash Spray",
    "Quick Wash Cycle",
]

row1_product = {
    "MFR URL": "https://learnwhirlpool.com/smartsearchresults?searchtext=WDTS7024R",
    "Ref URL 1": "https://www.whirlpool.com/content/dam/global/documents/202412/owners-manual-w11323304-revj.pdf",
    "Ref URL 2": "https://www.whirlpool.com/content/dam/global/documents/202406/installation-instructions-w11323304-revG.pdf",
    "PART_NUMBER": "25286031",
    "Dept": "Appliances",
    "Class": "Large Appliances",
    "Fine": "Dishwashers",
    "SKU - MY_PART_NUMBER": "1515867",
    "Mfg_Part_Num": "WDTS7024RZ",
    "Part_Desc": "WDTS7024RZ Dishwasher SS - Display Only",
    "E1_Brand": "-- Unbranded --",
    "Unilog_Brand": "-- No Unilog Brand --",
    "DIB_Brand": "-- No DIB Brand --",
    "Part_Manuf": "Appliance Dealers Cooperative (APPDE)",
    "MANUFACTURER_NAME": "Whirlpool Corporation",
    "BRAND_NAME": "Whirlpool®",
    "MANUFACTURER_PART_NUMBER": "WDTS7024RZ",
    "Classpath": "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers",
    "With": "With Washing 3rd Rack, Water Repellent Silverware Basket",
    "Product Name": "Dishwasher",
    "features": row1_features,
    "descriptions": {
        "MOBILE_DESC": "Whirlpool, Dishwasher, Eco Series, WDTS7024RZ, Built-in Mounting",
        "INVOICE_DESC": "DISHWASHER BLTLN SST SST 120V 10A 41DBA",
        "SHORT_DESC": "Whirlpool® Eco Series WDTS7024RZ Dishwasher, Built-in Mounting, Stainless Steel, Stainless Steel",
        "LONG_DESC1": "Whirlpool® Dishwasher, Eco Series, 120 V, 10 A, Built-in Mounting, 33-7/16 in H x 23-7/8 in W x 22-5/8 in D, 50-3/16 in Depth With Door Open, 33-7/16 in Minimum Height, 41 dBA Sound Level, Stainless Steel, Stainless Steel, Additional Information: Folding Tines, Leak Detection System, Moisture Repellent Silverware Basket, Normal Cycle, Quick Wash Cycle, Sani Rinse Option, Sensor Cycle, Triple Wash Spray",
        "RETAIL_DESC": "Eco Series Dishwasher, Built-in Mounting, Stainless Steel, Stainless Steel",
        "MARKETING_DESCRIPTION": "Load more and run less with our quietest and largest capacity dishwasher. A 3rd Rack provides dedicated space for mugs and bowls, while an adjustable 2nd Rack helps fit all the dishes and pans your family piles up.",
    },
    "attributes": row1_norm_attrs,
}

# ─────────────────────────────────────────────────────────────────────────────
# 4. Pipeline Validation & Export
# ─────────────────────────────────────────────────────────────────────────────
products = [row0_product, row1_product]

for idx, p in enumerate(products):
    val_res = validate_product(p, KNOWN_UOMS)
    assert val_res["valid"] is True, f"Row {idx} failed validation: {val_res['issues']}"

export_to_csv(products, REGRESSION_EXPORT_CSV, EXPECTED_CSV)

# ─────────────────────────────────────────────────────────────────────────────
# 5. Field-by-Field Diff Across All 252 Columns
# ─────────────────────────────────────────────────────────────────────────────
expected_df = pd.read_csv(EXPECTED_CSV, encoding="utf-8", keep_default_na=False)
exported_df = pd.read_csv(REGRESSION_EXPORT_CSV, encoding="utf-8", keep_default_na=False)

headers_expected = expected_df.columns.tolist()
headers_exported = exported_df.columns.tolist()

print("\n" + "=" * 74)
print("  GROUND-TRUTH REGRESSION TEST REPORT (ALL 252 COLUMNS DIFF)")
print("=" * 74)

# 1. Structural Checks
print(f"  Expected Column Count : {len(headers_expected)}")
print(f"  Exported Column Count : {len(headers_exported)}")
print(f"  Column Order Match    : {headers_expected == headers_exported}")
print(f"  Total Rows Tested     : {len(exported_df)}")

assert len(headers_exported) == 252, "Column count must be 252!"
assert headers_expected == headers_exported, "Header names or order do not match!"

# 2. Specific Verification Focus Areas
print("\n" + "-" * 74)
print("  VERIFICATION FOCUS AREAS")
print("-" * 74)

for r_idx, name in [(0, "Row 0 - Frigidaire (PDSH4816AF)"), (1, "Row 1 - Whirlpool (WDTS7024RZ)")]:
    inv = exported_df["INVOICE_DESC"].iloc[r_idx]
    inv_exp = expected_df["INVOICE_DESC"].iloc[r_idx]
    img = exported_df["Product Image"].iloc[r_idx]
    img_exp = expected_df["Product Image"].iloc[r_idx]
    spec = exported_df["Specification Sheet"].iloc[r_idx]
    spec_exp = expected_df["Specification Sheet"].iloc[r_idx]
    brand = exported_df["BRAND_NAME"].iloc[r_idx]

    print(f"\n  [{name}]")
    print(f"    - INVOICE_DESC        : {repr(inv)} (len={len(inv)}, <=40: {len(inv)<=40}) [Match: {inv == inv_exp}]")
    print(f"    - BRAND_NAME          : {repr(brand)}")
    print(f"    - Product Image       : {repr(img)} [Match: {img == img_exp}]")
    print(f"    - Specification Sheet : {repr(spec)} [Match: {spec == spec_exp}]")

    # Attributes check (1..15)
    print("    - Key Attribute Slots:")
    for slot in [1, 2, 4, 8, 9, 12, 13]:
        lbl = exported_df[f"ATTRIBUTE_LABEL {slot}"].iloc[r_idx]
        val = exported_df[f"ATTRIBUTE_VALUE {slot}"].iloc[r_idx]
        uom = exported_df[f"ATTRIBUTE_UOM {slot}"].iloc[r_idx]
        print(f"        Slot {slot:2d} -> Label: {lbl:<22} | Value: {val:<28} | UOM: {repr(uom)}")

# 3. Comprehensive 252-Field Diff Summary
print("\n" + "-" * 74)
print("  COMPREHENSIVE 252-FIELD DIFF RESULTS")
print("-" * 74)

total_fields = len(headers_expected) * 2
matches = 0
mismatches = []

for r_idx in range(2):
    r_name = "Frigidaire" if r_idx == 0 else "Whirlpool"
    for col in headers_expected:
        exp_val = str(expected_df[col].iloc[r_idx]).strip()
        got_val = str(exported_df[col].iloc[r_idx]).strip()

        if exp_val == got_val:
            matches += 1
        else:
            mismatches.append((r_idx, r_name, col, got_val, exp_val))

print(f"  Total Fields Evaluated : {total_fields} (252 cols x 2 rows)")
print(f"  Exact Field Matches    : {matches} / {total_fields} ({matches / total_fields:.2%})")

if mismatches:
    print(f"\n  [!] {len(mismatches)} Field Mismatch(es) Found:")
    for r_idx, r_name, col, got, exp in mismatches:
        print(f"      Row {r_idx} ({r_name}) -> Field '{col}':")
        print(f"          Exported: {repr(got)}")
        print(f"          Expected: {repr(exp)}")
else:
    print("  Zero field mismatches detected across all 252 columns.")

print("=" * 74)
all_passed = (matches == total_fields)
if all_passed:
    print("  GROUND-TRUTH REGRESSION TEST: 100% PASSED (504/504 FIELDS EXACT) [OK]")
else:
    print(f"  GROUND-TRUTH REGRESSION TEST: {len(mismatches)} MISMATCHES TO RESOLVE")
print("=" * 74)

sys.exit(0 if all_passed else 1)
