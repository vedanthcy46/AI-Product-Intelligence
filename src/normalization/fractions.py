"""
fractions.py -- Decimal <-> trade-standard inch-fraction conversion engine.

Fully deterministic, no LLM calls.

WHY NOT a lookup table?
  The official Decimal_Fraction.xlsx reference (63 entries, 1/64 to 63/64)
  was referenced in the challenge brief but never distributed.
  Computing mathematically from first principles is more robust:
  it covers all 64ths without relying on a missing file, and is
  provably correct for any power-of-2 denominator up to 64.

CONFIRMED REAL FORMATS (from 2 ground-truth rows):
  Attribute values use hyphen-separated whole+fraction:
    "50-1/4", "24-1/4", "10-3/8", "33-7/16", "22-5/8"
  The unit ("in") is stored in the adjacent ATTRIBUTE_UOM column,
  NOT appended to the value string.

TRADE STANDARD: denominators are always powers of 2 (2, 4, 8, 16, 32, 64).
  Other denominators (3, 5, 6, 7, ...) do not appear in standard inch
  measurements and are not produced by this module.
"""

from fractions import Fraction as _Fraction
from typing import Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_POWERS_OF_2 = {2, 4, 8, 16, 32, 64}


def _nearest_trade_fraction(decimal_part: float, max_denominator: int = 64) -> Optional[_Fraction]:
    """
    Return the nearest trade-standard fraction for a value in [0, 1).

    Strategy
    --------
    1. Multiply by max_denominator (64) and round to the nearest integer.
       This snaps the decimal to the closest 64th.
    2. Construct Fraction(n, 64) which auto-reduces to lowest terms
       (e.g. 16/64 -> 1/4, 8/64 -> 1/8).
    3. The reduced denominator is guaranteed to be a power of 2
       because 64 = 2^6, so every factor of 64 is also a power of 2.

    Returns None when the decimal part rounds to exactly 0 (whole number)
    or when it rounds up to 1 (caller must increment the whole part).
    """
    if max_denominator not in _POWERS_OF_2:
        raise ValueError(
            f"max_denominator must be a power of 2 (got {max_denominator}). "
            f"Allowed: {sorted(_POWERS_OF_2)}"
        )

    numerator = round(decimal_part * max_denominator)

    if numerator == 0:
        return None   # no fractional remainder

    if numerator == max_denominator:
        # Decimal part rounds up to a full unit; caller handles whole increment.
        # Signal with a sentinel value the caller recognises.
        return _Fraction(max_denominator, max_denominator)

    frac = _Fraction(numerator, max_denominator)  # auto-reduces to lowest terms
    return frac


# ---------------------------------------------------------------------------
# 1.  decimal_to_fraction
# ---------------------------------------------------------------------------

def decimal_to_fraction(value: float, max_denominator: int = 64) -> str:
    """
    Convert a decimal inch measurement to its trade-standard fraction string.

    Parameters
    ----------
    value          : Decimal value (e.g. 50.25, 0.375, 24.0).
    max_denominator: Highest allowed denominator, must be a power of 2 <= 64.
                     Defaults to 64 (finest standard resolution).

    Returns
    -------
    Formatted string in one of three forms:
      - Whole number only : "24"       (decimal part == 0)
      - Pure fraction     : "1/2"      (whole part == 0)
      - Whole + fraction  : "50-1/4"   (confirmed real format; hyphen separator)

    Fractions are always reduced to lowest terms (e.g. never "32/64", always "1/2").

    Examples
    --------
    decimal_to_fraction(0.5)     -> "1/2"
    decimal_to_fraction(0.375)   -> "3/8"
    decimal_to_fraction(50.25)   -> "50-1/4"
    decimal_to_fraction(24.0)    -> "24"
    decimal_to_fraction(33.4375) -> "33-7/16"
    """
    if value < 0:
        raise ValueError(f"Negative inch values are not expected: {value}")

    whole = int(value)
    decimal_part = value - whole

    frac = _nearest_trade_fraction(decimal_part, max_denominator)

    # Decimal part rounded UP to a full unit -> carry into whole number
    if frac is not None and frac == _Fraction(1, 1):
        whole += 1
        frac = None

    if frac is None:
        return str(whole)

    if whole == 0:
        return f"{frac.numerator}/{frac.denominator}"

    return f"{whole}-{frac.numerator}/{frac.denominator}"


