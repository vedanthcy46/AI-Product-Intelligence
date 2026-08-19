"""
grounding.py -- Evaluation metric for factual provenance across product batches.
"""

from typing import List, Dict, Any


def grounding_rate(products: List[Dict[str, Any]]) -> float:
    """
    Compute the percentage of attribute claims with a non-null source provenance.

    Parameters
    ----------
    products : list of dict
        List of product dictionaries containing an 'attributes' list.

    Returns
    -------
    float
        Fraction of populated attribute claims that have a non-empty source (0.0 to 1.0).
    """
    total_claims = 0
    grounded_claims = 0

    for prod in products:
        attrs = prod.get("attributes", [])
        for attr in attrs:
            val = attr.get("value")
            # Only count actual factual claims (attributes with a value)
            if val is not None and str(val).strip() != "":
                total_claims += 1
                source = attr.get("source")
                if source and str(source).strip():
                    grounded_claims += 1

    if total_claims == 0:
        return 1.0

    return round(grounded_claims / total_claims, 4)
