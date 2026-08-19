import os
import json
import logging
import pandas as pd
from typing import Optional, Tuple, List, Dict, Any

from src.pipeline.orchestrator import PipelineOrchestrator
from src.output.mapper import EXPECTED_OUTPUT_CSV, product_to_row

logger = logging.getLogger(__name__)


def _reorder_columns(output_df: pd.DataFrame) -> pd.DataFrame:
    """Re-order columns strictly according to the reference delivery format."""
    try:
        reference_df = pd.read_csv(EXPECTED_OUTPUT_CSV, nrows=0, encoding="utf-8")
        expected_columns = reference_df.columns.tolist()
        for col in expected_columns:
            if col not in output_df.columns:
                output_df[col] = ""
        return output_df[expected_columns]
    except Exception as e:
        logger.warning("Could not strictly reorder columns based on reference: %s", e)
        return output_df


def _run_rows(
    orchestrator: PipelineOrchestrator,
    input_df: pd.DataFrame,
    collect_internal: bool = False,
) -> Tuple[List[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
    """Run the orchestrator over every row. Returns (delivery_rows, internal_products)."""
    import concurrent.futures

    total = len(input_df)

    def _process_single(args):
        idx, row = args
        logger.info("Processing row %d/%d (MPN: %s)", idx + 1, total, row.get("Mfg_Part_Num", "N/A"))
        try:
            internal = orchestrator.build_internal_product(row.to_dict(), row_id=str(idx))
            mapped = product_to_row(internal)
            return mapped, (internal if collect_internal else None)
        except Exception as e:
            logger.error("Row %d failed: %s", idx + 1, e)
            return row.to_dict(), None

    delivery: List[Dict[str, Any]] = []
    internal: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for mapped, intern in executor.map(_process_single, input_df.iterrows()):
            delivery.append(mapped)
            if collect_internal and intern is not None:
                internal.append(intern)

    return delivery, (internal if collect_internal else None)


def process_batch(
    input_df: pd.DataFrame,
    master_path: str,
    output_path: str,
    limit: Optional[int] = None,
    internal_json_path: Optional[str] = None,
) -> pd.DataFrame:
    """
    Processes a batch of raw product rows using the PipelineOrchestrator,
    and writes the fully formed 252-column dataset to output_path.

    :param input_df: DataFrame containing raw input rows.
    :param master_path: Path to the manufacturer master Excel file.
    :param output_path: Where to save the output CSV.
    :param limit: Optional max number of rows to process (useful for testing).
    :param internal_json_path: Optional path to also write the rich internal
                               Product models (V1 — frontend data contract).
    """
    orchestrator = PipelineOrchestrator(master_path=master_path)

    if limit is not None:
        input_df = input_df.head(limit)

    delivery_rows, internal_products = _run_rows(
        orchestrator, input_df, collect_internal=internal_json_path is not None
    )

    output_df = pd.DataFrame(delivery_rows)
    output_df = _reorder_columns(output_df)

    # Create output dir if not exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    output_df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("Saved processed batch to %s", output_path)

    if internal_json_path is not None:
        os.makedirs(os.path.dirname(internal_json_path), exist_ok=True)
        with open(internal_json_path, "w", encoding="utf-8") as f:
            json.dump(internal_products, f, ensure_ascii=False, indent=2, default=str)
        logger.info("Saved internal product models (%d) to %s", len(internal_products), internal_json_path)

    return output_df