# Field Groups — UniHack 252-Column Output Schema

> Auto-generated from ground-truth rows. **Do not edit manually.**

_Input file_: `Unihack_ Sample Dataset - Input.csv` — 1000 rows, 6 cols  
_Output file_: `Unihack_ Expected Output - Delivery Format.csv` — 2 rows, 252 cols

## Column Groups

| Group | Count | Column Names (truncated if long) | Population in 2 real rows |
|---|---|---|---|
| **Reference URLs** | 6 | `MFR URL`, `Ref URL 1`, `Ref URL 2`, `Ref URL 3`, `Ref URL 4`, `Ref URL 5` | 1 filled in both rows; 3 blank in both rows |
| **Identity** | 5 | `PART_NUMBER`, `SKU - MY_PART_NUMBER`, `Mfg_Part_Num`, `MANUFACTURER_PART_NUMBER`, `ALTERNATE_PART_NUMBER` | 4 filled in both rows; 1 blank in both rows |
| **Input Passthrough** | 5 | `Part_Desc`, `E1_Brand`, `Unilog_Brand`, `DIB_Brand`, `Part_Manuf` | 5 filled in both rows |
| **Classification** | 5 | `Dept`, `Class`, `Fine`, `Classpath`, `Product Name` | 5 filled in both rows |
| **Manufacturer / Brand** | 3 | `MANUFACTURER_NAME`, `BRAND_NAME`, `TRADE_NAME` | 2 filled in both rows; 1 blank in both rows |
| **Descriptions** | 6 | `MOBILE_DESC`, `INVOICE_DESC`, `SHORT_DESC`, `LONG_DESC1`, `RETAIL_DESC`, `MARKETING_DESCRIPTION` | 5 filled in both rows |
| **Features** | 20 | `ITEM_FEATURES_1`, `ITEM_FEATURES_2`, `ITEM_FEATURES_3`, `ITEM_FEATURES_4`, `ITEM_FEATURES_5`, … (+15 more) | 9 blank in both rows |
| **Descriptive Extras** | 5 | `With`, `Standard/Approvals`, `Prop 65`, `Application`, `Includes` | 1 filled in both rows; 3 blank in both rows |
| **Attributes** | 150 | `ATTRIBUTE_LABEL 1`, `ATTRIBUTE_VALUE 1`, `ATTRIBUTE_UOM 1`, `ATTRIBUTE_LABEL 2`, `ATTRIBUTE_VALUE 2`, … (+145 more) | 29 filled in both rows; 117 blank in both rows |
| **Identifiers** | 4 | `UPC`, `EAN`, `GTIN`, `UNSPSC` | 4 blank in both rows |
| **Commercial** | 5 | `Warranty`, `List Price`, `Selling Qty`, `Selling UOM`, `Standard Packaging Information` | 4 blank in both rows |
| **Dimensions** | 10 | `LENGTH`, `LENGTH_UOM`, `HEIGHT`, `HEIGHT_UOM`, `WIDTH`, … (+5 more) | 10 blank in both rows |
| **Digital Assets** | 25 | `Product Image`, `Alternate Image 1`, `Alternate Image 2`, `Alternate Image 3`, `Alternate Image 4`, … (+20 more) | 2 filled in both rows; 19 blank in both rows |
| **Metadata** | 3 | `Country Of Origin`, `Discontinued`, `Actual Image (Yes/No)` | 1 filled in both rows; 2 blank in both rows |

**Total: 252 columns assigned across 14 groups**

---

## Detailed Group Breakdown

### Reference URLs (6 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `MFR URL` | ✅ | ✅ | `https://www.frigidaire.com/en/p/owner-center/product-support/PDSH4816AF` |
| `Ref URL 1` | — | ✅ | `https://www.whirlpool.com/content/dam/global/documents/202412/owners-manual-w113` |
| `Ref URL 2` | — | ✅ | `https://www.whirlpool.com/content/dam/global/documents/202406/installation-instr` |
| `Ref URL 3` | — | — | `` |
| `Ref URL 4` | — | — | `` |
| `Ref URL 5` | — | — | `` |

### Identity (5 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `PART_NUMBER` | ✅ | ✅ | `20887830` |
| `SKU - MY_PART_NUMBER` | ✅ | ✅ | `1515863` |
| `Mfg_Part_Num` | ✅ | ✅ | `PDSH4816AF` |
| `MANUFACTURER_PART_NUMBER` | ✅ | ✅ | `PDSH4816AF` |
| `ALTERNATE_PART_NUMBER` | — | — | `` |

