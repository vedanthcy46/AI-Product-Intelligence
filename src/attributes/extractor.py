import os
import re
import json
import logging
from typing import List, Dict, Any, Optional

from src.preprocessing.models import ProductInput
from src.preprocessing.understanding_model import ProductUnderstanding
from src.rag.document import Chunk
from src.llm_config import call_with_retry, completion_kwargs, get_chat_model

logger = logging.getLogger(__name__)

class AttributeExtractor:
    """
    T8 - RAG-Grounded Attribute Extraction
    Takes a product and a list of evidence chunks, and uses an LLM to extract
    candidate attributes.
    """

    def __init__(self, target_labels: Optional[List[str]] = None):
        """
        :param target_labels: Optional list of attribute labels to try and extract explicitly.
                              If None, LLM will extract whatever it finds.
        """
        self.target_labels = target_labels or [
            "Material", "Voltage", "Color", "Length", "Width", 
            "Height", "Weight", "Finish", "Amperage", "Power"
        ]

    def extract(self, product: ProductInput, evidence_chunks: List[Chunk]) -> List[Dict[str, Any]]:
        """
        Extracts candidate attributes grounded in the provided evidence.
        """
        if not evidence_chunks:
            return []

        try:
            import groq
        except ImportError:
            logger.error("groq not installed. Cannot extract attributes.")
            return []

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY not set. Skipping extraction.")
            return []

        # Prepare context from evidence
        context_parts = []
        for i, chunk in enumerate(evidence_chunks):
            # Include source and page for grounding citation
            context_parts.append(
                f"--- Evidence [{i+1}] ---\n"
                f"Source: {chunk.source_url} (Page {chunk.page})\n"
                f"Content: {chunk.text}\n"
            )
        context_text = "\n".join(context_parts)

        labels_text = ", ".join(self.target_labels)
        
        prompt = (
            f"You are a product data extraction expert. Given the following product and manufacturer evidence, "
            f"extract technical attributes.\n\n"
            f"Product MPN: {product.mfg_part_num or 'Unknown'}\n"
            f"Product Description: {product.part_desc or 'Unknown'}\n\n"
            f"Target Attribute Labels to look for (if present): {labels_text}\n\n"
            f"EVIDENCE CONTEXT:\n{context_text}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Extract any relevant technical attributes you find in the evidence.\n"
            f"2. For each attribute, provide the exact source URL and Page number where you found it (from the Evidence blocks above).\n"
            f"3. Split the value into 'candidate_value' (the number or text) and 'candidate_uom' (the unit of measure, if any).\n"
            f"4. Provide a 'confidence' score between 0.0 and 1.0.\n"
            f"5. Output ONLY a JSON object with a key 'attributes' containing a list of the extracted attribute objects.\n\n"
            f"JSON Schema for each object in the 'attributes' list:\n"
            f"{{\n"
            f"  \"label\": \"string\",\n"
            f"  \"candidate_value\": \"string\",\n"
            f"  \"candidate_uom\": \"string or null\",\n"
            f"  \"source\": \"string (URL)\",\n"
            f"  \"source_page\": \"integer\",\n"
            f"  \"confidence\": \"float\"\n"
            f"}}\n"
        )

        try:
            client = groq.Groq(api_key=api_key)
            response = call_with_retry(
                lambda: client.chat.completions.create(
                    model=get_chat_model(),
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0,
                    **completion_kwargs(get_chat_model(), 800),
                ),
                what="attribute extraction",
            )
            raw = response.choices[0].message.content.strip()
            
            data = json.loads(raw)
            attributes = data.get("attributes", [])
            
            if not isinstance(attributes, list):
                return []
                
            # Validate format softly
            valid_attributes = []
            for attr in attributes:
                if "label" in attr and "candidate_value" in attr:
                    valid_attributes.append({
                        "label": str(attr.get("label", "")),
                        "candidate_value": str(attr.get("candidate_value", "")),
                        "candidate_uom": attr.get("candidate_uom"),
                        "source": attr.get("source"),
                        "source_page": attr.get("source_page"),
                        "confidence": float(attr.get("confidence", 0.5)),
                    })
                    
            return valid_attributes
            
        except Exception as e:
            logger.error("LLM attribute extraction failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Fallback: description-derived candidates (no web evidence required)
    # ------------------------------------------------------------------

    # Understanding field -> display label. model_number is skipped on
    # purpose: it duplicates the MPN column.
    _FIELD_LABELS = {
        "material": "Material",
        "size": "Size",
        "finish": "Finish",
        "color": "Color",
        "shape": "Shape",
        "pressure_rating": "Pressure Rating",
        "temperature_rating": "Temperature Rating",
        "voltage": "Voltage",
        "amperage": "Amperage",
        "wattage": "Wattage",
        "thread_type": "Thread Type",
        "connection_type": "Connection Type",
        "end_type": "End Type",
        "gender": "Gender",
        "application": "Application",
        "industry": "Industry",
        "series": "Series",
        "product_type": "Product Type",
    }

    # "400V" / "2.8-4 A" / "45 x 97 x 73 mm" / "150 lb" -> value + uom
    _UOM_SPLIT = re.compile(r"^\s*([\d.,/\-\s]+?)\s*([A-Za-zµ°%]{1,6})\.?\s*$")

    @classmethod
    def _split_value_uom(cls, raw: Any) -> tuple:
        """Split a trailing unit off a numeric-leading string. Best effort."""
        text = str(raw).strip()
        m = cls._UOM_SPLIT.match(text)
        if m and re.search(r"\d", m.group(1)):
            return m.group(1).strip(), m.group(2)
        return text, None

    def extract_from_description(
        self, product: ProductInput, understanding: ProductUnderstanding
    ) -> List[Dict[str, Any]]:
        """
        Deterministic fallback when NO manufacturer evidence could be
        retrieved (dead URLs, PDF-only sources, LLM unavailable).

        Candidate attributes come from the T4 product-understanding facts
        parsed out of the part description — NOT invented by an LLM.

        Honesty rules:
          - source stays None: these are NOT web-grounded, so they must not
            count toward grounding rate or show a fake citation
          - confidence 0.35 (< the 0.7 review threshold) so the normalizer
            flags every one of them needs_review=True for a human decision
        """
        candidates: List[Dict[str, Any]] = []
        facts = understanding.known_facts()

        for field_name in self._FIELD_LABELS:
            value = facts.get(field_name)
            if value is None or not str(value).strip():
                continue
            if field_name == "product_type":
                # Identity, not a technical attribute — skip to avoid noise.
                continue
            value_text, uom = self._split_value_uom(value)
            candidates.append({
                "label": self._FIELD_LABELS[field_name],
                "candidate_value": value_text,
                "candidate_uom": uom,
                "source": None,
                "source_page": None,
                "confidence": 0.35,
            })

        for name, value in (understanding.extra_attributes or {}).items():
            if value is None or not str(value).strip():
                continue
            value_text, uom = self._split_value_uom(value)
            candidates.append({
                "label": str(name).replace("_", " ").title()[:60],
                "candidate_value": value_text,
                "candidate_uom": uom,
                "source": None,
                "source_page": None,
                "confidence": 0.35,
            })

        if candidates:
            logger.info("Description fallback produced %d candidate attribute(s) for %s",
                        len(candidates), product.mfg_part_num or "row")
        return candidates
