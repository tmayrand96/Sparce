from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Union


class BaseDocumentParser(ABC):
    """Contract for document parsers that extract text from a document path."""

    @abstractmethod
    def parse(self, document_path: Union[str, Path]) -> Dict[str, Any]:
        """Parse a document and return a structured text payload."""
        raise NotImplementedError


class DefaultDocumentParser(BaseDocumentParser):
    """Fallback parser for non-PDF documents that cannot be parsed by a specialized parser."""

    def parse(self, document_path: Union[str, Path]) -> Dict[str, Any]:
        path = Path(document_path)
        return {
            "status": "error",
            "source_type": "unsupported",
            "message": f"No parser registered for {path.suffix or 'unknown'} files",
            "file_name": path.name,
        }
