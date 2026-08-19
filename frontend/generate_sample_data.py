"""
generate_sample_data.py -- Preview scaffold for the frontend UI.

Builds a small set of sample *internal product* records (mirroring the two
confirmed ground-truth products), then runs the REAL validation + confidence
engines over them so frontend/data/metrics.json contains genuinely computed
numbers — never hardcoded demonstration figures.

This exists so the UI can be reviewed before the full pipeline + datasets are
available.  Replace with `python frontend/generate_data.py` for real output.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

OUT = os.path.join(ROOT, "frontend", "data")

KNOWN_UOMS = {"V", "A", "W", "kW", "in", "ft", "mm", "cm", "m", "lb", "kg", "oz",
              "g", "dBA", "dB", "%", "psi", "RPM", "CFM", "HP", "BTU", "BTUH",
              "hr", "min", "pc", "ea", "pk", "pr", "set", "kW-hr", "\u00b0F", "\u00b0C"}


def _attr(label, value, uom=None, source=None, source_page=None, confidence=0.9,
          lov_matched=True, needs_review=False):
    return {
        "label": label, "value": value, "uom": uom, "source": source,
        "source_page": source_page, "confidence": confidence,
        "lov_matched": lov_matched, "needs_review": needs_review,
    }


def _build():
    from src.content import generate_content
    from src.validation.validator import validate_product
    from src.validation.confidence import compute_confidence

    base = [
        {
            "row_id": "1",
            "mfg_part_num": "PDSH4816AF",
            "part_desc": "PDSH4816AF Dishwasher SS - Display Only",
            "manufacturer_name": "Rheem Manufacturing",
            "manufacturer_confidence": 0.99,
            "brand_name": "FRIGIDAIRE\u00ae",
            "classpath": "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers",
            "dept": "Appliances", "class_name": "Large Appliances", "fine": "Dishwashers",
            "classification_confidence": 0.96,
            "With": "CleanBoost\u2122",
            "attributes": [
                _attr("Series", "Professional Series"),
                _attr("Number of Wash Cycles", "5", source="mfr_spec.pdf", source_page=2),
                _attr("Voltage Rating", "120", "V", "mfr_spec.pdf", 3),
                _attr("Amperage Rating", "15", "A", "mfr_spec.pdf", 3),
                _attr("Mounting Type", "Leg", source="mfr_spec.pdf", source_page=1),
                _attr("Sound Level", "47", "dBA", "mfr_spec.pdf", 3),
                _attr("Material", "Stainless Steel", source="mfr_spec.pdf", source_page=1),
                _attr("Depth With Door Open", "50-1/4", "in", "mfr_spec.pdf", 4),
                _attr("Color", "Stainless Steel", source="mfr_spec.pdf", source_page=1),
            ],
        },
        {
            "row_id": "2",
            "mfg_part_num": "WDT750SAHZ",
            "part_desc": "Whirlpool Dishwasher 3rd Rack - SS",
            "manufacturer_name": "Whirlpool Corporation",
            "manufacturer_confidence": 0.97,
            "brand_name": "Whirlpool\u00ae",
            "classpath": "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers",
            "dept": "Appliances", "class_name": "Large Appliances", "fine": "Dishwashers",
            "classification_confidence": 0.94,
            "attributes": [
                _attr("Number of Wash Cycles", "6", source="whirlpool_spec.pdf", source_page=2),
                _attr("Voltage Rating", "120", "V", "whirlpool_spec.pdf", 3),
                _attr("Amperage Rating", "15", "A", "whirlpool_spec.pdf", 3),
                _attr("Mounting Type", "Leg", source="whirlpool_spec.pdf", source_page=1),
                _attr("Sound Level", "41", "dBA", "whirlpool_spec.pdf", 3),
                _attr("Material", "Stainless Steel", source=None, confidence=0.55, needs_review=True),
            ],
        },
    ]

    products = []
    for p in base:
        p = generate_content(p)
        val = validate_product(p, KNOWN_UOMS)
        conf = compute_confidence(p, val, p.get("manufacturer_confidence", 1.0),
                                  p.get("classification_confidence", 1.0))
        p["validation"] = val
        p["confidence"] = conf
        p["needs_review"] = conf["needs_review"]
        products.append(p)

    # Metrics computed with the exact same functions the real dashboard uses.
    n = len(products)
    high = sum(1 for p in products if p["confidence"]["status"] == "HIGH")
    review = sum(1 for p in products if p["confidence"]["needs_review"])
    failures = sum(1 for p in products if not p["validation"]["valid"])
    ground = sum(p["validation"]["grounding_rate"] for p in products) / n
    lov = sum(p["validation"]["lov_compliance_rate"] for p in products) / n
    uom = sum(p["validation"]["uom_compliance_rate"] for p in products) / n
    avg_conf = sum(p["confidence"]["overall_confidence"] for p in products) / n

    metrics = {
        "n_products": n,
        "high_confidence": high,
        "needs_review": review,
        "validation_failures": failures,
        "grounding_rate": round(ground, 4),
        "lov_compliance_rate": round(lov, 4),
        "uom_compliance_rate": round(uom, 4),
        "avg_confidence": round(avg_conf, 4),
        "field_accuracy": None,
    }
    return products, metrics


def main():
    products, metrics = _build()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "products.json"), "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"Sample preview data -> {OUT}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()