# ---------------------------------------------------------------------------
# 2.  fraction_to_decimal
# ---------------------------------------------------------------------------

def fraction_to_decimal(value: str) -> float:
    """
    Parse a trade-standard fraction string back to a float.

    Accepted formats
    ----------------
    - Whole number only : "24"      -> 24.0
    - Pure fraction     : "3/8"     -> 0.375
    - Whole + fraction  : "50-1/4"  -> 50.25   (confirmed real format)

    Notes
    -----
    The hyphen separator ("50-1/4") is the CONFIRMED real format.
    Space-separated ("50 1/4") is intentionally NOT accepted because it
    does not appear in the ground-truth data -- avoids mis-parsing strings
    where a space may carry other meaning.

    Integer and decimal whole-number strings ("24", "24.0") are both valid.

    Raises
    ------
    ValueError if the string cannot be parsed as a recognised format.

    Examples
    --------
    fraction_to_decimal("50-1/4") -> 50.25
    fraction_to_decimal("3/8")    -> 0.375
    fraction_to_decimal("24")     -> 24.0
    """
    s = value.strip()

    if not s:
        raise ValueError("Empty string cannot be converted to decimal.")

    # ── Case 1: Whole + fraction  e.g. "50-1/4" ──────────────────────────────
    if "-" in s:
        hyphen_idx = s.index("-")
        whole_str  = s[:hyphen_idx]
        frac_str   = s[hyphen_idx + 1:]

        if "/" not in frac_str:
            raise ValueError(
                f"Expected 'whole-num/den' format but fraction part has no '/': {value!r}"
            )

        num_str, den_str = frac_str.split("/", 1)
        try:
            whole = int(whole_str)
            num   = int(num_str.strip())
            den   = int(den_str.strip())
        except ValueError:
            raise ValueError(f"Non-integer component in fraction string: {value!r}")

        if den == 0:
            raise ValueError(f"Zero denominator in fraction string: {value!r}")

        return whole + num / den

    # ── Case 2: Pure fraction  e.g. "3/8" ────────────────────────────────────
    if "/" in s:
        num_str, den_str = s.split("/", 1)
        try:
            num = int(num_str.strip())
            den = int(den_str.strip())
        except ValueError:
            raise ValueError(f"Non-integer component in fraction string: {value!r}")

        if den == 0:
            raise ValueError(f"Zero denominator in fraction string: {value!r}")

        return num / den

    # ── Case 3: Plain number  e.g. "24" or "24.0" ────────────────────────────
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Cannot parse as number or fraction: {value!r}")


