"""
rules.py -- Atomic LOV and UOM compliance checks.

These are the lowest-level predicate functions used by validator.py.
Each takes a plain dict so callers can use raw dicts OR Attribute objects
serialised via .model_dump().
"""

from typing import Optional


def validate_lov_compliance(attribute: dict) -> bool:
    """
    Return True if the attribute's value is confirmed as LOV-matched.

    A LOV-matched attribute means the upstream lov.py recognised the value
    as a known canonical form or synonym.  An unmatched value is not
    necessarily wrong -- it may be a legitimate new value not yet in our
    inferred LOV stub -- but it requires human review.

    Parameters
    ----------
    attribute : dict with at minimum the key "lov_matched" (bool).
                Accepts both raw dicts and Attribute.model_dump() output.

    Returns
    -------
    bool -- True if lov_matched is truthy, False otherwise.
    """
    return bool(attribute.get("lov_matched", False))


def validate_uom_compliance(attribute: dict, known_uoms: set) -> bool:
    """
    Return True if the attribute's UOM is acceptable.

    Acceptable means:
      (a) The attribute has no UOM (uom is None / empty) -- perfectly valid
          for non-measurement attributes like "Series", "Mounting Type", etc.
      (b) The UOM is present AND appears in the caller-supplied known_uoms set.

    The known_uoms set should be the set of approved abbreviations from
    uom.UOM_TABLE.values() or a tighter project-specific subset.

    Parameters
    ----------
    attribute  : dict with at minimum the key "uom" (Optional[str]).
    known_uoms : Set of approved UOM abbreviation strings (e.g. {"V","A","in"}).

    Returns
    -------
    bool -- True if compliant, False if a UOM is present but unrecognised.
    """
    uom = attribute.get("uom")
    if not uom:          # None or empty string -- no UOM needed, fine
        return True
    return uom in known_uoms
