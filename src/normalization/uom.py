"""
uom.py — Unit of Measure normalisation engine.

All logic is fully deterministic (no LLM calls).
Consumes raw candidate strings from upstream and normalises them to the
approved abbreviation + format for the output schema.

CONFIRMED GROUND-TRUTH RULES (from 2 real Dishwasher rows):
  • Standard mode  : number<SPACE>unit  ->  "120 V", "15 A", "47 dBA", "24 in", "50-1/4 in"
  • Compressed mode: no space, INVOICE_DESC only -> "120V", "15A", "50-1/4IN"
    INVOICE_DESC is ALL-CAPS, so units are also uppercased in that field.

NOTE: No official UOM master list was distributed with the challenge.
  The UOM_TABLE below is inferred from:
    - The 2 confirmed ground-truth rows (V, A, dBA, in)
    - Reasonable coverage for industrial/retail hardware, tools, appliances
  Flag any unrecognised unit for human review; do NOT pass it through silently.
"""

import re
from typing import Optional, Literal, Tuple


# ---------------------------------------------------------------------------
# UOM_TABLE
# Mapping: raw variant (lower-cased at lookup time) -> approved abbreviation
#
# NOTE: This list is INFERRED, not from an official reference file.
#       Add new entries as upstream AI surfaces new unit strings.
#       Values (approved abbreviations) must match exactly what the
#       output schema expects — capitalisation is significant.
# ---------------------------------------------------------------------------
UOM_TABLE: dict[str, str] = {
    # ── Length ───────────────────────────────────────────────────────────────
    "in":           "in",
    "in.":          "in",
    "inch":         "in",
    "inches":       "in",
    "\"":           "in",   # double-quote shorthand for inches
    "ft":           "ft",
    "ft.":          "ft",
    "foot":         "ft",
    "feet":         "ft",
    "mm":           "mm",
    "millimeter":   "mm",
    "millimeters":  "mm",
    "millimetre":   "mm",
    "millimetres":  "mm",
    "cm":           "cm",
    "centimeter":   "cm",
    "centimeters":  "cm",
    "centimetre":   "cm",
    "centimetres":  "cm",
    "m":            "m",
    "meter":        "m",
    "meters":       "m",
    "metre":        "m",
    "metres":       "m",
    # ── Weight ───────────────────────────────────────────────────────────────
    "lb":           "lb",
    "lbs":          "lb",
    "lb.":          "lb",
    "lbs.":         "lb",
    "pound":        "lb",
    "pounds":       "lb",
    "kg":           "kg",
    "kilogram":     "kg",
    "kilograms":    "kg",
    "oz":           "oz",
    "oz.":          "oz",
    "ounce":        "oz",
    "ounces":       "oz",
    "g":            "g",
    "gram":         "g",
    "grams":        "g",
    # ── Electrical ───────────────────────────────────────────────────────────
    "v":            "V",    # confirmed ground truth
    "volt":         "V",
    "volts":        "V",
    "a":            "A",    # confirmed ground truth
    "amp":          "A",
    "amps":         "A",
    "ampere":       "A",
    "amperes":      "A",
    "w":            "W",
    "watt":         "W",
    "watts":        "W",
    "kw":           "kW",
    "kilowatt":     "kW",
    "kilowatts":    "kW",
    "kw-hr":        "kW-hr",   # seen in real ground truth (Annual Energy field)
    "kwh":          "kW-hr",
    "kw·h":         "kW-hr",
    # ── Sound ────────────────────────────────────────────────────────────────
    "dba":          "dBA",  # confirmed ground truth
    "db(a)":        "dBA",
    "db":           "dB",
    "decibel":      "dB",
    "decibels":     "dB",
    # ── Percentage ───────────────────────────────────────────────────────────
    "%":            "%",
    "percent":      "%",
    "pct":          "%",
    "pct.":         "%",
    # ── Pressure ─────────────────────────────────────────────────────────────
    "psi":          "psi",
    "p.s.i.":       "psi",
    "p.s.i":        "psi",
    # ── Temperature ──────────────────────────────────────────────────────────
    "°f":           "°F",
    "f":            "°F",   # bare "F" almost always means Fahrenheit in this domain
    "deg f":        "°F",
    "degrees f":    "°F",
    "°c":           "°C",
    "c":            "°C",   # bare "C" almost always means Celsius in this domain
    "deg c":        "°C",
    "degrees c":    "°C",
    # ── Misc hardware / packaging ─────────────────────────────────────────────
    "rpm":          "RPM",
    "r.p.m.":       "RPM",
    "cfm":          "CFM",
    "gpm":          "GPM",
    "hp":           "HP",
    "horsepower":   "HP",
    "btuh":         "BTUH",
    "btu/h":        "BTUH",
    "btu":          "BTU",
    "hr":           "hr",
    "hrs":          "hr",
    "hour":         "hr",
    "hours":        "hr",
    "min":          "min",
    "minute":       "min",
    "minutes":      "min",
    "pc":           "pc",
    "pcs":          "pc",
    "piece":        "pc",
    "pieces":       "pc",
    "ea":           "ea",
    "each":         "ea",
    "pk":           "pk",
    "pack":         "pk",
    "pr":           "pr",
    "pair":         "pr",
    "set":          "set",
}