### Input Passthrough (5 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `Part_Desc` | ✅ | ✅ | `PDSH4816AF Dishwasher SS - Display Only` |
| `E1_Brand` | ✅ | ✅ | `-- Unbranded --` |
| `Unilog_Brand` | ✅ | ✅ | `-- No Unilog Brand --` |
| `DIB_Brand` | ✅ | ✅ | `-- No DIB Brand --` |
| `Part_Manuf` | ✅ | ✅ | `Appliance Dealers Cooperative (APPDE)` |

### Classification (5 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `Dept` | ✅ | ✅ | `Appliances` |
| `Class` | ✅ | ✅ | `Large Appliances` |
| `Fine` | ✅ | ✅ | `Dishwashers` |
| `Classpath` | ✅ | ✅ | `Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers` |
| `Product Name` | ✅ | ✅ | `Dishwasher` |

### Manufacturer / Brand (3 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `MANUFACTURER_NAME` | ✅ | ✅ | `Rheem Manufacturing` |
| `BRAND_NAME` | ✅ | ✅ | `FRIGIDAIRE®` |
| `TRADE_NAME` | — | — | `` |

### Descriptions (6 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `MOBILE_DESC` | ✅ | ✅ | `Rheem Manufacturing FRIGIDAIRE, Dishwasher, Professional Series, PDSH4816AF` |
| `INVOICE_DESC` | ✅ | ✅ | `DISHWASHER LEG 5 SST 120V 15A 50-1/4IN` |
| `SHORT_DESC` | ✅ | ✅ | `FRIGIDAIRE® Professional Series PDSH4816AF Dishwasher With CleanBoost™, Leg Moun` |
| `LONG_DESC1` | ✅ | ✅ | `FRIGIDAIRE® Dishwasher With CleanBoost™, Professional Series, 5 Wash Cycles, 120` |
| `RETAIL_DESC` | ✅ | ✅ | `Professional Series Dishwasher, Leg Mounting, 5-Wash Cycle, Stainless Steel` |
| `MARKETING_DESCRIPTION` | — | ✅ | `Load more and run less with our quietest and largest capacity dishwasher. A 3rd ` |

### Features (20 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `ITEM_FEATURES_1` | — | ✅ | `3rd rack with extra wash action` |
| `ITEM_FEATURES_2` | — | ✅ | `Adjustable 2nd Rack` |
| `ITEM_FEATURES_3` | — | ✅ | `41 dBA` |
| `ITEM_FEATURES_4` | — | ✅ | `Moisture Repellent Silverware Basket` |
| `ITEM_FEATURES_5` | — | ✅ | `Sensor cycle` |
| `ITEM_FEATURES_6` | — | ✅ | `Sani Rinse Option` |
| `ITEM_FEATURES_7` | — | ✅ | `Leak Detection System` |
| `ITEM_FEATURES_8` | — | ✅ | `Folding Tines` |
| `ITEM_FEATURES_9` | — | ✅ | `Normal cycle` |
| `ITEM_FEATURES_10` | — | ✅ | `Triple Wash Spray` |
| `ITEM_FEATURES_11` | — | ✅ | `Quick Wash Cycle` |
| `ITEM_FEATURES_12` | — | — | `` |
| `ITEM_FEATURES_13` | — | — | `` |
| `ITEM_FEATURES_14` | — | — | `` |
| `ITEM_FEATURES_15` | — | — | `` |
| `ITEM_FEATURES_16` | — | — | `` |
| `ITEM_FEATURES_17` | — | — | `` |
| `ITEM_FEATURES_18` | — | — | `` |
| `ITEM_FEATURES_19` | — | — | `` |
| `ITEM_FEATURES_20` | — | — | `` |

### Descriptive Extras (5 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `With` | ✅ | ✅ | `With CleanBoost™` |
| `Standard/Approvals` | ✅ | — | `ASSE 1006\|CEE Tier 2 Qualified\|cUL Listed\|ENERGY STAR Certified\|NSF Certified\|UL` |
| `Prop 65` | — | — | `` |
| `Application` | — | — | `` |
| `Includes` | — | — | `` |

