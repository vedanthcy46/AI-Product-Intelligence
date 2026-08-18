"""
mapper.py -- Attribute candidate orchestration layer.

Sits between upstream AI extraction and the downstream normalisation engines.
Consumes a raw candidate dict, runs it through UOM and LOV normalisation,
and returns a fully populated Attribute object ready for output serialisation.

Flow
----
upstream dict
    -> UOM normalisation  (uom.py)
    -> LOV normalisation  (lov.py)
    -> Attribute object   (schema.py)
    -> output slot mapper (src/output/mapper.py)
"""

from typing import Optional

from src.attributes.schema import Attribute
from src.normalization.uom import normalize_uom
from src.normalization.lov import normalize_attribute_value
from src.normalization.fraction_utils import decimal_to_fraction

# Confidence threshold below which a value is automatically flagged.
CONFIDENCE_THRESHOLD: float = 0.7


def normalize_candidate_attribute(
    classpath: str,
    candidate: dict,
) -> Attribute:
    """
    Normalise one upstream extraction candidate into a validated Attribute.

    Parameters
    ----------
    classpath : Product classpath string — passed through to LOV engine for
                future per-category LOV tables.
    candidate : Dict from upstream extraction shaped as:
                {
                  "label"           : str,
                  "candidate_value" : Optional[str],
                  "candidate_uom"   : Optional[str],
                  "source"          : Optional[str],
                  "source_page"     : Optional[int],
                  "confidence"      : Optional[float],
                }

    Returns
    -------
    Attribute — fully populated, with needs_review set according to rules.

    needs_review is True if ANY of:
      - lov_matched is False           (unrecognised LOV value)
      - confidence < CONFIDENCE_THRESHOLD (0.7)
      - UOM normalisation failed for a value that had a uom

    needs_review is False for a value=None label (known-but-unfilled attribute)
    — confirmed valid state in ground truth; not an error.
    """
    label         = (candidate.get("label") or "").strip()
    raw_candidate = candidate.get("candidate_value")
    candidate_uom = candidate.get("candidate_uom")
    source        = candidate.get("source")
    source_page   = candidate.get("source_page")
    try:
        confidence    = float(candidate.get("confidence") or 0.5)
    except (ValueError, TypeError):
        confidence    = 0.5  # malformed upstream value — default to mid-confidence

    # Normalise None and whitespace-only to a clean None
    candidate_value: Optional[str] = (
        raw_candidate.strip() if isinstance(raw_candidate, str) and raw_candidate.strip()
        else None
    )

    # ── Step 1: No value ─────────────────────────────────────────────────────
    # "Known label, unfilled value" is a valid state per confirmed ground truth
    # (e.g. ATTRIBUTE_LABEL "Model" present with blank ATTRIBUTE_VALUE).
    # Do NOT flag this as needs_review.
    if candidate_value is None:
        return Attribute(
            label=label,
            value=None,
            uom=(candidate_uom or None),
            raw_value=None,
            source=source,
            source_page=source_page,
            confidence=confidence,
            lov_matched=False,
            needs_review=False,
        )

    # ── Step 2: UOM normalisation ─────────────────────────────────────────────
    uom_norm_failed = False
    normalised_uom: Optional[str] = None

    if candidate_uom and candidate_uom.strip():
        normalised_uom = normalize_uom(candidate_uom.strip())
        if normalised_uom is None:
            # Unrecognised unit — keep raw string for audit, flag for review
            uom_norm_failed = True
            normalised_uom  = candidate_uom.strip()

    # ── Step 3: LOV normalisation ─────────────────────────────────────────────
    canonical_value, lov_matched = normalize_attribute_value(
        classpath, label, candidate_value
    )

    # ── Step 3b: Fraction normalisation for inch measurements ────────────────
    if normalised_uom == "in" and canonical_value:
        try:
            val_float = float(canonical_value)
            canonical_value = decimal_to_fraction(val_float)
        except ValueError:
            # Already a fraction (e.g. "50-1/4") or complex dimension string
            pass

    # ── Step 4: needs_review ──────────────────────────────────────────────────
    needs_review = (
        not lov_matched
        or confidence < CONFIDENCE_THRESHOLD
        or uom_norm_failed
    )

    return Attribute(
        label=label,
        value=canonical_value,
        uom=normalised_uom,
        raw_value=candidate_value,      # original, pre-normalisation
        source=source,
        source_page=source_page,
        confidence=confidence,
        lov_matched=lov_matched,
        needs_review=needs_review,
    )
