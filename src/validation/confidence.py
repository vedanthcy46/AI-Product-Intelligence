"""
confidence.py -- Confidence scoring and human-review triage engine.

Combines upstream extraction confidence (manufacturer matching, classification)
with downstream deterministic validation metrics (LOV, UOM, grounding)
into a unified per-product confidence score and triage status.

Weights Breakdown (100% total):
  - 25% Manufacturer Match Confidence  (upstream entity resolution)
  - 25% Classification Confidence       (upstream category assignment)
  - 20% LOV Compliance Rate             (downstream controlled-vocab match)
  - 15% UOM Compliance Rate             (downstream unit validity)
  - 15% Grounding Rate                  (downstream source provenance)

Status Tiers:
  - HIGH   : overall_score > 0.85
  - MEDIUM : 0.60 <= overall_score <= 0.85
  - LOW    : overall_score < 0.60

Human Review Triage:
  needs_review = True if:
    - status == "LOW"
    - OR validation_result["valid"] is False (hard validation errors)
    - OR any attribute in product["attributes"] has needs_review == True
"""

from typing import Optional


def compute_confidence(
    product: dict,
    validation_result: dict,
    manufacturer_match_confidence: float = 1.0,
    classification_confidence: float = 1.0,
) -> dict:
    """
    Compute product-level confidence score and review requirements.

    Parameters
    ----------
    product : dict
        Product dictionary containing 'attributes' and 'descriptions'.
    validation_result : dict
        Output from validator.validate_product().
    manufacturer_match_confidence : float, default 1.0
        Upstream confidence score for resolved manufacturer.
    classification_confidence : float, default 1.0
        Upstream confidence score for resolved category/classpath.

    Returns
    -------
    dict
        {
            "overall_confidence": float (rounded to 4 decimals),
            "status": "HIGH" | "MEDIUM" | "LOW",
            "needs_review": bool,
            "review_reasons": list[str],
        }
    """
    lov_rate = float(validation_result.get("lov_compliance_rate", 1.0))
    uom_rate = float(validation_result.get("uom_compliance_rate", 1.0))
    grounding_rate = float(validation_result.get("grounding_rate", 1.0))
    is_valid = bool(validation_result.get("valid", True))

    # -- Weighted average computation -----------------------------------------
    # Weights: 25% mfr, 25% class, 20% lov, 15% uom, 15% grounding
    overall_score = (
        0.25 * manufacturer_match_confidence
        + 0.25 * classification_confidence
        + 0.20 * lov_rate
        + 0.15 * uom_rate
        + 0.15 * grounding_rate
    )
    overall_score = round(overall_score, 4)

    # -- Status assignment ---------------------------------------------------
    if overall_score > 0.85:
        status = "HIGH"
    elif overall_score >= 0.60:
        status = "MEDIUM"
    else:
        status = "LOW"

    # -- Identify review reasons ---------------------------------------------
    review_reasons: list[str] = []
    attributes = product.get("attributes", [])

    # Check for hard validation failure
    if not is_valid:
        review_reasons.append("Product failed hard validation checks (e.g. character limit exceeded)")
        for char_err in validation_result.get("character_non_compliant_fields", []):
            review_reasons.append(f"Field '{char_err}' exceeds allowed character limit")

    # Check for status LOW
    if status == "LOW":
        review_reasons.append(f"Overall confidence score ({overall_score:.2%}) is LOW (< 60%)")

    # Upstream confidence warnings
    if manufacturer_match_confidence < 0.70:
        review_reasons.append(f"Manufacturer match confidence is low ({manufacturer_match_confidence:.2%})")
    if classification_confidence < 0.70:
        review_reasons.append(f"Classification confidence is low ({classification_confidence:.2%})")

    # Downstream rate warnings & attribute-level flags
    unmatched_lov = [a for a in attributes if a.get("value") is not None and not a.get("lov_matched", False)]
    if unmatched_lov:
        labels_str = ", ".join(f"'{a.get('label')}'" for a in unmatched_lov[:3])
        if len(unmatched_lov) > 3:
            labels_str += f" (+{len(unmatched_lov)-3} more)"
        review_reasons.append(f"{len(unmatched_lov)} attribute(s) not LOV-matched: {labels_str}")

    if uom_rate < 1.0:
        review_reasons.append(f"UOM compliance rate is {uom_rate:.1%} (contains unapproved unit)")

    ungrounded_attrs = [a for a in attributes if a.get("value") is not None and not a.get("source")]
    if ungrounded_attrs:
        review_reasons.append(f"{len(ungrounded_attrs)} attribute(s) lack source grounding")

    # Check individual attribute needs_review flags
    flagged_attrs = [a for a in attributes if a.get("needs_review", False)]
    any_attr_needs_review = len(flagged_attrs) > 0
    for a in flagged_attrs:
        review_reasons.append(f"Attribute '{a.get('label')}' flagged with needs_review=True")

    # De-duplicate reasons while preserving order
    deduped_reasons = []
    seen = set()
    for r in review_reasons:
        if r not in seen:
            seen.add(r)
            deduped_reasons.append(r)

    # -- Determine needs_review ----------------------------------------------
    needs_review = (status == "LOW") or (not is_valid) or any_attr_needs_review

    return {
        "overall_confidence": overall_score,
        "status": status,
        "needs_review": needs_review,
        "review_reasons": deduped_reasons,
    }