# ---------------------------------------------------------------------------
# Self-test  (run directly: python -m src.normalization.fractions)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    def check(desc, got, expected):
        ok = (got == expected)
        status = " PASS" if ok else " FAIL"
        print(f"{status}  {desc}")
        if not ok:
            print(f"         expected : {expected!r}")
            print(f"         got      : {got!r}")
        return ok

    print()
    print("=" * 68)
    print("  fractions.py -- self-test")
    print("=" * 68)

    results = []

    # ---- decimal_to_fraction ------------------------------------------------
    results.append(check(
        "decimal_to_fraction(0.5)      -> '1/2'",
        decimal_to_fraction(0.5), "1/2"))

    results.append(check(
        "decimal_to_fraction(0.375)    -> '3/8'",
        decimal_to_fraction(0.375), "3/8"))

    results.append(check(
        "decimal_to_fraction(50.25)    -> '50-1/4'",
        decimal_to_fraction(50.25), "50-1/4"))

    results.append(check(
        "decimal_to_fraction(24.0)     -> '24'",
        decimal_to_fraction(24.0), "24"))

    results.append(check(
        "decimal_to_fraction(10.375)   -> '10-3/8'   [real example]",
        decimal_to_fraction(10.375), "10-3/8"))

    results.append(check(
        "decimal_to_fraction(33.4375)  -> '33-7/16'  [real example]",
        decimal_to_fraction(33.4375), "33-7/16"))

    results.append(check(
        "decimal_to_fraction(22.625)   -> '22-5/8'   [real example]",
        decimal_to_fraction(22.625), "22-5/8"))

    results.append(check(
        "decimal_to_fraction(24.25)    -> '24-1/4'   [real example]",
        decimal_to_fraction(24.25), "24-1/4"))

    # Always-reduce tests
    results.append(check(
        "decimal_to_fraction(0.5, 64)  -> '1/2'  (not '32/64')",
        decimal_to_fraction(0.5, 64), "1/2"))

    results.append(check(
        "decimal_to_fraction(0.25, 64) -> '1/4'  (not '16/64')",
        decimal_to_fraction(0.25, 64), "1/4"))

    # Edge: whole number with rounding that carries up
    results.append(check(
        "decimal_to_fraction(1.0)      -> '1'",
        decimal_to_fraction(1.0), "1"))

    # ---- fraction_to_decimal ------------------------------------------------
    results.append(check(
        "fraction_to_decimal('50-1/4') -> 50.25",
        fraction_to_decimal("50-1/4"), 50.25))

    results.append(check(
        "fraction_to_decimal('3/8')    -> 0.375",
        fraction_to_decimal("3/8"), 0.375))

    results.append(check(
        "fraction_to_decimal('24')     -> 24.0",
        fraction_to_decimal("24"), 24.0))

    results.append(check(
        "fraction_to_decimal('1/2')    -> 0.5",
        fraction_to_decimal("1/2"), 0.5))

    results.append(check(
        "fraction_to_decimal('33-7/16') -> 33.4375",
        fraction_to_decimal("33-7/16"), 33.4375))

    # ---- round-trips --------------------------------------------------------
    results.append(check(
        "round-trip: '10-3/8'  -> decimal -> fraction",
        decimal_to_fraction(fraction_to_decimal("10-3/8")), "10-3/8"))

    results.append(check(
        "round-trip: '33-7/16' -> decimal -> fraction",
        decimal_to_fraction(fraction_to_decimal("33-7/16")), "33-7/16"))

    results.append(check(
        "round-trip: '22-5/8'  -> decimal -> fraction",
        decimal_to_fraction(fraction_to_decimal("22-5/8")), "22-5/8"))

    results.append(check(
        "round-trip: '1/2'     -> decimal -> fraction",
        decimal_to_fraction(fraction_to_decimal("1/2")), "1/2"))

    # ---- error handling -----------------------------------------------------
    try:
        fraction_to_decimal("")
        results.append(check("fraction_to_decimal('') raises ValueError", False, True))
    except ValueError:
        results.append(check("fraction_to_decimal('') raises ValueError", True, True))

    try:
        fraction_to_decimal("50-1/0")
        results.append(check("fraction_to_decimal('50-1/0') raises ValueError", False, True))
    except ValueError:
        results.append(check("fraction_to_decimal('50-1/0') raises ValueError", True, True))

    try:
        decimal_to_fraction(-1.0)
        results.append(check("decimal_to_fraction(-1.0) raises ValueError", False, True))
    except ValueError:
        results.append(check("decimal_to_fraction(-1.0) raises ValueError", True, True))

    print("=" * 68)
    if all(results):
        print(f"  All {len(results)} tests passed (OK)")
    else:
        n_fail = results.count(False)
        print(f"  {n_fail} / {len(results)} tests FAILED -- see above")
    print("=" * 68)
    print()
    sys.exit(0 if all(results) else 1)
