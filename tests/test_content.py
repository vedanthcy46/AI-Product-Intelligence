"""
test_content.py -- Content generation tests (Vedanth track, V2-V7).

Verifies every description generator against the confirmed ground-truth
construction patterns (Frigidaire PDSH4816AF).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.content import (
    generate_content,
    generate_invoice_desc,
    generate_mobile_desc,
    generate_short_desc,
    generate_long_desc,
    generate_retail_desc,
    generate_features,
)
from src.validation.character_limits import CHARACTER_LIMITS

RESULTS = []


def check(name, condition):
    RESULTS.append((name, bool(condition)))
    if not condition:
        print(f"  FAIL  {name}")


def _frigidaire_product():
    return {
        "manufacturer_name": "Rheem Manufacturing",
        "brand_name": "FRIGIDAIRE\u00ae",
        "mfg_part_num": "PDSH4816AF",
        "fine": "Dishwashers",
        "product_name": "Dishwasher",
        "With": "CleanBoost\u2122",
        "attributes": [
            {"label": "Series", "value": "Professional Series"},
            {"label": "Number of Wash Cycles", "value": "5.0"},
            {"label": "Voltage Rating", "value": "120", "uom": "V"},
            {"label": "Amperage Rating", "value": "15", "uom": "A"},
            {"label": "Mounting Type", "value": "Leg"},
            {"label": "Sound Level", "value": "47", "uom": "dBA"},
            {"label": "Material", "value": "Stainless Steel"},
            {"label": "Depth With Door Open", "value": "50-1/4", "uom": "in"},
        ],
    }


def test_invoice_desc():
    out = generate_invoice_desc(_frigidaire_product())
    check("INVOICE_DESC matches ground truth", out == "DISHWASHER LEG 5 SST 120V 15A 50-1/4IN")
    limit = CHARACTER_LIMITS.get("INVOICE_DESC")
    if limit:
        check(f"INVOICE_DESC within {limit} char limit", len(out) <= limit)


def test_mobile_desc():
    out = generate_mobile_desc(_frigidaire_product())
    check(
        "MOBILE_DESC matches ground truth",
        out == "Rheem Manufacturing FRIGIDAIRE, Dishwasher, Professional Series, PDSH4816AF",
    )


def test_short_desc():
    out = generate_short_desc(_frigidaire_product())
    check(
        "SHORT_DESC starts with confirmed prefix",
        out.startswith("FRIGIDAIRE\u00ae Professional Series PDSH4816AF Dishwasher With CleanBoost\u2122, Leg Mounting"),
    )


def test_long_desc():
    out = generate_long_desc(_frigidaire_product())
    check(
        "LONG_DESC1 starts with confirmed prefix",
        out.startswith("FRIGIDAIRE\u00ae Dishwasher With CleanBoost\u2122, Professional Series, 5 Wash Cycles, 120 V"),
    )


def test_retail_desc():
    out = generate_retail_desc(_frigidaire_product())
    check(
        "RETAIL_DESC matches ground truth",
        out == "Professional Series Dishwasher, Leg Mounting, 5-Wash Cycle, Stainless Steel",
    )


def test_features():
    out = generate_features(_frigidaire_product())
    check("features is a list", isinstance(out, list))
    check("features non-empty", len(out) > 0)
    check("features within schema cap", len(out) <= 20)


def test_generate_content_fills_all_fields():
    product = _frigidaire_product()
    out = generate_content(product)
    for field in ["MOBILE_DESC", "INVOICE_DESC", "SHORT_DESC", "LONG_DESC1", "RETAIL_DESC", "MARKETING_DESCRIPTION"]:
        check(f"generate_content produces {field}", field in out["descriptions"] and bool(out["descriptions"][field]))
    check("generate_content produces features", "features" in out and isinstance(out["features"], list))


def test_no_invented_facts():
    # A product with NO attributes must not fabricate attribute-driven claims.
    # Product type comes from verified classification, so it may still appear.
    bare = {
        "brand_name": "Whirlpool\u00ae",
        "product_name": "Dishwasher",
        "attributes": [],
    }
    out = generate_content(bare)
    check("empty-product marketing is empty", out["descriptions"]["MARKETING_DESCRIPTION"] == "")
    check("empty-product invoice carries only product type", out["descriptions"]["INVOICE_DESC"] == "DISHWASHER")
    check("empty-product features empty", out["features"] == [])


def test_invoice_truncation():
    # Massive values must be truncated, not crash.
    product = _frigidaire_product()
    product["attributes"][0]["value"] = "Stainless Steel Alloy 304L Extra Special Grade"
    out = generate_invoice_desc(product)
    limit = CHARACTER_LIMITS.get("INVOICE_DESC")
    if limit:
        check("INVOICE_DESC truncated within limit", len(out) <= limit)


def main():
    print("=" * 60)
    print("  CONTENT GENERATION TESTS")
    print("=" * 60)
    test_invoice_desc()
    test_mobile_desc()
    test_short_desc()
    test_long_desc()
    test_retail_desc()
    test_features()
    test_generate_content_fills_all_fields()
    test_no_invented_facts()
    test_invoice_truncation()

    passed = sum(1 for _, ok in RESULTS if ok)
    total = len(RESULTS)
    print("-" * 60)
    print(f"  {passed}/{total} assertions passed")
    if passed != total:
        print("  FAILED:")
        for name, ok in RESULTS:
            if not ok:
                print(f"    - {name}")
        sys.exit(1)
    print("  All assertions passed (OK)")
    print("=" * 60)


if __name__ == "__main__":
    main()