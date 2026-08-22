import math
from collections import Counter
import re
from typing import List, Tuple

from src.rag.document import Chunk

class SimpleRetriever:
    """
    A lightweight BM25-inspired tf-idf retriever using standard library only.
    Designed for small document corpora (per-product retrieval).
    """

    def __init__(self, chunks: List[Chunk]):
        self.chunks = chunks
        self.tokenized_docs = [self._tokenize(chunk.text) for chunk in chunks]
        self.doc_freqs = self._compute_df()
        self.avg_dl = sum(len(doc) for doc in self.tokenized_docs) / max(1, len(self.tokenized_docs))
        self.N = len(self.chunks)
        
        # BM25 parameters
        self.k1 = 1.5
        self.b = 0.75

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r'\b\w+\b', text.lower())

    def _compute_df(self) -> Counter:
        df = Counter()
        for doc in self.tokenized_docs:
            for token in set(doc):
                df[token] += 1
        return df

    def _idf(self, token: str) -> float:
        n_q = self.doc_freqs.get(token, 0)
        # Standard BM25 IDF formulation
        return math.log((self.N - n_q + 0.5) / (n_q + 0.5) + 1.0)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        query_tokens = self._tokenize(query)
        if not query_tokens or not self.chunks:
            return []

        scores = []
        for i, (chunk, doc_tokens) in enumerate(zip(self.chunks, self.tokenized_docs)):
            score = 0.0
            doc_len = len(doc_tokens)
            doc_counts = Counter(doc_tokens)

            for token in query_tokens:
                if token not in doc_counts:
                    continue
                tf = doc_counts[token]
                idf = self._idf(token)
                
                # BM25 term frequency normalization
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / max(1, self.avg_dl)))
                
                score += idf * (numerator / denominator)
            
            scores.append((score, chunk))

        # Sort by score descending
        scores.sort(key=lambda x: x[0], reverse=True)
        
        # Return top-K non-zero scoring chunks
        results = []
        for score, chunk in scores:
            if score > 0:
                results.append((chunk, score))
                if len(results) >= top_k:
                    break
        
        return results
