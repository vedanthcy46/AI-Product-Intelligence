"""
exporter.py -- Export validated product records to delivery format CSV.

Strictly verifies that output contains exactly the 252 delivery headers in exact order.
"""

import os
import csv
from typing import List, Dict, Any, Optional
from src.output.mapper import get_expected_headers, product_to_row


def export_to_csv(
    products: List[Dict[str, Any]],
    output_path: str,
    expected_headers_path: Optional[str] = None,
) -> None:
    """
    Convert products to delivery format and export to CSV.

    Parameters
    ----------
    products : list of dict
        Internal product records.
    output_path : str
        Target CSV output file path.
    expected_headers_path : str, optional
        Path to expected output file for header verification.

    Raises
    ------
    ValueError
        If mapped rows do not match the exact 252 expected headers or order.
    """
    headers = get_expected_headers(expected_headers_path)
    expected_count = len(headers)

    mapped_rows: List[Dict[str, str]] = []
    for idx, prod in enumerate(products):
        row = product_to_row(prod, headers=headers)

        # Integrity verification
        row_keys = list(row.keys())
        if len(row_keys) != expected_count or row_keys != headers:
            missing = set(headers) - set(row_keys)
            extra = set(row_keys) - set(headers)
            raise ValueError(
                f"Row {idx} header mismatch against expected 252 columns! "
                f"Missing: {len(missing)} cols, Extra: {len(extra)} cols"
            )
        mapped_rows.append(row)

    # Ensure parent directory exists
    parent_dir = os.path.dirname(output_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    # Write CSV
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(mapped_rows)

    print(f"Successfully exported {len(mapped_rows)} products ({expected_count} cols) to: {output_path}")
