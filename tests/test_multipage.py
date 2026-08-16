"""Multi-page provenance test (README §5 Phase 1).

Real catalogs spread one product across pages: name/marketing on page 1,
spec table on page 2. This test builds a 2-page PDF and asserts that
extract_pdf merges fields across pages AND records the correct source
page for each field.

Run from the repo root (requires GROQ_API_KEY in .env):
    python -m tests.test_multipage --make-only   # regenerate the fixture
    python -m tests.test_multipage
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"
FIXTURE = SAMPLES_DIR / "synthetic_valve_multipage.pdf"


def make_sample_pdf() -> Path:
    """Page 1: product name + size. Page 2: remaining specs (incl. temp range)."""
    import pymupdf as fitz  # PyMuPDF

    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()

    # Page 1 — cover/marketing: name and size only
    page1 = doc.new_page()
    for y, (text, size) in enumerate(
        [
            ("GATE VALVE - SERIES GV-450", 16),
            ("", 11),
            ("Full bore industrial gate valve for oil and gas service.", 10),
            ("Size: 4 inch", 11),
        ],
        start=5,
    ):
        if text:
            page1.insert_text((60, y * 25), text, fontsize=size, fontname="helv")

    # Page 2 — spec sheet: remaining fields
    page2 = doc.new_page()
    for y, (text, size) in enumerate(
        [
            ("Technical Specifications", 14),
            ("", 11),
            ("Material:        316SS", 11),
            ("Pressure Rating: PN16", 11),
            ("Thread Type:     BSPP", 11),
            ("Temp Range:      -20 C to 200 C", 11),
        ],
        start=5,
    ):
        if text:
            page2.insert_text((60, y * 25), text, fontsize=size, fontname="helv")

    doc.save(FIXTURE)
    doc.close()
    return FIXTURE


def run_test() -> None:
    from extraction.pdf_extractor import extract_pdf

    if not FIXTURE.exists():
        make_sample_pdf()

    product = extract_pdf(FIXTURE)

    print("Extracted record:")
    for field, value in product.model_dump().items():
        print(f"  {field}: {value}")

    # Fields from page 1
    assert product.product_name is not None, "product_name should come from page 1"
    assert product.size is not None, "size should come from page 1"
    assert product.source.get("product_name") == "page 1", "product_name provenance wrong"
    assert product.source.get("size") == "page 1", "size provenance wrong"

    # Fields from page 2
    assert product.material is not None, "material should come from page 2"
    assert product.pressure_rating is not None, "pressure_rating should come from page 2"
    assert product.thread_type is not None, "thread_type should come from page 2"
    assert product.temperature_range is not None, "temperature_range should come from page 2"
    for field in ("material", "pressure_rating", "thread_type", "temperature_range"):
        assert product.source.get(field) == "page 2", f"{field} provenance wrong"
        assert field in product.confidence, f"missing confidence for {field}"

    print("\nPASS: fields merged across pages with correct per-page provenance.")


if __name__ == "__main__":
    if "--make-only" in sys.argv:
        print(make_sample_pdf())
    else:
        run_test()
