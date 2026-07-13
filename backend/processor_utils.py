from __future__ import annotations

from io import BytesIO
from typing import List

from PIL import Image

try:
    from pdf2image import convert_from_path
except ImportError:  # pragma: no cover - fallback for environments without pdf2image
    convert_from_path = None

try:
    import fitz  # type: ignore
except ImportError:  # pragma: no cover - fallback for environments without pymupdf
    fitz = None


def convert_to_images(pdf_path: str) -> List[Image.Image]:
    """Convert a PDF file into a list of high-resolution page images."""
    if not pdf_path:
        raise ValueError("PDF path must be provided")

    if convert_from_path is not None:
        images = convert_from_path(pdf_path, dpi=300)
        if images:
            return list(images)

    if fitz is not None:
        doc = fitz.open(pdf_path)
        try:
            images: List[Image.Image] = []
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                img_data = pix.tobytes("png")
                images.append(Image.open(BytesIO(img_data)))
            return images
        finally:
            doc.close()

    raise RuntimeError("No PDF conversion backend is available. Install pdf2image or pymupdf.")
