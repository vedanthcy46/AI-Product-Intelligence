"""
T4 — Product Understanding: extractor

Turns a raw ProductInput into a ProductUnderstanding by:
  1. Expanding known industrial abbreviations in the description (deterministic)
  2. Calling an LLM to extract structured candidate facts as JSON
  3. Mapping the LLM response onto ProductUnderstanding fields
  4. Falling back gracefully if the LLM is unavailable
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from src.preprocessing.models import ProductInput
from src.preprocessing.understanding_model import ProductUnderstanding
from src.llm_config import call_with_retry, completion_kwargs, get_chat_model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abbreviation expansion
#
# Rules for safe patterns:
#   - Only expand tokens that are ≥ 3 characters OR are unambiguous in context
#   - Never expand single/two-letter tokens (M, F, AL, PP, CS, etc.) —
#     they appear constantly in MPNs and part numbers
#   - Pressure patterns like "150#" are safe because the # anchor is unique
# ---------------------------------------------------------------------------

_ABBREV: dict[str, str] = {
    # Product types (3+ chars, low collision risk)
    r"\bCPLG\b": "Coupling",
    r"\bELB\b": "Elbow",
    r"\bELL\b": "Elbow",
    r"\bRED\b": "Reducer",
    r"\bNIP\b": "Nipple",
    r"\bBUSH\b": "Bushing",
    r"\bFLG\b": "Flange",
    r"\bVLV\b": "Valve",
    r"\bCHK\b": "Check Valve",
    r"\bNDL\b": "Needle",
    r"\bGLB\b": "Globe",
    r"\bFTG\b": "Fitting",
    r"\bADPT\b": "Adapter",
    r"\bSWAG\b": "Swage",
    # Materials (3+ chars)
    r"\bBRS\b": "Brass",
    r"\bBRZ\b": "Bronze",
    r"\bSST\b": "Stainless Steel",
    r"\bCPVC\b": "CPVC",
    r"\bALUM\b": "Aluminum",
    r"\bNYL\b": "Nylon",
    r"\bTEFLON\b": "PTFE",
    # Thread / connection (unambiguous)
    r"\bMNPT\b": "Male NPT",
    r"\bFNPT\b": "Female NPT",
    r"\bMIP\b": "Male Iron Pipe",
    r"\bFIP\b": "Female Iron Pipe",
    r"\bCOMP\b": "Compression",
    # Pressure — # is not a word char so \b doesn't work; use digit boundary
    r"(?<![\d])150#": "150 lb",
    r"(?<![\d])300#": "300 lb",
    r"(?<![\d])600#": "600 lb",
    r"(?<![\d])3000#": "3000 lb",
    r"(?<![\d])6000#": "6000 lb",
    # Schedule — safe because SCH prefix is unambiguous
    r"\bSCH\s*40\b": "Schedule 40",
    r"\bSCH\s*80\b": "Schedule 80",
    r"\bSCH\s*160\b": "Schedule 160",
    # Misc (3+ chars, low collision)
    r"\bHEX\b": "Hex",
    r"\bSTD\b": "Standard",
    r"\bXHVY\b": "Extra Heavy",
}

_ABBREV_PATTERNS = [
    (re.compile(pat, re.IGNORECASE), repl) for pat, repl in _ABBREV.items()
]


def expand_abbreviations(text: str) -> str:
    """
    Deterministically expand known industrial abbreviations in a description.
    Safe to call on Part_Desc. Do NOT call on raw MPNs — it will corrupt them.
    """
    for pattern, replacement in _ABBREV_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an industrial product data expert. Given a product description and \
part number, extract structured facts as JSON.

Return ONLY a JSON object with these keys (omit keys you cannot determine):
{
  "product_type": "...",
  "series": "...",
  "model_number": "...",
  "size": "...",
  "material": "...",
  "finish": "...",
  "color": "...",
  "shape": "...",
  "pressure_rating": "...",
  "temperature_rating": "...",
  "voltage": "...",
  "amperage": "...",
  "wattage": "...",
  "thread_type": "...",
  "connection_type": "...",
  "end_type": "...",
  "gender": "...",
  "application": "...",
  "industry": "...",
  "extra_attributes": {"key": "value"}
}

Rules:
- Values are candidate facts only — do not normalize units.
- Do not invent values. If unsure, omit the key.
- extra_attributes captures any real fact that doesn't fit the schema above.
- Return raw JSON only — no markdown fences, no explanation.
"""

