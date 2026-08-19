"""
features.py -- ITEM_FEATURES_1..20 generator (V7, features family).

Feature bullets are assembled from verified attributes and any evidence-derived
features already attached to the product record.  Maximum 20 bullets to match
the delivery schema's ITEM_FEATURES_1..20 slots.
"""

from src.content._helpers import (
    attribute_value,
    clean_number,
    value_with_uom,
)

MAX_FEATURES = 20


def _bullet(label: str, value: str, uom: str = "") -> str:
    if uom:
        return f"{label}: {value} {uom}"
    return f"{label}: {value}"


def generate_features(product: dict) -> list[str]:
    bullets: list[str] = []

    # Pre-seeded features from upstream evidence (RAG / extraction) first.
    existing = product.get("features", [])
    if isinstance(existing, list):
        for feat in existing:
            f = str(feat or "").strip()
            if f:
                bullets.append(f)

    # Derived feature bullets from verified attributes.
    sound = value_with_uom(product, "Sound Level", "Noise Level")
    if sound:
        bullets.append(f"Sound Level: {sound}")

    cycles = attribute_value(product, "Number of Wash Cycles", "Wash Cycles")
    if cycles:
        bullets.append(f"{clean_number(cycles)} Wash Cycles")

    voltage = value_with_uom(product, "Voltage Rating", "Voltage")
    if voltage:
        bullets.append(f"Voltage: {voltage}")

    amperage = value_with_uom(product, "Amperage Rating", "Amperage", "Current Rating")
    if amperage:
        bullets.append(f"Amperage: {amperage}")

    material = attribute_value(product, "Material")
    if material:
        bullets.append(f"Material: {material}")

    color = attribute_value(product, "Color", "Finish")
    if color:
        bullets.append(f"Color: {color}")

    mounting = attribute_value(product, "Mounting Type", "Mounting", "Mount")
    if mounting:
        bullets.append(f"Mounting: {mounting}")

    size = attribute_value(product, "Size")
    if size:
        bullets.append(f"Size: {size}")

    with_value = product.get("With") or product.get("with")
    if with_value:
        bullets.append(f"With {str(with_value).strip()}")

    # De-duplicate, keep the original order, cap at 20.
    seen: set[str] = set()
    result: list[str] = []
    for b in bullets:
        key = b.lower()
        if key not in seen:
            seen.add(key)
            result.append(b)
        if len(result) >= MAX_FEATURES:
            break
    return result[:MAX_FEATURES]