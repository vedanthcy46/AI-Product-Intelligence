from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

# Placeholder values that should be treated as empty
_PLACEHOLDERS = {
    "-- unbranded --",
    "-- no unilog brand --",
    "-- no dib brand --",
    "-- no e1 brand --",
    "n/a",
    "none",
    "",
}


def _clean(value: Optional[str]) -> Optional[str]:
    """Strip whitespace; return None for placeholder/empty values."""
    if pd.isna(value) if isinstance(value, float) else value is None:
        return None
    v = str(value).strip()
    if v.lower() in _PLACEHOLDERS:
        return None
    return v or None


@dataclass
class ProductInput:
    mfg_part_num: Optional[str] = field(default=None)
    part_desc: Optional[str] = field(default=None)
    e1_brand: Optional[str] = field(default=None)
    unilog_brand: Optional[str] = field(default=None)
    dib_brand: Optional[str] = field(default=None)
    part_manuf: Optional[str] = field(default=None)
    row_id: Optional[str] = field(default=None)  # traceability through the pipeline

    @classmethod
    def from_row(cls, row: dict, row_id: Optional[str] = None) -> "ProductInput":
        """Build a cleaned ProductInput from a raw catalogue row dict."""
        return cls(
            mfg_part_num=_clean(row.get("Mfg_Part_Num")),
            part_desc=_clean(row.get("Part_Desc")),
            e1_brand=_clean(row.get("E1_Brand")),
            unilog_brand=_clean(row.get("Unilog_Brand")),
            dib_brand=_clean(row.get("DIB_Brand")),
            part_manuf=_clean(row.get("Part_Manuf")),
            row_id=str(row_id) if row_id is not None else None,
        )

    @property
    def best_brand(self) -> Optional[str]:
        """Return the first non-None brand signal in priority order."""
        return self.unilog_brand or self.e1_brand or self.dib_brand

    @property
    def best_manufacturer(self) -> Optional[str]:
        """part_manuf first; falls back to best_brand when part_manuf is absent."""
        return self.part_manuf or self.best_brand

    def has_any_brand(self) -> bool:
        return self.best_brand is not None

    def to_dict(self) -> dict:
        return {
            "row_id": self.row_id,
            "mfg_part_num": self.mfg_part_num,
            "part_desc": self.part_desc,
            "e1_brand": self.e1_brand,
            "unilog_brand": self.unilog_brand,
            "dib_brand": self.dib_brand,
            "part_manuf": self.part_manuf,
        }
