"""
T2 — Manufacturer Resolution
Pipeline: exact → normalized → fuzzy → LLM disambiguation
Reference: UniCat_Manufacturer_and_Brand_List.xlsx
"""

from __future__ import annotations

import re
import os
import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from src.entity_resolution._utils import normalize, similarity, coerce_code
from src.llm_config import call_with_retry, completion_kwargs, get_chat_model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class ManufacturerMatch:
    manufacturer_name: Optional[str]
    manufacturer_code: Optional[str]
    confidence: float
    method: str          # exact | normalized | fuzzy | llm | unresolved
    needs_review: bool

    def __repr__(self) -> str:
        review = " ⚠ needs_review" if self.needs_review else ""
        return (
            f"ManufacturerMatch({self.manufacturer_name!r}, "
            f"code={self.manufacturer_code!r}, "
            f"conf={self.confidence:.2f}, method={self.method}{review})"
        )


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

class ManufacturerResolver:
    FUZZY_THRESHOLD = 0.82   # below this → accepted but flagged for review
    REVIEW_THRESHOLD = 0.70  # below this → not accepted, escalate to LLM

    def __init__(self, master_path: str):
        """
        Load the manufacturer/brand master list.
        Expects columns: Manufacturer_Name, Manufacturer_Code (at minimum).

        If the master file is missing/unreadable the resolver degrades
        gracefully: every raw value passes through as-is with low confidence,
        flagged for review (so downstream stages still run).
        """
        self._empty = True
        self._exact_map: dict[str, int] = {}
        self._norm_map: dict[str, int] = {}
        self._names: list[str] = []
        self._codes: list[Optional[str]] = []
        self._norm_names: list[str] = []

        if not master_path or not os.path.exists(master_path):
            logger.warning("Manufacturer master not found (%s); pass-through mode (low confidence).", master_path)
            return

        df = pd.read_excel(master_path, dtype=str).fillna("")
        df.columns = [c.strip() for c in df.columns]

        name_col = self._find_col(df.columns, ["manufacturer", "name"], df.columns[0])
        code_col = self._find_col(df.columns, ["code"], None)

        names: list[str] = df[name_col].tolist()
        codes: list[Optional[str]] = (
            [coerce_code(v) for v in df[code_col]] if code_col else [None] * len(names)
        )
        norm_names: list[str] = [normalize(n) for n in names]

        # O(1) lookup dicts — first occurrence wins on normalized collision
        self._exact_map = {n: i for i, n in enumerate(names)}
        for i, n in enumerate(norm_names):
            if n not in self._norm_map:
                self._norm_map[n] = i

        self._names = names
        self._codes = codes
        self._norm_names = norm_names
        self._empty = False

    @staticmethod
    def _find_col(columns: list[str], keywords: list[str], default) -> Optional[str]:
        """Return the first column whose name contains ALL keywords (case-insensitive)."""
        for col in columns:
            col_lower = col.lower()
            if all(kw in col_lower for kw in keywords):
                return col
        return default

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def resolve(self, raw: Optional[str]) -> ManufacturerMatch:
        if not raw or not raw.strip():
            return ManufacturerMatch(None, None, 0.0, "unresolved", True)

        raw = raw.strip()
        if self._empty:
            return ManufacturerMatch(raw, None, 0.35, "pass-through", True)
        return (
            self._exact(raw)
            or self._normalized(raw)
            or self._fuzzy(raw)
            or self._llm(raw)
            or ManufacturerMatch(None, None, 0.0, "unresolved", True)
        )

    # ------------------------------------------------------------------
    # Step 1 — Exact  O(1)
    # ------------------------------------------------------------------

    def _exact(self, raw: str) -> Optional[ManufacturerMatch]:
        i = self._exact_map.get(raw)
        if i is None:
            return None
        return ManufacturerMatch(self._names[i], self._codes[i], 1.0, "exact", False)

    # ------------------------------------------------------------------
    # Step 2 — Normalized  O(1)
    # ------------------------------------------------------------------

    def _normalized(self, raw: str) -> Optional[ManufacturerMatch]:
        i = self._norm_map.get(normalize(raw))
        if i is None:
            return None
        return ManufacturerMatch(self._names[i], self._codes[i], 0.97, "normalized", False)

    # ------------------------------------------------------------------
    # Step 3 — Fuzzy  O(n)
    # ------------------------------------------------------------------

    def _fuzzy(self, raw: str) -> Optional[ManufacturerMatch]:
        norm_raw = normalize(raw)
        best_score, best_idx = 0.0, -1

        for i, norm in enumerate(self._norm_names):
            score = similarity(norm_raw, norm)
            if score > best_score:
                best_score, best_idx = score, i

        if best_idx == -1 or best_score < self.REVIEW_THRESHOLD:
            return None

        needs_review = best_score < self.FUZZY_THRESHOLD
        return ManufacturerMatch(
            self._names[best_idx],
            self._codes[best_idx],
            round(best_score, 4),
            "fuzzy",
            needs_review,
        )

    # ------------------------------------------------------------------
    # Step 4 — LLM  (only when all deterministic steps fail)
    # ------------------------------------------------------------------

    def _llm(self, raw: str) -> Optional[ManufacturerMatch]:
        """
        Ask Llama3 via Groq to pick the best canonical manufacturer from the
        top-5 fuzzy candidates. Skips gracefully if groq is not installed
        or GROQ_API_KEY is not set.
        """
        try:
            import groq
        except ImportError:
            return None

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None

        norm_raw = normalize(raw)
        top5 = sorted(
            range(len(self._norm_names)),
            key=lambda i: similarity(norm_raw, self._norm_names[i]),
            reverse=True,
        )[:5]
        candidates = [self._names[i] for i in top5]

        prompt = (
            f"You are a product data expert.\n"
            f"Raw manufacturer string: '{raw}'\n"
            f"Choose the single best match from the list below, "
            f"or reply exactly NONE if nothing fits.\n"
            f"Reply with only the name, no extra text.\n"
            + "\n".join(f"- {c}" for c in candidates)
        )

        try:
            client = groq.Groq(api_key=api_key)
            response = call_with_retry(
                lambda: client.chat.completions.create(
                    model=get_chat_model(),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    **completion_kwargs(get_chat_model(), 60),
                ),
                what="manufacturer resolution",
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("LLM manufacturer resolution failed: %s", e)
            return None

        if answer.upper() == "NONE":
            return None

        answer = re.sub(r"^[-•*]\s*", "", answer).strip()
        i = self._norm_map.get(normalize(answer))
        if i is not None:
            return ManufacturerMatch(self._names[i], self._codes[i], 0.80, "llm", False)

        return None
