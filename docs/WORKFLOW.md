# Workflow — How the System Works End to End

This document explains the complete workflow of the UniHack AI Product Content
Enrichment Pipeline: the goal, every stage of the backend pipeline, the internal
data model that flows between stages, and how the frontend consumes it.

---

## 1. Goal

Transform **messy industrial catalogue rows** (a manufacturer part number plus a
cryptic description) into **standardized, searchable, commerce-ready product
records** in Unilog's exact 252-column delivery format — with every claim
grounded in manufacturer evidence and normalized against controlled vocabularies.

The guiding philosophy:

> **The AI proposes. The evidence grounds it. The controlled vocabularies
> constrain it. Deterministic rules validate it. Confidence identifies
> uncertainty. Humans handle the difficult cases.**

The system is **never** `LLM → 252 columns`. A rich internal `Product` model is
built stage by stage, and only the final step serializes it into the delivery
format.

---

## 2. High-Level Flow

```text
Raw Catalogue Row (6 columns)
     │
     ▼
┌──────────────────────────────────────────────────────────────────┐
│  1  PREPROCESSING & UNDERSTANDING    src/preprocessing/           │
│  2  ENTITY RESOLUTION                src/entity_resolution/       │
│  3  CLASSIFICATION                   src/classification/          │
│  4  SOURCE DISCOVERY                 src/source_discovery/        │
│  5  RAG / EVIDENCE                   src/rag/                     │
│  6  ATTRIBUTE EXTRACTION             src/attributes/extractor.py  │
│  7  NORMALIZATION  (UOM / LOV / frac) src/normalization/           │
│  8  CONTENT GENERATION               src/content/                 │
│  9  VALIDATION                       src/validation/              │
│ 10  CONFIDENCE + REVIEW Triage       src/validation/confidence.py │
└──────────────────────────────────────────────────────────────────┘
     │
     ▼
Rich internal Product model   →   src/output/mapper.py
     ▼
252-Column Delivery Row  (exact headers, exact order, "" for empty)
```

Orchestration: `src/pipeline/orchestrator.py` (single row) and
`src/pipeline/batch.py` (multi-threaded batch over a DataFrame).

---

## 3. Stage-by-Stage Walkthrough

### Stage 1 — Preprocessing & Product Understanding

**Files:** `src/preprocessing/models.py`, `understanding.py`, `understanding_model.py`

The 6 raw input columns are cleaned into a `ProductInput`:

| Raw column | Example | Cleaned to |
|---|---|---|
| `Mfg_Part_Num` | `PDSH4816AF` | `mfg_part_num` |
| `Part_Desc` | `PDSH4816AF Dishwasher SS - Display Only` | `part_desc` |
| `E1_Brand` | `-- Unbranded --` | `None` (placeholder) |
| `Unilog_Brand` | `-- No Unilog Brand --` | `None` (placeholder) |
| `DIB_Brand` | `-- No DIB Brand --` | `None` (placeholder) |
| `Part_Manuf` | `Appliance Dealers Cooperative (APPDE)` | `part_manuf` |

- Placeholder strings (`-- Unbranded --`, `-- No DIB Brand --`, `n/a`, `none`)
  become `None`.
- Best brand = `Unilog_Brand` → `E1_Brand` → `DIB_Brand` (first non-empty).
- Best manufacturer = `Part_Manuf` → best brand.

Next, `ProductUnderstandingExtractor` expands industrial abbreviations
deterministically (`CPLG`→`Coupling`, `BRS`→`Brass`, `SST`→`Stainless Steel`,
`150#`→`150 lb`, …) and — when a Groq API key is present — asks the LLM for a
structured JSON of **candidate facts**:

```text
"3/8 CPLG BRS 150#"   →   ProductUnderstanding(
                                product_type="Coupling",
                                size="3/8",
                                material="Brass",
                                pressure_rating="150 lb",
                            )
```

These are **candidate facts only** — not yet normalized or validated. Without a
key, the stage degrades gracefully to the raw description.

### Stage 2 — Entity Resolution (Manufacturer & Brand)

