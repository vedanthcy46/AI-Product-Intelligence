"""
validator.py -- Orchestration layer: full product-level validation.

Runs every atomic check across all attributes and description fields of a
product dict and collects a structured compliance report.

Expected product dict shape (minimal)
--------------------------------------
{
  "descriptions": {
      "INVOICE_DESC": "...",
      "SHORT_DESC":   "...",
      ...
  },
  "attributes": [
      {
          "label":      str,
          "value":      Optional[str],
          "uom":        Optional[str],
          "source":     Optional[str],
          "lov_matched": bool,
          ...
      },
      ...
  ]
}

Both keys are optional -- an absent key is treated as empty.
"""

from typing import Optional

from src.validation.rules import validate_lov_compliance, validate_uom_compliance
from src.validation.character_limits import validate_character_limit, CHARACTER_LIMITS
from src.validation.grounding import validate_grounding


def validate_product(product: dict, known_uoms: set) -> dict:
    """
    Run all validation checks and return a structured compliance report.

    Parameters
    ----------
    product    : Product dict (see module docstring for shape).
    known_uoms : Set of approved UOM abbreviation strings.
                 Typically: set(uom.UOM_TABLE.values())

    Returns
    -------
    {
      "valid": bool,
          # True only if there are zero hard violations.
          # Hard violations: character limit exceeded.
          # Soft issues (LOV non-match, low grounding) are reported
          # in "issues" but do NOT make valid=False alone -- they
          # require human review, not automatic rejection.

      "issues": list[str],
          # Human-readable description of every problem found.

      "lov_compliance_rate": float,
          # % of attributes where lov_matched is True.
          # Attributes with value=None are EXCLUDED from this denominator
          # (a known-but-unfilled label has no value to LOV-check).

      "uom_compliance_rate": float,
          # % of attributes that HAVE a uom AND whose uom is in known_uoms.
          # Denominator = attributes that have a non-None uom.

      "grounding_rate": float,
          # % of attributes with a non-None, non-empty source.
          # Denominator = all attributes (including value=None ones).

      "character_compliant_fields": list[str],
          # Fields checked (have a known limit) and within limit.

      "character_non_compliant_fields": list[str],
          # Fields checked (have a known limit) and over limit.

      "unchecked_fields": list[str],
          # Fields present in descriptions but with no known limit.
          # Honestly reported as unchecked; not passed or failed.
    }
    """
    issues: list[str] = []
    attributes: list[dict] = product.get("attributes", [])
    descriptions: dict = product.get("descriptions", {})

    # ── LOV compliance ────────────────────────────────────────────────────────
    # Exclude value=None attributes from the LOV denominator.
    lov_checkable = [a for a in attributes if a.get("value") is not None]
    if lov_checkable:
        lov_passed  = [a for a in lov_checkable if validate_lov_compliance(a)]
        lov_failed  = [a for a in lov_checkable if not validate_lov_compliance(a)]
        lov_rate    = len(lov_passed) / len(lov_checkable)
        for a in lov_failed:
            issues.append(
                f"LOV non-compliance: attribute '{a.get('label')}' "
                f"value={a.get('value')!r} not LOV-matched -- needs human review"
            )
    else:
        lov_rate = 1.0  # no checkable attributes -> trivially compliant

    # ── UOM compliance ────────────────────────────────────────────────────────
    uom_checkable = [a for a in attributes if a.get("uom")]
    if uom_checkable:
        uom_passed = [a for a in uom_checkable if validate_uom_compliance(a, known_uoms)]
        uom_failed = [a for a in uom_checkable if not validate_uom_compliance(a, known_uoms)]
        uom_rate   = len(uom_passed) / len(uom_checkable)
        for a in uom_failed:
            issues.append(
                f"UOM non-compliance: attribute '{a.get('label')}' "
                f"uom={a.get('uom')!r} not in approved UOM set"
            )
    else:
        uom_rate = 1.0

    # ── Grounding ─────────────────────────────────────────────────────────────
    # Factual claims to ground are attributes with non-None values.
    ground_checkable = [a for a in attributes if a.get("value") is not None]
    if ground_checkable:
        grounded    = [a for a in ground_checkable if validate_grounding(a)]
        ungrounded  = [a for a in ground_checkable if not validate_grounding(a)]
        ground_rate = len(grounded) / len(ground_checkable)
        for a in ungrounded:
            issues.append(
                f"Ungrounded: attribute '{a.get('label')}' "
                f"value={a.get('value')!r} has no source -- needs review"
            )
    else:
        ground_rate = 1.0

    # ── Character limits ──────────────────────────────────────────────────────
    char_compliant:     list[str] = []
    char_non_compliant: list[str] = []
    unchecked:          list[str] = []
    hard_violation      = False

    for field_name, value in descriptions.items():
        result = validate_character_limit(field_name, value or "")
        if result is True:
            char_compliant.append(field_name)
        elif result is False:
            char_non_compliant.append(field_name)
            hard_violation = True
            char_count = len(value) if value else 0
            limit      = CHARACTER_LIMITS.get(field_name, "?")
            val_str = repr(value)
            val_preview = (val_str[:60] + "...") if len(val_str) > 60 else val_str
            issues.append(
                f"Character limit exceeded: {field_name} is {char_count} chars "
                f"(limit={limit}): {val_preview}"
            )
        else:  # result is None
            unchecked.append(field_name)

    # ── Overall validity ──────────────────────────────────────────────────────
    # Hard violations: character limit exceeded.
    # Soft issues (LOV, grounding) are informational -- human review, not auto-reject.
    valid = not hard_violation

    return {
        "valid":                          valid,
        "issues":                         issues,
        "lov_compliance_rate":            round(lov_rate, 4),
        "uom_compliance_rate":            round(uom_rate, 4),
        "grounding_rate":                 round(ground_rate, 4),
        "character_compliant_fields":     char_compliant,
        "character_non_compliant_fields": char_non_compliant,
        "unchecked_fields":               unchecked,
    }