### Attributes (150 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `ATTRIBUTE_LABEL 1` | ✅ | ✅ | `Series` |
| `ATTRIBUTE_VALUE 1` | ✅ | ✅ | `Professional Series` |
| `ATTRIBUTE_UOM 1` | — | — | `` |
| `ATTRIBUTE_LABEL 2` | ✅ | ✅ | `Model` |
| `ATTRIBUTE_VALUE 2` | — | — | `` |
| `ATTRIBUTE_UOM 2` | — | — | `` |
| `ATTRIBUTE_LABEL 3` | ✅ | ✅ | `Number of Wash Cycles` |
| `ATTRIBUTE_VALUE 3` | ✅ | — | `5.0` |
| `ATTRIBUTE_UOM 3` | — | — | `` |
| `ATTRIBUTE_LABEL 4` | ✅ | ✅ | `Voltage Rating` |
| `ATTRIBUTE_VALUE 4` | ✅ | ✅ | `120` |
| `ATTRIBUTE_UOM 4` | ✅ | ✅ | `V` |
| `ATTRIBUTE_LABEL 5` | ✅ | ✅ | `Amperage Rating` |
| `ATTRIBUTE_VALUE 5` | ✅ | ✅ | `15` |
| `ATTRIBUTE_UOM 5` | ✅ | ✅ | `A` |
| `ATTRIBUTE_LABEL 6` | ✅ | ✅ | `Mounting Type` |
| `ATTRIBUTE_VALUE 6` | ✅ | ✅ | `Leg` |
| `ATTRIBUTE_UOM 6` | — | — | `` |
| `ATTRIBUTE_LABEL 7` | ✅ | ✅ | `Plug Type` |
| `ATTRIBUTE_VALUE 7` | — | — | `` |
| `ATTRIBUTE_UOM 7` | — | — | `` |
| `ATTRIBUTE_LABEL 8` | ✅ | ✅ | `Size` |
| `ATTRIBUTE_VALUE 8` | ✅ | ✅ | `24 in W x 24-1/4 in D` |
| `ATTRIBUTE_UOM 8` | — | — | `` |
| `ATTRIBUTE_LABEL 9` | ✅ | ✅ | `Depth With Door Open` |
| `ATTRIBUTE_VALUE 9` | ✅ | ✅ | `50-1/4` |
| `ATTRIBUTE_UOM 9` | ✅ | ✅ | `in` |
| `ATTRIBUTE_LABEL 10` | ✅ | ✅ | `Minimum Height` |
| `ATTRIBUTE_VALUE 10` | ✅ | ✅ | `8-1/2 in Upper Rack, 11-1/4 in Lower Rack` |
| `ATTRIBUTE_UOM 10` | — | ✅ | `in` |
| `ATTRIBUTE_LABEL 11` | ✅ | ✅ | `Maximum Height` |
| `ATTRIBUTE_VALUE 11` | ✅ | — | `10-3/8 in Upper Rack, 13-1/4 in Lower Rack` |
| `ATTRIBUTE_UOM 11` | — | — | `` |
| `ATTRIBUTE_LABEL 12` | ✅ | ✅ | `Sound Level` |
| `ATTRIBUTE_VALUE 12` | ✅ | ✅ | `47` |
| `ATTRIBUTE_UOM 12` | ✅ | ✅ | `dBA` |
| `ATTRIBUTE_LABEL 13` | ✅ | ✅ | `Material` |
| `ATTRIBUTE_VALUE 13` | ✅ | ✅ | `Stainless Steel` |
| `ATTRIBUTE_UOM 13` | — | — | `` |
| `ATTRIBUTE_LABEL 14` | ✅ | ✅ | `Color` |
| `ATTRIBUTE_VALUE 14` | — | ✅ | `Stainless Steel` |
| `ATTRIBUTE_UOM 14` | — | — | `` |
| `ATTRIBUTE_LABEL 15` | ✅ | ✅ | `Additional Information` |
| `ATTRIBUTE_VALUE 15` | ✅ | ✅ | `240 kW-hr Annual Energy, 1 to 12 hr Delay Start Hours` |
| `ATTRIBUTE_UOM 15` | — | — | `` |
| `ATTRIBUTE_LABEL 16` | — | — | `` |
| `ATTRIBUTE_VALUE 16` | — | — | `` |
| `ATTRIBUTE_UOM 16` | — | — | `` |
| `ATTRIBUTE_LABEL 17` | — | — | `` |
| `ATTRIBUTE_VALUE 17` | — | — | `` |
| `ATTRIBUTE_UOM 17` | — | — | `` |
| `ATTRIBUTE_LABEL 18` | — | — | `` |
| `ATTRIBUTE_VALUE 18` | — | — | `` |
| `ATTRIBUTE_UOM 18` | — | — | `` |
| `ATTRIBUTE_LABEL 19` | — | — | `` |
| `ATTRIBUTE_VALUE 19` | — | — | `` |
| `ATTRIBUTE_UOM 19` | — | — | `` |
| `ATTRIBUTE_LABEL 20` | — | — | `` |
| `ATTRIBUTE_VALUE 20` | — | — | `` |
| `ATTRIBUTE_UOM 20` | — | — | `` |
| `ATTRIBUTE_LABEL 21` | — | — | `` |
| `ATTRIBUTE_VALUE 21` | — | — | `` |
| `ATTRIBUTE_UOM 21` | — | — | `` |
| `ATTRIBUTE_LABEL 22` | — | — | `` |
| `ATTRIBUTE_VALUE 22` | — | — | `` |
| `ATTRIBUTE_UOM 22` | — | — | `` |
| `ATTRIBUTE_LABEL 23` | — | — | `` |
| `ATTRIBUTE_VALUE 23` | — | — | `` |
| `ATTRIBUTE_UOM 23` | — | — | `` |
| `ATTRIBUTE_LABEL 24` | — | — | `` |
| `ATTRIBUTE_VALUE 24` | — | — | `` |
| `ATTRIBUTE_UOM 24` | — | — | `` |
| `ATTRIBUTE_LABEL 25` | — | — | `` |
| `ATTRIBUTE_VALUE 25` | — | — | `` |
| `ATTRIBUTE_UOM 25` | — | — | `` |
| `ATTRIBUTE_LABEL 26` | — | — | `` |
| `ATTRIBUTE_VALUE 26` | — | — | `` |
| `ATTRIBUTE_UOM 26` | — | — | `` |
| `ATTRIBUTE_LABEL 27` | — | — | `` |
| `ATTRIBUTE_VALUE 27` | — | — | `` |
| `ATTRIBUTE_UOM 27` | — | — | `` |
| `ATTRIBUTE_LABEL 28` | — | — | `` |
| `ATTRIBUTE_VALUE 28` | — | — | `` |
| `ATTRIBUTE_UOM 28` | — | — | `` |
| `ATTRIBUTE_LABEL 29` | — | — | `` |
| `ATTRIBUTE_VALUE 29` | — | — | `` |
| `ATTRIBUTE_UOM 29` | — | — | `` |
| `ATTRIBUTE_LABEL 30` | — | — | `` |
| `ATTRIBUTE_VALUE 30` | — | — | `` |
| `ATTRIBUTE_UOM 30` | — | — | `` |
| `ATTRIBUTE_LABEL 31` | — | — | `` |
| `ATTRIBUTE_VALUE 31` | — | — | `` |
| `ATTRIBUTE_UOM 31` | — | — | `` |
| `ATTRIBUTE_LABEL 32` | — | — | `` |
| `ATTRIBUTE_VALUE 32` | — | — | `` |
| `ATTRIBUTE_UOM 32` | — | — | `` |
| `ATTRIBUTE_LABEL 33` | — | — | `` |
| `ATTRIBUTE_VALUE 33` | — | — | `` |
| `ATTRIBUTE_UOM 33` | — | — | `` |
| `ATTRIBUTE_LABEL 34` | — | — | `` |
| `ATTRIBUTE_VALUE 34` | — | — | `` |
| `ATTRIBUTE_UOM 34` | — | — | `` |
| `ATTRIBUTE_LABEL 35` | — | — | `` |
| `ATTRIBUTE_VALUE 35` | — | — | `` |
| `ATTRIBUTE_UOM 35` | — | — | `` |
| `ATTRIBUTE_LABEL 36` | — | — | `` |
| `ATTRIBUTE_VALUE 36` | — | — | `` |
| `ATTRIBUTE_UOM 36` | — | — | `` |
| `ATTRIBUTE_LABEL 37` | — | — | `` |
| `ATTRIBUTE_VALUE 37` | — | — | `` |
| `ATTRIBUTE_UOM 37` | — | — | `` |
| `ATTRIBUTE_LABEL 38` | — | — | `` |
| `ATTRIBUTE_VALUE 38` | — | — | `` |
| `ATTRIBUTE_UOM 38` | — | — | `` |
| `ATTRIBUTE_LABEL 39` | — | — | `` |
| `ATTRIBUTE_VALUE 39` | — | — | `` |
| `ATTRIBUTE_UOM 39` | — | — | `` |
| `ATTRIBUTE_LABEL 40` | — | — | `` |
| `ATTRIBUTE_VALUE 40` | — | — | `` |
| `ATTRIBUTE_UOM 40` | — | — | `` |
| `ATTRIBUTE_LABEL 41` | — | — | `` |
| `ATTRIBUTE_VALUE 41` | — | — | `` |
| `ATTRIBUTE_UOM 41` | — | — | `` |
| `ATTRIBUTE_LABEL 42` | — | — | `` |
| `ATTRIBUTE_VALUE 42` | — | — | `` |
| `ATTRIBUTE_UOM 42` | — | — | `` |
| `ATTRIBUTE_LABEL 43` | — | — | `` |
| `ATTRIBUTE_VALUE 43` | — | — | `` |
| `ATTRIBUTE_UOM 43` | — | — | `` |
| `ATTRIBUTE_LABEL 44` | — | — | `` |
| `ATTRIBUTE_VALUE 44` | — | — | `` |
| `ATTRIBUTE_UOM 44` | — | — | `` |
| `ATTRIBUTE_LABEL 45` | — | — | `` |
| `ATTRIBUTE_VALUE 45` | — | — | `` |
| `ATTRIBUTE_UOM 45` | — | — | `` |
| `ATTRIBUTE_LABEL 46` | — | — | `` |
| `ATTRIBUTE_VALUE 46` | — | — | `` |
| `ATTRIBUTE_UOM 46` | — | — | `` |
| `ATTRIBUTE_LABEL 47` | — | — | `` |
| `ATTRIBUTE_VALUE 47` | — | — | `` |
| `ATTRIBUTE_UOM 47` | — | — | `` |
| `ATTRIBUTE_LABEL 48` | — | — | `` |
| `ATTRIBUTE_VALUE 48` | — | — | `` |
| `ATTRIBUTE_UOM 48` | — | — | `` |
| `ATTRIBUTE_LABEL 49` | — | — | `` |
| `ATTRIBUTE_VALUE 49` | — | — | `` |
| `ATTRIBUTE_UOM 49` | — | — | `` |
| `ATTRIBUTE_LABEL 50` | — | — | `` |
| `ATTRIBUTE_VALUE 50` | — | — | `` |
| `ATTRIBUTE_UOM 50` | — | — | `` |

