# Evaluation — Methodology & Metrics

> Reference: `Unilog-Sample_200_Items-Input-vs-Output.xlsx` (200 labelled rows).
> Code: `src/evaluation/`.

## Metrics

All metrics are computed from **actual pipeline output**, never hardcoded
(the frontend metrics dashboard reads these numbers).

### Field Accuracy

```text
Correct predictions
──────────────────── × 100
Expected values
```

Per-field comparison against the labelled delivery output. Core fields:
`MANUFACTURER_NAME`, `BRAND_NAME`, `Classpath`, `Product Name`, `INVOICE_DESC`,
`SHORT_DESC`, `MOBILE_DESC`, `RETAIL_DESC` (configurable).

### LOV Compliance

```text
Valid canonical values
────────────────────── × 100
Generated values
```

Share of attribute values that matched the approved LOV after normalisation.
Attributes with `value = None` are excluded (a known-but-unfilled label has no
value to check).

### UOM Compliance

```text
Approved UOM values
─────────────────── × 100
Generated UOM values
```

Share of attributes carrying a UOM that is present in the approved UOM master.

### Character Compliance

```text
Fields within limits
──────────────────── × 100
Generated fields
```

Only `INVOICE_DESC` (limit 40, confirmed from ground truth) is currently
enforceable. Other limits are `TODO` until the official content guidelines
document is supplied — these fields are honestly reported as *unchecked*, not
silently passed.

### Grounding Rate

```text
Supported factual claims
───────────────────────── × 100
Factual claims generated
```

Share of attributes with a non-None value that carry a `source` from the RAG
evidence layer.

### Review Rate

```text
Rows requiring review
───────────────────── × 100
Rows processed
```

Rows flagged by the confidence triage engine (`status == LOW`, hard validation
failure, or any attribute `needs_review`).

## Confidence Model (`src/validation/confidence.py`)

Weighted score (100% total):

| Signal | Weight |
|---|---|
| Manufacturer match confidence | 25% |
| Classification confidence | 25% |
| LOV compliance rate | 20% |
| UOM compliance rate | 15% |
| Grounding rate | 15% |

Tiers: `HIGH > 0.85`, `MEDIUM 0.60–0.85`, `LOW < 0.60`.

## Structural Completeness (1,000-row bulk)

When no labels exist, `structural_completeness()` reports honest proxies:

- `classpath_populated_pct`
- `manufacturer_populated_pct`
- `brand_populated_pct`
- `avg_attributes_per_product`
- `needs_review_pct`

## Demo Story (from plan section 18/22)

```text
200 Ground-Truth Products

Field Accuracy       XX.X%   (measured)
LOV Compliance       XX.X%   (measured)
UOM Compliance       XX.X%   (measured)
Character Compliance XX.X%   (measured)
Grounding Rate       XX.X%   (measured)
Review Rate           XX.X%   (measured)
```

## Running

```bash
# 200-row labelled evaluation
python scripts/evaluate_200.py

# 1,000-row structural report
python scripts/evaluate_1000.py
```

## Definition of Done (Y9)

- [x] 200-row evaluation works
- [x] Accuracy metrics generated
- [x] Metrics are never hardcoded in the UI