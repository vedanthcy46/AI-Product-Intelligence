"""
mapper.py -- Serializer from internal Product data model to 252-column delivery format.

Guarantees 100% exact column header alignment against the official ground-truth delivery format.
Unpopulated fields are written as empty string "" (never "N/A" or "None").
"""

import os
import re
import pandas as pd
from typing import Dict, List, Optional, Any

EXPECTED_OUTPUT_CSV = r"C:\Users\Yashas BR\OneDrive\Desktop\Hack2skills\data\reference\Unihack_ Expected Output - Delivery Format.csv"

_CACHED_HEADERS: Optional[List[str]] = None


def get_expected_headers(headers_path: Optional[str] = None) -> List[str]:
    """
    Load the exact 252-column header list directly from the delivery format reference file.
    Caches the headers in memory.
    """
    global _CACHED_HEADERS
    if _CACHED_HEADERS is not None and headers_path is None:
        return _CACHED_HEADERS

    path = headers_path or EXPECTED_OUTPUT_CSV
    if not os.path.exists(path):
        raise FileNotFoundError(f"Reference delivery format not found at: {path}")

    df = pd.read_csv(path, nrows=0, encoding="utf-8")
    headers = df.columns.tolist()
    if headers_path is None:
        _CACHED_HEADERS = headers
    return headers


def clean_brand_for_filename(brand_name: str) -> str:
    """
    Strip trademark / registered symbols from brand name for asset filenames.
    E.g. "FRIGIDAIRE®" -> "FRIGIDAIRE", "Whirlpool®" -> "Whirlpool"
    """
    if not brand_name:
        return ""
    # Remove registered trademark, trademark, copyright symbols
    cleaned = re.sub(r"[®™©®™©]", "", brand_name)
    # Remove unwanted punctuation and trim
    cleaned = cleaned.strip()
    return cleaned