### Identifiers (4 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `UPC` | — | — | `` |
| `EAN` | — | — | `` |
| `GTIN` | — | — | `` |
| `UNSPSC` | — | — | `` |

### Commercial (5 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `Warranty` | ✅ | — | `1 Year Manufacturer, 1 Year Labor and Parts` |
| `List Price` | — | — | `` |
| `Selling Qty` | — | — | `` |
| `Selling UOM` | — | — | `` |
| `Standard Packaging Information` | — | — | `` |

### Dimensions (10 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `LENGTH` | — | — | `` |
| `LENGTH_UOM` | — | — | `` |
| `HEIGHT` | — | — | `` |
| `HEIGHT_UOM` | — | — | `` |
| `WIDTH` | — | — | `` |
| `WIDTH_UOM` | — | — | `` |
| `WEIGHT` | — | — | `` |
| `WEIGHT_UOM` | — | — | `` |
| `VOLUME` | — | — | `` |
| `VOLUME_UOM` | — | — | `` |

### Digital Assets (25 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `Product Image` | ✅ | ✅ | `FRIGIDAIRE_PDSH4816AF.jpg` |
| `Alternate Image 1` | ✅ | — | `FRIGIDAIRE_PDSH4816AF_1.jpg` |
| `Alternate Image 2` | ✅ | — | `FRIGIDAIRE_PDSH4816AF_2.jpg` |
| `Alternate Image 3` | ✅ | — | `FRIGIDAIRE_PDSH4816AF_3.jpg` |
| `Alternate Image 4` | ✅ | — | `FRIGIDAIRE_PDSH4816AF_4.jpg` |
| `SDS` | — | — | `` |
| `SDS_1` | — | — | `` |
| `Warranty Information` | — | — | `` |
| `Catalog` | — | — | `` |
| `Specification Sheet` | ✅ | ✅ | `FRIGIDAIRE_PDSH4816AF_Specification_Sheet.pdf` |
| `Instruction/Installation Manual` | — | — | `` |
| `Service Manual` | — | — | `` |
| `Owners/User Manual` | — | — | `` |
| `Line Drawing` | — | — | `` |
| `MTR` | — | — | `` |
| `RoHS` | — | — | `` |
| `Full Engineering Drawing` | — | — | `` |
| `Energy Star Guide` | — | — | `` |
| `Technical Bulletin` | — | — | `` |
| `Submittal` | — | — | `` |
| `Compatibility Chart` | — | — | `` |
| `Size Chart` | — | — | `` |
| `Product Label/Insert` | — | — | `` |
| `Video Link` | — | — | `` |
| `Video Link 1` | — | — | `` |

