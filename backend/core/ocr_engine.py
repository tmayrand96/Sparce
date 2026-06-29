import os
from pathlib import Path
from typing import Union, Dict, Any
from PIL import Image, UnidentifiedImageError
import pytesseract

class OCREngineError(Exception):
    """Custom exception class for OCR Engine pipeline failures."""
    pass

class OCREngine:
    """Handles image validation and local text extraction via Tesseract OCR."""
    
    def __init__(self) -> None:
        # We initialize the class with a safe fallback mapping for configurations if needed later
        pass

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
        Executes local OCR processing to extract text content from the target image.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            A structured payload containing the raw 'text' string and metadata status flags.
        """
        try:
            # First, filter the input path through our validation barrier
            clean_path = self.validate_image(image_path)
            
            # Execute physical pixel evaluation and text extraction
            # We open the image cleanly within a context manager
            with Image.open(clean_path) as img:
                raw_text = pytesseract.image_to_string(img)
                
            return {
                "status": "success",
                "raw_text": raw_text.strip(),
                "file_name": clean_path.name
            }
            
        except OCREngineError as ocr_err:
            # Capture our predictable structural barriers
            return {
                "status": "error",
                "error_type": "ValidationFailure",
                "message": str(ocr_err)
            }
        except Exception as system_err:
            # Capture unexpected system dependencies (e.g., Tesseract binary disconnected)
            return {
                "status": "error",
                "error_type": "SystemFailure",
                "message": f"Underlying OCR subsystem failed: {str(system_err)}"
            }