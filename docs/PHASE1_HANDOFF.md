# Phase 1 Handoff — PDF Extraction (Vedanth → Yashas / Tanush)

Status: **code-complete and tested against live Groq.** Branch: `feat/vedanth-pdf`.

## Contract for Yashas (Phase 3 — dispatcher + SQLite)

```python
from extraction.pdf_extractor import extract_pdf

product = extract_pdf("data/samples/anything.pdf")  # -> schema.Product
```

- One `Product` per PDF. For a folder: `python -m extraction.pdf_extractor data/samples/`
  prints **JSONL** (one record per line) with an extra `"file"` key — ready to pipe
  straight into SQLite ingestion.
- Errors: `FileNotFoundError` (bad path), `RuntimeError` (missing API key),
  `InstructorRetryException` (LLM failed after 3 retries). Wrap accordingly.

### Record shape (see `schema.py` — single source of truth)

```json
{
  "product_name": "FORGED BALL VALVE - SERIES FBV-200",
  "size": "2 inch",
  "material": "Carbon Steel",
  "pressure_rating": "200 WOG",
  "thread_type": "NPT",
  "temperature_range": null,
  "confidence": {"size": "high", "material": "high", ...},
  "source": {"size": "page 1", "material": "page 1", ...},
  "flags": []
}
```

**Field-name reconciliation note (README §3):** PDF provenance is already unified to
`source: dict[field, "page N"]` strings — matches the Phase 3 target shape, so your
Excel extractor only needs to emit `"row N of <file>"` into the same dict.
`confidence` keys exist **only for non-null fields**. Absent field → value `null`,
no `source`/`confidence` entries for it. `flags` always `[]` from extraction
(your Phase 4 owns flags).

## Contract for Tanush (Phase 5 — backend/UI)

- Source links in the UI: `"page N"` → render PDF page N (1-based) via react-pdf.
  Bounding-box highlighting is **not** available (deferred Phase 6 stretch) —
  show the text label, per README §5 scope-cut.
- PDFs are never mutated; the UI can read the original uploaded file directly.

## Environment

- Python 3.12 · deps in `requirements.txt` (pymupdf, openai, instructor, pydantic, python-dotenv)
- `.env` at repo root: Groq key under `GROQ_API_KEY` (or `ANTHROPIC_API_KEY` — both read)
- Backend: Groq (`https://api.groq.com/openai/v1`), model `llama-3.3-70b-versatile`
- **Rate limits:** free-tier key is ~12k TPM. The extractor throttles per page
  (`GROQ_PAGE_DELAY`, default 2s) and backs off on 429s (`GROQ_RATE_RETRIES`,
  default 6). Already-extracted pages are cached in `.cache/extraction/`, so
  re-runs are free and instant.
- **Known limitation:** current Groq key has no vision model → extraction runs in
  **text mode** (`page.get_text()`). Scanned/image-only PDFs return empty records.
  Flip `EXTRACT_VISION=true` + a vision `GROQ_MODEL` when one becomes available;
  the image pipeline is already implemented behind that flag.

## Tests (all passing)

```
python -m tests.test_hallucination   # missing field -> null, never a guess
python -m tests.test_multipage       # cross-page merge + per-page provenance
python -m tests.test_table_format    # noisy cover page + spec-table layout
```