### Metadata (3 columns)

| Column | Filled Row 1 (Frigidaire) | Filled Row 2 (Whirlpool) | Sample Value |
|---|---|---|---|
| `Country Of Origin` | — | — | `` |
| `Discontinued` | — | — | `` |
| `Actual Image (Yes/No)` | ✅ | ✅ | `Yes` |

---

## Data Reality Check — Input Analysis

_Source_: `Unihack_ Sample Dataset - Input.csv` (1000 rows, 6 columns)

### Manufacturer Distribution

**Unique `Part_Manuf` values: 76**

| Rank | Part_Manuf | Count |
|---|---|---|
| 1 | Phillips Lighting (5831) | 111 |
| 2 | Milwaukee Accessory (4031) | 108 |
| 3 | Boise Cascade Building Materials (BOICA) | 85 |
| 4 | Appliance Dealers Cooperative (APPDE) | 84 |
| 5 | Kichler Lighting (KICLI) | 56 |
| 6 | Parksite (6151) | 55 |
| 7 | Black & Decker/dewlt (2585) | 55 |
| 8 | Freud Inc (2435) | 46 |
| 9 | U S Lumber (3073) | 43 |
| 10 | - | 41 |
| 11 | Satco Prod Inc (5573) | 41 |
| 12 | Makita Usa Inc (5142) | 23 |
| 13 | Southwire/g Turner (6603) | 19 |
| 14 | Leviton Mfg Co (4927) | 17 |
| 15 | Festool USA (FESTO) | 16 |

