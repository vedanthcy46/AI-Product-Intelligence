from pydantic import BaseModel
from typing import Optional, Literal, Dict, List


class Product(BaseModel):
    product_name: Optional[str] = None
    size: Optional[str] = None
    material: Optional[str] = None
    pressure_rating: Optional[str] = None
    thread_type: Optional[str] = None
    temperature_range: Optional[str] = None
    manufacturer_name: Optional[str] = None
    brand_name: Optional[str] = None
    classpath: Optional[str] = None
    attributes: List[Dict] = []   # list of {label, value, uom, source, confidence}
    descriptions: Dict[str, Optional[str]] = {}   # keyed by MOBILE_DESC, INVOICE_DESC, SHORT_DESC, LONG_DESC1, RETAIL_DESC, MARKETING_DESCRIPTION
    confidence: Dict[str, Literal["high", "medium", "low"]] = {}
    source: Dict[str, str] = {}
    flags: List[str] = []
