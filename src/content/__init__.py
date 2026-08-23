"""
content/__init__.py -- Content generation package (Vedanth track, V2-V7).

Exposes the ContentGenerator facade and every individual generator so the
pipeline can call the full set or a single field.
"""

from src.content.generator import ContentGenerator, generate_content
from src.content.invoice import generate_invoice_desc
from src.content.mobile import generate_mobile_desc
from src.content.title import generate_short_desc, generate_retail_desc
from src.content.long_description import generate_long_desc
from src.content.marketing import generate_marketing_description
from src.content.features import generate_features

__all__ = [
    "ContentGenerator",
    "generate_content",
    "generate_invoice_desc",
    "generate_mobile_desc",
    "generate_short_desc",
    "generate_retail_desc",
    "generate_long_desc",
    "generate_marketing_description",
    "generate_features",
]