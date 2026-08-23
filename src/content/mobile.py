"""
mobile.py -- MOBILE_DESC generator (V4).

Follows the confirmed ground-truth construction:

    Rheem Manufacturing FRIGIDAIRE, Dishwasher, Professional Series, PDSH4816AF

Token order:
    1. Manufacturer name   (canonical, e.g. "Rheem Manufacturing")
    2. Brand name          (trademark symbols stripped)
    3. Product type        (title case)
    4. Series              (when available)
    5. MPN                 (manufacturer part number)

Facts are only included when verified — never invented.
"""

import re
from typing import Optional

from src.content._helpers import (
    attribute_value,
    resolve_product_type,
)

_TM = re.compile(r"[®™©]")


def clean_brand(brand: Optional[str]) -> Optional[str]:
    if not brand:
        return None
    return _TM.sub("", brand).strip() or None


def generate_mobile_desc(product: dict) -> str:
    manufacturer = product.get("manufacturer_name") or product.get("MANUFACTURER_NAME")
    brand = clean_brand(product.get("brand_name") or product.get("BRAND_NAME"))
    product_type = resolve_product_type(product)
    series = attribute_value(product, "Series")
    mpn = (
        product.get("mfg_part_num")
        or product.get("Mfg_Part_Num")
        or product.get("manufacturer_part_number")
        or product.get("MANUFACTURER_PART_NUMBER")
    )

    # Head: manufacturer + brand space-joined ("Rheem Manufacturing FRIGIDAIRE")
    head = " ".join(str(p).strip() for p in (manufacturer, brand) if p)
    # Tail: product type, series, MPN comma-joined
    tail = [str(p).strip() for p in (product_type, series, mpn) if p]

    if not head:
        return ", ".join(tail)
    if not tail:
        return head
    return f"{head}, {', '.join(tail)}"