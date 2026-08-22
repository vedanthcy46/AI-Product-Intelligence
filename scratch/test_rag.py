import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.document import Document, Chunk
from src.rag.retriever import SimpleRetriever
from src.rag.pipeline import RAGPipeline
from src.source_discovery.discovery import SourceResult

def test_retriever():
    print("--- Testing SimpleRetriever ---")
    chunks = [
        Chunk(text="This product is a stainless steel pipe fitting.", source_url="url1", manufacturer="Acme", mpn="123", document_type="spec", page=1),
        Chunk(text="The operating voltage is 120V and amperage is 15A.", source_url="url2", manufacturer="Acme", mpn="123", document_type="spec", page=2),
        Chunk(text="Dimensions are 10 inches by 5 inches.", source_url="url3", manufacturer="Acme", mpn="123", document_type="spec", page=3),
    ]
    retriever = SimpleRetriever(chunks)
    
    # Test a query that should match chunk 2
    query = "voltage and amperage"
    results = retriever.search(query)
    
    print(f"Query: '{query}'")
    for chunk, score in results:
        print(f"  Score: {score:.4f} | Text: {chunk.text}")
        
    assert "120V" in results[0][0].text, "Retriever failed to fetch correct chunk."
    print("Retriever Test Passed!\n")

def test_pipeline():
    print("--- Testing RAGPipeline ---")
    pipeline = RAGPipeline(chunk_size=10, chunk_overlap=2)
    
    sources = [
        SourceResult(url="http://acme.com/spec", manufacturer="Acme", mpn="123", document_type="specification_sheet", confidence=0.9),
    ]
    
    queries = ["voltage dimensions"]
    
    chunks = pipeline.run(sources, queries, top_k=2)
    
    print(f"Pipeline retrieved {len(chunks)} chunks.")
    for i, c in enumerate(chunks):
        print(f"  Chunk {i+1}: {c.text}")
        
    assert len(chunks) > 0, "Pipeline failed to retrieve chunks."
    print("Pipeline Test Passed!\n")

if __name__ == "__main__":
    test_retriever()
    test_pipeline()
