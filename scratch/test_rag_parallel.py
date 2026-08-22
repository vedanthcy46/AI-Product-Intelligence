"""Offline test: RAG fetch is concurrent, order-stable, failure-isolated."""
import sys, os, time, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.pipeline import RAGPipeline
from src.source_discovery.discovery import SourceResult

LATENCY = 0.6  # simulated per-URL latency

class FakeResponse:
    def __init__(self, html): self.text = html
    def raise_for_status(self): pass

def fake_get(url, headers=None, timeout=None):
    assert timeout == 3.0, f"expected 3s default timeout, got {timeout}"
    if url.endswith("/boom"):
        raise ConnectionError(f"simulated outage {url}")
    time.sleep(LATENCY)
    return FakeResponse("<html><body>" + f"{url} specs pressure psi " * 60 + "</body></html>")

fake_requests = types.ModuleType("requests")
fake_requests.get = fake_get
fake_requests.RequestException = Exception
sys.modules["requests"] = fake_requests

import src.rag.pipeline as ragmod          # noqa: E402  (patch before use)
ragmod.requests = fake_requests

sources = [
    SourceResult(url=f"https://acme.com/p/{i}", manufacturer="Acme", mpn="AC-1",
                 document_type="product_page", confidence=0.7)
    for i in range(4)
] + [SourceResult(url="https://acme.com/boom", manufacturer="Acme", mpn="AC-1",
                  document_type="specification_sheet", confidence=0.7),
     SourceResult(url="https://acme.com/s.pdf", manufacturer="Acme", mpn="AC-1",
                  document_type="specification_sheet", confidence=0.7)]

statuses = []
t0 = time.monotonic()
docs = RAGPipeline()._fetch_documents_traced(sources, statuses)
elapsed = time.monotonic() - t0

assert len(docs) == 4, f"expected 4 fetched docs, got {len(docs)}"
assert [s["url"] for s in statuses] == [s.url for s in sources], "trace must preserve input order"
by_url = {s["url"]: s["status"] for s in statuses}
assert by_url["https://acme.com/boom"] == "failed"
assert by_url["https://acme.com/s.pdf"] == "pdf_skipped"
assert all(by_url[f"https://acme.com/p/{i}"] == "fetched" for i in range(4))
assert all(d.text_content.startswith("https") for d in docs)

serial_time = LATENCY * 5  # what the old sequential loop would have cost
print(f"elapsed={elapsed:.2f}s vs sequential floor={serial_time:.2f}s "
      f"(timeout env={os.getenv('RAG_FETCH_TIMEOUT', '3')})")
assert elapsed < LATENCY * 3, f"not actually parallel: {elapsed:.2f}s"

print("PARALLEL FETCH TEST PASSED")
