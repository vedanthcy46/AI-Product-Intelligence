import os
import sys

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pandas as pd
from src.pipeline.orchestrator import PipelineOrchestrator
import src.output.mapper as mapper

def main():
    print("Testing PipelineOrchestrator...")
    
    # Mock get_expected_headers
    def mock_get_expected_headers(path=None):
        return [
            "Mfg_Part_Num", "Part_Desc", "MANUFACTURER_NAME", "BRAND_NAME", 
            "Classpath", "Dept", "Class", "Fine", "MFR URL",
            "ATTRIBUTE_LABEL 1", "ATTRIBUTE_VALUE 1", "ATTRIBUTE_UOM 1"
        ]
    mapper.get_expected_headers = mock_get_expected_headers
    
    # Mock pd.read_excel to avoid FileNotFoundError
    original_read_excel = pd.read_excel
    def mock_read_excel(*args, **kwargs):
        return pd.DataFrame(columns=["Manufacturer_Name", "Manufacturer_Code"])
    pd.read_excel = mock_read_excel
    
    master_path = "dummy_path.xlsx"
        
    import src.attributes.extractor as attr_ext
    original_extract = attr_ext.AttributeExtractor.extract
    
    def mock_extract(self, product, chunks):
        return [
            {"label": "Material", "candidate_value": "Stainless Steel", "candidate_uom": None, "source": "mock", "source_page": 1, "confidence": 0.95},
            {"label": "Voltage Rating", "candidate_value": "120", "candidate_uom": "V", "source": "mock", "source_page": 2, "confidence": 0.88}
        ]
    attr_ext.AttributeExtractor.extract = mock_extract
    
    from src.pipeline.batch import process_batch
    
    input_df = pd.DataFrame([
        {"Mfg_Part_Num": "12345", "Part_Desc": "1/2 IN BRASS COUPLING", "Part_Manuf": "Acme Corp"},
        {"Mfg_Part_Num": "67890", "Part_Desc": "3/4 IN STEEL FLANGE", "Part_Manuf": "Acme Corp"}
    ])
    
    print("\nRunning multi-threaded batch processor...")
    output_df = process_batch(input_df, master_path="dummy_path.xlsx", output_path="scratch/test_output.csv")
    
    print(f"\nBatch processing complete. Output shape: {output_df.shape}")
    print("Test finished.")

if __name__ == "__main__":
    main()
