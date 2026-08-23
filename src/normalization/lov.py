"""
lov.py -- List-of-Values normalisation engine.  ** STUB VERSION **

NOTE: No official LOV master file was distributed with the challenge.
This stub is built from:
  - Values observed in the 2 confirmed ground-truth rows (Frigidaire +
    Whirlpool dishwashers).
  - Reasonable inference for common industrial/retail attribute values.
The full engine will be extended as more upstream candidate data surfaces.

DESIGN DECISION — what counts as a "LOV field"?
  Only controlled-vocabulary attributes have a LOV (Material, Color,
  Mounting Type, etc.).  Numeric/measurement attributes (Voltage Rating,
  Amperage Rating, Sound Level, ...) do NOT have a LOV — their values
  are validated structurally by uom.py, not by value matching.
  If a label is not in LOV_FIELDS, this function returns (value, True)
  so it does NOT trigger a needs_review flag for the absence of a LOV.
"""

from typing import Tuple

# ---------------------------------------------------------------------------
# Synonym map: raw string (lower-cased at lookup) -> approved canonical form
# Seeded from confirmed ground-truth values + common inference.
# Add new synonyms here as upstream AI surfaces them.
# ---------------------------------------------------------------------------
_SYNONYMS: dict[str, str] = {
    # ── Material ─────────────────────────────────────────────────────────────
    "stainless steel":      "Stainless Steel",
    "ss":                   "Stainless Steel",
    "sst":                  "Stainless Steel",
    "stainless-steel":      "Stainless Steel",
    "stainless":            "Stainless Steel",
    "steel":                "Steel",
    "aluminum":             "Aluminum",
    "aluminium":            "Aluminum",
    "alum":                 "Aluminum",
    "plastic":              "Plastic",
    "polypropylene":        "Polypropylene",
    "pp":                   "Polypropylene",
    "abs":                  "ABS Plastic",
    "abs plastic":          "ABS Plastic",
    "copper":               "Copper",
    "brass":                "Brass",
    "cast iron":            "Cast Iron",
    "iron":                 "Cast Iron",
    "glass":                "Glass",
    "tempered glass":       "Tempered Glass",
    "rubber":               "Rubber",
    "silicone":             "Silicone",
    "nylon":                "Nylon",
    # ── Color ─────────────────────────────────────────────────────────────────
    "stainless steel color": "Stainless Steel",   # color field usage
    "black":                 "Black",
    "white":                 "White",
    "silver":                "Silver",
    "gray":                  "Gray",
    "grey":                  "Gray",
    "red":                   "Red",
    "blue":                  "Blue",
    "green":                 "Green",
    "bronze":                "Bronze",
    "nickel":                "Nickel",
    "chrome":                "Chrome",
    "brushed nickel":        "Brushed Nickel",
    # ── Mounting Type ─────────────────────────────────────────────────────────
    "leg":                   "Leg",
    "leg mounting":          "Leg",
    "built-in":              "Built-in",
    "built in":              "Built-in",
    "surface":               "Surface",
    "recessed":              "Recessed",
    "flush":                 "Flush",
    "semi-flush":            "Semi-Flush",
    "pendant":               "Pendant",
    "wall":                  "Wall",
    "ceiling":               "Ceiling",
    # ── Plug Type ─────────────────────────────────────────────────────────────
    "hardwire":              "Hardwire",
    "hard wire":             "Hardwire",
    "hardwired":             "Hardwire",
    "cord":                  "Cord",
    "nema 5-15":             "NEMA 5-15",
    "nema 5-20":             "NEMA 5-20",
    # ── Product type / name  (from confirmed ground truth) ────────────────────
    "dishwasher":            "Dishwasher",
    # ── Boolean-like ─────────────────────────────────────────────────────────
    "yes":                   "Yes",
    "no":                    "No",
    "true":                  "Yes",
    "false":                 "No",
}

# Alias for external API compatibility
SEED_SYNONYM_MAP = _SYNONYMS

# ---------------------------------------------------------------------------
# LOV_FIELDS: set of label strings (lower-cased) that ARE controlled-vocab.
# Labels NOT in this set are treated as free-text / numeric — no LOV check.
# ---------------------------------------------------------------------------
_LOV_FIELDS: set[str] = {
    "material",
    "color",
    "colour",
    "finish",
    "mounting type",
    "plug type",
    "product name",
    "brand",
    "brand name",
    "series",
    "type",
    "style",
    "fuel type",
    "door style",
    "handle style",
    "control type",
    "installation type",
    "item type",
    "application",
}


def normalize_attribute_value(
    classpath: str,
    label: str,
    value: str,
) -> Tuple[str, bool]:
    """
    Attempt to normalise *value* for *label* against the LOV.

    Parameters
    ----------
    classpath : Product classpath string (reserved for future per-category
                LOV tables — not yet used, but accepted for API stability).
    label     : Attribute label string (e.g. "Material", "Color").
    value     : Raw candidate value from upstream extraction.

    Returns
    -------
    (canonical_value, lov_matched)

    - If the label is NOT a LOV field (numeric/measurement attribute):
        returns (value, True)  — no LOV check applies; do not flag.
    - If the label IS a LOV field and the value matches a known synonym:
        returns (canonical_form, True)
    - If the label IS a LOV field but the value is not recognised:
        returns (value, False)  — caller should set needs_review=True.

    NOTE: This stub covers values seen in ground truth + common inference.
    Unrecognised values from a controlled-vocab field are flagged, not
    silently accepted or rejected — the human reviewer makes the final call.
    """
    if not value:
        return (value, False)

    label_key = label.strip().lower()
    value_key  = value.strip().lower()

    # Not a controlled-vocab field → no LOV constraint, treat as matched
    if label_key not in _LOV_FIELDS:
        return (value, True)

    # Controlled-vocab field → look up synonym
    canonical = _SYNONYMS.get(value_key)
    if canonical is not None:
        return (canonical, True)

    # Not found in synonym map → flag for human review
    return (value, False)
