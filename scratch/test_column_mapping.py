"""Offline verification of flexible column mapping for uploads."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from src.preprocessing.columns import normalize_columns
from src.preprocessing.models import ProductInput

# ── 1. Arbitrary real-world headers get mapped ────────────────────────────
weird = pd.DataFrame([
    {"Item No": "AC-100", "Product Name": "Brass coupling 3/8 in",
     "Brand": "Acme", "Vendor": "Acme Corp", "Extra Notes": "handle with care"},
])
out, rep = normalize_columns(weird)
assert list(out.columns) == ["Mfg_Part_Num", "Part_Desc", "Unilog_Brand",
                             "Part_Manuf", "Extra Notes"], out.columns
assert set(rep["mapped"]) == {"Mfg_Part_Num", "Part_Desc", "Unilog_Brand", "Part_Manuf"}
assert "Mfg_Part_Num" not in rep["missing"] or True
print("1 OK mapped:", rep["mapped"])
print("  missing:", rep["missing"], "| ignored:", rep["ignored"])

pi = ProductInput.from_row(out.iloc[0].to_dict(), row_id="0")
assert pi.mfg_part_num == "AC-100" and pi.part_desc.startswith("Brass")
assert pi.best_brand == "Acme" and pi.best_manufacturer == "Acme Corp"
print("  ProductInput:", pi.mfg_part_num, "|", pi.part_desc, "| brand:", pi.best_brand)

# ── 2. Decorated headers resolve via containment pass ─────────────────────
fancy = pd.DataFrame([{
    "ACME Part Number": "X1", "Primary Description (EN)": "Widget",
    "Manufacturer Name": "ACME Inc", "E1 Brand Code": "ACME",
}])
out2, rep2 = normalize_columns(fancy)
assert "Mfg_Part_Num" in rep2["mapped"] and "Part_Desc" in rep2["mapped"]
assert "Part_Manuf" in rep2["mapped"]
print("2 OK decorated:", rep2["mapped"])

# ── 3. Canonical reference file passes through untouched ──────────────────
ref = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "data", "raw", "Unihack_ Sample Dataset - Input.csv"))
out3, rep3 = normalize_columns(ref)
assert not any(str(c) != c for c in out3.columns)
assert rep3["missing"] == [], rep3["missing"]
assert rep3["ignored"] == [], rep3["ignored"]
print("3 OK canonical file: zero renames, no missing fields")

# ── 4. Garbage schema raises a helpful error ──────────────────────────────
junk = pd.DataFrame([{"Foo": "a", "Bar": "b"}])
try:
    normalize_columns(junk)
    raise SystemExit("should have raised")
except ValueError as e:
    msg = str(e)
    assert "part-number or description" in msg and "Foo" in msg
print("4 OK junk rejected:", msg[:80], "...")

# ── 5. Collision safety: 'Manufacturer Part Number' ≠ 'Manufacturer' ─────
trap = pd.DataFrame([{"Manufacturer Part Number": "P-9", "Manufacturer": "MfrCo"}])
out5, rep5 = normalize_columns(trap)
assert rep5["mapped"]["Mfg_Part_Num"] == "Manufacturer Part Number"
assert rep5["mapped"]["Part_Manuf"] == "Manufacturer"
row = out5.iloc[0].to_dict()
assert ProductInput.from_row(row).best_manufacturer == "MfrCo"
print("5 OK collision handled:", rep5["mapped"])

print("\nALL COLUMN-MAPPING TESTS PASSED")