def product_to_row(product: Dict[str, Any], headers: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Map an internal product dict into an exact 252-column row dict matching the delivery format.

    Parameters
    ----------
    product : dict
        Internal product representation (from schema.Product or candidate extraction).
    headers : list of str, optional
        Pre-loaded exact 252 column header list.

    Returns
    -------
    dict
        Dictionary keyed by all 252 columns with normalized string values (empty string for unpopulated).
    """
    if headers is None:
        headers = get_expected_headers()

    # Initialise all 252 columns to empty string ""
    row: Dict[str, str] = {h: "" for h in headers}

    # ── 1. Reference URLs ───────────────────────────────────────────────────
    if "MFR URL" in row:
        row["MFR URL"] = str(product.get("mfr_url") or product.get("MFR URL") or "").strip()
    for i in range(1, 6):
        k = f"Ref URL {i}"
        if k in row:
            row[k] = str(product.get(f"ref_url_{i}") or product.get(k) or "").strip()

    # ── 2. Identity & Passthrough ───────────────────────────────────────────
    mpn = (
        product.get("mfg_part_num")
        or product.get("Mfg_Part_Num")
        or product.get("manufacturer_part_number")
        or product.get("MANUFACTURER_PART_NUMBER")
        or ""
    )
    mpn = str(mpn).strip()

    if "PART_NUMBER" in row:
        row["PART_NUMBER"] = str(product.get("part_number") or product.get("PART_NUMBER") or "").strip()
    if "SKU - MY_PART_NUMBER" in row:
        row["SKU - MY_PART_NUMBER"] = str(product.get("sku") or product.get("SKU - MY_PART_NUMBER") or "").strip()
    if "Mfg_Part_Num" in row:
        row["Mfg_Part_Num"] = mpn
    if "MANUFACTURER_PART_NUMBER" in row:
        row["MANUFACTURER_PART_NUMBER"] = mpn
    if "ALTERNATE_PART_NUMBER" in row:
        row["ALTERNATE_PART_NUMBER"] = str(product.get("alternate_part_number") or product.get("ALTERNATE_PART_NUMBER") or "").strip()

    if "Part_Desc" in row:
        row["Part_Desc"] = str(product.get("part_desc") or product.get("Part_Desc") or "").strip()
    if "E1_Brand" in row:
        row["E1_Brand"] = str(product.get("e1_brand") or product.get("E1_Brand") or "-- Unbranded --").strip()
    if "Unilog_Brand" in row:
        row["Unilog_Brand"] = str(product.get("unilog_brand") or product.get("Unilog_Brand") or "-- No Unilog Brand --").strip()
    if "DIB_Brand" in row:
        row["DIB_Brand"] = str(product.get("dib_brand") or product.get("DIB_Brand") or "-- No DIB Brand --").strip()
    if "Part_Manuf" in row:
        row["Part_Manuf"] = str(product.get("part_manuf") or product.get("Part_Manuf") or "").strip()

    # ── 3. Classification ───────────────────────────────────────────────────
    classpath_val = str(product.get("classpath") or product.get("Classpath") or "").strip()
    if "Classpath" in row:
        row["Classpath"] = classpath_val

    # Auto-derive Dept / Class / Fine from Classpath when not explicitly set.
    # Classpath format: "Level1>Level2>Level3" (e.g. "Appliances>Kitchen>Dishwashers")
    cp_parts = [p.strip() for p in classpath_val.split(">") if p.strip()] if classpath_val else []

    if "Dept" in row:
        explicit = str(product.get("dept") or product.get("Dept") or "").strip()
        row["Dept"] = explicit or (cp_parts[0] if len(cp_parts) >= 1 else "")
    if "Class" in row:
        explicit = str(product.get("class_name") or product.get("Class") or "").strip()
        row["Class"] = explicit or (cp_parts[1] if len(cp_parts) >= 2 else "")
    if "Fine" in row:
        explicit = str(product.get("fine") or product.get("Fine") or "").strip()
        row["Fine"] = explicit or (cp_parts[2] if len(cp_parts) >= 3 else "")

    if "Product Name" in row:
        row["Product Name"] = str(product.get("product_name") or product.get("Product Name") or "").strip()

    # ── 4. Manufacturer / Brand ─────────────────────────────────────────────
    mfr_name = str(product.get("manufacturer_name") or product.get("MANUFACTURER_NAME") or "").strip()
    brand_name = str(product.get("brand_name") or product.get("BRAND_NAME") or "").strip()
    trade_name = str(product.get("trade_name") or product.get("TRADE_NAME") or "").strip()

    if "MANUFACTURER_NAME" in row:
        row["MANUFACTURER_NAME"] = mfr_name
    if "BRAND_NAME" in row:
        row["BRAND_NAME"] = brand_name
    if "TRADE_NAME" in row:
        row["TRADE_NAME"] = trade_name

    # ── 5. Descriptions ─────────────────────────────────────────────────────
    descs = product.get("descriptions", {})
    desc_fields = [
        "MOBILE_DESC",
        "INVOICE_DESC",
        "SHORT_DESC",
        "LONG_DESC1",
        "RETAIL_DESC",
        "MARKETING_DESCRIPTION",
    ]
    for df in desc_fields:
        if df in row:
            val = descs.get(df) if isinstance(descs, dict) else product.get(df)
            row[df] = str(val or "").strip()

    # ── 6. Features (ITEM_FEATURES_1..20) ───────────────────────────────────
    features = product.get("features", [])
    if isinstance(features, list):
        for idx, feat in enumerate(features[:20], start=1):
            k = f"ITEM_FEATURES_{idx}"
            if k in row:
                row[k] = str(feat or "").strip()

    # ── 7. Descriptive Extras ───────────────────────────────────────────────
    extras = ["With", "Standard/Approvals", "Prop 65", "Application", "Includes"]
    for ex in extras:
        if ex in row:
            val = product.get(ex) or product.get(ex.lower().replace("/", "_")) or ""
            row[ex] = str(val).strip()

    # ── 8. Attributes (ATTRIBUTE_LABEL/VALUE/UOM 1 through 50) ───────────────
    attrs = product.get("attributes", [])
    if isinstance(attrs, list):
        for idx, attr in enumerate(attrs[:50], start=1):
            lbl_key = f"ATTRIBUTE_LABEL {idx}"
            val_key = f"ATTRIBUTE_VALUE {idx}"
            uom_key = f"ATTRIBUTE_UOM {idx}"

            if isinstance(attr, dict):
                lbl = attr.get("label") or ""
                val = attr.get("value")
                uom = attr.get("uom") or ""

                if lbl_key in row:
                    row[lbl_key] = str(lbl).strip()
                if val_key in row:
                    row[val_key] = str(val).strip() if val is not None else ""
                if uom_key in row:
                    row[uom_key] = str(uom).strip()

    # ── 9. Identifiers & Commercial ─────────────────────────────────────────
    direct_fields = [
        "UPC", "EAN", "GTIN", "UNSPSC", "Warranty", "List Price",
        "Selling Qty", "Selling UOM", "Standard Packaging Information",
        "LENGTH", "LENGTH_UOM", "HEIGHT", "HEIGHT_UOM", "WIDTH", "WIDTH_UOM",
        "WEIGHT", "WEIGHT_UOM", "VOLUME", "VOLUME_UOM",
    ]
    for df in direct_fields:
        if df in row:
            val = product.get(df) or product.get(df.lower()) or ""
            row[df] = str(val).strip()

    # ── 10. Digital Assets ──────────────────────────────────────────────────
    brand_clean = clean_brand_for_filename(brand_name)
    if brand_clean and mpn:
        base_asset = f"{brand_clean}_{mpn}"
        if "Product Image" in row and not row["Product Image"]:
            row["Product Image"] = f"{base_asset}.jpg"
        if "Specification Sheet" in row and not row["Specification Sheet"]:
            row["Specification Sheet"] = f"{base_asset}_Specification_Sheet.pdf"

    # Explicit digital asset overrides if provided in product
    digital_assets = [
        "Product Image", "Alternate Image 1", "Alternate Image 2", "Alternate Image 3", "Alternate Image 4",
        "SDS", "SDS_1", "Warranty Information", "Catalog", "Specification Sheet",
        "Instruction/Installation Manual", "Service Manual", "Owners/User Manual",
        "Line Drawing", "MTR", "RoHS", "Full Engineering Drawing", "Energy Star Guide",
        "Technical Bulletin", "Submittal", "Compatibility Chart", "Size Chart",
        "Product Label/Insert", "Video Link", "Video Link 1",
    ]
    for da in digital_assets:
        if da in product and product[da]:
            row[da] = str(product[da]).strip()

    # ── 11. Metadata ────────────────────────────────────────────────────────
    if "Country Of Origin" in row:
        row["Country Of Origin"] = str(product.get("country_of_origin") or product.get("Country Of Origin") or "").strip()
    if "Discontinued" in row:
        row["Discontinued"] = str(product.get("discontinued") or product.get("Discontinued") or "").strip()
    if "Actual Image (Yes/No)" in row:
        # Default to "Yes" if Product Image is populated, else check product dict
        row["Actual Image (Yes/No)"] = str(product.get("Actual Image (Yes/No)") or ("Yes" if row.get("Product Image") else "")).strip()

    return row
