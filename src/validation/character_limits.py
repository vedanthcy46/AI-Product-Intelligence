"""
character_limits.py -- Per-field character-limit enforcement.

IMPORTANT: The official content-guidelines document was NOT distributed
with the challenge.  Only one limit is confirmed from real ground truth.
All others are marked as TODO and must NOT be assumed correct.
"""

from typing import Optional

# ---------------------------------------------------------------------------
# CHARACTER_LIMITS
# Key  : exact output column name (case-sensitive)
# Value: maximum allowed character count (inclusive)
# ---------------------------------------------------------------------------
CHARACTER_LIMITS: dict[str, int] = {
    # ── CONFIRMED from real ground-truth rows ─────────────────────────────────
    # Both Frigidaire and Whirlpool INVOICE_DESC examples are 39-40 chars.
    "INVOICE_DESC": 40,

    # ── TODO: limits below this line are NOT confirmed ────────────────────────
    # Add real values when/if the content guidelines doc becomes available.
    # "MOBILE_DESC":       ???,
    # "SHORT_DESC":        ???,
    # "LONG_DESC1":        ???,
    # "RETAIL_DESC":       ???,
    # "MARKETING_DESCRIPTION": ???,
    # "ITEM_FEATURES_*":   ???,
}


def validate_character_limit(field_name: str, value: str) -> Optional[bool]:
    """
    Check whether *value* fits within the known character limit for *field_name*.

    Returns
    -------
    True   -- field has a known limit AND value is within it.
    False  -- field has a known limit AND value exceeds it.
    None   -- field has NO known limit (not checkable).
              This is deliberately distinct from True/False:
              "not checked" != "passed".  Callers should surface
              unchecked fields separately rather than silently passing them.

    Parameters
    ----------
    field_name : Exact column name string (e.g. "INVOICE_DESC").
    value      : The string value to check.  None/empty is treated as 0 chars.
    """
    limit = CHARACTER_LIMITS.get(field_name)
    if limit is None:
        return None   # no known limit -- cannot validate

    char_count = len(value) if value else 0
    return char_count <= limit
