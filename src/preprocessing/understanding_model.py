"""
T4 — Product Understanding: data model

ProductUnderstanding is the intermediate structured representation produced
from a raw ProductInput. It holds candidate facts — not yet normalized or
validated — that feed into:
  - Classification (T5)
  - RAG query generation (T6/T7)
  - Attribute extraction (T8)
  - Content generation (Vedanth)

Example:
    Raw:  "3/8 CPLG BRS 150#"
    →
    ProductUnderstanding(
        product_type="Coupling",
        size="3/8",
        material="Brass",
        pressure_rating="150 lb",
    )
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProductUnderstanding:
    # Core identity
    product_type: Optional[str] = field(default=None)       # e.g. "Coupling", "Valve"
    series: Optional[str] = field(default=None)
    model_number: Optional[str] = field(default=None)       # cleaned MPN

    # Physical attributes (candidate values — not yet UOM-normalized)
    size: Optional[str] = field(default=None)
    material: Optional[str] = field(default=None)
    finish: Optional[str] = field(default=None)
    color: Optional[str] = field(default=None)
    shape: Optional[str] = field(default=None)

    # Ratings / specs
    pressure_rating: Optional[str] = field(default=None)
    temperature_rating: Optional[str] = field(default=None)
    voltage: Optional[str] = field(default=None)
    amperage: Optional[str] = field(default=None)
    wattage: Optional[str] = field(default=None)

    # Connection / configuration
    thread_type: Optional[str] = field(default=None)        # e.g. "NPT", "BSP"
    connection_type: Optional[str] = field(default=None)
    end_type: Optional[str] = field(default=None)
    gender: Optional[str] = field(default=None)             # Male / Female

    # Application context
    application: Optional[str] = field(default=None)
    industry: Optional[str] = field(default=None)

    # Catch-all for real facts that don't map to a named field
    extra_attributes: dict[str, str] = field(default_factory=dict)

    # Provenance — never used as facts
    row_id: Optional[str] = field(default=None)
    source_desc: Optional[str] = field(default=None)        # original Part_Desc for audit

    def to_dict(self) -> dict:
        """Full serialization including provenance fields."""
        return dataclasses.asdict(self)

    def known_facts(self) -> dict[str, str]:
        """
        Non-None named fact fields only — excludes extra_attributes, row_id,
        source_desc. Used by classification and RAG query generation.
        """
        skip = {"row_id", "source_desc", "extra_attributes"}
        return {
            k: v
            for k, v in dataclasses.asdict(self).items()
            if k not in skip and v is not None
        }

    def all_facts(self) -> dict[str, str]:
        """known_facts merged with extra_attributes. Used by content generation."""
        return {**self.known_facts(), **self.extra_attributes}

    def is_empty(self) -> bool:
        """True if no facts were extracted at all."""
        return not self.known_facts() and not self.extra_attributes