**Files:** `src/entity_resolution/manufacturer.py`, `brand.py`

Resolves the messy raw manufacturer/brand strings against the master list
`UniCat_Manufacturer_and_Brand_List.xlsx`:

```text
Raw string → clean → exact match → normalized match → fuzzy match
          → candidate ranking → LLM disambiguation (only if ambiguous)
          → canonical Manufacturer / Brand (+ code + confidence)
```

Rules:
- **Never invent** manufacturer/brand names — output must exist in the master.
- Low-confidence matches carry `needs_review=True` for the review queue.
- Brand placeholders (`-- Unbranded --`, etc.) are already `None` by Stage 1.

### Stage 3 — Classification

**Files:** `src/classification/taxonomy.py`, `classifier.py`

Determines `Dept > Class > Fine > Classpath` from a **controlled taxonomy**
(never invented):

```text
ProductUnderstanding
      → keyword match (deterministic)
      → fuzzy match (difflib)
      → LLM ranking only among the top-K candidates
      → final Classpath + confidence
```

If the LLM returns a value outside `VALID_CLASSPATHS`, it is rejected.

### Stage 4 — Manufacturer Source Discovery

**Files:** `src/source_discovery/discovery.py`

Generates deterministic retrieval queries (`<MPN> specifications`,
`<MPN> installation manual`, …) and asks the LLM to suggest **official
manufacturer URLs** (product page, spec sheet, installation manual). Marketplace
domains (`amazon`, `grainger`, `mcmaster`, `homedepot`, …) are filtered out per
the challenge sourcing rules. Degrades to an empty list without a key.

### Stage 5 — RAG / Evidence Retrieval

**Files:** `src/rag/pipeline.py`, `document.py`, `retriever.py`

For each discovered source: fetch the page (`requests` + `BeautifulSoup`), strip
scripts/nav/footers, chunk the text with overlap, and retrieve top-K chunks with
a BM25-style retriever.

Every chunk keeps **source metadata** so the system can always answer
*"where did this attribute come from?"*:

```json
{ "source_url": "...", "manufacturer": "...", "mpn": "...",
  "document_type": "specification_sheet", "page": 3 }
```

### Stage 6 — Attribute Extraction (RAG-grounded)

**Files:** `src/attributes/extractor.py`

The LLM reads the product + evidence chunks and extracts candidate attributes
**only from that evidence**, citing source URL + page for each:

```json
{ "label": "Voltage Rating", "candidate_value": "120",
  "candidate_uom": "V", "source": "mfr_spec.pdf", "source_page": 3,
  "confidence": 0.94 }
```

No evidence → no attributes (never hallucinated).

### Stage 7 — Normalization

**Files:** `src/normalization/uom.py`, `lov.py`, `fraction_utils.py`
**Entry:** `src/attributes/mapper.py::normalize_candidate_attribute`

Each candidate passes through the deterministic engines:

1. **UOM engine** — normalizes unit names against the approved UOM master
   (`inches`→`in`, `volts`→`V`); unknown units are flagged for review.
2. **LOV engine** — maps supplier values to the canonical list of values
   (`SS`, `SST`, `Stainless-steel` → `Stainless Steel`); unrecognized values
   are kept but flagged `lov_matched=False`.
3. **Fraction engine** — inch measurements become fractions
   (`0.5 in`→`1/2 in`, `0.375 in`→`3/8 in`, `50.25 in`→`50-1/4 in`).

The result is a normalized `Attribute`:

```json
{ "label": "Material", "value": "Stainless Steel", "uom": null,
  "raw_value": "SST", "source": "manufacturer_spec.pdf",
  "source_page": 3, "confidence": 0.94,
  "lov_matched": true, "needs_review": false }
```

### Stage 8 — Content Generation

**Files:** `src/content/` (`invoice.py`, `mobile.py`, `title.py`,
`long_description.py`, `marketing.py`, `features.py`, `generator.py`)

Deterministic templates that assemble descriptions **only from verified
attributes** (no invented claims), reproducing the confirmed ground-truth
constructions:

