"""
marketing.py -- MARKETING_DESCRIPTION generator (V7).

A natural-language paragraph assembled deterministically from verified
features and attributes only.  No claims are made that are not grounded in
the product record (V7 rule: only verified attributes + evidence + guidelines).
"""

from src.content._helpers import (
    attribute_value,
    clean_number,
    resolve_product_type,
    value_with_uom,
)


def _feature_phrases(product: dict, max_items: int = 4) -> list[str]:
    """Build short feature phrases from verified data, newest first."""
    phrases: list[str] = []

    sound = value_with_uom(product, "Sound Level", "Noise Level")
    if sound:
        phrases.append(f"a quiet {sound} sound rating")

    cycles = attribute_value(product, "Number of Wash Cycles", "Wash Cycles")
    if cycles:
        phrases.append(f"{clean_number(cycles)} wash cycles to choose from")

    voltage = value_with_uom(product, "Voltage Rating", "Voltage")
    if voltage:
        phrases.append(f"{voltage} operation")

    material = attribute_value(product, "Material")
    if material:
        phrases.append(f"a {material} construction")

    # Anything the evidence already surfaced as a feature bullet
    features = product.get("features", [])
    if isinstance(features, list):
        for feat in features:
            f = str(feat or "").strip()
            if f:
                phrases.append(f)

    # De-duplicate while preserving order, cap the count
    seen, out = set(), []
    for p in phrases:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
        if len(out) >= max_items:
            break
    return out


def _list_phrase(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def generate_marketing_description(product: dict) -> str:
    brand = product.get("brand_name") or product.get("BRAND_NAME")
    product_type = resolve_product_type(product)

    phrases = _feature_phrases(product)
    if not phrases:
        return ""

    who = brand if brand else "This"
    what = product_type or "product"

    sentence_1 = (
        f"{who} {what} offers {_list_phrase(phrases)} "
        f"for dependable everyday performance."
    )

    # Optional closing sentence from the "With" descriptive extra.
    with_value = product.get("With") or product.get("with")
    if with_value:
        sentence_1 = sentence_1.rstrip(".")
        sentence_1 += f", and comes equipped {str(with_value).strip().lower()}."

    return sentence_1