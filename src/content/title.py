"""
title.py -- SHORT_DESC and RETAIL_DESC generators (V5).

Short description follows the confirmed ground-truth construction:

    FRIGIDAIRE® Professional Series PDSH4816AF Dishwasher With CleanBoost™,
    Leg Mounting, 5 Wash Cycles, Stainless Steel

Retail description follows:

    Professional Series Dishwasher, Leg Mounting, 5-Wash Cycle, Stainless Steel

Both consume only verified attributes and the confirmed "With" descriptive
extra — no unsupported claims.
"""

from src.content._helpers import (
    attribute_value,
    clean_number,
    resolve_product_type,
)


def _short_head(product: dict) -> str:
    """Space-joined head: BRAND + Series + MPN + Product Type (+ With value)."""
    brand = product.get("brand_name") or product.get("BRAND_NAME")
    series = attribute_value(product, "Series")
    mpn = (
        product.get("mfg_part_num")
        or product.get("Mfg_Part_Num")
        or product.get("manufacturer_part_number")
        or product.get("MANUFACTURER_PART_NUMBER")
    )
    product_type = resolve_product_type(product)
    with_value = product.get("With") or product.get("with")

    head = " ".join(
        str(p).strip() for p in (brand, series, mpn, product_type) if p
    )
    if with_value:
        head = f"{head} With {str(with_value).strip()}" if head else f"With {str(with_value).strip()}"
    return head


def _short_tail(product: dict) -> list[str]:
    """Comma-joined tail: mounting, wash cycles, material."""
    mounting = attribute_value(product, "Mounting Type", "Mounting", "Mount")
    wash_cycles = attribute_value(product, "Number of Wash Cycles", "Wash Cycles")
    material = attribute_value(product, "Material")

    tail = []
    if mounting:
        tail.append(f"{str(mounting).strip()} Mounting")
    if wash_cycles:
        tail.append(f"{clean_number(wash_cycles)} Wash Cycles")
    if material:
        tail.append(str(material).strip())
    return tail


def _retail_head(product: dict) -> str:
    """Space-joined head: Series + Product Type."""
    series = attribute_value(product, "Series")
    product_type = resolve_product_type(product)
    return " ".join(str(p).strip() for p in (series, product_type) if p)


def _retail_tail(product: dict) -> list[str]:
    """Comma-joined tail: mounting, N-Wash Cycle, material."""
    mounting = attribute_value(product, "Mounting Type", "Mounting", "Mount")
    wash_cycles = attribute_value(product, "Number of Wash Cycles", "Wash Cycles")
    material = attribute_value(product, "Material")

    tail = []
    if mounting:
        tail.append(f"{str(mounting).strip()} Mounting")
    if wash_cycles:
        tail.append(f"{clean_number(wash_cycles)}-Wash Cycle")
    if material:
        tail.append(str(material).strip())
    return tail


def _head_tail(head: str, tail: list[str]) -> str:
    if not head:
        return ", ".join(tail)
    if not tail:
        return head
    return f"{head}, {', '.join(tail)}"


def generate_short_desc(product: dict) -> str:
    return _head_tail(_short_head(product), _short_tail(product))


def generate_retail_desc(product: dict) -> str:
    return _head_tail(_retail_head(product), _retail_tail(product))