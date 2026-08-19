import logging
from typing import Dict, Any, Optional

from src.preprocessing.models import ProductInput
from src.entity_resolution.manufacturer import ManufacturerResolver
from src.entity_resolution.brand import BrandResolver
from src.preprocessing.understanding import ProductUnderstandingExtractor
from src.classification.classifier import ProductClassifier
from src.source_discovery.discovery import ManufacturerSourceDiscovery
from src.rag.pipeline import RAGPipeline
from src.attributes.extractor import AttributeExtractor
from src.attributes.mapper import normalize_candidate_attribute
from src.content import ContentGenerator
from src.validation.validator import validate_product
from src.validation.confidence import compute_confidence
from src.output.mapper import product_to_row

logger = logging.getLogger(__name__)

# Approved UOM abbreviations for validation (subset of the UOM master).
KNOWN_UOMS: set = {
    "V", "A", "W", "kW", "in", "ft", "mm", "cm", "m", "lb", "kg", "oz", "g",
    "dBA", "dB", "%", "psi", "RPM", "CFM", "HP", "BTU", "BTUH", "hr", "min",
    "pc", "ea", "pk", "pr", "set", "kW-hr", "°F", "°C",
}


class PipelineOrchestrator:
    """
    T9 - Pipeline Orchestration
    Connects all the AI and deterministic components from start to finish.

    `build_internal_product` returns the rich internal Product model
    (V1 — what the frontend consumes).  `process_row` serialises that model
    into the exact 252-column delivery format.
    """

    def __init__(self, master_path: str):
        self.manufacturer_resolver = ManufacturerResolver(master_path)
        try:
            self.brand_resolver = BrandResolver(master_path)
        except Exception:
            logger.warning("BrandResolver unavailable; falling back to ManufacturerResolver")
            self.brand_resolver = self.manufacturer_resolver

        self.understanding_extractor = ProductUnderstandingExtractor()
        self.classifier = ProductClassifier()
        self.source_discovery = ManufacturerSourceDiscovery()
        self.rag_pipeline = RAGPipeline()
        self.attribute_extractor = AttributeExtractor()
        self.content_generator = ContentGenerator()

    # ------------------------------------------------------------------
    # Core: build the rich internal product model
    # ------------------------------------------------------------------

    def build_internal_product(self, raw_row: dict, row_id: str = "") -> Dict[str, Any]:
        """
        Run the full enrichment chain and return the internal Product dict:

            Product
            ├── Identity, Manufacturer, Brand, Classification
            ├── Attributes  (normalized, grounded, LOV-matched)
            ├── Descriptions, Features, Sources
            ├── Validation, Confidence, Review Status

        Raises on hard failure — callers decide how to degrade.
        """
        product_input = ProductInput.from_row(raw_row, row_id=row_id)
        internal_product: Dict[str, Any] = product_input.to_dict()

        # 2. Entity Resolution
        mfr_match = self.manufacturer_resolver.resolve(product_input.best_manufacturer)
        internal_product["manufacturer_name"] = (
            mfr_match.manufacturer_name or product_input.best_manufacturer
        )
        internal_product["manufacturer_code"] = mfr_match.manufacturer_code
        internal_product["manufacturer_confidence"] = mfr_match.confidence

        brand_match = self.brand_resolver.resolve(product_input.best_brand)
        internal_product["brand_name"] = brand_match.brand_name or product_input.best_brand
        internal_product["brand_code"] = brand_match.brand_code
        internal_product["brand_confidence"] = brand_match.confidence

        # 3. Product Understanding
        understanding = self.understanding_extractor.extract(product_input)

        # 4. Classification
        classification = self.classifier.classify(understanding)
        internal_product["classpath"] = classification.classpath
        internal_product["dept"] = classification.dept
        internal_product["class_name"] = classification.class_name
        internal_product["fine"] = classification.fine
        internal_product["classification_confidence"] = classification.confidence

        # 5. Manufacturer Source Discovery
        sources = self.source_discovery.discover(product_input, classification)
        internal_product["sources"] = sources

        # 6. RAG Pipeline
        queries = [
            f"{internal_product.get('manufacturer_name') or ''} {product_input.mfg_part_num or ''} specifications",
            f"{product_input.mfg_part_num or ''} dimensions",
        ]
        evidence_chunks = self.rag_pipeline.run(sources, queries, top_k=3)

        # 7. Attribute Extraction
        candidate_attributes = self.attribute_extractor.extract(product_input, evidence_chunks)

        # 8. Normalization
        normalized_attributes = []
        for candidate in candidate_attributes:
            attr = normalize_candidate_attribute(
                classpath=internal_product.get("classpath", ""),
                candidate=candidate,
            )
            normalized_attributes.append(attr.model_dump() if hasattr(attr, "model_dump") else attr.__dict__)
        internal_product["attributes"] = normalized_attributes

        # 9. Content Generation (Vedanth track: V2-V7)
        self.content_generator.generate(internal_product)

        # 10. Validation + Confidence (Yashas track: Y7-Y8)
        validation = validate_product(internal_product, known_uoms=KNOWN_UOMS)
        confidence = compute_confidence(
            internal_product,
            validation_result=validation,
            manufacturer_match_confidence=internal_product.get("manufacturer_confidence", 1.0),
            classification_confidence=internal_product.get("classification_confidence", 1.0),
        )
        internal_product["validation"] = validation
        internal_product["confidence"] = confidence
        internal_product["needs_review"] = confidence["needs_review"]

        return internal_product

    # ------------------------------------------------------------------
    # Delivery-format entry point
    # ------------------------------------------------------------------

    def process_row(self, raw_row: dict, row_id: str = "") -> Dict[str, Any]:
        """
        Process a single row into the 252-column delivery format.
        Gracefully degrades: on failure, raw input is passed through directly.
        """
        try:
            internal_product = self.build_internal_product(raw_row, row_id=row_id)
            return product_to_row(internal_product)
        except Exception as e:
            logger.exception("Failed to process row %s: %s", row_id, e)
            return product_to_row(raw_row)