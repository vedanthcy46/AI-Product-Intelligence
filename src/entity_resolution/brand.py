"""
T3 — Brand Resolution
Pipeline: exact → normalized → fuzzy
Reference: UniCat_Manufacturer_and_Brand_List.xlsx (same master as T2)

Intentionally deterministic-only — no LLM fallback.
Brand names are short and well-defined; fuzzy matching is sufficient,
and an LLM fallback risks hallucinating brand names.
"""

from __future__ import annotations

import os
import re
import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from src.entity_resolution._utils import normalize, similarity, coerce_code

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class BrandMatch:
    brand_name: Optional[str]
    brand_code: Optional[str]
    confidence: float
    method: str          # exact | normalized | fuzzy | unresolved
    needs_review: bool

    def __repr__(self) -> str:
        review = " ⚠ needs_review" if self.needs_review else ""
        return (
            f"BrandMatch({self.brand_name!r}, "
            f"code={self.brand_code!r}, "
            f"conf={self.confidence:.2f}, method={self.method}{review})"
        )


# ---------------------------------------------------------------------------
# Placeholder detection
# ---------------------------------------------------------------------------

_BRAND_PLACEHOLDERS = {
    "-- unbranded --",
    "-- no unilog brand --",
    "-- no dib brand --",
    "-- no e1 brand --",
    "unbranded",
    "n/a",
    "none",
    "",
}


def _is_placeholder(raw: str) -> bool:
    return raw.strip().lower() in _BRAND_PLACEHOLDERS


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

class BrandResolver:
    FUZZY_THRESHOLD = 0.85   # tighter than manufacturer — short strings need precision
    REVIEW_THRESHOLD = 0.72

    def __init__(self, master_path: str):
        """
        Load brand list from the same master Excel used by ManufacturerResolver.
        Prefers a Brand_Name column; falls back to Manufacturer_Name.

        If the master file is missing/unreadable the resolver degrades
        gracefully: brand values pass through as-is with low confidence,
        flagged for review (so downstream stages still run).
        """
        self._empty = True
        self._names: list[str] = []
        self._codes: list[Optional[str]] = []
        self._norm_names: list[str] = []
        self._exact_map: dict[str, int] = {}
        self._norm_map: dict[str, int] = {}

        if not master_path or not os.path.exists(master_path):
            logger.warning("Brand master not found (%s); pass-through mode (low confidence).", master_path)
            return

        df = pd.read_excel(master_path, dtype=str).fillna("")
        df.columns = [c.strip() for c in df.columns]

        name_col = self._find_col(df.columns, ["brand", "name"]) \
                or self._find_col(df.columns, ["manufacturer", "name"]) \
                or df.columns[0]

        code_col = self._find_col(df.columns, ["brand", "code"]) \
                or self._find_col(df.columns, ["code"])

        names, codes = self._load_master(df, name_col, code_col)
        norm_names = [normalize(n) for n in names]

        self._names = names
        self._codes = codes
        self._norm_names = norm_names

        # O(1) lookup dicts — first occurrence wins on normalized collision
        self._exact_map = {n: i for i, n in enumerate(names)}
        for i, n in enumerate(norm_names):
            if n not in self._norm_map:
                self._norm_map[n] = i
        self._empty = False

    @staticmethod
    def _find_col(columns: list[str], keywords: list[str]) -> Optional[str]:
        """Return first column whose name contains ALL keywords (case-insensitive)."""
        for col in columns:
            col_lower = col.lower()
            if all(kw in col_lower for kw in keywords):
                return col
        return None

    @staticmethod
    def _load_master(
        df: pd.DataFrame,
        name_col: str,
        code_col: Optional[str],
    ) -> tuple[list[str], list[Optional[str]]]:
        """
        Extract deduplicated brand names and codes from the master DataFrame.
        Uses vectorized pandas — no iterrows.
        """
        sub = df[[name_col]].copy() if code_col is None else df[[name_col, code_col]].copy()
        sub[name_col] = sub[name_col].str.strip()
        sub = sub[sub[name_col] != ""].drop_duplicates(subset=[name_col])

        names: list[str] = sub[name_col].tolist()
        codes: list[Optional[str]] = (
            [coerce_code(v) for v in sub[code_col]] if code_col else [None] * len(names)
        )
        return names, codes

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def resolve(self, raw: Optional[str]) -> BrandMatch:
        """
        Resolve a raw brand string to a canonical brand.
        Returns BrandMatch(name=None, needs_review=False) for placeholders/empty —
        missing brand is expected data, not an error.
        """
        if not raw or _is_placeholder(raw):
            return BrandMatch(None, None, 0.0, "unresolved", False)

        raw = raw.strip()
        if self._empty:
            return BrandMatch(raw, None, 0.35, "pass-through", True)
        return (
            self._exact(raw)
            or self._normalized(raw)
            or self._fuzzy(raw)
            or BrandMatch(None, None, 0.0, "unresolved", True)
        )

    def resolve_best(self, *candidates: Optional[str]) -> BrandMatch:
        """
        Try multiple raw brand candidates in priority order; return the first
        successful resolution. Designed for unilog_brand → e1_brand → dib_brand.
        """
        for candidate in candidates:
            result = self.resolve(candidate)
            if result.brand_name is not None:
                return result
        return BrandMatch(None, None, 0.0, "unresolved", False)

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _exact(self, raw: str) -> Optional[BrandMatch]:
        i = self._exact_map.get(raw)
        if i is None:
            return None
        return BrandMatch(self._names[i], self._codes[i], 1.0, "exact", False)

    def _normalized(self, raw: str) -> Optional[BrandMatch]:
        i = self._norm_map.get(normalize(raw))
        if i is None:
            return None
        return BrandMatch(self._names[i], self._codes[i], 0.97, "normalized", False)

    def _fuzzy(self, raw: str) -> Optional[BrandMatch]:
        norm_raw = normalize(raw)
        best_score, best_idx = 0.0, -1

        for i, norm in enumerate(self._norm_names):
            score = similarity(norm_raw, norm)
            if score > best_score:
                best_score, best_idx = score, i

        if best_idx == -1 or best_score < self.REVIEW_THRESHOLD:
            return None

        needs_review = best_score < self.FUZZY_THRESHOLD
        return BrandMatch(
            self._names[best_idx],
            self._codes[best_idx],
            round(best_score, 4),
            "fuzzy",
            needs_review,
        )
