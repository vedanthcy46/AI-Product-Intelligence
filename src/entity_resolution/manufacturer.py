"""
T2 — Manufacturer Resolution
Pipeline: exact → normalized → fuzzy → LLM disambiguation
Reference: UniCat_Manufacturer_and_Brand_List.xlsx
"""

from __future__ import annotations

import re
import os
from dataclasses import dataclass
from typing import Optional
import pandas as pd
from difflib import SequenceMatcher


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
# Helpers
# ---------------------------------------------------------------------------

def _normalize(s: str) -> str:
    """Lowercase, collapse punctuation/extra spaces for comparison."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _coerce_code(value: str) -> Optional[str]:
    """Return None for blank/missing codes instead of empty string."""
    v = value.strip()
    return v if v else None


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

class ManufacturerResolver:
    FUZZY_THRESHOLD = 0.82   # below this → accepted but flagged for review
    REVIEW_THRESHOLD = 0.70  # below this → not accepted at all, go to LLM

    def __init__(self, master_path: str):
        """
        Load the manufacturer/brand master list.
        Expects columns: Manufacturer_Name, Manufacturer_Code (at minimum).
        """
        df = pd.read_excel(master_path, dtype=str).fillna("")
        df.columns = [c.strip() for c in df.columns]

        name_col = next(
            (c for c in df.columns if "manufacturer" in c.lower() and "name" in c.lower()),
            df.columns[0],
        )
        code_col = next(
            (c for c in df.columns if "code" in c.lower()),
            None,
        )

        names: list[str] = df[name_col].tolist()
        codes: list[Optional[str]] = (
            [_coerce_code(v) for v in df[code_col]] if code_col else [None] * len(names)
        )
        norm_names: list[str] = [_normalize(n) for n in names]

        # O(1) lookup dicts for exact and normalized matching
        self._exact_map: dict[str, int] = {n: i for i, n in enumerate(names)}
        self._norm_map: dict[str, int] = {}
        for i, n in enumerate(norm_names):
            if n not in self._norm_map:   # first occurrence wins on collision
                self._norm_map[n] = i

        # Keep lists for fuzzy scan
        self._names = names
        self._codes = codes
        self._norm_names = norm_names

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def resolve(self, raw: Optional[str]) -> ManufacturerMatch:
        if not raw or not raw.strip():
            return ManufacturerMatch(None, None, 0.0, "unresolved", True)

        raw = raw.strip()

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
        i = self._norm_map.get(_normalize(raw))
        if i is None:
            return None
        return ManufacturerMatch(self._names[i], self._codes[i], 0.97, "normalized", False)

    # ------------------------------------------------------------------
    # Step 3 — Fuzzy  O(n) — returns top match with score
    # ------------------------------------------------------------------

    def _fuzzy(self, raw: str) -> Optional[ManufacturerMatch]:
        norm_raw = _normalize(raw)
        best_score, best_idx = 0.0, -1

        for i, norm in enumerate(self._norm_names):
            score = _similarity(norm_raw, norm)
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

        # Reuse fuzzy scores to build candidate list — no duplicate scan
        norm_raw = _normalize(raw)
        top5 = sorted(
            range(len(self._norm_names)),
            key=lambda i: _similarity(norm_raw, self._norm_names[i]),
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
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60,
                temperature=0,
            )
            answer = response.choices[0].message.content.strip()
        except Exception:
            return None

        if answer.upper() == "NONE":
            return None

        # Strip any leading bullet the model may echo back ("- Name" → "Name")
        answer = re.sub(r"^[-•*]\s*", "", answer).strip()

        norm_answer = _normalize(answer)
        i = self._norm_map.get(norm_answer)
        if i is not None:
            return ManufacturerMatch(self._names[i], self._codes[i], 0.80, "llm", False)

        return None
