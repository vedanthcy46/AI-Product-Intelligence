import sys
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.normalization.uom import normalize_measurement
from src.normalization.fractions import decimal_to_fraction, fraction_to_decimal
from src.normalization.lov import normalize_attribute_value

print("=" * 72)
print("  STANDALONE PER-MODULE SMOKE TESTS")
print("=" * 72)

# 1. uom.py: normalize_measurement("24 inches") -> "24 in"
t1 = normalize_measurement("24 inches")
print(f"uom.py       normalize_measurement('24 inches')                         = {t1!r}")
assert t1 == "24 in", f"Expected '24 in', got {t1!r}"

# 2. uom.py: normalize_measurement("99 xyz") -> None
t2 = normalize_measurement("99 xyz")
print(f"uom.py       normalize_measurement('99 xyz')                             = {t2!r}")
assert t2 is None, f"Expected None, got {t2!r}"

# 3. fractions.py: decimal_to_fraction(50.25) -> "50-1/4"
t3 = decimal_to_fraction(50.25)
print(f"fractions.py decimal_to_fraction(50.25)                                 = {t3!r}")
assert t3 == "50-1/4", f"Expected '50-1/4', got {t3!r}"

# 4. fractions.py: round-trip decimal_to_fraction(fraction_to_decimal("10-3/8")) -> "10-3/8"
t4 = decimal_to_fraction(fraction_to_decimal("10-3/8"))
print(f"fractions.py decimal_to_fraction(fraction_to_decimal('10-3/8'))           = {t4!r}")
assert t4 == "10-3/8", f"Expected '10-3/8', got {t4!r}"

# 5. lov.py: normalize_attribute_value("*", "Material", "SST") -> ("Stainless Steel", True)
t5 = normalize_attribute_value("*", "Material", "SST")
print(f"lov.py       normalize_attribute_value('*', 'Material', 'SST')          = {t5!r}")
assert t5 == ("Stainless Steel", True), f"Expected ('Stainless Steel', True), got {t5!r}"

# 6. lov.py: normalize_attribute_value("*", "Brand", "FRIGIDAIRE®") -> ("FRIGIDAIRE®", False)
t6 = normalize_attribute_value("*", "Brand", "FRIGIDAIRE®")
print(f"lov.py       normalize_attribute_value('*', 'Brand', 'FRIGIDAIRE®')     = {t6!r}")
assert t6 == ("FRIGIDAIRE®", False), f"Expected ('FRIGIDAIRE®', False), got {t6!r}"

print("=" * 72)
print("  ALL 6 SMOKE TESTS PASSED EXACTLY AS SPECIFIED (6/6) [OK]")
print("=" * 72)
