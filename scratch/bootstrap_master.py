"""Generate a bootstrap manufacturer/brand master from the input dataset.

The official UniCat_Manufacturer_and_Brand_List.xlsx is a gitignored
proprietary file. Until it is provided, this builds a starter master from
the Part_Manuf column ("Name (CODE)" pairs) plus the brand columns, so the
entity-resolution ladder has real candidates to match against.

Column names matter: ManufacturerResolver looks for ["manufacturer","name"]
+ ["code"]; BrandResolver prefers ["brand","name"], falling back to the
first column. So we keep exactly two columns: Manufacturer_Name, Code.

Output: data/reference/UniCat_Manufacturer_and_Brand_List.xlsx
"""
import os
import re
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(ROOT, "data", "raw", "Unihack_ Sample Dataset - Input.csv")
OUT = os.path.join(ROOT, "data", "reference", "UniCat_Manufacturer_and_Brand_List.xlsx")

BRAND_PLACEHOLDERS = {"", "-- unbranded --", "-- no unilog brand --", "-- no dib brand --",
                      "-- no e1 brand --", "commodity - unbranded", "nan", "none", "n/a"}
NAME_CODE = re.compile(r"^(?P<name>.+?)\s*\((?P<code>[^()]+)\)\s*$")

df = pd.read_csv(INPUT, encoding="utf-8")

entries = {}  # canonical name -> code


def add(name, code=None):
    name = (name or "").strip()
    if not name or name.lower() in BRAND_PLACEHOLDERS:
        return
    if name not in entries:
        entries[name] = (code or "").strip() or None


# Manufacturers: "Freud Inc (2435)" -> name + code. Keep the raw string too,
# so exact matching succeeds both before and after normalization.
for v in df["Part_Manuf"].dropna().astype(str):
    v = v.strip()
    m = NAME_CODE.match(v)
    if m:
        add(m.group("name"), m.group("code"))
        add(v, m.group("code"))
    else:
        add(v)

# Brands: include as canonical entries too (BrandResolver falls back to the
# first column when no brand column exists).
for col in ("E1_Brand", "Unilog_Brand", "DIB_Brand"):
    if col in df.columns:
        for v in df[col].dropna().astype(str):
            add(v)

rows = [{"Manufacturer_Name": n, "Code": c} for n, c in sorted(entries.items())]
# Fill missing codes with generated ones so every entry has an identity.
for i, r in enumerate(rows, 1):
    if not r["Code"]:
        r["Code"] = f"MFR-{i:04d}"

out_df = pd.DataFrame(rows)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
out_df.to_excel(OUT, index=False)
print(f"Wrote {len(rows)} entries to {OUT}")
print(out_df.head(12).to_string(index=False))