| Field | Example generated |
|---|---|
| `INVOICE_DESC` | `DISHWASHER LEG 5 SST 120V 15A 50-1/4IN` (≤ 40 chars) |
| `MOBILE_DESC` | `Rheem Manufacturing FRIGIDAIRE, Dishwasher, Professional Series, PDSH4816AF` |
| `SHORT_DESC` | `FRIGIDAIRE® Professional Series PDSH4816AF Dishwasher With CleanBoost™, …` |
| `LONG_DESC1` | `FRIGIDAIRE® Dishwasher With CleanBoost™, Professional Series, 5 Wash Cycles, 120 V, …` |
| `RETAIL_DESC` | `Professional Series Dishwasher, Leg Mounting, 5-Wash Cycle, Stainless Steel` |
| `MARKETING_DESCRIPTION` | A paragraph assembled from verified sound/cycles/voltage/material/features |
| `ITEM_FEATURES_1..20` | Feature bullets from verified attributes + evidence |

### Stage 9 — Validation

**Files:** `src/validation/validator.py`, `rules.py`, `character_limits.py`, `grounding.py`

Checks per product:

- **LOV compliance** — is every value in the approved LOV?
- **UOM compliance** — is every unit approved?
- **Grounding** — does every factual attribute have a source?
- **Character limits** — confirmed `INVOICE_DESC` = 40 chars (hard failure if
  exceeded; other limits are reported as *unchecked* until the guidelines doc
  is supplied — never silently passed).
- **Casing / completeness** rules are ready to enforce as limits are confirmed.

### Stage 10 — Confidence & Review Triage

**Files:** `src/validation/confidence.py`

Weighted score: 25% manufacturer match + 25% classification + 20% LOV +
15% UOM + 15% grounding.

| Status | Score | Action |
|---|---|---|
| `HIGH` | > 0.85 | Auto-accept |
| `MEDIUM` | 0.60–0.85 | OK, but flagged if any attribute needs review |
| `LOW` | < 0.60 | Human review |

`needs_review = True` if status is LOW, hard validation fails, or any attribute
carries `needs_review=True`.

### Stage 11 — Output (252 Columns)

**Files:** `src/output/mapper.py`, `exporter.py`

- Reads the **exact header list** from
  `data/reference/Unihack_ Expected Output - Delivery Format.csv`
  (never hardcoded).
- Initializes all 252 columns to `""` (never `None`/`N/A`/`nan`).
- Maps the internal product → positional `ATTRIBUTE_LABEL/VALUE/UOM` slots,
  `ITEM_FEATURES_1..20`, description fields, `With`/`Includes`, etc.
- Auto-derives `Dept/Class/Fine` from `Classpath` when not explicit.
- Derives asset filenames (`FRIGIDAIRE_PDSH4816AF_Specification_Sheet.pdf`).
- Verifies header count/order before writing CSV.

---

## 4. The Internal Data Model (V1)

The single object that flows through every stage and is consumed by both the
output mapper and the frontend:

```text
Product
├── Identity            (row_id, mfg_part_num, part_desc, brands, part_manuf)
├── Manufacturer        (manufacturer_name, manufacturer_code, manufacturer_confidence)
├── Brand               (brand_name, brand_code, brand_confidence)
├── Classification      (dept, class_name, fine, classpath, classification_confidence)
├── Attributes          [ {label, value, uom, raw_value, source, source_page,
                           confidence, lov_matched, needs_review} ]
├── Descriptions        (MOBILE_DESC, INVOICE_DESC, SHORT_DESC, LONG_DESC1,
                          RETAIL_DESC, MARKETING_DESCRIPTION)
├── Features            [ ITEM_FEATURES_1 .. 20 ]
├── Sources             [ {source_url, manufacturer, mpn, document_type, page} ]
├── Validation          (valid, issues, lov/uom/grounding rates, char compliance)
├── Confidence          (overall_confidence, status, needs_review, review_reasons)
└── Review Status       (accept / edit / reject — held by the frontend)
```

This is what `build_internal_product()` produces and what the frontend renders.