### Sample Part_Desc Strings (20 diverse examples)

| # | Part_Desc |
|---|---|
| 1 | 586891 Led 60W Med A19 27k |
| 2 | M200G-21L Milw M12 Gray - Heated Hoodie Kit L |
| 3 | 48-11-2330 Milw Heated Gear Power Source |
| 4 | GNE27JYMFS GE Fridge SS |
| 5 | HLSMS9129FS1E 9" Motion Lt |
| 6 | 52485 52" MB Anisten Fan |
| 7 | C7CDABS4RW3 Café Coffee Maker MW |
| 8 | 575217 60W Led Med 50k 2pk |
| 9 | 191V02-0 Makita #2 Phillips Bit 5pk |
| 10 | 1x6-20' American Walnut Sq Edg - Landmark Azek PVC Decking |
| 11 | 3401-20 Milw M12 Drill Driver - Brushless Compact (Bare) |
| 12 | WKE100HWA LG Laundry Center Wh - Display |
| 13 | SMC2266KS Microwave SS Display Only |
| 14 | 48-59-1211 Milw Power Supply - Charger |
| 15 | KPTCS450A Kreg 20V Ionic 4-1/2" Circ Saw |
| 16 | 578802 Festool 80x133 S GR PRO/10 |
| 17 | Wh 4x4-39 Blank Post RDI |
| 18 | DCG460B Dewalt 60V Grinder - 7-9" |
| 19 | 25168 Mason Line Brd Green - 250' |
| 20 | 8' Premier Rib XL Black |

---

> **Pipeline Constraint**
>
> Input spans multiple product categories across ~76 manufacturers — pipeline must be
> category-agnostic, not built around one fixed vertical.
> Attribute labels, UOMs, classpaths, and description formats will vary
> significantly per product type. All normalization rules must be generic and
> data-driven, not hardcoded to any single category schema.
