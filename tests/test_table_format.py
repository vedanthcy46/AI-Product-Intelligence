"""Realistic-catalog test: noisy cover page + tabular spec sheet.

Real valve catalogs open with marketing pages (no specs) and list specs
in two-column tables. This fixture reproduces both and asserts that:
  * the cover page contributes nothing (no hallucinated fields),
  * the spec table is parsed correctly,
  * the absent temperature_range stays null.

Run from the repo root (requires GROQ_API_KEY in .env):
    python -m tests.test_table_format --make-only   # regenerate the fixture
    python -m tests.test_table_format
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"
FIXTURE = SAMPLES_DIR / "synthetic_catalog_table.pdf"


def make_sample_pdf() -> Path:
    import pymupdf as fitz  # PyMuPDF

    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()

    # Page 1 — pure marketing noise, no specifications at all
    page1 = doc.new_page()
    noise = [
        ("ACME VALVE COMPANY", 20),
        ("", 12),
        ("Industrial Flow Control Solutions Since 1962", 12),
        ("", 12),
        ("Quality. Reliability. Performance.", 11),
        ("www.acmevalves.example", 10),
    ]
    y = 100
    for text, size in noise:
        if text:
            page1.insert_text((60, y), text, fontsize=size, fontname="helv")
        y += size + 16

    # Page 2 — product heading + two-column spec table (no temp range)
    page2 = doc.new_page()
    page2.insert_text((60, 80), "SWING CHECK VALVE - CV-88 SERIES", fontsize=16, fontname="helv")
    page2.insert_text((60, 110), "Technical Specifications", fontsize=12, fontname="helv")

    table_rows = [
        ("Port Size", "1/2 inch"),
        ("Body Material", "Brass"),
        ("Max Pressure", "400 WOG"),
        ("End Connection", "NPT"),
    ]
    y = 150
    for label, value in table_rows:
        page2.insert_text((70, y), label, fontsize=11, fontname="helv")
        page2.insert_text((280, y), value, fontsize=11, fontname="helv")
        y += 24

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

    # Specs live on page 2 — the marketing cover must contribute nothing.
    assert product.product_name is not None, "product_name missing"
    assert product.source.get("product_name") == "page 2", "product_name must come from page 2"

    assert product.size is not None, "size missing (table row: Port Size)"
    assert product.material is not None, "material missing (table row: Body Material)"
    assert product.pressure_rating is not None, "pressure_rating missing (table row: Max Pressure)"
    assert product.thread_type is not None, "thread_type missing (table row: End Connection)"
    for field in ("size", "material", "pressure_rating", "thread_type"):
        assert product.source.get(field) == "page 2", f"{field} provenance wrong"
        assert field in product.confidence, f"missing confidence for {field}"

    # Absent field must remain null despite the noisy cover page.
    assert product.temperature_range is None, (
        f"HALLUCINATION: temperature_range not in catalog, got {product.temperature_range!r}"
    )
    assert "temperature_range" not in product.source

    print("\nPASS: cover-page noise ignored; spec table extracted; absent field stayed null.")


if __name__ == "__main__":
    if "--make-only" in sys.argv:
        print(make_sample_pdf())
    else:
        run_test()
