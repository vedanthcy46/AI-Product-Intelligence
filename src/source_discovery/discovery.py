"""
T6 — Manufacturer Source Discovery

Goal: Find authoritative manufacturer URLs for a product.

Pipeline:
    ProductInput + ClassificationResult
        ↓
    Query Generation  (deterministic, no LLM)
        ↓
    LLM-Assisted URL Discovery  (Groq — asks for likely manufacturer URLs)
        ↓
    SourceResult list  { url, manufacturer, mpn, document_type, confidence }

Design decisions:
  - Query generation is fully deterministic — no LLM needed.
  - URL discovery uses the LLM as a "knowledgeable assistant" to suggest
    likely manufacturer page patterns.  It does NOT scrape the web.
  - Marketplace / distributor URLs (amazon, grainger, mcmaster, etc.) are
    filtered out per the challenge sourcing rules.
  - Every SourceResult carries metadata so downstream RAG can cite provenance.
  - Graceful degradation: if Groq is unavailable, returns empty list (not a crash).
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from src.preprocessing.models import ProductInput
from src.classification.classifier import ClassificationResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Blocked domains — marketplace / distributor sources to exclude
# ---------------------------------------------------------------------------
_BLOCKED_DOMAINS = {
    "amazon", "ebay", "walmart", "grainger", "mcmaster", "fastenal",
    "homedepot", "lowes", "menards", "zoro", "globalindustrial",
    "uline", "mscdirect", "hdpe", "plumbersstock", "supplyhouse",
    "ferguson", "build", "acehardware", "truevalue",
}


def _is_blocked(url: str) -> bool:
    url_lower = url.lower()
    return any(domain in url_lower for domain in _BLOCKED_DOMAINS)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

@dataclass
class SourceResult:
    url: str
    manufacturer: Optional[str]
    mpn: Optional[str]
    document_type: str   # product_page | specification_sheet | installation_manual | catalogue | technical_doc
    confidence: float
    query_used: Optional[str] = field(default=None)

    def to_dict(self) -> dict:
        return {
            "source_url": self.url,
            "manufacturer": self.manufacturer,
            "mpn": self.mpn,
            "document_type": self.document_type,
            "confidence": self.confidence,
            "query_used": self.query_used,
        }


# ---------------------------------------------------------------------------
# Query generation  (deterministic)
# ---------------------------------------------------------------------------

def generate_queries(product: ProductInput, classification: Optional[ClassificationResult] = None) -> list[str]:
    """
    Generate a set of retrieval queries for a product.

    Returns a deduplicated list of query strings ordered by specificity.
    No LLM is used here — this is fully deterministic.
    """
    mpn = (product.mfg_part_num or "").strip()
    mfr = (product.best_manufacturer or "").strip()
    desc = (product.part_desc or "").strip()
    fine = classification.fine if classification and classification.fine else ""

    queries: list[str] = []

    if mpn and mfr:
        queries += [
            f"{mfr} {mpn} specifications",
            f"{mfr} {mpn} datasheet",
            f"{mfr} {mpn} installation manual",
            f"{mfr} {mpn} technical data",
        ]
    if mpn:
        queries += [
            f"{mpn} specifications",
            f"{mpn} datasheet",
        ]
    if mpn and fine:
        queries.append(f"{mpn} {fine}")
    if mfr and fine:
        queries.append(f"{mfr} {fine} specifications")
    if desc:
        queries.append(desc)

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for q in queries:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            result.append(q)

    return result


# ---------------------------------------------------------------------------
# Source Discovery
# ---------------------------------------------------------------------------

class ManufacturerSourceDiscovery:
    """
    T6 — Discover authoritative manufacturer source URLs for a product.

    Uses Groq LLM to suggest likely manufacturer page URLs based on the
    product's MPN, manufacturer name, and product type.  The LLM is asked
    to reason about where a manufacturer would publish product information,
    not to hallucinate arbitrary URLs.

    Falls back gracefully to an empty list if Groq is unavailable.
    """

    def discover(
        self,
        product: ProductInput,
        classification: Optional[ClassificationResult] = None,
    ) -> list[SourceResult]:
        """
        Main entry point.

        Returns a list of SourceResult objects, filtered to remove
        marketplace/distributor URLs.  May be empty if no sources found.
        """
        queries = generate_queries(product, classification)
        if not queries:
            return []

        raw_sources = self._llm_discover(product, queries)
        return [s for s in raw_sources if not _is_blocked(s.url)]

    # ------------------------------------------------------------------
    # LLM discovery
    # ------------------------------------------------------------------

    def _llm_discover(
        self,
        product: ProductInput,
        queries: list[str],
    ) -> list[SourceResult]:
        try:
            import groq
        except ImportError:
            return []

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return []

        mpn = product.mfg_part_num or "N/A"
        mfr = product.best_manufacturer or "Unknown"
        desc = product.part_desc or "N/A"
        top_queries = "\n".join(f"- {q}" for q in queries[:5])

        prompt = (
            f"You are a product data researcher.\n"
            f"Manufacturer: {mfr}\n"
            f"Part Number: {mpn}\n"
            f"Description: {desc}\n\n"
            f"Search queries:\n{top_queries}\n\n"
            f"List up to 5 likely OFFICIAL manufacturer URLs where product specifications, "
            f"datasheets, or installation manuals for this part would be found.\n"
            f"Only include manufacturer-owned domains (not Amazon, Grainger, eBay, etc.).\n"
            f"For each URL, also state the document type on the same line.\n"
            f"Format each line exactly as:\n"
            f"URL | document_type\n"
            f"Where document_type is one of: product_page, specification_sheet, installation_manual, catalogue, technical_doc\n"
            f"If you cannot determine real URLs, reply: NONE"
        )

        try:
            client = groq.Groq(api_key=api_key)
            response = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("LLM source discovery failed: %s", e)
            return []

        if raw.upper() == "NONE" or not raw:
            return []

        return self._parse_llm_response(raw, product)

    # ------------------------------------------------------------------
    # Parse LLM response
    # ------------------------------------------------------------------

    _VALID_DOC_TYPES = {
        "product_page", "specification_sheet", "installation_manual",
        "catalogue", "technical_doc",
    }

    def _parse_llm_response(self, raw: str, product: ProductInput) -> list[SourceResult]:
        results: list[SourceResult] = []

        for line in raw.splitlines():
            line = line.strip()
            if not line or line.upper() == "NONE":
                continue

            # Strip leading list markers (-, *, 1., etc.)
            line = re.sub(r"^[-*•\d.]+\s*", "", line).strip()

            if "|" in line:
                parts = line.split("|", 1)
                url = parts[0].strip()
                doc_type = parts[1].strip().lower().replace(" ", "_")
            else:
                # No pipe separator — treat whole line as URL
                url = line.strip()
                doc_type = "product_page"

            # Basic URL validation
            if not url.startswith("http"):
                continue

            if doc_type not in self._VALID_DOC_TYPES:
                doc_type = "product_page"

            results.append(SourceResult(
                url=url,
                manufacturer=product.best_manufacturer,
                mpn=product.mfg_part_num,
                document_type=doc_type,
                confidence=0.70,
                query_used=None,
            ))

        return results
