# Field Transformation Matrix

This document specifies how each key internal field is sourced, transformed,
validated, and prioritised during pipeline processing.

> **Reference**: Unihack_ Expected Output - Delivery Format.csv (252 columns)
> **Ground Truth Rows**: Frigidaire PDSH4816AF, Whirlpool WDTS7024RZ

---

## Legend

| Symbol | Meaning |
|--------|---------|
| `[P]` | Passthrough — copied verbatim from input |
| `[N]` | Normalised — value is transformed before output |
| `[G]` | Generated — derived deterministically from other fields |
| `[E]` | Enriched — sourced from external upstream AI extraction |
| `[B]` | Blank — intentionally left empty when data is unavailable |

---

## Priority Scale

| Level | Description |
|-------|-------------|
| **P1** | Judge-critical — incorrect = guaranteed score penalty |
| **P2** | High-value — affects most scoring rubrics |
| **P3** | Medium-value — nice to have, improves completeness score |
| **P4** | Low — fills structural slots; rarely scored directly |

---

## Core Identity Fields

| Field | Purpose | Source | Transform | Validation | Priority |
|-------|---------|--------|-----------|------------|---------|
| `Mfg_Part_Num` | Manufacturer part number (primary key) | Input CSV passthrough | `[P]` none | Must not be empty | **P1** |
| `MANUFACTURER_PART_NUMBER` | Same as Mfg_Part_Num in output schema | Input CSV `Mfg_Part_Num` | `[P]` copied | Must match `Mfg_Part_Num` | **P1** |
| `MANUFACTURER_NAME` | True manufacturer (not distributor) | Upstream AI extraction | `[E]` resolved from brand/MPN lookup | Must not be `Part_Manuf` value | **P1** |
| `BRAND_NAME` | Brand name with trademark symbols verbatim | Upstream AI extraction | `[E]` preserve `®`/`™` exactly | Must not strip symbols; title-case rules apply | **P1** |
| `ALTERNATE_PART_NUMBER` | Secondary/cross-reference part number | Upstream AI extraction | `[E]` optional | Empty string if unavailable | **P3** |
| `Part_Manuf` | Distributor (NOT manufacturer) | Input CSV passthrough | `[P]` never treated as manufacturer | Must not populate `MANUFACTURER_NAME` from this | **P1** |

---

## Classification Fields

| Field | Purpose | Source | Transform | Validation | Priority |
|-------|---------|--------|-----------|------------|---------|
| `Classpath` | Full product hierarchy path | Upstream AI extraction | `[E]` `Category>Subcategory>Type` format | `>` delimited; no trailing `>` | **P1** |
| `Dept` | Top-level department | Derived from `Classpath[0]` | `[G]` split on `>` | Must match `Classpath` hierarchy | **P2** |
| `Class` | Mid-level class | Derived from `Classpath[1]` | `[G]` split on `>` | Must match `Classpath` hierarchy | **P2** |
| `Fine` | Leaf-level fine class | Derived from `Classpath[2]` | `[G]` split on `>` | Must match `Classpath` hierarchy | **P2** |

---

## Description Fields

| Field | Purpose | Source | Transform | Validation | Priority |
|-------|---------|--------|-----------|------------|---------|
| `INVOICE_DESC` | Compressed shipping label description | AI extraction + template | `[N]` ALL CAPS, compressed UOM (no space), ≤ 40 chars | Hard limit 40 chars; fail validation if exceeded | **P1** |
| `SHORT_DESC` | Customer-facing short description | AI extraction + template | `[N]` title-case; brand + series + MPN + key features | No hard char limit confirmed | **P2** |
| `LONG_DESC1` | Full technical description | AI extraction + template | `[N]` sentence case; all key attributes listed | No hard char limit confirmed | **P2** |
| `MOBILE_DESC` | Compact mobile display description | AI extraction + template | `[N]` ≤ 80 chars target; comma-separated key facts | Approx 80 chars; unchecked by validator | **P3** |
| `RETAIL_DESC` | Retailer display description | AI extraction + template | `[N]` plain prose; no brand trademark in this slot | No hard char limit confirmed | **P3** |
| `MARKETING_DESCRIPTION` | Long-form marketing copy | Upstream AI extraction | `[E]` verbatim from manufacturer | May be empty if not found | **P4** |

---

## Attribute Fields (ATTRIBUTE_LABEL/VALUE/UOM 1-50)

| Field | Purpose | Source | Transform | Validation | Priority |
|-------|---------|--------|-----------|------------|---------|
| `ATTRIBUTE_LABEL n` | Attribute name in slot n | AI extraction candidate label | `[E]` title-case; positional (slot 1..50) | Max 50 slots; unfilled slots blank | **P1** |
| `ATTRIBUTE_VALUE n` | Attribute value in slot n | AI extraction candidate value | `[N]` LOV normalisation + fraction engine for inch dims | LOV-matched or flagged for review | **P1** |
| `ATTRIBUTE_UOM n` | Unit of measure for slot n | AI extraction candidate UOM | `[N]` `normalize_uom()` → standard symbol (e.g. `in`, `V`) | Must be in approved UOM set or flagged | **P1** |

