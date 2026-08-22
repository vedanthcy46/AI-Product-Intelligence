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
    progress_cb=None,
) -> Tuple[List[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
    """Run the orchestrator over every row. Returns (delivery_rows, internal_products).

    max_workers stays small by default: each row already fans out several
    Groq LLM calls and the global pacer (LLM_MIN_INTERVAL) serializes their
    starts against the token-per-minute cap. 3 workers overlap the parallel
    web-fetch phase of one row with the LLM phases of others; override with
    PIPELINE_WORKERS if your key allows more.
    """
    import concurrent.futures

    total = len(input_df)
    max_workers = int(os.getenv("PIPELINE_WORKERS", "3"))

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
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for mapped, intern in executor.map(_process_single, input_df.iterrows()):
            delivery.append(mapped)
            if collect_internal and intern is not None:
                internal.append(intern)
            done += 1
            if progress_cb is not None:
                try:
                    progress_cb(done, total)
                except Exception:
                    pass

    return delivery, (internal if collect_internal else None)


def process_batch(
    input_df: pd.DataFrame,
    master_path: Optional[str] = None,
    output_path: str = "",
    limit: Optional[int] = None,
    internal_json_path: Optional[str] = None,
    progress_cb=None,
) -> pd.DataFrame:
    """
    Processes a batch of raw product rows using the PipelineOrchestrator,
    and writes the fully formed 252-column dataset to output_path.

    :param input_df: DataFrame containing raw input rows.
    :param master_path: Optional path to the manufacturer master Excel file.
                        When missing/None the resolvers degrade to pass-through
                        mode (low confidence, flagged for review).
    :param output_path: Where to save the output CSV.
    :param limit: Optional max number of rows to process (useful for testing).
    :param internal_json_path: Optional path to also write the rich internal
                               Product models (V1 — frontend data contract).
    :param progress_cb: Optional callable(done, total) fired after each row.
    """
    orchestrator = PipelineOrchestrator(master_path=master_path)

    if limit is not None:
        input_df = input_df.head(limit)

    delivery_rows, internal_products = _run_rows(
        orchestrator, input_df, collect_internal=internal_json_path is not None,
        progress_cb=progress_cb,
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