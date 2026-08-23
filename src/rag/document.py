from dataclasses import dataclass
from typing import Optional

@dataclass
class Document:
    """Represents a downloaded manufacturer document."""
    url: str
    manufacturer: Optional[str]
    mpn: Optional[str]
    document_type: str
    text_content: str

@dataclass
class Chunk:
    """Represents a chunk of text from a manufacturer document."""
    text: str
    source_url: str
    manufacturer: Optional[str]
    mpn: Optional[str]
    document_type: str
    page: int

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "source_url": self.source_url,
            "manufacturer": self.manufacturer,
            "mpn": self.mpn,
            "document_type": self.document_type,
            "page": self.page,
        }
