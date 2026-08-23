"""
field_accuracy.py -- Field-by-field accuracy evaluation against ground truth.

Compares predicted values against expected ground-truth values.
Includes small-sample size disclaimers when evaluating against limited benchmarks.
"""

from typing import Optional, List, Dict, Any


def compare_field(predicted: Optional[Any], expected: Optional[Any]) -> bool:
    """
    Compare predicted vs expected field value.

    Normalization:
      - Treats None, NaN, and whitespace-only strings as empty.
      - Case-insensitive string comparison after trimming whitespace.
      - If both are empty -> returns True (correctly identified as blank).
      - If one is empty and other is not -> returns False.
    """
    # Normalize predicted
    if predicted is None:
        p_str = ""
    else:
        p_str = str(predicted).strip()
        if p_str.lower() in ("nan", "none", "null"):
            p_str = ""

    # Normalize expected
    if expected is None:
        e_str = ""
    else:
        e_str = str(expected).strip()
        if e_str.lower() in ("nan", "none", "null"):
            e_str = ""

    # Both empty is a match
    if not p_str and not e_str:
        return True

    # Case-insensitive comparison
    return p_str.lower() == e_str.lower()


def field_accuracy(
    predicted_products: List[Dict[str, Any]],
    expected_products: List[Dict[str, Any]],
    fields: List[str],
) -> Dict[str, Any]:
    """
    Compute per-field accuracy and overall average accuracy.

    Parameters
    ----------
    predicted_products : list of dict
        Predicted product records.
    expected_products : list of dict
        Ground-truth product records.
    fields : list of str
        Field names to evaluate.

    Returns
    -------
    dict
        {
            "per_field": {field: accuracy_pct},
            "overall": float,
            "n_rows": int,
            "warning": Optional[str],
        }
    """
    n_rows = min(len(predicted_products), len(expected_products))
    if n_rows == 0 or not fields:
        return {
            "per_field": {},
            "overall": 0.0,
            "n_rows": n_rows,
            "warning": "No rows or fields to evaluate",
        }

    per_field_correct: Dict[str, int] = {f: 0 for f in fields}

    for p, e in zip(predicted_products[:n_rows], expected_products[:n_rows]):
        for f in fields:
            p_val = p.get(f)
            e_val = e.get(f)
            if compare_field(p_val, e_val):
                per_field_correct[f] += 1

    per_field_acc = {
        f: round(per_field_correct[f] / n_rows, 4) for f in fields
    }

    overall_acc = round(sum(per_field_acc.values()) / len(fields), 4)

    result = {
        "per_field": per_field_acc,
        "overall": overall_acc,
        "n_rows": n_rows,
    }

    if n_rows < 5:
        result["warning"] = "small sample size, results indicative only"

    return result
