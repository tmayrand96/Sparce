from pathlib import Path
from typing import Any, Dict, Union

import pdfplumber
from pypdf import PdfReader

from .base_document_parser import BaseDocumentParser


class PDFDocumentParser(BaseDocumentParser):
    """Parse PDF documents into a structured text payload."""

    def parse(self, document_path: Union[str, Path]) -> Dict[str, Any]:
        path = Path(document_path)
        text_chunks: list[str] = []

        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text_chunks.append(page_text.strip())
        except Exception:
            text_chunks = []

        if not text_chunks:
            try:
                reader = PdfReader(str(path))
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    if page_text and page_text.strip():
                        text_chunks.append(page_text.strip())
            except Exception as exc:
                return {
                    "status": "error",
                    "source_type": "pdf",
                    "message": f"Unable to parse PDF content: {exc}",
                    "file_name": path.name,
                }

        if not text_chunks:
            return {
                "status": "error",
                "source_type": "pdf",
                "message": "No text could be extracted from the PDF.",
                "file_name": path.name,
            }

        return {
            "status": "success",
            "source_type": "pdf",
            "raw_text": "\n\n".join(text_chunks),
            "page_count": len(text_chunks),
            "file_name": path.name,
        }
