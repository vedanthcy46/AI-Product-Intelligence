"""
invoice.py -- INVOICE_DESC generator (V3).

Follows the confirmed ground-truth construction:

    DISHWASHER LEG 5 SST 120V 15A 50-1/4IN

Token order:
    1. Product type          (uppercase)
    2. Mounting type         (uppercase)
    3. Number of wash cycles (number only)
    4. Material              (uppercase abbreviation)
    5. Voltage rating        (120V)
    6. Amperage rating       (15A)
    7. Depth with door open  (50-1/4IN)

All tokens are drawn exclusively from verified attributes; missing tokens are
skipped rather than guessed.  Enforced against the confirmed 40-char limit.
"""

from typing import Optional

from src.content._helpers import (
    attribute_value,
    attribute_uom,
    clean_number,
    join_parts,
    resolve_product_type,
    truncate,
)

INVOICE_LIMIT = 40

# Abbreviations mirror the preprocessing abbreviation table for consistency.
_MATERIAL_ABBREV = {
    "stainless steel": "SST",
    "stainless-steel": "SST",
    "brass": "BRS",
    "bronze": "BRZ",
    "aluminum": "ALUM",
    "aluminium": "ALUM",
    "nylon": "NYL",
    "copper": "CPR",
    "cast iron": "CI",
    "plastic": "PLS",
}


def _abbrev_material(material: Optional[str]) -> Optional[str]:
    if not material:
        return None
    low = " ".join(material.strip().lower().split())
    for key, abbr in _MATERIAL_ABBREV.items():
        if key in low:
            return abbr
    # Known word, no abbreviation -- emit uppercase verbatim
    return material.strip().upper()


def _token_text(value: str, uom: str) -> str:
    """'120' + 'V' -> '120V' (no space, per invoice ground truth)."""
    value = clean_number(value)
    if uom:
        uom_upper = uom.upper()
        if uom_upper == "IN":
            uom_upper = "IN"
        return f"{value}{uom_upper}"
    return value


def generate_invoice_desc(product: dict) -> str:
    """Build the INVOICE_DESC string for an internal product dict."""
    product_type = resolve_product_type(product)
    mounting = attribute_value(product, "Mounting Type", "Mounting", "Mount")
    wash_cycles = attribute_value(product, "Number of Wash Cycles", "Wash Cycles", "Wash Cycle Count")
    material = attribute_value(product, "Material")
    voltage = attribute_value(product, "Voltage Rating", "Voltage")
    amperage = attribute_value(product, "Amperage Rating", "Amperage", "Current Rating")
    depth = attribute_value(product, "Depth With Door Open", "Depth", "Depth with Door Open")

    tokens: list[Optional[str]] = []

    if product_type:
        tokens.append(product_type.strip().upper())
    if mounting:
        tokens.append(mounting.strip().upper())
    if wash_cycles:
        tokens.append(clean_number(wash_cycles))
    mat = _abbrev_material(material)
    if mat:
        tokens.append(mat)
    if voltage:
        tokens.append(_token_text(voltage, attribute_uom(product, "Voltage Rating", "Voltage") or "V"))
    if amperage:
        tokens.append(_token_text(amperage, attribute_uom(product, "Amperage Rating", "Amperage", "Current Rating") or "A"))
    if depth:
        tokens.append(_token_text(depth, attribute_uom(product, "Depth With Door Open", "Depth", "Depth with Door Open") or "in"))

    text = " ".join(t for t in tokens if t)
    return truncate(text, INVOICE_LIMIT)