"""
generator.py -- ContentGenerator facade (V2).

Assembles all description fields and feature bullets into the internal
product dict under `descriptions` and `features`, ready for:
  - the output mapper (252-column serialisation)
  - the validator (character limits, grounding)
  - the frontend (product detail / review)
"""

from typing import Any

from src.content.invoice import generate_invoice_desc
from src.content.mobile import generate_mobile_desc
from src.content.title import generate_short_desc, generate_retail_desc
from src.content.long_description import generate_long_desc
from src.content.marketing import generate_marketing_description
from src.content.features import generate_features

DESCRIPTION_FIELDS = [
    "MOBILE_DESC",
    "INVOICE_DESC",
    "SHORT_DESC",
    "LONG_DESC1",
    "RETAIL_DESC",
    "MARKETING_DESCRIPTION",
]


class ContentGenerator:
    """Deterministic content generation over a verified internal product dict."""

    def generate(self, product: dict) -> dict:
        """
        Populate and return *product* with `descriptions` and `features`.

        The input dict is mutated (its 'descriptions' and 'features' keys are
        (re)written) and returned, matching the pipeline's pass-by-reference
        style.
        """
        descriptions = {
            "MOBILE_DESC": generate_mobile_desc(product),
            "INVOICE_DESC": generate_invoice_desc(product),
            "SHORT_DESC": generate_short_desc(product),
            "LONG_DESC1": generate_long_desc(product),
            "RETAIL_DESC": generate_retail_desc(product),
            "MARKETING_DESCRIPTION": generate_marketing_description(product),
        }
        product["descriptions"] = descriptions
        product["features"] = generate_features(product)
        return product


def generate_content(product: dict) -> dict:
    """Module-level convenience wrapper around ContentGenerator.generate."""
    return ContentGenerator().generate(product)