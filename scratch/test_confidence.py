import sys
sys.path.insert(0, r"C:\Users\Yashas BR\OneDrive\Desktop\Hack2skills")

from src.validation.validator import validate_product
from src.validation.confidence import compute_confidence

KNOWN_UOMS = {"V", "A", "W", "kW", "in", "ft", "mm", "cm", "m",
              "lb", "kg", "oz", "g", "dBA", "dB", "%", "psi",
              "RPM", "CFM", "HP", "BTU", "BTUH", "hr", "min",
              "pc", "ea", "pk", "pr", "set", "kW-hr", "°F", "°C"}

# ── 1. High-Confidence Clean Product ──────────────────────────────────────────
CLEAN_PRODUCT = {
    "descriptions": {
        "INVOICE_DESC": "DISHWASHER LEG 5 SST 120V 15A",  # 30 chars (<=40)
        "SHORT_DESC": "Frigidaire Professional Series Dishwasher",
    },
    "attributes": [
        {"label": "Series", "value": "Professional Series", "uom": None, "source": "mfr_page", "lov_matched": True, "needs_review": False},
        {"label": "Voltage Rating", "value": "120", "uom": "V", "source": "spec_sheet", "lov_matched": True, "needs_review": False},
        {"label": "Amperage Rating", "value": "15", "uom": "A", "source": "spec_sheet", "lov_matched": True, "needs_review": False},
        {"label": "Material", "value": "Stainless Steel", "uom": None, "source": "mfr_page", "lov_matched": True, "needs_review": False},
    ],
}

clean_val = validate_product(CLEAN_PRODUCT, KNOWN_UOMS)
clean_conf = compute_confidence(
    CLEAN_PRODUCT,
    clean_val,
    manufacturer_match_confidence=0.98,
    classification_confidence=0.95,
)

# ── 2. Low-Confidence Broken Product ──────────────────────────────────────────
BROKEN_PRODUCT = {
    "descriptions": {
        "INVOICE_DESC": "DISHWASHER LEG 5 SST 120V 15A 50-1/4IN EXTRA LONG TEXT OVER 40 CHARS",  # 68 chars (>40)
    },
    "attributes": [
        {"label": "Series", "value": "Eco Series", "uom": None, "source": "mfr_page", "lov_matched": True, "needs_review": False},
        {"label": "Color", "value": "Gunmetal", "uom": None, "source": None, "lov_matched": False, "needs_review": True},
        {"label": "Weight", "value": "55", "uom": "xyz", "source": None, "lov_matched": False, "needs_review": True},
    ],
}

broken_val = validate_product(BROKEN_PRODUCT, KNOWN_UOMS)
broken_conf = compute_confidence(
    BROKEN_PRODUCT,
    broken_val,
    manufacturer_match_confidence=0.40,
    classification_confidence=0.40,
)

# ── 3. Genuine Medium-Confidence Product ──────────────────────────────────────
MEDIUM_PRODUCT = {
    "descriptions": {
        "INVOICE_DESC": "DISHWASHER BUILT-IN 120V 10A",  # 28 chars (<=40)
    },
    "attributes": [
        {"label": "Series", "value": "Standard Series", "uom": None, "source": "catalog", "lov_matched": True, "needs_review": False},
        {"label": "Voltage Rating", "value": "120", "uom": "V", "source": "spec_sheet", "lov_matched": True, "needs_review": False},
        {"label": "Color", "value": "Stainless Steel", "uom": None, "source": "catalog", "lov_matched": True, "needs_review": False},
        {"label": "Finish", "value": "Matte Custom", "uom": None, "source": "catalog", "lov_matched": False, "needs_review": False}, # 1 unmatched LOV
    ],
}

medium_val = validate_product(MEDIUM_PRODUCT, KNOWN_UOMS)
# mfr=0.75, class=0.75, lov_rate=3/4=0.75, uom=1.0, grounding=1.0
# Score = 0.25*0.75 + 0.25*0.75 + 0.20*0.75 + 0.15*1.0 + 0.15*1.0 = 0.1875 + 0.1875 + 0.15 + 0.15 + 0.15 = 0.8250 (MEDIUM: 0.60 - 0.85)
medium_conf = compute_confidence(
    MEDIUM_PRODUCT,
    medium_val,
    manufacturer_match_confidence=0.75,
    classification_confidence=0.75,
)

# ── Display Results ───────────────────────────────────────────────────────────
print("=" * 68)
print("  HIGH-CONFIDENCE CLEAN PRODUCT RESULT")
print("=" * 68)
print(f"  Overall Score  : {clean_conf['overall_confidence']:.4f} ({clean_conf['overall_confidence']:.2%})")
print(f"  Status         : {clean_conf['status']}")
print(f"  Needs Review   : {clean_conf['needs_review']}")
print(f"  Review Reasons : {clean_conf['review_reasons']}")

print("\n" + "=" * 68)
print("  LOW-CONFIDENCE BROKEN PRODUCT RESULT")
print("=" * 68)
print(f"  Overall Score  : {broken_conf['overall_confidence']:.4f} ({broken_conf['overall_confidence']:.2%})")
print(f"  Status         : {broken_conf['status']}")
print(f"  Needs Review   : {broken_conf['needs_review']}")
print(f"  Review Reasons ({len(broken_conf['review_reasons'])}):")
for r in broken_conf["review_reasons"]:
    print(f"    - {r}")

print("\n" + "=" * 68)
print("  GENUINE MEDIUM-CONFIDENCE PRODUCT RESULT")
print("=" * 68)
print(f"  Overall Score  : {medium_conf['overall_confidence']:.4f} ({medium_conf['overall_confidence']:.2%})")
print(f"  Status         : {medium_conf['status']}")
print(f"  Needs Review   : {medium_conf['needs_review']}")
print(f"  Review Reasons ({len(medium_conf['review_reasons'])}):")
for r in medium_conf["review_reasons"]:
    print(f"    - {r}")

# ── Assertions ───────────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("  ASSERTIONS")
print("=" * 68)

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

# Clean product assertions
check("clean: score == 0.9825", clean_conf["overall_confidence"], 0.9825)
check("clean: status == 'HIGH'", clean_conf["status"], "HIGH")
check("clean: needs_review == False", clean_conf["needs_review"], False)
check("clean: review_reasons is empty", clean_conf["review_reasons"], [])

# Broken product assertions
check("broken: status == 'LOW'", broken_conf["status"], "LOW")
check("broken: needs_review == True", broken_conf["needs_review"], True)
check("broken: review_reasons populated", len(broken_conf["review_reasons"]) > 0, True)

# Medium product assertions
check("medium: score == 0.8250", medium_conf["overall_confidence"], 0.8250)
check("medium: in 0.60-0.85 band", 0.60 <= medium_conf["overall_confidence"] <= 0.85, True)
check("medium: status == 'MEDIUM'", medium_conf["status"], "MEDIUM")

print("=" * 68)
if all_pass:
    print("  All assertions passed (OK)")
else:
    print("  SOME ASSERTIONS FAILED")
print("=" * 68)

sys.exit(0 if all_pass else 1)
