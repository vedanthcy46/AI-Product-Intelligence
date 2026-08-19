"""
grounding.py -- Source-grounding compliance check.

A "grounded" attribute is one whose value can be traced back to a real
source document (manufacturer page, spec sheet, etc.).  Ungrounded values
came from AI hallucination or missing provenance — they should be flagged
but not automatically rejected (the human reviewer decides).
"""


def validate_grounding(attribute: dict) -> bool:
    """
    Return True if the attribute has a non-None, non-empty source.

    Parameters
    ----------
    attribute : dict with at minimum the key "source" (Optional[str]).
                A None or empty-string source means the value has no
                traceable provenance.

    Returns
    -------
    bool -- True if grounded (source present), False otherwise.
    """
    source = attribute.get("source")
    return bool(source and str(source).strip())
