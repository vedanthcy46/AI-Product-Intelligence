import os
import logging
import pandas as pd
from typing import Optional

from src.pipeline.orchestrator import PipelineOrchestrator
from src.output.mapper import EXPECTED_OUTPUT_CSV

logger = logging.getLogger(__name__)

def process_batch(
    input_df: pd.DataFrame, 
    master_path: str,
    output_path: str, 
    limit: Optional[int] = None
) -> pd.DataFrame:
    """
    Processes a batch of raw product rows using the PipelineOrchestrator,
    and writes the fully formed 252-column dataset to output_path.
    
    :param input_df: DataFrame containing raw input rows.
    :param master_path: Path to the manufacturer master Excel file.
    :param output_path: Where to save the output CSV.
    :param limit: Optional max number of rows to process (useful for testing).
    """
    import concurrent.futures

    orchestrator = PipelineOrchestrator(master_path=master_path)
    
    if limit is not None:
        input_df = input_df.head(limit)
        
    results = []
    total = len(input_df)
    
    def _process_single(args):
        idx, row = args
        logger.info(f"Processing row {idx + 1}/{total} (MPN: {row.get('Mfg_Part_Num', 'N/A')})")
        try:
            return orchestrator.process_row(row.to_dict(), row_id=str(idx))
        except Exception as e:
            logger.error(f"Row {idx + 1} failed: {e}")
            return row.to_dict()  # fallback

    # Execute in parallel to maximize throughput
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = executor.map(_process_single, input_df.iterrows())
        for res in futures:
            results.append(res)
        
    output_df = pd.DataFrame(results)
    
    # Re-order columns strictly according to the reference format if possible
    try:
        reference_df = pd.read_csv(EXPECTED_OUTPUT_CSV, nrows=0, encoding="utf-8")
        expected_columns = reference_df.columns.tolist()
        
        # Ensure all expected columns exist, fill with "" if missing
        for col in expected_columns:
            if col not in output_df.columns:
                output_df[col] = ""
                
        # Reorder
        output_df = output_df[expected_columns]
    except Exception as e:
        logger.warning(f"Could not strictly reorder columns based on reference: {e}")
    
    # Create dir if not exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    output_df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"Saved processed batch to {output_path}")
    
    return output_df
