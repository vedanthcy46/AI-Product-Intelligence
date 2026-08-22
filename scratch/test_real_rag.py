import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.pipeline import RAGPipeline
from src.source_discovery.discovery import SourceResult

def test_real_pipeline():
    print("--- Testing Real Web Fetch RAGPipeline ---")
    pipeline = RAGPipeline(chunk_size=100, chunk_overlap=20)
    
    sources = [
        # Using a reliable test page
        SourceResult(url="https://example.com", manufacturer="Example", mpn="123", document_type="product_page", confidence=0.9),
    ]
    
    queries = ["domain"]
    
    chunks = pipeline.run(sources, queries, top_k=2)
    
    print(f"Pipeline retrieved {len(chunks)} chunks.")
    for i, c in enumerate(chunks):
        print(f"  Chunk {i+1} ({c.source_url}): {c.text}")
        
    assert len(chunks) > 0, "Pipeline failed to retrieve chunks from real web page."
    print("Real Web Fetch Pipeline Test Passed!\n")

if __name__ == "__main__":
    test_real_pipeline()
