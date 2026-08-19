import logging
from typing import Dict, Any, List

from src.preprocessing.models import ProductInput
from src.entity_resolution.manufacturer import ManufacturerResolver
# Assuming a similar resolver exists or we just use ManufacturerResolver for brands if they use same logic
from src.preprocessing.understanding import ProductUnderstandingExtractor
from src.classification.classifier import ProductClassifier
from src.source_discovery.discovery import ManufacturerSourceDiscovery
from src.rag.pipeline import RAGPipeline
from src.attributes.extractor import AttributeExtractor
from src.attributes.mapper import normalize_candidate_attribute
from src.output.mapper import product_to_row

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    """
    T9 - Pipeline Orchestration
    Connects all the AI and deterministic components from start to finish.
    """

    def __init__(self, master_path: str):
        self.manufacturer_resolver = ManufacturerResolver(master_path)
        # Note: BrandResolver might exist, we fallback to ManufacturerResolver if not, 
        # as they both read from the same master file usually.
        try:
            from src.entity_resolution.brand import BrandResolver
            self.brand_resolver = BrandResolver(master_path)
        except ImportError:
            self.brand_resolver = self.manufacturer_resolver

        self.understanding_extractor = ProductUnderstandingExtractor()
        self.classifier = ProductClassifier()
        self.source_discovery = ManufacturerSourceDiscovery()
        self.rag_pipeline = RAGPipeline()
        self.attribute_extractor = AttributeExtractor()

    def process_row(self, raw_row: dict, row_id: str = "") -> Dict[str, Any]:
        """
        Process a single row from raw catalogue into the 252-column format.
        """
        try:
            # 1. Preprocessing
            product_input = ProductInput.from_row(raw_row, row_id=row_id)
            internal_product: Dict[str, Any] = product_input.to_dict()

            # 2. Entity Resolution
            mfr_match = self.manufacturer_resolver.resolve(product_input.best_manufacturer)
            internal_product["manufacturer_name"] = mfr_match.manufacturer_name or product_input.best_manufacturer
            
            # Using best brand signal
            brand_match = self.brand_resolver.resolve(product_input.best_brand)
            internal_product["brand_name"] = brand_match.brand_name or product_input.best_brand

            # 3. Product Understanding
            understanding = self.understanding_extractor.extract(product_input)
            
            # 4. Classification
            classification = self.classifier.classify(understanding)
            internal_product["classpath"] = classification.classpath
            internal_product["dept"] = classification.dept
            internal_product["class_name"] = classification.class_name
            internal_product["fine"] = classification.fine

            # 5. Manufacturer Source Discovery
            sources = self.source_discovery.discover(product_input, classification)
            
            # 6. RAG Pipeline
            queries = [
                f"{internal_product['manufacturer_name']} {product_input.mfg_part_num} specifications",
                f"{product_input.mfg_part_num} dimensions"
            ]
            evidence_chunks = self.rag_pipeline.run(sources, queries, top_k=3)

            # 7. Attribute Extraction
            candidate_attributes = self.attribute_extractor.extract(product_input, evidence_chunks)

            # 8. Normalization
            normalized_attributes = []
            for candidate in candidate_attributes:
                # normalize_candidate_attribute returns an Attribute dataclass
                attr = normalize_candidate_attribute(
                    classpath=internal_product.get("classpath", ""),
                    candidate=candidate
                )
                normalized_attributes.append(attr.dict() if hasattr(attr, "dict") else attr.__dict__)
            
            internal_product["attributes"] = normalized_attributes

            # 9. Output Generation
            final_row = product_to_row(internal_product)
            return final_row

        except Exception as e:
            logger.exception("Failed to process row %s: %s", row_id, e)
            # Graceful degradation: pass input fields directly to output mapper
            return product_to_row(raw_row)
