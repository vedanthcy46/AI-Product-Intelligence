"""
test_normalization.py -- Deterministic normalization tests (Yashas track).

Covers LOV, UOM, and fraction engines with independently-known expected values.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.normalization.uom import normalize_uom, normalize_measurement
from src.normalization.fraction_utils import decimal_to_fraction, fraction_to_decimal
from src.normalization.lov import normalize_attribute_value

RESULTS = []


def check(name, condition):
    RESULTS.append((name, bool(condition)))
    if not condition:
        print(f"  FAIL  {name}")


def test_uom():
    check("uom '' -> None", normalize_uom("") is None)
    check("uom None -> None", normalize_uom(None) is None)
    check("uom '  volts  ' -> V", normalize_uom("  volts  ") == "V")
    check("uom 'in' -> in", normalize_uom("in") == "in")
    check("uom 'min' -> min (not confused)", normalize_uom("min") == "min")
    check("measurement '  120   V  ' -> '120 V'", normalize_measurement("  120   V  ") == "120 V")
    check("measurement '120' -> None (no unit)", normalize_measurement("120") is None)
    check("measurement '99 xyz' -> None", normalize_measurement("99 xyz") is None)


def test_fractions():
    check("decimal_to_fraction(-1.5) raises", _raises(lambda: decimal_to_fraction(-1.5)))
    check("decimal_to_fraction(0) -> '0'", decimal_to_fraction(0) == "0")
    check("decimal_to_fraction(0.125) -> '1/8'", decimal_to_fraction(0.125) == "1/8")
    check("decimal_to_fraction(0.375) -> '3/8'", decimal_to_fraction(0.375) == "3/8")
    check("decimal_to_fraction(0.5) -> '1/2'", decimal_to_fraction(0.5) == "1/2")
    check("decimal_to_fraction(50.25) -> '50-1/4'", decimal_to_fraction(50.25) == "50-1/4")
    check("fraction_to_decimal('1/2') -> 0.5", fraction_to_decimal("1/2") == 0.5)
    check("fraction_to_decimal('') raises", _raises(lambda: fraction_to_decimal("")))


def test_lov():
    val, matched = normalize_attribute_value("*", "Material", "SS")
    check("LOV SS -> Stainless Steel", val == "Stainless Steel" and matched)
    val, matched = normalize_attribute_value("*", "Material", "SST")
    check("LOV SST -> Stainless Steel", val == "Stainless Steel" and matched)
    val, _ = normalize_attribute_value("*", "Material", "   ")
    check("LOV whitespace no crash", isinstance(val, str))


def _raises(fn):
    try:
        fn()
        return False
    except (ValueError, TypeError):
        return True


def main():
    print("=" * 60)
    print("  NORMALIZATION TESTS")
    print("=" * 60)
    test_uom()
    test_fractions()
    test_lov()

    passed = sum(1 for _, ok in RESULTS if ok)
    total = len(RESULTS)
    print("-" * 60)
    print(f"  {passed}/{total} assertions passed")
    if passed != total:
        for name, ok in RESULTS:
            if not ok:
                print(f"    - {name}")
        sys.exit(1)
    print("  All assertions passed (OK)")
    print("=" * 60)


if __name__ == "__main__":
    main()