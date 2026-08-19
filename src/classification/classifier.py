"""
T5 — Classification

Pipeline:
    ProductUnderstanding
        ↓
    Keyword Match (deterministic, O(n))
        ↓
    Normalized Fuzzy Match (difflib, O(n))
        ↓
    LLM Ranking (Groq, only when deterministic steps are ambiguous)
        ↓
    ClassificationResult  { dept, class_name, fine, classpath, confidence, method }

The LLM is NEVER allowed to invent taxonomy values outside the controlled
vocabulary in taxonomy.py.  It only picks from the top-K candidates already
identified by the deterministic steps.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

from src.preprocessing.understanding_model import ProductUnderstanding
from src.classification.taxonomy import TAXONOMY, VALID_CLASSPATHS

logger = logging.getLogger(__name__)

# Minimum fuzzy score to include a candidate in LLM ranking
_FUZZY_MIN = 0.30
# Score above which we accept without LLM
_ACCEPT_THRESHOLD = 0.60
# Top-K candidates passed to LLM
_TOP_K = 5


@dataclass
class ClassificationResult:
    dept: Optional[str]
    class_name: Optional[str]
    fine: Optional[str]
    classpath: Optional[str]
    confidence: float
    method: str          # keyword | fuzzy | llm | unresolved
    needs_review: bool

    def __repr__(self) -> str:
        return (
            f"ClassificationResult({self.classpath!r}, "
            f"conf={self.confidence:.2f}, method={self.method})"
        )


class ProductClassifier:

    def classify(self, understanding: ProductUnderstanding) -> ClassificationResult:
        """
        Main entry point.  Returns a ClassificationResult from a ProductUnderstanding.
        """
        text = self._build_search_text(understanding)

        result = (
            self._keyword_match(text)
            or self._fuzzy_match(text)
        )

        if result is not None and result.confidence >= _ACCEPT_THRESHOLD:
            return result

        # Ambiguous — escalate to LLM with top-K candidates
        candidates = self._top_k_fuzzy(text, k=_TOP_K)
        llm_result = self._llm_rank(text, candidates)
        if llm_result is not None:
            return llm_result

        # Return best fuzzy result even if below threshold, flagged for review
        if result is not None:
            return ClassificationResult(
                dept=result.dept,
                class_name=result.class_name,
                fine=result.fine,
                classpath=result.classpath,
                confidence=result.confidence,
                method=result.method,
                needs_review=True,
            )

        return ClassificationResult(
            dept=None, class_name=None, fine=None, classpath=None,
            confidence=0.0, method="unresolved", needs_review=True,
        )

    # ------------------------------------------------------------------
    # Build search text from ProductUnderstanding
    # ------------------------------------------------------------------

    @staticmethod
    def _build_search_text(u: ProductUnderstanding) -> str:
        parts = [
            u.product_type or "",
            u.source_desc or "",
            u.application or "",
            u.industry or "",
            u.material or "",
            " ".join(u.extra_attributes.values()) if u.extra_attributes else "",
        ]
        return " ".join(p for p in parts if p).lower()

    # ------------------------------------------------------------------
    # Step 1 — Keyword match (deterministic)
    # ------------------------------------------------------------------

    @staticmethod
    def _keyword_match(text: str) -> Optional[ClassificationResult]:
        best_entry = None
        best_hits = 0

        for entry in TAXONOMY:
            hits = sum(1 for kw in entry["keywords"] if kw in text)
            if hits > best_hits:
                best_hits = hits
                best_entry = entry

        if best_entry is None or best_hits == 0:
            return None

        # Confidence scales with keyword hit density
        confidence = min(0.95, 0.50 + best_hits * 0.15)
        return ClassificationResult(
            dept=best_entry["dept"],
            class_name=best_entry["class_name"],
            fine=best_entry["fine"],
            classpath=best_entry["classpath"],
            confidence=round(confidence, 4),
            method="keyword",
            needs_review=confidence < _ACCEPT_THRESHOLD,
        )

    # ------------------------------------------------------------------
    # Step 2 — Fuzzy match (difflib)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_entry(text: str, entry: dict) -> float:
        """Compute similarity between search text and a taxonomy entry."""
        target = " ".join([
            entry["fine"].lower(),
            entry["class_name"].lower(),
            entry["dept"].lower(),
            " ".join(entry["keywords"]),
        ])
        return SequenceMatcher(None, text, target).ratio()

    @classmethod
    def _fuzzy_match(cls, text: str) -> Optional[ClassificationResult]:
        best_score, best_entry = 0.0, None
        for entry in TAXONOMY:
            score = cls._score_entry(text, entry)
            if score > best_score:
                best_score, best_entry = score, entry

        if best_entry is None or best_score < _FUZZY_MIN:
            return None

        return ClassificationResult(
            dept=best_entry["dept"],
            class_name=best_entry["class_name"],
            fine=best_entry["fine"],
            classpath=best_entry["classpath"],
            confidence=round(best_score, 4),
            method="fuzzy",
            needs_review=best_score < _ACCEPT_THRESHOLD,
        )

    @classmethod
    def _top_k_fuzzy(cls, text: str, k: int) -> list[dict]:
        scored = sorted(
            TAXONOMY,
            key=lambda e: cls._score_entry(text, e),
            reverse=True,
        )
        return scored[:k]

    # ------------------------------------------------------------------
    # Step 3 — LLM ranking (Groq, constrained to top-K candidates)
    # ------------------------------------------------------------------

    @staticmethod
    def _llm_rank(text: str, candidates: list[dict]) -> Optional[ClassificationResult]:
        try:
            import groq
        except ImportError:
            return None

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None

        candidate_lines = "\n".join(
            f"{i+1}. {c['classpath']}" for i, c in enumerate(candidates)
        )
        prompt = (
            f"You are a product taxonomy expert.\n"
            f"Product description: \"{text}\"\n\n"
            f"Choose the single best matching category from this list.\n"
            f"Reply with ONLY the exact classpath string (e.g. Plumbing>Pipe Fittings>Couplings).\n"
            f"If none fit, reply exactly: NONE\n\n"
            f"{candidate_lines}"
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
        except Exception as e:
            logger.error("LLM classification failed: %s", e)
            return None

        if answer.upper() == "NONE":
            return None

        # Validate the LLM answer is in the controlled vocabulary
        if answer not in VALID_CLASSPATHS:
            # Try to find a close match among candidates
            for c in candidates:
                if c["classpath"].lower() == answer.lower():
                    answer = c["classpath"]
                    break
            else:
                logger.warning("LLM returned classpath not in taxonomy: %r", answer)
                return None

        parts = answer.split(">")
        return ClassificationResult(
            dept=parts[0] if len(parts) > 0 else None,
            class_name=parts[1] if len(parts) > 1 else None,
            fine=parts[2] if len(parts) > 2 else None,
            classpath=answer,
            confidence=0.82,
            method="llm",
            needs_review=False,
        )