# ---------------------------------------------------------------------------
# 1.  normalize_uom
# ---------------------------------------------------------------------------
def normalize_uom(raw_unit: str) -> Optional[str]:
    """
    Look up *raw_unit* in UOM_TABLE (case-insensitive, whitespace-trimmed).

    Returns:
        Approved abbreviation string, or None if the unit is not recognised.

    Examples:
        normalize_uom("inches") -> "in"
        normalize_uom("VOLTS")  -> "V"
        normalize_uom("xyz")    -> None
    """
    if not raw_unit:
        return None
    key = raw_unit.strip().lower()
    return UOM_TABLE.get(key, None)


# ---------------------------------------------------------------------------
# 2.  parse_numeric_value
# ---------------------------------------------------------------------------
# Pattern: optional leading integer, optional fractional part written as -N/D
# e.g.  "50-1/4"  "24"  "120"  "3-1/2"
_FRACTION_RE = re.compile(
    r"^"
    r"(?P<whole>\d+)"           # mandatory whole number
    r"(?:-(?P<num>\d+)/(?P<den>\d+))?"  # optional -numerator/denominator
    r"$"
)

# Pattern for a simple decimal / integer (no fraction)
_DECIMAL_RE = re.compile(r"^-?\d+(\.\d+)?$")


def parse_numeric_value(raw: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Split a raw measurement string into (numeric_value_or_None, unit_string_or_None).

    Strategy
    --------
    1. Strip and try to split on the first boundary between digits/fraction and
       alphabetic/symbol characters.
    2. For plain integers/decimals, convert numeric part to float.
    3. For mixed-number fractions (e.g. "50-1/4"), do NOT convert to float
       (that would silently corrupt the value).  Return (None, unit) and let
       the caller invoke the fraction engine if needed.

    Returns
    -------
    (float_or_None, unit_str_or_None)

    Note on number-only input (e.g. "120" with no unit):
        Returns (120.0, None).  The caller must supply a unit separately or
        flag the record — a measurement without a known unit is ambiguous.

    Examples:
        parse_numeric_value("24 inches") -> (24.0, "inches")
        parse_numeric_value("120V")      -> (120.0, "V")
        parse_numeric_value("50-1/4 in") -> (None, "in")   # fraction — don't corrupt
        parse_numeric_value("47 dBA")   -> (47.0, "dBA")
        parse_numeric_value("24")       -> (24.0, None)
    """
    if not raw:
        return (None, None)

    s = raw.strip()

    # ── Step 1: split numeric prefix from unit suffix ────────────────────────
    # A numeric prefix may contain digits, hyphens, slashes, and dots
    # (covers integers, decimals, and mixed fractions like "50-1/4").
    match = re.match(r"^([0-9][0-9./\-]*)(.*)$", s)
    if not match:
        # Starts with something non-numeric — can't parse
        return (None, s if s else None)

    num_part  = match.group(1).strip()
    unit_part = match.group(2).strip() or None

    # ── Step 2: try to convert numeric part ─────────────────────────────────
    if _FRACTION_RE.match(num_part):
        fm = _FRACTION_RE.match(num_part)
        if fm.group("num") is not None:
            # Mixed number fraction — keep as string, do NOT convert to float.
            # Caller should route through fractions.py if a float is needed.
            return (None, unit_part)
        else:
            # Plain whole number
            return (float(fm.group("whole")), unit_part)

    if _DECIMAL_RE.match(num_part):
        return (float(num_part), unit_part)

    # Couldn't cleanly parse the numeric part
    return (None, unit_part)


# ---------------------------------------------------------------------------
# 3.  format_standard
# ---------------------------------------------------------------------------
def format_standard(number_str: str, uom: str) -> str:
    """
    Return the standard (space-separated) format: "{number_str} {uom}".

    Confirmed ground-truth pattern for all fields EXCEPT INVOICE_DESC.

    Examples:
        format_standard("120", "V")    -> "120 V"
        format_standard("47", "dBA")   -> "47 dBA"
        format_standard("50-1/4", "in") -> "50-1/4 in"
    """
    return f"{number_str.strip()} {uom.strip()}"


# ---------------------------------------------------------------------------
# 4.  format_compressed
# ---------------------------------------------------------------------------
def format_compressed(
    number_str: str,
    uom: str,
    uppercase_unit: bool = False,
) -> str:
    """
    Return the compressed (no-space) format used in INVOICE_DESC.

    Confirmed ground truth: "120V", "15A", "50-1/4IN".
    Because INVOICE_DESC is ALL-CAPS, units appear uppercased there.

    Parameters
    ----------
    number_str     : The numeric portion as a string (fractions preserved).
    uom            : The approved UOM abbreviation.
    uppercase_unit : If True, the unit is uppercased before concatenation.
                     Should be True when formatting for INVOICE_DESC.
                     Defaults to False to avoid unintentionally changing
                     case for units that have meaningful capitalisation
                     (e.g. "kW" should NOT become "KW" except in INVOICE_DESC).

    Examples:
        format_compressed("120", "V")                    -> "120V"
        format_compressed("50-1/4", "in", uppercase_unit=True) -> "50-1/4IN"
        format_compressed("15", "A",  uppercase_unit=True)     -> "15A"
    """
    unit = uom.strip().upper() if uppercase_unit else uom.strip()
    return f"{number_str.strip()}{unit}"


# ---------------------------------------------------------------------------
# 5.  normalize_measurement  (full pipeline)
# ---------------------------------------------------------------------------
def normalize_measurement(
    raw: str,
    mode: Literal["standard", "compressed"] = "standard",
    uppercase_unit: bool = False,
) -> Optional[str]:
    """
    End-to-end normalisation: parse raw string -> normalise unit -> reformat.

    Parameters
    ----------
    raw            : Raw measurement string from upstream (e.g. "24 inches",
                     "120V", "47 dBA", "50-1/4 in").
    mode           : "standard"   -> spaced format  ("120 V")
                     "compressed" -> no-space format ("120V")
                     Use "compressed" + uppercase_unit=True for INVOICE_DESC.
    uppercase_unit : Passed through to format_compressed when mode="compressed".

    Returns
    -------
    Normalised string, or None if the unit is not recognised.
    Callers MUST treat None as a flag for human review — do not silently
    pass unrecognised units through.

    Behaviour on number-only input (no unit detectable, e.g. "120"):
        Returns None — a measurement without a unit is ambiguous and cannot
        be reliably normalised.  Caller should flag and request unit context
        from upstream.

    Examples:
        normalize_measurement("24 inches")          -> "24 in"
        normalize_measurement("120V")               -> "120 V"
        normalize_measurement("47 dBA")             -> "47 dBA"
        normalize_measurement("50-1/4 in", "compressed", uppercase_unit=True)
                                                    -> "50-1/4IN"
        normalize_measurement("99 xyz")             -> None
        normalize_measurement("120")                -> None  (no unit)
    """
    if not raw:
        return None

    # ── Step 1: determine the numeric and raw-unit portions ──────────────────
    # Special-case: input may already be "number unit" or "numberUNIT" with
    # no space (compressed input like "120V").
    # parse_numeric_value handles both layouts.

    float_val, raw_unit = parse_numeric_value(raw)

    # Reconstruct the numeric string from the original (preserve fractions)
    # by stripping the unit suffix from the raw string.
    s = raw.strip()
    if raw_unit:
        # num_str is everything before the unit in the original string
        num_str = s[: len(s) - len(raw_unit)].rstrip()
    else:
        num_str = s

    if not num_str:
        return None  # nothing parseable on the numeric side

    # ── Step 2: no unit -> cannot normalise ──────────────────────────────────
    if not raw_unit:
        # Number-only input is ambiguous — flag it.
        return None

    # ── Step 3: normalise the unit ───────────────────────────────────────────
    approved_uom = normalize_uom(raw_unit)
    if approved_uom is None:
        return None  # unrecognised unit — caller must flag

    # ── Step 4: reformat ─────────────────────────────────────────────────────
    if mode == "compressed":
        return format_compressed(num_str, approved_uom, uppercase_unit=uppercase_unit)
    return format_standard(num_str, approved_uom)


# ---------------------------------------------------------------------------
# Self-test (run directly: python -m src.normalization.uom)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    PASS = "\033[92m PASS\033[0m"
    FAIL = "\033[91m FAIL\033[0m"

    cases = [
        # (description, call_result, expected)
        (
            'normalize_measurement("24 inches")',
            normalize_measurement("24 inches"),
            "24 in",
        ),
        (
            'normalize_measurement("120V")',
            normalize_measurement("120V"),
            "120 V",
        ),
        (
            'normalize_measurement("120")  [number-only -> None, ambiguous]',
            normalize_measurement("120"),
            None,
        ),
        (
            'normalize_measurement("47 dBA")',
            normalize_measurement("47 dBA"),
            "47 dBA",
        ),
        (
            'normalize_measurement("99 xyz")  [unknown unit -> None]',
            normalize_measurement("99 xyz"),
            None,
        ),
        (
            'format_compressed("50-1/4", "in")  [no uppercase]',
            format_compressed("50-1/4", "in"),
            "50-1/4in",
        ),
        (
            'format_compressed("50-1/4", "in", uppercase_unit=True)  [INVOICE_DESC style]',
            format_compressed("50-1/4", "in", uppercase_unit=True),
            "50-1/4IN",
        ),
        (
            'normalize_measurement("50-1/4 in", compressed+uppercase)  [full pipeline, fraction]',
            normalize_measurement("50-1/4 in", mode="compressed", uppercase_unit=True),
            "50-1/4IN",
        ),
        # Extra coverage
        (
            'normalize_uom("VOLTS")',
            normalize_uom("VOLTS"),
            "V",
        ),
        (
            'normalize_uom("dba")  [lowercase dba -> dBA]',
            normalize_uom("dba"),
            "dBA",
        ),
        (
            'normalize_uom("kw")  [kw -> kW, case matters in approved form]',
            normalize_uom("kw"),
            "kW",
        ),
        (
            'parse_numeric_value("50-1/4 in")  [fraction -> float is None]',
            parse_numeric_value("50-1/4 in"),
            (None, "in"),
        ),
        (
            'parse_numeric_value("120V")  [int + compressed unit]',
            parse_numeric_value("120V"),
            (120.0, "V"),
        ),
        (
            'parse_numeric_value("24 inches")',
            parse_numeric_value("24 inches"),
            (24.0, "inches"),
        ),
        (
            'parse_numeric_value("24")  [number-only -> unit is None]',
            parse_numeric_value("24"),
            (24.0, None),
        ),
    ]

    print("\n" + "=" * 68)
    print("  UOM normalisation engine — self-test")
    print("=" * 68)
    all_pass = True
    for desc, got, expected in cases:
        ok = got == expected
        if not ok:
            all_pass = False
        status = PASS if ok else FAIL
        print(f"{status}  {desc}")
        if not ok:
            print(f"         expected : {expected!r}")
            print(f"         got      : {got!r}")

    print("=" * 68)
    if all_pass:
        print("  All tests passed (OK)")
    else:
        print("  Some tests FAILED — see above")
    print("=" * 68 + "\n")
    sys.exit(0 if all_pass else 1)
