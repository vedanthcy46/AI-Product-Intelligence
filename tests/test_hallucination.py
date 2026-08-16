"""Hallucination test (README §5 Phase 1).

Generates a synthetic spec-sheet PDF deliberately MISSING temperature_range,
then runs extract_pdf and asserts null is returned for the missing field —
not a guess.

Run from the repo root (requires ANTHROPIC_API_KEY in .env):
    python -m tests.test_hallucination --make-only   # regenerate the fixture
    python -m tests.test_hallucination
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"
FIXTURE = SAMPLES_DIR / "synthetic_valve_missing_temp.pdf"


def make_sample_pdf() -> Path:
    """Create a one-page spec sheet with every field EXCEPT temperature_range."""
    import pymupdf as fitz  # PyMuPDF

    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()

    lines = [
        ("FORGED BALL VALVE - SERIES FBV-200", 16),
        ("", 11),
        ("Size:            2 inch", 11),
        ("Material:        Carbon Steel", 11),
        ("Pressure Rating: 200 WOG", 11),
        ("Thread Type:     NPT", 11),
        # temperature_range deliberately omitted
        ("", 11),
        ("Suitable for water, oil and gas lines.", 10),
    ]

    y = 80
    for text, size in lines:
        if text:
            page.insert_text((60, y), text, fontsize=size, fontname="helv")
        y += size + 14

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

    # Hard requirement: the missing field must be null, not a hallucination.
    assert product.temperature_range is None, (
        f"HALLUCINATION: temperature_range was not on the page but got "
        f"{product.temperature_range!r}"
    )

    # Sanity: the fields that ARE on the page should be extracted.
    assert product.product_name is not None, "product_name should be extracted"
    assert product.size is not None, "size should be extracted"
    assert product.material is not None, "material should be extracted"
    assert product.pressure_rating is not None, "pressure_rating should be extracted"
    assert product.thread_type is not None, "thread_type should be extracted"

    # Provenance must point at page 1 for every extracted field.
    for field in ("product_name", "size", "material", "pressure_rating", "thread_type"):
        assert product.source.get(field) == "page 1", f"bad source for {field}"
        assert field in product.confidence, f"missing confidence for {field}"

    print("\nPASS: missing field returned null; present fields extracted with provenance.")


if __name__ == "__main__":
    if "--make-only" in sys.argv:
        print(make_sample_pdf())
    else:
        run_test()
