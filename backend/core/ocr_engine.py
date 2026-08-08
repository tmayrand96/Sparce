import logging
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
import pytesseract

from backend.processor_utils import convert_to_images
from backend.token_provider import BaseTokenProvider, EnvTokenProvider
from backend.utils.environment_check import EnvironmentDependencyError, verify_system_dependencies
from .pdf_parser import PDFDocumentParser

verify_system_dependencies(["pdftoppm"])

class OCREngineError(Exception):
    """Custom exception class for OCR Engine pipeline failures."""
    pass

class OCREngine:
    """Handles image validation and local text extraction via Tesseract OCR."""

    def __init__(self, provider: Optional[BaseTokenProvider] = None) -> None:
        self.provider = provider or EnvTokenProvider()
        self.logger = logging.getLogger(__name__)

    def _load_cv2(self):
        try:
            import cv2
            return cv2
        except ImportError:
            self.logger.warning(
                "OpenCV is not installed; falling back to Pillow preprocessing for OCR images."
            )
            return None

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        processed_image = image
        if processed_image.mode not in ("RGB", "L"):
            processed_image = processed_image.convert("RGB")

        image_array = np.array(processed_image)
        cv2 = self._load_cv2()

        if cv2 is not None:
            if image_array.ndim == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_array

            try:
                thresholded = cv2.adaptiveThreshold(
                    gray,
                    255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY,
                    15,
                    10,
                )
            except cv2.error as exc:
                self.logger.warning(
                    "OpenCV adaptive thresholding failed; falling back to Otsu thresholding: %s",
                    exc,
                )
                _, thresholded = cv2.threshold(
                    gray,
                    0,
                    255,
                    cv2.THRESH_BINARY + cv2.THRESH_OTSU,
                )

            return Image.fromarray(thresholded)

        grayscale_image = processed_image.convert("L")
        thresholded = grayscale_image.point(lambda px: 0 if px < 128 else 255)
        return thresholded.convert("L")

    def _run_tesseract(self, image: Image.Image) -> str:
        configs = [r"--oem 3 --psm 6", r"--oem 3 --psm 3", r"--oem 3 --psm 11"]
        for config in configs:
            try:
                raw_text = pytesseract.image_to_string(image, config=config).strip()
            except Exception as exc:
                self.logger.warning("Tesseract OCR failed for config %s: %s", config, exc)
                raw_text = ""

            if raw_text:
                if config != configs[0]:
                    self.logger.warning("Tesseract fallback succeeded with config %s", config)
                return raw_text

        self.logger.warning("Tesseract returned empty text for all PSM fallbacks.")
        return ""

    def _extract_text_from_pdf_images(self, pdf_path: Path) -> Dict[str, Any]:
        try:
            page_images = convert_to_images(str(pdf_path))
        except Exception as exc:
            return {
                "status": "error",
                "error_type": "SystemFailure",
                "source_type": "pdf",
                "message": f"Scanned PDF conversion failed: {exc}",
                "file_name": pdf_path.name,
            }

        if not page_images:
            return {
                "status": "error",
                "error_type": "SystemFailure",
                "source_type": "pdf",
                "message": "No PDF pages could be rendered for OCR.",
                "file_name": pdf_path.name,
            }

        results: List[Dict[str, Any]] = []
        for page_index, page_image in enumerate(page_images):
            try:
                processed_image = self._preprocess_image(page_image)
                page_text = self._run_tesseract(processed_image).strip()
                if page_text:
                    results.append({"page_index": page_index, "raw_text": page_text})
                else:
                    self.logger.warning(
                        "OCR produced no text for PDF page %s; continuing to next page.",
                        page_index,
                    )
            except Exception as exc:
                self.logger.warning(
                    "Preprocessing or OCR failed for PDF page %s: %s", page_index, exc
                )

        if not results:
            return {
                "status": "error",
                "error_type": "SystemFailure",
                "source_type": "pdf",
                "message": "Scanned PDF conversion produced no readable text.",
                "page_count": len(page_images),
                "file_name": pdf_path.name,
            }

        combined_text = "\n\n".join(page["raw_text"] for page in results)
        return {
            "status": "success",
            "source_type": "pdf",
            "page_count": len(page_images),
            "results": results,
            "raw_text": combined_text,
            "file_name": pdf_path.name,
        }

    def validate_image(self, image_path: Union[str, Path]) -> Path:
        """
        Validates the existence, type, and structural integrity of an image file.
        
        Args:
            image_path: The string path or Path object targeting the image.
            
        Returns:
            A verified Path object.
            
        Raises:
            OCREngineError: If the file is missing, unsupported, or corrupted.
        """
        target_path = Path(image_path)
        
        # 1. Structural File Existence Check
        if not target_path.exists():
            raise OCREngineError(f"Target image path does not exist: {target_path}")
        
        if not target_path.is_file():
            raise OCREngineError(f"Target path is a directory, expected a file: {target_path}")

        # 2. Functional Integrity Check (Using Pillow to test if it can open the asset)
        try:
            with Image.open(target_path) as img:
                img.verify()  # Verifies the internal stream integrity without loading whole pixels
        except UnidentifiedImageError:
            raise OCREngineError(f"Unsupported or invalid image format: {target_path.name}")
        except Exception as e:
            raise OCREngineError(f"Corrupted or unreadable image stream: {str(e)}")
            
        return target_path

    def extract_text(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Executes local OCR processing to extract text content from the target image or PDF.

        Args:
            image_path: Path to the image file or PDF document.

        Returns:
            A structured payload containing OCR results for each page/image.
        """
        try:
            target_path = Path(image_path)
            if not target_path.exists():
                raise OCREngineError(f"Target image path does not exist: {target_path}")
            if not target_path.is_file():
                raise OCREngineError(f"Target path is a directory, expected a file: {target_path}")

            if target_path.suffix.lower() == ".pdf":
                parser = PDFDocumentParser()
                parsed_result = parser.parse(target_path)

                if parsed_result.get("status") == "success":
                    raw_text = parsed_result.get("raw_text", "")
                    if raw_text and raw_text.strip():
                        return {
                            "status": "success",
                            "source_type": "pdf",
                            "page_count": parsed_result.get("page_count", 1),
                            "results": [{
                                "page_index": 0,
                                "raw_text": raw_text,
                            }],
                            "raw_text": raw_text,
                            "file_name": target_path.name,
                        }

                    self.logger.info(
                        "Native PDF text extraction returned no text; falling back to scanned PDF OCR."
                    )
                else:
                    self.logger.warning(
                        "Native PDF parser did not return success: %s",
                        parsed_result.get("message", "Unknown parser error"),
                    )

                return self._extract_text_from_pdf_images(target_path)

            clean_path = self.validate_image(target_path)
            with Image.open(clean_path) as img:
                corrected_image = ImageOps.exif_transpose(img)
                processed_image = self._preprocess_image(corrected_image)
                raw_text = self._run_tesseract(processed_image).strip()

            return {
                "status": "success",
                "source_type": "image",
                "page_count": 1,
                "results": [{
                    "page_index": 0,
                    "raw_text": raw_text,
                }],
                "raw_text": raw_text,
                "file_name": clean_path.name,
            }

        except OCREngineError as ocr_err:
            return {
                "status": "error",
                "error_type": "ValidationFailure",
                "message": str(ocr_err),
            }
        except Exception as system_err:
            return {
                "status": "error",
                "error_type": "SystemFailure",
                "message": f"Underlying OCR subsystem failed: {str(system_err)}",
            }
