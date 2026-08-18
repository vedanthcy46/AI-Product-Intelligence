"""
Shared helpers for entity resolution (T2, T3).
Single source of truth — imported by both manufacturer.py and brand.py.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Optional


def normalize(s: str) -> str:
    """Lowercase, collapse punctuation and extra spaces for comparison."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def coerce_code(value: str) -> Optional[str]:
    """Return None for blank/missing codes instead of empty string."""
    v = value.strip()
    return v if v else None
