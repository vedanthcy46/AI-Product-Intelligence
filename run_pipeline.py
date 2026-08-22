"""
run_pipeline.py -- CLI entry point for the full enrichment pipeline.

Usage:
    python run_pipeline.py --input data/raw/input.csv \
        --output data/processed/output.csv \
        --master data/reference/UniCat_Manufacturer_and_Brand_List.xlsx \
        [--limit 200] [--workers 5]

Requires the data files (gitignored, supplied locally) and a Groq API key in
.env for the LLM-assisted stages (understanding, classification ranking,
attribute extraction). The pipeline degrades gracefully without the key.
"""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv  # optional convenience

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("run_pipeline")


def _resolve(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Product Content Enrichment Pipeline")
    parser.add_argument("--input", required=True, help="Path to raw catalogue input CSV (6 cols)")
    parser.add_argument("--output", required=True, help="Path to write the 252-column delivery CSV")
    parser.add_argument("--master", default="data/reference/UniCat_Manufacturer_and_Brand_List.xlsx",
                        help="Path to manufacturer/brand master xlsx")
    parser.add_argument("--limit", type=int, default=None, help="Only process first N rows")
    parser.add_argument("--workers", type=int, default=5, help="ThreadPoolExecutor workers")
    parser.add_argument("--env", default=".env", help="Path to .env file (optional)")
    parser.add_argument("--internal-json", default=None,
                        help="Optional path to also write the rich internal Product JSON (frontend data)")
    args = parser.parse_args()

    # Load .env if present
    if args.env and os.path.exists(args.env):
        try:
            load_dotenv(args.env)
        except ImportError:
            logger.info("python-dotenv not installed; skipping .env load")

    input_path = _resolve(args.input)
    output_path = _resolve(args.output)
    master_path = _resolve(args.master)

    if not os.path.exists(input_path):
        logger.error("Input file not found: %s", input_path)
        return 1
    if not os.path.exists(master_path):
        logger.warning("Master file not found at %s — running in pass-through mode "
                       "(manufacturer/brand unmatched, low confidence).", master_path)
        master_path = None

    import pandas as pd
    from src.pipeline.batch import process_batch
    from src.preprocessing.columns import normalize_columns

    logger.info("Loading input: %s", input_path)
    input_df = pd.read_csv(input_path, encoding="utf-8")

    # Accept real-world headers ("Part Number", "Description", ...) by mapping
    # them onto the canonical six-field schema before processing.
    input_df, col_report = normalize_columns(input_df)
    if col_report["mapped"]:
        logger.info("Column mapping: %s",
                    ", ".join(f"{o} -> {c}" for c, o in col_report["mapped"].items()))
    if col_report["missing"]:
        logger.warning("No matching column found for: %s (treated as empty)",
                       ", ".join(col_report["missing"]))

    logger.info("Processing %d rows (limit=%s, workers=%d)...",
                len(input_df), args.limit, args.workers)
    internal_json = _resolve(args.internal_json) if args.internal_json else None
    output_df = process_batch(
        input_df=input_df,
        master_path=master_path,
        output_path=output_path,
        limit=args.limit,
        internal_json_path=internal_json,
    )

    logger.info("Done. %d rows written to %s", len(output_df), output_path)
    print(f"\nPipeline complete: {len(output_df)} rows -> {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())