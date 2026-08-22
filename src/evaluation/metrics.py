"""
metrics.py -- Unified evaluation metrics suite.

Combines ground-truth field accuracy, LOV/UOM compliance, grounding rate,
and provides structural completeness scoring for unlabeled bulk datasets.
"""

from typing import List, Dict, Any, Set, Optional
from src.evaluation.field_accuracy import field_accuracy
from src.evaluation.grounding import grounding_rate
from src.validation.validator import validate_product
from src.validation.confidence import compute_confidence


def full_evaluation(
    predicted_products: List[Dict[str, Any]],
    expected_products: List[Dict[str, Any]],
    known_uoms: Set[str],
    fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Comprehensive evaluation against labeled ground truth.

    Combines:
      - Field accuracy across common/specified fields
      - LOV compliance rate
      - UOM compliance rate
      - Source grounding rate
      - Review rate (% requiring manual triage)
    """
    if fields is None:
        # Default core fields to evaluate
        fields = [
            "MANUFACTURER_NAME",
            "BRAND_NAME",
            "Classpath",
            "Product Name",
            "INVOICE_DESC",
            "SHORT_DESC",
            "MOBILE_DESC",
            "RETAIL_DESC",
        ]

    n_rows = min(len(predicted_products), len(expected_products))

    # 1. Field Accuracy
    acc_result = field_accuracy(predicted_products, expected_products, fields)

    # 2. Validation & Confidence metrics over predicted records
    lov_rates: List[float] = []
    uom_rates: List[float] = []
    needs_review_count = 0

    for prod in predicted_products:
        val_res = validate_product(prod, known_uoms)
        conf_res = compute_confidence(prod, val_res)

        lov_rates.append(val_res["lov_compliance_rate"])
        uom_rates.append(val_res["uom_compliance_rate"])
        if conf_res["needs_review"]:
            needs_review_count += 1

    avg_lov = round(sum(lov_rates) / len(lov_rates), 4) if lov_rates else 1.0
    avg_uom = round(sum(uom_rates) / len(uom_rates), 4) if uom_rates else 1.0
    g_rate = grounding_rate(predicted_products)
    rev_rate = round(needs_review_count / len(predicted_products), 4) if predicted_products else 0.0

    eval_result = {
        "field_accuracy": acc_result,
        "lov_compliance_rate": avg_lov,
        "uom_compliance_rate": avg_uom,
        "grounding_rate": g_rate,
        "review_rate": rev_rate,
        "n_evaluated": n_rows,
    }

    if n_rows < 5:
        eval_result["warning"] = "small sample size, results indicative only"

    return eval_result


def structural_completeness(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Structural completeness and health metrics for unlabelled bulk datasets (e.g. 1000-row batch).

    This serves as an honest, verifiable proxy for data health when ground truth
    labels are not available.
    """
    total = len(products)
    if total == 0:
        return {
            "n_products": 0,
            "classpath_populated_pct": 0.0,
            "manufacturer_populated_pct": 0.0,
            "brand_populated_pct": 0.0,
            "avg_attributes_per_product": 0.0,
            "needs_review_pct": 0.0,
        }

    classpath_pop = 0
    mfr_pop = 0
    brand_pop = 0
    total_attrs = 0
    review_count = 0

    for p in products:
        if p.get("classpath") or p.get("Classpath"):
            classpath_pop += 1
        if p.get("manufacturer_name") or p.get("MANUFACTURER_NAME"):
            mfr_pop += 1
        if p.get("brand_name") or p.get("BRAND_NAME"):
            brand_pop += 1

        attrs = p.get("attributes", [])
        populated_attrs = [a for a in attrs if a.get("value") is not None and str(a.get("value")).strip()]
        total_attrs += len(populated_attrs)

        if p.get("needs_review", False):
            review_count += 1

    return {
        "n_products": total,
        "classpath_populated_pct": round(classpath_pop / total, 4),
        "manufacturer_populated_pct": round(mfr_pop / total, 4),
        "brand_populated_pct": round(brand_pop / total, 4),
        "avg_attributes_per_product": round(total_attrs / total, 2),
        "needs_review_pct": round(review_count / total, 4),
    }
