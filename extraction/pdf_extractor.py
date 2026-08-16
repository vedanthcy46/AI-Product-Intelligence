"""Phase 1 — PDF extraction (Vedanth).

extract_pdf(path) -> Product with confidence + source_page provenance.

Pipeline per README §5 Phase 1 (adapted to the Groq backend):
  PyMuPDF -> text layer extracted per page -> Groq LLM (via Instructor)
  -> structured fields with confidence, merged into one Product.

The README's vision-model variant (150 DPI PNG -> multimodal model) is
swappable: render_pages() is kept ready for when a vision-capable model
is available on the key — flip EXTRACT_VISION = True.

LLM backend: Groq's OpenAI-compatible endpoint. Instructor runs in JSON
mode by default (override with GROQ_INSTRUCTOR_MODE).

Design rules enforced here:
  * Process page-by-page, never the whole doc at once (context-bloat risk).
  * The prompt demands: "Return null if absent. Include confidence
    (high/medium/low) and source page per field."
  * Missing field -> null, never a guess (see hallucination test).
  * Bounding boxes are deferred to Phase 6 (stretch) — not attempted here.

Usage:
    python -m extraction.pdf_extractor path/to/catalog.pdf   # single file
    python -m extraction.pdf_extractor data/samples/          # batch → JSONL
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Literal

import pymupdf as fitz  # PyMuPDF
import instructor
from openai import OpenAI, RateLimitError
from pydantic import BaseModel, Field

# Allow running as a script from the repo root without installation.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schema import PRODUCT_FIELDS, Confidence, Product  # noqa: E402

DPI = 150
# Flip to True once a vision-capable model is available on the Groq key.
EXTRACT_VISION = os.environ.get("EXTRACT_VISION", "false").lower() in ("1", "true", "yes")
GROQ_BASE_URL = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
INSTRUCTOR_MODE = os.environ.get("GROQ_INSTRUCTOR_MODE", "JSON")
MAX_RETRIES = 3

# Groq free tier is ~12k TPM; a 24-page catalog burns that fast.
RATE_LIMIT_RETRIES = int(os.environ.get("GROQ_RATE_RETRIES", "6"))
PAGE_DELAY = float(os.environ.get("GROQ_PAGE_DELAY", "2.0"))  # seconds between page calls
# Per-page cache: re-runs (debugging, tests) never resend an extracted page.
CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "extraction"

SYSTEM_PROMPT = """\
You are an industrial product-data extraction engine. You receive the text
of one page at a time from an industrial catalog or spec sheet PDF.

Extract the product specification fields visible on THIS page:
product_name, size, material, pressure_rating, thread_type, temperature_range.

Rules:
1. Return null if absent. Never guess, infer, or fill in a value that is not
   visibly stated on the page.
2. Include confidence (high/medium/low) and source page per field.
   - high: value clearly printed and unambiguous
   - medium: value present but partially obscured, abbreviated, or needs
     light interpretation
   - low: value uncertain, inferred from context, or poorly printed
3. Copy values exactly as printed (units included), e.g. "2 inch", "200 WOG".
4. product_name means the full product title/heading, including descriptive
   words AND model/series identifiers, e.g. "FORGED BALL VALVE - SERIES
   FBV-200" — do not drop either part.
5. If the page contains no product specifications at all (cover page, table
   of contents, marketing fluff), return all fields as null.
6. Respond with a single JSON object and nothing else — no markdown fences,
   no commentary.
"""


class PageExtraction(BaseModel):
    """Structured output schema handed to Instructor (one page at a time)."""

    product_name: str | None = Field(None, description="Product/model name as printed, or null if absent")
    size: str | None = Field(None, description='e.g. "2 inch", "DN50"; null if absent')
    material: str | None = Field(None, description='e.g. "Carbon Steel", "316SS"; null if absent')
    pressure_rating: str | None = Field(None, description='e.g. "200 WOG", "PN16"; null if absent')
    thread_type: str | None = Field(None, description='e.g. "NPT", "BSPP", "Metric"; null if absent')
    temperature_range: str | None = Field(None, description='e.g. "-20°C to 200°C"; null if absent')
    confidence: dict[str, Literal["high", "medium", "low"]] = Field(
        default_factory=dict,
        description="Confidence per non-null field only",
    )


def _load_env() -> None:
    """Load .env from the repo root if python-dotenv is available."""
    try:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    except ImportError:
        pass


def _get_client() -> instructor.Instructor:
    _load_env()
    # .env keeps the key under the generic ANTHROPIC_API_KEY name; accept
    # GROQ_API_KEY too so either works.
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
    client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
    return instructor.from_openai(client, mode=instructor.Mode[INSTRUCTOR_MODE.upper()])


def render_pages(path: Path, dpi: int = DPI) -> list[bytes]:
    """Render each page of the PDF to a PNG (bytes) at the given DPI."""
    pages: list[bytes] = []
    with fitz.open(path) as doc:
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=matrix)
            pages.append(pix.tobytes("png"))
    return pages


# Bytes commonly mis-decoded when a PDF uses CP1252-like font encodings.
_ENCODING_FIXES = {
    b"\x92": "\u00b0",  # degree sign (e.g. "-50\x92C" -> "-50°C")
    b"\x93": "\u00b1",  # plus-minus
    b"\x96": "\u2013",  # en dash
    b"\x97": "\u2014",  # em dash
}


def _fix_encoding(text: str) -> str:
    """Recover mojibake from legacy font encodings (common in real catalogs)."""
    raw = text.encode("latin-1", errors="ignore")
    for byte, char in _ENCODING_FIXES.items():
        raw = raw.replace(byte, char.encode("utf-8"))
    return raw.decode("utf-8", errors="replace")


def read_page_text(path: Path) -> list[str]:
    """Extract the text layer of every page, with encoding recovery."""
    with fitz.open(path) as doc:
        return [_fix_encoding(page.get_text()) for page in doc]


def extract_page(client: instructor.Instructor, png: bytes, page_number: int) -> PageExtraction:
    """Run the vision model on one page image and return structured fields."""
    return _create_with_backoff(
        client,
        model=DEFAULT_MODEL,
        max_retries=MAX_RETRIES,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64.b64encode(png).decode('ascii')}",
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            f"This is page {page_number} of the document. "
                            "Extract the fields visible on this page. "
                            "Return null if absent."
                        ),
                    },
                ],
            },
        ],
        response_model=PageExtraction,
    )


def extract_page_text(client: instructor.Instructor, text: str, page_number: int) -> PageExtraction:
    """Run the LLM on one page's extracted text and return structured fields."""
    return _create_with_backoff(
        client,
        model=DEFAULT_MODEL,
        max_retries=MAX_RETRIES,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    f"This is the text of page {page_number} of the document.\n\n"
                    f"--- PAGE TEXT START ---\n{text}\n--- PAGE TEXT END ---\n\n"
                    "Extract the fields present in this text. Return null if absent."
                ),
            },
        ],
        response_model=PageExtraction,
    )


