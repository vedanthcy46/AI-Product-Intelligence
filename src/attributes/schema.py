"""
schema.py -- Shared Attribute data model.

Single source of truth for an attribute slot in the 252-column output schema.
Every ATTRIBUTE_LABEL/VALUE/UOM triple produced by the pipeline is represented
as one Attribute object before being serialised into the positional slots.
"""

from pydantic import BaseModel
from typing import Optional


class Attribute(BaseModel):
    label: str
    value: Optional[str] = None
    uom: Optional[str] = None
    raw_value: Optional[str] = None      # pre-normalisation, kept for audit trail
    source: Optional[str] = None
    source_page: Optional[int] = None
    confidence: float = 0.5
    lov_matched: bool = False
    needs_review: bool = False