### Normalisation Rules for Attribute Values

| Value Type | Rule | Example |
|-----------|------|---------|
| Inch measurements (decimal) | `decimal_to_fraction()` via fractions.py | `50.25` → `50-1/4` |
| Inch measurements (whole number decimal) | Strip `.0` suffix | `24.0` → `24` |
| LOV-controlled fields (Material, Color, etc.) | `normalize_attribute_value()` via lov.py synonym map | `SST` → `Stainless Steel` |
| Non-LOV fields (Voltage, Sound Level) | Pass through unchanged | `120` → `120` |
| UOM symbols | `normalize_uom()` | `inches` → `in`, `volts` → `V`, `amps` → `A` |

---

## Digital Asset Fields

| Field | Purpose | Source | Transform | Validation | Priority |
|-------|---------|--------|-----------|------------|---------|
| `Product Image` | Primary product photo filename | Generated | `[G]` `{BRAND_no_symbols}_{MPN}.jpg` | Both brand and MPN must be non-empty | **P1** |
| `Specification Sheet` | Spec sheet PDF filename | Generated | `[G]` `{BRAND_no_symbols}_{MPN}_Specification_Sheet.pdf` | Both brand and MPN must be non-empty | **P1** |
| `Alternate Image 1-4` | Additional image filenames | AI extraction or empty | `[E]` or `[B]`; do NOT auto-generate if not provided | Must not auto-generate without explicit upstream data | **P3** |

### Brand Symbol Stripping Rule (Digital Assets Only)

```
FRIGIDAIRE® → FRIGIDAIRE
Whirlpool®  → Whirlpool
```
Symbols stripped: `®`, `™`, `©`

---

## Reference & URL Fields

| Field | Purpose | Source | Transform | Validation | Priority |
|-------|---------|--------|-----------|------------|---------|
| `MFR URL` | Manufacturer product page URL | AI extraction | `[E]` verbatim | Must be a valid URL format if populated | **P2** |
| `Ref URL 1-4` | Supporting reference URLs | AI extraction | `[E]` verbatim (e.g. manual PDFs, install guides) | Empty string if not found | **P3** |

---

## Commercial & Metadata Fields

| Field | Purpose | Source | Transform | Validation | Priority |
|-------|---------|--------|-----------|------------|---------|
| `Country Of Origin` | Manufacturing country | AI extraction | `[E]` verbatim | Empty string if unavailable | **P4** |
| `Discontinued` | Discontinuation flag | AI extraction | `[E]` boolean or empty | `Yes`/`No`/`""` | **P4** |
| `Actual Image (Yes/No)` | Whether real image was found | Generated from asset pipeline | `[G]` `Yes` if `Product Image` populated, else `No` | Must be consistent with `Product Image` field | **P3** |
| `Warranty` | Warranty terms string | AI extraction | `[E]` verbatim | Empty string if unavailable | **P3** |

---

## Input Passthrough Fields

These columns are copied verbatim from the input CSV without modification.

| Field | Notes |
|-------|-------|
| `PART_NUMBER` | Internal system ID |
| `SKU - MY_PART_NUMBER` | Internal SKU |
| `Mfg_Part_Num` | Raw MPN from input |
| `Part_Desc` | Raw part description from input |
| `E1_Brand` | Placeholder — treat as null (`-- Unbranded --`) |
| `Unilog_Brand` | Placeholder — treat as null (`-- No Unilog Brand --`) |
| `DIB_Brand` | Placeholder — treat as null (`-- No DIB Brand --`) |
| `Part_Manuf` | Distributor — never use as manufacturer source |

---

## Key Confirmed Constraints (from Ground Truth)

| Constraint | Source | Detail |
|-----------|--------|--------|
| `INVOICE_DESC` ≤ 40 chars | Ground truth rows | Hard limit; validator enforces |
| `BRAND_NAME` preserves `®`/`™` | Ground truth rows | `FRIGIDAIRE®`, `Whirlpool®` |
| Digital asset filenames strip symbols | Ground truth rows | `FRIGIDAIRE_PDSH4816AF.jpg` not `FRIGIDAIRE®_...` |
| INVOICE_DESC uses compressed UOM | Ground truth rows | `120V`, `15A`, `50-1/4IN` — no spaces |
| Standard attribute UOM uses space | Ground truth rows | `120 V`, `47 dBA`, `24 in` |
| Fraction format for inch dims | Ground truth rows | `50-1/4`, `33-7/16`, `22-5/8` |
| Attribute slots are positional 1..50 | Spec | Order = order attributes appear in `product["attributes"]` |
| `Part_Manuf` is distributor not mfr | Ground truth analysis | `Appliance Dealers Cooperative (APPDE)` |
