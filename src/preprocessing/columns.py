"""
Flexible column mapping for uploaded catalogue files.

The canonical pipeline input schema is six fields:
    Mfg_Part_Num, Part_Desc, E1_Brand, Unilog_Brand, DIB_Brand, Part_Manuf

Real-world uploads rarely use those exact headers ("Part Number",
"Description", "Brand", "Vendor", ...).  Without mapping, every row silently
resolves to None and the pipeline produces empty pass-through output.

normalize_columns() maps common header variants onto the canonical names and
reports exactly what it matched, missed, and left untouched — so the UI can
tell the user what happened instead of failing silently.
"""

import logging
import re
from typing import Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

CANONICAL_FIELDS = [
    "Mfg_Part_Num", "Part_Desc", "E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf",
]

# Alias -> canonical field. Matching happens on a *normalized* header form:
# lowercase with every non-alphanumeric character removed, so "Part-No.",
# "PART NUMBER", "part_number" and "PartNumber" all collapse to "partnumber".
# Longest aliases win; the table is intentionally generous.
_ALIASES: Dict[str, str] = {
    # ── Mfg_Part_Num ──────────────────────────────────────────────
    "manufacturerpartnumber": "Mfg_Part_Num",
    "manufacturerpartnum": "Mfg_Part_Num",
    "mfrpartnumber": "Mfg_Part_Num",
    "mfgpartnumber": "Mfg_Part_Num",
    "mfgpartnum": "Mfg_Part_Num",
    "mfrpartnum": "Mfg_Part_Num",
    "manufpartnumber": "Mfg_Part_Num",
    "manufacturernumber": "Mfg_Part_Num",
    "itemnumber": "Mfg_Part_Num",
    "itemno": "Mfg_Part_Num",
    "itemnum": "Mfg_Part_Num",
    "productcode": "Mfg_Part_Num",
    "partcode": "Mfg_Part_Num",
    "modelno": "Mfg_Part_Num",
    "productnumber": "Mfg_Part_Num",
    "modelnumber": "Mfg_Part_Num",
    "cataloguenumber": "Mfg_Part_Num",
    "catnumber": "Mfg_Part_Num",
    "skunumber": "Mfg_Part_Num",
    "partnumber": "Mfg_Part_Num",
    "partno": "Mfg_Part_Num",
    "partnum": "Mfg_Part_Num",
    "partid": "Mfg_Part_Num",
    "mpn": "Mfg_Part_Num",
    "sku": "Mfg_Part_Num",
    "pn": "Mfg_Part_Num",
    # ── Part_Desc ─────────────────────────────────────────────────
    "partdescription": "Part_Desc",
    "productdescription": "Part_Desc",
    "itemdescription": "Part_Desc",
    "productname": "Part_Desc",
    "itemname": "Part_Desc",
    "partdesc": "Part_Desc",
    "description": "Part_Desc",
    "producttitle": "Part_Desc",
    "itemtitle": "Part_Desc",
    "desc": "Part_Desc",
    # ── E1_Brand ──────────────────────────────────────────────────
    "e1brand": "E1_Brand",
    "ebrand": "E1_Brand",
    "brand1": "E1_Brand",
    "brandone": "E1_Brand",
    # ── Unilog_Brand ──────────────────────────────────────────────
    "unilogbrand": "Unilog_Brand",
    "ubrand": "Unilog_Brand",
    "genericbrand": "Unilog_Brand",
    "brand": "Unilog_Brand",   # bare "Brand" → primary brand slot
    # ── DIB_Brand ─────────────────────────────────────────────────
    "dibbrand": "DIB_Brand",
    "dbrand": "DIB_Brand",
    "brand2": "DIB_Brand",
    "secondarybrand": "DIB_Brand",
    # ── Part_Manuf ────────────────────────────────────────────────
    "partmanufacturer": "Part_Manuf",
    "partmanufacture": "Part_Manuf",
    "manufacturername": "Part_Manuf",
    "manufacturermfr": "Part_Manuf",
    "manufacturer": "Part_Manuf",
    "partmanuf": "Part_Manuf",
    "mfr": "Part_Manuf",
    "mfg": "Part_Manuf",
    "maker": "Part_Manuf",
    "vendor": "Part_Manuf",
    "supplier": "Part_Manuf",
    "brandowner": "Part_Manuf",
}


def _norm(header: str) -> str:
    """Lowercase + strip all non-alphanumerics: 'Part-No.' -> 'partno'."""
    return re.sub(r"[^a-z0-9]", "", str(header).strip().lower())


def _build_alias_index() -> List[Tuple[str, str]]:
    """Aliases sorted longest-first so 'manufacturerpartnumber' beats 'mfr'."""
    return sorted(_ALIASES.items(), key=lambda kv: len(kv[0]), reverse=True)


_ALIAS_INDEX = _build_alias_index()


def normalize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    Rename whatever columns can be recognized into the canonical schema.

    Returns:
        (df, report) where report = {
            "mapped":   {canonical: original_header, ...},
            "missing":  [canonical, ...],
            "ignored":  [original_header, ...],   # unrecognized columns kept as-is
        }

    Raises:
        ValueError: when neither an MPN nor a description column exists —
                    there would be nothing meaningful to enrich.
    """
    if df.columns.empty:
        raise ValueError("The uploaded file has no header row.")

    original_headers = [str(c) for c in df.columns]
    norm_to_orig: Dict[str, str] = {}
    for orig in original_headers:
        n = _norm(orig)
        if n and n not in norm_to_orig:      # first occurrence wins on dupes
            norm_to_orig[n] = orig

    claimed_norms = set()
    rename_map: Dict[str, str] = {}          # original header -> canonical
    mapped: Dict[str, str] = {}

    def claim(alias: str, canonical: str, norm_header: str):
        orig = norm_to_orig[norm_header]
        if canonical in mapped:
            return                            # earlier match already owns it
        rename_map[orig] = canonical
        mapped[canonical] = orig
        claimed_norms.add(norm_header)
        logger.info("Column '%s' mapped to %s (via '%s')", orig, canonical, alias)

    # Pass 1 — exact normalized matches (handles the tricky collisions like
    # "Manufacturer Part Number" vs "Manufacturer").
    for norm_header in norm_to_orig:
        canonical = _ALIASES.get(norm_header)
        if canonical:
            claim(norm_header, canonical, norm_header)

    # Pass 2 — containment fallback for decorated headers such as
    # "ACME Part Number" or "Primary Description (EN)".
    for alias, canonical in _ALIAS_INDEX:
        if canonical in mapped or len(alias) < 5:
            continue                          # short stems too risky in pass 2
        for norm_header in norm_to_orig:
            if norm_header in claimed_norms:
                continue
            if alias in norm_header:
                claim(alias, canonical, norm_header)
                break

    out = df.rename(columns=rename_map)
    missing = [f for f in CANONICAL_FIELDS if f not in mapped]

    if "Mfg_Part_Num" not in mapped and "Part_Desc" not in mapped:
        raise ValueError(
            "Could not find a part-number or description column. "
            f"Recognized headers include: {', '.join(CANONICAL_FIELDS)} "
            "(common aliases like 'Part Number', 'Description', 'Brand', "
            "'Manufacturer' also work). Found these headers: "
            f"{', '.join(original_headers)}"
        )

    report = {"mapped": mapped, "missing": missing, "ignored": [
        h for h in original_headers if h not in rename_map
    ]}
    return out, report


__all__ = ["normalize_columns", "CANONICAL_FIELDS"]