---

## 5. Frontend Workflow (V8–V12)

**Folder:** `frontend/` — a static, no-build dashboard (vanilla HTML/CSS/JS).

### How data reaches the UI

```text
pipeline (run_pipeline.py --internal-json data/processed/products.json)
     │   writes the rich internal Product models (V1)
     ▼
frontend/generate_data.py
     │   re-computes aggregate metrics with the REAL validation/confidence code
     ▼
frontend/data/products.json   ← products, attributes, evidence, confidence
frontend/data/metrics.json    ← metrics computed from that output (never hardcoded)
     ▼
frontend/serve.py   →   http://127.0.0.1:8000
```

> **Important:** `metrics.json` is *computed* from the actual pipeline output by
> `_compute_metrics()` (same `validate_product` / `compute_confidence`
> functions the backend uses). There are **no hardcoded demonstration numbers**.

### Views

| View | Route | What it shows | Plan ref |
|---|---|---|---|
| **Dashboard** | `#dashboard` | Products Processed, High Confidence, Needs Review, Validation Failures, Grounding Rate + recent products table | V8 |
| **Products** | `#products` | Searchable list (MPN / description / brand / classpath) | V9 |
| **Product Detail** | `#product/<id>` | Identity, manufacturer, brand, MPN, classpath, confidence, attributes, descriptions, features | V9 |
| **Evidence viewer** | click an attribute | Source URL, document type, page, raw value — proves RAG grounding | V10 |
| **Review** | `#review` | Queue of products flagged `needs_review`, with reasons | V11 |
| **Metrics** | `#metrics` | Field accuracy, LOV/UOM compliance, grounding rate, review rate, avg confidence — measured | V12 |

### Human review (V11)

On the product detail page: **Accept / Edit / Reject**. Decisions are persisted
in `localStorage` (`unihack.reviews`) so they survive reloads, and the review
badge in the header updates live.

### Export (V17 DoD)

The Products view has an **Export CSV** button that generates a client-side CSV
of the filtered internal products.

### Running the UI

```powershell
# real data
python frontend/generate_data.py --limit 200     # builds frontend/data from pipeline output
python frontend/serve.py                          # opens http://127.0.0.1:8000

# or preview without the full dataset
python frontend/generate_sample_data.py           # sample internal products, real metric computation
python frontend/serve.py
```

---

## 6. How to Run Everything

```powershell
pip install -r requirements.txt          # pydantic, pandas, openpyxl, groq, requests, bs4, python-dotenv
# place datasets under data/raw and data/reference (gitignored)
# optionally add GROQ_API_KEY to .env

# 1. Full pipeline → 252-column CSV + internal JSON
python run_pipeline.py --input "data/raw/Unihack_ Sample Dataset - Input.csv" `
    --output "data/processed/output.csv" `
    --master "data/reference/UniCat_Manufacturer_and_Brand_List.xlsx" `
    --internal-json data/processed/products.json --limit 200

# 2. Tests
python tests/run_all.py

# 3. Evaluation (needs the 200-row labelled file)
python scripts/evaluate_200.py           # field accuracy + compliance metrics
python scripts/evaluate_1000.py          # structural completeness + scale report

# 4. Frontend
python frontend/generate_data.py
python frontend/serve.py
```

---

## 7. Code Map by Team (ownership)

| Area | Code | Team |
|---|---|---|
| Understanding, Entity Resolution, Classification, Source Discovery, RAG, Pipeline | `src/preprocessing/`, `src/entity_resolution/`, `src/classification/`, `src/source_discovery/`, `src/rag/`, `src/pipeline/` | Tanush |
| Normalization, Validation, Confidence, Evaluation, Output | `src/normalization/`, `src/validation/`, `src/evaluation/`, `src/output/`, `src/attributes/mapper.py` | Yashas |
| Content Generation, Frontend, Review | `src/content/`, `frontend/` | Vedanth |

Shared work: dataset analysis, 200-row testing, integration, demo
(see `UNIHACK_IMPLEMENTATION_PLAN.md` sections 7–8).