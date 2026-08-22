"""
Test runner for the validation engine.
Two mock products: one "clean", one "broken".
"""

import sys
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.validation.validator import validate_product

# Known UOMs for the test (a realistic subset from uom.UOM_TABLE.values())
KNOWN_UOMS = {"V", "A", "W", "kW", "in", "ft", "mm", "cm", "m",
              "lb", "kg", "oz", "g", "dBA", "dB", "%", "psi",
              "RPM", "CFM", "HP", "BTU", "BTUH", "hr", "min",
              "pc", "ea", "pk", "pr", "set", "kW-hr", "°F", "°C"}

# ─── Clean product ────────────────────────────────────────────────────────────
CLEAN_PRODUCT = {
    "descriptions": {
        "INVOICE_DESC":   "DISHWASHER LEG 5 SST 120V 15A",   # 30 chars -- under 40
        "SHORT_DESC":     "Frigidaire Professional Series Dishwasher",
        "LONG_DESC1":     "A full long description that has no confirmed char limit.",
        "MOBILE_DESC":    "Frigidaire, Dishwasher, Professional Series",
        "RETAIL_DESC":    "Professional Series Dishwasher, Leg Mounting",
    },
    "attributes": [
        {"label": "Series",          "value": "Professional Series", "uom": None,  "source": "manufacturer_page", "lov_matched": True},
        {"label": "Mounting Type",   "value": "Leg",                 "uom": None,  "source": "spec_sheet",        "lov_matched": True},
        {"label": "Voltage Rating",  "value": "120",                 "uom": "V",   "source": "spec_sheet",        "lov_matched": True},
        {"label": "Amperage Rating", "value": "15",                  "uom": "A",   "source": "spec_sheet",        "lov_matched": True},
        {"label": "Sound Level",     "value": "47",                  "uom": "dBA", "source": "manufacturer_page", "lov_matched": True},
        {"label": "Material",        "value": "Stainless Steel",     "uom": None,  "source": "manufacturer_page", "lov_matched": True},
        {"label": "Model",           "value": None,                  "uom": None,  "source": None,                "lov_matched": False},  # known-but-unfilled
    ],
}

# ─── Broken product ───────────────────────────────────────────────────────────
BROKEN_PRODUCT = {
    "descriptions": {
        "INVOICE_DESC":   "DISHWASHER LEG 5 SST 120V 15A 50-1/4IN EXTRA LONG TEXT HERE",  # 60 chars -- over 40
        "SHORT_DESC":     "Whirlpool Eco Series Dishwasher, Built-in Mounting",
        "LONG_DESC1":     "A long description with no confirmed limit.",
    },
    "attributes": [
        {"label": "Series",          "value": "Eco Series",          "uom": None,   "source": "manufacturer_page", "lov_matched": True},
        {"label": "Mounting Type",   "value": "Built-in",            "uom": None,   "source": "spec_sheet",        "lov_matched": True},
        {"label": "Voltage Rating",  "value": "120",                 "uom": "V",    "source": "spec_sheet",        "lov_matched": True},
        # Bad: LOV not matched (value "Gunmetal" not in stub LOV for Color)
        {"label": "Color",           "value": "Gunmetal",            "uom": None,   "source": "ai_extraction",     "lov_matched": False},
        # Bad: no source (ungrounded, has a real value)
        {"label": "Sound Level",     "value": "41",                  "uom": "dBA",  "source": None,                "lov_matched": True},
        # Bad: uom "xyz" not in known_uoms
        {"label": "Weight",          "value": "55",                  "uom": "xyz",  "source": "spec_sheet",        "lov_matched": True},
    ],
}

