import logging
from pathlib import Path
from typing import Any, Dict, Union

import pdfplumber
from pypdf import PdfReader
import pytesseract

from backend.processor_utils import convert_to_images

from .base_document_parser import BaseDocumentParser


class PDFDocumentParser(BaseDocumentParser):
    """Parse PDF documents into a structured text payload."""

    def parse(self, document_path: Union[str, Path]) -> Dict[str, Any]:
        path = Path(document_path)
        logger = logging.getLogger(__name__)
        file_size_kb = path.stat().st_size / 1024 if path.exists() else 0
        text_chunks: list[str] = []
        page_count = 0

        if file_size_kb == 0:
            logger.warning("PDF metadata: file=%s pages=0 size_kb=0.00", path.name)
            return {
                "status": "error",
                "error_type": "empty_file",
                "source_type": "pdf",
                "message": "The uploaded PDF is empty.",
                "file_name": path.name,
                "page_count": 0,
                "file_size_kb": 0.0,
            }

        try:
            with pdfplumber.open(path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text_chunks.append(page_text.strip())
        except Exception as exc:
            logger.warning("pdfplumber extraction failed for %s: %s", path.name, exc)

        if not text_chunks:
            try:
                reader = PdfReader(str(path))
                page_count = len(reader.pages)
                if reader.is_encrypted:
                    logger.info(
                        "PDF metadata: file=%s pages=%s size_kb=%.2f",
                        path.name,
                        page_count,
                        file_size_kb,
                    )
                    return {
                        "status": "error",
                        "error_type": "encrypted",
                        "message": "The PDF is encrypted or password-protected and cannot be read.",
                        "file_name": path.name,
                        "page_count": page_count,
                        "file_size_kb": round(file_size_kb, 2),
                    }
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    if page_text and page_text.strip():
                        text_chunks.append(page_text.strip())
            except Exception as exc:
                return {
                    "status": "error",
                    "error_type": "invalid_pdf",
                    "source_type": "pdf",
                    "message": f"Unable to parse PDF content: {exc}",
                    "file_name": path.name,
                    "page_count": page_count,
                    "file_size_kb": round(file_size_kb, 2),
                }

        logger.info(
            "PDF metadata: file=%s pages=%s size_kb=%.2f",
            path.name,
            page_count,
            file_size_kb,
        )

        if text_chunks:
            return {
                "status": "success",
                "source_type": "pdf",
                "raw_text": "\n\n".join(text_chunks),
                "page_count": page_count,
                "file_name": path.name,
                "file_size_kb": round(file_size_kb, 2),
                "extraction_method": "native",
            }

        try:
            page_images = convert_to_images(str(path))
            ocr_chunks = [
                pytesseract.image_to_string(image).strip()
                for image in page_images
            ]
            ocr_text = "\n\n".join(text for text in ocr_chunks if text)
        except Exception as exc:
            logger.warning("OCR fallback failed for %s: %s", path.name, exc)
            ocr_text = ""

        if not ocr_text.strip():
            return {
                "status": "error",
                "error_type": "scanned_or_empty",
                "source_type": "pdf",
                "message": (
                    "No readable text was found. The PDF may be empty, a scanned document "
                    "without legible text, or its pages could not be rendered for OCR."
                ),
                "file_name": path.name,
                "page_count": page_count,
                "file_size_kb": round(file_size_kb, 2),
            }

        return {
            "status": "success",
            "source_type": "pdf",
            "raw_text": ocr_text,
            "page_count": page_count or len(ocr_chunks),
            "file_name": path.name,
            "file_size_kb": round(file_size_kb, 2),
            "extraction_method": "ocr",
        }
