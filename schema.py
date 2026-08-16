"""Single source of truth: Product model — agreed by all in Phase 0.

Every extraction path (PDF, Excel) must return records shaped like this.
Provenance fields (confidence, source) are auto-populated by extractors;
flags are added by the validation layer (Phase 4).
"""

from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]

# The 5-8 core fields of the schema. All optional — missing means null,
# never a guess.
PRODUCT_FIELDS: tuple[str, ...] = (
    "product_name",
    "size",
    "material",
    "pressure_rating",
    "thread_type",
    "temperature_range",
)


class Product(BaseModel):
    product_name: str | None = None
    size: str | None = None  # e.g., "2 inch", "DN50"
    material: str | None = None  # e.g., "Carbon Steel", "316SS"
    pressure_rating: str | None = None  # e.g., "200 WOG", "PN16"
    thread_type: str | None = None  # e.g., "NPT", "BSPP", "Metric"
    temperature_range: str | None = None  # e.g., "-20°C to 200°C"

    # provenance fields (auto-populated)
    confidence: dict[str, Confidence] = Field(default_factory=dict)
    source: dict[str, str] = Field(default_factory=dict)  # "page 2" or "row 5 of valves.xlsx"
    flags: list[str] = Field(default_factory=list)