# ─── Run + report ─────────────────────────────────────────────────────────────
def print_report(label, product, report):
    print(f"\n{'=' * 68}")
    print(f"  {label}")
    print(f"{'=' * 68}")
    print(f"  valid                          : {report['valid']}")
    print(f"  lov_compliance_rate            : {report['lov_compliance_rate']:.1%}")
    print(f"  uom_compliance_rate            : {report['uom_compliance_rate']:.1%}")
    print(f"  grounding_rate                 : {report['grounding_rate']:.1%}")
    print(f"  character_compliant_fields     : {report['character_compliant_fields']}")
    print(f"  character_non_compliant_fields : {report['character_non_compliant_fields']}")
    print(f"  unchecked_fields               : {report['unchecked_fields']}")
    if report["issues"]:
        print(f"  issues ({len(report['issues'])}):")
        for iss in report["issues"]:
            print(f"    - {iss}")
    else:
        print("  issues: none")


clean_report  = validate_product(CLEAN_PRODUCT,  KNOWN_UOMS)
broken_report = validate_product(BROKEN_PRODUCT, KNOWN_UOMS)

print_report("CLEAN PRODUCT", CLEAN_PRODUCT, clean_report)
print_report("BROKEN PRODUCT", BROKEN_PRODUCT, broken_report)

# ─── Assertions ───────────────────────────────────────────────────────────────
print()
print("=" * 68)
print("  Assertions")
print("=" * 68)

all_pass = True

def check(desc, got, expected):
    global all_pass
    ok = (got == expected)
    if not ok:
        all_pass = False
    print(f"  {'PASS' if ok else 'FAIL'}  {desc}")
    if not ok:
        print(f"         expected : {expected!r}")
        print(f"         got      : {got!r}")
    return ok

# Clean product assertions
check("clean: valid=True",                    clean_report["valid"], True)
check("clean: lov_compliance_rate=1.0",       clean_report["lov_compliance_rate"], 1.0)
check("clean: uom_compliance_rate=1.0",       clean_report["uom_compliance_rate"], 1.0)
check("clean: grounding_rate=1.0",            clean_report["grounding_rate"], 1.0)
check("clean: INVOICE_DESC compliant",        "INVOICE_DESC" in clean_report["character_compliant_fields"], True)
check("clean: no char violations",            clean_report["character_non_compliant_fields"], [])
check("clean: no issues",                     clean_report["issues"], [])

# Unchecked fields present in clean (SHORT_DESC, LONG_DESC1, MOBILE_DESC, RETAIL_DESC)
check("clean: unchecked_fields non-empty",    len(clean_report["unchecked_fields"]) > 0, True)

# Broken product assertions
check("broken: valid=False (char limit violated)", broken_report["valid"], False)

# LOV rate: 6 checkable (all value!=None), 1 lov_matched=False -> 5/6 = 0.8333
check("broken: lov_compliance_rate=5/6",      broken_report["lov_compliance_rate"], round(5/6, 4))

# UOM rate: 3 attributes with uom (V=OK, dBA=OK, xyz=FAIL) -> 2/3 = 0.6667
check("broken: uom_compliance_rate=2/3",      broken_report["uom_compliance_rate"], round(2/3, 4))

# Grounding: 6 attributes with value, 1 has source=None -> 5/6 grounded = 0.8333
check("broken: grounding_rate=5/6",           broken_report["grounding_rate"], round(5/6, 4))

check("broken: INVOICE_DESC non-compliant",   "INVOICE_DESC" in broken_report["character_non_compliant_fields"], True)
check("broken: has issues",                   len(broken_report["issues"]) > 0, True)

# Issues should include LOV, grounding, UOM, and char-limit messages
issue_text = " | ".join(broken_report["issues"])
check("broken: LOV issue present",            "LOV non-compliance" in issue_text, True)
check("broken: Ungrounded issue present",     "Ungrounded" in issue_text, True)
check("broken: UOM issue present",            "UOM non-compliance" in issue_text, True)
check("broken: Char limit issue present",     "Character limit exceeded" in issue_text, True)

print("=" * 68)
if all_pass:
    print("  All assertions passed (OK)")
else:
    print("  SOME ASSERTIONS FAILED -- see above")
print("=" * 68)
print()

import sys as _sys
_sys.exit(0 if all_pass else 1)
