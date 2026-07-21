from pathlib import Path
from typing import Optional, Union, Dict, Any

from PIL import Image, UnidentifiedImageError
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
                return {
                    "status": "error",
                    "error_type": "ValidationFailure",
                    "message": parsed_result.get("message", "Unable to parse PDF content"),
                }

            clean_path = self.validate_image(target_path)
            with Image.open(clean_path) as img:
                raw_text = pytesseract.image_to_string(img).strip()

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