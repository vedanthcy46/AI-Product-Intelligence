"""
long_description.py -- LONG_DESC1 generator (V6).

Follows the confirmed ground-truth construction:

    FRIGIDAIRE® Dishwasher With CleanBoost™, Professional Series,
    5 Wash Cycles, 120 V, 15 A, 47 dBA, Stainless Steel

Token order:
    1. Brand (with trademark symbol)
    2. Product type
    3. "With <With-value>"            (descriptive extra, when present)
    4. Series
    5. Number of wash cycles
    6. Voltage rating + UOM
    7. Amperage rating + UOM
    8. Sound level + UOM
    9. Material

Every token comes from verified attributes or the confirmed "With" field.
"""

from src.content._helpers import (
    attribute_value,
    clean_number,
    resolve_product_type,
    value_with_uom,
)


def generate_long_desc(product: dict) -> str:
    brand = product.get("brand_name") or product.get("BRAND_NAME")
    product_type = resolve_product_type(product)
    with_value = product.get("With") or product.get("with")

    # Head: brand + product type space-joined, plus "With <value>"
    head = " ".join(str(p).strip() for p in (brand, product_type) if p)
    if with_value:
        head = f"{head} With {str(with_value).strip()}" if head else f"With {str(with_value).strip()}"

    # Tail: series, wash cycles, voltage, amperage, sound, material comma-joined
    series = attribute_value(product, "Series")
    wash_cycles = attribute_value(product, "Number of Wash Cycles", "Wash Cycles")
    voltage = value_with_uom(product, "Voltage Rating", "Voltage")
    amperage = value_with_uom(product, "Amperage Rating", "Amperage", "Current Rating")
    sound = value_with_uom(product, "Sound Level", "Noise Level")
    material = attribute_value(product, "Material")

    tail = []
    if series:
        tail.append(str(series).strip())
    if wash_cycles:
        tail.append(f"{clean_number(wash_cycles)} Wash Cycles")
    if voltage:
        tail.append(str(voltage).strip())
    if amperage:
        tail.append(str(amperage).strip())
    if sound:
        tail.append(str(sound).strip())
    if material:
        tail.append(str(material).strip())

    if not head:
        return ", ".join(tail)
    if not tail:
        return head
    return f"{head}, {', '.join(tail)}"