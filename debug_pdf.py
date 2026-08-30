#!/usr/bin/env python
"""
Debug script to inspect PDF content and understand structure.
"""

from pathlib import Path
from backend.core.pdf_parser import PDFDocumentParser

pdf_path = Path("tests/Rapport-Template-Soir.pdf")

parser = PDFDocumentParser()
result = parser.parse(pdf_path)

if result.get("status") == "success":
    text = result.get("raw_text", "")
    print("=" * 80)
    print("PDF CONTENT:")
    print("=" * 80)
    print(text)
    print("\n" + "=" * 80)
    print(f"Text length: {len(text)} characters")
    print("=" * 80)
else:
    print(f"Error parsing PDF: {result}")
