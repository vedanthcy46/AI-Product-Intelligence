"""
_helpers.py -- Shared utilities for the content generation package.

Everything here is deterministic.  Content generators consume the verified
internal product dict (attributes + classifications) and never invent facts.
"""

from typing import Any, Optional

# Ground-truth "fine" values are plural nouns ("Dishwashers").  When used as a
# standalone product-type token ("Dishwasher") the trailing "s" is removed.
# A short allow-list guards against naive singularisation of known irregulars.
_IRREGULAR_SINGULAR = {
    "accessories": "accessory",
    "analyzers": "analyzer",
    "brushes": "brush",
    "cabinets": "cabinet",
    "clutches": "clutch",
    "couplers": "coupler",
    "disconnects": "disconnect",
    "filters": "filter",
    "fixtures": "fixture",
    "generators": "generator",
    "lamps": "lamp",
    "lashes": "latch",
    "meters": "meter",
    "pumps": "pump",
    "reducers": "reducer",
    "sensors": "sensor",
    "switches": "switch",
    "valves": "valve",
}


def singularize(word: Optional[str]) -> Optional[str]:
    """Best-effort singularisation for a taxonomy 'fine' value."""
    if not word:
        return None
    w = word.strip()
    if not w:
        return None
    low = w.lower()
    if low in _IRREGULAR_SINGULAR:
        return _IRREGULAR_SINGULAR[low]
    # Don't touch words ending in "ss"/"us" (Dress, Bus) or single-letter tokens
    if low.endswith("ss") or low.endswith("us") or len(w) <= 3:
        return w
    if low.endswith("s"):
        return w[:-1]
    return w


def resolve_product_type(product: dict) -> Optional[str]:
    """
    Determine the product-type token used in descriptions.

    Preference order: explicit product_name -> singularised 'fine'
    (from the taxonomy) -> class_name -> dept.
    """
    name = product.get("product_name")
    if name:
        return str(name).strip() or None
    fine = product.get("fine")
    if fine:
        return singularize(str(fine)) or None
    class_name = product.get("class_name")
    if class_name:
        return str(class_name).strip() or None
    dept = product.get("dept")
    if dept:
        return str(dept).strip() or None
    return None


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def find_attribute(product: dict, *label_keys: str) -> Optional[dict]:
    """
    Find an attribute dict by label.  Tries exact normalised match first,
    then a containment match so "Voltage Rating" also matches a candidate
    labelled "voltage".  Returns None when no attribute matches.
    """
    attrs = product.get("attributes", [])
    if not isinstance(attrs, list):
        return None

    keys = [_norm(k) for k in label_keys if k]
    for a in attrs:
        if not isinstance(a, dict):
            continue
        label = _norm(a.get("label") or "")
        if label in keys:
            return a
    for a in attrs:
        if not isinstance(a, dict):
            continue
        label = _norm(a.get("label") or "")
        for k in keys:
            if k and (k in label or label in k):
                return a
    return None


def attribute_value(product: dict, *label_keys: str) -> Optional[str]:
    """Return the value of the first matching attribute (or None)."""
    a = find_attribute(product, *label_keys)
    if a is None:
        return None
    v = a.get("value")
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def attribute_uom(product: dict, *label_keys: str) -> Optional[str]:
    """Return the UOM of the first matching attribute (or None)."""
    a = find_attribute(product, *label_keys)
    if a is None:
        return None
    u = a.get("uom")
    if u is None:
        return None
    s = str(u).strip()
    return s if s else None


def value_with_uom(product: dict, *label_keys: str) -> Optional[str]:
    """Return 'value uom' (e.g. '120 V') or just the value when no UOM."""
    value = attribute_value(product, *label_keys)
    if value is None:
        return None
    uom = attribute_uom(product, *label_keys)
    return f"{value} {uom}" if uom else value


def clean_number(value: str) -> str:
    """Strip trailing '.0' from numeric strings ('5.0' -> '5')."""
    try:
        f = float(value)
        if f == int(f):
            return str(int(f))
    except (ValueError, TypeError):
        pass
    return value


def join_parts(*parts: Optional[str]) -> str:
    """Join non-empty parts with ', ' — the canonical list separator."""
    cleaned = []
    for p in parts:
        if p is None:
            continue
        s = str(p).strip()
        if s:
            cleaned.append(s)
    return ", ".join(cleaned)


def truncate(text: str, limit: int) -> str:
    """Truncate to *limit* characters, appending nothing (delivery truncates)."""
    if text is None:
        return ""
    return text if len(text) <= limit else text[:limit]