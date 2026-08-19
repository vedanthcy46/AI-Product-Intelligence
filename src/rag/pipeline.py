import logging
from typing import List, Optional

from src.rag.document import Document, Chunk
from src.rag.retriever import SimpleRetriever
from src.source_discovery.discovery import SourceResult
from src.preprocessing.models import ProductInput
from src.classification.classifier import ClassificationResult

logger = logging.getLogger(__name__)

class RAGPipeline:
    """
    T7 - RAG Pipeline
    Orchestrates downloading (mocked for now), chunking, and retrieving 
    relevant chunks of evidence from manufacturer sources.
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def run(
        self, 
        sources: List[SourceResult], 
        queries: List[str], 
        top_k: int = 5
    ) -> List[Chunk]:
        """
        Main entry point for the RAG pipeline.
        Fetches documents for the given sources, chunks them, and retrieves top-k chunks for queries.
        """
        if not sources or not queries:
            return []

        documents = self._fetch_documents(sources)
        if not documents:
            return []

        chunks = self._chunk_documents(documents)
        if not chunks:
            return []

        retriever = SimpleRetriever(chunks)
        
        # We can either score chunks against all queries, or use a combined query.
        # Here we just combine the queries into a larger search text for the retriever,
        # or score individually and take the union of top-K. We will score individually.
        relevant_chunks = []
        seen = set()
        
        for query in queries:
            results = retriever.search(query, top_k=top_k)
            for chunk, score in results:
                # Use a simple tuple of (url, page, text) to deduplicate chunks
                sig = (chunk.source_url, chunk.page, chunk.text)
                if sig not in seen:
                    seen.add(sig)
                    relevant_chunks.append(chunk)

        # Sort by relevance? For now, order of queries gives rough priority.
        # We limit to `top_k * len(queries)` total chunks.
        return relevant_chunks

    def _fetch_documents(self, sources: List[SourceResult]) -> List[Document]:
        """
        Downloads and extracts text from URLs using requests and BeautifulSoup.
        """
        import requests
        from bs4 import BeautifulSoup

        docs = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        for src in sources:
            url = src.url
            try:
                # Basic PDF detection by extension - gracefully skip parsing raw PDFs for now unless needed
                if url.lower().endswith(".pdf"):
                    logger.info(f"Skipping PDF parsing for {url} (add PyMuPDF if PDF support is needed).")
                    continue
                    
                response = requests.get(url, headers=headers, timeout=5)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Strip out script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.extract()
                    
                text = soup.get_text(separator=" ", strip=True)
                
                # Only keep docs that actually have text
                if text and len(text) > 50:
                    docs.append(Document(
                        url=src.url,
                        manufacturer=src.manufacturer,
                        mpn=src.mpn,
                        document_type=src.document_type,
                        text_content=text
                    ))
            except requests.RequestException as e:
                logger.warning(f"Failed to fetch {url}: {e}")
                
        return docs

    def _chunk_documents(self, documents: List[Document]) -> List[Chunk]:
        """
        Splits text content of documents into overlapping chunks.
        """
        chunks = []
        for doc in documents:
            text = doc.text_content
            # Very basic chunking by words
            words = text.split()
            
            i = 0
            page_counter = 1
            while i < len(words):
                chunk_words = words[i : i + self.chunk_size]
                chunk_text = " ".join(chunk_words)
                
                if chunk_text.strip():
                    chunks.append(Chunk(
                        text=chunk_text,
                        source_url=doc.url,
                        manufacturer=doc.manufacturer,
                        mpn=doc.mpn,
                        document_type=doc.document_type,
                        page=page_counter
                    ))
                
                i += (self.chunk_size - self.chunk_overlap)
                page_counter += 1
                
        return chunks