def _create_with_backoff(client: instructor.Instructor, **kwargs) -> PageExtraction:
    """Instructor create() with explicit 429 backoff (free-tier TPM limits)."""
    delay = 5.0
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError as exc:
            msg = str(exc)
            if "tokens per day" in msg:
                # Daily quota exhausted — retrying is pointless until reset.
                raise RuntimeError(
                    "Groq daily token quota exhausted. Wait for the reset "
                    "(see 'try again in ...' below) and re-run — already-extracted "
                    "pages are cached, so nothing is wasted.\n" + msg
                ) from exc
            if attempt == RATE_LIMIT_RETRIES:
                raise
            wait = delay
            retry_after = getattr(getattr(exc, "response", None), "headers", {}).get("retry-after")
            if retry_after:
                try:
                    wait = max(float(retry_after) + 1.0, 1.0)
                except ValueError:
                    pass
            print(
                f"Rate limited; retrying in {wait:.0f}s "
                f"({attempt + 1}/{RATE_LIMIT_RETRIES})",
                file=sys.stderr,
            )
            time.sleep(wait)
            delay = min(delay * 2, 30.0)
    raise RuntimeError("unreachable")


def _cache_key(kind: str, content: str | bytes) -> str:
    h = hashlib.sha256()
    h.update(DEFAULT_MODEL.encode())
    h.update(kind.encode())
    h.update(SYSTEM_PROMPT.encode())
    h.update(content.encode("utf-8") if isinstance(content, str) else content)
    return h.hexdigest()


def _cache_get(key: str) -> PageExtraction | None:
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        return PageExtraction.model_validate_json(path.read_text(encoding="utf-8"))
    return None


def _cache_put(key: str, page: PageExtraction) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.json").write_text(page.model_dump_json(), encoding="utf-8")


def _extract_page_cached(
    client: instructor.Instructor,
    kind: str,
    content: str | bytes,
    page_number: int,
) -> PageExtraction:
    """Cache-aware, throttled page extraction (text or image mode)."""
    key = _cache_key(kind, content)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    time.sleep(PAGE_DELAY)  # stay under the TPM ceiling on burst runs
    page = (
        extract_page(client, content, page_number)
        if kind == "image"
        else extract_page_text(client, content, page_number)
    )
    _cache_put(key, page)
    return page


def extract_pdf(path: str | Path) -> Product:
    """Extract a single Product from a PDF, page by page.

    Fields found on earlier pages win; provenance records the page each
    field was actually seen on (e.g. "page 2").
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    client = _get_client()
    product = Product()

    if EXTRACT_VISION:
        pages = render_pages(path)
    else:
        pages = read_page_text(path)

    for page_number, content in enumerate(pages, start=1):
        if EXTRACT_VISION:
            page = _extract_page_cached(client, "image", content, page_number)
        else:
            if not content.strip():
                continue  # scanned page with no text layer — nothing to extract
            page = _extract_page_cached(client, "text", content, page_number)
        for field in PRODUCT_FIELDS:
            value = getattr(page, field)
            if value is not None and getattr(product, field) is None:
                setattr(product, field, value)
                product.source[field] = f"page {page_number}"
                confidence: Confidence = page.confidence.get(field, "medium")
                product.confidence[field] = confidence

    return product


def main() -> None:
    # Force UTF-8 output: Windows consoles default to a legacy code page and
    # would corrupt non-ASCII values like "-50°C to +400°C" in the JSONL feed.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) != 2:
        print("Usage: python -m extraction.pdf_extractor <file.pdf | samples_dir>", file=sys.stderr)
        raise SystemExit(1)

    target = Path(sys.argv[1])
    if target.is_dir():
        # Batch mode: one JSONL record per PDF, ready for the Phase 3 pipeline.
        for pdf in sorted(target.glob("*.pdf")):
            record = {"file": pdf.name, **extract_pdf(pdf).model_dump()}
            print(json.dumps(record, ensure_ascii=False))
    else:
        product = extract_pdf(target)
        print(json.dumps(product.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
