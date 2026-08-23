# Output Schema — 252-Column Delivery Format

> Exact header list is loaded from `data/reference/Unihack_ Expected Output - Delivery Format.csv`
> by `src/output/mapper.py::get_expected_headers()`. **Do not hardcode column lists
> elsewhere** — always read from the reference file.

## Column Groups (14 groups / 252 columns)

| Group | Count | Columns | Populated in 2 GT rows |
|---|---|---|---|
| Reference URLs | 6 | `MFR URL`, `Ref URL 1`..`Ref URL 5` | 1–2 |
| Identity | 5 | `PART_NUMBER`, `SKU - MY_PART_NUMBER`, `Mfg_Part_Num`, `MANUFACTURER_PART_NUMBER`, `ALTERNATE_PART_NUMBER` | 4 |
| Input Passthrough | 5 | `Part_Desc`, `E1_Brand`, `Unilog_Brand`, `DIB_Brand`, `Part_Manuf` | 5 |
| Classification | 5 | `Dept`, `Class`, `Fine`, `Classpath`, `Product Name` | 5 |
| Manufacturer / Brand | 3 | `MANUFACTURER_NAME`, `BRAND_NAME`, `TRADE_NAME` | 2 |
| Descriptions | 6 | `MOBILE_DESC`, `INVOICE_DESC`, `SHORT_DESC`, `LONG_DESC1`, `RETAIL_DESC`, `MARKETING_DESCRIPTION` | 5 |
| Features | 20 | `ITEM_FEATURES_1`..`ITEM_FEATURES_20` | 11 |
| Descriptive Extras | 5 | `With`, `Standard/Approvals`, `Prop 65`, `Application`, `Includes` | 1–2 |
| Attributes | 150 | `ATTRIBUTE_LABEL n` / `ATTRIBUTE_VALUE n` / `ATTRIBUTE_UOM n` (n = 1..50) | 45 |
| Identifiers | 4 | `UPC`, `EAN`, `GTIN`, `UNSPSC` | 0 |
| Commercial | 5 | `Warranty`, `List Price`, `Selling Qty`, `Selling UOM`, `Standard Packaging Information` | 1 |
| Dimensions | 10 | `LENGTH`, `HEIGHT`, `WIDTH`, `WEIGHT`, `VOLUME` (+ `_UOM` each) | 0 |
| Digital Assets | 25 | `Product Image`, `Alternate Image 1-4`, `Specification Sheet`, manuals, … | 2–5 |
| Metadata | 3 | `Country Of Origin`, `Discontinued`, `Actual Image (Yes/No)` | 1 |

## Serialisation Rules

1. **Every column** present in the row dict — exactly the 252 reference headers, in order.
2. **Unpopulated** → `""` (empty string). Never `None`, `"N/A"`, `"nan"`, `"None"`.
3. **`Dept` / `Class` / `Fine`** are auto-derived from `Classpath` (`Level1>Level2>Level3`)
   when not explicitly set.
4. **Attributes** map 1:1 onto the positional `ATTRIBUTE_LABEL/VALUE/UOM` slots.
5. **Digital asset filenames** are derived as `<BRAND>_<MPN>[_Suffix]` when brand+MPN exist
   (e.g. `FRIGIDAIRE_PDSH4816AF_Specification_Sheet.pdf`).
6. **`Actual Image (Yes/No)`** defaults to `Yes` when `Product Image` is populated.

## Confirmed Ground-Truth Description Samples

| Field | Frigidaire PDSH4816AF |
|---|---|
| `INVOICE_DESC` | `DISHWASHER LEG 5 SST 120V 15A 50-1/4IN` (≤ 40 chars) |
| `MOBILE_DESC` | `Rheem Manufacturing FRIGIDAIRE, Dishwasher, Professional Series, PDSH4816AF` |
| `SHORT_DESC` | `FRIGIDAIRE® Professional Series PDSH4816AF Dishwasher With CleanBoost™, Leg Moun…` |
| `LONG_DESC1` | `FRIGIDAIRE® Dishwasher With CleanBoost™, Professional Series, 5 Wash Cycles, 120…` |
| `RETAIL_DESC` | `Professional Series Dishwasher, Leg Mounting, 5-Wash Cycle, Stainless Steel` |

Content generators in `src/content/` reproduce these constructions from verified
attributes only (see `docs/field_transformation_matrix.md`).

## Interface

```python
from src.output.mapper import get_expected_headers, product_to_row

headers = get_expected_headers()            # list[str] length 252
row = product_to_row(internal_product, headers)  # dict[str, str] keyed by headers
```

Schema integrity is verified before writing by `src/output/exporter.py`.