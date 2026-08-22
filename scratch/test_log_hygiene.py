"""Verify: single delivery-format warning, aggregated RAG fetch summary."""
import sys, os, types, time, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 1. Delivery-format warning fires exactly ONCE across repeated batches ──
records = []
h = logging.Handler()
h.emit = lambda r: records.append(r.getMessage())
logging.getLogger("src.output.mapper").addHandler(h)
logging.getLogger("src.output.mapper").setLevel(logging.INFO)

import pandas as pd
from src.pipeline.batch import _reorder_columns
from src.output.mapper import get_expected_headers

df = pd.DataFrame([{"Mfg_Part_Num": "X-1", "Part_Desc": "widget"}])
for _ in range(3):
    out = _reorder_columns(df.copy())

warnings = [m for m in records if "Delivery format reference" in m]
assert len(warnings) == 1, f"expected 1 warning, got {len(warnings)}: {warnings}"
assert len(out.columns) == len(get_expected_headers())
assert list(out.columns) == get_expected_headers()
print(f"1 OK reorder: {len(out.columns)} cols, exactly 1 fallback warning")

# ── 2. RAG fetch logs ONE summary line, statuses carry error reasons ───────
class FakeResponse:
    def __init__(self): self.text = "<html><body>" + "spec psi " * 40 + "</body></html>"
    def raise_for_status(self): pass

def flaky_get(url, headers=None, timeout=None):
    if url.endswith("/dead1"):
        raise Exception("404 Client Error: Not Found")
    if url.endswith("/dead2"):
        raise Exception("403 Client Error: Forbidden")
    if url.endswith("/thin"):
        class Thin:  # page exists but has almost no usable text
            text = "hi"
            def raise_for_status(self): pass
        return Thin()
    time.sleep(0)
    class R(FakeResponse):
        def __init__(self):
            self.text = "<html><body>" + f"{url} pressure specs " * 60 + "</body></html>"
        def raise_for_status(self): pass
    return R()

fake_requests = types.ModuleType("requests")
fake_requests.get = flaky_get
fake_requests.RequestException = Exception
sys.modules["requests"] = fake_requests
import src.rag.pipeline as ragmod
ragmod.requests = fake_requests

from src.rag.pipeline import RAGPipeline
from src.source_discovery.discovery import SourceResult

sources = [
    SourceResult(url="https://x.com/ok", manufacturer="M", mpn="P", document_type="product_page", confidence=0.7),
    SourceResult(url="https://x.com/dead1", manufacturer="M", mpn="P", document_type="product_page", confidence=0.7),
    SourceResult(url="https://x.com/dead2", manufacturer="M", mpn="P", document_type="catalogue", confidence=0.7),
    SourceResult(url="https://x.com/thin", manufacturer="M", mpn="P", document_type="technical_doc", confidence=0.7),
]

rag_logs = []
rh = logging.Handler(); rh.emit = lambda r: rag_logs.append((r.levelname, r.getMessage()))
lg = logging.getLogger("src.rag.pipeline"); lg.addHandler(rh); lg.setLevel(logging.INFO)

statuses = []
docs = RAGPipeline()._fetch_documents_traced(sources, statuses)

warn_or_info = [(lvl, m) for lvl, m in rag_logs if lvl in ("INFO", "WARNING") and "RAG fetch" in m]
assert len(warn_or_info) == 1, f"expected exactly 1 summary line, got {warn_or_info}"
print("2 OK summary line:", warn_or_info[0][1])

by_url = {s["url"]: s for s in statuses}
assert by_url["https://x.com/dead1"]["error"].startswith("Exception: 404")
assert by_url["https://x.com/dead2"]["error"].startswith("Exception: 403")
assert by_url["https://x.com/thin"]["status"] == "failed"
assert "no usable text" in by_url["https://x.com/thin"]["error"]
assert by_url["https://x.com/ok"]["status"] == "fetched" and "error" not in by_url["https://x.com/ok"]
assert len(docs) == 1
print("   error fields:", [by_url[u]["error"][:44] for u in by_url if "error" in by_url[u]])
print("\nALL LOG-HYGIENE TESTS PASSED")
