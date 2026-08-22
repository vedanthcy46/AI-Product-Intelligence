# Dataset Map — UniHack 200/1000 Row Catalogue

## Input Dataset

_File_: `data/raw/Unihack_ Sample Dataset - Input.csv`

| Rows | Columns | Source |
|---|---|---|
| 1,000 (working) / 200 (labelled evaluation subset) | 6 | Raw industrial distributor catalogue |

### Input Columns

| Column | Example | Meaning | Cleaning |
|---|---|---|---|
| `Mfg_Part_Num` | `PDSH4816AF` | Manufacturer part number | Trim; empty → `None` |
| `Part_Desc` | `PDSH4816AF Dishwasher SS - Display Only` | Raw catalogue description, heavily abbreviated | Trim; never expanded for output |
| `E1_Brand` | `-- Unbranded --` | Brand signal 1 | Placeholder → `None` |
| `Unilog_Brand` | `-- No Unilog Brand --` | Brand signal 2 (priority 1) | Placeholder → `None` |
| `DIB_Brand` | `-- No DIB Brand --` | Brand signal 3 | Placeholder → `None` |
| `Part_Manuf` | `Appliance Dealers Cooperative (APPDE)` | Manufacturer signal (priority 1) | Trim |

**Placeholder values treated as empty**: `-- Unbranded --`, `-- No Unilog Brand --`,
`-- No DIB Brand --`, `-- No E1 Brand --`, `n/a`, `none`, empty string.

**Brand priority**: `Unilog_Brand` > `E1_Brand` > `DIB_Brand`
**Manufacturer priority**: `Part_Manuf` > best brand signal

### Data Reality (from 1000 rows)

- **76 unique `Part_Manuf` values** — dominated by Phillips Lighting (111), Milwaukee
  Accessory (108), Boise Cascade (85), Appliance Dealers Cooperative (84).
- **`-` (hyphen) used as a real manufacturer value** in 41 rows — must be resolved or
  flagged, not dropped silently.
- **Duplicate MPNs exist in source data** (e.g. `AVM6EV` appears twice with different
  descriptions) — an upstream data-entry issue, passed through faithfully.
- Descriptions are highly abbreviated and category-diverse:

  | # | Part_Desc |
  |---|---|
  | 1 | `586891 Led 60W Med A19 27k` |
  | 2 | `3/8 CPLG BRS 150#` |
  | 3 | `52485 52" MB Anisten Fan` |
  | 4 | `1x6-20' American Walnut Sq Edg - Landmark Azek PVC Decking` |
  | 5 | `Wh 4x4-39 Blank Post RDI` |

---

## Delivery Output Dataset

_File_: `data/reference/Unihack_ Expected Output - Delivery Format.csv`

| Rows | Columns |
|---|---|
| 2 (labelled ground truth) | 252 |

The 252 columns are grouped in `docs/field_groups.md`. The pipeline must:

1. Preserve exact header names and column order (see `docs/output_schema.md`).
2. Write empty string `""` for unpopulated fields (never `None`, `N/A`, or `nan`).
3. Map the internal `Product` representation, not the 252 columns directly
   (per the plan's "Important Principle", section 2).

---

## Evaluation Dataset

_File_: `data/reference/Unilog-Sample_200_Items-Input-vs-Output.xlsx`

200 labelled input→output rows used by `src/evaluation/` to measure field
accuracy, LOV/UOM compliance, grounding, and review rate.

---

## Internal Product Model

```text
Product
├── Identity            (mfg_part_num, part_desc, brands, part_manuf, row_id)
├── Manufacturer        (manufacturer_name, manufacturer_code, confidence)
├── Brand               (brand_name, brand_code, confidence)
├── Classification      (dept, class_name, fine, classpath, confidence)
├── Attributes          [ {label, value, uom, source, source_page, confidence,
                           lov_matched, needs_review} ]
├── Descriptions        (MOBILE_DESC, INVOICE_DESC, SHORT_DESC, LONG_DESC1,
                          RETAIL_DESC, MARKETING_DESCRIPTION)
├── Features            [ ITEM_FEATURES_1 .. ITEM_FEATURES_20 ]
├── Sources             (MFR URL, Ref URL 1-5)
├── Confidence          (overall_confidence, status, needs_review, review_reasons)
├── Validation          (valid, lov/uom/grounding rates, char compliance)
└── Review Status       (accept / edit / reject)
```

This internal model is serialised into the 252-column delivery format only at the
final output step (`src/output/mapper.py`).