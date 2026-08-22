import os
import json
import logging
from typing import List, Dict, Any, Optional

from src.preprocessing.models import ProductInput
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
