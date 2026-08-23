import os
import sys
import pandas as pd
from unittest.mock import patch
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.document import Chunk, Document
from src.rag.retriever import SimpleRetriever
from src.rag.pipeline import RAGPipeline
from src.attributes.extractor import AttributeExtractor
from src.source_discovery.discovery import SourceResult
from src.preprocessing.models import ProductInput
from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.batch import process_batch

# Suppress overly verbose logs for chaos testing
logging.basicConfig(level=logging.ERROR)

def run_tests():
    errors_found = []

    print("--- 1. Testing Retriever with Edge Cases ---")
    try:
        # Edge case: Empty chunks
        retriever_empty = SimpleRetriever([])
        res = retriever_empty.search("test")
        assert res == [], "Empty retriever should return empty list."
        
        # Edge case: Chunks with no text or only whitespace
        retriever_ws = SimpleRetriever([Chunk(text="   ", source_url="a", manufacturer="a", mpn="1", document_type="a", page=1)])
        res = retriever_ws.search("test")
        assert res == [], "Whitespace chunks should return empty list."
        
        # Edge case: Query with no matching words
        chunks = [Chunk(text="apple banana", source_url="a", manufacturer="a", mpn="1", document_type="a", page=1)]
        retriever = SimpleRetriever(chunks)
        res = retriever.search("orange")
        assert res == [], "Non-matching query should return empty list."
    except Exception as e:
        errors_found.append(f"Retriever crashed: {e}")

    print("--- 2. Testing RAGPipeline Fetcher with Garbage URLs ---")
    try:
        pipeline = RAGPipeline()
        garbage_sources = [
            SourceResult(url="http://this-does-not-exist.12345", manufacturer="a", mpn="1", document_type="a", confidence=1.0),
            SourceResult(url="invalid-url", manufacturer="a", mpn="1", document_type="a", confidence=1.0),
        ]
        # This should handle exceptions and return empty document list
        docs = pipeline._fetch_documents(garbage_sources)
        assert docs == [], "Garbage URLs should be caught and return empty docs."
    except Exception as e:
        errors_found.append(f"RAGPipeline _fetch_documents crashed: {e}")

    print("--- 3. Testing AttributeExtractor with weird JSON responses ---")
    try:
        extractor = AttributeExtractor()
        product = ProductInput(mfg_part_num="123")
        
        # Test missing GROQ_API_KEY
        os.environ.pop("GROQ_API_KEY", None)
        res = extractor.extract(product, [Chunk(text="test", source_url="a", manufacturer="a", mpn="1", document_type="a", page=1)])
        assert res == [], "Missing API key should return empty list without crashing."
    except Exception as e:
        errors_found.append(f"AttributeExtractor crashed on missing API key: {e}")

    print("--- 4. Testing Orchestrator with Missing/Garbage Input ---")
    try:
        # Mock pd.read_excel and mapper
        import src.output.mapper as mapper
        mapper.get_expected_headers = lambda x=None: ["Mfg_Part_Num", "Part_Desc"]
        pd.read_excel = lambda *a, **k: pd.DataFrame(columns=["Manufacturer_Name", "Manufacturer_Code"])
        
        orchestrator = PipelineOrchestrator("dummy.xlsx")
        
        # Missing keys completely
        res1 = orchestrator.process_row({})
        assert isinstance(res1, dict)
        
        # None values
        res2 = orchestrator.process_row({"Mfg_Part_Num": None, "Part_Desc": None})
        assert isinstance(res2, dict)
        
        # Weird types
        res3 = orchestrator.process_row({"Mfg_Part_Num": 123, "Part_Desc": ["weird", "list"]})
        assert isinstance(res3, dict)
    except Exception as e:
        errors_found.append(f"Orchestrator crashed on garbage input: {e}")
        
    print("--- 5. Testing Batch Processor with Empty / Weird DataFrame ---")
    try:
        df_empty = pd.DataFrame()
        out_empty = process_batch(df_empty, "dummy.xlsx", "scratch/test_out.csv")
        assert out_empty.empty, "Empty input should yield empty output."
        
        df_weird = pd.DataFrame([{"Not_A_Real_Col": "test"}])
        out_weird = process_batch(df_weird, "dummy.xlsx", "scratch/test_out.csv")
        assert not out_weird.empty, "Weird column input should still output a row with default schemas."
    except Exception as e:
        errors_found.append(f"Batch Processor crashed: {e}")

    if errors_found:
        print("\n=== MINOR BUGS FOUND ===")
        for err in errors_found:
            print(f"- {err}")
        sys.exit(1)
    else:
        print("\n=== ALL CHAOS TESTS PASSED. NO CRASHES ===")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
