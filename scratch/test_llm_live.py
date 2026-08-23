"""Live LLM check: run ONE raw row through the orchestrator.

Prints what the AI stages produced. Does NOT touch frontend/data or
data/processed/products.json.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))

import pandas as pd

from src.pipeline.orchestrator import PipelineOrchestrator

INPUT = os.path.join(ROOT, "data", "raw", "Unihack_ Sample Dataset - Input.csv")

df = pd.read_csv(INPUT, encoding="utf-8").head(1)
row = df.iloc[0].to_dict()
print("input row:", {k: v for k, v in row.items()})
print("GROQ_API_KEY set:", bool(os.getenv("GROQ_API_KEY")))

orch = PipelineOrchestrator(master_path=None)
product = orch.build_internal_product(row, row_id="smoke-0")

print("\n--- RESULT ---")
print("classpath:", product.get("classpath"), "| conf:", product.get("classification_confidence"))
print("manufacturer:", product.get("manufacturer_name"), "| conf:", product.get("manufacturer_confidence"))
print("brand:", product.get("brand_name"))
print("sources:", len(product.get("sources") or []))
for s in (product.get("sources") or [])[:3]:
    d = s.to_dict() if hasattr(s, "to_dict") else s
    print("   ", d.get("source_url"), d.get("document_type"))
print("attributes:", len(product.get("attributes") or []))
for a in (product.get("attributes") or [])[:5]:
    print("   ", a.get("label"), "=", a.get("value"), a.get("uom") or "", "| src:", a.get("source"))
print("descriptions:", {k: (v[:60] + "..." if len(str(v)) > 60 else v) for k, v in (product.get("descriptions") or {}).items()})
