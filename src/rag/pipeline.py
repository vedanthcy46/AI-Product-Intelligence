import concurrent.futures
import logging
import os
from typing import List, Optional, Tuple

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
        scored, _trace = self.run_traced(sources, queries, top_k=top_k)
        return [chunk for chunk, _score in scored]

    def run_traced(
        self,
        sources: List[SourceResult],
        queries: List[str],
        top_k: int = 5,
    ) -> Tuple[List[Tuple[Chunk, float]], dict]:
        """
        Same as run(), but also returns a trace of what happened at every stage:

            {
              "queries": [...],
              "documents": [{url, document_type, status, chars}, ...],
              "chunks_indexed": N,
              "retrievals": [{query, hits: [{page, score}, ...]}, ...],
            }

        The trace powers the RAG Evidence view in the frontend — every chunk
        handed to attribute extraction can be shown with its source URL, page
        and BM25 score.
        """
        trace: dict = {
            "queries": list(queries or []),
            "documents": [],
            "chunks_indexed": 0,
            "retrievals": [],
        }
        if not sources or not queries:
            return [], trace

        documents = self._fetch_documents_traced(sources, trace["documents"])
        if not documents:
            return [], trace

        chunks = self._chunk_documents(documents)
        trace["chunks_indexed"] = len(chunks)
        if not chunks:
            return [], trace

        retriever = SimpleRetriever(chunks)

        relevant: List[Chunk] = []
        best_score: dict = {}
        seen = set()

        for query in queries:
            results = retriever.search(query, top_k=top_k)
            hits = []
            for chunk, score in results:
                # Use a simple tuple of (url, page, text) to deduplicate chunks
                sig = (chunk.source_url, chunk.page, chunk.text)
                hits.append({"url": chunk.source_url, "page": chunk.page, "score": round(score, 2)})
                if score > best_score.get(sig, 0.0):
                    best_score[sig] = score
                if sig not in seen:
                    seen.add(sig)
                    relevant.append(chunk)
            trace["retrievals"].append({"query": query, "hits": hits})

        scored = [(chunk, round(best_score[(chunk.source_url, chunk.page, chunk.text)], 2))
                  for chunk in relevant]
        # Sort by relevance score descending so the strongest evidence comes first.
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored, trace

    def _fetch_documents(self, sources: List[SourceResult]) -> List[Document]:
        docs, _statuses = self._fetch_documents_traced(sources)
        return docs

    def _fetch_documents_traced(
        self, sources: List[SourceResult], statuses_out: Optional[List[dict]] = None
    ) -> List[Document]:
        """
        Downloads and extracts text from URLs using requests and BeautifulSoup.

        Sources are fetched CONCURRENTLY — hallucinated/unreachable URLs used
        to burn their full timeout one after another (5 URLs x 5s = ~25s per
        row); in parallel the row now waits at most one timeout (~3s).

        When statuses_out is provided, records one status entry per attempted
        source (in input order): fetched | failed | pdf_skipped.
        """
        import requests
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        timeout = float(os.getenv("RAG_FETCH_TIMEOUT", "3"))
        max_workers = max(1, int(os.getenv("RAG_FETCH_WORKERS", "4")))

        def _attempt(src: SourceResult) -> Tuple[Optional[Document], dict]:
            url = src.url
            try:
                # Basic PDF detection by extension - gracefully skip parsing raw PDFs for now unless needed
                if url.lower().endswith(".pdf"):
                    logger.info(f"Skipping PDF parsing for {url} (add PyMuPDF if PDF support is needed).")
                    return None, {"url": url, "document_type": src.document_type,
                                  "status": "pdf_skipped", "chars": None}

                response = requests.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Strip out script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.extract()

                text = soup.get_text(separator=" ", strip=True)

                # Only keep docs that actually have text
                if text and len(text) > 50:
                    doc = Document(
                        url=src.url,
                        manufacturer=src.manufacturer,
                        mpn=src.mpn,
                        document_type=src.document_type,
                        text_content=text
                    )
                    return doc, {"url": url, "document_type": src.document_type,
                                 "status": "fetched", "chars": len(text)}
                return None, {"url": url, "document_type": src.document_type,
                              "status": "failed", "chars": len(text or "")}
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")
                return None, {"url": url, "document_type": src.document_type,
                              "status": "failed", "chars": None}

        docs: List[Document] = []
        statuses: List[dict] = []

        # executor.map preserves input order, so trace entries stay aligned
        # with the discovered source list regardless of completion order.
        if not sources:
            return []
        workers = max(1, min(max_workers, len(sources)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(_attempt, sources))

        for doc, status in results:
            statuses.append(status)
            if doc is not None:
                docs.append(doc)

        if statuses_out is not None:
            statuses_out.extend(statuses)
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
