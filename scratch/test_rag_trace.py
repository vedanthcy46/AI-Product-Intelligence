"""Offline verification: RAGPipeline.run_traced() trace shape + scoring,
with the network fetch monkeypatched to local fake documents."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.pipeline import RAGPipeline
from src.source_discovery.discovery import SourceResult
from src.rag.document import Document


def fake_fetch(self, sources, statuses_out=None):
    docs = [
        Document(url="https://acme.com/pdp/123", manufacturer="Acme", mpn="AC-100",
                 document_type="product_page",
                 text_content="The AC-100 brass coupling features a pressure rating of 150 psi "
                              "and a 3/8 inch thread size. Voltage rating is 120 V. " * 30),
        Document(url="https://acme.com/spec/123.pdf", manufacturer="Acme", mpn="AC-100",
                 document_type="specification_sheet", text_content="x" * 10),
    ]
    if statuses_out is not None:
        statuses_out.append({"url": docs[0].url, "document_type": "product_page",
                             "status": "fetched", "chars": len(docs[0].text_content)})
        statuses_out.append({"url": docs[1].url, "document_type": "specification_sheet",
                             "status": "pdf_skipped", "chars": None})
    return docs


RAGPipeline._fetch_documents_traced = fake_fetch

sources = [
    SourceResult(url="https://acme.com/pdp/123", manufacturer="Acme", mpn="AC-100",
                 document_type="product_page", confidence=0.7),
    SourceResult(url="https://acme.com/spec/123.pdf", manufacturer="Acme", mpn="AC-100",
                 document_type="specification_sheet", confidence=0.7),
]
queries = ["AC-100 specifications", "AC-100 dimensions"]

scored, trace = RAGPipeline().run_traced(sources, queries, top_k=2)

assert trace["chunks_indexed"] > 0, "chunks must be indexed"
assert len(trace["documents"]) == 2, "both source attempts traced"
assert trace["documents"][0]["status"] == "fetched"
assert trace["documents"][1]["status"] == "pdf_skipped"
assert [r["query"] for r in trace["retrievals"]] == queries
assert scored, "must retrieve evidence"
assert all(isinstance(c.text, str) and s >= 0 for c, s in scored)
assert all(scored[i][1] >= scored[i + 1][1] for i in range(len(scored) - 1)), "sorted desc by score"
assert all(set(e) == {"url", "document_type", "status", "chars"} for e in trace["documents"])

# backward compat: run() still returns plain chunks
plain = RAGPipeline().run(sources, queries, top_k=2)
assert plain and all(hasattr(c, "text") for c in plain)

print("TRACE OK:", {
    "docs": [(d["status"], d["chars"]) for d in trace["documents"]],
    "chunks_indexed": trace["chunks_indexed"],
    "evidence": [(c.page, s) for c, s in scored],
    "retrieval_hits": [[h["score"] for h in r["hits"]] for r in trace["retrievals"]],
})

# Simulate exactly what orchestrator stores on internal_product
rag_field = dict(trace)
rag_field["sources"] = [s.to_dict() for s in sources]
rag_field["evidence"] = [
    {"url": c.source_url, "document_type": c.document_type, "page": c.page,
     "score": s, "snippet": (c.text or "")[:400]}
    for c, s in scored
]
import json
json.dumps(rag_field)  # must serialize cleanly
print("ORCH FIELD OK:", list(rag_field.keys()))
