import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_TEST", "1")

tmp = os.path.join(os.environ["TEMP"], "weird_upload.csv")
with open(tmp, "w", encoding="utf-8") as f:
    f.write("Item No,Product Name,Brand,Vendor\nP-1,Coupling 1/2 in,Acme,Acme Corp\nP-2,Valve 3/4 in,Beta,Beta LLC\n")

from frontend.server import _load_input
df = _load_input(tmp)
assert list(df.columns) == ["Mfg_Part_Num", "Part_Desc", "Unilog_Brand", "Part_Manuf"], df.columns
rep = df.attrs["column_map"]
assert rep["mapped"]["Mfg_Part_Num"] == "Item No"
assert set(rep["missing"]) == {"E1_Brand", "DIB_Brand"}
print("SERVER _load_input OK ->", list(df.columns))

# Junk file must raise the user-facing ValueError
junk = os.path.join(os.environ["TEMP"], "junk_upload.csv")
with open(junk, "w", encoding="utf-8") as f:
    f.write("Foo,Bar\n1,2\n")
try:
    _load_input(junk)
    raise SystemExit("should have raised")
except ValueError as e:
    print("SERVER junk rejected OK ->", str(e)[:70], "...")
