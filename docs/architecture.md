# Architecture — AI Product Content Enrichment Pipeline

## System Philosophy

> **The AI proposes. The evidence grounds it. The controlled vocabularies
> constrain it. Deterministic rules validate it. Confidence identifies
> uncertainty. Humans handle the difficult cases.**

The pipeline is **never** `LLM → 252 Columns`. A rich internal `Product` model
(see `docs/dataset_map.md`) flows through modular stages, and only the final
output step serialises it into the 252-column delivery format.

## End-to-End Flow

```text
Raw Catalogue Row
     ↓
1. Preprocessing            src/preprocessing/        T1
     ↓
2. Entity Resolution        src/entity_resolution/    T2, T3
     ↓
3. Product Understanding    src/preprocessing/        T4
     ↓
4. Classification           src/classification/       T5
     ↓
5. Source Discovery         src/source_discovery/     T6
     ↓
6. RAG / Evidence           src/rag/                  T7
     ↓
7. Attribute Extraction     src/attributes/           Y6, T8
     ↓
8. Normalization            src/normalization/        Y3, Y4, Y5
     ↓
9. Content Generation       src/content/              V2-V7
     ↓
10. Validation              src/validation/           Y7, Y8
     ↓
11. Evaluation              src/evaluation/           Y9
     ↓
12. Output (252 columns)    src/output/               Y10
```

Orchestration lives in `src/pipeline/` (`orchestrator.py` single row,
`batch.py` multi-threaded batch).

## Module Map

| Module | Responsibility | Owner |
|---|---|---|
| `src/preprocessing/models.py` | `ProductInput` (cleaned 6-field input) | Tanush |
| `src/preprocessing/understanding.py` | abbreviation expansion + LLM fact extraction | Tanush |
| `src/entity_resolution/` | manufacturer & brand resolution (exact → normalized → fuzzy → LLM) | Tanush |
| `src/classification/` | dept/class/fine/classpath from controlled taxonomy | Tanush |
| `src/source_discovery/` | manufacturer web source discovery | Tanush |
| `src/rag/` | document fetch → parse → chunk → BM25 retrieval | Tanush |
| `src/attributes/` | `Attribute` schema, extraction, candidate normalisation | Yashas |
| `src/normalization/` | LOV engine, UOM engine, fraction engine | Yashas |
| `src/validation/` | LOV/UOM/char/grounding validation + confidence triage | Yashas |
| `src/evaluation/` | metrics against 200 ground-truth rows | Yashas |
| `src/output/` | 252-column mapper + CSV/XLSX exporter | Yashas |
| `src/content/` | invoice/mobile/short/long/retail/marketing/features | Vedanth |
| `src/pipeline/` | orchestrator + batch | Tanush |

## Data Contracts

### Attribute (final, normalised)

```json
{
  "label": "Material",
  "value": "Stainless Steel",
  "uom": null,
  "raw_value": "SST",
  "source": "manufacturer_spec.pdf",
  "source_page": 3,
  "confidence": 0.94,
  "lov_matched": true,
  "needs_review": false
}
```

### RAG Evidence Chunk

```json
{
  "source_url": "https://...",
  "manufacturer": "...",
  "mpn": "...",
  "document_type": "specification_sheet",
  "page": 3
}
```

### Product-level Confidence

```json
{
  "overall_confidence": 0.97,
  "status": "HIGH",
  "needs_review": false,
  "review_reasons": []
}
```

## Failure Strategy

- **Graceful degradation**: a row that throws mid-pipeline falls back to
  pass-through of the raw input into the output mapper (`orchestrator.py`).
- **Never invent values**: LLM outputs are constrained to controlled vocabularies
  (taxonomy, LOV, UOM master) before acceptance.
- **Soft vs hard validation**: character-limit overflow is a hard failure;
  LOV/grounding misses are soft issues routed to human review.

## Technology

- Python 3, `pydantic` data models, `pandas`/`openpyxl` for I/O
- Groq LLM (`llama3-8b-8192`) for understanding, classification ranking, extraction
- `requests` + `beautifulsoup4` for source discovery / document parsing
- BM25 retriever in `src/rag/retriever.py` (no external vector DB)
- `concurrent.futures` for batch throughput

## Repository Layout

```text
data/          raw + reference datasets (gitignored, local only)
docs/          dataset map, output schema, field groups, transformation matrix
src/           pipeline modules (see Module Map)
frontend/      dashboard + product/review/metrics UI (V8-V12)
tests/         automated tests
scripts/       build/verification helper scripts
run_pipeline.py CLI entry point
```

See `UNIHACK_IMPLEMENTATION_PLAN.md` section 19 for the canonical layout.