_KNOWN_FIELDS = {
    "product_type", "series", "model_number", "size", "material", "finish",
    "color", "shape", "pressure_rating", "temperature_rating", "voltage",
    "amperage", "wattage", "thread_type", "connection_type", "end_type",
    "gender", "application", "industry",
}


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class ProductUnderstandingExtractor:

    def __init__(self, model: str = ""):
        self._model = model or get_chat_model()
        self._unavailable_logged = False

    def extract(self, product: ProductInput) -> ProductUnderstanding:
        """
        Main entry point. Returns a ProductUnderstanding from a ProductInput.

        The MPN is passed to the LLM raw — never abbreviation-expanded —
        because expanding it would corrupt the part number string.
        """
        expanded_desc = expand_abbreviations(product.part_desc or "")

        llm_facts = self._call_llm(
            expanded_desc=expanded_desc,
            raw_mpn=product.mfg_part_num,
        )

        if llm_facts is None:
            if not self._unavailable_logged:
                logger.warning(
                    "LLM unavailable — returning minimal understanding for all rows "
                    "(set GROQ_API_KEY to enable enrichment). First affected row: %s",
                    product.row_id,
                )
                self._unavailable_logged = True
            return ProductUnderstanding(
                source_desc=product.part_desc,
                row_id=product.row_id,
            )

        return self._map_to_understanding(llm_facts, product)

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    def _call_llm(
        self,
        expanded_desc: str,
        raw_mpn: Optional[str],
    ) -> Optional[dict]:
        try:
            import groq
        except ImportError:
            return None

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None

        user_content = (
            f"Part Number: {raw_mpn or 'N/A'}\n"
            f"Description: {expanded_desc or 'N/A'}"
        )

        try:
            client = groq.Groq(api_key=api_key)
            response = call_with_retry(
                lambda: client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0,
                    **completion_kwargs(self._model, 512),
                ),
                what="understanding",
            )
            raw = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("LLM call failed for understanding extraction: %s", e)
            return None

        return self._parse_json(raw)

    # ------------------------------------------------------------------
    # JSON parsing — robust against markdown fences and whitespace
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(raw: str) -> Optional[dict]:
        # Strip opening fence: ```json or ``` with optional trailing spaces
        raw = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
        # Strip closing fence
        raw = re.sub(r"\n?```\s*$", "", raw.strip()).strip()

        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM JSON: %.200s", raw)
            return None

    # ------------------------------------------------------------------
    # Map LLM dict → ProductUnderstanding
    # ------------------------------------------------------------------

    @staticmethod
    def _map_to_understanding(facts: dict, product: ProductInput) -> ProductUnderstanding:
        def get(key: str) -> Optional[str]:
            v = facts.get(key)
            if v is None:
                return None
            s = str(v).strip()
            return s if s else None

        # Collect extra_attributes: explicit dict from LLM + any unknown top-level keys
        extra: dict[str, str] = {}
        llm_extra = facts.get("extra_attributes")
        if isinstance(llm_extra, dict):
            extra.update({k: str(v) for k, v in llm_extra.items() if v})

        for k, v in facts.items():
            if k not in _KNOWN_FIELDS and k != "extra_attributes" and v:
                extra[k] = str(v)

        return ProductUnderstanding(
            product_type=get("product_type"),
            series=get("series"),
            model_number=get("model_number"),
            size=get("size"),
            material=get("material"),
            finish=get("finish"),
            color=get("color"),
            shape=get("shape"),
            pressure_rating=get("pressure_rating"),
            temperature_rating=get("temperature_rating"),
            voltage=get("voltage"),
            amperage=get("amperage"),
            wattage=get("wattage"),
            thread_type=get("thread_type"),
            connection_type=get("connection_type"),
            end_type=get("end_type"),
            gender=get("gender"),
            application=get("application"),
            industry=get("industry"),
            extra_attributes=extra,
            row_id=product.row_id,
            source_desc=product.part_desc,
        )
