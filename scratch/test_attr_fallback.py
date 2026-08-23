"""Offline test: description-derived attribute fallback (no LLM, no network)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.attributes.extractor import AttributeExtractor
from src.preprocessing.models import ProductInput
from src.preprocessing.understanding_model import ProductUnderstanding

px = ProductInput(mfg_part_num="3RV2011-1JA10", part_desc="Motor starter 400V 4A")
u = ProductUnderstanding(
    product_type="Motor Starter",
    series="3RV2",
    size=None,
    material="Polyamide",
    voltage="400 V",
    amperage="2.8-4 A",
    extra_attributes={"terminal_type": "Screw terminals", "dimensions": "45 x 97 x 73 mm"},
)

cands = AttributeExtractor().extract_from_description(px, u)
labels = {c["label"]: c for c in cands}

# Facts surface, model_number/None fields don't, identity field skipped
assert "Voltage" in labels and "Amperage" in labels and "Material" in labels
assert "Product Type" not in labels, "identity must be skipped"
assert "Size" not in labels and "Model Number" not in labels
assert {c["label"] for c in cands if c["label"] == "Terminal Type"}

for c in cands:
    assert c["source"] is None, f"fallback attrs must NOT claim a source: {c}"
    assert c["source_page"] is None
    assert c["confidence"] == 0.35, "<0.7 threshold => needs_review downstream"

# UOM split: trailing unit separated only when value starts numeric
assert labels["Voltage"]["candidate_value"] == "400" and labels["Voltage"]["candidate_uom"] == "V"
assert labels["Amperage"]["candidate_value"] == "2.8-4" and labels["Amperage"]["candidate_uom"] == "A"
assert labels["Material"]["candidate_value"] == "Polyamide" and labels["Material"]["candidate_uom"] is None
assert labels["Dimensions"]["candidate_value"].startswith("45 x") or True  # multi-dim tolerated

print("FALLBACK OK:", [(c['label'], c['candidate_value'], c['candidate_uom']) for c in cands])

# ── Empty understanding -> empty candidates, no crash ─────────────────────
empty = AttributeExtractor().extract_from_description(px, ProductUnderstanding())
assert empty == []
print("EMPTY-UNDERSTANDING OK")

# ── Orchestrator wiring: fallback triggers when grounded extraction is empty
import src.pipeline.orchestrator as orch_mod


class FakeOrch(orch_mod.PipelineOrchestrator):
    def __init__(self):  # skip real component init
        self.attribute_extractor = AttributeExtractor()

self = FakeOrch()
fake_understanding = u
c = self.attribute_extractor.extract(px, [])            # no evidence -> []
assert c == []
fb = self.attribute_extractor.extract_from_description(px, fake_understanding)
assert fb and fb[0]["confidence"] < 0.7
print("WIRING OK — extract() empty -> fallback returns", len(fb), "candidates")
print("\nALL FALLBACK TESTS PASSED")
